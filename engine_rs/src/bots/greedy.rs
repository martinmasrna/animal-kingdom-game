//! GreedyBot (bots/greedy_bot.py): the one-ply evaluation pilot, also the fast policy inside the searchers.

use crate::actions::Action;
use crate::bots::features::{evaluate, opponent_lethal_next_turn, roar_fizzled, Evaluator, Weights};
use crate::data::*;
use crate::rng::PyRandom;
use crate::rules;
use crate::state::State;

#[derive(Clone)]
pub struct GreedyBot {
    pub weights: Weights,
    pub evaluator: Evaluator,
    pub rng: PyRandom,
    pub depth: i32,
    pub beam_width: usize,
    pub slip: f64,
    pub slip_rng: PyRandom,
    pub mulligan: bool,
}

impl GreedyBot {
    pub fn new(weights: Weights, evaluator: Evaluator, seed: i64, depth: i32, beam_width: usize, slip: f64, mulligan: bool) -> GreedyBot {
        GreedyBot { weights, evaluator, rng: PyRandom::seeded(seed), depth, beam_width, slip, slip_rng: PyRandom::seeded(seed ^ 0x51195), mulligan }
    }

    pub fn eval(&self, st: &State, me: Player) -> f64 {
        match &self.evaluator {
            Evaluator::Hand => evaluate(st, me, &self.weights),
            e => e.value(st, me, &self.weights),
        }
    }

    /// One action from `legal` for `me` (the seat to act, a pending chooser included).
    pub fn choose(&mut self, st: &State, me: Player, legal: &[Action]) -> Action {
        if let Some(keep) = keep_hand_skip(st, legal) {
            return keep;
        }
        if self.slip != 0.0 && self.slip_rng.random() < self.slip {
            let moves: Vec<&Action> = legal.iter().filter(|a| !matches!(a, Action::Pass)).collect();
            let pool: Vec<&Action> = if moves.is_empty() { legal.iter().collect() } else { moves };
            return pool[self.slip_rng.choice_index(pool.len())].clone();
        }
        let opp = other(me);
        let mut best_score = f64::NEG_INFINITY;
        let mut best: Vec<&Action> = Vec::new();
        let mut fallback_score = f64::NEG_INFINITY;
        let mut fallback: Vec<&Action> = Vec::new();
        for action in legal {
            let mut nxt = st.clone();
            let _ = rules::apply_action(&mut nxt, action, false);
            let mut score = self.rollout_value(&nxt, me, self.depth - 1);
            if roar_fizzled(st, &nxt, me, action) {
                score -= self.weights.wasted_roar;
            }
            if score > fallback_score {
                fallback_score = score;
                fallback = vec![action];
            } else if score == fallback_score {
                fallback.push(action);
            }
            if nxt.result.is_none() && opponent_lethal_next_turn(&nxt, opp) {
                continue;
            }
            if score > best_score {
                best_score = score;
                best = vec![action];
            } else if score == best_score {
                best.push(action);
            }
        }
        let pick = |rng: &mut PyRandom, v: &Vec<&Action>| -> Action {
            if v.len() == 1 {
                v[0].clone()
            } else {
                v[rng.choice_index(v.len())].clone()
            }
        };
        if !best.is_empty() {
            return pick(&mut self.rng, &best);
        }
        pick(&mut self.rng, &fallback)
    }

    fn rollout_value(&self, st: &State, me: Player, remaining: i32) -> f64 {
        if remaining <= 0 || st.result.is_some() {
            return self.eval(st, me);
        }
        let mut s = st.clone();
        advance_to_my_turn(&mut s, me);
        if s.result.is_some() {
            return self.eval(&s, me);
        }
        let candidates = rules::legal_actions(&s);
        if candidates.is_empty() {
            return self.eval(&s, me);
        }
        let mut scored: Vec<(f64, State)> = Vec::new();
        for a in &candidates {
            let mut nxt = s.clone();
            let _ = rules::apply_action(&mut nxt, a, false);
            let v = self.eval(&nxt, me);
            scored.push((v, nxt));
        }
        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        let beam: Vec<&(f64, State)> = if self.beam_width > 0 { scored.iter().take(self.beam_width).collect() } else { scored.iter().collect() };
        beam.iter().map(|(_, nxt)| self.rollout_value(nxt, me, remaining - 1)).fold(f64::NEG_INFINITY, f64::max)
    }
}

fn advance_to_my_turn(st: &mut State, me: Player) {
    let mut guard = 0;
    while st.result.is_none() && st.player_to_act() != me && guard < 20 {
        guard += 1;
        let legal = rules::legal_actions(st);
        if legal.is_empty() {
            break;
        }
        let filler = legal.iter().find(|a| !matches!(a, Action::Draw)).unwrap_or(&legal[0]).clone();
        let _ = rules::apply_action(st, &filler, false);
    }
}

/// The mulligan step while one is pending: keep (the bots that don't mulligan), else None.
pub fn keep_hand_skip(st: &State, legal: &[Action]) -> Option<Action> {
    if let Some(p) = &st.pending {
        if crate::value::m_get_s(p, "kind") == Some("mulligan") {
            return legal.iter().find(|a| a.is_skip()).cloned();
        }
    }
    None
}
