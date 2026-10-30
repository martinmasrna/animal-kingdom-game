//! The bots: a bot is built from a spec string the way sim.runner.make_bot builds one (`kind:k=v,...`, `w.<name>`
//! for an evaluation weight), and plays through `choose`.

pub mod features;
pub mod greedy;
pub mod search;
pub mod world;

use serde_json as sj;

use crate::actions::Action;
use crate::data::Player;
use crate::rng::PyRandom;
use crate::rules;
use crate::state::State;
use features::{Evaluator, Weights};
use greedy::GreedyBot;
use search::{Kind, Mulligan, Searcher};

pub const EASY_SLIP: f64 = 0.3;

pub enum Bot {
    Random(PyRandom),
    Greedy(GreedyBot),
    Search(Searcher),
}

fn coerce(v: &str) -> sj::Value {
    if let Ok(i) = v.parse::<i64>() {
        return sj::Value::from(i);
    }
    if let Ok(f) = v.parse::<f64>() {
        return sj::Value::from(f);
    }
    match v.to_ascii_lowercase().as_str() {
        "true" => sj::Value::Bool(true),
        "false" => sj::Value::Bool(false),
        _ => sj::Value::String(v.to_string()),
    }
}

/// `kind[:k=v,k=v]` -> (kind, kwargs).
pub fn parse_spec(spec: &str) -> (String, Vec<(String, sj::Value)>) {
    let (head, tail) = spec.split_once(':').unwrap_or((spec, ""));
    let kwargs = tail
        .split(',')
        .filter(|s| !s.is_empty())
        .filter_map(|item| item.split_once('=').map(|(k, v)| (k.trim().to_string(), coerce(v.trim()))))
        .collect();
    (head.trim().to_ascii_lowercase(), kwargs)
}

fn as_usize(v: &sj::Value) -> usize {
    v.as_u64().unwrap_or(0) as usize
}
fn as_f64(v: &sj::Value) -> f64 {
    v.as_f64().unwrap_or(0.0)
}
fn as_bool(v: &sj::Value) -> bool {
    v.as_bool().unwrap_or(v.as_f64().unwrap_or(0.0) != 0.0)
}

impl Bot {
    /// Build a bot from a spec and a seed; `evaluator_json` is the artifact of a `*_learned` kind when given.
    pub fn from_spec(spec: &str, seed: i64, evaluator_json: Option<&sj::Value>) -> Result<Bot, String> {
        let (mut kind, kwargs) = parse_spec(spec);
        let mut weights = Weights::default();
        let mut extra: Vec<(String, sj::Value)> = Vec::new();
        for (k, v) in kwargs {
            if let Some(name) = k.strip_prefix("w.") {
                weights.set(name, &v)?;
            } else {
                extra.push((k, v));
            }
        }
        let mut evaluator = Evaluator::Hand;
        if let Some(base) = kind.strip_suffix("_learned") {
            let ev = evaluator_json.ok_or("a learned bot needs its evaluator artifact")?;
            evaluator = Evaluator::from_json(ev)?;
            kind = base.to_string();
            extra.retain(|(k, _)| k != "eval");
        }
        let get = |name: &str| extra.iter().find(|(k, _)| k == name).map(|(_, v)| v);
        match kind.as_str() {
            "random" => Ok(Bot::Random(PyRandom::seeded(seed))),
            "greedy" | "easy" | "lookahead" | "greedy_belief" => {
                if kind == "greedy_belief" {
                    weights.coverage_exposure = 40.0;
                }
                let (mut depth, mut beam) = if kind == "lookahead" { (3, 8) } else { (1, 8) };
                let mut slip = if kind == "easy" { EASY_SLIP } else { 0.0 };
                if let Some(v) = get("depth") {
                    depth = v.as_i64().unwrap_or(1) as i32;
                }
                if let Some(v) = get("beam_width") {
                    beam = as_usize(v);
                }
                if let Some(v) = get("slip") {
                    slip = as_f64(v);
                }
                let mulligan = get("mulligan").map(as_bool).unwrap_or(false);
                Ok(Bot::Greedy(GreedyBot::new(weights, evaluator, seed, depth, beam, slip, mulligan)))
            }
            "turn" | "referee" => {
                let is_ref = kind == "referee";
                let determinizations = get("determinizations").map(as_usize).unwrap_or(if is_ref { 5 } else { 3 });
                let beam_width = get("beam_width").map(as_usize).unwrap_or(8);
                let reveal = get("deck_reveal_choice_width").map(as_usize).unwrap_or(if is_ref { 0 } else { 2 });
                let max_nodes = match get("max_search_nodes") {
                    Some(sj::Value::Null) => None,
                    Some(v) => Some(as_usize(v)),
                    None => Some(if is_ref { 150 } else { 80 }),
                };
                let quiesce = get("quiesce").map(as_bool).unwrap_or(false);
                let mulligan = match get("mulligan") {
                    Some(sj::Value::String(s)) if s == "table" => return Err("the table mulligan is not ported".into()),
                    Some(v) if as_bool(v) => Mulligan::Search,
                    _ => Mulligan::Keep,
                };
                let decisive = get("decisive").map(as_f64).unwrap_or(search::DECISIVE);
                let mut s = Searcher::new(if is_ref { Kind::Referee } else { Kind::Turn }, weights, evaluator, seed, determinizations, beam_width, reveal, max_nodes, quiesce, mulligan, decisive);
                if is_ref {
                    if let Some(v) = get("staged") {
                        s.staged = as_bool(v);
                    }
                    if let Some(v) = get("root_width") {
                        s.root_width = as_usize(v);
                    }
                    s.reply_width = get("reply_width").map(as_usize).unwrap_or(8);
                    if let Some(v) = get("depth") {
                        s.depth = v.as_i64().unwrap_or(0) as i32;
                    }
                    if let Some(v) = get("next_width") {
                        s.next_width = as_usize(v);
                    }
                    if let Some(v) = get("deepen_top") {
                        s.deepen_top = as_usize(v);
                    }
                    if let Some(v) = get("deepen_roots") {
                        s.deepen_roots = as_usize(v);
                    }
                    if let Some(v) = get("time_budget") {
                        s.time_budget = as_f64(v);
                    }
                    if let Some(v) = get("den_sense") {
                        s.den_sense = as_bool(v);
                    }
                    if let Some(v) = get("den_far") {
                        s.den_far = as_usize(v);
                    }
                    if let Some(v) = get("reply_turns") {
                        s.reply_turns = as_usize(v);
                    }
                    if let Some(v) = get("deepen_chase") {
                        s.deepen_chase = as_bool(v);
                    }
                    if let Some(v) = get("den_open") {
                        s.den_open = as_bool(v);
                    }
                    if let Some(v) = get("reply_min") {
                        s.reply_min = as_bool(v);
                    }
                    if let Some(v) = get("outs") {
                        s.outs = as_usize(v);
                    }
                }
                Ok(Bot::Search(s))
            }
            other => Err(format!("unknown bot kind {other:?}")),
        }
    }

    pub fn choose(&mut self, st: &State, me: Player, legal: &[Action]) -> Action {
        match self {
            Bot::Random(rng) => {
                if let Some(k) = greedy::keep_hand_skip(st, legal) {
                    return k;
                }
                legal[rng.choice_index(legal.len())].clone()
            }
            Bot::Greedy(g) => g.choose(st, me, legal),
            Bot::Search(s) => s.choose(st, me, legal),
        }
    }

    pub fn root_scores(&self) -> Vec<(Action, f64)> {
        match self {
            Bot::Search(s) => s.last_root_scores.clone(),
            _ => Vec::new(),
        }
    }

    pub fn stats(&self) -> Option<search::Stats> {
        match self {
            Bot::Search(s) => Some(s.stats.clone()),
            _ => None,
        }
    }
}

/// Play `st` to the end with two bots; returns the action log as dicts. `on_decision` sees every top-level and
/// sub-choice decision (the actor, the state before, the action after it is applied is not available here).
pub fn play_out(st: &mut State, bots: &mut [Bot; 2], epsilon: f64, eps_rng: &mut PyRandom, mut record: impl FnMut(&State, Player, bool)) -> Vec<sj::Value> {
    let mut log = Vec::new();
    let mut guard = 0;
    while rules::is_terminal(st).is_none() && guard < 5000 {
        guard += 1;
        let actor = st.player_to_act();
        let legal = rules::legal_actions(st);
        if legal.is_empty() {
            break;
        }
        record(st, actor, true);
        let action = if legal.len() > 1 && epsilon > 0.0 && eps_rng.random() < epsilon {
            legal[eps_rng.choice_index(legal.len())].clone()
        } else {
            bots[actor.min(1) as usize].choose(st, actor, &legal)
        };
        log.push(action.to_json(st));
        let _ = rules::apply_action(st, &action, false);
        if rules::is_terminal(st).is_none() {
            record(st, actor, false);
        }
    }
    log
}
