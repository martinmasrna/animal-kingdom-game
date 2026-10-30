//! Card behaviour (the EFFECTS and THEN tables of engine/effects.py): which hooks a card has and what each does.

use crate::data::*;
use crate::effects::*;
use crate::state::{State, Unit};
use crate::statics;
use crate::strength::effective_strength;
use crate::value::{m_get_i, m_get_s, Map, Value};
use crate::vmap;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u32)]
pub enum Hook {
    OnPlace,
    OnPlaceOntoEnemy,
    OnCoverEnemy,
    OnFlee,
    OnFriendlyPlace,
    OnEnemyPlacedAdjacent,
    OnAnimalPlacedAdjacent,
    OnCovered,
    OnAllyCovered,
    OnRemove,
    OnRemoveEvent,
    OnDrawEvent,
    OnShuffleEvent,
    OnDraw,
    OnGain,
    OnGainInHand,
    OnGainStrength,
    OnStartOfTurn,
    OnEndOfTurn,
    OnDawnInHand,
    OnRoam,
    OnFriendlyRoam,
    OnFriendlyFlee,
}

impl Hook {
    pub fn name(self) -> &'static str {
        match self {
            Hook::OnStartOfTurn => "on_start_of_turn",
            Hook::OnEndOfTurn => "on_end_of_turn",
            Hook::OnPlace => "on_place",
            _ => "hook",
        }
    }
}

pub enum Args {
    None,
    Place(Cr),
    Cover(Unit),
    Flee(i64),
    FriendlyPlace(Unit),
    PlacedAdjacent(Unit, Cr),
    Covered(Unit, Cr),
    AllyCovered(Unit, Unit, Cr),
    Remove(Cr, usize),
    RemoveEvent(Cr, CardId, Player, Option<Player>, Option<CardId>),
    CardEvent(Cr, CardId, Player),
    Gain(i32),
    GainStrength(Option<Cr>),
    Timed(Cr),
    Roam(Cr, RoamEvent),
    FriendlyRoam(Unit, RoamEvent),
    FriendlyFlee(Unit),
}

const GROWS: &[Hook] = &[Hook::OnDawnInHand, Hook::OnStartOfTurn, Hook::OnGain];

/// The hooks each card has, as a bitmask over `Hook`.
pub fn hook_mask(card: &str) -> u32 {
    use Hook::*;
    let hooks: &[Hook] = match card {
        "cuckoo_legend" | "praying_mantis" | "raccoon" | "hammerhead" | "locust_legend" | "badger" | "coyote" | "street_dog" | "fox" | "wolverine" | "lion_legend"
        | "lion_legend_2" | "jaguar" | "serval" | "bobcat" | "alley_cat" | "kitten" | "bee_legend" | "forager_ant" | "nurse_bee" | "nurse_bumblebee"
        | "termite_king" | "termite_queen" | "queen_bee" | "soldier_ant" | "worker_ant" | "worker_bee" | "mole_legend"
        | "rat_legend_2" | "skunk_legend" | "falcon_legend" | "mole" | "naked_mole_rat" | "hornet" | "skunk" | "hare" | "cheetah" | "rat"
        | "falcon" | "bat" | "dolphin" | "mouse" | "raven_legend" | "hawk" | "cottonmouth" | "magpie" | "black_mamba" | "mosquito" | "raven"
        | "bird_egg" | "snake_egg" | "tuna_legend" | "swordfish" | "barracuda" | "piranha_legend" | "remora" | "cod" | "sardine" | "sunfish"
        | "capybara_legend" | "macaque_legend" | "rat_legend" | "chipmunk_legend" | "flying_squirrel" | "beaver" | "electric_eel" | "squirrel"
        | "chipmunk" | "gopher" | "mara" | "rodent_legend" | "octopus_legend_2" | "squirrel_legend" | "chameleon_legend" | "chameleon" | "black_bear"
        | "grizzly_bear" | "stag_beetle" | "owl" | "rhinoceros_legend" | "tiger_legend" | "rhinoceros" | "oxpecker" | "anteater" | "sloth"
        | "gorilla_legend" | "bee_legend_2" | "butterfly_legend_monarch" | "hummingbird" | "macaque" | "orangutan" | "tarsier" | "chimpanzee"
        | "baboon" | "stork" | "gorilla" | "zebra_legend" | "honey_badger" | "warthog" | "albatross" | "boar" | "gazelle" | "deer" | "impala" | "baby_impala" | "rabbit" | "vole"
        | "octopus" | "macaw" | "woodpecker" | "sperm_whale" | "butterfly" | "cuckoo" | "opossum" | "fox_legend" | "viper" | "andean_condor"
        | "ocelot" | "tutorial_lynx" | "tutorial_chipmunk" | "krill" | "dung_beetle_legend_form2" | "dung_beetle_legend_form3" | "dung_beetle_legend_form4" => &[OnPlace],
        "zebra" => &[OnFlee],
        "hamster" => &[OnDrawEvent],
        "deer_legend" => &[OnPlace, OnFriendlyFlee, OnFlee],
        "okapi" => &[OnStartOfTurn, OnEndOfTurn],
        "meerkat" => &[OnPlace, OnEnemyPlacedAdjacent],
        "pheasant_legend" | "earthworm" | "worm" | "cockroach" | "cockroach_legend" | "dart_frog" => &[OnRemove],
        "tarantula" | "sea_turtle" | "hyena" | "wolf_legend" | "queen_ant" | "scout_bee" | "army_ant_legend"
        | "anaconda_legend" | "manta_ray_legend" | "dormouse" | "tortoise_legend" | "whale_shark" | "dung_beetle" | "wildebeest"
        | "dingo" | "sperm_whale_legend" => &[OnEndOfTurn],
        "city_spider" | "goose_legend" | "bat_legend" | "baboon_legend" | "groundhog" => &[OnStartOfTurn],
        "wolf_legend_2" => &[OnFriendlyRoam, OnRoam],
        "bush_dog" | "jackal" => &[OnRoam],
        "elephant_legend" => &[OnPlace, OnRoam],
        "dhole" => &[OnCoverEnemy],
        "lion_legend_4" => &[OnRemoveEvent],
        "lynx" => &[OnPlaceOntoEnemy],
        "worker_wasp" | "african_wild_dog" => &[OnFriendlyPlace],
        "swan_legend" | "cuckoo_egg" | "golden_egg" => &[OnDraw],
        "manta_ray" => &[OnAllyCovered],
        "golden_orb_weaver" | "hippopotamus" => &[OnEnemyPlacedAdjacent],
        "butterfly_legend" => GROWS,
        "butterfly_legend_caterpillar" | "butterfly_legend_chrysalis" | "butterfly_legend_butterfly" => &[OnPlace, OnDawnInHand, OnStartOfTurn, OnGain],
        "caterpillar" => &[OnGainInHand],
        _ => &[],
    };
    hooks.iter().fold(0u32, |m, h| m | (1 << *h as u32))
}

/// Run `body`'s hook for `unit`, stamping what it pushes with the card (`as_card` when another card runs it as its
/// own, the Macaw). An inked animal has no effects.
pub fn run(st: &mut State, body: CardId, as_card: Option<CardId>, hook: Hook, unit: &Unit, args: &Args) {
    if st.is_inked(unit.iid) {
        return;
    }
    let stamp = as_card.unwrap_or(body);
    let n = st.effect_stack.len();
    let was = (st.cause, st.cause_iid);
    st.cause = Some(stamp);
    st.cause_iid = Some(unit.iid);
    let name = st.cname(body).to_string();
    dispatch(st, &name, hook, unit, args);
    st.cause = was.0;
    st.cause_iid = was.1;
    let stamp_v = card_v(st, stamp);
    for step in st.effect_stack[n..].iter_mut() {
        if !step.contains_key("by_card") {
            step.insert("by_card".into(), stamp_v.clone());
        }
        if step.get("by_card") == Some(&stamp_v) && !step.contains_key("by_iid") {
            step.insert("by_iid".into(), Value::Int(unit.iid));
        }
    }
}

fn cfg(st: &State, k: &str) -> i32 {
    st.cfg().int(k)
}

fn cid(st: &State, name: &str) -> CardId {
    st.card_id(name).unwrap_or_else(|| panic!("no card {name:?}"))
}

// ------------------------------------------------------------------ generic Roars

fn draws(st: &mut State, unit: &Unit, n: i32) {
    push_draw(st, unit.owner, n);
}
fn gains(st: &mut State, unit: &Unit, attr: &str) {
    let n = cfg(st, attr);
    push_gain(st, unit.owner, n);
}
fn removes(st: &mut State, unit: &Unit, cr: Cr, max_attr: Option<&str>, min_attr: Option<&str>) {
    let max = max_attr.map(|a| cfg(st, a));
    let min = min_attr.map(|a| cfg(st, a));
    let targets = adjacent_enemy_targets(st, unit, cr, max, min, true);
    push_remove_choice(st, unit.owner, unit.card, targets, false);
}
fn draws_filtered(st: &mut State, unit: &Unit, spec: &'static str, n: i32) {
    st.effect_stack.push(vmap!("op" => Value::s("draw_filtered"), "player" => pn(unit.owner), "n" => Value::Int(n as i64), "spec" => Value::s(spec)));
}
/// `card`: the card whose Roar this is, which a repeat (Big Gus, the Macaw) runs on its own unit.
fn conditional(st: &State, card: &str, unit: &Unit) -> bool {
    roar_condition(st, unit.owner, card, Some(unit)).unwrap_or(false)
}

/// Whether the "if ..." of `card`'s Roar holds; None for a card with no such condition.
pub fn roar_condition(st: &State, player: Player, card: &str, unit: Option<&Unit>) -> Option<bool> {
    let on_top = unit.map(|u| st.tops().any(|(_, t)| t.iid == u.iid)).unwrap_or(false);
    let card_tags = st.card_id(card).map(|c| st.card(c).tags).unwrap_or(0);
    let others = |tags: u32| -> i32 {
        let n = control_tag_count(st, player, tags);
        if on_top && card_tags & tags == tags {
            n - 1
        } else {
            n
        }
    };
    let colony_min = cfg(st, "colony_synergy_threshold");
    let hand_after = || st.hands[player as usize].len() as i32 - if unit.is_some() { 0 } else { 1 };
    let strength = || -> i32 {
        if let Some(u) = unit {
            return effective_strength(st, u, None);
        }
        let c = st.card_id(card).unwrap();
        playable_copy(st, player, c).map(|inst| crate::strength::placement_strength(st, &inst)).unwrap_or(0)
    };
    let placed_plus = st.units_placed_this_turn + if unit.is_some() { 0 } else { 1 };
    Some(match card {
        "gopher" | "mara" => fed_this_turn(st, player),
        "bobcat" | "tutorial_lynx" | "ocelot" => others(T_CAT) >= 1,
        "serval" => played_this_turn(st, player, T_CAT, unit) >= 1,
        "soldier_ant" | "nurse_bee" => others(T_COLONY) + 1 >= colony_min,
        "hammerhead" => lost_this_turn(st, player) >= 1,
        "hare" | "rat" => placed_plus >= cfg(st, "hare_played_min"),
        "macaque" => hand_after() >= cfg(st, "macaque_hand_min"),
        "gorilla" => strength() >= cfg(st, "gorilla_min"),
        "fox" => st.turn_flags.any_roamed,
        _ => return None,
    })
}

fn played_this_turn(st: &State, player: Player, tag: u32, unit: Option<&Unit>) -> i32 {
    if player > B {
        return 0;
    }
    st.turn_flags.played[player as usize].iter().filter(|(iid, c)| st.card(*c).tags & tag != 0 && unit.map(|u| u.iid != *iid).unwrap_or(true)).count() as i32
}

fn add_strength(st: &mut State, iid: i64, n: i32) {
    if let Some(u) = st.unit_by_iid_mut(iid) {
        u.strength_counter += n as i16;
        let u = u.clone();
        crate::emit!(st, "strength", vmap!("iid" => Value::Int(iid), "card" => card_v(st, u.card), "owner" => pn(u.owner), "n" => Value::Int(n as i64)));
    }
}

/// The Chameleons: the unit `me_iid`, if it is on the board, becomes a copy of `card` with `counter` (no Roar).
fn become_copy(st: &mut State, me_iid: i64, card: CardId, counter: i16) {
    if st.find_instance(me_iid).is_none() || st.find_unit(me_iid).is_none() {
        return;
    }
    if let Some(me) = st.find_instance_mut(me_iid) {
        me.strength_counter = counter;
    }
    transform(st, me_iid, card);
}

/// A copy carries the animal's ticking timers, as far along as they are: its own seen from the copy's side, the ones on
/// it (venom, poison) as they are. As in Python.
fn copy_timers(st: &mut State, src: &Unit, me_iid: i64, me_owner: Player) {
    let swap = |p: Player| -> Player {
        if src.owner == me_owner || src.owner == WILD {
            p
        } else if p == src.owner {
            me_owner
        } else if p == other(src.owner) {
            other(me_owner)
        } else {
            p
        }
    };
    let found: Vec<Map> = st.scheduled.iter().filter(|s| m_get_i(s, "iid") == Some(src.iid)).cloned().collect();
    for mut s in found {
        let Some(Value::Map(mut step)) = s.get("step").cloned() else { continue };
        let own = m_get_i(&step, "by_iid") == Some(src.iid);
        for (k, v) in step.0.iter_mut() {
            if (*k == "iid" || *k == "by_iid") && v.as_i64() == Some(src.iid) {
                *v = Value::Int(me_iid);
            } else if own && (*k == "player" || *k == "by_player") {
                if let Some(p) = v.as_str() {
                    *v = pn(swap(player_from(p)));
                }
            }
        }
        if own {
            if let Some(o) = m_get_s(&s, "owner") {
                let o = swap(player_from(o));
                s.insert("owner", pn(o));
            }
        }
        s.insert("iid", Value::Int(me_iid));
        s.insert("step", Value::Map(step));
        st.scheduled.push(s);
    }
}

fn put_back(st: &mut State, unit: &Unit, cr: Cr, pos: usize, counter: i32) {
    if st.pile_take(unit.card, Some(unit.owner)) {
        let iid = st.new_iid();
        let mut back = Unit::new(unit.card, unit.owner, iid);
        back.strength_counter = counter as i16;
        let at = pos.min(st.stack(cr).len());
        st.insert_unit(cr, at, back);
        crate::emit!(st, "place", vmap!("player" => pn(unit.owner), "iid" => Value::Int(iid), "card" => card_v(st, unit.card), "cr" => cr_v(st, cr), "from_hand" => Value::Bool(false), "at" => Value::Int(at as i64)));
    }
}

fn remove_tops(st: &mut State, unit: &Unit, crs: Vec<Cr>) {
    for nb in crs.into_iter().rev() {
        if let Some(top) = st.top(nb).cloned() {
            let step = remove_iid_step(st, top.iid, unit.owner, true, None, Some(unit.card));
            st.effect_stack.push(step);
        }
    }
}

fn adjacent_enemy_unit_crossroads(st: &State, unit: &Unit, cr: Cr, chosen: bool) -> Vec<Cr> {
    adjacent_tops(st, cr, None)
        .into_iter()
        .filter(|(nb, top)| top.owner != unit.owner && statics::can_be_removed(st, top, Some(*nb), false) && (!chosen || statics::can_be_chosen(st, top, unit.owner, Some(*nb))))
        .map(|(nb, _)| nb)
        .collect()
}

pub fn has_spare_copy(st: &State, player: Player, card: CardId) -> bool {
    st.hands[player as usize].iter().any(|u| u.card == card) || st.decks[player as usize].contains(&card)
}

pub fn remove_another_copy(st: &mut State, player: Player, card: CardId) {
    let p = player as usize;
    if let Some(inst) = st.hands[p].iter().find(|u| u.card == card).cloned() {
        remove_from_hand(st, player, inst.iid);
        return;
    }
    if let Some(pos) = st.decks[p].iter().position(|c| *c == card) {
        st.decks[p].remove(pos);
    }
    st.jelly_take(player, card);
    st.pile_add(card, Some(player));
    crate::emit!(st, "remove", vmap!("zone" => Value::s("deck"), "card" => card_v(st, card), "owner" => pn(player)));
    // a remove event from nowhere on the board: the Python engine fires it with cr None
    fire_remove_event_pub(st, card, player);
}

fn fire_remove_event_pub(st: &mut State, card: CardId, owner: Player) {
    // _fire_remove_event(state, card_id, player, None): the remove reactors on the board.
    for c in st.sorted_occupied() {
        let top = st.top(c).cloned().unwrap();
        if st.g.has_hook(top.card, Hook::OnRemoveEvent) {
            run(st, top.card, None, Hook::OnRemoveEvent, &top, &Args::RemoveEvent(c, card, owner, None, None));
        }
    }
}

fn fill(st: &mut State, unit: &Unit, cr: Cr) {
    let (c, o) = (unit.card, unit.owner);
    let p = o as usize;
    let hand_iids: Vec<i64> = st.hands[p].iter().filter(|u| u.card == c).map(|u| u.iid).collect();
    let deck_n = st.decks[p].iter().filter(|x| **x == c).count();
    // ("hand", inst) entries then ("deck", None) entries, shuffled
    let mut sources: Vec<Option<i64>> = hand_iids.iter().map(|i| Some(*i)).collect();
    sources.extend(std::iter::repeat(None).take(deck_n));
    st.rng.shuffle(&mut sources);
    let mut empty = empty_neighbors(st, cr);
    st.rng.shuffle(&mut empty);
    for (src, spot) in sources.into_iter().zip(empty.into_iter()) {
        if st.occupied(spot) || st.result.is_some() {
            continue;
        }
        let (inst, from_hand) = match src {
            Some(iid) => {
                let Some(pos) = st.hands[p].iter().position(|u| u.iid == iid) else { continue };
                (st.hands[p].remove(pos), true)
            }
            None => {
                let Some(pos) = st.decks[p].iter().position(|x| *x == c) else { continue };
                st.decks[p].remove(pos);
                (st.deck_instance(o, c), false)
            }
        };
        land_unit(st, o, inst, spot, from_hand, false, false, false);
    }
}

fn spawn_pups(st: &mut State, unit: &Unit, cr: Cr, n: i32, tokens: &[&str]) {
    let mut empty = empty_neighbors(st, cr);
    st.rng.shuffle(&mut empty);
    for (i, spot) in empty.into_iter().take(n.max(0) as usize).enumerate() {
        let t = cid(st, tokens[i % tokens.len()]);
        spawn(st, unit.owner, t, spot);
    }
}

fn adjacent_ally_fish(st: &State, unit: &Unit, cr: Cr) -> i32 {
    statics::fish_worth(st, unit.owner)
        * adjacent_tops(st, cr, Some(unit.owner)).iter().filter(|(_, t)| st.card(t.card).has_tag(T_FISH)).count() as i32
}

fn drain_place(st: &mut State, unit: &Unit, cr: Cr, amount: i32) {
    let options: Vec<Value> = adjacent_tops(st, cr, None)
        .into_iter()
        .filter(|(nb, top)| top.owner != unit.owner && statics::can_be_chosen(st, top, unit.owner, Some(*nb)))
        .map(|(nb, _)| cr_v(st, nb))
        .collect();
    push_choose(st, unit.owner, options, "drain", false, vmap!("amount" => Value::Int(amount as i64)));
}

fn it_roams(st: &mut State, iid: i64) {
    st.effect_stack.push(vmap!("op" => Value::s("it_roams"), "iid" => Value::Int(iid)));
}

fn crs(st: &State, v: Vec<Cr>) -> Vec<Value> {
    v.into_iter().map(|c| cr_v(st, c)).collect()
}

fn remove_all_adjacent(st: &mut State, unit: &Unit, cr: Cr) {
    for (nb, top) in adjacent_tops(st, cr, None) {
        if statics::can_be_removed(st, &top, Some(nb), false) {
            let step = remove_iid_step(st, top.iid, unit.owner, true, None, Some(unit.card));
            st.effect_stack.push(step);
        }
    }
}

/// Whenever a Canine of `owner`'s roams (the Black Wolf's own roam included): give it +1 strength and draw a card.
fn black_wolf_grows(st: &mut State, owner: Player, roamer: &Unit) {
    if st.card(roamer.card).has_tag(T_CANINE) {
        let g = cfg(st, "black_wolf_grant");
        grant(st, vec![roamer.iid], g);
        let d = cfg(st, "black_wolf_draw");
        push_draw(st, owner, d);
    }
}

/// Whether no enemy of `enemy_of` tops a crossroad next to `cr`: the animal on `cr` has no other enemy beside it.
fn lonely(st: &State, enemy_of: Player, cr: Cr) -> bool {
    !adjacent_tops(st, cr, None).iter().any(|(_, t)| t.owner != enemy_of)
}

/// The crossroads of `owner`'s other top animals connected to the one on `cr` through a chain of `owner`'s top animals,
/// in crossroad-name order.
fn connected_allies(st: &State, owner: Player, cr: Cr) -> Vec<Cr> {
    let gm = st.map();
    let mut seen: Vec<bool> = vec![false; gm.n()];
    seen[cr as usize] = true;
    let mut queue = vec![cr];
    let mut qi = 0;
    while qi < queue.len() {
        let c = queue[qi];
        qi += 1;
        for &nb in gm.neighbors(c) {
            if !seen[nb as usize] && st.owner_of(nb) == Some(owner) {
                seen[nb as usize] = true;
                queue.push(nb);
            }
        }
    }
    gm.sorted.iter().copied().filter(|&c| seen[c as usize] && c != cr).collect()
}

fn sweep(st: &mut State, unit: &Unit, cr: Cr, max_attr: &str) {
    let max = cfg(st, max_attr);
    for nb in adjacent_enemy_targets(st, unit, cr, Some(max), None, false) {
        let iid = st.top(nb).unwrap().iid;
        let step = remove_iid_step(st, iid, unit.owner, true, None, Some(unit.card));
        st.effect_stack.push(step);
    }
}

fn hq_adjacent_draw(st: &mut State, unit: &Unit, cr: Cr, n: i32) {
    if st.map().in_front(other(unit.owner), cr) {
        push_draw(st, unit.owner, n);
    }
}

fn chipmunk(st: &mut State, unit: &Unit) {
    let now = cfg(st, "chipmunk_food_now");
    push_gain(st, unit.owner, now);
    let later = cfg(st, "chipmunk_food_later");
    schedule(st, unit, 1, vmap!("op" => Value::s("gain_food"), "player" => pn(unit.owner), "amount" => Value::Int(later as i64)), false, None);
}

fn mole_legend(st: &mut State, unit: &Unit) {
    let o = unit.owner;
    st.effect_stack.push(vmap!("op" => Value::s("discard_choice"), "player" => pn(o)));
    push_play_extra(st, o, None, false);
    push_draw(st, o, 1);
}

fn mole(st: &mut State, unit: &Unit, cr: Cr) {
    push_play_extra(st, unit.owner, Some(vmap!("adjacent_to" => cr_v(st, cr))), false);
}

fn butterfly_evolve(st: &mut State, inst: &Unit) {
    const STAGES: [&str; 5] = ["butterfly_legend", "butterfly_legend_caterpillar", "butterfly_legend_chrysalis", "butterfly_legend_butterfly", "butterfly_legend_monarch"];
    let name = st.cname(inst.card).to_string();
    if let Some(i) = STAGES.iter().position(|s| *s == name) {
        if i + 1 < STAGES.len() {
            let next = cid(st, STAGES[i + 1]);
            transform(st, inst.iid, next);
        }
    }
}

fn draw_then_give_one(st: &mut State, unit: &Unit) {
    let g = cfg(st, "butterfly_grant");
    st.effect_stack.push(vmap!("op" => Value::s("hand_grant_one"), "player" => pn(unit.owner), "amount" => Value::Int(g as i64)));
    push_draw(st, unit.owner, 1);
}

fn butterfly_stage_place(st: &mut State, unit: &Unit, draw_attr: Option<&str>, grant_attr: &str) {
    let g = cfg(st, grant_attr);
    st.effect_stack.push(vmap!("op" => Value::s("hand_grant_all"), "player" => pn(unit.owner), "amount" => Value::Int(g as i64)));
    let n = draw_attr.map(|a| cfg(st, a)).unwrap_or(1);
    push_draw(st, unit.owner, n);
}

fn spawns_beside(st: &mut State, unit: &Unit, cr: Cr, token: &str) {
    let empty = empty_neighbors(st, cr);
    if !empty.is_empty() {
        let spot = empty[st.rng.choice_index(empty.len())];
        let t = cid(st, token);
        spawn(st, unit.owner, t, spot);
    }
}

fn twin_place(st: &mut State, unit: &Unit, twin: &'static str) {
    st.effect_stack.push(vmap!("op" => Value::s("play_named"), "chooser" => pn(unit.owner), "card_id" => Value::s(twin)));
}

fn base_int(st: &State, card: CardId) -> i32 {
    st.card(card).base.unwrap_or(0)
}

pub fn rattlesnake_shuffle_event(st: &mut State, player: Player) {
    let Some(rs) = st.g.known.rattlesnake else { return };
    if owns_copy(st, player, rs) {
        *st.card_strength_counters[player as usize].entry(rs).or_insert(0) += 1;
        crate::emit!(st, "strength", vmap!("card" => Value::s("rattlesnake"), "owner" => pn(player), "n" => Value::Int(1)));
    }
}

pub fn vultures_dusk(st: &mut State, player: Player) {
    let Some(vulture) = st.g.known.vulture else { return };
    let lost = st.turn_flags.lost[0] + st.turn_flags.lost[1];
    if lost < cfg(st, "vulture_removals") {
        return;
    }
    let p = player as usize;
    let in_hand: Vec<i64> = st.hands[p].iter().filter(|u| u.card == vulture).map(|u| u.iid).collect();
    for iid in in_hand {
        let empty: Vec<Cr> = st.map().sorted.iter().copied().filter(|&c| !st.occupied(c)).collect();
        if empty.is_empty() {
            return;
        }
        let Some(pos) = st.hands[p].iter().position(|u| u.iid == iid) else { continue };
        let inst = st.hands[p].remove(pos);
        let spot = empty[st.rng.choice_index(empty.len())];
        land_unit(st, player, inst, spot, true, false, false, false);
    }
    while st.decks[p].contains(&vulture) {
        let empty: Vec<Cr> = st.map().sorted.iter().copied().filter(|&c| !st.occupied(c)).collect();
        if empty.is_empty() {
            return;
        }
        let pos = st.decks[p].iter().position(|c| *c == vulture).unwrap();
        st.decks[p].remove(pos);
        let inst = st.deck_instance(player, vulture);
        let spot = empty[st.rng.choice_index(empty.len())];
        land_unit(st, player, inst, spot, false, false, false, false);
    }
}

// ------------------------------------------------------------------ the dispatch

fn dispatch(st: &mut State, card: &str, hook: Hook, unit: &Unit, args: &Args) {
    use Hook::*;
    let owner = unit.owner;
    let cr = match args {
        Args::Place(c) | Args::Timed(c) => *c,
        _ => 0,
    };
    match (card, hook) {
        // Aristocrats
        ("cuckoo_legend", OnPlace) => {
            let cap = cfg(st, "cuckoo_legend_max");
            let options: Vec<Cr> = adjacent_tops(st, cr, None)
                .into_iter()
                .filter(|(nb, top)| effective_strength(st, top, None) <= cap && statics::can_be_removed(st, top, Some(*nb), false) && statics::can_be_chosen(st, top, owner, Some(*nb)))
                .map(|(nb, _)| nb)
                .collect();
            let o = crs(st, options);
            push_choose(st, owner, o, "cuckoo", false, Map::default());
        }
        ("pheasant_legend", OnRemove) => {
            if st.pile_take(unit.card, Some(owner)) {
                shuffle_back(st, owner, &[unit.card], None);
            }
        }
        ("praying_mantis", OnPlace) => {
            let o = crs(st, adjacent_friendly_units(st, unit, cr));
            let n = cfg(st, "mantis_draw");
            push_choose(st, owner, o, "remove_and_draw", false, vmap!("n" => Value::Int(n as i64)));
        }
        ("tarantula", OnEndOfTurn) => {
            // "Dusk: remove the weakest animal next to this and gain its strength." (Martin, 2026-10-29: as the City Spider picks)
            let options: Vec<(Cr, i32)> = adjacent_tops(st, cr, None)
                .into_iter()
                .filter(|(nb, top)| statics::can_be_removed(st, top, Some(*nb), false))
                .map(|(nb, top)| (nb, effective_strength(st, &top, None)))
                .collect();
            if !options.is_empty() {
                let low = options.iter().map(|(_, s)| *s).min().unwrap();
                let lows: Vec<Cr> = options.iter().filter(|(_, s)| *s == low).map(|(nb, _)| *nb).collect();
                let nb = lows[st.rng.choice_index(lows.len())];
                remove_top(st, nb, owner, true, Some(unit.card));
                if low > 0 {
                    add_strength(st, unit.iid, low);
                }
            }
        }
        ("sea_turtle", OnEndOfTurn) => {
            let c = cid(st, "baby_turtle");
            gain_to_hand(st, owner, c, 0);
        }
        ("tiger_legend", OnPlace) => removes(st, unit, cr, Some("tiger_legend_max"), None),
        ("sperm_whale_legend", OnEndOfTurn) => {
            let options: Vec<(Cr, i32)> = adjacent_tops(st, cr, None)
                .into_iter()
                .filter(|(nb, top)| top.owner != unit.owner && statics::can_be_removed(st, top, Some(*nb), false))
                .map(|(nb, top)| (nb, effective_strength(st, &top, None)))
                .collect();
            if !options.is_empty() {
                let high = options.iter().map(|(_, s)| *s).max().unwrap();
                let highs: Vec<Cr> = options.iter().filter(|(_, s)| *s == high).map(|(nb, _)| *nb).collect();
                let nb = highs[st.rng.choice_index(highs.len())];
                remove_top(st, nb, owner, true, Some(unit.card));
            }
        }
        ("raccoon", OnPlace) => {
            let mut names: Vec<&'static str> = st.pile_cards_of(owner).iter().map(|c| st.cname(*c)).collect();
            names.sort();
            names.dedup();
            push_choose(st, owner, names.into_iter().map(Value::Str).collect(), "pile_to_hand", false, vmap!("from_owner" => pn(owner)));
        }
        ("hammerhead", OnPlace) => {
            if conditional(st, card, unit) {
                let targets: Vec<Cr> = adjacent_tops(st, cr, None)
                    .into_iter()
                    .filter(|(nb, top)| statics::can_be_removed(st, top, Some(*nb), false) && statics::can_be_chosen(st, top, owner, Some(*nb)))
                    .map(|(nb, _)| nb)
                    .collect();
                push_remove_choice(st, owner, unit.card, targets, false);
            }
        }
        ("hyena", OnEndOfTurn) => {
            let removed = lost_this_turn(st, A) + lost_this_turn(st, B);
            let per = cfg(st, "hyena_food_per");
            push_gain(st, owner, per * removed);
        }
        ("city_spider", OnStartOfTurn) => {
            let options: Vec<(Cr, i32)> = adjacent_tops(st, cr, None)
                .into_iter()
                .filter(|(nb, top)| statics::can_be_removed(st, top, Some(*nb), false))
                .map(|(nb, top)| (nb, effective_strength(st, &top, None)))
                .collect();
            if !options.is_empty() {
                let low = options.iter().map(|(_, s)| *s).min().unwrap();
                let lows: Vec<Cr> = options.iter().filter(|(_, s)| *s == low).map(|(nb, _)| *nb).collect();
                let nb = lows[st.rng.choice_index(lows.len())];
                remove_top(st, nb, owner, true, Some(unit.card));
            }
        }
        ("earthworm", OnRemove) => {
            let Args::Remove(rcr, _) = args else { return };
            draw_cards(st, owner, 1);
            let worms = cfg(st, "earthworm_worms");
            let worm = cid(st, "worm");
            for _ in 0..worms {
                let blocked = st.top(*rcr).map(|t| t.owner != owner).unwrap_or(false);
                if blocked || st.result.is_some() {
                    return;
                }
                spawn(st, owner, worm, *rcr);
            }
        }
        ("worm", OnRemove) => {
            draw_cards(st, owner, 1);
        }
        ("cockroach", OnRemove) => {
            let Args::Remove(rcr, pos) = args else { return };
            put_back(st, unit, *rcr, *pos, 0);
            let empty = empty_neighbors(st, *rcr);
            if !empty.is_empty() && st.result.is_none() {
                let spot = empty[st.rng.choice_index(empty.len())];
                let roach = cid(st, "roach");
                spawn(st, owner, roach, spot);
            }
        }
        ("cockroach_legend", OnRemove) => {
            let Args::Remove(rcr, pos) = args else { return };
            let g = cfg(st, "cockroach_legend_growth");
            put_back(st, unit, *rcr, *pos, (unit.strength_counter as i32).max(0) + g);
            draw_cards(st, owner, 1);
        }
        ("dart_frog", OnRemove) => {
            let Args::Remove(rcr, _) = args else { return };
            let targets: Vec<Cr> = adjacent_tops(st, *rcr, None).into_iter().map(|(nb, _)| nb).collect();
            remove_tops(st, unit, targets);
        }
        ("locust_legend", OnPlace) => {
            let locust = cid(st, "locust_swarm");
            let delay = cfg(st, "locust_delay");
            for c in st.map().sorted.clone() {
                let iid = st.new_iid();
                let l = Unit::new(locust, WILD, iid);
                land_unit(st, WILD, l.clone(), c, false, true, false, false);
                let l_now = st.unit_by_iid(iid).cloned().unwrap_or(l);
                schedule(st, &l_now, delay, vmap!("op" => Value::s("locust_eat"), "iid" => Value::Int(iid), "by_player" => pn(owner)), false, None);
            }
        }
        // Canines
        ("wolf_legend_2", OnFriendlyRoam) => {
            if let Args::FriendlyRoam(roamer, _) = args {
                black_wolf_grows(st, owner, roamer);
            }
        }
        ("wolf_legend_2", OnRoam) => black_wolf_grows(st, owner, unit),
        ("wolf_legend", OnEndOfTurn) => {
            let n = adjacent_tops(st, cr, Some(owner)).iter().filter(|(_, t)| st.card(t.card).has_tag(T_CANINE)).count() as i32;
            if n != 0 {
                let g = cfg(st, "wolf_legend_grant");
                grant(st, vec![unit.iid], n * g);
            }
        }
        ("fox", OnPlace) => {
            if conditional(st, card, unit) {
                let n = cfg(st, "fox_draw");
                push_draw(st, owner, n);
            }
        }
        ("dhole", OnCoverEnemy) => {
            if let Some(at) = statics::crossroad_of(st, unit.iid) {
                if lonely(st, owner, at) {
                    let n = cfg(st, "dhole_draw");
                    push_draw(st, owner, n);
                }
            }
        }
        ("wolverine", OnPlace) => {
            let targets: Vec<Cr> = adjacent_enemy_targets(st, unit, cr, None, None, true).into_iter().filter(|nb| lonely(st, owner, *nb)).collect();
            push_remove_choice(st, owner, unit.card, targets, false);
        }
        ("jackal", OnRoam) => {
            // "Roam. Whenever this roams, remove an adjacent enemy weaker than this.": judged where it lands, by its strength then
            if let Args::Roam(to, _) = args {
                let cap = effective_strength(st, unit, None) - 1;
                let targets = adjacent_enemy_targets(st, unit, *to, Some(cap), None, true);
                push_remove_choice(st, owner, unit.card, targets, false);
            }
        }
        ("bush_dog", OnRoam) => {
            if let Args::Roam(_, ev) = args {
                if !st.occupied(ev.from) {
                    let pup = cid(st, "pup");
                    spawn(st, owner, pup, ev.from);
                }
            }
        }
        ("african_wild_dog", OnFriendlyPlace) => {
            // a Canine played next to this roams: played from the hand only, never a token or a placed animal
            if let Args::FriendlyPlace(placed) = args {
                let played = placed.owner <= B && st.turn_flags.played[placed.owner as usize].iter().any(|(i, _)| *i == placed.iid);
                let near = match (statics::crossroad_of(st, placed.iid), statics::crossroad_of(st, unit.iid)) {
                    (Some(a), Some(b)) => st.map().adjacent(a, b),
                    _ => false,
                };
                if played && near && st.card(placed.card).has_tag(T_CANINE) {
                    it_roams(st, placed.iid);
                }
            }
        }
        ("badger", OnPlace) => draws_filtered(st, unit, "keyword:Roam", 1),
        ("coyote", OnPlace) => {
            let o = crs(st, connected_allies(st, owner, cr));
            push_choose(st, owner, o, "coyote", false, Map::default());
        }
        ("street_dog", OnPlace) => {
            let options: Vec<Cr> = connected_allies(st, owner, cr)
                .into_iter()
                .filter(|&c| st.top(c).map(|t| statics::has_keyword(st, t, K_ROAM, Some(c))).unwrap_or(false))
                .collect();
            let o = crs(st, options);
            let g = cfg(st, "street_dog_grant");
            push_choose(st, owner, o, "street_dog", false, vmap!("amount" => Value::Int(g as i64)));
        }
        // Cats
        ("lion_legend", OnPlace) => twin_place(st, unit, "lion_legend_2"),
        ("lion_legend_2", OnPlace) => twin_place(st, unit, "lion_legend"),
        ("lion_legend_4", OnRemoveEvent) => {
            if let Args::RemoveEvent(_, _, ev_owner, by_player, by_card) = args {
                if *by_player == Some(owner) && *ev_owner != owner && by_card.map(|c| st.card(c).has_tag(T_CAT)).unwrap_or(false) && !capped(st, "cap_queen_adira", unit) {
                    draw_cards(st, owner, 1);
                }
            }
        }
        ("jaguar", OnPlace) => removes(st, unit, cr, Some("jaguar_max"), None),
        ("serval", OnPlace) => {
            if conditional(st, card, unit) {
                let t = adjacent_enemy_targets(st, unit, cr, None, None, true);
                push_remove_choice(st, owner, unit.card, t, false);
            }
        }
        ("lynx", OnPlaceOntoEnemy) => {
            let n = cfg(st, "lynx_draw");
            draws(st, unit, n);
        }
        ("bobcat", OnPlace) | ("tutorial_lynx", OnPlace) => {
            if conditional(st, card, unit) {
                draws(st, unit, 1);
            }
        }
        ("ocelot", OnPlace) => {
            if conditional(st, card, unit) {
                push_play_extra(st, owner, Some(vmap!("tags_all" => Value::List(vec![Value::s("Cat")]))), false);
            }
        }
        // Colony
        ("army_ant_legend", OnEndOfTurn) => {
            let per = cfg(st, "army_ant_legend_per");
            let n = control_tag_count(st, owner, 0);
            push_gain(st, owner, per * n);
        }
        ("bee_legend", OnPlace) => {
            // the stack runs last-in first: the Worker is drawn first, as in Python
            draws_filtered(st, unit, "tag:Colony&tag:Nurse", 1);
            draws_filtered(st, unit, "tag:Colony&tag:Soldier", 1);
            draws_filtered(st, unit, "tag:Colony&tag:Worker", 1);
        }
        ("forager_ant", OnPlace) => {
            let n = cfg(st, "forager_ant_food");
            gain_food(st, owner, n, true, false);
            if fed_this_turn(st, owner) {
                let d = cfg(st, "forager_ant_draw");
                push_draw(st, owner, d);
            }
        }
        ("queen_ant", OnEndOfTurn) => spawns_beside(st, unit, cr, "young_ant"),
        ("scout_bee", OnEndOfTurn) => {
            if food_gained_this_turn(st, owner) >= cfg(st, "scout_bee_threshold") {
                let d = cfg(st, "scout_bee_draw");
                push_draw(st, owner, d);
            }
        }
        ("nurse_bee", OnPlace) => {
            if conditional(st, card, unit) {
                let n = cfg(st, "nurse_bee_draw");
                draws(st, unit, n);
            }
        }
        ("nurse_bumblebee", OnPlace) => draws_filtered(st, unit, "tag:Colony", 1),
        ("termite_king", OnPlace) => {
            let n = control_tag_count(st, owner, T_COLONY | T_QUEEN);
            if n > 0 {
                push_draw(st, owner, n);
            }
        }
        ("termite_queen", OnPlace) => push_play_extra(st, owner, Some(vmap!("tags_all" => Value::List(vec![Value::s("Colony")]), "tags_none" => Value::List(vec![Value::s("Queen")]))), false),
        ("queen_bee", OnPlace) => {
            // Roar: add a Worker Bee, Soldier Bee or Nurse Bee to your hand, made out of thin air; the owner picks
            let options = ["worker_bee", "guard_bee", "nurse_bee"].into_iter().map(Value::s).collect();
            push_choose(st, owner, options, "make_in_hand", false, Map::new());
        }
        ("soldier_ant", OnPlace) | ("gopher", OnPlace) => {
            if conditional(st, card, unit) {
                removes(st, unit, cr, None, None);
            }
        }
        ("worker_ant", OnPlace) => {
            let per = cfg(st, "worker_ant_per");
            let n = control_tag_count(st, owner, 0);
            push_gain(st, owner, per * n);
        }
        ("worker_wasp", OnFriendlyPlace) => {
            if let Args::FriendlyPlace(placed) = args {
                if st.card(placed.card).has_tag(T_COLONY) {
                    let n = cfg(st, "worker_wasp_per_place");
                    gain_food(st, placed.owner, n, true, false);
                }
            }
        }
        ("worker_bee", OnPlace) => gains(st, unit, "worker_bee_food"),
        // Den Rush
        ("mole_legend", OnPlace) => mole_legend(st, unit),
        ("rat_legend_2", OnPlace) => {
            let mut options = adjacent_enemy_unit_crossroads(st, unit, cr, true);
            options.extend(adjacent_friendly_units(st, unit, cr));
            options.sort_by(|a, b| st.crname(*a).cmp(st.crname(*b)));
            if !options.is_empty() {
                let o = crs(st, options);
                st.effect_stack.push(vmap!("op" => Value::s("rat_legend_2_wipe"), "chooser" => pn(owner), "options" => Value::List(o)));
            }
        }
        ("skunk_legend", OnPlace) => {
            for nb in adjacent_enemy_unit_crossroads(st, unit, cr, false) {
                let iid = st.top(nb).unwrap().iid;
                st.effect_stack.push(vmap!("op" => Value::s("bounce_iid"), "iid" => Value::Int(iid)));
            }
        }
        ("falcon_legend", OnPlace) => {
            let n = st.map().front(other(owner)).iter().filter(|&&c| st.top(c).map(|t| t.owner == owner).unwrap_or(false)).count() as i32;
            push_draw(st, owner, n);
        }
        ("mole", OnPlace) | ("naked_mole_rat", OnPlace) => mole(st, unit, cr),
        ("hornet", OnPlace) => {
            let targets = adjacent_enemy_targets(st, unit, cr, None, None, true);
            let hornet = cid(st, "hornet");
            if !targets.is_empty() && has_spare_copy(st, owner, hornet) {
                let o = crs(st, targets);
                st.effect_stack.push(vmap!("op" => Value::s("hornet_kill"), "chooser" => pn(owner), "options" => Value::List(o)));
            }
        }
        ("skunk", OnPlace) => {
            let options = adjacent_enemy_unit_crossroads(st, unit, cr, true);
            if !options.is_empty() {
                let o = crs(st, options);
                st.effect_stack.push(vmap!("op" => Value::s("skunk_bounce"), "chooser" => pn(owner), "options" => Value::List(o)));
            }
        }
        ("hare", OnPlace) => {
            if conditional(st, card, unit) {
                let n = cfg(st, "hare_draw");
                draws(st, unit, n);
            }
        }
        ("alley_cat", OnPlace) => {
            let c = cid(st, "kitten");
            for _ in 0..cfg(st, "alley_cat_kittens") {
                gain_to_hand(st, owner, c, 0);
            }
        }
        ("kitten", OnPlace) => {
            let n = cfg(st, "kitten_draw");
            draws_filtered(st, unit, "rarity:common", n);
        }
        ("falcon", OnPlace) => hq_adjacent_draw(st, unit, cr, 1),
        ("cheetah", OnPlace) => { let n = cfg(st, "cheetah_draw"); hq_adjacent_draw(st, unit, cr, n) }
        ("rat", OnPlace) => {
            if conditional(st, card, unit) {
                let t = adjacent_enemy_targets(st, unit, cr, None, None, true);
                let rat = cid(st, "rat");
                push_remove_choice(st, owner, rat, t, false);
            }
        }
        ("bat", OnPlace) | ("dolphin", OnPlace) => draws(st, unit, 1),
        ("mouse", OnPlace) => draws_filtered(st, unit, "tag:Rodent", 1),
        // Egg Control
        ("anaconda_legend", OnEndOfTurn) => {
            let me = cid(st, "anaconda_legend");
            let decay = cfg(st, "anaconda_legend_decay");
            let counter = st.growth(owner, me);
            if base_int(st, me) + counter - decay <= 0 {
                remove_specific(st, cr, unit.iid, owner, true, Some(me), false);
                return;
            }
            crate::emit!(st, "to_deck", vmap!("cr" => cr_v(st, cr), "iid" => Value::Int(unit.iid), "card" => card_v(st, unit.card), "owner" => pn(owner)));
            st.take_unit(cr, unit.iid);
            *st.card_strength_counters[owner as usize].entry(me).or_insert(0) -= decay;
            crate::emit!(st, "strength", vmap!("card" => Value::s("anaconda_legend"), "owner" => pn(owner), "n" => Value::Int(-(decay as i64))));
            shuffle_back(st, owner, &[me], None);
            push_draw(st, owner, 1);
        }
        ("raven_legend", OnPlace) => {
            let n = cfg(st, "raven_legend_steals");
            st.effect_stack.push(vmap!("op" => Value::s("steal_from_pile"), "player" => pn(owner), "n" => Value::Int(n as i64)));
        }
        ("goose_legend", OnStartOfTurn) => {
            let egg = cid(st, "golden_egg");
            let n = cfg(st, "aurum_eggs") as usize;
            shuffle_back(st, owner, &vec![egg; n], Some(owner));
        }
        ("bat_legend", OnStartOfTurn) => push_draw(st, owner, 1),
        ("swan_legend", OnDraw) => {
            let opp = other(owner);
            if !st.hands[opp as usize].is_empty() {
                let i = st.rng.choice_index(st.hands[opp as usize].len());
                let iid = st.hands[opp as usize][i].iid;
                remove_from_hand(st, opp, iid);
            }
        }
        ("hawk", OnPlace) => removes(st, unit, cr, Some("stoop_max"), None),
        ("cottonmouth", OnPlace) => {
            let targets = adjacent_enemy_targets(st, unit, cr, None, None, true);
            if !targets.is_empty() {
                let o = crs(st, targets);
                st.effect_stack.push(vmap!("op" => Value::s("venom"), "chooser" => pn(owner), "options" => Value::List(o)));
            }
        }
        ("magpie", OnPlace) => st.effect_stack.push(vmap!("op" => Value::s("magpie_steal"), "player" => pn(owner))),
        ("black_mamba", OnPlace) => removes(st, unit, cr, Some("black_mamba_max"), None),
        ("mosquito", OnPlace) => {
            let n = cfg(st, "mosquito_drain");
            drain_place(st, unit, cr, n);
        }
        ("viper", OnPlace) => {
            let n = cfg(st, "viper_poison");
            drain_place(st, unit, cr, n);
        }
        ("raven", OnPlace) => st.effect_stack.push(vmap!("op" => Value::s("raven_dig"), "player" => pn(owner))),
        ("owl", OnPlace) => st.effect_stack.push(vmap!("op" => Value::s("scout"), "player" => pn(owner), "spec" => Value::Null)),
        ("bird_egg", OnPlace) => {
            st.effect_stack.push(vmap!("op" => Value::s("scout"), "player" => pn(owner), "spec" => Value::s("tag:Bird")));
            let d = cfg(st, "bird_egg_hatch_delay");
            schedule(st, unit, d, vmap!("op" => Value::s("bird_egg_hatch"), "iid" => Value::Int(unit.iid)), false, None);
        }
        ("snake_egg", OnPlace) => {
            let n = cfg(st, "snake_egg_draw");
            st.effect_stack.push(vmap!("op" => Value::s("draw_filtered"), "player" => pn(owner), "n" => Value::Int(n as i64), "spec" => Value::s("tag:Snake")));
            let d = cfg(st, "egg_hatch_delay");
            let hn = cfg(st, "egg_hatch_draw");
            schedule(st, unit, d, vmap!("op" => Value::s("egg_hatch"), "iid" => Value::Int(unit.iid), "n" => Value::Int(hn as i64), "spec" => Value::s("tag:Snake")), false, None);
        }
        // Fish
        ("tuna_legend", OnPlace) => {
            let n = statics::regions_of(st, owner).len() as i32;
            let f = cfg(st, "tuna_legend_food");
            push_gain(st, owner, n * f);
            push_draw(st, owner, n);
        }
        ("manta_ray_legend", OnEndOfTurn) => {
            if statics::regions_of(st, owner).len() as i32 >= cfg(st, "manta_legend_regions") {
                let d = cfg(st, "manta_legend_draw");
                push_draw(st, owner, d);
            }
        }
        ("swordfish", OnPlace) => {
            let n = adjacent_ally_fish(st, unit, cr) as usize;
            let mut targets = adjacent_enemy_targets(st, unit, cr, None, None, false);
            st.rng.shuffle(&mut targets);
            for nb in targets.into_iter().take(n) {
                let iid = st.top(nb).unwrap().iid;
                let step = remove_iid_step(st, iid, owner, true, None, Some(unit.card));
                st.effect_stack.push(step);
            }
        }
        ("barracuda", OnPlace) => {
            let max = control_tag_count(st, owner, T_FISH) * statics::fish_worth(st, owner);
            let t = adjacent_enemy_targets(st, unit, cr, Some(max), None, true);
            push_remove_choice(st, owner, unit.card, t, false);
        }
        ("piranha_legend", OnPlace) => {
            let need = cfg(st, "piranha_legend_fish");
            let prey: Vec<(Cr, i64)> = st.tops().filter(|(_, u)| u.owner != owner).map(|(c, u)| (c, u.iid)).collect();
            for (at, iid) in prey {
                if adjacent_ally_fish(st, unit, at) >= need {
                    let step = remove_iid_step(st, iid, owner, true, None, Some(unit.card));
                    st.effect_stack.push(step);
                }
            }
        }
        ("manta_ray", OnAllyCovered) => {
            if let Args::AllyCovered(covered, coverer, ccr) = args {
                let at = statics::crossroad_of(st, unit.iid);
                if coverer.owner != owner && st.card(covered.card).has_tag(T_FISH) && at.map(|a| st.map().adjacent(a, *ccr)).unwrap_or(false) {
                    push_draw(st, owner, 1);
                }
            }
        }
        ("remora", OnPlace) => {
            if adjacent_ally_fish(st, unit, cr) >= 1 {
                push_play_extra(st, owner, Some(vmap!("tags_all" => Value::List(vec![Value::s("Fish")]))), false);
            }
        }
        ("cod", OnPlace) => {
            let n = adjacent_ally_fish(st, unit, cr);
            push_draw(st, owner, n);
        }
        ("sardine", OnPlace) => fill(st, unit, cr),
        ("sunfish", OnPlace) => spawns_beside(st, unit, cr, "baby_fish"),
        ("deer", OnPlace) => spawns_beside(st, unit, cr, "fawn"),
        // Food Aggro
        ("hamster", OnDrawEvent) => {
            // "Whenever you draw a card, gain 5 food." (Martin, 2026-10-29): your draws only, each card once.
            if let Args::CardEvent(_, _, player) = args {
                if *player == owner {
                    let f = cfg(st, "hamster_draw_food");
                    push_gain(st, owner, f);
                }
            }
        }
        ("vole", OnPlace) => {
            // "Roar: repeat the Roar of an adjacent Rodent." (Martin, 2026-10-29): one Rodent neighbour with a Roar, the
            // owner's choice, repeated as the Vole's own; never a repeater (the legend, another Vole), or two would go for ever.
            let (gus, vole) = (st.card_id("capybara_legend"), st.card_id("vole"));
            let o: Vec<Cr> = adjacent_tops(st, cr, Some(owner))
                .into_iter()
                .filter(|(_, top)| st.card(top.card).has_tag(T_RODENT) && top.card != unit.card && Some(top.card) != gus && Some(top.card) != vole && st.g.has_hook(top.card, OnPlace))
                .map(|(nb, _)| nb)
                .collect();
            push_choose(st, owner, crs(st, o), "repeat_roar", false, vmap!("vole" => Value::Int(unit.iid)));
        }
        ("capybara_legend", OnPlace) => {
            // each repeat is Big Gus's own, at its crossroad (as the Macaw's copy is the Macaw's); repeaters (the Vole, another
            // of these) are never repeated, or two side by side would go for ever
            let vole = st.card_id("vole");
            for (_nb, top) in adjacent_tops(st, cr, Some(owner)).into_iter().rev() {
                if st.card(top.card).has_tag(T_RODENT) && top.card != unit.card && Some(top.card) != vole && st.g.has_hook(top.card, OnPlace) {
                    run(st, top.card, Some(unit.card), OnPlace, unit, &Args::Place(cr));
                }
            }
        }
        ("macaque_legend", OnPlace) => st.effect_stack.push(vmap!("op" => Value::s("draw_to_match"), "player" => pn(owner))),
        ("rat_legend", OnPlace) => {
            let others = control_tag_count(st, owner, T_RODENT) - 1;
            push_draw(st, owner, 1);
            let per = cfg(st, "rat_king_per_rodent");
            push_gain(st, owner, per * others.max(0));
        }
        ("chipmunk_legend", OnPlace) => {
            let per = cfg(st, "chipmunk_legend_food_per");
            let step = cfg(st, "chipmunk_legend_food_step");
            let n = per * (st.food[owner as usize] / step);
            push_gain(st, owner, n);
        }
        ("flying_squirrel", OnPlace) => {
            push_draw(st, owner, 1);
            gains(st, unit, "flying_squirrel_food");
        }
        ("meerkat", OnPlace) => draws(st, unit, 1),
        ("meerkat", OnEnemyPlacedAdjacent) => push_draw(st, owner, 1),
        ("beaver", OnPlace) => {
            let n = cfg(st, "beaver_bonus_actions");
            schedule(st, unit, 1, vmap!("op" => Value::s("grant_action"), "player" => pn(owner), "n" => Value::Int(n as i64)), false, None);
        }
        ("krill", OnPlace) => {
            st.turn_flags.titan_discount[owner.min(1) as usize] = true;
            push_draw(st, owner, 1);
        }
        ("electric_eel", OnPlace) => {
            let opp = other(owner);
            let n = cfg(st, "eel_actions");
            schedule(st, unit, 1, vmap!("op" => Value::s("cap_actions"), "player" => pn(opp), "n" => Value::Int(n as i64)), true, Some(opp));
        }
        ("dormouse", OnEndOfTurn) => {
            let n = food_gained_this_turn(st, owner) / cfg(st, "fed_threshold");
            if n > 0 {
                push_draw(st, owner, n);
            }
        }
        ("squirrel", OnPlace) => gains(st, unit, "squirrel_food"),
        ("chipmunk", OnPlace) | ("tutorial_chipmunk", OnPlace) => chipmunk(st, unit),
        ("mara", OnPlace) => {
            if conditional(st, card, unit) {
                let n = cfg(st, "mara_draw");
                draws(st, unit, n);
            }
        }
        ("groundhog", OnStartOfTurn) => gains(st, unit, "groundhog_food"),
        ("rodent_legend", OnPlace) => {
            let n = food_gained_this_turn(st, owner);
            push_gain(st, owner, n);
        }
        // Food OTK
        ("octopus_legend_2", OnPlace) => st.effect_stack.push(vmap!("op" => Value::s("scout"), "player" => pn(owner), "spec" => Value::s("rarity:legendary"))),
        ("squirrel_legend", OnPlace) => {
            let stake = st.food[owner as usize];
            lose_food(st, owner, stake, Some(unit.card));
            if stake != 0 {
                let d = cfg(st, "otk_squirrel_delay");
                let m = cfg(st, "otk_squirrel_multiplier");
                schedule(st, unit, d, vmap!("op" => Value::s("gain_food"), "player" => pn(owner), "amount" => Value::Int((stake * m) as i64)), false, None);
            }
        }
        ("chameleon_legend", OnPlace) => {
            let options: Vec<Cr> = adjacent_tops(st, cr, None).into_iter().filter(|(nb, top)| statics::can_be_chosen(st, top, owner, Some(*nb))).map(|(nb, _)| nb).collect();
            let o = crs(st, options);
            push_choose(st, owner, o, "copy_and_add", false, vmap!("self" => Value::Int(unit.iid)));
        }
        ("chameleon", OnPlace) => {
            let o: Vec<Value> = hand_iids(st, owner, 0).into_iter().map(Value::Int).collect();
            push_choose(st, owner, o, "copy_from_hand", false, vmap!("self" => Value::Int(unit.iid)));
        }
        ("golden_orb_weaver", OnEnemyPlacedAdjacent) => {
            if let Args::PlacedAdjacent(placed, pcr) = args {
                if (statics::has_keyword(st, placed, K_FLIGHT, Some(*pcr)) || statics::has_keyword(st, placed, K_ROAM, Some(*pcr))) && statics::can_be_removed(st, placed, Some(*pcr), false) {
                    let step = remove_iid_step(st, placed.iid, owner, true, None, Some(unit.card));
                    st.effect_stack.push(step);
                }
            }
        }
        ("black_bear", OnPlace) => {
            let d = cfg(st, "black_bear_delay");
            let n = cfg(st, "black_bear_draw");
            schedule(st, unit, d, vmap!("op" => Value::s("draw"), "player" => pn(owner), "n" => Value::Int(n as i64)), false, None);
        }
        ("grizzly_bear", OnPlace) => push_draw(st, other(owner), 1),
        ("stag_beetle", OnPlace) => {
            let n = st.tops().filter(|(c, t)| t.owner == owner && statics::has_keyword(st, t, K_ARMOR, Some(*c))).count() as i32;
            let per = cfg(st, "stag_beetle_per_armor");
            push_gain(st, owner, n * per);
        }
        // Giants
        ("sperm_whale", OnPlace) => remove_all_adjacent(st, unit, cr),
        ("rhinoceros_legend", OnPlace) => removes(st, unit, cr, None, None),
        ("tortoise_legend", OnEndOfTurn) => gains(st, unit, "tortoise_legend_food"),
        ("rhinoceros", OnPlace) => sweep(st, unit, cr, "rhinoceros_max"),
        ("albatross", OnPlace) => sweep(st, unit, cr, "albatross_max"),
        ("elephant_legend", OnPlace) => sweep(st, unit, cr, "elephant_legend_max"),
        ("elephant_legend", OnRoam) => {
            if let Args::Roam(to, _) = args {
                sweep(st, unit, *to, "elephant_legend_max");
            }
        }
        ("hippopotamus", OnEnemyPlacedAdjacent) => {
            if let Args::PlacedAdjacent(placed, pcr) = args {
                if effective_strength(st, placed, None) <= cfg(st, "hippopotamus_max") && statics::can_be_removed(st, placed, Some(*pcr), false) {
                    let step = remove_iid_step(st, placed.iid, owner, true, None, Some(unit.card));
                    st.effect_stack.push(step);
                }
            }
        }
        ("whale_shark", OnEndOfTurn) => draws(st, unit, 1),
        ("dung_beetle_legend_form2", OnPlace) | ("dung_beetle_legend_form3", OnPlace) | ("dung_beetle_legend_form4", OnPlace) => {
            // the legendary Dung Beetle's later forms; pushed last-first so the draw resolves first, as in Python
            let name = st.cname(unit.card);
            let form = if name.ends_with("form4") { 4 } else if name.ends_with("form3") { 3 } else { 2 };
            if form >= 4 {
                push_play_extra(st, owner, None, false);
            }
            if form >= 3 {
                removes(st, unit, cr, None, None);
            }
            push_draw(st, owner, 1);
        }
        ("oxpecker", OnPlace) => st.effect_stack.push(vmap!("op" => Value::s("oxpecker"), "player" => pn(owner))),
        ("anteater", OnPlace) => st.effect_stack.push(vmap!("op" => Value::s("anteater"), "player" => pn(owner))),
        ("dung_beetle", OnEndOfTurn) => {
            let n = st.tops().filter(|(c, t)| t.owner == owner && statics::has_keyword(st, t, K_HUNGRY, Some(*c))).count() as i32;
            let per = cfg(st, "dung_beetle_per");
            push_gain(st, owner, n * per);
        }
        ("sloth", OnPlace) => {
            let d = cfg(st, "sloth_delay");
            let f = cfg(st, "sloth_food");
            schedule(st, unit, d, vmap!("op" => Value::s("gain_food"), "player" => pn(owner), "amount" => Value::Int(f as i64)), false, None);
        }
        // Handlock
        ("baboon_legend", OnStartOfTurn) => {
            let hand = hand_iids(st, owner, 0);
            let k = hand.len().min(cfg(st, "baboon_legend_count") as usize);
            let picks: Vec<i64> = st.rng.sample_indexes(hand.len(), k).into_iter().map(|i| hand[i]).collect();
            let g = cfg(st, "baboon_legend_grant");
            grant(st, picks, g);
        }
        ("gorilla_legend", OnPlace) => {
            let iids = hand_iids(st, owner, 0);
            let g = cfg(st, "gorilla_legend_grant");
            grant(st, iids, g);
        }
        ("bee_legend_2", OnPlace) => {
            let p = owner as usize;
            let mut distinct: Vec<CardId> = Vec::new();
            for c in &st.decks[p] {
                if !distinct.contains(c) {
                    distinct.push(*c);
                }
            }
            st.jelly[p].clear();
            st.jelly_set[p] = true;
            for c in distinct {
                let n = st.decks[p].iter().filter(|x| **x == c).count() as i32;
                let counter = st.jelly_counter(owner, c);
                st.jelly[p].insert(c, (n, counter));
            }
            let mut mine: Vec<Unit> = st.order.iter().flat_map(|&c| st.stacks[c as usize].iter().filter(|u| u.owner == owner).cloned()).collect();
            mine.extend(st.hands[p].iter().cloned());
            for inst in mine {
                let d = st.jelly_counter(owner, inst.card) - inst.strength_counter as i32;
                grant(st, vec![inst.iid], d);
            }
        }
        ("butterfly_legend", OnDawnInHand) | ("butterfly_legend", OnStartOfTurn) | ("butterfly_legend", OnGain)
        | ("butterfly_legend_caterpillar", OnDawnInHand) | ("butterfly_legend_caterpillar", OnStartOfTurn) | ("butterfly_legend_caterpillar", OnGain)
        | ("butterfly_legend_chrysalis", OnDawnInHand) | ("butterfly_legend_chrysalis", OnStartOfTurn) | ("butterfly_legend_chrysalis", OnGain)
        | ("butterfly_legend_butterfly", OnDawnInHand) | ("butterfly_legend_butterfly", OnStartOfTurn) | ("butterfly_legend_butterfly", OnGain) => butterfly_evolve(st, unit),
        ("butterfly_legend_caterpillar", OnPlace) => draws(st, unit, 1),
        ("butterfly_legend_chrysalis", OnPlace) | ("butterfly", OnPlace) => draw_then_give_one(st, unit),
        ("butterfly_legend_butterfly", OnPlace) => butterfly_stage_place(st, unit, None, "butterfly_legend_stage4_grant"),
        ("butterfly_legend_monarch", OnPlace) => butterfly_stage_place(st, unit, Some("butterfly_legend_stage5_draw"), "butterfly_legend_stage5_grant"),
        ("hummingbird", OnPlace) => {
            let n = cfg(st, "hummingbird_draw");
            draws(st, unit, n);
        }
        ("macaque", OnPlace) => {
            if conditional(st, card, unit) {
                let t = adjacent_enemy_targets(st, unit, cr, None, None, true);
                push_remove_choice(st, owner, unit.card, t, false);
            }
        }
        ("orangutan", OnPlace) => {
            let o: Vec<Value> = hand_iids(st, owner, T_PRIMATE).into_iter().map(Value::Int).collect();
            push_choose(st, owner, o, "duplicate", false, Map::default());
        }
        ("tarsier", OnPlace) => {
            let g = cfg(st, "tarsier_grant");
            st.effect_stack.push(vmap!("op" => Value::s("hand_grant_one"), "player" => pn(owner), "amount" => Value::Int(g as i64), "tag" => Value::s("Primate")));
            st.effect_stack.push(vmap!("op" => Value::s("draw_filtered"), "player" => pn(owner), "n" => Value::Int(1), "spec" => Value::s("tag:Primate")));
        }
        ("chimpanzee", OnPlace) => {
            let s = effective_strength(st, unit, None);
            let t = adjacent_enemy_targets(st, unit, cr, Some(s), None, true);
            push_remove_choice(st, owner, unit.card, t, false);
        }
        ("baboon", OnPlace) => {
            let hand = hand_iids(st, owner, 0);
            let count = cfg(st, "baboon_count");
            let g = cfg(st, "baboon_grant");
            if hand.len() as i32 <= count {
                grant(st, hand, g);
            } else {
                push_choose(st, owner, hand.into_iter().map(Value::Int).collect(), "hand_grant", false, vmap!("amount" => Value::Int(g as i64), "count" => Value::Int(count as i64)));
            }
        }
        ("stork", OnPlace) => {
            const YOUNGLINGS: [&str; 8] = ["baby_lion", "baby_wolf", "baby_squirrel", "baby_owl", "baby_python", "baby_bear", "baby_gorilla", "baby_zebra"];
            let k = cfg(st, "stork_younglings") as usize;
            for i in st.rng.sample_indexes(YOUNGLINGS.len(), k) {
                let c = cid(st, YOUNGLINGS[i]);
                gain_to_hand(st, owner, c, 0);
            }
        }
        ("caterpillar", OnGainInHand) => {
            let b = cid(st, "butterfly");
            transform(st, unit.iid, b);
            draw_cards(st, owner, 1);
        }
        ("gorilla", OnPlace) => {
            if conditional(st, card, unit) {
                push_draw(st, owner, 1);
            }
        }
        // Hoofed
        ("zebra_legend", OnPlace) => {
            let mut kinds: Vec<CardId> = Vec::new();
            for (_, t) in st.tops() {
                if t.owner == owner && t.iid != unit.iid && st.card(t.card).has_tag(T_HOOFED) && !kinds.contains(&t.card) {
                    kinds.push(t.card);
                }
            }
            push_draw(st, owner, kinds.len() as i32);
        }
        ("honey_badger", OnPlace) => removes(st, unit, cr, None, Some("honey_badger_min")),
        ("okapi", OnStartOfTurn) | ("okapi", OnEndOfTurn) | ("baby_impala", OnPlace) => {
            // Okapi: "Dawn and Dusk: if this is grazing, draw a card." Baby Impala: "Flee. Roar: if this is grazing, draw a card."
            if statics::grazing(st, unit, Some(cr)) {
                push_draw(st, owner, 1);
            }
        }
        ("zebra", OnFlee) => {
            // "Flee. When this flees, return the enemy that covered it to its owner's hand." (Martin, 2026-10-29: the kick, back)
            if let Args::Flee(coverer) = args {
                st.effect_stack.push(vmap!("op" => Value::s("flee_return"), "iid" => Value::Int(*coverer)));
            }
        }
        ("deer_legend", OnPlace) => {
            let n = cfg(st, "deer_legend_draw");
            draws_filtered(st, unit, "keyword:Flee", n);
        }
        ("deer_legend", OnFriendlyFlee) => {
            // "Whenever one of your animals flees, it gains 2 strength": the fled card, now in hand.
            if let Args::FriendlyFlee(fled) = args {
                let g = cfg(st, "deer_legend_grant");
                grant(st, vec![fled.iid], g);
            }
        }
        ("deer_legend", OnFlee) => {
            // The legendary Deer fleeing grows itself (`unit` is its hand instance here).
            let g = cfg(st, "deer_legend_grant");
            grant(st, vec![unit.iid], g);
        }
        ("rabbit", OnPlace) => {
            // "Roar: play a Bunny next to this.": made and played on a neighbouring crossroad of the owner's choice.
            st.effect_stack.push(vmap!("op" => Value::s("play_named"), "chooser" => pn(owner), "card_id" => Value::s("bunny"), "make" => Value::Bool(true), "adjacent_to" => cr_v(st, cr)));
        }
        ("impala", OnPlace) => {
            // "Flee. Roar: play a Baby Impala.": made and played at once, a full placement with its Roar.
            st.effect_stack.push(vmap!("op" => Value::s("play_named"), "chooser" => pn(owner), "card_id" => Value::s("baby_impala"), "make" => Value::Bool(true)));
        }
        ("warthog", OnPlace) => {
            // "Roar: remove an adjacent enemy that has another of your Hoofed animals next to it.": the herd mobs the intruder
            let t: Vec<Cr> = adjacent_enemy_targets(st, unit, cr, None, None, true)
                .into_iter()
                .filter(|nb| adjacent_tops(st, *nb, Some(owner)).iter().any(|(_, t)| t.iid != unit.iid && st.card(t.card).has_tag(T_HOOFED)))
                .collect();
            push_remove_choice(st, owner, unit.card, t, false);
        }
        ("boar", OnPlace) => {
            let t: Vec<Cr> = adjacent_enemy_targets(st, unit, cr, None, None, true).into_iter().filter(|nb| st.stack(*nb).len() == 1).collect();
            push_remove_choice(st, owner, unit.card, t, false);
        }
        ("gazelle", OnPlace) => {
            let f = cfg(st, "gazelle_food");
            push_gain(st, owner, f);
            push_draw(st, owner, 1);
        }
        ("wildebeest", OnEndOfTurn) => {
            if statics::grazing(st, unit, Some(cr)) {
                let f = cfg(st, "wildebeest_food");
                push_gain(st, owner, f);
            }
        }
        // The pool
        ("octopus", OnPlace) => {
            for nb in st.map().neighbors(cr).to_vec() {
                if let Some(top) = st.top(nb).cloned() {
                    if top.owner != owner && !st.inked.contains(&top.iid) {
                        st.inked.insert(top.iid);
                        crate::emit!(st, "inked", vmap!("iid" => Value::Int(top.iid), "card" => card_v(st, top.card), "owner" => pn(top.owner)));
                    }
                }
            }
        }
        ("macaw", OnPlace) => {
            if owner > B {
                return;
            }
            let copied = st.last_roar[other(owner) as usize];
            if let Some(c) = copied {
                if st.g.has_hook(c, OnPlace) {
                    st.last_roar[owner as usize] = Some(c);
                    let macaw = st.g.known.macaw;
                    run(st, c, macaw, OnPlace, unit, &Args::Place(cr));
                }
            }
        }
        ("woodpecker", OnPlace) => {
            if owner <= B {
                st.roar_twice[owner as usize] = Some(st.turn_counter);
            }
        }
        ("cuckoo", OnPlace) => {
            let egg = cid(st, "cuckoo_egg");
            let n = cfg(st, "cuckoo_eggs") as usize;
            shuffle_back(st, other(owner), &vec![egg; n], Some(owner));
        }
        ("cuckoo_egg", OnDraw) => {
            draw_cards(st, other(owner), 1);
        }
        ("golden_egg", OnDraw) => {
            if st.hands[owner as usize].iter().any(|u| u.iid == unit.iid) {
                remove_from_hand(st, owner, unit.iid);
            }
            let n = cfg(st, "golden_egg_draw");
            draw_cards(st, owner, n);
        }
        ("opossum", OnPlace) => {
            let o = crs(st, adjacent_friendly_units(st, unit, cr));
            push_choose(st, owner, o, "return_ally", false, Map::default());
        }
        ("fox_legend", OnPlace) => {
            let n = cfg(st, "alpha_pups");
            spawn_pups(st, unit, cr, n, &["baby_fox", "baby_fox_2"]);
        }
        ("andean_condor", OnPlace) => {
            let o = owner as usize;
            let Some(&mine_top) = st.decks[o].last() else { return };
            let their_str = st.decks[other(owner) as usize].last().map(|c| base_int(st, *c)).unwrap_or(0);
            if base_int(st, mine_top) > their_str {
                push_draw(st, owner, 1);
            }
        }
        ("dingo", OnEndOfTurn) => {
            let iids: Vec<i64> = adjacent_tops(st, cr, Some(owner)).iter().filter(|(_, t)| st.card(t.card).has_tag(T_CANINE)).map(|(_, t)| t.iid).collect();
            let g = cfg(st, "dingo_grant");
            grant(st, iids, g);
        }
        _ => {}
    }
}

// ============================================================== THEN: what a choice does

pub fn then(st: &mut State, name: &str, step: &Map, choice: &Value) {
    let chooser = player_from(m_get_s(step, "chooser").unwrap_or("A"));
    let by_card = m_get_s(step, "by_card").and_then(|n| st.card_id(n));
    let cr_of = |st: &State| choice.as_str().and_then(|s| st.map().cr(s));
    match name {
        "remove" => {
            if let Some(cr) = cr_of(st) {
                remove_top(st, cr, chooser, true, by_card);
            }
        }
        "set_strength" => {
            if let Some(cr) = cr_of(st) {
                if let Some(top) = st.top(cr).cloned() {
                    let delta = cfg(st, "serval_set") - effective_strength(st, &top, None);
                    add_strength(st, top.iid, delta);
                }
            }
        }
        "drain" => {
            if let Some(cr) = cr_of(st) {
                if let Some(top) = st.top(cr).cloned() {
                    let amount = m_get_i(step, "amount").unwrap_or(0) as i32;
                    add_strength(st, top.iid, -amount);
                }
            }
        }
        "grant" => {
            let iid = match choice {
                Value::Str(s) => st.map().cr(s).and_then(|c| st.top(c)).map(|t| t.iid),
                Value::Int(i) => st.find_instance(*i).map(|u| u.iid),
                _ => None,
            };
            if let Some(iid) = iid {
                grant(st, vec![iid], m_get_i(step, "amount").unwrap_or(0) as i32);
            }
        }
        "hand_grant" => {
            let iid = choice.as_i64().unwrap_or(-1);
            let mut picked: Vec<Value> = step.get("picked").and_then(|p| p.as_list()).cloned().unwrap_or_default();
            picked.push(Value::Int(iid));
            let count = m_get_i(step, "count").unwrap_or(0);
            let amount = m_get_i(step, "amount").unwrap_or(0);
            let left = count - picked.len() as i64;
            let rest: Vec<Value> = hand_iids(st, chooser, 0).into_iter().filter(|i| !picked.iter().any(|p| p.as_i64() == Some(*i))).map(Value::Int).collect();
            if left > 0 && !rest.is_empty() {
                let mut args = vmap!("amount" => Value::Int(amount), "count" => Value::Int(count), "picked" => Value::List(picked));
                if let Some(bc) = step.get("by_card") {
                    args.insert("by_card".into(), bc.clone());
                }
                push_choose(st, chooser, rest, "hand_grant", false, args);
            }
            grant(st, vec![iid], amount as i32);
        }
        "coyote" => {
            if let Some(cr) = cr_of(st) {
                let iid = match st.top_mut(cr) {
                    Some(top) => {
                        top.granted_roam = true;
                        top.iid
                    }
                    None => return,
                };
                it_roams(st, iid);
            }
        }
        "street_dog" => {
            if let Some(cr) = cr_of(st) {
                let Some(top) = st.top(cr).cloned() else { return };
                it_roams(st, top.iid);   // pushed first, so the +3 lands before it moves
                grant(st, vec![top.iid], m_get_i(step, "amount").unwrap_or(0) as i32);
            }
        }
        "copy_and_add" => {
            let me_iid = m_get_i(step, "self").unwrap_or(-1);
            let Some(cr) = cr_of(st) else { return };
            let Some(target) = st.top(cr).cloned() else { return };
            become_copy(st, me_iid, target.card, target.strength_counter);
            if st.find_unit(me_iid).is_some() {
                copy_timers(st, &target, me_iid, chooser);
            }
            gain_to_hand(st, chooser, target.card, 0);
        }
        "copy_from_hand" => {
            let me_iid = m_get_i(step, "self").unwrap_or(-1);
            let iid = choice.as_i64().unwrap_or(-1);
            if let Some(inst) = st.hands[chooser as usize].iter().find(|u| u.iid == iid).cloned() {
                become_copy(st, me_iid, inst.card, inst.strength_counter);
            }
        }
        "return_ally" => {
            if let Some(cr) = cr_of(st) {
                if let Some(top) = st.top(cr).cloned() {
                    if top.owner == chooser && statics::can_be_removed(st, &top, Some(cr), false) {
                        bounce(st, cr, &top, 0);
                    }
                }
            }
        }
        "cuckoo" => {
            if let Some(cr) = cr_of(st) {
                let Some(top) = st.top(cr).cloned() else { return };
                if top.owner == chooser {
                    push_play_extra(st, chooser, None, false);
                }
                remove_top(st, cr, chooser, true, by_card);
            }
        }
        "remove_and_draw" => {
            if let Some(cr) = cr_of(st) {
                if remove_top(st, cr, chooser, true, by_card) {
                    draw_cards(st, chooser, m_get_i(step, "n").unwrap_or(0) as i32);
                }
            }
        }
        "repeat_roar" => {
            // Vole: the chosen neighbour's Roar happens again, as the Vole's own, at the Vole's crossroad.
            let (Some(cr), Some(iid)) = (cr_of(st), m_get_i(step, "vole")) else { return };
            let Some((vole_cr, pos)) = st.find_unit(iid) else { return };
            let vole = st.unit_at(vole_cr, pos).clone();
            if let Some(top) = st.top(cr).cloned() {
                if st.g.has_hook(top.card, Hook::OnPlace) {
                    run(st, top.card, Some(vole.card), Hook::OnPlace, &vole, &Args::Place(vole_cr));
                }
            }
        }
        "pile_to_hand" => {
            let Some(card) = choice.as_str().and_then(|s| st.card_id(s)) else { return };
            let from_owner = m_get_s(step, "from_owner").map(player_from);
            if st.pile_take(card, from_owner) {
                crate::emit!(st, "unremove", vmap!("card" => card_v(st, card), "owner" => from_owner.map(pn).unwrap_or(Value::Null), "to" => pn(chooser)));
                gain_to_hand(st, chooser, card, 0);
            }
        }
        "make_in_hand" => {
            let Some(card) = choice.as_str().and_then(|s| st.card_id(s)) else { return };
            gain_to_hand(st, chooser, card, 0);
        }
        "duplicate" => {
            let iid = choice.as_i64().unwrap_or(-1);
            if let Some(inst) = st.hands[chooser as usize].iter().find(|u| u.iid == iid).cloned() {
                gain_to_hand(st, chooser, inst.card, inst.strength_counter as i32);
            }
        }
        "discard" => {
            let iid = choice.as_i64().unwrap_or(-1);
            if st.hands[chooser as usize].iter().any(|u| u.iid == iid) {
                remove_from_hand(st, chooser, iid);
            }
        }
        "roam_to" => {
            let iid = m_get_i(step, "iid").unwrap_or(-1);
            if let Some((origin, pos)) = st.find_unit(iid) {
                if pos + 1 == st.stack(origin).len() {
                    let owner = st.unit_at(origin, pos).owner;
                    let target = if choice.as_str() == Some("den") {
                        Some(crate::actions::Target::Hq(other(owner)))
                    } else {
                        cr_of(st).map(crate::actions::Target::Cr)
                    };
                    if let Some(t) = target {
                        let _ = do_roam(st, owner, origin, &t, true);
                    }
                }
            }
        }
        _ => panic!("unknown THEN {name:?}"),
    }
}
