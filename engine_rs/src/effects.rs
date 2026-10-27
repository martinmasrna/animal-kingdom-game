//! The effect engine (engine/effects.py): the placement mechanic, event dispatch, the effect-stack interpreter and
//! its operations, removal, food, draws and shuffles, Roam, the delayed-effect scheduler, Dawn and Dusk. Card
//! behaviour itself is in cards.rs.

use smallvec::SmallVec;
use crate::actions::{Action, Target, SKIP};
use crate::cards::{self, Args, Hook};
use crate::data::*;
use crate::state::{GameResult, State, Unit};
use crate::statics;
use crate::strength::{effective_strength, placement_strength, raw_strength};
use crate::value::{m_flag, m_get_i, m_get_s, Map, Value};
use crate::vmap;

pub fn pn(p: Player) -> Value {
    Value::s(player_name(p))
}
pub fn cr_v(st: &State, cr: Cr) -> Value {
    Value::s(st.crname(cr))
}
pub fn card_v(st: &State, c: CardId) -> Value {
    Value::s(st.cname(c))
}
fn opt_cr(st: &State, cr: Option<Cr>) -> Value {
    cr.map(|c| cr_v(st, c)).unwrap_or(Value::Null)
}
fn step_player(st: &State, step: &Map, key: &str) -> Player {
    let _ = st;
    player_from(m_get_s(step, key).unwrap_or("A"))
}
fn step_card(st: &State, step: &Map, key: &str) -> Option<CardId> {
    m_get_s(step, key).and_then(|n| st.card_id(n))
}
fn step_cr(st: &State, step: &Map, key: &str) -> Option<Cr> {
    m_get_s(step, key).and_then(|n| st.map().cr(n))
}

// ============================================================== pending / requests

pub struct Pending {
    pub mode: &'static str,
    pub chooser: Player,
    pub optional: bool,
    pub options: Vec<Value>,
    pub placements: Vec<Map>,
    pub kind: Option<&'static str>,
    pub from_deck_reveal: bool,
}

impl Pending {
    pub fn choice(chooser: Player, optional: bool, options: Vec<Value>) -> Pending {
        Pending { mode: "choice", chooser, optional, options, placements: vec![], kind: None, from_deck_reveal: false }
    }
    pub fn revealed(mut self) -> Pending {
        self.from_deck_reveal = true;
        self
    }
    pub fn place(chooser: Player, optional: bool, placements: Vec<Map>) -> Pending {
        Pending { mode: "place", chooser, optional, options: vec![], placements, kind: None, from_deck_reveal: false }
    }
    pub fn to_map(&self) -> Map {
        let mut p = vmap!("mode" => Value::s(self.mode), "chooser" => pn(self.chooser), "optional" => Value::Bool(self.optional));
        if self.mode == "choice" {
            p.insert("options".into(), Value::List(self.options.clone()));
        } else {
            p.insert("placements".into(), Value::List(self.placements.iter().map(|m| Value::Map(m.clone())).collect()));
        }
        if self.from_deck_reveal {
            p.insert("from_deck_reveal".into(), Value::Bool(true));
        }
        if let Some(k) = self.kind {
            p.insert("kind".into(), Value::s(k));
        }
        p
    }
}

pub fn legal_pending(st: &State) -> Vec<Action> {
    let p = st.pending.as_ref().expect("no pending");
    let mut acts = Vec::new();
    if m_get_s(p, "mode") == Some("choice") {
        for o in p.get("options").and_then(|o| o.as_list()).unwrap() {
            acts.push(Action::Choice(o.clone()));
        }
    } else {
        for pl in p.get("placements").and_then(|o| o.as_list()).unwrap() {
            let m = pl.as_map().unwrap();
            acts.push(place_from_map(st, m));
        }
    }
    if m_flag(p, "optional") {
        acts.push(Action::skip());
    }
    acts
}

pub fn place_from_map(st: &State, m: &Map) -> Action {
    let t = m.get("target").and_then(|t| t.as_list()).unwrap();
    let kind = t[0].as_str().unwrap();
    let w = t[1].as_str().unwrap();
    let target = if kind == "hq" { Target::Hq(player_from(w)) } else { Target::Cr(st.map().cr(w).unwrap()) };
    Action::Place { card: st.card_id(m_get_s(m, "card_id").unwrap()).unwrap(), target, iid: m_get_i(m, "iid") }
}

pub fn place_dict(st: &State, card: CardId, target: &Target, iid: Option<i64>) -> Map {
    let t = match target {
        Target::Cr(c) => Value::List(vec![Value::s("cr"), cr_v(st, *c)]),
        Target::Hq(p) => Value::List(vec![Value::s("hq"), pn(*p)]),
    };
    let mut d = vmap!("card_id" => card_v(st, card), "target" => t);
    if let Some(i) = iid {
        d.insert("iid".into(), Value::Int(i));
    }
    d
}

pub fn apply_pending(st: &mut State, action: &Action) {
    let mode = m_get_s(st.pending.as_ref().unwrap(), "mode").unwrap_or("").to_string();
    let step = st.effect_stack.last_mut().expect("a pending choice with no paused step");
    if mode == "choice" {
        if let Action::Choice(v) = action {
            step.insert("choice".into(), v.clone());
        }
    } else if action.is_skip() {
        step.insert("place_action".into(), Value::s(SKIP));
    } else if let Action::Place { card, target, iid } = action {
        let d = {
            let t = match target {
                Target::Cr(c) => Value::List(vec![Value::s("cr"), Value::Str(st.crname(*c))]),
                Target::Hq(p) => Value::List(vec![Value::s("hq"), pn(*p)]),
            };
            let mut d = vmap!("card_id" => Value::Str(st.cname(*card)), "target" => t);
            if let Some(i) = iid {
                d.insert("iid".into(), Value::Int(*i));
            }
            d
        };
        st.effect_stack.last_mut().unwrap().insert("place_action".into(), Value::Map(d));
    }
    st.pending = None;
}

// ===================================================================== resolve loop

pub fn resolve(st: &mut State) {
    loop {
        drain(st);
        if st.pending.is_some() || st.result.is_some() || !st.effect_stack.is_empty() {
            return;
        }
        if !remove_below_zero(st) {
            return;
        }
    }
}

/// An animal whose strength drops below 0 dies: removed by the rules, not by an effect, so Armor doesn't stop it.
fn remove_below_zero(st: &mut State) -> bool {
    let dying: Vec<(Cr, i64, Player)> = st
        .sorted_occupied()
        .into_iter()
        .filter_map(|cr| st.top(cr).filter(|u| raw_strength(st, u, None) < 0).map(|u| (cr, u.iid, u.owner)))
        .collect();
    for &(cr, iid, owner) in &dying {
        remove_specific(st, cr, iid, owner, false, None, false);
    }
    !dying.is_empty()
}

fn drain(st: &mut State) {
    while st.pending.is_none() && st.result.is_none() && !st.effect_stack.is_empty() {
        let mut step = st.effect_stack.pop().unwrap();
        let n = st.effect_stack.len();
        let was = (st.cause, st.cause_iid);
        st.cause = step_card(st, &step, "by_card");
        st.cause_iid = m_get_i(&step, "by_iid");
        let op = m_get_s(&step, "op").unwrap_or("").to_string();
        let req = run_op(st, &op, &mut step);
        st.cause = was.0;
        st.cause_iid = was.1;
        if let Some(by_card) = step.get("by_card").cloned() {
            if by_card.as_str().map(|s| !s.is_empty()).unwrap_or(false) {
                let by_iid = step.get("by_iid").cloned();
                for new in st.effect_stack[n..].iter_mut() {
                    if !new.contains_key("by_card") {
                        new.insert("by_card".into(), by_card.clone());
                    }
                    if let Some(bi) = &by_iid {
                        if new.get("by_card") == Some(&by_card) && !new.contains_key("by_iid") {
                            new.insert("by_iid".into(), bi.clone());
                        }
                    }
                }
            }
        }
        if let Some(req) = req {
            st.effect_stack.push(step);
            st.pending = Some(req.to_map());
            return;
        }
    }
}

// ================================================================== mulligan

fn op_mulligan(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    let p = player as usize;
    let mut done = false;
    if let Some(choice) = step.shift_remove("choice") {
        if choice.as_str() == Some(SKIP) {
            done = true;
        } else if let Some(iid) = choice.as_i64() {
            let returned: Vec<CardId> = step.get("returned").unwrap().as_list().unwrap().iter().map(|v| st.card_id(v.as_str().unwrap()).unwrap()).collect();
            if let Some(pos) = st.hands[p].iter().position(|u| u.iid == iid) {
                let inst_card = st.hands[p][pos].card;
                let mut black = returned.clone();
                black.push(inst_card);
                if mulligan_replacement(&st.decks[p], &black).is_some() {
                    let inst = st.hands[p].remove(pos);
                    step.get_mut("returned").unwrap().as_list_mut().unwrap().push(card_v(st, inst.card));
                    let i = mulligan_replacement(&st.decks[p], &black).unwrap();
                    let cid = st.decks[p].remove(i);
                    let iid_new = st.new_iid();
                    let new = Unit::new(cid, player, iid_new);
                    st.hands[p].push(new.clone());
                    crate::emit!(st, "mulligan", vmap!("player" => pn(player), "returned" => Value::Int(inst.iid),
                        "drawn" => Value::List(vec![Value::Int(new.iid), card_v(st, new.card)])));
                }
            }
        }
    }
    let returned: Vec<CardId> = step.get("returned").unwrap().as_list().unwrap().iter().map(|v| st.card_id(v.as_str().unwrap()).unwrap()).collect();
    let cap = st.cfg().mulligan_cap(player, st.first_player);
    if !done && !st.hands[p].is_empty() && (returned.len() as i32) < cap && mulligan_replacement(&st.decks[p], &returned).is_some() {
        let mut req = Pending::choice(player, true, st.hands[p].iter().map(|u| Value::Int(u.iid)).collect());
        req.kind = Some("mulligan");
        return Some(req);
    }
    if !returned.is_empty() {
        st.decks[p].extend(returned.iter().copied());
        let mut d = std::mem::take(&mut st.decks[p]);
        st.rng.shuffle(&mut d);
        st.decks[p] = d;
    }
    if !st.effect_stack.iter().any(|s| m_get_s(s, "op") == Some("mulligan")) {
        for q in [A, B] {
            st.ensure_mates(q, None);
        }
        let cur = st.current;
        let t = st.turn_counter;
        crate::emit!(st, "turn_start", vmap!("player" => pn(cur), "turn" => Value::Int(t as i64)));
    }
    None
}

fn mulligan_replacement(deck: &[CardId], blacklist: &[CardId]) -> Option<usize> {
    (0..deck.len()).rev().find(|&i| !blacklist.contains(&deck[i]))
}

// ============================================================ placement + events

pub fn do_placement(st: &mut State, player: Player, card: CardId, target: &Target, iid: Option<i64>) -> Result<(), String> {
    let p = player as usize;
    let unit = match iid {
        None => playable_copy(st, player, card),
        Some(i) => playable_copies(st, player, card).into_iter().find(|u| u.iid == i),
    };
    let unit = unit.ok_or_else(|| format!("{} has no playable {:?} in hand", player_name(player), st.cname(card)))?;
    let strength = placement_strength(st, &unit);
    let pos = st.hands[p].iter().position(|u| u.iid == unit.iid).unwrap();
    st.hands[p].remove(pos);
    let cost = st.card(card).food_cost;
    if cost != 0 {
        st.food[p] -= cost;
        crate::emit!(st, "pay", vmap!("player" => pn(player), "n" => Value::Int(cost as i64), "card" => card_v(st, card)));
    }
    st.units_placed_this_turn += 1;
    match target {
        Target::Hq(den) => {
            crate::emit!(st, "capture", vmap!("player" => pn(player), "iid" => Value::Int(unit.iid), "card" => card_v(st, card),
                "den" => pn(*den), "str" => Value::Int(strength as i64)));
            st.result = Some(GameResult { winner: Some(player), reason: "hq_capture".into() });
        }
        Target::Cr(cr) => land_unit(st, player, unit, *cr, true, true, true, false),
    }
    Ok(())
}

pub fn playable_copies(st: &State, player: Player, card: CardId) -> Vec<Unit> {
    st.hands[player as usize].iter().filter(|u| u.card == card && u.locked_until_turn as i32 <= st.turn_counter).cloned().collect()
}

/// (iid, copy) for each distinct playable version of `card` in hand.
pub fn copy_choices(st: &State, player: Player, card: CardId) -> Vec<(Option<i64>, Unit)> {
    let copies = playable_copies(st, player, card);
    let mut firsts: Vec<Unit> = Vec::new();
    for u in &copies {
        if !firsts.iter().any(|f| f.strength_counter == u.strength_counter) {
            firsts.push(u.clone());
        }
    }
    if firsts.len() <= 1 {
        return playable_copy(st, player, card).map(|b| vec![(None, b)]).unwrap_or_default();
    }
    firsts.into_iter().map(|u| (Some(u.iid), u)).collect()
}

pub fn canonical_place(st: &State, player: Player, action: &Action) -> Action {
    if let Action::Place { card, target, iid: Some(iid) } = action {
        let unit = st.hands[player as usize].iter().find(|u| u.iid == *iid && u.card == *card);
        let Some(unit) = unit else { return action.clone() };
        let choices = copy_choices(st, player, *card);
        if choices.len() == 1 && choices[0].0.is_none() {
            return Action::Place { card: *card, target: target.clone(), iid: None };
        }
        let rep = choices.iter().find(|(_, u)| u.strength_counter == unit.strength_counter).map(|(i, _)| *i).unwrap_or(Some(*iid));
        return Action::Place { card: *card, target: target.clone(), iid: rep };
    }
    action.clone()
}

/// The highest-counter copy that isn't Skunk-locked, first in hand order on ties.
pub fn playable_copy(st: &State, player: Player, card: CardId) -> Option<Unit> {
    let mut best: Option<&Unit> = None;
    for u in &st.hands[player as usize] {
        if u.card != card || u.locked_until_turn as i32 > st.turn_counter {
            continue;
        }
        if best.map(|b| u.strength_counter > b.strength_counter).unwrap_or(true) {
            best = Some(u);
        }
    }
    best.cloned()
}

fn take_from_hand(st: &mut State, player: Player, card: CardId) -> Unit {
    let p = player as usize;
    let mut best: Option<usize> = None;
    for (i, u) in st.hands[p].iter().enumerate() {
        if u.card == card && best.map(|b| u.strength_counter > st.hands[p][b].strength_counter).unwrap_or(true) {
            best = Some(i);
        }
    }
    st.hands[p].remove(best.expect("no copy in hand"))
}

/// The same instance lands on the board. `roar` false: an effect's placement that doesn't Roar; `play` false: placed,
/// not played; `reveal`: shown large as it lands.
pub fn land_unit(st: &mut State, player: Player, mut unit: Unit, cr: Cr, from_hand: bool, roar: bool, play: bool, reveal: bool) {
    let covered = st.top(cr).cloned();
    let is_apex = st.card(unit.card).has_kw(K_APEX);
    let onto_enemy = covered.as_ref().map(|c| c.owner != player).unwrap_or(false);
    unit.placed_on_turn = st.turn_counter as i16;
    st.stamp_played(&mut unit);
    let unit = unit;
    st.push_unit(cr, unit.clone());
    if st.record_events {    // the live game only: an imagined placement builds no event maps
        let mut f = vmap!("player" => pn(player), "iid" => Value::Int(unit.iid), "card" => card_v(st, unit.card), "cr" => cr_v(st, cr), "from_hand" => Value::Bool(from_hand));
        if reveal {
            f.insert("reveal".into(), Value::Bool(true));
        }
        st.emit("place", f);
        if let Some(c) = &covered {
            st.emit("cover", vmap!("cr" => cr_v(st, cr), "iid" => Value::Int(c.iid), "card" => card_v(st, c.card), "owner" => pn(c.owner), "by" => Value::Int(unit.iid)));
        }
    }
    if let Some(c) = &covered {
        push_theron(st, &unit, c);
    }
    if is_apex {
        if let Some(c) = &covered {
            st.effect_stack.push(vmap!("op" => Value::s("apex_eat"), "iid" => Value::Int(unit.iid), "prey" => Value::Int(c.iid), "by_card" => card_v(st, unit.card), "cr" => cr_v(st, cr), "owner" => pn(unit.owner)));
        }
    }
    push_reactions(st, &unit, cr, covered.as_ref(), onto_enemy);
    if onto_enemy {
        let c = covered.as_ref().unwrap();
        fire_cover_event(st, &unit, c);
        push_flee(st, c, &unit, cr);
    }
    if play && player <= B {
        st.turn_flags.played[player as usize].push((unit.iid, unit.card));
    }
    fire_place_event(st, &unit);
    if roar {
        let has_place = st.g.has_hook(unit.card, Hook::OnPlace);
        if Some(unit.card) != st.g.known.macaw && has_place {
            if player <= B {
                st.last_roar[player as usize] = Some(unit.card);
            }
        }
        let mut times = 1;
        if unit.owner <= B
            && st.roar_twice[unit.owner as usize] == Some(st.turn_counter)
            && Some(unit.card) != st.g.known.woodpecker
            && (has_place || (onto_enemy && st.g.has_hook(unit.card, Hook::OnPlaceOntoEnemy)))
        {
            st.roar_twice[unit.owner as usize] = None;
            times = 2;
        }
        for _ in 0..times {
            cards::run(st, unit.card, None, Hook::OnPlace, &unit, &Args::Place(cr));
            if onto_enemy {
                cards::run(st, unit.card, None, Hook::OnPlaceOntoEnemy, &unit, &Args::Place(cr));
            }
        }
    }
}

fn fire_cover_event(st: &mut State, coverer: &Unit, covered: &Unit) {
    if st.g.has_hook(coverer.card, Hook::OnCoverEnemy) {
        cards::run(st, coverer.card, None, Hook::OnCoverEnemy, coverer, &Args::Cover(covered.clone()));
    }
}

// King Theron, pushed before everything else the cover sets off so it resolves last (effects.py `_push_theron`).
fn push_theron(st: &mut State, coverer: &Unit, covered: &Unit) {
    if covered.owner == coverer.owner || !st.card(coverer.card).has_tag(T_CAT) {
        return;
    }
    let theron = st.g.known.lion_legend_3;
    for (_, iid) in statics::active_tops(st, coverer.owner, theron) {
        let top = st.unit_by_iid(iid).cloned().unwrap();
        if !capped(st, "cap_king_theron", &top) {
            let step = remove_iid_step(st, covered.iid, coverer.owner, true, None, Some(coverer.card));
            st.effect_stack.push(step);
        }
        return;
    }
}

fn push_flee(st: &mut State, covered: &Unit, coverer: &Unit, cr: Cr) {
    if coverer.owner != covered.owner && statics::has_keyword(st, covered, K_FLEE, Some(cr)) {
        st.effect_stack.push(vmap!("op" => Value::s("flee"), "iid" => Value::Int(covered.iid), "coverer" => Value::Int(coverer.iid),
            "by_card" => card_v(st, covered.card), "by_iid" => Value::Int(covered.iid)));
    }
}

fn op_flee(st: &mut State, step: &mut Map) -> Option<Pending> {
    let iid = m_get_i(step, "iid").unwrap();
    let Some((cr, pos)) = st.find_unit(iid) else { return None };
    let unit = st.unit_at(cr, pos).clone();
    bounce(st, cr, &unit, 0);
    if st.g.has_hook(unit.card, Hook::OnFlee) {
        cards::run(st, unit.card, None, Hook::OnFlee, &unit, &Args::Flee(m_get_i(step, "coverer").unwrap_or(-1)));
    }
    None
}

fn fire_place_event(st: &mut State, placed: &Unit) {
    let tops: SmallVec<[Unit; 16]> = st.tops().filter(|(_, t)| t.owner == placed.owner && t.iid != placed.iid).map(|(_, t)| *t).collect();
    for top in tops {
        if st.g.has_hook(top.card, Hook::OnFriendlyPlace) {
            cards::run(st, top.card, None, Hook::OnFriendlyPlace, &top, &Args::FriendlyPlace(placed.clone()));
        }
    }
}

fn push_reactions(st: &mut State, unit: &Unit, cr: Cr, covered: Option<&Unit>, _onto_enemy: bool) {
    let nbs: SmallVec<[Cr; 8]> = SmallVec::from_slice(st.map().neighbors(cr));
    for nb in nbs {
        let Some(top) = st.top(nb).cloned() else { continue };
        if top.owner != unit.owner && st.g.has_hook(top.card, Hook::OnEnemyPlacedAdjacent) {
            cards::run(st, top.card, None, Hook::OnEnemyPlacedAdjacent, &top, &Args::PlacedAdjacent(unit.clone(), cr));
        }
        if st.g.has_hook(top.card, Hook::OnAnimalPlacedAdjacent) {
            cards::run(st, top.card, None, Hook::OnAnimalPlacedAdjacent, &top, &Args::PlacedAdjacent(unit.clone(), cr));
        }
    }
    if let Some(covered) = covered {
        let keywords = statics::unit_keywords(st, covered, Some(cr), false);
        if keywords & K_SPIKES != 0 {
            spikes_covered(st, covered, unit, cr);
        }
        if keywords & K_POISON != 0 {
            poison_covered(st, covered, unit);
        }
        if st.g.has_hook(covered.card, Hook::OnCovered) {
            cards::run(st, covered.card, None, Hook::OnCovered, covered, &Args::Covered(unit.clone(), cr));
        }
        if covered.owner != unit.owner && st.card(covered.card).has_tag(T_COLONY) {
            push_queen_guards(st, covered.owner, unit, cr);
        }
        let watchers: SmallVec<[Unit; 16]> = st.tops().filter(|(_, t)| t.owner == covered.owner && t.iid != covered.iid).map(|(_, t)| *t).collect();
        for top in watchers {
            if st.g.has_hook(top.card, Hook::OnAllyCovered) {
                cards::run(st, top.card, None, Hook::OnAllyCovered, &top, &Args::AllyCovered(covered.clone(), unit.clone(), cr));
            }
        }
    }
}

fn push_queen_guards(st: &mut State, owner: Player, coverer: &Unit, cr: Cr) {
    let Some(guard) = st.g.known.hornet_legend else { return };
    let held = st.hands[owner as usize].iter().any(|u| u.card == guard) || st.decks[owner as usize].contains(&guard);
    if held {
        st.effect_stack.push(vmap!("op" => Value::s("queen_guard"), "card" => card_v(st, guard), "player" => pn(owner),
            "coverer" => Value::Int(coverer.iid), "cr" => cr_v(st, cr), "by_card" => card_v(st, guard)));
    }
}

fn op_queen_guard(st: &mut State, step: &mut Map) -> Option<Pending> {
    let cid = step_card(st, step, "card").unwrap();
    let owner = step_player(st, step, "player");
    let cr = step_cr(st, step, "cr").unwrap();
    let coverer = m_get_i(step, "coverer").unwrap();
    if !st.stack(cr).iter().any(|u| u.iid == coverer) {
        return None;
    }
    let p = owner as usize;
    let (inst, from_hand) = if let Some(pos) = st.hands[p].iter().position(|u| u.card == cid) {
        (st.hands[p].remove(pos), true)
    } else if let Some(pos) = st.decks[p].iter().position(|c| *c == cid) {
        st.decks[p].remove(pos);
        (st.deck_instance(owner, cid), false)
    } else {
        return None;
    };
    land_unit(st, owner, inst, cr, from_hand, false, false, true);
    None
}

// ================================================================= removal & food

/// Remove a specific unit from a stack (mid-stack ok), firing the removal reactions.
pub fn remove_specific(st: &mut State, cr: Cr, iid: i64, by_player: Player, by_effect: bool, by_card: Option<CardId>, armor_checked: bool) -> bool {
    let Some(pos) = st.stack(cr).iter().position(|u| u.iid == iid) else { return false };
    let unit = st.unit_at(cr, pos).clone();
    if by_effect && !armor_checked && !statics::can_be_removed(st, &unit, None, false) {
        return false;
    }
    let was_top = pos + 1 == st.stack(cr).len();
    crate::emit!(st, "remove", vmap!("cr" => cr_v(st, cr), "iid" => Value::Int(unit.iid), "card" => card_v(st, unit.card), "owner" => pn(unit.owner), "by" => pn(by_player)));
    st.take_unit(cr, iid);
    st.turn_flags.lost[unit.owner as usize] += 1;
    st.turn_flags.removed_any = true;
    if let Some(py) = st.g.known.python {
        for p in [A, B] {
            if owns_copy(st, p, py) {
                let g = st.cfg().int("python_growth");
                *st.card_strength_counters[p as usize].entry(py).or_insert(0) += g;
            }
        }
    }
    let uncovered = if was_top { st.top(cr).map(|u| u.iid) } else { None };
    let entered_pile = dispose(st, &unit);
    if entered_pile {
        fire_remove_event(st, unit.card, unit.owner, Some(cr), Some(by_player), by_card, uncovered);
    }
    fire_on_remove(st, &unit, cr, pos);
    true
}

fn dispose(st: &mut State, unit: &Unit) -> bool {
    st.pile_add(unit.card, Some(unit.owner));
    true
}

pub fn remove_top(st: &mut State, cr: Cr, by_player: Player, by_effect: bool, by_card: Option<CardId>) -> bool {
    let Some(top) = st.top(cr).cloned() else { return false };
    remove_specific(st, cr, top.iid, by_player, by_effect, by_card, false)
}

fn op_apex_eat(st: &mut State, step: &mut Map) -> Option<Pending> {
    let iid = m_get_i(step, "iid").unwrap();
    let Some((cr, i)) = st.find_unit(iid) else {
        // the cover's reactions removed the predator: it still eats (effects.py `_op_apex_eat`)
        let Some(cr) = step_cr(st, step, "cr") else { return None };
        let Some(prey) = st.top(cr).cloned() else { return None };
        if Some(prey.iid) == m_get_i(step, "prey") && statics::can_be_removed(st, &prey, Some(cr), true) {
            let owner = step_player(st, step, "owner");
            remove_specific(st, cr, prey.iid, owner, true, step_card(st, step, "by_card"), true);
        }
        return None;
    };
    let apex = st.unit_at(cr, i).clone();
    if i == 0 {
        return None;
    }
    let prey = st.unit_at(cr, i - 1).clone();
    if Some(prey.iid) == m_get_i(step, "prey") {
        let gained = effective_strength(st, &prey, None);
        if !statics::can_be_removed(st, &prey, Some(cr), true) {
            return None;
        }
        if remove_specific(st, cr, prey.iid, apex.owner, true, Some(apex.card), true) {
            let grown = if Some(apex.card) == st.g.known.anaconda {
                gained
            } else if Some(apex.card) == st.g.known.leopard_legend {
                st.cfg().int("leopard_legend_growth")
            } else {
                0
            };
            if grown != 0 {
                if let Some(a) = st.unit_by_iid_mut(apex.iid) {
                    a.strength_counter += grown as i16;
                }
                crate::emit!(st, "strength", vmap!("iid" => Value::Int(apex.iid), "card" => card_v(st, apex.card), "owner" => pn(apex.owner), "n" => Value::Int(grown as i64)));
            }
        }
    }
    None
}

fn fire_on_remove(st: &mut State, unit: &Unit, cr: Cr, pos: usize) {
    if st.g.has_hook(unit.card, Hook::OnRemove) {
        cards::run(st, unit.card, None, Hook::OnRemove, unit, &Args::Remove(cr, pos));
    }
}

pub fn food_gained_this_turn(st: &State, player: Player) -> i32 {
    st.turn_flags.food_gained[player.min(1) as usize]
}
pub fn fed_this_turn(st: &State, player: Player) -> bool {
    food_gained_this_turn(st, player) >= st.cfg().int("fed_threshold")
}
pub fn lost_this_turn(st: &State, player: Player) -> i32 {
    st.turn_flags.lost[player as usize]
}

pub fn lose_food(st: &mut State, player: Player, amount: i32, card: Option<CardId>) {
    let amount = amount.min(st.food[player as usize]);
    if amount > 0 {
        st.food[player as usize] -= amount;
        let mut f = vmap!("player" => pn(player), "n" => Value::Int(amount as i64));
        if let Some(c) = card {
            f.insert("card".into(), card_v(st, c));
        }
        crate::emit!(st, "pay", f);
    }
}

pub fn gain_food(st: &mut State, player: Player, amount: i32, rider: bool, income: bool) {
    let mut amount = amount;
    if let Some(cap) = statics::food_cap(st) {
        amount = amount.min(cap - food_gained_this_turn(st, player));
    }
    if amount <= 0 {
        return;
    }
    st.food[player as usize] += amount;
    let mut f = vmap!("player" => pn(player), "n" => Value::Int(amount as i64));
    if income {
        f.insert("income".into(), Value::Bool(true));
    }
    crate::emit!(st, "food", f);
    st.turn_flags.food_gained[player.min(1) as usize] += amount;
    if st.food[player as usize] >= st.map().win_food {
        st.result = Some(GameResult { winner: Some(player), reason: "food".into() });
        return;
    }
    if rider {
        let tops = statics::active_tops(st, player, st.g.known.bumblebee_legend);
        let falstaffs = tops.len() as i32;
        if falstaffs > 0 && !(st.cfg().flag("cap_falstaff") && st.turn_flags.falstaff[player.min(1) as usize]) {
            if st.cfg().flag("cap_falstaff") {
                st.turn_flags.falstaff[player.min(1) as usize] = true;
            }
            let was = (st.cause, st.cause_iid);
            st.cause = st.g.known.bumblebee_legend;
            st.cause_iid = Some(tops[0].1);
            let extra = falstaffs * st.cfg().int("bumblebee_legend_food_rider");
            gain_food(st, player, extra, false, false);
            st.cause = was.0;
            st.cause_iid = was.1;
        }
    }
}

// ============================================ draw / shuffle / remove event engine

pub struct RemoveEvent {
    pub card: CardId,
    pub owner: Player,
    pub cr: Option<Cr>,
    pub by_player: Option<Player>,
    pub by_card: Option<CardId>,
}

fn fire_remove_event(st: &mut State, card: CardId, owner: Player, cr: Option<Cr>, by_player: Option<Player>, by_card: Option<CardId>, skip: Option<i64>) {
    let ev = RemoveEvent { card, owner, cr, by_player, by_card };
    for c in st.sorted_occupied() {
        let top = st.top(c).cloned().unwrap();
        if Some(top.iid) == skip {
            continue;
        }
        if st.g.has_hook(top.card, Hook::OnRemoveEvent) {
            cards::run(st, top.card, None, Hook::OnRemoveEvent, &top, &Args::RemoveEvent(c, ev.card, ev.owner, ev.by_player, ev.by_card));
        }
    }
}

fn fire_shuffle_event(st: &mut State, card: CardId, player: Player) {
    for c in st.sorted_occupied() {
        let top = st.top(c).cloned().unwrap();
        if st.g.has_hook(top.card, Hook::OnShuffleEvent) {
            cards::run(st, top.card, None, Hook::OnShuffleEvent, &top, &Args::CardEvent(c, card, player));
        }
    }
    cards::rattlesnake_shuffle_event(st, player);
}

fn fire_draw_event(st: &mut State, card: CardId, player: Player) {
    for c in st.sorted_occupied() {
        let top = st.top(c).cloned().unwrap();
        if st.g.has_hook(top.card, Hook::OnDrawEvent) {
            cards::run(st, top.card, None, Hook::OnDrawEvent, &top, &Args::CardEvent(c, card, player));
        }
    }
}

fn fire_draw(st: &mut State, drawn: Vec<Unit>) {
    let mut drawn = drawn;
    if !drawn.is_empty() {
        let owner = drawn[0].owner;
        crate::emit!(st, "draw", vmap!("player" => pn(owner), "cards" => Value::List(drawn.iter().map(|u| Value::List(vec![Value::Int(u.iid), card_v(st, u.card)])).collect())));
        let over = st.hands[owner as usize].len() as i32 - st.cfg().hand_limit;
        if over > 0 {
            let keep = drawn.len().saturating_sub(over as usize);
            let burned: Vec<Unit> = drawn.split_off(keep);
            for inst in burned {
                remove_from_hand(st, inst.owner, inst.iid);
            }
        }
    }
    for inst in &drawn {
        fire_draw_event(st, inst.card, inst.owner);
        if st.g.has_hook(inst.card, Hook::OnDraw) {
            cards::run(st, inst.card, None, Hook::OnDraw, inst, &Args::None);
        }
    }
    if !drawn.is_empty() {
        let owner = drawn[0].owner;
        let before = st.hands[owner as usize].len();
        st.ensure_mates(owner, Some(drawn.clone()));
        let entered: Vec<Unit> = st.hands[owner as usize][before..].to_vec();
        burn_over_limit(st, owner, &entered);
    }
}

pub fn draw_cards(st: &mut State, player: Player, n: i32) -> Vec<Unit> {
    let drawn = st.draw(player, n);
    fire_draw(st, drawn.clone());
    drawn
}

pub fn draw_filtered_random(st: &mut State, player: Player, n: i32, spec: &str) -> Vec<Unit> {
    let mut drawn = Vec::new();
    for _ in 0..n.max(0) {
        let candidates: Vec<CardId> = st.decks[player as usize].iter().copied().filter(|c| matches(st, *c, spec)).collect();
        if candidates.is_empty() {
            break;
        }
        let cid = candidates[st.rng.choice_index(candidates.len())];
        let pos = st.decks[player as usize].iter().position(|c| *c == cid).unwrap();
        st.decks[player as usize].remove(pos);
        let inst = st.deck_instance(player, cid);
        st.hands[player as usize].push(inst.clone());
        drawn.push(inst);
    }
    fire_draw(st, drawn.clone());
    drawn
}

pub fn shuffle_back(st: &mut State, player: Player, cards: &[CardId], by: Option<Player>) {
    let p = player as usize;
    st.decks[p].extend(cards.iter().copied());
    let mut d = std::mem::take(&mut st.decks[p]);
    st.rng.shuffle(&mut d);
    st.decks[p] = d;
    for &c in cards {
        fire_shuffle_event(st, c, by.unwrap_or(player));
    }
}

pub fn gain_to_hand(st: &mut State, player: Player, card: CardId, strength_counter: i32) -> Unit {
    let before = st.hands[player as usize].len();
    let inst = st.add_to_hand(player, card, strength_counter);
    let entered: Vec<Unit> = st.hands[player as usize][before..].to_vec();
    burn_over_limit(st, player, &entered);
    inst
}

fn burn_over_limit(st: &mut State, player: Player, entered: &[Unit]) {
    let over = st.hands[player as usize].len() as i32 - st.cfg().hand_limit;
    if over <= 0 {
        return;
    }
    let start = entered.len().saturating_sub(over as usize);
    for inst in &entered[start..] {
        if st.hands[player as usize].iter().any(|u| u.iid == inst.iid) {
            remove_from_hand(st, player, inst.iid);
        }
    }
}

pub fn remove_from_hand(st: &mut State, player: Player, iid: i64) {
    let p = player as usize;
    let Some(pos) = st.hands[p].iter().position(|u| u.iid == iid) else { return };
    let inst = st.hands[p].remove(pos);
    st.pile_add(inst.card, Some(inst.owner));
    crate::emit!(st, "remove", vmap!("zone" => Value::s("hand"), "iid" => Value::Int(inst.iid), "card" => card_v(st, inst.card), "owner" => pn(inst.owner)));
    fire_remove_event(st, inst.card, inst.owner, None, None, None, None);
}

pub fn matches(st: &State, card: CardId, spec: &str) -> bool {
    if spec.contains('&') {
        return spec.split('&').all(|part| matches(st, card, part));
    }
    let (kind, val) = spec.split_once(':').unwrap_or((spec, ""));
    let c = st.card(card);
    match kind {
        "tag" => c.tags & tag_bit(val) != 0,
        "rarity" => c.rarity == val,
        "keyword" => c.keywords & kw_bit(val) != 0,
        _ => panic!("unknown filter spec {spec:?}"),
    }
}

pub fn capped(st: &mut State, flag_name: &'static str, unit: &Unit) -> bool {
    if !st.cfg().flag(flag_name) {
        return false;
    }
    if st.turn_flags.caps.iter().any(|(f, i)| *f == flag_name && *i == unit.iid) {
        return true;
    }
    st.turn_flags.caps.push((flag_name, unit.iid));
    false
}

// ========================================================== legal placement helper

pub fn legal_placements(st: &State, player: Player, allowed: Option<&[CardId]>, titan_ok: bool) -> Vec<Action> {
    let gm = st.map();
    let occ = st.connected_occupied(player);
    let enemy = other(player);
    let enemy_hq = gm.front(enemy).iter().any(|&c| occ & (1 << c) != 0);
    let mut connectable = 0u32;
    for &cr in &gm.sorted {
        if st.is_connected(player, cr, occ) {
            connectable |= 1 << cr;
        }
    }
    let mut ids: Vec<CardId> = st.hands[player as usize].iter().map(|u| u.card).collect();
    ids.sort_by(|a, b| st.cname(*a).cmp(st.cname(*b)));
    ids.dedup();
    let mut choices: Vec<(CardId, Option<i64>, Unit)> = Vec::new();
    for card in ids {
        if let Some(al) = allowed {
            if !al.contains(&card) {
                continue;
            }
        }
        for (iid, placer) in copy_choices(st, player, card) {
            choices.push((card, iid, placer));
        }
    }
    let mut out = Vec::new();
    let mut reach_cache: Vec<(i32, u32)> = Vec::new();
    for (card, iid, placer) in choices {
        let c = st.card(card);
        if c.food_cost > st.food[player as usize] {
            continue;
        }
        if c.has_kw(K_TITAN) && !titan_ok {
            continue;
        }
        let is_apex = c.has_kw(K_APEX);
        let flight = statics::ignores_connection(st, card);
        let mut extra = statics::extra_placement_crossroads(st, card, player);
        let reach = statics::reach_of(st, card);
        if reach > 0 {
            let mask = match reach_cache.iter().find(|(r, _)| *r == reach) {
                Some((_, m)) => *m,
                None => {
                    let m = statics::reach_crossroads(st, player, reach, occ);
                    reach_cache.push((reach, m));
                    m
                }
            };
            extra |= mask;
        }
        for &cr in &gm.sorted {
            let bit = 1u32 << cr;
            if !(flight || connectable & bit != 0 || extra & bit != 0) {
                continue;
            }
            match st.top(cr) {
                None => {
                    if !is_apex {
                        out.push(Action::Place { card, target: Target::Cr(cr), iid });
                    }
                }
                Some(top) => {
                    if is_apex {
                        if apex_can_land(st, &placer, top) {
                            out.push(Action::Place { card, target: Target::Cr(cr), iid });
                        }
                    } else if top.owner == player || statics::can_cover(st, &placer, top, false) {
                        out.push(Action::Place { card, target: Target::Cr(cr), iid });
                    }
                }
            }
        }
        if enemy_hq && !is_apex {
            out.push(Action::Place { card, target: Target::Hq(enemy), iid });
        }
    }
    out
}

fn apex_can_land(st: &State, placer: &Unit, top: &Unit) -> bool {
    if top.owner == placer.owner {
        return true;
    }
    statics::can_cover(st, placer, top, false)
}

// ======================================================================== Roam

pub fn legal_roams(st: &State, player: Player, free_only: bool) -> Vec<Action> {
    if !st.tops().any(|(_, u)| u.owner == player && statics::can_roam(st, u)) {
        return Vec::new();
    }
    let occ = st.connected_occupied(player);
    let mut out = Vec::new();
    for cr in st.sorted_occupied() {
        let unit = st.top(cr).unwrap();
        if unit.owner != player || !statics::can_roam(st, unit) || st.turn_flags.roamed.contains(&unit.iid) {
            continue;
        }
        if free_only && free_roams_left(st, player, Some(unit)) == 0 {
            continue;
        }
        for t in roam_targets(st, unit, cr, occ) {
            out.push(Action::Roam { origin: cr, target: t });
        }
    }
    out
}

pub fn roam_targets(st: &State, unit: &Unit, cr: Cr, occ: u32) -> Vec<Target> {
    let player = unit.owner;
    let enemy = other(player);
    let gm = st.map();
    let mut pack: u32 = 1 << cr;
    let mut queue = vec![cr];
    let mut qi = 0;
    while qi < queue.len() {
        let c = queue[qi];
        qi += 1;
        for &nb in gm.neighbors(c) {
            if pack & (1 << nb) == 0 && st.owner_of(nb) == Some(player) {
                pack |= 1 << nb;
                queue.push(nb);
            }
        }
    }
    let n = statics::reach_of(st, unit.card).max(1);
    let mut dist: Vec<i32> = vec![-1; gm.n()];
    let mut order: Vec<Cr> = Vec::new();
    for c in 0..gm.n() as Cr {
        if pack & (1 << c) != 0 {
            dist[c as usize] = 0;
            order.push(c);
        }
    }
    let mut qi = 0;
    while qi < order.len() {
        let c = order[qi];
        qi += 1;
        if dist[c as usize] < n {
            for &nb in gm.neighbors(c) {
                if dist[nb as usize] < 0 {
                    dist[nb as usize] = dist[c as usize] + 1;
                    order.push(nb);
                }
            }
        }
    }
    let is_apex = statics::has_keyword(st, unit, K_APEX, Some(cr));
    let mut out = Vec::new();
    for &c in &gm.sorted {
        if dist[c as usize] < 0 || c == cr {
            continue;
        }
        let ok = match st.top(c) {
            None => !is_apex,
            Some(top) => top.owner == player || statics::can_cover(st, unit, top, true),
        };
        if ok {
            out.push(Target::Cr(c));
        }
    }
    if !is_apex && occ & (1 << cr) != 0 && gm.front(enemy).iter().any(|&c| pack & (1 << c) != 0) {
        out.push(Target::Hq(enemy));
    }
    out
}

fn own_free_roams(st: &State, player: Player, unit: Option<&Unit>) -> i32 {
    let own = |iid: i64| st.turn_flags.free_roam_iid.iter().find(|(i, _)| *i == iid).map(|(_, n)| *n).unwrap_or(0);
    if let Some(u) = unit {
        return own(u.iid) as i32;
    }
    st.tops().filter(|(_, t)| t.owner == player && own(t.iid) != 0 && !st.turn_flags.roamed.contains(&t.iid)).count() as i32
}

pub fn free_roams_left(st: &State, player: Player, unit: Option<&Unit>) -> i32 {
    let p = player.min(1) as usize;
    let granted = statics::free_roams(st, player) + st.turn_flags.free_roams[p];
    (granted - st.turn_flags.free_roams_used[p]).max(0) + own_free_roams(st, player, unit)
}

pub fn pay_for_roam(st: &mut State, player: Player, unit: Option<&Unit>) {
    if let Some(u) = unit {
        if let Some(pos) = st.turn_flags.free_roam_iid.iter().position(|(i, n)| *i == u.iid && *n != 0) {
            st.turn_flags.free_roam_iid.remove(pos);
            return;
        }
    }
    if free_roams_left(st, player, unit) - own_free_roams(st, player, unit) != 0 {
        st.turn_flags.free_roams_used[player.min(1) as usize] += 1;
    } else {
        st.actions_taken_this_turn += 1;
    }
}

pub fn do_roam(st: &mut State, player: Player, origin: Cr, target: &Target) -> Result<(), String> {
    let unit = match st.top(origin) {
        Some(u) if u.owner == player => u.clone(),
        _ => return Err(format!("{} has no animal on {:?} to roam", player_name(player), st.crname(origin))),
    };
    if !st.turn_flags.roamed.contains(&unit.iid) {
        st.turn_flags.roamed.push(unit.iid);
    }
    st.turn_flags.roams[player.min(1) as usize] += 1;
    match target {
        Target::Hq(den) => {
            crate::emit!(st, "roam", vmap!("player" => pn(player), "iid" => Value::Int(unit.iid), "card" => card_v(st, unit.card), "cr" => cr_v(st, origin), "to" => Value::Null, "den" => pn(*den)));
            let s = effective_strength(st, &unit, None);
            crate::emit!(st, "capture", vmap!("player" => pn(player), "iid" => Value::Int(unit.iid), "card" => card_v(st, unit.card), "den" => pn(*den), "str" => Value::Int(s as i64), "roam" => Value::Bool(true)));
            st.result = Some(GameResult { winner: Some(player), reason: "hq_capture".into() });
            return Ok(());
        }
        Target::Cr(where_) => {
            let where_ = *where_;
            st.pop_top(origin);
            crate::emit!(st, "roam", vmap!("player" => pn(player), "iid" => Value::Int(unit.iid), "card" => card_v(st, unit.card), "cr" => cr_v(st, origin), "to" => cr_v(st, where_)));
            let covered = st.top(where_).cloned();
            let onto_enemy = covered.as_ref().map(|c| c.owner != player).unwrap_or(false);
            st.push_unit(where_, unit.clone());
            if let Some(c) = &covered {
                crate::emit!(st, "cover", vmap!("cr" => cr_v(st, where_), "iid" => Value::Int(c.iid), "card" => card_v(st, c.card), "owner" => pn(c.owner), "by" => Value::Int(unit.iid)));
            }
            if let Some(c) = &covered {
                push_theron(st, &unit, c);
            }
            if statics::has_keyword(st, &unit, K_APEX, Some(where_)) {
                if let Some(c) = &covered {
                    st.effect_stack.push(vmap!("op" => Value::s("apex_eat"), "iid" => Value::Int(unit.iid), "prey" => Value::Int(c.iid), "by_card" => card_v(st, unit.card), "cr" => cr_v(st, where_), "owner" => pn(unit.owner)));
                }
            }
            push_reactions(st, &unit, where_, covered.as_ref(), onto_enemy);
            if onto_enemy {
                let c = covered.as_ref().unwrap();
                fire_cover_event(st, &unit, c);
                push_flee(st, c, &unit, where_);
            }
            let event = RoamEvent { player, iid: unit.iid, from: origin, to: Some(where_), covered: covered.as_ref().map(|c| c.iid), onto_enemy };
            let watchers: Vec<Unit> = st.tops().filter(|(_, t)| t.owner == player && t.iid != unit.iid).map(|(_, t)| t.clone()).collect();
            for top in watchers {
                if st.g.has_hook(top.card, Hook::OnFriendlyRoam) {
                    cards::run(st, top.card, None, Hook::OnFriendlyRoam, &top, &Args::FriendlyRoam(unit.clone(), event.clone()));
                }
            }
            if st.g.has_hook(unit.card, Hook::OnRoam) {
                cards::run(st, unit.card, None, Hook::OnRoam, &unit, &Args::Roam(where_, event));
            }
        }
    }
    Ok(())
}

#[derive(Clone, Debug)]
pub struct RoamEvent {
    pub player: Player,
    pub iid: i64,
    pub from: Cr,
    pub to: Option<Cr>,
    pub covered: Option<i64>,
    pub onto_enemy: bool,
}

fn op_grant_free_roam(st: &mut State, step: &mut Map) -> Option<Pending> {
    let p = step_player(st, step, "player").min(1) as usize;
    st.turn_flags.free_roams[p] += m_get_i(step, "n").unwrap_or(0) as i32;
    None
}

// ============================================================= delayed scheduler

pub fn schedule(st: &mut State, unit: &Unit, owner_turn_delay: i32, mut step: Map, while_buried: bool, turn_of: Option<Player>) {
    if !step.contains_key("by_card") {
        step.insert("by_card".into(), card_v(st, unit.card));
    }
    if !step.contains_key("by_iid") {
        step.insert("by_iid".into(), Value::Int(unit.iid));
    }
    st.scheduled.push(vmap!("iid" => Value::Int(unit.iid), "owner" => pn(turn_of.unwrap_or(unit.owner)), "while_buried" => Value::Bool(while_buried),
        "remaining" => Value::Int(owner_turn_delay as i64), "step" => Value::Map(step)));
}

pub fn start_of_turn(st: &mut State, player: Player) {
    let on_board: Vec<i64> = st.order.iter().flat_map(|&c| st.stacks[c as usize].iter().map(|u| u.iid)).collect();
    let tops: Vec<i64> = st.tops().map(|(_, u)| u.iid).collect();
    let mut fired: Vec<Map> = Vec::new();
    let mut keep: Vec<Map> = Vec::new();
    let scheduled: Vec<Map> = std::mem::take(&mut *st.scheduled);
    for mut s in scheduled {
        let owner = m_get_s(&s, "owner").unwrap_or("");
        let iid = m_get_i(&s, "iid").unwrap_or(-1);
        if owner != player_name(player) && owner != "wild" {
            keep.push(s);
        } else if !on_board.contains(&iid) {
            continue;
        } else if !tops.contains(&iid) && !m_flag(&s, "while_buried") {
            keep.push(s);
        } else {
            let r = m_get_i(&s, "remaining").unwrap_or(0) - 1;
            s.insert("remaining".into(), Value::Int(r));
            if r <= 0 {
                fired.push(s);
            } else {
                keep.push(s);
            }
        }
    }
    st.scheduled = keep.into();
    let hand: Vec<Unit> = st.hands[player as usize].to_vec();
    for inst in hand {
        if st.g.has_hook(inst.card, Hook::OnDawnInHand) {
            cards::run(st, inst.card, None, Hook::OnDawnInHand, &inst, &Args::None);
        }
    }
    push_timed_hooks(st, player, Hook::OnStartOfTurn);   // Dawn, under the timers: the payouts resolve first
    for s in fired.into_iter().rev() {
        st.effect_stack.push(s.get("step").unwrap().as_map().unwrap().clone());
    }
}

pub fn end_of_turn(st: &mut State, player: Player) {
    cards::vultures_dusk(st, player);
    push_timed_hooks(st, player, Hook::OnEndOfTurn);
}

fn push_timed_hooks(st: &mut State, player: Player, hook: Hook) {
    let mut due: SmallVec<[(i32, &'static str, i64, &'static str, &'static str); 16]> = SmallVec::new();
    for (cr, top) in st.tops() {
        if top.owner != player {
            continue;
        }
        if st.g.has_hook(top.card, hook) {
            due.push((top.play_seq as i32, st.crname(cr), top.iid, st.cname(top.card), hook.name()));
        }
        if hook == Hook::OnStartOfTurn && st.card(top.card).has_kw(K_HUNGRY) {
            due.push((top.play_seq as i32, st.crname(cr), top.iid, st.cname(top.card), "hungry"));
        }
    }
    let times = if hook == Hook::OnEndOfTurn && !statics::active_tops(st, player, st.g.known.sloth_legend).is_empty() { 2 } else { 1 };
    due.sort();
    for (_, _, iid, card_name, hname) in due.into_iter().rev() {
        for _ in 0..times {
            st.effect_stack.push(vmap!("op" => Value::s("timed_hook"), "hook" => Value::s(hname), "iid" => Value::Int(iid), "player" => pn(player),
                "by_card" => Value::Str(card_name), "by_iid" => Value::Int(iid)));
        }
    }
}

fn op_timed_hook(st: &mut State, step: &mut Map) -> Option<Pending> {
    let iid = m_get_i(step, "iid").unwrap();
    let Some((cr, pos)) = st.find_unit(iid) else { return None };
    let unit = st.unit_at(cr, pos).clone();
    if pos + 1 != st.stack(cr).len() || player_name(unit.owner) != m_get_s(step, "player").unwrap_or("") {
        return None;
    }
    let hname = m_get_s(step, "hook").unwrap_or("");
    if hname == "hungry" {
        eat(st, &unit, cr);
        return None;
    }
    let hook = if hname == "on_start_of_turn" { Hook::OnStartOfTurn } else { Hook::OnEndOfTurn };
    if st.g.has_hook(unit.card, hook) {
        cards::run(st, unit.card, None, hook, &unit, &Args::Timed(cr));
    }
    None
}

fn eat(st: &mut State, unit: &Unit, cr: Cr) {
    if !statics::has_keyword(st, unit, K_HUNGRY, Some(cr)) {
        return;
    }
    let n = st.card(unit.card).hungry;
    let prev = (st.cause, st.cause_iid);
    st.cause = Some(unit.card);
    st.cause_iid = Some(unit.iid);
    let eaten = if unit.owner <= B { n.min(st.food[unit.owner as usize]) } else { 0 };
    if eaten > 0 {
        lose_food(st, unit.owner, eaten, Some(unit.card));
        st.hungry_eaten[unit.owner as usize] += eaten;
    }
    if eaten < n {
        if let Some(u) = st.unit_by_iid_mut(unit.iid) {
            u.strength_counter -= (n - eaten) as i16;
        }
        crate::emit!(st, "strength", vmap!("iid" => Value::Int(unit.iid), "card" => card_v(st, unit.card), "owner" => pn(unit.owner), "n" => Value::Int((eaten - n) as i64)));
    }
    st.cause = prev.0;
    st.cause_iid = prev.1;
}

// ===================================================================== op registry

fn op_gain_food(st: &mut State, step: &mut Map) -> Option<Pending> {
    gain_food(st, step_player(st, step, "player"), m_get_i(step, "amount").unwrap_or(0) as i32, true, false);
    None
}

fn op_draw(st: &mut State, step: &mut Map) -> Option<Pending> {
    draw_cards(st, step_player(st, step, "player"), m_get_i(step, "n").unwrap_or(0) as i32);
    None
}

fn op_draw_filtered(st: &mut State, step: &mut Map) -> Option<Pending> {
    let spec = m_get_s(step, "spec").unwrap_or("").to_string();
    draw_filtered_random(st, step_player(st, step, "player"), m_get_i(step, "n").unwrap_or(0) as i32, &spec);
    None
}

fn op_egg_hatch(st: &mut State, step: &mut Map) -> Option<Pending> {
    let iid = m_get_i(step, "iid").unwrap();
    let Some((cr, pos)) = st.find_unit(iid) else { return None };
    let egg = st.unit_at(cr, pos).clone();
    remove_specific(st, cr, egg.iid, egg.owner, false, None, false);
    let spec = m_get_s(step, "spec").unwrap_or("").to_string();
    draw_filtered_random(st, egg.owner, m_get_i(step, "n").unwrap_or(0) as i32, &spec);
    None
}

fn op_raven_dig(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    let p = player as usize;
    if !step.contains_key("remaining") {
        let n = st.cfg().int("raven_draw");
        draw_cards(st, player, n);
        let rem = st.cfg().int("raven_shuffle").min(st.hands[p].len() as i32);
        step.insert("remaining".into(), Value::Int(rem as i64));
        step.insert("shuffled".into(), Value::List(vec![]));
    }
    loop {
        if let Some(choice) = step.shift_remove("choice") {
            if let Some(iid) = choice.as_i64() {
                if let Some(pos) = st.hands[p].iter().position(|u| u.iid == iid) {
                    let inst = st.hands[p].remove(pos);
                    crate::emit!(st, "leave_hand", vmap!("zone" => Value::s("hand"), "owner" => pn(player), "iid" => Value::Int(inst.iid), "card" => card_v(st, inst.card), "to" => Value::s("deck")));
                    let cv = card_v(st, inst.card);
                    step.get_mut("shuffled").unwrap().as_list_mut().unwrap().push(cv);
                    let r = m_get_i(step, "remaining").unwrap_or(0) - 1;
                    step.insert("remaining".into(), Value::Int(r));
                }
            }
        }
        if m_get_i(step, "remaining").unwrap_or(0) > 0 && !st.hands[p].is_empty() {
            let options: Vec<Value> = st.hands[p].iter().map(|u| Value::Int(u.iid)).collect();
            if options.len() == 1 {
                step.insert("choice".into(), options[0].clone());
                continue;
            }
            return Some(Pending::choice(player, false, options).revealed());
        }
        break;
    }
    let shuffled: Vec<CardId> = step.get("shuffled").unwrap().as_list().unwrap().iter().map(|v| st.card_id(v.as_str().unwrap()).unwrap()).collect();
    if !shuffled.is_empty() {
        shuffle_back(st, player, &shuffled, None);
    }
    None
}

fn op_scout(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    let p = player as usize;
    if !step.contains_key("pulled") {
        let n = st.cfg().int("scout_count") as usize;
        let spec = m_get_s(step, "spec").map(|s| s.to_string());
        let order: Vec<usize> = match &spec {
            None => (0..st.decks[p].len()).rev().collect(),
            Some(sp) => {
                let mut o: Vec<usize> = (0..st.decks[p].len()).filter(|&i| matches(st, st.decks[p][i], sp)).collect();
                st.rng.shuffle(&mut o);
                o
            }
        };
        let mut picks: Vec<usize> = Vec::new();
        let mut seen: Vec<CardId> = Vec::new();
        for i in order {
            if picks.len() == n {
                break;
            }
            let c = st.decks[p][i];
            if !seen.contains(&c) {
                seen.push(c);
                picks.push(i);
            }
        }
        picks.sort_by(|a, b| b.cmp(a));
        let pulled: Vec<CardId> = picks.iter().map(|&i| st.decks[p].remove(i)).collect();
        if pulled.is_empty() {
            return None;
        }
        step.insert("pulled".into(), Value::List(pulled.iter().map(|c| card_v(st, *c)).collect()));
        let mut distinct: Vec<&'static str> = pulled.iter().map(|c| st.cname(*c)).collect();
        distinct.sort();
        distinct.dedup();
        if distinct.len() == 1 {
            step.insert("choice", Value::Str(distinct[0]));
        } else {
            return Some(Pending::choice(player, false, distinct.into_iter().map(Value::Str).collect()).revealed());
        }
    }
    let mut pulled: Vec<CardId> = step.get("pulled").unwrap().as_list().unwrap().iter().map(|v| st.card_id(v.as_str().unwrap()).unwrap()).collect();
    let choice = st.card_id(m_get_s(step, "choice").unwrap()).unwrap();
    if let Some(pos) = pulled.iter().position(|c| *c == choice) {
        pulled.remove(pos);
    }
    let inst = st.deck_instance(player, choice);
    st.hands[p].push(inst.clone());
    fire_draw(st, vec![inst]);
    shuffle_back(st, player, &pulled, None);
    None
}

fn op_bird_egg_hatch(st: &mut State, step: &mut Map) -> Option<Pending> {
    let iid = m_get_i(step, "iid").unwrap();
    let Some((cr, pos)) = st.find_unit(iid) else { return None };
    let egg = st.unit_at(cr, pos).clone();
    remove_specific(st, cr, egg.iid, egg.owner, false, None, false);
    st.effect_stack.push(vmap!("op" => Value::s("draw_filtered"), "player" => pn(egg.owner), "n" => Value::Int(1), "spec" => Value::s("tag:Bird")));
    None
}

fn op_remove_choice(st: &mut State, step: &mut Map) -> Option<Pending> {
    let options = step.get("options").and_then(|o| o.as_list()).cloned().unwrap_or_default();
    if options.is_empty() {
        return None;
    }
    if !step.contains_key("choice") {
        return Some(Pending::choice(step_player(st, step, "chooser"), m_flag(step, "optional"), options));
    }
    let chosen = step.get("choice").unwrap().clone();
    if chosen.as_str() == Some(SKIP) {
        return None;
    }
    let cr = st.map().cr(chosen.as_str().unwrap()).unwrap();
    let by_card = step_card(st, step, "by_card");
    remove_top(st, cr, step_player(st, step, "by_player"), true, by_card);
    None
}

pub fn remove_iid_step(st: &State, iid: i64, by_player: Player, by_effect: bool, source_iid: Option<i64>, by_card: Option<CardId>) -> Map {
    let mut m = vmap!("op" => Value::s("remove_iid"), "iid" => Value::Int(iid), "by_player" => pn(by_player), "by_effect" => Value::Bool(by_effect),
        "source_iid" => source_iid.map(Value::Int).unwrap_or(Value::Null));
    if let Some(c) = by_card {
        m.insert("by_card".into(), card_v(st, c));
    }
    m
}

pub fn remove_choice_step(st: &State, chooser: Player, options: Vec<Cr>, by_card: CardId, optional: bool) -> Map {
    vmap!("op" => Value::s("remove_choice"), "chooser" => pn(chooser), "by_player" => pn(chooser), "by_card" => card_v(st, by_card),
        "options" => Value::List(options.iter().map(|c| cr_v(st, *c)).collect()), "optional" => Value::Bool(optional))
}

fn op_remove_iid(st: &mut State, step: &mut Map) -> Option<Pending> {
    if let Some(src) = m_get_i(step, "source_iid") {
        if st.find_unit(src).is_none() {
            return None;
        }
    }
    let iid = m_get_i(step, "iid").unwrap();
    if let Some((cr, _)) = st.find_unit(iid) {
        let by_card = step_card(st, step, "by_card");
        remove_specific(st, cr, iid, step_player(st, step, "by_player"), m_flag(step, "by_effect"), by_card, false);
    }
    None
}

fn hand_allowed(st: &State, player: Player, filt: &Map) -> Vec<CardId> {
    let mut allowed: Vec<CardId> = Vec::new();
    let exclude = m_get_s(filt, "exclude_id").and_then(|n| st.card_id(n));
    let tags_all: u32 = filt.get("tags_all").and_then(|t| t.as_list()).map(|l| l.iter().filter_map(|x| x.as_str()).fold(0, |a, t| a | tag_bit(t))).unwrap_or(0);
    let tags_none: u32 = filt.get("tags_none").and_then(|t| t.as_list()).map(|l| l.iter().filter_map(|x| x.as_str()).fold(0, |a, t| a | tag_bit(t))).unwrap_or(0);
    for u in &st.hands[player as usize] {
        let c = st.card(u.card);
        if Some(u.card) == exclude {
            continue;
        }
        if c.tags & tags_all != tags_all {
            continue;
        }
        if c.tags & tags_none != 0 {
            continue;
        }
        if !allowed.contains(&u.card) {
            allowed.push(u.card);
        }
    }
    allowed
}

fn op_play_extra(st: &mut State, step: &mut Map) -> Option<Pending> {
    if m_flag(step, "played") {
        return None;
    }
    let chooser = step_player(st, step, "chooser");
    if let Some(pa) = step.get("place_action").cloned() {
        if pa.as_str() != Some(SKIP) {
            let m = pa.as_map().unwrap();
            if let Action::Place { card, target, iid } = place_from_map(st, m) {
                let _ = do_placement(st, chooser, card, &target, iid);
            }
        }
        step.insert("played".into(), Value::Bool(true));
        return None;
    }
    let filt = step.get("filter").and_then(|f| f.as_map()).cloned().unwrap_or_default();
    let allowed = hand_allowed(st, chooser, &filt);
    let mut placements = legal_placements(st, chooser, Some(&allowed), false);
    if let Some(near) = m_get_s(&filt, "adjacent_to").and_then(|n| st.map().cr(n)) {
        let enemy_den_near = st.map().in_front(other(chooser), near);
        placements.retain(|p| match p {
            Action::Place { target: Target::Cr(c), .. } => st.map().adjacent(near, *c),
            Action::Place { target: Target::Hq(_), .. } => enemy_den_near,
            _ => false,
        });
    }
    if placements.is_empty() {
        return None;
    }
    let dicts: Vec<Map> = placements.iter().map(|p| match p {
        Action::Place { card, target, iid } => place_dict(st, *card, target, *iid),
        _ => Map::default(),
    }).collect();
    Some(Pending::place(chooser, m_flag(step, "optional"), dicts))
}

fn op_play_named(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "chooser");
    let p = player as usize;
    let cid = step_card(st, step, "card_id").unwrap();
    if !step.contains_key("fetched") && m_flag(step, "make") {
        st.add_to_hand(player, cid, 0);              // a token made out of thin air (Queen Bee), only to be placed at once
        step.insert("fetched".into(), Value::s("made"));
    }
    if !step.contains_key("fetched") {
        let in_hand = st.hands[p].iter().any(|u| u.card == cid);
        if !in_hand && st.decks[p].contains(&cid) {
            let pos = st.decks[p].iter().position(|c| *c == cid).unwrap();
            st.decks[p].remove(pos);
            let jellied = st.jelly_take(player, cid).unwrap_or(0);
            st.add_to_hand(player, cid, jellied);
            step.insert("fetched".into(), Value::Bool(true));
        } else {
            step.insert("fetched".into(), Value::Bool(false));
        }
    }
    let return_if_fetched = |st: &mut State, step: &Map| {
        let made = step.get("fetched").and_then(|v| v.as_str()) == Some("made");
        if (made || m_flag(step, "fetched")) && st.hands[p].iter().any(|u| u.card == cid) {
            let back = take_from_hand(st, player, cid);
            if made {
                crate::emit!(st, "leave_hand", vmap!("zone" => Value::s("hand"), "owner" => pn(player), "iid" => Value::Int(back.iid), "card" => card_v(st, cid), "to" => Value::s("gone")));
                return;
            }
            crate::emit!(st, "leave_hand", vmap!("zone" => Value::s("hand"), "owner" => pn(player), "iid" => Value::Int(back.iid), "card" => card_v(st, cid), "to" => Value::s("deck")));
            st.decks[p].push(cid);
        }
    };
    if let Some(pa) = step.get("place_action").cloned() {
        if pa.as_str() == Some(SKIP) {
            return_if_fetched(st, step);
        } else if let Action::Place { card, target, iid } = place_from_map(st, pa.as_map().unwrap()) {
            let _ = do_placement(st, player, card, &target, iid);
        }
        return None;
    }
    let allowed: Vec<CardId> = if st.hands[p].iter().any(|u| u.card == cid) { vec![cid] } else { vec![] };
    let placements = legal_placements(st, player, Some(&allowed), false);
    if placements.is_empty() {
        return_if_fetched(st, step);
        return None;
    }
    let dicts: Vec<Map> = placements.iter().map(|pl| match pl {
        Action::Place { card, target, iid } => place_dict(st, *card, target, *iid),
        _ => Map::default(),
    }).collect();
    Some(Pending::place(player, false, dicts))
}

fn op_grant_strength(st: &mut State, step: &mut Map) -> Option<Pending> {
    let amount = m_get_i(step, "amount").unwrap_or(0) as i32;
    let iids: Vec<i64> = step.get("iids").and_then(|l| l.as_list()).map(|l| l.iter().filter_map(|v| v.as_i64()).collect()).unwrap_or_default();
    for iid in iids {
        let Some(inst) = st.find_instance_mut(iid) else { continue };
        inst.strength_counter += amount as i16;
        let inst = inst.clone();
        crate::emit!(st, "strength", vmap!("iid" => Value::Int(iid), "card" => card_v(st, inst.card), "owner" => pn(inst.owner), "n" => Value::Int(amount as i64)));
        if amount <= 0 {
            continue;
        }
        if st.find_unit(iid).is_some() {
            fire_on_gain_strength(st, &inst);
        } else if inst.owner <= B && st.hands[inst.owner as usize].iter().any(|u| u.iid == iid) {
            gain_in_hand(st, &inst, amount);
        } else {
            continue;
        }
        let now = st.find_instance(iid).cloned().unwrap_or(inst);
        if st.g.has_hook(now.card, Hook::OnGain) {
            cards::run(st, now.card, None, Hook::OnGain, &now, &Args::Gain(amount));
        }
    }
    None
}

fn gain_in_hand(st: &mut State, inst: &Unit, amount: i32) {
    if let Some(mate) = st.card(inst.card).mate {
        let p = inst.owner as usize;
        if let Some(pos) = st.hands[p].iter().position(|u| u.card == mate) {
            st.hands[p][pos].strength_counter += amount as i16;
            let partner = st.hands[p][pos].clone();
            crate::emit!(st, "strength", vmap!("iid" => Value::Int(partner.iid), "card" => card_v(st, partner.card), "owner" => pn(partner.owner), "n" => Value::Int(amount as i64)));
        }
    }
    if st.g.has_hook(inst.card, Hook::OnGainInHand) {
        cards::run(st, inst.card, None, Hook::OnGainInHand, inst, &Args::Gain(amount));
    }
}

fn op_cap_actions(st: &mut State, step: &mut Map) -> Option<Pending> {
    let p = step_player(st, step, "player").min(1) as usize;
    let n = m_get_i(step, "n").unwrap_or(0) as i32;
    let cur = st.turn_flags.action_cap[p].unwrap_or(n);
    st.turn_flags.action_cap[p] = Some(cur.min(n));
    None
}

fn op_grant_action(st: &mut State, step: &mut Map) -> Option<Pending> {
    let p = step_player(st, step, "player").min(1) as usize;
    st.turn_flags.bonus_actions[p] += m_get_i(step, "n").unwrap_or(0) as i32;
    None
}

// ============================================ instance / strength-counter helpers

fn fire_on_gain_strength(st: &mut State, unit: &Unit) {
    if !st.g.has_hook(unit.card, Hook::OnGainStrength) {
        return;
    }
    if st.turn_flags.gain_str.contains(&unit.iid) {
        return;
    }
    st.turn_flags.gain_str.push(unit.iid);
    let cr = statics::crossroad_of(st, unit.iid);
    cards::run(st, unit.card, None, Hook::OnGainStrength, unit, &Args::GainStrength(cr));
}

/// Crossroads adjacent to `cr` whose enemy top is removable within the bounds; `chosen` excludes Stealth.
pub fn adjacent_enemy_targets(st: &State, unit: &Unit, cr: Cr, max_strength: Option<i32>, min_strength: Option<i32>, chosen: bool) -> Vec<Cr> {
    let mut out = Vec::new();
    for &nb in st.map().neighbors(cr) {
        let Some(top) = st.top(nb) else { continue };
        if top.owner == unit.owner {
            continue;
        }
        if !statics::can_be_removed(st, top, Some(nb), false) {
            continue;
        }
        if chosen && !statics::can_be_chosen(st, top, unit.owner, Some(nb)) {
            continue;
        }
        let s = effective_strength(st, top, None);
        if max_strength.map(|m| s > m).unwrap_or(false) {
            continue;
        }
        if min_strength.map(|m| s < m).unwrap_or(false) {
            continue;
        }
        out.push(nb);
    }
    out
}

pub fn adjacent_friendly_units(st: &State, unit: &Unit, cr: Cr) -> Vec<Cr> {
    st.map().neighbors(cr).iter().copied().filter(|&nb| st.top(nb).map(|t| t.owner == unit.owner && statics::can_be_removed(st, t, Some(nb), false)).unwrap_or(false)).collect()
}

/// (crossroad, top) for every occupied crossroad adjacent to `cr`, sorted; only `owner`'s when given.
pub fn adjacent_tops(st: &State, cr: Cr, owner: Option<Player>) -> Vec<(Cr, Unit)> {
    st.map().neighbors(cr).iter().copied().filter_map(|nb| st.top(nb).filter(|t| owner.map(|o| t.owner == o).unwrap_or(true)).map(|t| (nb, t.clone()))).collect()
}

pub fn control_tag_count(st: &State, player: Player, tags: u32) -> i32 {
    st.tops().filter(|(_, u)| u.owner == player && st.card(u.card).tags & tags == tags).count() as i32
}

pub fn grant(st: &mut State, iids: Vec<i64>, amount: i32) {
    if !iids.is_empty() && amount != 0 {
        st.effect_stack.push(vmap!("op" => Value::s("grant_strength"), "iids" => Value::List(iids.into_iter().map(Value::Int).collect()), "amount" => Value::Int(amount as i64)));
    }
}

pub fn push_gain(st: &mut State, owner: Player, amount: i32) {
    if amount != 0 {
        st.effect_stack.push(vmap!("op" => Value::s("gain_food"), "player" => pn(owner), "amount" => Value::Int(amount as i64)));
    }
}

pub fn push_draw(st: &mut State, owner: Player, n: i32) {
    if n != 0 {
        st.effect_stack.push(vmap!("op" => Value::s("draw"), "player" => pn(owner), "n" => Value::Int(n as i64)));
    }
}

pub fn push_remove_choice(st: &mut State, owner: Player, by_card: CardId, targets: Vec<Cr>, optional: bool) {
    if !targets.is_empty() {
        let step = remove_choice_step(st, owner, targets, by_card, optional);
        st.effect_stack.push(step);
    }
}

/// A choice among `options` whose pick `then` acts on. `args`: extra fields of the step.
pub fn push_choose(st: &mut State, chooser: Player, options: Vec<Value>, then: &'static str, optional: bool, args: Map) {
    if options.is_empty() {
        return;
    }
    let mut m = vmap!("op" => Value::s("choose"), "chooser" => pn(chooser), "options" => Value::List(options), "then" => Value::s(then), "optional" => Value::Bool(optional));
    for (k, v) in args {
        m.insert(k, v);
    }
    st.effect_stack.push(m);
}

fn op_choose(st: &mut State, step: &mut Map) -> Option<Pending> {
    if !step.contains_key("choice") {
        let options = step.get("options").and_then(|o| o.as_list()).cloned().unwrap_or_default();
        let mut p = Pending::choice(step_player(st, step, "chooser"), m_flag(step, "optional"), options);
        p.from_deck_reveal = m_flag(step, "hidden");
        return Some(p);
    }
    let choice = step.get("choice").unwrap().clone();
    if choice.as_str() == Some(SKIP) {
        return None;
    }
    let then = m_get_s(step, "then").unwrap_or("").to_string();
    cards::then(st, &then, step, &choice);
    None
}

pub fn push_play_extra(st: &mut State, owner: Player, filter: Option<Map>, optional: bool) {
    st.effect_stack.push(vmap!("op" => Value::s("play_extra"), "chooser" => pn(owner), "filter" => Value::Map(filter.unwrap_or_default()), "optional" => Value::Bool(optional)));
}

/// Return a board unit to its owner's hand (no Remove Pile, no triggers).
pub fn bounce(st: &mut State, cr: Cr, top: &Unit, lock_until: i32) {
    crate::emit!(st, "bounce", vmap!("cr" => cr_v(st, cr), "iid" => Value::Int(top.iid), "card" => card_v(st, top.card), "owner" => pn(top.owner)));
    st.take_unit(cr, top.iid);
    if top.owner == WILD {
        return;
    }
    let inst = gain_to_hand(st, top.owner, top.card, 0);
    let p = top.owner as usize;
    if let Some(u) = st.hands[p].iter_mut().find(|u| u.iid == inst.iid) {
        u.locked_until_turn = lock_until as i16;
    }
}

/// A token made on `cr` by an effect: it lands as a placement would, with nothing to Roar.
pub fn spawn(st: &mut State, owner: Player, card: CardId, cr: Cr) {
    let iid = st.new_iid();
    land_unit(st, owner, Unit::new(card, owner, iid), cr, false, true, false, false);
}

pub fn empty_neighbors(st: &State, cr: Cr) -> Vec<Cr> {
    st.map().neighbors(cr).iter().copied().filter(|&nb| !st.occupied(nb)).collect()
}

pub fn hand_iids(st: &State, player: Player, tag: u32) -> Vec<i64> {
    st.hands[player as usize].iter().filter(|u| tag == 0 || st.card(u.card).tags & tag != 0).map(|u| u.iid).collect()
}

/// `inst` becomes another card, keeping its strength counter, in hand or on the board.
pub fn transform(st: &mut State, iid: i64, card: CardId) {
    let Some(inst) = st.find_instance_mut(iid) else { return };
    let was = inst.card;
    inst.card = card;
    let owner = inst.owner;
    st.recache();
    crate::emit!(st, "transform", vmap!("iid" => Value::Int(iid), "owner" => pn(owner), "card" => card_v(st, card), "was" => card_v(st, was)));
}

fn op_forced_roam(st: &mut State, step: &mut Map) -> Option<Pending> {
    let iid = m_get_i(step, "iid").unwrap();
    let Some((cr, pos)) = st.find_unit(iid) else { return None };
    if pos + 1 != st.stack(cr).len() || st.turn_flags.roamed.contains(&iid) {
        return None;
    }
    let unit = st.unit_at(cr, pos).clone();
    if statics::can_roam(st, &unit) {
        match st.turn_flags.free_roam_iid.iter_mut().find(|(i, _)| *i == iid) {
            Some(e) => e.1 = 1,
            None => st.turn_flags.free_roam_iid.push((iid, 1)),
        }
    }
    None
}

fn op_draw_to_match(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    let n = st.hands[other(player) as usize].len() as i32 - st.hands[player as usize].len() as i32;
    if n > 0 {
        draw_cards(st, player, n);
    }
    None
}

fn op_anteater(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    let drawn = draw_cards(st, player, 1);
    if let Some(d) = drawn.first() {
        if st.hands[player as usize].iter().any(|u| u.iid == d.iid) {
            let inst = st.hands[player as usize].iter().find(|u| u.iid == d.iid).cloned().unwrap();
            let s = placement_strength(st, &inst);
            gain_food(st, player, s, true, false);
        }
    }
    None
}

/// Grimm: one pick from the opponent's Remove Pile, then the next with the options asked afresh. As in Python.
fn op_steal_from_pile(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    let opp = crate::data::other(player);
    let n = m_get_i(step, "n").unwrap_or(0);
    let mut names: Vec<&'static str> = st.pile_cards_of(opp).iter().map(|c| st.cname(*c)).collect();
    names.sort();
    names.dedup();
    if names.is_empty() || n <= 0 {
        return None;
    }
    if n > 1 {
        let mut next = step.clone();
        next.insert("n", Value::Int(n - 1));
        st.effect_stack.push(next);
    }
    push_choose(st, player, names.into_iter().map(Value::Str).collect(), "pile_to_hand", false, vmap!("from_owner" => pn(opp)));
    None
}

fn op_oxpecker(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    draw_cards(st, player, 1);
    let hand = st.hands[player as usize].clone();
    if let Some(s) = hand.iter().map(|u| placement_strength(st, u)).max() {
        gain_food(st, player, s, true, false);
    }
    None
}

fn op_locust_eat(st: &mut State, step: &mut Map) -> Option<Pending> {
    let iid = m_get_i(step, "iid").unwrap();
    let Some((cr, pos)) = st.find_unit(iid) else { return None };
    if pos + 1 != st.stack(cr).len() {
        return None;
    }
    let by = step_player(st, step, "by_player");
    let locust = st.g.known.locust_swarm;
    if remove_top(st, cr, by, true, locust) {
        remove_top(st, cr, by, true, locust);
    }
    None
}

fn op_discard_choice(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    let hand = hand_iids(st, player, 0);
    if !hand.is_empty() {
        let mut args = Map::default();
        if let Some(bc) = step.get("by_card") {
            args.insert("by_card".into(), bc.clone());
        }
        push_choose(st, player, hand.into_iter().map(Value::Int).collect(), "discard", false, args);
    }
    None
}

fn op_hornet_kill(st: &mut State, step: &mut Map) -> Option<Pending> {
    let chooser = step_player(st, step, "chooser");
    if !step.contains_key("choice") {
        return Some(Pending::choice(chooser, false, step.get("options").and_then(|o| o.as_list()).cloned().unwrap_or_default()));
    }
    let choice = step.get("choice").unwrap().clone();
    if choice.as_str() == Some(SKIP) {
        return None;
    }
    let hornet = st.card_id("hornet").unwrap();
    if !cards::has_spare_copy(st, chooser, hornet) {
        return None; // no other Hornet left by the time the Roar resolves: nothing to discard, so nothing removed
    }
    cards::remove_another_copy(st, chooser, hornet);
    let cr = st.map().cr(choice.as_str().unwrap()).unwrap();
    remove_top(st, cr, chooser, true, Some(hornet));
    None
}

fn op_pestis_wipe(st: &mut State, step: &mut Map) -> Option<Pending> {
    let chooser = step_player(st, step, "chooser");
    if !step.contains_key("choice") {
        return Some(Pending::choice(chooser, false, step.get("options").and_then(|o| o.as_list()).cloned().unwrap_or_default()));
    }
    let choice = step.get("choice").unwrap().clone();
    if choice.as_str() == Some(SKIP) {
        return None;
    }
    let target = st.map().cr(choice.as_str().unwrap()).unwrap();
    let doomed: Vec<i64> = st.stack(target).iter().rev().filter(|u| statics::can_be_removed(st, u, None, false)).map(|u| u.iid).collect();
    let by_card = st.card_id("rat_legend_2");
    for iid in doomed {
        remove_specific(st, target, iid, chooser, true, by_card, true);
    }
    None
}

fn op_bounce_iid(st: &mut State, step: &mut Map) -> Option<Pending> {
    let iid = m_get_i(step, "iid").unwrap();
    if let Some((cr, pos)) = st.find_unit(iid) {
        let u = st.unit_at(cr, pos).clone();
        bounce(st, cr, &u, 0);
    }
    None
}

fn op_skunk_bounce(st: &mut State, step: &mut Map) -> Option<Pending> {
    let chooser = step_player(st, step, "chooser");
    if !step.contains_key("choice") {
        return Some(Pending::choice(chooser, false, step.get("options").and_then(|o| o.as_list()).cloned().unwrap_or_default()));
    }
    let choice = step.get("choice").unwrap().clone();
    let Some(cr) = choice.as_str().and_then(|s| st.map().cr(s)) else { return None };
    if let Some(top) = st.top(cr).cloned() {
        let lock = st.turn_counter + 2;
        bounce(st, cr, &top, lock);
    }
    None
}

fn op_venom(st: &mut State, step: &mut Map) -> Option<Pending> {
    let chooser = step_player(st, step, "chooser");
    if !step.contains_key("choice") {
        return Some(Pending::choice(chooser, false, step.get("options").and_then(|o| o.as_list()).cloned().unwrap_or_default()));
    }
    let choice = step.get("choice").unwrap().clone();
    let Some(cr) = choice.as_str().and_then(|s| st.map().cr(s)) else { return None };
    if let Some(target) = st.top(cr).cloned() {
        let by_card = step_card(st, step, "by_card");
        let inner = remove_iid_step(st, target.iid, chooser, true, None, by_card);
        st.scheduled.push(vmap!("iid" => Value::Int(target.iid), "owner" => pn(chooser), "remaining" => Value::Int(1), "while_buried" => Value::Bool(true), "step" => Value::Map(inner)));
    }
    None
}

fn op_magpie_steal(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    let p = player as usize;
    if !step.contains_key("stolen") {
        step.insert("stolen".into(), Value::Bool(true));
        let o = other(player) as usize;
        if !st.hands[o].is_empty() {
            let i = st.rng.choice_index(st.hands[o].len());
            let inst = st.hands[o].remove(i);
            let iid = st.new_iid();
            let new = Unit::new(inst.card, player, iid);
            let before = st.hands[p].len();
            st.hands[p].push(new.clone());
            crate::emit!(st, "steal", vmap!("player" => pn(player), "victim" => pn(other(player)), "iid" => Value::Int(inst.iid), "new" => Value::Int(new.iid), "card" => card_v(st, inst.card)));
            st.ensure_mates(player, Some(vec![new]));
            let entered: Vec<Unit> = st.hands[p][before..].to_vec();
            burn_over_limit(st, player, &entered);
        }
    }
    if st.hands[p].is_empty() {
        return None;
    }
    if !step.contains_key("choice") {
        if st.hands[p].len() == 1 {
            step.insert("choice".into(), Value::Int(st.hands[p][0].iid));
        } else {
            return Some(Pending::choice(player, false, st.hands[p].iter().map(|u| Value::Int(u.iid)).collect()).revealed());
        }
    }
    let iid = m_get_i(step, "choice").unwrap_or(-1);
    remove_from_hand(st, player, iid);
    None
}

fn op_hand_grant_one(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    let tag = m_get_s(step, "tag").map(tag_bit).unwrap_or(0);
    let options = hand_iids(st, player, tag);
    let mut args = vmap!("amount" => Value::Int(m_get_i(step, "amount").unwrap_or(0)));
    if let Some(bc) = step.get("by_card") {
        args.insert("by_card".into(), bc.clone());
    }
    push_choose(st, player, options.into_iter().map(Value::Int).collect(), "grant", false, args);
    None
}

fn op_hand_grant_all(st: &mut State, step: &mut Map) -> Option<Pending> {
    let player = step_player(st, step, "player");
    let iids = hand_iids(st, player, 0);
    grant(st, iids, m_get_i(step, "amount").unwrap_or(0) as i32);
    None
}

fn run_op(st: &mut State, op: &str, step: &mut Map) -> Option<Pending> {
    match op {
        "mulligan" => op_mulligan(st, step),
        "gain_food" => op_gain_food(st, step),
        "draw" => op_draw(st, step),
        "draw_filtered" => op_draw_filtered(st, step),
        "egg_hatch" => op_egg_hatch(st, step),
        "raven_dig" => op_raven_dig(st, step),
        "scout" => op_scout(st, step),
        "bird_egg_hatch" => op_bird_egg_hatch(st, step),
        "remove_choice" => op_remove_choice(st, step),
        "remove_iid" => op_remove_iid(st, step),
        "apex_eat" => op_apex_eat(st, step),
        "play_extra" => op_play_extra(st, step),
        "play_named" => op_play_named(st, step),
        "grant_strength" => op_grant_strength(st, step),
        "grant_action" => op_grant_action(st, step),
        "cap_actions" => op_cap_actions(st, step),
        "grant_free_roam" => op_grant_free_roam(st, step),
        "timed_hook" => op_timed_hook(st, step),
        "flee" => op_flee(st, step),
        "queen_guard" => op_queen_guard(st, step),
        "choose" => op_choose(st, step),
        "forced_roam" => op_forced_roam(st, step),
        "draw_to_match" => op_draw_to_match(st, step),
        "anteater" => op_anteater(st, step),
        "oxpecker" => op_oxpecker(st, step),
        "steal_from_pile" => op_steal_from_pile(st, step),
        "locust_eat" => op_locust_eat(st, step),
        "discard_choice" => op_discard_choice(st, step),
        "hornet_kill" => op_hornet_kill(st, step),
        "rat_legend_2_wipe" => op_pestis_wipe(st, step),
        "bounce_iid" => op_bounce_iid(st, step),
        "skunk_bounce" => op_skunk_bounce(st, step),
        "venom" => op_venom(st, step),
        "magpie_steal" => op_magpie_steal(st, step),
        "hand_grant_one" => op_hand_grant_one(st, step),
        "hand_grant_all" => op_hand_grant_all(st, step),
        _ => panic!("unknown op {op:?}"),
    }
}

// ============================================================ reactions to covers

fn spikes_covered(st: &mut State, covered: &Unit, coverer: &Unit, cr: Cr) {
    if coverer.owner == covered.owner || covered.retaliation_used {
        return;
    }
    if let Some(u) = st.unit_by_iid_mut(covered.iid) {
        u.retaliation_used = true;
    }
    if statics::can_be_removed(st, coverer, Some(cr), false) {
        let step = remove_iid_step(st, coverer.iid, covered.owner, true, None, Some(covered.card));
        st.effect_stack.push(step);
    }
}

fn poison_covered(st: &mut State, covered: &Unit, coverer: &Unit) {
    if coverer.owner == covered.owner {
        return;
    }
    let inner = remove_iid_step(st, coverer.iid, covered.owner, true, None, Some(covered.card));
    st.scheduled.push(vmap!("iid" => Value::Int(coverer.iid), "owner" => pn(covered.owner), "remaining" => Value::Int(1), "while_buried" => Value::Bool(true), "step" => Value::Map(inner)));
    crate::emit!(st, "poisoned", vmap!("iid" => Value::Int(coverer.iid), "card" => card_v(st, coverer.card), "owner" => pn(coverer.owner), "by" => Value::Int(covered.iid)));
}

pub fn owns_copy(st: &State, player: Player, card: CardId) -> bool {
    let p = player as usize;
    st.starting_decks[p].contains(&card)
        || st.decks[p].contains(&card)
        || st.hands[p].iter().any(|u| u.card == card)
        || st.order.iter().any(|&c| st.stacks[c as usize].iter().any(|u| u.card == card && u.owner == player))
}

pub fn find_unit_pair(st: &State, iid: i64) -> Option<(Cr, Unit)> {
    st.find_unit(iid).map(|(cr, p)| (cr, st.unit_at(cr, p).clone()))
}

pub fn opt_cr_value(st: &State, cr: Option<Cr>) -> Value {
    opt_cr(st, cr)
}
