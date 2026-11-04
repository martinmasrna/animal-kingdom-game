//! The rules (engine/rules.py): legal actions, applying one, the turn structure, income and the win conditions.

use crate::actions::{Action, Target};
use crate::data::*;
use crate::effects;
use crate::state::{mulligan_request, GameResult, State};
use crate::statics;
use crate::value::m_get_s;
use serde_json as sj;

pub const TITAN_ACTIONS: i32 = 2;

pub fn legal_actions(st: &State) -> Vec<Action> {
    if st.decided() {
        return Vec::new();
    }
    if st.pending.is_some() {
        return effects::legal_pending(st);
    }
    top_level_actions(st)
}

pub fn can_pass(st: &State) -> bool {
    st.result.is_none() && st.pending.is_none() && st.effect_stack.is_empty()
}

fn top_level_actions(st: &State) -> Vec<Action> {
    let player = st.current;
    let left = actions_left(st);
    if left <= 0 {
        return if effects::free_roams_left(st, player, None) > 0 { effects::legal_roams(st, player, true) } else { Vec::new() };
    }
    let mut actions = Vec::new();
    if !st.decks[player as usize].is_empty() {
        actions.push(Action::Draw);
    }
    let titan_ok = left >= titan_cost(st, player) && st.food[player.min(1) as usize] >= titan_food(st, player);
    actions.extend(effects::legal_placements(st, player, None, titan_ok));
    actions.extend(effects::legal_roams(st, player, false));
    actions
}

fn has_top_level_action(st: &State) -> bool {
    if actions_left(st) > 0 && !st.decks[st.current as usize].is_empty() {
        return true;
    }
    !top_level_actions(st).is_empty()
}

/// Two actions; one after a Krill this turn, or while the legendary Krill is yours. As in Python.
pub fn titan_cost(st: &State, player: Player) -> i32 {
    let cheap = st.turn_flags.titan_discount[player.min(1) as usize] || statics::controls(st, player, st.card_id("krill_legend"));
    if cheap { TITAN_ACTIONS - 1 } else { TITAN_ACTIONS }
}

/// The legendary Krill's food for a Titan; none when a common Krill already made this one cost one action.
pub fn titan_food(st: &State, player: Player) -> i32 {
    if st.turn_flags.titan_discount[player.min(1) as usize] || !statics::controls(st, player, st.card_id("krill_legend")) {
        return 0;
    }
    st.cfg().int("krill_legend_food")
}

pub fn turn_actions(st: &State) -> i32 {
    let base = if st.turn_counter == 0 { st.cfg().first_turn_actions } else { st.cfg().actions_per_turn };
    let p = st.current.min(1) as usize;
    let total = base + st.turn_flags.bonus_actions[p];
    match st.turn_flags.action_cap[p] {
        Some(cap) => total.min(cap),
        None => total,
    }
}

fn actions_left(st: &State) -> i32 {
    turn_actions(st) - st.actions_taken_this_turn
}

// ------------------------------------------------------------- apply / resolve

/// Where `player`'s mulligan waits under the one being chosen now: its index on the effect stack, else None.
pub fn early_mulligan(st: &State, player: Player) -> Option<usize> {
    let p = st.pending.as_ref()?;
    if m_get_s(p, "kind") != Some("mulligan") || m_get_s(p, "chooser") == Some(player_name(player)) {
        return None;
    }
    let n = st.effect_stack.len();
    (0..n.saturating_sub(1)).find(|&i| m_get_s(&st.effect_stack[i], "op") == Some("mulligan") && m_get_s(&st.effect_stack[i], "player") == Some(player_name(player)))
}

pub fn apply_early_mulligan(st: &mut State, player: Player, action: &Action) -> Result<(), String> {
    let i = early_mulligan(st, player).ok_or("not your decision")?;
    let waiting = st.pending.clone();
    let step = st.effect_stack.remove(i);
    let step_key = step.clone();
    st.effect_stack.push(step);
    st.pending = Some(mulligan_request(st, player));
    if let Err(e) = apply_action(st, action, true) {
        // restore: the step back where it was, the other's request pending as before
        if let Some(pos) = st.effect_stack.iter().rposition(|s| *s == step_key) {
            let s = st.effect_stack.remove(pos);
            st.effect_stack.insert(i.min(st.effect_stack.len()), s);
        }
        st.pending = waiting;
        return Err(e);
    }
    let still_mine = st.pending.as_ref().map(|p| m_get_s(p, "chooser") == Some(player_name(player))).unwrap_or(false);
    let top_is_step = st.effect_stack.last().map(|s| m_get_s(s, "op") == Some("mulligan") && m_get_s(s, "player") == Some(player_name(player))).unwrap_or(false);
    if still_mine && top_is_step {
        let s = st.effect_stack.pop().unwrap();
        st.effect_stack.insert(i.min(st.effect_stack.len()), s);
        st.pending = waiting;
    }
    Ok(())
}

/// Apply one action as a game log records it.
pub fn apply_logged(st: &mut State, adict: &sj::Value) -> Result<(), String> {
    let action = Action::from_json(st, adict)?;
    if let Some(by) = adict.get("by").and_then(|b| b.as_str()) {
        let by = player_from(by);
        if early_mulligan(st, by).is_some() {
            return apply_early_mulligan(st, by, &action);
        }
    }
    apply_action(st, &action, true)
}

pub fn apply_action(st: &mut State, action: &Action, validate: bool) -> Result<(), String> {
    if st.decided() {
        return Err("cannot act: the game is over".into());
    }
    if let Action::Pass = action {
        if !can_pass(st) {
            return Err("cannot end the turn mid-resolution".into());
        }
        end_turn(st);
        return Ok(());
    }
    let action = match action {
        Action::Place { .. } => {
            let chooser = st.player_to_act();
            effects::canonical_place(st, chooser, action)
        }
        _ => action.clone(),
    };
    if validate && !legal_actions(st).contains(&action) {
        return Err(format!("illegal action {}", action.to_json(st)));
    }
    if st.pending.is_some() {
        effects::apply_pending(st, &action);
    } else {
        match &action {
            Action::Draw => {
                st.actions_taken_this_turn += 1;
                let n = st.cfg().draw_action_count;
                let cur = st.current;
                effects::draw_cards(st, cur, n);
            }
            Action::Place { card, target, iid } => {
                let titan = st.card(*card).has_kw(K_TITAN);
                let cur = st.current;
                st.actions_taken_this_turn += if titan { titan_cost(st, cur) } else { 1 };
                if titan {
                    let food = titan_food(st, cur);
                    if food > 0 {
                        let krill = st.card_id("krill_legend");
                        effects::lose_food(st, cur, food, krill);
                    }
                    st.turn_flags.titan_discount[cur.min(1) as usize] = false;
                }
                effects::do_placement(st, cur, *card, target, *iid)?;
            }
            Action::Roam { origin, target } => {
                let cur = st.current;
                let top = st.top(*origin).cloned();
                effects::pay_for_roam(st, cur, top.as_ref());
                effects::do_roam(st, cur, *origin, target, false)?;
            }
            _ => return Err("unexpected action".into()),
        }
    }
    resolve_and_maybe_end_turn(st);
    Ok(())
}

fn resolve_and_maybe_end_turn(st: &mut State) {
    effects::resolve(st);
    if st.decided() {
        return;
    }
    if !st.effect_stack.is_empty() || st.pending.is_some() {
        return;
    }
    if has_top_level_action(st) {
        return;
    }
    end_turn(st);
}

fn end_turn(st: &mut State) {
    let player = st.current;
    crate::emit!(st, "turn_end", crate::vmap!("player" => effects::pn(player)));
    effects::end_of_turn(st, player);
    effects::resolve(st);
    if st.decided() {
        return;
    }
    produce_food(st, player);
    if st.decided() {
        return;
    }
    let acted = st.actions_taken_this_turn != 0 || st.turn_flags.roams[player.min(1) as usize] != 0;
    st.idle_turns = if acted { 0 } else { st.idle_turns + 1 };
    if st.idle_turns >= 2 {
        st.result = Some(resolve_passes(st));
        return;
    }
    st.turn_counter += 1;
    st.units_placed_this_turn = 0;
    st.actions_taken_this_turn = 0;
    st.turn_flags = crate::state::TurnFlags::default();
    st.current = other(player);
    let (cur, t) = (st.current, st.turn_counter);
    crate::emit!(st, "turn_start", crate::vmap!("player" => effects::pn(cur), "turn" => crate::value::Value::Int(t as i64)));
    effects::start_of_turn(st, cur);
    effects::resolve(st);
    if st.result.is_none() && st.pending.is_none() && st.effect_stack.is_empty() && st.turn_counter < st.cfg().max_turns && !has_top_level_action(st) {
        end_turn(st);
    }
}

// ------------------------------------------------------------- regions / food

pub fn region_income(st: &State, player: Player) -> i32 {
    statics::regions_of(st, player).iter().map(|&i| region_yield(st, player, i)).sum()
}

pub fn region_yield(st: &State, player: Player, region: usize) -> i32 {
    (st.map().regions[region].food + statics::region_food_modifier(st, player)).max(0)
}

fn produce_food(st: &mut State, player: Player) {
    let total = region_income(st, player);
    if total != 0 {
        effects::gain_food(st, player, total, true, true);
    }
}

// ------------------------------------------------------------------ terminal

pub fn is_terminal(st: &State) -> Option<GameResult> {
    if let Some(r) = &st.result {
        return Some(r.clone());
    }
    if st.turn_counter >= st.cfg().max_turns {
        return Some(resolve_by_food(st, "max_turns"));
    }
    None
}

fn resolve_passes(st: &State) -> GameResult {
    let (a, b) = (st.food[0], st.food[1]);
    if a > b {
        GameResult { winner: Some(A), reason: "passes".into() }
    } else if b > a {
        GameResult { winner: Some(B), reason: "passes".into() }
    } else {
        GameResult { winner: Some(other(st.current)), reason: "passes".into() }
    }
}

fn resolve_by_food(st: &State, reason: &str) -> GameResult {
    let (a, b) = (st.food[0], st.food[1]);
    if a > b {
        GameResult { winner: Some(A), reason: reason.into() }
    } else if b > a {
        GameResult { winner: Some(B), reason: reason.into() }
    } else {
        GameResult { winner: None, reason: reason.into() }
    }
}

pub fn target_name(st: &State, t: &Target) -> String {
    match t {
        Target::Cr(c) => st.crname(*c).to_string(),
        Target::Hq(p) => format!("den {}", player_name(*p)),
    }
}
