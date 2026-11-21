//! The effect engine: strength and cost, the placement mechanic, the cover, removal, food, draws, and the effect stack.
//!
//! Effects resolve as steps on `state.effect_stack`, last in first out, drained by `resolve()`. A step that needs a
//! choice surfaces as `state.pending`; the choice arrives as a normal action and resumes the paused step.

use smallvec::SmallVec;

use crate::actions::{Action, Target};
use crate::cards::{CrushLimit, LeaderKind, OnCover, OnDeath, OnRaid, Roar};
use crate::data::*;
use crate::events::Ev;
use crate::state::*;

// ================================================================== strength, counts, cost

/// `player`'s count of `what`: cards in their hand, their animals on the board (top units), the regions they control,
/// the cards they played from hand this turn (none while it isn't their turn).
pub fn count(st: &State, player: Player, what: Count) -> i32 {
    match what {
        Count::Hand => st.hands[player as usize].len() as i32,
        Count::Ally => st.board.own[player as usize].count_ones() as i32,
        Count::Region => {
            let own = st.board.own[player as usize];
            st.g.map.regions.iter().filter(|r| r.mask & own == r.mask).count() as i32
        }
        Count::Played => if st.current == player { st.played_this_turn } else { 0 },
    }
}

/// The strength a unit of `card` has for `owner` now: on the board, or as it would be played from hand.
#[inline]
pub fn card_strength(st: &State, card: CardId, owner: Player) -> i32 {
    let c = st.card(card);
    match c.base_strength {
        Some(v) => v,
        None => (st.cfg().shade_growth * count(st, owner, c.dynamic.expect("a dynamic card names its count"))).max(0),
    }
}

#[inline]
pub fn effective_strength(st: &State, u: &Unit) -> i32 {
    (card_strength(st, u.card, u.owner) + u.strength_mod).max(0)
}

/// May `placer`, played from hand, cover the enemy `target`? Only when it is strictly stronger.
#[inline]
pub fn can_cover(st: &State, placer: &Unit, target: &Unit) -> bool {
    effective_strength(st, placer) > effective_strength(st, target)
}

/// Armor: no ability removes it (a cover's removal is the rules', not an ability's).
#[inline]
pub fn can_be_removed(st: &State, u: &Unit) -> bool {
    !st.card(u.card).has(ARMOR)
}

/// Stealth: an enemy's ability can't choose it.
#[inline]
pub fn can_be_chosen(st: &State, u: &Unit, by_player: Player) -> bool {
    by_player == u.owner || !st.card(u.card).has(STEALTH)
}

fn base_cost(st: &State, card: CardId, player: Player) -> i32 {
    let c = st.card(card);
    match c.beh.djinn {
        None => c.cost,
        Some(what) => {
            let per = match what {
                Count::Played => st.cfg().combo_djinn_discount,
                Count::Region => st.cfg().region_djinn_discount,
                _ => 1,
            };
            c.cost - per * count(st, player, what)
        }
    }
}

/// What playing this copy from hand costs: its card's cost, a Djinn's less its count, plus what effects put on the copy,
/// never below 0.
pub fn unit_cost(st: &State, u: &Unit) -> i32 {
    (base_cost(st, u.card, u.owner) + u.cost_mod).max(0)
}

/// What playing `card` from hand costs `player`: its cheapest copy in their hand, or the card's cost when they hold none.
pub fn mana_cost(st: &State, card: CardId, player: Player) -> i32 {
    st.hands[player as usize].iter().filter(|u| u.card == card).map(|u| unit_cost(st, u)).min()
        .unwrap_or_else(|| base_cost(st, card, player).max(0))
}

/// The hand slot a placement of `card` plays: its cheapest copy in hand, the first of those.
pub fn playable_copy(st: &State, player: Player, card: CardId) -> Option<usize> {
    let mut best: Option<(usize, i32)> = None;
    for (i, u) in st.hands[player as usize].iter().enumerate() {
        if u.card == card {
            let c = unit_cost(st, u);
            if best.map_or(true, |(_, b)| c < b) {
                best = Some((i, c));
            }
        }
    }
    best.map(|(i, _)| i)
}

// ================================================================== placement

/// Every placement `player` could make from hand now with `left` mana, cards in id order and tiles in name order, the
/// den raid last for each card. A card lands on an empty tile, on its owner's animal, or on an enemy it is stronger
/// than; Flight lands anywhere; Hungry only on an enemy it is stronger than. A connected animal (or a flier) may raid
/// the enemy den, reached through their base.
pub fn legal_placements(st: &State, player: Player, left: i32, out: &mut Vec<Action>) {
    let occ = st.connected_occupied(player);
    let enemy = other(player);
    let reach_den = st.g.map.hq_front[enemy as usize] & occ != 0;
    let connectable = st.connectable(player, occ);
    let n_tiles = st.g.map.n_tiles() as Tile;
    let hand = &st.hands[player as usize];
    let mut ids: SmallVec<[CardId; 12]> = hand.iter().map(|u| u.card).collect();
    ids.sort_unstable();
    ids.dedup();
    for card in ids {
        let placer = hand[playable_copy(st, player, card).unwrap()];
        if unit_cost(st, &placer) > left {
            continue;
        }
        let c = st.card(card);
        let (hungry, flight) = (c.has(HUNGRY), c.has(FLIGHT));
        let strength = effective_strength(st, &placer);
        for t in 0..n_tiles {
            if !(flight || connectable >> t & 1 == 1) {
                continue;
            }
            let ok = match st.board.top(t) {
                None => !hungry,
                Some(top) if top.owner == player => !hungry,
                Some(top) => strength > effective_strength(st, &top),
            };
            if ok {
                out.push(Action::Place { card, target: Target::Tile(t) });
            }
        }
        if (reach_den || flight) && !hungry {
            out.push(Action::Place { card, target: Target::Den(enemy) });
        }
    }
}

pub fn do_placement(st: &mut State, player: Player, card: CardId, target: Target) -> Result<(), String> {
    let Some(i) = playable_copy(st, player, card) else {
        return Err(format!("{} has no {:?} in hand", pname(player), st.g.cards.name_of(card)));
    };
    let unit = st.hands[player as usize][i];
    let strength = effective_strength(st, &unit); // as it is played
    st.hands[player as usize].remove(i);
    st.played_this_turn += 1;
    let nth = st.cfg().assassin_nth_card;
    if nth != 0 && st.played_this_turn % nth == 0 && st.leads(player, st.g.named.assassin) {
        // the Assassin: every third card played in a turn draws
        st.effect_stack.push(Step::by(StepKind::Draw { player, n: 1 }, st.g.named.assassin.unwrap()));
    }
    match target {
        Target::Den(enemy) => raid(st, player, unit, enemy, strength),
        Target::Tile(t) => land_unit(st, player, unit, t),
    }
    Ok(())
}

/// The food a raid by `player`'s `card` at `strength` destroys, before the den's own food caps it: its strength, doubled
/// for a card whose raids destroy double, and the Raider's 1 more.
pub fn raid_food(st: &State, player: Player, card: CardId, strength: i32) -> i32 {
    let bonus = if st.leads(player, st.g.named.raider) { st.cfg().raider_leader_bonus } else { 0 };
    let factor = if st.card(card).beh.double_raider { st.cfg().double_raid_factor } else { 1 };
    strength.max(0) * factor + bonus
}

/// The den raid: an animal that enters the enemy den destroys food equal to its strength, at most what they have, and
/// is spent to the Remove Pile without landing (no Roar). A den emptied loses the game.
fn raid(st: &mut State, player: Player, unit: Unit, enemy: Player, strength: i32) {
    let n = raid_food(st, player, unit.card, strength).min(st.food[enemy as usize]);
    st.emit(Ev::Raid { player, iid: unit.iid, card: unit.card, den: enemy, strength, n });
    st.pile_add(unit.card, unit.owner);
    st.food[enemy as usize] -= n;
    if st.result.is_none() && st.food[enemy as usize] <= 0 {
        st.result = Some(GameResult { winner: Some(player), reason: Reason::Starved });
    }
    if st.result.is_none() {
        match st.card(unit.card).beh.on_raid {
            Some(OnRaid::Draw) => st.effect_stack.push(Step::by_unit(StepKind::Draw { player: unit.owner, n: 1 }, &unit)),
            None => {}
        }
    }
}

/// The animal lands on `cr`. What it covered is removed once its Roar and every reaction to the cover have resolved
/// (the stack is last in, first out: that removal goes in first).
fn land_unit(st: &mut State, player: Player, unit: Unit, cr: Tile) {
    let covered = st.board.top(cr);
    let onto_enemy = covered.map_or(false, |c| c.owner != player);
    st.board.push(cr, unit);
    st.emit(Ev::Place { player, iid: unit.iid, card: unit.card, cr });
    if let Some(cov) = covered {
        st.emit(Ev::Cover { cr, iid: cov.iid, card: cov.card, owner: cov.owner, by: unit.iid });
        if onto_enemy && st.card(unit.card).has(HUNGRY) {
            st.effect_stack.push(Step::by(StepKind::HungryFood { player, prey: cov.iid }, unit.card));
        }
        if onto_enemy {
            match st.card(unit.card).beh.on_cover {
                // it removes an enemy by covering it: the draw waits below the cover's removal
                Some(OnCover::DrawIfItRemoves) => st.effect_stack.push(Step::by_unit(StepKind::DrawIfGone { player: unit.owner, prey: cov.iid, n: 1 }, &unit)),
                None => {}
            }
        }
        st.effect_stack.push(Step::new(StepKind::CoverRemove { cr }));
    }
    if onto_enemy && st.leads(player, st.g.named.warlord) {
        st.effect_stack.push(Step::by(StepKind::GainFood { player, amount: st.cfg().warlord_leader_food }, st.g.named.warlord.unwrap()));
    }
    if onto_enemy {
        let cov = covered.unwrap();
        if st.card(cov.card).has(SPIKES) {
            // Spikes: the first time an enemy covers it, that enemy is removed. Once per animal.
            if !cov.retaliation_used {
                st.board.under_mut(cr).expect("the covered animal is beneath the top").retaliation_used = true;
                if can_be_removed(st, &unit) {
                    st.effect_stack.push(remove_iid_step(unit.iid, cov.owner, cov.card));
                }
            }
        }
        if st.card(cov.card).has(POISON) {
            // Poison: the enemy that covers it is removed at the start of the Poison animal's owner's next turn.
            st.scheduled.push(Scheduled { iid: unit.iid, owner: cov.owner, remaining: 1, step: remove_iid_step(unit.iid, cov.owner, cov.card) });
            st.emit(Ev::Poisoned { iid: unit.iid, card: unit.card, owner: unit.owner, by: cov.iid });
        }
    }
    if let Some(roar) = st.card(unit.card).beh.on_place {
        let n = st.effect_stack.len();
        let prev = (st.cause, st.cause_iid);
        st.cause = Some(unit.card);
        st.cause_iid = Some(unit.iid);
        run_roar(st, roar, &unit, cr);
        (st.cause, st.cause_iid) = prev;
        for step in &mut st.effect_stack[n..] {
            // every step a Roar pushes names its card and unit as the source
            let by = *step.by_card.get_or_insert(unit.card);
            if by == unit.card {
                step.by_iid.get_or_insert(unit.iid);
            }
        }
    }
}

fn remove_iid_step(iid: i32, by_player: Player, by_card: CardId) -> Step {
    Step::by(StepKind::RemoveIid { iid, by_player: Some(by_player) }, by_card)
}

// ================================================================== the cards' Roars

fn run_roar(st: &mut State, roar: Roar, unit: &Unit, cr: Tile) {
    let owner = unit.owner;
    match roar {
        Roar::Weaken(amount) => {
            // "give an adjacent enemy -N strength": for good; at 0 the rule removes it. Stealth hides from it.
            let targets: Tiles = st.g.map.neighbors[cr as usize].iter().copied()
                .filter(|&nb| st.board.top(nb).map_or(false, |top| top.owner != owner && can_be_chosen(st, &top, owner)))
                .collect();
            if !targets.is_empty() {
                st.effect_stack.push(Step::by(StepKind::WeakenChoice { chooser: owner, options: targets, amount }, unit.card));
            }
        }
        Roar::RemoveAdjacent => {
            // the adjacent enemies its player may choose: removable (no Armor) and choosable (no Stealth)
            let targets: Tiles = st.g.map.neighbors[cr as usize].iter().copied()
                .filter(|&nb| st.board.top(nb).map_or(false, |top| top.owner != owner && can_be_removed(st, &top) && can_be_chosen(st, &top, owner)))
                .collect();
            if !targets.is_empty() {
                st.effect_stack.push(Step::by(StepKind::RemoveChoice { chooser: owner, options: targets, optional: false }, unit.card));
            }
        }
        Roar::Crush(limit) => {
            // every one at once, no choice, so Stealth doesn't hide; a removal by an ability, so Armor holds
            let max = match limit {
                CrushLimit::Rhino => st.cfg().crush_max,
                CrushLimit::Albatross => st.cfg().crush_albatross_max,
                CrushLimit::YoungRhino => st.cfg().crush_young_max,
                CrushLimit::YoungAlbatross => st.cfg().crush_young_albatross_max,
            };
            for i in 0..st.g.map.neighbors[cr as usize].len() {
                let nb = st.g.map.neighbors[cr as usize][i];
                if let Some(top) = st.board.top(nb) {
                    if top.owner != owner && effective_strength(st, &top) <= max {
                        st.effect_stack.push(remove_iid_step(top.iid, owner, unit.card));
                    }
                }
            }
        }
        Roar::Draw => st.effect_stack.push(Step::new(StepKind::Draw { player: owner, n: 1 })),
        Roar::Scout => st.effect_stack.push(Step::new(StepKind::Scout { player: owner })),
        Roar::Duplicate => {
            // a Spore on an adjacent tile, wherever a card could be placed: empty, yours, or an enemy the Spore is
            // stronger than
            let Some(spore_card) = st.g.named.spore else { return };
            let spore = Unit::new(spore_card, owner, -1);
            let tiles: Tiles = st.g.map.neighbors[cr as usize].iter().copied()
                .filter(|&nb| st.board.top(nb).map_or(true, |top| top.owner == owner || can_cover(st, &spore, &top)))
                .collect();
            if !tiles.is_empty() {
                st.effect_stack.push(Step::new(StepKind::PlaceToken { player: owner, card: spore_card, options: tiles }));
            }
        }
        Roar::MamaSpore => {
            let Some(spore_card) = st.g.named.spore else { return };
            st.effect_stack.push(Step::new(StepKind::ToHand { player: owner, card: spore_card, n: st.cfg().mama_spores }));
        }
        Roar::AssassinCard => {
            // each card then in hand, for as long as it stays there
            let d = st.cfg().assassin_card_discount;
            for u in st.hands[owner as usize].iter_mut() {
                u.cost_mod -= d;
            }
        }
        Roar::SageCard => st.power_discount[owner as usize] += st.cfg().sage_card_power_discount,
        // this turn's mana, on top of what is left, past the cap too
        Roar::GainMana => st.mana_spent -= st.cfg().mana_blob_mana,
    }
}

// ================================================================== removal, food, draws

/// Remove the unit `iid` from the stack on `cr` (mid-stack too) to the Remove Pile. Armor stops any removal by an
/// ability (`by_effect`); the rules' own removals pass it.
fn remove_specific(st: &mut State, cr: Tile, iid: i32, by_player: Option<Player>, by_effect: bool) -> bool {
    let Some((at, unit)) = st.board.find(iid) else { return false };
    if at != cr {
        return false;
    }
    if by_effect && !can_be_removed(st, &unit) {
        return false;
    }
    st.emit(Ev::Remove { cr, iid, card: unit.card, owner: unit.owner, by: by_player });
    st.board.remove(cr, iid);
    st.pile_add(unit.card, unit.owner);
    match st.card(unit.card).beh.on_death {
        // "Death: draw a card.": when it is removed from the board, by anything, its owner draws
        Some(OnDeath::Draw) => st.effect_stack.push(Step::by_unit(StepKind::Draw { player: unit.owner, n: 1 }, &unit)),
        None => {}
    }
    true
}

/// A turn cap cut the turn's effects short: what a cover left beneath it is removed now, by the rules and with nothing
/// set off (the effects are over), so no animal stays buried.
pub fn remove_buried(st: &mut State) {
    if !st.board.has_buried() {
        return;
    }
    let tiles: SmallVec<[Tile; 24]> = st.board.tiles().iter().copied().collect();
    for t in tiles {
        let Some(top) = st.board.top(t) else { continue };
        for u in st.board.buried_of(t) {
            st.emit(Ev::Remove { cr: t, iid: u.iid, card: u.card, owner: u.owner, by: Some(top.owner) });
            st.board.remove(t, u.iid);
            st.pile_add(u.card, u.owner);
        }
    }
}

pub fn gain_food(st: &mut State, player: Player, amount: i32, income: bool) {
    if amount <= 0 {
        return;
    }
    st.food[player as usize] += amount;
    st.emit(Ev::Food { player, n: amount, income });
    if st.food[player as usize] >= st.g.map.win_food {
        st.result = Some(GameResult { winner: Some(player), reason: Reason::Food });
    }
}

/// The newest of `made` past the hand limit burn to the Remove Pile.
fn burn_over_limit(st: &mut State, player: Player, made: &[Unit]) {
    let over = st.hands[player as usize].len() as i32 - st.cfg().hand_limit;
    if over <= 0 {
        return;
    }
    let from = made.len().saturating_sub(over as usize);
    for inst in &made[from..] {
        let hand = &mut st.hands[player as usize];
        if let Some(i) = hand.iter().position(|u| u.iid == inst.iid) {
            hand.remove(i);
        }
        st.pile_add(inst.card, inst.owner);
        st.emit(Ev::Burn { iid: inst.iid, card: inst.card, owner: inst.owner });
    }
}

/// The food `player` would lose to fatigue by drawing `n` cards now: nothing for each card their deck still holds,
/// then one step more for each card it does not.
pub fn fatigue_due(st: &State, player: Player, n: i32) -> i32 {
    let p = player as usize;
    let empty = (n.max(0) - st.decks[p].len() as i32).max(0);
    let step = st.cfg().fatigue_step;
    (1..=empty).map(|k| (st.fatigue[p] + k) * step).sum()
}

/// Draw n cards; the newest past the hand limit burn to the Remove Pile. Fatigue: each card the deck no longer holds
/// is not drawn and costs the player food instead, one step more each time (1, then 2, then 3, ...); at no food they
/// lose, whoever's turn it is.
pub fn draw_cards(st: &mut State, player: Player, n: i32) {
    let drawn = st.draw(player, n);
    if !drawn.is_empty() {
        if st.events.on {
            st.emit(Ev::Draw { player, cards: drawn.iter().map(|u| (u.iid, u.card)).collect() });
        }
        burn_over_limit(st, player, &drawn);
    }
    let p = player as usize;
    for _ in drawn.len() as i32..n.max(0) {
        if st.result.is_some() {
            return;
        }
        st.fatigue[p] += 1;
        let lost = (st.fatigue[p] * st.cfg().fatigue_step).min(st.food[p]).max(0);
        st.food[p] -= lost;
        st.emit(Ev::Fatigue { player, n: lost, count: st.fatigue[p] });
        if st.food[p] <= 0 {
            st.result = Some(GameResult { winner: Some(other(player)), reason: Reason::Starved });
        }
    }
}

/// Advance `player`'s timers (Poison) and push those that come due; a timer on a unit gone from the board is cancelled.
pub fn start_of_turn(st: &mut State, player: Player) {
    if st.scheduled.is_empty() {
        return;
    }
    let all = std::mem::take(&mut st.scheduled);
    let mut fired: SmallVec<[Scheduled; 2]> = SmallVec::new();
    for mut s in all {
        if s.owner != player {
            st.scheduled.push(s);
        } else if st.board.holds(s.iid) {
            s.remaining -= 1;
            if s.remaining <= 0 { fired.push(s) } else { st.scheduled.push(s) }
        }
    }
    for s in fired.into_iter().rev() {
        // the earliest scheduled ends on top of the stack and resolves first
        st.effect_stack.push(s.step);
    }
}

// ================================================================== the resolve loop

/// Drain the effect stack until it is empty, a choice is needed, or the game is decided. Each time it empties, every
/// animal at 0 strength is removed (whatever that sets off resolves in turn).
pub fn resolve(st: &mut State) -> Result<(), String> {
    loop {
        drain(st)?;
        if st.pending.is_some() || st.result.is_some() || !st.effect_stack.is_empty() || !remove_the_weak(st) {
            return Ok(());
        }
    }
}

/// The rule: an animal at 0 strength is removed, by the rules, so Armor doesn't hold. Whether any was.
fn remove_the_weak(st: &mut State) -> bool {
    let weak: SmallVec<[(Tile, i32); 4]> = st.board.units().iter().filter(|(_, u)| effective_strength(st, u) <= 0).map(|(t, u)| (*t, u.iid)).collect();
    for &(cr, iid) in &weak {
        remove_specific(st, cr, iid, None, false);
    }
    !weak.is_empty()
}

fn drain(st: &mut State) -> Result<(), String> {
    while st.pending.is_none() && st.result.is_none() {
        let Some(mut step) = st.effect_stack.pop() else { break };
        st.effect_steps_this_turn += 1;
        let max = st.cfg().max_effect_steps_per_turn;
        if st.effect_steps_this_turn > max {
            // The turn's effect cap: what is left is dropped, and the turn ends (rules::apply_action) once this returns.
            if st.effect_steps_this_turn == max + 1 {
                let cards = stack_cards(st, step.by_card);
                record_cap(st, CapKind::EffectSteps, cards);
            }
            st.effect_stack.clear();
            st.pending = None;
            return Ok(());
        }
        let n = st.effect_stack.len();
        let was = (st.cause, st.cause_iid);
        st.cause = step.by_card;
        st.cause_iid = step.by_iid;
        let req = run_op(st, &mut step);
        (st.cause, st.cause_iid) = was;
        let req = req?;
        if let Some(by) = step.by_card {
            // what a step sets off is that card's doing too (that very unit's, when the card matches)
            for new in &mut st.effect_stack[n..] {
                let new_by = *new.by_card.get_or_insert(by);
                if step.by_iid.is_some() && new_by == by && new.by_iid.is_none() {
                    new.by_iid = step.by_iid;
                }
            }
        }
        if let Some(req) = req {
            // the step needs a choice: put it back and pause
            st.effect_stack.push(step);
            st.pending = Some(req);
            return Ok(());
        }
    }
    Ok(())
}

/// A turn cap fired: the `turn_capped` event, kept on the state too. `cards`: where the dropped steps came from.
pub fn record_cap(st: &mut State, cap: CapKind, mut cards: Vec<CardId>) {
    cards.sort_unstable();
    cards.dedup();
    let rec = Cap { cap, player: st.current, turn: st.turn_counter, cards };
    st.emit(Ev::TurnCapped { cap, player: rec.player, turn: rec.turn, cards: rec.cards.clone() });
    st.caps.push(rec);
}

pub fn stack_cards(st: &State, extra: Option<CardId>) -> Vec<CardId> {
    st.effect_stack.iter().filter_map(|s| s.by_card).chain(extra).collect()
}

fn choice_pending(chooser: Player, optional: bool, options: &Tiles) -> Option<Pending> {
    Some(Pending { chooser, optional, mulligan: false, options: Options::Tiles(options.clone()) })
}

/// Index of the topmost deck card (the end) that is no copy of a returned card or of `extra`.
fn mulligan_replacement(deck: &[CardId], returned: &[CardId], extra: Option<CardId>) -> Option<usize> {
    (0..deck.len()).rev().find(|&i| !returned.contains(&deck[i]) && Some(deck[i]) != extra)
}

/// Run one step. Ok(Some) when it needs a choice first.
fn run_op(st: &mut State, step: &mut Step) -> Result<Option<Pending>, String> {
    match &mut step.kind {
        StepKind::Mulligan { player, returned } => {
            // A blacklist mulligan: each returned card is replaced at once by the top deck card that is no copy of
            // anything returned so far, up to the opening hand's size; SKIP keeps the rest. Returned cards are shuffled
            // back at the end.
            let player = *player;
            let p = player as usize;
            let mut done = false;
            if let Some(choice) = step.choice.take() {
                match choice {
                    Choice::Skip => done = true,
                    Choice::Iid(iid) => {
                        if let Some(i) = st.hands[p].iter().position(|u| u.iid == iid) {
                            let inst = st.hands[p][i];
                            if mulligan_replacement(&st.decks[p], returned, Some(inst.card)).is_some() {
                                st.hands[p].remove(i);
                                returned.push(inst.card);
                                let at = mulligan_replacement(&st.decks[p], returned, None).unwrap();
                                let card = st.decks[p].remove(at);
                                let new = Unit::new(card, player, st.new_iid());
                                st.hands[p].push(new);
                                st.emit(Ev::Mulligan { player, returned: inst.iid, drawn: (new.iid, new.card) });
                            }
                        }
                    }
                    _ => {}
                }
            }
            if !done && !st.hands[p].is_empty() && (returned.len() as i32) < st.cfg().mulligan_cap(player, st.first_player)
                && mulligan_replacement(&st.decks[p], returned, None).is_some() {
                return Ok(Some(Pending { chooser: player, optional: true, mulligan: true, options: Options::Iids(st.hands[p].iter().map(|u| u.iid).collect()) }));
            }
            if !returned.is_empty() {
                // a kept hand leaves the deck order (and the RNG) untouched
                st.decks[p].extend(returned.iter().copied());
                st.rng.shuffle(&mut st.decks[p]);
            }
            if !st.effect_stack.iter().any(|s| matches!(s.kind, StepKind::Mulligan { .. })) {
                // both done: the first turn begins, with its card
                st.emit(Ev::TurnStart { player: st.current, turn: st.turn_counter });
                draw_cards(st, st.current, st.cfg().turn_draw_count);
            }
            Ok(None)
        }
        StepKind::CoverRemove { cr } => {
            // Every animal still beneath the top of `cr` is removed, by the rules, so Armor doesn't hold. If the coverer
            // is gone, what it covered is the top again and stays.
            let cr = *cr;
            if st.board.has_buried() {
                let under = st.board.buried_of(cr);
                if !under.is_empty() {
                    let top_owner = st.board.top(cr).unwrap().owner;
                    for u in under {
                        remove_specific(st, cr, u.iid, Some(top_owner), false);
                    }
                }
            }
            Ok(None)
        }
        StepKind::HungryFood { player, prey } => {
            // Hungry: once its prey is gone from the board, its player gains the food.
            if !st.board.holds(*prey) {
                gain_food(st, *player, st.cfg().hungry_food, false);
            }
            Ok(None)
        }
        StepKind::GainFood { player, amount } => {
            gain_food(st, *player, *amount, false);
            Ok(None)
        }
        StepKind::Draw { player, n } => {
            draw_cards(st, *player, *n);
            Ok(None)
        }
        StepKind::DrawIfGone { player, prey, n } => {
            if !st.board.holds(*prey) {
                draw_cards(st, *player, *n);
            }
            Ok(None)
        }
        StepKind::Scout { player } => {
            // Look at the top cards of your deck, put the one you choose into your hand and shuffle the rest back.
            let player = *player;
            let p = player as usize;
            let n = (st.cfg().scout_look.max(0) as usize).min(st.decks[p].len());
            if n == 0 {
                return Ok(None);
            }
            let k = match step.choice {
                None => return Ok(Some(Pending { chooser: player, optional: false, mulligan: false, options: Options::Deck(n as u8) })),
                Some(Choice::Deck(k)) if (k as usize) < st.decks[p].len() => k as usize,
                Some(other) => return Err(format!("bad Scout choice {other:?}")),
            };
            let at = st.decks[p].len() - 1 - k;
            let card = st.decks[p].remove(at);
            let inst = Unit::new(card, player, st.new_iid());
            st.hands[p].push(inst);
            st.emit(Ev::Draw { player, cards: vec![(inst.iid, inst.card)] });
            if st.hands[p].len() as i32 > st.cfg().hand_limit {
                // past the hand limit it burns, as a draw does
                st.hands[p].pop();
                st.pile_add(inst.card, inst.owner);
                st.emit(Ev::Burn { iid: inst.iid, card: inst.card, owner: inst.owner });
            }
            st.rng.shuffle(&mut st.decks[p]);
            Ok(None)
        }
        StepKind::PlaceToken { player, card, options } => {
            // A token on the tile its player chooses (free, as anything an effect puts into play): it lands as a placed
            // animal does, so it may cover.
            if options.is_empty() {
                return Ok(None);
            }
            match step.choice {
                None => Ok(choice_pending(*player, false, options)),
                Some(Choice::Tile(t)) => {
                    let (player, card) = (*player, *card);
                    let unit = Unit::new(card, player, st.new_iid());
                    land_unit(st, player, unit, t);
                    Ok(None)
                }
                Some(other) => Err(format!("bad token tile {other:?}")),
            }
        }
        StepKind::ToHand { player, card, n } => {
            // New copies of a card into a player's hand; past the hand limit they burn, as a draw does.
            let (player, card, n) = (*player, *card, *n);
            let mut made: SmallVec<[Unit; 4]> = SmallVec::new();
            for _ in 0..n {
                let inst = Unit::new(card, player, st.new_iid());
                st.hands[player as usize].push(inst);
                made.push(inst);
            }
            if st.events.on {
                st.emit(Ev::Draw { player, cards: made.iter().map(|u| (u.iid, u.card)).collect() });
            }
            burn_over_limit(st, player, &made);
            Ok(None)
        }
        StepKind::RemoveIid { iid, by_player } => {
            if let Some((cr, _)) = st.board.find(*iid) {
                remove_specific(st, cr, *iid, *by_player, true);
            }
            Ok(None)
        }
        StepKind::WeakenChoice { chooser, options, amount } => {
            // The player picks the enemy a Roar gives -N strength, for good, even when there is one.
            if options.is_empty() {
                return Ok(None);
            }
            match step.choice {
                None => Ok(choice_pending(*chooser, false, options)),
                Some(Choice::Tile(t)) => {
                    let amount = *amount;
                    if let Some(top) = st.board.top_mut(t) {
                        top.strength_mod -= amount;
                        let top = *top;
                        st.emit(Ev::Strength { iid: top.iid, card: top.card, owner: top.owner, n: -amount });
                    }
                    Ok(None)
                }
                Some(other) => Err(format!("bad target {other:?}")),
            }
        }
        StepKind::RemoveChoice { chooser, options, optional } => {
            // The player picks the enemy a Roar removes, even when there is one.
            if options.is_empty() {
                return Ok(None);
            }
            match step.choice {
                None => Ok(choice_pending(*chooser, *optional, options)),
                Some(Choice::Skip) => Ok(None),
                Some(Choice::Tile(t)) => {
                    let chooser = *chooser;
                    if let Some(top) = st.board.top(t) {
                        remove_specific(st, t, top.iid, Some(chooser), true);
                    }
                    Ok(None)
                }
                Some(other) => Err(format!("bad target {other:?}")),
            }
        }
    }
}

// ================================================================== leaders

fn power_price(st: &State, leader: Option<CardId>) -> i32 {
    // the Elf's power has its own price, every other the config's
    if leader.is_some() && leader == st.g.named.elf { st.cfg().elf_power_cost } else { st.cfg().leader_power_cost }
}

/// What `player`'s leader's power costs: its price less what their Sage's card took off it, never below 0.
pub fn power_cost(st: &State, player: Player) -> i32 {
    (power_price(st, st.leaders[player as usize]) - st.power_discount[player as usize]).max(0)
}

/// Whether `player`'s leader has a power that would do something now, not used yet this turn; the caller checks the mana.
pub fn leader_usable(st: &State, player: Player) -> bool {
    let Some(lead) = st.leaders[player as usize] else { return false };
    if st.card(lead).beh.leader != Some(LeaderKind::Power) || st.power_used {
        return false;
    }
    if Some(lead) == st.g.named.elf {
        return count(st, player, Count::Region) > 0; // food for each region you control: none, nothing to gain
    }
    true // the Sage draws: from an empty deck too, where the draw costs food (fatigue)
}

/// `player` uses their leader's power (the caller has paid for it).
pub fn do_leader(st: &mut State, player: Player) -> Result<(), String> {
    let Some(lead) = st.leaders[player as usize] else { return Err(format!("{} has no leader", pname(player))) };
    st.emit(Ev::LeaderPower { player, card: lead });
    st.power_used = true;
    if Some(lead) == st.g.named.sage {
        st.effect_stack.push(Step::by(StepKind::Draw { player, n: 1 }, lead));
    } else if Some(lead) == st.g.named.elf {
        // "Gain 1 food for each region you control."
        let amount = st.cfg().elf_food_per_region * count(st, player, Count::Region);
        st.effect_stack.push(Step::by(StepKind::GainFood { player, amount }, lead));
    } else {
        return Err(format!("{:?} has no power to use", st.g.cards.name_of(lead)));
    }
    Ok(())
}
