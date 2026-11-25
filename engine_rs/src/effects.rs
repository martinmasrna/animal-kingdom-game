//! The effect engine: strength and cost, the placement mechanic, the cover, removal, food, draws, and the effect stack.
//!
//! Effects resolve as steps on `state.effect_stack`, last in first out, drained by `resolve()`. A step that needs a
//! choice surfaces as `state.pending`; the choice arrives as a normal action and resumes the paused step.

use smallvec::SmallVec;

use crate::actions::{Action, Target};
use crate::cards::{CrushLimit, OnCover, OnDeath, OnRaid, Roar};
use crate::data::*;
use crate::events::Ev;
use crate::state::*;

// ================================================================== strength, counts, cost

/// `player`'s count of `what`: cards in their hand, their animals on the board (top units), the regions they control,
/// the cards they played from hand this turn (none while it isn't their turn), the food their opponent lost this game,
/// the food their regions produced this game.
pub fn count(st: &State, player: Player, what: Count) -> i32 {
    match what {
        Count::Hand => st.hands[player as usize].len() as i32,
        Count::Ally => st.board.own[player as usize].count_ones() as i32,
        Count::Region => {
            let own = st.board.own[player as usize];
            st.g.map.regions.iter().filter(|r| r.mask & own == r.mask).count() as i32
        }
        Count::Played => if st.current == player { st.played_this_turn } else { 0 },
        Count::EnemyFoodLost => st.food_lost[other(player) as usize],
        Count::FoodProduced => st.food_produced[player as usize],
    }
}

/// The strength a unit of `card` has for `owner` now: on the board, or as it would be played from hand. Gorrak leading
/// adds to a Hungry card's, in hand and on the board; Nightmare carries what he has grown.
#[inline]
pub fn card_strength(st: &State, card: CardId, owner: Player) -> i32 {
    let c = st.card(card);
    let base = match c.base_strength {
        Some(v) => v,
        None => (st.cfg().shade_growth * count(st, owner, c.dynamic.expect("a dynamic card names its count"))).max(0),
    };
    let base = if c.has(HUNGRY) && st.leads(owner, st.g.named.warlord) { base + st.cfg().warlord_hungry_bonus } else { base };
    // Nightmare, while he leads: grown at every Dusk, wherever he is (one copy, a legendary)
    if Some(card) == st.g.named.raider && st.leads(owner, st.g.named.raider) { base + st.leeroy_growth[owner as usize] } else { base }
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

/// Spikes, for `u` standing on `cr`: its own, or an adjacent ally's "Adjacent allies have Spikes." (the Porcupine).
pub fn has_spikes(st: &State, u: &Unit, cr: Tile) -> bool {
    st.card(u.card).has(SPIKES)
        || st.g.map.neighbors[cr as usize].iter().any(|&nb| st.board.top(nb).map_or(false, |t| t.owner == u.owner && st.card(t.card).beh.spikes_aura))
}

/// Stealth: an enemy's ability can't choose it.
#[inline]
pub fn can_be_chosen(st: &State, u: &Unit, by_player: Player) -> bool {
    by_player == u.owner || !st.card(u.card).has(STEALTH)
}

fn base_cost(st: &State, card: CardId, player: Player) -> i32 {
    let c = st.card(card);
    // Gorrak: "Your Hungry allies cost 1 more, but gain 3 strength."
    let tax = if c.has(HUNGRY) && st.leads(player, st.g.named.warlord) { st.cfg().warlord_hungry_tax } else { 0 };
    tax + match c.beh.djinn {
        None => c.cost,
        Some(what) => {
            let per = match what {
                Count::Played => st.cfg().combo_djinn_discount,
                _ => 1,
            };
            c.cost - per * count(st, player, what)
        }
    }
}

/// The Rogue: "Every third card you play costs 1 less.": what `player`'s next card played this turn costs less.
pub fn rogue_discount(st: &State, player: Player) -> i32 {
    let nth = st.cfg().rogue_nth_card;
    if nth > 0 && st.current == player && (st.played_this_turn + 1) % nth == 0 && st.leads(player, st.g.named.assassin) {
        st.cfg().rogue_discount
    } else {
        0
    }
}

/// What playing this copy from hand costs: its card's cost, a Djinn's less its count, plus what effects put on the copy,
/// less the Rogue's discount, never below 0.
pub fn unit_cost(st: &State, u: &Unit) -> i32 {
    (base_cost(st, u.card, u.owner) + u.cost_mod - rogue_discount(st, u.owner)).max(0)
}

/// What playing `card` from hand costs `player`: its cheapest copy in their hand, or the card's cost when they hold none.
pub fn mana_cost(st: &State, card: CardId, player: Player) -> i32 {
    st.hands[player as usize].iter().filter(|u| u.card == card).map(|u| unit_cost(st, u)).min()
        .unwrap_or_else(|| (base_cost(st, card, player) - rogue_discount(st, player)).max(0))
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
    let all = st.g.map.all_tiles();
    let hand = &st.hands[player as usize];
    // each distinct card with the copy a placement plays (`playable_copy`: the cheapest, the first of those), in id order
    let mut copies: SmallVec<[(CardId, i32, usize); 12]> = SmallVec::new();
    for (i, u) in hand.iter().enumerate() {
        let cost = unit_cost(st, u);
        match copies.iter_mut().find(|c| c.0 == u.card) {
            Some(c) => {
                if cost < c.1 {
                    *c = (u.card, cost, i);
                }
            }
            None => copies.push((u.card, cost, i)),
        }
    }
    copies.sort_unstable_by_key(|c| c.0);
    for (card, cost, i) in copies {
        let placer = hand[i];
        if cost > left {
            continue;
        }
        let c = st.card(card);
        let (hungry, flight) = (c.has(HUNGRY), c.has(FLIGHT));
        let strength = effective_strength(st, &placer);
        let mut tiles = if flight { all } else { connectable & all };
        while tiles != 0 {
            let t = tiles.trailing_zeros() as Tile;
            tiles &= tiles - 1;
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
    let discounted = rogue_discount(st, player) > 0;
    st.hands[player as usize].remove(i);
    st.played_this_turn += 1;
    if discounted {
        // the Rogue's third card, paid for 1 less: her token shows it
        let lead = st.g.named.assassin.unwrap();
        st.effect_stack.push(Step::by(StepKind::LeaderTrigger { player, card: lead }, lead));
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
    let _ = player;
    let factor = if st.card(card).beh.double_raider { st.cfg().double_raid_factor } else { 1 };
    strength.max(0) * factor
}

/// The den raid: an animal that enters the enemy den destroys food equal to its strength, at most what they have, and
/// is spent to the Remove Pile without landing (no Roar). A den emptied loses the game.
fn raid(st: &mut State, player: Player, unit: Unit, enemy: Player, strength: i32) {
    let n = raid_food(st, player, unit.card, strength).min(st.food[enemy as usize]);
    st.raids[player as usize] += 1;
    st.emit(Ev::Raid { player, iid: unit.iid, card: unit.card, den: enemy, strength, n });
    st.pile_add(unit.card, unit.owner);
    st.food[enemy as usize] -= n;
    st.food_lost[enemy as usize] += n;
    if st.result.is_none() && st.food[enemy as usize] <= 0 {
        st.result = Some(GameResult { winner: Some(player), reason: Reason::Starved });
    }
    if st.result.is_none() {
        // "Whenever you raid, draw a card." for each such animal of the raider's owner on the board (the Plunderer)
        let mut m = st.board.own[player as usize];
        let mut n = 0;
        let mut by = None;
        while m != 0 {
            let t = m.trailing_zeros() as Tile;
            m &= m - 1;
            if let Some(top) = st.board.top(t) {
                if st.card(top.card).beh.raid_draw_aura {
                    n += 1;
                    by = Some(top);
                }
            }
        }
        if let Some(b) = by {
            st.effect_stack.push(Step::by_unit(StepKind::Draw { player, n }, &b));
        }
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
    if onto_enemy {
        let cov = covered.unwrap();
        if has_spikes(st, &cov, cr) {
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
            // a Spore on an adjacent empty crossroad the game picks, none when there is none
            let Some(spore_card) = st.g.named.spore else { return };
            let tiles: Tiles = st.g.map.neighbors[cr as usize].iter().copied().filter(|&nb| st.board.top(nb).is_none()).collect();
            if !tiles.is_empty() {
                let t = tiles[st.rng.randbelow(tiles.len())];
                let spore = Unit::new(spore_card, owner, st.new_iid());
                land_unit(st, owner, spore, t);
            }
        }
        Roar::MamaSpore => {
            let Some(spore_card) = st.g.named.spore else { return };
            st.effect_stack.push(Step::new(StepKind::ToHand { player: owner, card: spore_card, n: st.cfg().mama_spores }));
        }
        Roar::RogueCard => {
            // "If you played 3 or more cards this turn, draw 3 cards.": itself counts
            if st.played_this_turn >= st.cfg().rogue_card_needs {
                st.effect_stack.push(Step::new(StepKind::Draw { player: owner, n: st.cfg().rogue_card_draws }));
            }
        }
        Roar::ScoutTwice => {
            for _ in 0..st.cfg().reno_scouts {
                st.effect_stack.push(Step::new(StepKind::Scout { player: owner }));
            }
        }
        Roar::UpgradeFireballs => upgrade_fireballs(st, owner),
        Roar::EatCrystals => {
            // "destroy all your mana crystals. Gain 1 food for each.": the mana they held this turn goes with them
            let n = std::mem::take(&mut st.crystals[owner as usize]);
            st.effect_stack.push(Step::new(StepKind::GainFood { player: owner, amount: n * st.cfg().mana_eater_food_per_crystal }));
        }
        Roar::DoubleFood => {
            let amount = st.food[owner as usize];
            st.effect_stack.push(Step::new(StepKind::GainFood { player: owner, amount }));
        }
        // this turn's mana, on top of what is left, past the cap too
        Roar::GainMana => st.mana_spent -= st.cfg().mana_blob_mana,
        Roar::Scorch => {
            // every adjacent unit at once, its own player's too; no choice, so Stealth doesn't hide it; at 0 the rule removes it
            let burn = st.cfg().scorch_burn;
            for i in 0..st.g.map.neighbors[cr as usize].len() {
                let nb = st.g.map.neighbors[cr as usize][i];
                if let Some(top) = st.board.top_mut(nb) {
                    top.strength_mod -= burn;
                    let top = *top;
                    st.emit(Ev::Strength { iid: top.iid, card: top.card, owner: top.owner, n: -burn });
                    credit_if_doomed(st, unit.iid, &top);
                }
            }
            for (i, r) in st.g.map.regions.iter().enumerate() {
                if r.mask & (1u64 << cr) != 0 {
                    st.scorched |= 1u64 << i;
                }
            }
        }
    }
}

/// The Pyromancer's card: every Fireball in `player`'s hand a step up (Baby to Young to Adult to Elder; an Elder stays),
/// each keeping what it cost.
fn upgrade_fireballs(st: &mut State, player: Player) {
    let fb = st.g.named.fireballs;
    let p = player as usize;
    for i in 0..st.hands[p].len() {
        let u = st.hands[p][i];
        let Some(step) = fb[..3].iter().position(|&f| f == Some(u.card)) else { continue };
        let Some(next) = fb[step + 1] else { continue };
        let cost_mod = base_cost(st, u.card, player) + u.cost_mod - base_cost(st, next, player);
        let to = &mut st.hands[p][i];
        to.card = next;
        to.cost_mod = cost_mod;
        if u.made {
            // what both players watched made: it is the bigger one now
            if let Some(m) = st.made[p].iter().position(|&c| c == u.card) {
                st.made[p][m] = next;
            }
        }
    }
}

// ================================================================== the Angel Warrior, the Mage

/// The Angel Warrior: "After your ally removes an enemy, give it +1 strength." `remover`: the unit whose doing the
/// removal was, if it is still on the board; `victim_owner`: whose unit went.
fn credit_removal(st: &mut State, remover: Option<i32>, victim_owner: Player) {
    let Some(iid) = remover else { return };
    let Some((t, u)) = st.board.find(iid) else { return };
    if u.owner == victim_owner || !st.leads(u.owner, st.g.named.angel) || st.board.top(t).map(|x| x.iid) != Some(iid) {
        return;
    }
    let n = st.cfg().angel_removal_buff;
    st.emit(Ev::LeaderTrigger { player: u.owner, card: st.g.named.angel.unwrap() });
    let top = st.board.top_mut(t).unwrap();
    top.strength_mod += n;
    let top = *top;
    st.emit(Ev::Strength { iid: top.iid, card: top.card, owner: top.owner, n });
}

/// An effect of the unit `remover` brought `target` to 0 strength: the rules remove it once the effects finish, and the
/// removal is the remover's doing (the Angel Warrior's passive).
fn credit_if_doomed(st: &mut State, remover: i32, target: &Unit) {
    if effective_strength(st, target) <= 0 {
        if let Some((_, r)) = st.board.find(remover) {
            if r.owner != target.owner {
                credit_removal(st, Some(remover), target.owner);
            }
        }
    }
}

/// The Angel Warrior's card at its owner's Dawn: "give all connected allies +1 strength.", the allies in an unbroken
/// chain of adjacent allies from it (Martin, 2026-11-25: "Connected to Angel").
fn angel_dawn(st: &mut State, player: Player) {
    let own = st.board.own[player as usize];
    let mut m = own;
    while m != 0 {
        let t = m.trailing_zeros() as Tile;
        m &= m - 1;
        let Some(angel) = st.board.top(t) else { continue };
        if !st.card(angel.card).beh.angel_dawn {
            continue;
        }
        let mut seen = 1u64 << t;
        let mut frontier = seen;
        while frontier != 0 {
            let mut next = 0u64;
            let mut f = frontier;
            while f != 0 {
                let x = f.trailing_zeros() as usize;
                f &= f - 1;
                next |= st.g.map.nb_mask[x];
            }
            frontier = next & own & !seen;
            seen |= frontier;
        }
        let n = st.cfg().angel_dawn_buff;
        let mut allies = seen & !(1u64 << t);
        let prev = (st.cause, st.cause_iid);
        (st.cause, st.cause_iid) = (Some(angel.card), Some(angel.iid));
        while allies != 0 {
            let a = allies.trailing_zeros() as Tile;
            allies &= allies - 1;
            let top = st.board.top_mut(a).unwrap();
            top.strength_mod += n;
            let top = *top;
            st.emit(Ev::Strength { iid: top.iid, card: top.card, owner: top.owner, n });
        }
        (st.cause, st.cause_iid) = prev;
    }
}

/// The Mage's card: "If your deck is empty, transform into Mage, Transformed.", wherever it is, the moment the deck is
/// empty; on the board it does not roar.
pub fn transform_mages(st: &mut State) {
    let (Some(mage), Some(into)) = (st.g.named.sage, st.g.named.mage_transformed) else { return };
    for p in 0..2usize {
        if !st.decks[p].is_empty() {
            continue;
        }
        for u in st.hands[p].iter_mut() {
            if u.card == mage {
                u.card = into;
            }
        }
        let mut m = st.board.own[p];
        while m != 0 {
            let t = m.trailing_zeros() as Tile;
            m &= m - 1;
            if let Some(top) = st.board.top_mut(t) {
                if top.card == mage {
                    top.card = into;
                }
            }
        }
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
        // "Fall: add two [Flight 1] to your hand.": when it is removed from the board, by anything
        Some(OnDeath::GainFood) => {
            let amount = st.cfg().delicious_food_food;
            st.effect_stack.push(Step::by_unit(StepKind::GainFood { player: unit.owner, amount }, &unit));
        }
        Some(OnDeath::Hatch) => {
            if let Some(f) = st.g.named.flight_1 {
                st.effect_stack.push(Step::by_unit(StepKind::ToHand { player: unit.owner, card: f, n: st.cfg().bird_egg_flights }, &unit));
            }
        }
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
    if n > 0 && st.leads(player, st.g.named.reno) {
        // Reno: each "draw a card" waits on the stack and Scouts if the deck holds no duplicates by then (DrawOrScout)
        for _ in 0..n {
            st.effect_stack.push(Step::new(StepKind::DrawOrScout { player }));
        }
        return;
    }
    draw_plain(st, player, n);
}

/// Whether `player`'s deck holds no two copies of a card (Reno).
pub fn no_duplicates(st: &State, player: Player) -> bool {
    let d = &st.decks[player as usize];
    (0..d.len()).all(|i| !d[i + 1..].contains(&d[i]))
}

/// The draw itself, whoever leads.
fn draw_plain(st: &mut State, player: Player, n: i32) {
    let drawn = st.draw(player, n);
    if !drawn.is_empty() {
        if st.events.on {
            st.emit(Ev::Draw { player, cards: drawn.iter().map(|u| (u.iid, u.card)).collect() });
        }
        burn_over_limit(st, player, &drawn);
        // the Golden Egg: "When you draw this, draw a card." (one burned past the hand limit was drawn all the same)
        let eggs = drawn.iter().filter(|u| st.card(u.card).beh.draw_on_draw).count() as i32;
        if eggs > 0 {
            draw_cards(st, player, eggs * st.cfg().golden_egg_draws);
        }
    }
    let p = player as usize;
    for _ in drawn.len() as i32..n.max(0) {
        if st.result.is_some() {
            return;
        }
        st.fatigue[p] += 1;
        if st.leads(player, st.g.named.sage) {
            // the Mage: "Fatigue gains you food instead of losing it."
            st.emit(Ev::LeaderTrigger { player, card: st.g.named.sage.unwrap() });
            gain_food(st, player, st.fatigue[p] * st.cfg().fatigue_step, false);
            continue;
        }
        let lost = (st.fatigue[p] * st.cfg().fatigue_step).min(st.food[p]).max(0);
        st.food[p] -= lost;
        st.food_lost[p] += lost;
        st.emit(Ev::Fatigue { player, n: lost, count: st.fatigue[p] });
        if st.food[p] <= 0 {
            st.result = Some(GameResult { winner: Some(other(player)), reason: Reason::Starved });
        }
    }
}

/// Advance `player`'s timers (Poison) and push those that come due; a timer on a unit gone from the board is cancelled.
pub fn start_of_turn(st: &mut State, player: Player) {
    angel_dawn(st, player);
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
        transform_mages(st);
        if st.pending.is_some() || st.result.is_some() || !st.effect_stack.is_empty() || !remove_the_weak(st) {
            return Ok(());
        }
    }
}

/// The rule: an animal at 0 strength is removed, by the rules, so Armor doesn't hold. Whether any was.
fn remove_the_weak(st: &mut State) -> bool {
    // nearly always none is: say so without listing the board in order
    let mut m = st.board.occ;
    let mut any = false;
    while m != 0 && !any {
        let t = m.trailing_zeros() as Tile;
        m &= m - 1;
        any = effective_strength(st, &st.board.top(t).unwrap()) <= 0;
    }
    if !any && !st.board.buried_units().any(|u| effective_strength(st, u) <= 0) {
        return false;
    }
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

/// The `aim` event: `chooser` picked the piece on `t` for the effect now resolving (its cause is the source).
fn aim(st: &mut State, chooser: Player, t: Tile) {
    if let Some(top) = st.board.top(t) {
        st.emit(Ev::Aim { player: chooser, cr: t, iid: top.iid, card: top.card });
    }
}

fn choice_pending(chooser: Player, optional: bool, options: &Tiles) -> Option<Pending> {
    Some(Pending { chooser, optional, mulligan: false, options: Options::Tiles(options.clone()) })
}

/// Index of the topmost deck card (the end) that is no copy of a returned card or of `extra`.
fn mulligan_replacement(deck: &[CardId], returned: &[CardId], extra: Option<CardId>) -> Option<usize> {
    (0..deck.len()).rev().find(|&i| !returned.contains(&deck[i]) && Some(deck[i]) != extra)
}

/// Scout: look at the top cards of your deck, draw the one you choose and shuffle the rest back: a draw, so a Golden Egg
/// drawn this way draws a card, from the deck shuffled. Ok(Some) while the choice waits.
fn scout(st: &mut State, player: Player, choice: Option<Choice>) -> Result<Option<Pending>, String> {
    let p = player as usize;
    let n = (st.cfg().scout_look.max(0) as usize).min(st.decks[p].len());
    if n == 0 {
        return Ok(None);
    }
    let k = match choice {
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
    if st.card(card).beh.draw_on_draw {
        draw_cards(st, player, st.cfg().golden_egg_draws);
    }
    Ok(None)
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
                st.bottom_nightmare(player);
            }
            if !st.effect_stack.iter().any(|s| matches!(s.kind, StepKind::Mulligan { .. })) {
                // both done: the first turn begins, with its crystal and its card
                let first = st.current;
                st.begin_turn_mana(first);
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
                    let top = st.board.top(cr).unwrap();
                    for u in under {
                        if remove_specific(st, cr, u.iid, Some(top.owner), false) && u.owner != top.owner {
                            credit_removal(st, Some(top.iid), u.owner);
                        }
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
        StepKind::LeaderTrigger { player, card } => {
            let (player, card) = (*player, *card);
            st.emit(Ev::LeaderTrigger { player, card });
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
        StepKind::DrawOrScout { player } => {
            let player = *player;
            if st.decks[player as usize].is_empty() || !no_duplicates(st, player) {
                // an empty deck draws (fatigue) and a deck with a duplicate draws as any
                draw_plain(st, player, 1);
                return Ok(None);
            }
            scout(st, player, step.choice)
        }
        StepKind::Scout { player } => {
            let player = *player;
            scout(st, player, step.choice)
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
            make_into_hand(st, player, card, n, 0);
            Ok(None)
        }
        StepKind::RemoveIid { iid, by_player } => {
            if let Some((cr, u)) = st.board.find(*iid) {
                if remove_specific(st, cr, *iid, *by_player, true) {
                    credit_removal(st, step.by_iid, u.owner);
                }
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
                    aim(st, *chooser, t);
                    if let Some(top) = st.board.top_mut(t) {
                        top.strength_mod -= amount;
                        let top = *top;
                        st.emit(Ev::Strength { iid: top.iid, card: top.card, owner: top.owner, n: -amount });
                        if let Some(by) = step.by_iid {
                            credit_if_doomed(st, by, &top);
                        }
                    }
                    Ok(None)
                }
                Some(other) => Err(format!("bad target {other:?}")),
            }
        }
        StepKind::BuffChoice { chooser, options, amount } => {
            // The player picks the ally an effect gives +N strength, for good.
            if options.is_empty() {
                return Ok(None);
            }
            match step.choice {
                None => Ok(choice_pending(*chooser, false, options)),
                Some(Choice::Tile(t)) => {
                    let amount = *amount;
                    aim(st, *chooser, t);
                    if let Some(top) = st.board.top_mut(t) {
                        top.strength_mod += amount;
                        let top = *top;
                        st.emit(Ev::Strength { iid: top.iid, card: top.card, owner: top.owner, n: amount });
                    }
                    Ok(None)
                }
                Some(other) => Err(format!("bad target {other:?}")),
            }
        }
        StepKind::HandBuffChoice { chooser, options, amount } => {
            // The player picks the card in their hand an effect gives +N strength, for good.
            if options.is_empty() {
                return Ok(None);
            }
            match step.choice {
                None => Ok(Some(Pending { chooser: *chooser, optional: false, mulligan: false, options: Options::Iids(options.clone()) })),
                Some(Choice::Iid(i)) => {
                    let (c, amount) = (*chooser as usize, *amount);
                    if let Some(u) = st.hands[c].iter_mut().find(|u| u.iid == i) {
                        u.strength_mod += amount;
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
                    aim(st, chooser, t);
                    if let Some(top) = st.board.top(t) {
                        if remove_specific(st, t, top.iid, Some(chooser), true) {
                            credit_removal(st, step.by_iid, top.owner);
                        }
                    }
                    Ok(None)
                }
                Some(other) => Err(format!("bad target {other:?}")),
            }
        }
    }
}

// ================================================================== leaders

/// What `player`'s leader's power costs: its price, less what has been taken off it, never below 0.
pub fn power_cost(st: &State, player: Player) -> i32 {
    let price = match st.leaders[player as usize] {
        Some(l) => crate::view::power_price(st.cfg(), &st.card(l).id),
        None => st.cfg().leader_power_cost,
    };
    (price - st.power_discount[player as usize]).max(0)
}

/// Where `player`'s Nightmare is in their deck (an index; the top is the end), when he is there.
fn nightmare_in_deck(st: &State, player: Player) -> Option<usize> {
    let id = st.g.named.raider?;
    st.decks[player as usize].iter().position(|&c| c == id)
}

/// Whether `player`'s Nightmare is on top of their deck: his power then draws him ("Draw Nightmare").
pub fn nightmare_on_top(st: &State, player: Player) -> bool {
    st.leads(player, st.g.named.raider) && st.decks[player as usize].last().copied() == st.g.named.raider && st.g.named.raider.is_some()
}

/// Whether `player`'s leader has a power that would do something now, not used yet this turn; the caller checks the mana.
pub fn leader_usable(st: &State, player: Player) -> bool {
    let Some(lead) = st.leaders[player as usize] else { return false };
    if !crate::cards::has_power(&st.card(lead).id) || st.power_used {
        return false;
    }
    let n = &st.g.named;
    if Some(lead) == n.raider {
        return nightmare_in_deck(st, player).is_some(); // in the deck (on top, the power draws him)
    }
    if Some(lead) == n.angel {
        return st.board.own[player as usize] != 0; // an ally to give +2
    }
    if Some(lead) == n.warlord {
        return n.delicious_food.is_some() && st.g.map.all_tiles() & !st.board.occ != 0; // an empty crossroad
    }
    if Some(lead) == n.assassin {
        return st.played_this_turn > 0 && !st.hands[player as usize].is_empty(); // a card to give it to, and something to give
    }
    if Some(lead) == n.pyromancer {
        return n.fireballs.iter().all(|f| f.is_some());
    }
    true // a draw: from an empty deck too, where it costs food (fatigue)
}

/// The Fireball the Pyromancer's power gives now: Baby, then a step up after every 3 uses, Elder at most.
pub fn pyro_fireball(st: &State, player: Player) -> Option<CardId> {
    let per = st.cfg().pyro_uses_per_upgrade.max(1);
    let stage = (st.power_uses[player as usize] / per).clamp(0, 3) as usize;
    st.g.named.fireballs[stage]
}

/// Nightmare at Dusk: "Gain +1 strength.", wherever he is.
pub fn grow_leeroy(st: &mut State, player: Player) {
    if st.leads(player, st.g.named.raider) {
        st.leeroy_growth[player as usize] += st.cfg().leeroy_growth;
    }
}

/// `player` uses their leader's power (the caller has paid for it).
pub fn do_leader(st: &mut State, player: Player) -> Result<(), String> {
    let Some(lead) = st.leaders[player as usize] else { return Err(format!("{} has no leader", pname(player))) };
    st.emit(Ev::LeaderPower { player, card: lead });
    st.power_used = true;
    let p = player as usize;
    let g = st.g.clone();
    let n = &g.named;
    if Some(lead) == n.sage || Some(lead) == n.reno {
        // "Draw a card." (Reno's passive may make it a Scout)
        st.effect_stack.push(Step::by(StepKind::Draw { player, n: 1 }, lead));
    } else if Some(lead) == n.raider {
        // "Swap Nightmare with the card above."; on top, the power draws him
        match nightmare_in_deck(st, player) {
            Some(i) if i + 1 < st.decks[p].len() => st.decks[p].swap(i, i + 1), // the deck's top is its end
            Some(_) => {
                let drawn = st.draw(player, 1);
                if st.events.on {
                    st.emit(Ev::Draw { player, cards: drawn.iter().map(|u| (u.iid, u.card)).collect() });
                }
                burn_over_limit(st, player, &drawn);
            }
            None => {}
        }
    } else if Some(lead) == n.elf {
        // "Gain 1 food for each region you control."
        let amount = st.cfg().elf_power_food_per_region * count(st, player, Count::Region);
        st.effect_stack.push(Step::by(StepKind::GainFood { player, amount }, lead));
    } else if Some(lead) == n.angel {
        // "Give an ally +2 strength."
        let mut options = Tiles::new();
        let mut m = st.board.own[p];
        while m != 0 {
            let t = m.trailing_zeros() as Tile;
            m &= m - 1;
            options.push(t);
        }
        let amount = st.cfg().angel_power_buff;
        st.effect_stack.push(Step::by(StepKind::BuffChoice { chooser: player, options, amount }, lead));
    } else if Some(lead) == n.assassin {
        // "Give a card in your hand +1 strength for each card you played this turn."
        let amount = st.cfg().rogue_power_per_card * st.played_this_turn;
        let options = st.hands[p].iter().map(|u| u.iid).collect();
        st.effect_stack.push(Step::by(StepKind::HandBuffChoice { chooser: player, options, amount }, lead));
    } else if Some(lead) == n.pyromancer {
        // "Add a Fireball to your hand.", the one this many uses have upgraded it to
        let f = pyro_fireball(st, player).ok_or("no Fireball in the card table")?;
        make_into_hand(st, player, f, 1, 0);
    } else if Some(lead) == n.warlord {
        // "Summon Delicious Food on a random empty crossroad.": the player's own, landing as an effect puts it (no Roar)
        let food = n.delicious_food.ok_or("no Delicious Food in the card table")?;
        let free = st.g.map.all_tiles() & !st.board.occ;
        let tiles: Tiles = (0..64u8).filter(|&t| free >> t & 1 == 1).collect();
        if !tiles.is_empty() {
            let t = tiles[st.rng.randbelow(tiles.len())];
            let unit = Unit::new(food, player, st.new_iid());
            land_unit(st, player, unit, t);
        }
    } else if Some(lead) == n.mana_eater {
        // "Next turn, gain 2 more mana."
        st.next_mana[p] += st.cfg().mana_eater_power_mana;
    } else {
        return Err(format!("{:?} has no power to use", st.g.cards.name_of(lead)));
    }
    st.power_uses[p] += 1;
    Ok(())
}

/// New copies of `card` into `player`'s hand, made by an effect both players watched, each with `strength_mod` for good;
/// past the hand limit they burn, as a draw does.
fn make_into_hand(st: &mut State, player: Player, card: CardId, n: i32, strength_mod: i32) {
    let mut made: SmallVec<[Unit; 4]> = SmallVec::new();
    for _ in 0..n {
        let inst = Unit { made: true, strength_mod, ..Unit::new(card, player, st.new_iid()) };
        st.hands[player as usize].push(inst);
        st.made[player as usize].push(card);
        made.push(inst);
    }
    if st.events.on {
        st.emit(Ev::Draw { player, cards: made.iter().map(|u| (u.iid, u.card)).collect() });
    }
    burn_over_limit(st, player, &made);
}
