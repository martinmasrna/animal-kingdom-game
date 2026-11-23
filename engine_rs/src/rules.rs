//! The rules: legal actions, applying an action, the turn, food and the end of the game.
//!
//! A turn: on a player's Nth own turn they have min(N, mana_cap) mana. They play cards from hand, each for its cost, and
//! their leader's power for its price, until they end the turn (never ended for them). At its end every region they hold
//! pays its food. The map's win_food wins; a player whose food drops to 0 loses.

use crate::actions::Action;
use crate::data::*;
use crate::effects;
use crate::events::Ev;
use crate::state::*;

// ------------------------------------------------------------------ legal actions

/// Every legal action for the player to act; ending the turn only when nothing else is (it is legal whenever `can_pass`
/// says so). Empty once the game is over.
pub fn legal_actions(st: &State) -> Vec<Action> {
    let mut out = Vec::new();
    legal_actions_into(st, &mut out);
    out
}

/// The same, into `out` (cleared first): a search reuses one list for every position it follows.
pub fn legal_actions_into(st: &State, out: &mut Vec<Action>) {
    out.clear();
    if is_terminal(st).is_some() {
        return;
    }
    if let Some(p) = &st.pending {
        match &p.options {
            Options::Iids(v) => out.extend(v.iter().map(|&i| Action::Choice(Choice::Iid(i)))),
            Options::Tiles(v) => out.extend(v.iter().map(|&t| Action::Choice(Choice::Tile(t)))),
            Options::Deck(n) => out.extend((0..*n).map(|k| Action::Choice(Choice::Deck(k)))),
        }
        if p.optional {
            out.push(Action::Choice(Choice::Skip));
        }
        return;
    }
    plays(st, st.current, out);
    if out.is_empty() {
        out.push(Action::Pass);
    }
}

/// Ending the turn is legal whenever nothing is resolving.
pub fn can_pass(st: &State) -> bool {
    is_terminal(st).is_none() && st.pending.is_none() && st.effect_stack.is_empty()
}

/// Every play from hand the mana left pays for, and the leader's power while it pays for that.
fn plays(st: &State, player: Player, out: &mut Vec<Action>) {
    let left = mana_left(st, player);
    effects::legal_placements(st, player, left, out);
    if left >= effects::power_cost(st, player) && effects::leader_usable(st, player) {
        out.push(Action::Leader);
    }
}

/// Which of `player`'s own turns is the current one if it is theirs, else their next: 1 for their first.
pub fn own_turn_number(st: &State, player: Player) -> i32 {
    (st.turn_counter + if player == st.current { 0 } else { 1 }) / 2 + 1
}

/// `player`'s mana this turn if it is theirs, else at the start of their next.
pub fn mana_total(st: &State, player: Player) -> i32 {
    own_turn_number(st, player).min(st.cfg().mana_cap)
}

/// The mana `player` has left: this turn's unspent mana, or all of their next turn's while it isn't theirs.
pub fn mana_left(st: &State, player: Player) -> i32 {
    let total = mana_total(st, player);
    if player == st.current { total - st.mana_spent } else { total }
}

// ------------------------------------------------------------------ the mulligan, both at once

/// Where `player`'s mulligan waits under the one being chosen now, if it does: both players mulligan at once, though
/// the stack resolves one step at a time. Its index on the effect stack.
pub fn early_mulligan(st: &State, player: Player) -> Option<usize> {
    let p = st.pending.as_ref()?;
    if !p.mulligan || p.chooser == player {
        return None;
    }
    let below = st.effect_stack.len().saturating_sub(1);
    st.effect_stack[..below].iter().position(|s| matches!(s.kind, StepKind::Mulligan { player: q, .. } if q == player))
}

fn is_mulligan_of(step: &Step, player: Player) -> bool {
    matches!(step.kind, StepKind::Mulligan { player: q, .. } if q == player)
}

/// Apply `player`'s mulligan choice while the other player is still choosing theirs: their step comes to the top, takes
/// the choice, and goes back under the other's if it isn't done.
pub fn apply_early_mulligan(st: &mut State, player: Player, action: &Action) -> Result<(), String> {
    let Some(i) = early_mulligan(st, player) else { return Err("not your decision".into()) };
    let waiting = st.pending.clone();
    let step = st.effect_stack.remove(i);
    st.effect_stack.push(step);
    st.pending = Some(Pending {
        chooser: player,
        optional: true,
        mulligan: true,
        options: Options::Iids(st.hands[player as usize].iter().map(|u| u.iid).collect()),
    });
    if let Err(e) = apply_action(st, action, true) {
        if let Some(at) = st.effect_stack.iter().rposition(|s| is_mulligan_of(s, player)) {
            let step = st.effect_stack.remove(at);
            st.effect_stack.insert(i.min(st.effect_stack.len()), step);
        }
        st.pending = waiting;
        return Err(e);
    }
    let more = st.pending.as_ref().map_or(false, |p| p.chooser == player) && st.effect_stack.last().map_or(false, |s| is_mulligan_of(s, player));
    if more {
        // more to choose: back under
        let step = st.effect_stack.pop().unwrap();
        st.effect_stack.insert(i, step);
        st.pending = waiting;
    }
    Ok(())
}

/// Apply one action as a game log records it: one marked "by" a player is their mulligan choice made while the other
/// was choosing theirs.
pub fn apply_logged(st: &mut State, action: &Action, by: Option<Player>) -> Result<(), String> {
    match by {
        Some(p) if early_mulligan(st, p).is_some() => apply_early_mulligan(st, p, action),
        _ => apply_action(st, action, true),
    }
}

// ------------------------------------------------------------------ apply

/// Apply one action (a play, the leader's power, ending the turn, or a pending choice). An Err unless it is legal; a bot
/// applying an action it just drew from `legal_actions` passes validate = false.
pub fn apply_action(st: &mut State, action: &Action, validate: bool) -> Result<(), String> {
    if is_terminal(st).is_some() {
        return Err("cannot act: the game is over".into());
    }
    if let Action::Pass = action {
        if !can_pass(st) {
            return Err("cannot end the turn mid-resolution".into());
        }
        return end_turn(st);
    }
    if validate && !legal_actions(st).contains(action) {
        return Err(format!("illegal action {}", action.to_json(&st.g)));
    }
    st.applied_this_turn += 1;
    if st.pending.is_some() {
        // record the choice on the paused step; it resolves on below
        let Action::Choice(c) = action else { return Err(format!("unexpected action {}", action.to_json(&st.g))) };
        st.effect_stack.last_mut().ok_or("a choice with nothing waiting on it")?.choice = Some(*c);
        st.pending = None;
    } else {
        match *action {
            Action::Place { card, target } => {
                st.mana_spent += effects::mana_cost(st, card, st.current);
                effects::do_placement(st, st.current, card, target)?;
            }
            Action::Leader => {
                st.mana_spent += effects::power_cost(st, st.current);
                effects::do_leader(st, st.current)?;
            }
            _ => return Err(format!("unexpected action {}", action.to_json(&st.g))),
        }
    }
    effects::resolve(st)?;
    // The turn's caps: past either the turn ends at once, whatever is still resolving (a loop of effects).
    let over_effects = st.effect_steps_this_turn > st.cfg().max_effect_steps_per_turn;
    if (over_effects || st.applied_this_turn >= st.cfg().max_actions_per_turn) && st.result.is_none() {
        if !over_effects {
            let cards = effects::stack_cards(st, None);
            effects::record_cap(st, CapKind::Actions, cards);
        }
        st.pending = None;
        st.effect_stack.clear();
        effects::remove_buried(st); // the cover's own removal was among what the cap dropped
        end_turn(st)?;
    }
    Ok(())
}

fn end_turn(st: &mut State) -> Result<(), String> {
    let player = st.current;
    st.emit(Ev::TurnEnd { player });
    effects::gain_food(st, player, region_income(st, player), true);
    if st.result.is_some() {
        return Ok(());
    }
    st.turn_counter += 1;
    st.mana_spent = 0;
    st.applied_this_turn = 0;
    st.played_this_turn = 0;
    st.food_lost = [0, 0];
    st.power_used = false;
    st.effect_steps_this_turn = 0;
    st.current = other(player);
    st.emit(Ev::TurnStart { player: st.current, turn: st.turn_counter });
    effects::draw_cards(st, st.current, st.cfg().turn_draw_count); // the turn's free card
    if st.result.is_some() {
        return Ok(()); // fatigue took their last food
    }
    effects::start_of_turn(st, st.current);
    effects::resolve(st)?;
    if st.result.is_none() {
        st.result = is_terminal(st); // the turn limit: the game is over, and the position says so
    }
    Ok(())
}

// ------------------------------------------------------------------ regions, food, the end

/// The food `player`'s regions pay at the end of their turn: each its own, and 1 more each while a card that says
/// "Your regions produce 1 more food." (the Elf's) is theirs on the board.
pub fn region_income(st: &State, player: Player) -> i32 {
    let own = st.board.own[player as usize];
    let (mut food, mut held) = (0, 0);
    for r in &st.g.map.regions {
        if r.mask & own == r.mask {
            food += r.food;
            held += 1;
        }
    }
    if held == 0 {
        return 0;
    }
    let mut bonus = 0;
    let mut m = own;
    while m != 0 {
        let t = m.trailing_zeros() as Tile;
        m &= m - 1;
        if st.card(st.board.top(t).unwrap().card).beh.region_bonus {
            bonus = st.cfg().elf_card_region_bonus;
            break;
        }
    }
    food + bonus * held
}

/// The game's result if it is over (the turn limit ends it on food).
pub fn is_terminal(st: &State) -> Option<GameResult> {
    if st.result.is_some() {
        return st.result;
    }
    if st.turn_counter >= st.cfg().max_turns {
        let (a, b) = (st.food[0], st.food[1]);
        let winner = if a > b { Some(0) } else if b > a { Some(1) } else { None };
        return Some(GameResult { winner, reason: Reason::MaxTurns });
    }
    None
}
