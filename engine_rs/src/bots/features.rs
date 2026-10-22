//! The evaluation (bots/features.py and bots/greedy_bot.py's evaluate): the hand-written terms with their weights,
//! the rung-0/1/2 feature vector for the learned evaluators, and the position helpers the bots share
//! (roar_fizzled, enabled_roar_ids, opponent_lethal_next_turn). Term bodies and the order of every floating-point sum
//! follow the Python so a position scores to the same bits.

use serde_json as sj;

use crate::actions::{Action, Target};
use crate::data::*;
use crate::effects;
use crate::rules;
use crate::state::{State, Unit};
use crate::strength::{aura_sources, effective_strength};
use crate::value::{m_get_i, m_get_s, Value};

pub const T_NORM: f64 = 13.0;
pub const DECK_NORM: f64 = 30.0;
pub const TOTAL_CARDS_NORM: f64 = 60.0;
pub const HQ_DIST_CAP: i32 = 12;
pub const HAND_RANK_WEIGHTS: [f64; 6] = [1.0, 1.0, 1.0, 1.0, 1.0, 0.5];
pub const HAND_CARD_BONUS: f64 = 0.5;
pub const HAND_UNSEEN_CARD: f64 = 3.0;

#[derive(Clone, Debug)]
pub struct Weights {
    pub food_progress: f64,
    pub food_proximity: f64,
    pub food_curve: f64,
    pub food_race: bool,
    pub board_presence: f64,
    pub connection: f64,
    pub region_control: f64,
    pub region_hold: f64,
    pub enemy_hq_threat: f64,
    pub own_hq_threat: f64,
    pub hq_threat_reach: f64,
    pub card_economy: f64,
    pub effect_readiness: f64,
    pub pending_payoff: f64,
    pub buried_presence: f64,
    pub pending_alive: f64,
    pub pending_target: f64,
    pub coverage_exposure: f64,
    pub readiness_cap: i32,
    pub hand_value: f64,
    pub hand_ranks: Vec<f64>,
    pub wasted_roar: f64,
}

impl Default for Weights {
    fn default() -> Weights {
        Weights {
            food_progress: 1.0,
            food_proximity: 30.0,
            food_curve: 1.0,
            food_race: false,
            board_presence: 0.5,
            connection: 1.0,
            region_control: 2.0,
            region_hold: 0.0,
            enemy_hq_threat: 40.0,
            own_hq_threat: 40.0,
            hq_threat_reach: 0.0,
            card_economy: 0.0,
            effect_readiness: 0.0,
            pending_payoff: 20.0,
            buried_presence: 0.0,
            pending_alive: 0.0,
            pending_target: 0.0,
            coverage_exposure: 0.0,
            readiness_cap: 0,
            hand_value: 1.0,
            hand_ranks: HAND_RANK_WEIGHTS.to_vec(),
            wasted_roar: 8.0,
        }
    }
}

impl Weights {
    /// Set one field from a `w.<name>=<value>` spec override.
    pub fn set(&mut self, name: &str, v: &sj::Value) -> Result<(), String> {
        let f = |v: &sj::Value| -> Result<f64, String> {
            match v {
                sj::Value::Number(n) => Ok(n.as_f64().unwrap()),
                sj::Value::Bool(b) => Ok(*b as i32 as f64),
                _ => Err(format!("weight {name} needs a number, got {v}")),
            }
        };
        match name {
            "food_progress" => self.food_progress = f(v)?,
            "food_proximity" => self.food_proximity = f(v)?,
            "food_curve" => self.food_curve = f(v)?,
            "food_race" => self.food_race = v.as_bool().unwrap_or(f(v)? != 0.0),
            "board_presence" => self.board_presence = f(v)?,
            "connection" => self.connection = f(v)?,
            "region_control" => self.region_control = f(v)?,
            "region_hold" => self.region_hold = f(v)?,
            "enemy_hq_threat" => self.enemy_hq_threat = f(v)?,
            "own_hq_threat" => self.own_hq_threat = f(v)?,
            "hq_threat_reach" => self.hq_threat_reach = f(v)?,
            "card_economy" => self.card_economy = f(v)?,
            "effect_readiness" => self.effect_readiness = f(v)?,
            "pending_payoff" => self.pending_payoff = f(v)?,
            "buried_presence" => self.buried_presence = f(v)?,
            "pending_alive" => self.pending_alive = f(v)?,
            "pending_target" => self.pending_target = f(v)?,
            "coverage_exposure" => self.coverage_exposure = f(v)?,
            "readiness_cap" => self.readiness_cap = f(v)? as i32,
            "hand_value" => self.hand_value = f(v)?,
            "wasted_roar" => self.wasted_roar = f(v)?,
            _ => return Err(format!("unknown weight {name:?}")),
        }
        Ok(())
    }
}

// ------------------------------------------------------------------ terms

pub fn food_terms(st: &State, me: Player, opp: Player) -> (f64, f64) {
    ((st.food[me as usize] - st.food[opp as usize]) as f64, st.food[me as usize] as f64 / st.map().win_food as f64)
}

pub fn board_presence(st: &State, me: Player) -> f64 {
    let sources = aura_sources(st);
    let mut presence = 0.0;
    for (_, top) in st.tops() {
        let s = effective_strength(st, top, Some(&sources)) as f64;
        presence += if top.owner == me { s } else { -s };
    }
    presence
}

/// (food, mine fraction, theirs fraction) per region, in map order.
pub fn region_fractions(st: &State, me: Player, opp: Player) -> Vec<(f64, f64, f64)> {
    st.map()
        .regions
        .iter()
        .map(|r| {
            let n = r.corners.len() as f64;
            let mut mine = 0;
            let mut theirs = 0;
            for &c in &r.corners {
                match st.owner_of(c) {
                    Some(o) if o == me => mine += 1,
                    Some(o) if o == opp => theirs += 1,
                    _ => {}
                }
            }
            (r.food as f64, mine as f64 / n, theirs as f64 / n)
        })
        .collect()
}

pub fn region_control(fractions: &[(f64, f64, f64)]) -> f64 {
    let mut region = 0.0;
    for &(food, mine, theirs) in fractions {
        region += food * (mine.powf(3.0) - theirs.powf(3.0));
    }
    region
}

fn comb(n: u64, k: u64) -> f64 {
    if k > n {
        return 0.0;
    }
    let k = k.min(n - k);
    let mut r: u128 = 1;
    for i in 0..k {
        r = r * (n - i) as u128 / (i + 1) as u128;
    }
    r as f64
}

pub fn opponent_unseen(st: &State, opp: Player) -> Vec<CardId> {
    let mut ids: Vec<CardId> = st.hands[opp as usize].iter().map(|u| u.card).collect();
    ids.extend(st.decks[opp as usize].iter().copied());
    ids
}

pub fn p_opponent_can_cover(st: &State, opp: Player, defender_strength: i32) -> f64 {
    let unseen = opponent_unseen(st, opp);
    let n = unseen.len() as u64;
    let h = st.hands[opp as usize].len() as u64;
    if n == 0 || h == 0 {
        return 0.0;
    }
    let k = unseen.iter().filter(|c| st.card(**c).base.map(|b| b > defender_strength).unwrap_or(false)).count() as u64;
    if k == 0 {
        return 0.0;
    }
    if k > n - h {
        return 1.0;
    }
    1.0 - comb(n - k, h) / comb(n, h)
}

pub fn held_region_control(st: &State, me: Player, opp: Player) -> f64 {
    let unseen = opponent_unseen(st, opp);
    let n_unseen = unseen.len() as u64;
    let h_opp = st.hands[opp as usize].len() as u64;
    let mut their_strengths: Vec<i32> = unseen.iter().filter_map(|c| st.card(*c).base).collect();
    their_strengths.sort();
    let my_best = st.hands[me as usize].iter().filter(|u| st.card(u.card).base.is_some()).map(|u| effective_strength(st, u, None)).max().unwrap_or(-1);
    let sources = aura_sources(st);
    let mut region = 0.0;
    for r in &st.map().regions {
        let n = r.corners.len() as f64;
        let mut mine = 0.0;
        let mut theirs = 0.0;
        for &cr in &r.corners {
            let Some(top) = st.top(cr) else { continue };
            if top.owner == me {
                let mut hold = 1.0;
                if n_unseen > 0 && h_opp > 0 {
                    let s = effective_strength(st, top, Some(&sources));
                    let k = their_strengths.iter().filter(|x| **x > s).count() as u64;
                    if k > 0 {
                        hold = if k <= n_unseen - h_opp { comb(n_unseen - k, h_opp) / comb(n_unseen, h_opp) } else { 0.0 };
                    }
                }
                mine += hold;
            } else if top.owner == opp {
                let covered = my_best > effective_strength(st, top, Some(&sources));
                theirs += if covered { 0.0 } else { 1.0 };
            }
        }
        region += r.food as f64 * ((mine / n).powf(3.0) - (theirs / n).powf(3.0));
    }
    region
}

fn reachable_front(st: &State, attacker: Player, defender: Player, connection: u32) -> i32 {
    let gm = st.map();
    let cut: Vec<Cr> = gm.front(defender).iter().copied().filter(|&cr| connection & (1 << cr) == 0 && st.owner_of(cr) == Some(attacker)).collect();
    if cut.is_empty() {
        return 0;
    }
    let mut count = 0;
    for front in cut {
        let mut group: u32 = 1 << front;
        let mut queue = vec![front];
        while let Some(cr) = queue.pop() {
            for &nb in gm.neighbors(cr) {
                if group & (1 << nb) == 0 && st.owner_of(nb) == Some(attacker) {
                    group |= 1 << nb;
                    queue.push(nb);
                }
            }
        }
        for cr in 0..gm.n() as Cr {
            if group & (1 << cr) == 0 {
                continue;
            }
            let mut hit = false;
            for &nb in gm.neighbors(cr) {
                if st.occupied(nb) {
                    continue;
                }
                if gm.in_front(attacker, nb) || gm.neighbors(nb).iter().any(|&x| connection & (1 << x) != 0) {
                    hit = true;
                    break;
                }
            }
            if hit {
                count += 1;
                break;
            }
        }
    }
    count
}

pub fn hq_threat_terms(st: &State, me: Player, opp: Player, my_connection: u32, opp_connection: u32, reach: f64) -> (f64, f64) {
    let gm = st.map();
    let mut enemy = gm.front(opp).iter().filter(|&&cr| my_connection & (1 << cr) != 0).count() as f64;
    let mut own = gm.front(me).iter().filter(|&&cr| opp_connection & (1 << cr) != 0).count() as f64;
    if reach != 0.0 {
        enemy += reach * reachable_front(st, me, opp, my_connection) as f64;
        own += reach * reachable_front(st, opp, me, opp_connection) as f64;
    }
    (enemy, own)
}

pub fn coverage_exposure_worst(st: &State, me: Player, opp: Player, opp_connection: u32) -> f64 {
    let mut worst = 0.0f64;
    for &cr in st.map().front(me) {
        if let Some(top) = st.top(cr) {
            if top.owner == me && st.is_connected(opp, cr, opp_connection) {
                let p = p_opponent_can_cover(st, opp, effective_strength(st, top, None));
                worst = worst.max(p);
            }
        }
    }
    worst
}

pub fn card_economy(st: &State, me: Player, opp: Player) -> f64 {
    (st.hands[me as usize].len() as i64 - st.hands[opp as usize].len() as i64) as f64
}

pub fn hand_value(st: &State, me: Player, opp: Player, ranks: &[f64]) -> f64 {
    let mut vals: Vec<f64> = st.hands[me as usize].iter().map(|u| 0.5 * effective_strength(st, u, None) as f64 + 1.0).collect();
    vals.sort_by(|a, b| b.partial_cmp(a).unwrap());
    let mut mine = 0.0;
    for (w, v) in ranks.iter().zip(vals.iter()) {
        mine += w * v;
    }
    mine += HAND_CARD_BONUS * vals.len() as f64;
    let n = st.hands[opp as usize].len();
    let mut theirs = 0.0;
    for w in ranks.iter().take(n) {
        theirs += w * HAND_UNSEEN_CARD;
    }
    theirs += HAND_CARD_BONUS * n as f64;
    mine - theirs
}

fn timer_alive(st: &State, s: &crate::value::Map) -> bool {
    let iid = m_get_i(s, "iid");
    for &cr in &st.order {
        let stack = &st.stacks[cr as usize];
        for (k, u) in stack.iter().enumerate() {
            if Some(u.iid) == iid {
                return k + 1 == stack.len() || crate::value::m_flag(s, "while_buried");
            }
        }
    }
    false
}

pub fn pending_payoff(st: &State, me: Player, alive_only: bool) -> f64 {
    let mut pending = 0.0;
    for s in &st.scheduled {
        if alive_only && !timer_alive(st, s) {
            continue;
        }
        let owner = m_get_s(s, "owner").unwrap_or("");
        let remaining = m_get_i(s, "remaining").unwrap_or(0).max(0);
        let horizon = 2 * remaining - if player_name(st.current) == owner { 0 } else { 1 };
        let disc = 1.0 / (1.0 + horizon.max(0) as f64);
        pending += if owner == player_name(me) { disc } else { -disc };
    }
    pending
}

pub fn pending_target_strength(st: &State, me: Player) -> f64 {
    let mut total = 0.0;
    for s in &st.scheduled {
        let Some(step) = s.get("step").and_then(|x| x.as_map()) else { continue };
        if m_get_s(step, "op") != Some("remove_iid") {
            continue;
        }
        let Some(iid) = m_get_i(step, "iid") else { continue };
        let Some(target) = st.unit_by_iid(iid) else { continue };
        let owner = m_get_s(s, "owner").unwrap_or("");
        if player_name(target.owner) == owner {
            continue;
        }
        let remaining = m_get_i(s, "remaining").unwrap_or(0).max(0);
        let horizon = 2 * remaining - if player_name(st.current) == owner { 0 } else { 1 };
        let value = effective_strength(st, target, None) as f64 / (1.0 + 0.25 * horizon.max(0) as f64);
        total += if owner == player_name(me) { value } else { -value };
    }
    total
}

pub fn buried_presence(st: &State, me: Player) -> f64 {
    let mut total = 0.0;
    for &cr in &st.order {
        let stack = &st.stacks[cr as usize];
        for u in &stack[..stack.len() - 1] {
            let s = effective_strength(st, u, None) as f64;
            total += if u.owner == me { s } else { -s };
        }
    }
    total
}

// ------------------------------------------------------------------ roars

fn unit_count(st: &State) -> usize {
    st.order.iter().map(|&c| st.stacks[c as usize].len()).sum()
}

fn total_strength_counters(st: &State) -> i64 {
    let board: i64 = st.order.iter().flat_map(|&c| st.stacks[c as usize].iter().map(|u| u.strength_counter as i64)).sum();
    let hands: i64 = st.hands.iter().flat_map(|h| h.iter().map(|u| u.strength_counter as i64)).sum();
    board + hands
}

/// True if `action` played a card with a Roar and nothing beyond the unit landing happened.
pub fn roar_fizzled(pre: &State, post: &State, me: Player, action: &Action) -> bool {
    let Action::Place { card, target: Target::Cr(_), .. } = action else { return false };
    if !pre.card(*card).has_roar {
        return false;
    }
    let replay;
    let post = if post.current != pre.current || post.turn_counter != pre.turn_counter {
        let mut p = pre.clone();
        p.actions_taken_this_turn -= 1;
        let _ = rules::apply_action(&mut p, action, false);
        replay = p;
        &replay
    } else {
        post
    };
    if post.pending.is_some() {
        return false;
    }
    if post.food != pre.food {
        return false;
    }
    if post.remove_pile.len() != pre.remove_pile.len() {
        return false;
    }
    let opp = other(me);
    if post.hands[me as usize].len() + 1 != pre.hands[me as usize].len() {
        return false;
    }
    if post.hands[opp as usize].len() != pre.hands[opp as usize].len() {
        return false;
    }
    if unit_count(post) != unit_count(pre) + 1 {
        return false;
    }
    if total_strength_counters(post) != total_strength_counters(pre) {
        return false;
    }
    if post.scheduled.len() != pre.scheduled.len() {
        return false;
    }
    true
}

/// The distinct Roars in hand with at least one live legal placement.
pub fn enabled_roar_ids(st: &State, player: Player) -> Vec<CardId> {
    if st.result.is_some() || st.pending.is_some() || st.player_to_act() != player || st.actions_taken_this_turn != 0 {
        return Vec::new();
    }
    let mut roars: Vec<CardId> = Vec::new();
    for u in &st.hands[player as usize] {
        if st.card(u.card).has_roar && !roars.contains(&u.card) {
            roars.push(u.card);
        }
    }
    if roars.is_empty() {
        return Vec::new();
    }
    let placements: Vec<Action> = effects::legal_placements(st, player, Some(&roars), false).into_iter().filter(|a| matches!(a, Action::Place { target: Target::Cr(_), .. })).collect();
    let mut by_card: Vec<(CardId, Vec<Action>)> = Vec::new();
    for a in placements {
        let Action::Place { card, .. } = &a else { continue };
        match by_card.iter_mut().find(|(c, _)| c == card) {
            Some(e) => e.1.push(a),
            None => by_card.push((*card, vec![a])),
        }
    }
    let opponent = other(player);
    let occ = st.connected_occupied(player);
    let cr_of = |a: &Action| match a {
        Action::Place { target: Target::Cr(c), .. } => *c,
        _ => 0,
    };
    let mut representatives: Vec<Action> = Vec::new();
    for (_, actions) in &by_card {
        let tactical: Vec<&Action> = actions.iter().filter(|a| st.owner_of(cr_of(a)) == Some(opponent) || st.map().neighbors(cr_of(a)).iter().any(|&nb| st.owner_of(nb) == Some(opponent))).collect();
        let empty: Vec<&Action> = actions.iter().filter(|a| !st.occupied(cr_of(a))).collect();
        let connected: Vec<&Action> = actions.iter().filter(|a| st.is_connected(player, cr_of(a), occ)).collect();
        let all: Vec<&Action> = actions.iter().collect();
        let mut chosen: Vec<&Action> = Vec::new();
        for group in [tactical, empty, connected, all] {
            if let Some(first) = group.first() {
                if !chosen.contains(first) {
                    chosen.push(first);
                }
            }
        }
        representatives.extend(chosen.into_iter().cloned());
    }
    let mut enabled: Vec<CardId> = Vec::new();
    for action in representatives {
        let Action::Place { card, .. } = &action else { continue };
        if enabled.contains(card) {
            continue;
        }
        let mut nxt = st.clone();
        let _ = rules::apply_action(&mut nxt, &action, false);
        if !roar_fizzled(st, &nxt, player, &action) {
            enabled.push(*card);
        }
    }
    enabled
}

pub fn enabled_roar_count(st: &State, player: Player) -> i32 {
    enabled_roar_ids(st, player).len() as i32
}

pub fn capped(w: &Weights, live: i32) -> i32 {
    if w.readiness_cap != 0 {
        live.min(w.readiness_cap)
    } else {
        live
    }
}

/// True if `opponent` can capture a den on their upcoming turn (public information only).
pub fn opponent_lethal_next_turn(st: &State, opponent: Player) -> bool {
    let me = other(opponent);
    let gm = st.map();
    let opp_connection = st.connected_occupied(opponent);
    let reaches = gm.front(me).iter().any(|&cr| opp_connection & (1 << cr) != 0);
    if !reaches {
        return st.current == opponent
            && st.cfg().actions_per_turn >= 2
            && st.hands[opponent as usize].len() >= 2
            && gm.front(me).iter().any(|&cr| !st.occupied(cr) && gm.neighbors(cr).iter().any(|&nb| opp_connection & (1 << nb) != 0));
    }
    if !st.hands[opponent as usize].is_empty() {
        return true;
    }
    st.cfg().actions_per_turn >= 2 && st.cfg().draw_action_count > 0 && !st.decks[opponent as usize].is_empty()
}

// ------------------------------------------------------------------ evaluate

pub fn evaluate(st: &State, me: Player, w: &Weights) -> f64 {
    let opp = other(me);
    if let Some(r) = &st.result {
        if r.winner == Some(me) {
            return f64::INFINITY;
        }
        if r.winner == Some(opp) {
            return f64::NEG_INFINITY;
        }
        return 0.0;
    }
    let mut score = 0.0;
    let (food_progress, food_proximity) = food_terms(st, me, opp);
    score += w.food_progress * food_progress;
    if w.food_curve != 1.0 || w.food_race {
        let mut proximity = food_proximity.powf(w.food_curve);
        if w.food_race {
            proximity -= (st.food[opp as usize] as f64 / st.map().win_food as f64).powf(w.food_curve);
        }
        score += w.food_proximity * proximity;
    } else {
        score += w.food_proximity * food_proximity;
    }
    score += w.board_presence * board_presence(st, me);
    let my_connection = st.connected_occupied(me);
    score += w.connection * my_connection.count_ones() as f64;
    if w.region_hold != 0.0 {
        let held = held_region_control(st, me, opp);
        let plain = if w.region_hold < 1.0 { region_control(&region_fractions(st, me, opp)) } else { 0.0 };
        score += w.region_control * ((1.0 - w.region_hold) * plain + w.region_hold * held);
    } else {
        score += w.region_control * region_control(&region_fractions(st, me, opp));
    }
    let opp_connection = st.connected_occupied(opp);
    let (enemy_threat, own_threat) = hq_threat_terms(st, me, opp, my_connection, opp_connection, w.hq_threat_reach);
    score += w.enemy_hq_threat * enemy_threat;
    score -= w.own_hq_threat * own_threat;
    if w.coverage_exposure != 0.0 {
        score -= w.coverage_exposure * coverage_exposure_worst(st, me, opp, opp_connection);
    }
    score += w.card_economy * card_economy(st, me, opp);
    if w.effect_readiness != 0.0 {
        score += w.effect_readiness * capped(w, enabled_roar_count(st, me)) as f64;
    }
    if w.hand_value != 0.0 {
        score += w.hand_value * hand_value(st, me, opp, &w.hand_ranks);
    }
    if w.pending_payoff != 0.0 {
        score += w.pending_payoff * pending_payoff(st, me, w.pending_alive != 0.0);
    }
    if w.pending_target != 0.0 {
        score += w.pending_target * pending_target_strength(st, me);
    }
    if w.buried_presence != 0.0 {
        score += w.buried_presence * buried_presence(st, me);
    }
    score
}

// ------------------------------------------------------------------ the feature vector

pub const RUNG0: [&str; 11] = [
    "food_progress", "food_proximity", "board_presence", "connection", "region_control", "enemy_hq_threat", "own_hq_threat",
    "coverage_exposure", "card_economy", "effect_readiness", "pending_payoff",
];
pub const RUNG1_EXTRA: [&str; 13] = [
    "growth_board_diff", "growth_rate_diff", "dynamic_board_diff", "dynamic_fuel", "phase_x_growth", "sched_near_diff", "sched_far_diff",
    "income_diff", "income_x_future", "deck_diff", "phase_x_food", "hq_dist_diff", "flight_hand_expected_diff",
];
pub const RUNG2_EXTRA: [&str; 24] = [
    "to_move", "phase", "hand_mine", "hand_theirs", "hand_roars", "hand_dead_roars", "hand_strength_mean", "hand_strength_max", "hand_small",
    "hand_fliers", "hand_food_cards", "hand_food_affordable", "hand_tag_matches", "units_mine", "units_theirs", "engines_mine", "engines_theirs",
    "board_tag_pairs", "extra_actions_mine", "extra_actions_theirs", "den_front_held", "den_front_pressure", "pending_target_strength",
    "buried_presence",
];

pub fn feature_names(set: &str) -> Vec<&'static str> {
    let mut v: Vec<&str> = RUNG0.to_vec();
    if set == "rung1" || set == "rung2" {
        v.extend(RUNG1_EXTRA);
    }
    if set == "rung2" {
        v.extend(RUNG2_EXTRA);
    }
    v
}

fn growth_board_diff(st: &State, me: Player, opp: Player) -> f64 {
    let mut bm = 0i64;
    let mut bt = 0i64;
    for &c in &st.order {
        for u in &st.stacks[c as usize] {
            if u.owner == me {
                bm += u.strength_counter as i64;
            } else if u.owner == opp {
                bt += u.strength_counter as i64;
            }
        }
    }
    let gm: i64 = st.card_strength_counters[me as usize].values().map(|v| *v as i64).sum();
    let gt: i64 = st.card_strength_counters[opp as usize].values().map(|v| *v as i64).sum();
    ((bm - bt) + (gm - gt)) as f64
}

fn dynamic_board_diff(st: &State, me: Player, opp: Player) -> i32 {
    let mut mine = 0;
    let mut theirs = 0;
    for (_, top) in st.tops() {
        if st.card(top.card).base.is_none() {
            if top.owner == me {
                mine += 1;
            } else if top.owner == opp {
                theirs += 1;
            }
        }
    }
    mine - theirs
}

fn scheduled_horizon_diffs(st: &State, me: Player) -> (f64, f64) {
    let mut near = 0.0;
    let mut far = 0.0;
    for s in &st.scheduled {
        let remaining = m_get_i(s, "remaining").unwrap_or(0).max(0);
        let sign = if m_get_s(s, "owner") == Some(player_name(me)) { 1.0 } else { -1.0 };
        if remaining <= 1 {
            near += sign;
        } else {
            far += sign;
        }
    }
    (near, far)
}

fn income_diff(fractions: &[(f64, f64, f64)]) -> f64 {
    let mut mi = 0.0;
    let mut ti = 0.0;
    for &(food, mine, theirs) in fractions {
        if mine >= 1.0 {
            mi += food;
        }
        if theirs >= 1.0 {
            ti += food;
        }
    }
    mi - ti
}

fn bfs_distance(st: &State, sources: u32, targets: &[Cr]) -> i32 {
    let gm = st.map();
    if sources == 0 {
        return HQ_DIST_CAP;
    }
    let tmask = targets.iter().fold(0u32, |m, c| m | (1 << c));
    if sources & tmask != 0 {
        return 0;
    }
    let mut seen = sources;
    let mut frontier: Vec<Cr> = (0..gm.n() as Cr).filter(|c| sources & (1 << c) != 0).collect();
    let mut dist = 0;
    while !frontier.is_empty() && dist < HQ_DIST_CAP {
        dist += 1;
        let mut next = Vec::new();
        for cr in frontier {
            for &nb in gm.neighbors(cr) {
                if tmask & (1 << nb) != 0 {
                    return dist;
                }
                if seen & (1 << nb) == 0 {
                    seen |= 1 << nb;
                    next.push(nb);
                }
            }
        }
        frontier = next;
    }
    HQ_DIST_CAP
}

fn hq_dist_diff(st: &State, me: Player, opp: Player, my_connection: u32, opp_connection: u32) -> f64 {
    let gm = st.map();
    let front_mask = |p: Player| gm.front(p).iter().fold(0u32, |m, c| m | (1 << c));
    let my_sources = if my_connection != 0 { my_connection } else { front_mask(me) };
    let opp_sources = if opp_connection != 0 { opp_connection } else { front_mask(opp) };
    let my_dist = bfs_distance(st, my_sources, gm.front(opp));
    let opp_dist = bfs_distance(st, opp_sources, gm.front(me));
    (1.0 / (1.0 + my_dist as f64)) - (1.0 / (1.0 + opp_dist as f64))
}

fn flight_hand_expected_diff(st: &State, me: Player, opp: Player) -> f64 {
    let own = st.hands[me as usize].iter().filter(|u| st.card(u.card).has_kw(K_FLIGHT)).count() as f64;
    let unseen = opponent_unseen(st, opp);
    let n = unseen.len();
    let h = st.hands[opp as usize].len();
    let expected = if n == 0 || h == 0 { 0.0 } else {
        let flight = unseen.iter().filter(|c| st.card(**c).has_kw(K_FLIGHT)).count();
        h as f64 * (flight as f64 / n as f64)
    };
    own - expected
}

fn extra_actions(st: &State, player: Player) -> f64 {
    let mut pending = 0i64;
    for s in &st.scheduled {
        if m_get_s(s, "owner") == Some(player_name(player)) {
            if let Some(step) = s.get("step").and_then(|x| x.as_map()) {
                if m_get_s(step, "op") == Some("grant_action") {
                    pending += m_get_i(step, "n").unwrap_or(1);
                }
            }
        }
    }
    (m_get_i(&st.turn_flags, &format!("bonus_actions_{}", player_name(player))).unwrap_or(0) + pending) as f64
}

/// The feature vector for `st` from `me`'s side, in `feature_names` order. `st` must be non-terminal.
pub fn extract(st: &State, me: Player, set: &str) -> Vec<f64> {
    let opp = other(me);
    let my_connection = st.connected_occupied(me);
    let opp_connection = st.connected_occupied(opp);
    let mut v: Vec<f64> = Vec::with_capacity(48);
    let (food_progress, food_proximity) = food_terms(st, me, opp);
    v.push(food_progress);
    v.push(food_proximity);
    v.push(board_presence(st, me));
    v.push(my_connection.count_ones() as f64);
    let fractions = region_fractions(st, me, opp);
    v.push(region_control(&fractions));
    let (enemy, own) = hq_threat_terms(st, me, opp, my_connection, opp_connection, 0.0);
    v.push(enemy);
    v.push(-own);
    v.push(-coverage_exposure_worst(st, me, opp, opp_connection));
    v.push(card_economy(st, me, opp));
    let live = enabled_roar_count(st, me);
    v.push(live as f64);
    v.push(pending_payoff(st, me, false));
    if set == "rung1" || set == "rung2" {
        let phase = (st.turn_counter as f64 / T_NORM).min(1.0);
        let growth = growth_board_diff(st, me, opp);
        v.push(growth);
        v.push(growth / (st.turn_counter.max(1) as f64));
        let dyn_ = dynamic_board_diff(st, me, opp);
        v.push(dyn_ as f64);
        v.push((st.remove_pile.len() as f64 / TOTAL_CARDS_NORM) * dyn_ as f64);
        v.push(phase * growth);
        let (near, far) = scheduled_horizon_diffs(st, me);
        v.push(near);
        v.push(far);
        let income = income_diff(&fractions);
        v.push(income);
        v.push(income * (1.0 - phase));
        v.push((st.decks[me as usize].len() as f64 - st.decks[opp as usize].len() as f64) / DECK_NORM);
        v.push(phase * food_progress);
        v.push(hq_dist_diff(st, me, opp, my_connection, opp_connection));
        v.push(flight_hand_expected_diff(st, me, opp));
    }
    if set == "rung2" {
        let hand: Vec<&Card> = st.hands[me as usize].iter().map(|u| st.card(u.card)).collect();
        let strengths: Vec<i32> = hand.iter().filter_map(|c| c.base).collect();
        let roars = hand.iter().filter(|c| c.has_roar).count() as i32;
        let tops: Vec<&Unit> = st.tops().map(|(_, u)| u).collect();
        let mine: Vec<&Unit> = tops.iter().copied().filter(|u| u.owner == me).collect();
        let theirs: Vec<&Unit> = tops.iter().copied().filter(|u| u.owner == opp).collect();
        let my_tags: Vec<u32> = mine.iter().map(|u| st.card(u.card).tags).collect();
        let board_tags = my_tags.iter().fold(0u32, |a, t| a | t);
        let mut pairs = 0;
        for i in 0..my_tags.len() {
            for j in i + 1..my_tags.len() {
                if my_tags[i] & my_tags[j] != 0 {
                    pairs += 1;
                }
            }
        }
        let gm = st.map();
        let held = gm.front(me).iter().filter(|&&cr| st.owner_of(cr) == Some(me)).count();
        let mut near_front = gm.front(me).iter().fold(0u32, |m, c| m | (1 << c));
        for &cr in gm.front(me) {
            for &nb in gm.neighbors(cr) {
                near_front |= 1 << nb;
            }
        }
        let pressure = (near_front & opp_connection).count_ones();
        v.push((st.current == me) as i32 as f64);
        v.push((st.turn_counter as f64 / T_NORM).min(1.0));
        v.push(hand.len() as f64);
        v.push(st.hands[opp as usize].len() as f64);
        v.push(roars as f64);
        v.push((roars - live).max(0) as f64);
        v.push(if strengths.is_empty() { 0.0 } else { strengths.iter().map(|s| *s as f64).sum::<f64>() / strengths.len() as f64 });
        v.push(strengths.iter().copied().max().unwrap_or(0) as f64);
        v.push(strengths.iter().filter(|s| **s <= 2).count() as f64);
        v.push(hand.iter().filter(|c| c.has_kw(K_FLIGHT)).count() as f64);
        v.push(hand.iter().filter(|c| c.food_cost != 0).count() as f64);
        v.push(hand.iter().filter(|c| c.food_cost != 0 && c.food_cost <= st.food[me as usize]).count() as f64);
        v.push(hand.iter().filter(|c| c.tags & board_tags != 0).count() as f64);
        v.push(mine.len() as f64);
        v.push(theirs.len() as f64);
        v.push(mine.iter().filter(|u| st.card(u.card).has_ability && !st.card(u.card).has_roar).count() as f64);
        v.push(theirs.iter().filter(|u| st.card(u.card).has_ability && !st.card(u.card).has_roar).count() as f64);
        v.push(pairs as f64);
        v.push(extra_actions(st, me));
        v.push(extra_actions(st, opp));
        v.push(held as f64);
        v.push(pressure as f64);
        v.push(pending_target_strength(st, me));
        v.push(buried_presence(st, me));
    }
    v
}

/// `features.extract` as the deployed learned path scores an afterstate: reframed to `me`'s next top-level decision
/// once control has passed to the opponent.
pub fn extract_as_scored(st: &mut State, me: Player, set: &str) -> Vec<f64> {
    if st.current == me {
        return extract(st, me, set);
    }
    reframed_at_my_turn(st, me, |s| extract(s, me, set))
}

pub fn reframed_at_my_turn<T>(st: &mut State, me: Player, f: impl FnOnce(&State) -> T) -> T {
    let saved_current = st.current;
    let saved_pending = st.pending.take();
    let saved_stack = std::mem::take(&mut st.effect_stack);
    let saved_actions = st.actions_taken_this_turn;
    st.current = me;
    st.actions_taken_this_turn = 0;
    let out = f(st);
    st.current = saved_current;
    st.pending = saved_pending;
    st.effect_stack = saved_stack;
    st.actions_taken_this_turn = saved_actions;
    out
}

// ------------------------------------------------------------------ learned evaluators

#[derive(Clone, Debug)]
pub struct LinearEval {
    pub feature_set: String,
    pub weights: Vec<f64>,
    pub bias: f64,
}

#[derive(Clone, Debug)]
pub struct NetEval {
    pub feature_set: String,
    pub mean: Vec<f64>,
    pub std: Vec<f64>,
    pub w1: Vec<Vec<f64>>,
    pub b1: Vec<f64>,
    pub w2: Vec<f64>,
    pub b2: f64,
    pub scale: f64,
}

#[derive(Clone, Debug)]
pub enum Evaluator {
    Hand,
    Linear(LinearEval),
    Net(NetEval),
}

impl Evaluator {
    pub fn from_json(d: &sj::Value) -> Result<Evaluator, String> {
        let fs = d["feature_set"].as_str().ok_or("evaluator without feature_set")?.to_string();
        let vec = |k: &str| -> Vec<f64> { d[k].as_array().map(|a| a.iter().map(|x| x.as_f64().unwrap_or(0.0)).collect()).unwrap_or_default() };
        if d.get("kind").and_then(|k| k.as_str()) == Some("mlp") || d.get("w1").is_some() {
            Ok(Evaluator::Net(NetEval {
                feature_set: fs,
                mean: vec("mean"),
                std: vec("std"),
                w1: d["w1"].as_array().map(|rows| rows.iter().map(|r| r.as_array().unwrap().iter().map(|x| x.as_f64().unwrap_or(0.0)).collect()).collect()).unwrap_or_default(),
                b1: vec("b1"),
                w2: vec("w2"),
                b2: d["b2"].as_f64().unwrap_or(0.0),
                scale: d.get("scale").and_then(|s| s.as_f64()).unwrap_or(1.0),
            }))
        } else {
            Ok(Evaluator::Linear(LinearEval { feature_set: fs, weights: vec("weights"), bias: d["bias"].as_f64().unwrap_or(0.0) }))
        }
    }

    pub fn value(&self, st: &State, me: Player, w: &Weights) -> f64 {
        match self {
            Evaluator::Hand => evaluate(st, me, w),
            Evaluator::Linear(l) => {
                if let Some(r) = &st.result {
                    return if r.winner == Some(me) { f64::INFINITY } else if r.winner == Some(other(me)) { f64::NEG_INFINITY } else { 0.0 };
                }
                let phi = extract(st, me, &l.feature_set);
                let mut s = 0.0;
                for (w, x) in l.weights.iter().zip(phi.iter()) {
                    s += w * x;
                }
                l.bias + s
            }
            Evaluator::Net(n) => {
                if let Some(r) = &st.result {
                    return if r.winner == Some(me) { f64::INFINITY } else if r.winner == Some(other(me)) { f64::NEG_INFINITY } else { 0.0 };
                }
                let phi = extract(st, me, &n.feature_set);
                let z: Vec<f64> = phi.iter().zip(n.mean.iter()).zip(n.std.iter()).map(|((x, m), s)| (x - m) / s).collect();
                let mut out = n.b2;
                for ((row, b), w) in n.w1.iter().zip(n.b1.iter()).zip(n.w2.iter()) {
                    let mut acc = 0.0;
                    for (a, x) in row.iter().zip(z.iter()) {
                        acc += a * x;
                    }
                    let h = b + acc;
                    if h > 0.0 {
                        out += w * h;
                    }
                }
                n.scale * out
            }
        }
    }
}

pub fn value_of(v: &Value) -> Option<i64> {
    v.as_i64()
}
