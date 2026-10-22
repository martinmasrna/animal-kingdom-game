//! The Animal Kingdom engine in Rust, behind the Python engine's interface: an `Engine` built from the same
//! cards.json, maps.json and Config as the Python package, and a `State` with new_game / clone / legal_actions /
//! apply_action / apply_logged / is_terminal / to_dict / from_dict.

pub mod actions;
pub mod bots;
pub mod cards;
pub mod data;
pub mod effects;
pub mod rng;
pub mod rules;
pub mod state;
pub mod statics;
pub mod strength;
pub mod value;

use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};
use serde_json as sj;

use crate::data::*;
use crate::state::{Game, State};

fn json_to_py(py: Python<'_>, v: &sj::Value) -> PyResult<Py<PyAny>> {
    Ok(match v {
        sj::Value::Null => py.None(),
        sj::Value::Bool(b) => PyBool::new(py, *b).to_owned().into_any().unbind(),
        sj::Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                PyInt::new(py, i).into_any().unbind()
            } else {
                PyFloat::new(py, n.as_f64().unwrap_or(0.0)).into_any().unbind()
            }
        }
        sj::Value::String(s) => PyString::new(py, s).into_any().unbind(),
        sj::Value::Array(a) => {
            let items: Vec<Py<PyAny>> = a.iter().map(|x| json_to_py(py, x)).collect::<PyResult<_>>()?;
            PyList::new(py, items)?.into_any().unbind()
        }
        sj::Value::Object(o) => {
            let d = PyDict::new(py);
            for (k, x) in o {
                d.set_item(k, json_to_py(py, x)?)?;
            }
            d.into_any().unbind()
        }
    })
}

fn py_to_json(obj: &Bound<'_, PyAny>) -> PyResult<sj::Value> {
    if obj.is_none() {
        return Ok(sj::Value::Null);
    }
    if let Ok(b) = obj.downcast::<PyBool>() {
        return Ok(sj::Value::Bool(b.is_true()));
    }
    if let Ok(i) = obj.extract::<i64>() {
        return Ok(sj::Value::from(i));
    }
    if let Ok(f) = obj.extract::<f64>() {
        return Ok(sj::Value::from(f));
    }
    if let Ok(s) = obj.extract::<String>() {
        return Ok(sj::Value::String(s));
    }
    if let Ok(l) = obj.downcast::<PyList>() {
        return Ok(sj::Value::Array(l.iter().map(|x| py_to_json(&x)).collect::<PyResult<_>>()?));
    }
    if let Ok(t) = obj.downcast::<PyTuple>() {
        return Ok(sj::Value::Array(t.iter().map(|x| py_to_json(&x)).collect::<PyResult<_>>()?));
    }
    if let Ok(d) = obj.downcast::<PyDict>() {
        let mut m = sj::Map::new();
        for (k, v) in d.iter() {
            m.insert(k.extract::<String>()?, py_to_json(&v)?);
        }
        return Ok(sj::Value::Object(m));
    }
    Err(PyValueError::new_err(format!("cannot convert {obj:?} to JSON")))
}

fn err(e: String) -> PyErr {
    PyValueError::new_err(e)
}

#[pyclass]
pub struct Engine {
    g: Arc<Game>,
}

#[pymethods]
impl Engine {
    #[new]
    #[pyo3(signature = (cards_json, maps_json, config_json, map_id="map_b"))]
    fn new(cards_json: &str, maps_json: &str, config_json: &str, map_id: &str) -> PyResult<Engine> {
        let cards_raw: sj::Value = sj::from_str(cards_json).map_err(|e| err(e.to_string()))?;
        let maps_raw: sj::Value = sj::from_str(maps_json).map_err(|e| err(e.to_string()))?;
        let cfg_raw: sj::Value = sj::from_str(config_json).map_err(|e| err(e.to_string()))?;
        let cards = Cards::from_json(&cards_raw).map_err(err)?;
        let rec = maps_raw["maps"].as_array().and_then(|a| a.iter().find(|m| m["id"].as_str() == Some(map_id))).ok_or_else(|| err(format!("no such map {map_id:?}")))?;
        let map = GameMap::from_json(rec).map_err(err)?;
        let cfg = Config::from_json(&cfg_raw).map_err(err)?;
        Ok(Engine { g: Arc::new(Game::new(cards, map, cfg)) })
    }

    #[pyo3(signature = (deck_a, deck_b, seed, first_player=None, stacked=false))]
    fn new_game(&self, deck_a: Vec<String>, deck_b: Vec<String>, seed: i64, first_player: Option<String>, stacked: bool) -> PyResult<PyState> {
        let ids = |d: &Vec<String>| -> PyResult<Vec<CardId>> { d.iter().map(|n| self.g.cards.id_of(n).ok_or_else(|| err(format!("unknown card {n:?}")))).collect() };
        let a = ids(&deck_a)?;
        let b = ids(&deck_b)?;
        let fp = first_player.map(|s| player_from(&s));
        Ok(PyState { st: State::new_game(self.g.clone(), &a, &b, seed, fp, stacked) })
    }

    fn from_dict(&self, d: &Bound<'_, PyAny>) -> PyResult<PyState> {
        let v = py_to_json(d)?;
        Ok(PyState { st: State::from_json(self.g.clone(), &v) })
    }

    fn card_ids(&self) -> Vec<String> {
        self.g.cards.list.iter().map(|c| c.id.clone()).collect()
    }
}

#[pyclass(name = "State")]
pub struct PyState {
    st: State,
}

#[pymethods]
impl PyState {
    fn clone(&self) -> PyState {
        PyState { st: self.st.clone() }
    }

    fn to_dict(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        json_to_py(py, &self.st.to_json())
    }

    fn to_json(&self) -> String {
        self.st.to_json().to_string()
    }

    fn legal_actions(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let acts = rules::legal_actions(&self.st);
        let items: Vec<Py<PyAny>> = acts.iter().map(|a| json_to_py(py, &a.to_json(&self.st))).collect::<PyResult<_>>()?;
        Ok(PyList::new(py, items)?.into_any().unbind())
    }

    #[pyo3(signature = (action, validate=true))]
    fn apply_action(&mut self, action: &Bound<'_, PyAny>, validate: bool) -> PyResult<()> {
        let v = py_to_json(action)?;
        let a = actions::Action::from_json(&self.st, &v).map_err(err)?;
        rules::apply_action(&mut self.st, &a, validate).map_err(err)
    }

    fn apply_logged(&mut self, action: &Bound<'_, PyAny>) -> PyResult<()> {
        let v = py_to_json(action)?;
        rules::apply_logged(&mut self.st, &v).map_err(err)
    }

    fn is_terminal(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match rules::is_terminal(&self.st) {
            None => Ok(py.None()),
            Some(r) => json_to_py(py, &sj::json!({"winner": r.winner.map(player_name), "reason": r.reason})),
        }
    }

    fn can_pass(&self) -> bool {
        rules::can_pass(&self.st)
    }

    fn player_to_act(&self) -> &'static str {
        player_name(self.st.player_to_act())
    }

    #[getter]
    fn current(&self) -> &'static str {
        player_name(self.st.current)
    }

    #[getter]
    fn turn_counter(&self) -> i32 {
        self.st.turn_counter
    }

    #[getter]
    fn actions_taken_this_turn(&self) -> i32 {
        self.st.actions_taken_this_turn
    }

    #[getter]
    fn pending(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match &self.st.pending {
            None => Ok(py.None()),
            Some(p) => json_to_py(py, &value::Value::Map(p.clone()).to_json()),
        }
    }

    #[getter]
    fn food(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        json_to_py(py, &sj::json!({"A": self.st.food[0], "B": self.st.food[1]}))
    }

    #[getter]
    fn result(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match &self.st.result {
            None => Ok(py.None()),
            Some(r) => json_to_py(py, &sj::json!({"winner": r.winner.map(player_name), "reason": r.reason})),
        }
    }

    /// The events since the last call (and clears them).
    fn events(&mut self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let evs = std::mem::take(&mut self.st.events);
        let items: Vec<Py<PyAny>> = evs.iter().map(|m| json_to_py(py, &value::Value::Map(m.clone()).to_json())).collect::<PyResult<_>>()?;
        Ok(PyList::new(py, items)?.into_any().unbind())
    }

    fn set_record_events(&mut self, on: bool) {
        self.st.record_events = on;
    }

    #[pyo3(signature = (player, card, unit_iid=None))]
    fn roar_condition(&self, player: &str, card: &str, unit_iid: Option<i64>) -> Option<bool> {
        let unit = unit_iid.and_then(|i| self.st.find_instance(i).cloned());
        cards::roar_condition(&self.st, player_from(player), card, unit.as_ref())
    }
}

#[pyclass(name = "Bot")]
pub struct PyBot {
    bot: bots::Bot,
}

#[pymethods]
impl PyBot {
    #[new]
    #[pyo3(signature = (spec, seed, evaluator_json=None))]
    fn new(spec: &str, seed: i64, evaluator_json: Option<&str>) -> PyResult<PyBot> {
        let ev = match evaluator_json {
            Some(s) => Some(sj::from_str::<sj::Value>(s).map_err(|e| err(e.to_string()))?),
            None => None,
        };
        Ok(PyBot { bot: bots::Bot::from_spec(spec, seed, ev.as_ref()).map_err(err)? })
    }

    /// The bot's action for the seat to act in `state`, as a dict.
    fn choose(&mut self, py: Python<'_>, state: &PyState) -> PyResult<Py<PyAny>> {
        let me = state.st.player_to_act();
        let legal = rules::legal_actions(&state.st);
        if legal.is_empty() {
            return Err(err("no legal actions".into()));
        }
        let a = self.bot.choose(&state.st, me, &legal);
        json_to_py(py, &a.to_json(&state.st))
    }

    /// The root candidates with their scores from the last search, as (action dict, score) pairs.
    fn root_scores(&self, py: Python<'_>, state: &PyState) -> PyResult<Py<PyAny>> {
        let items: Vec<Py<PyAny>> = self
            .bot
            .root_scores()
            .iter()
            .map(|(a, s)| {
                let t = PyTuple::new(py, [json_to_py(py, &a.to_json(&state.st))?, PyFloat::new(py, *s).into_any().unbind()])?;
                Ok(t.into_any().unbind())
            })
            .collect::<PyResult<_>>()?;
        Ok(PyList::new(py, items)?.into_any().unbind())
    }

    fn stats(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match self.bot.stats() {
            None => Ok(py.None()),
            Some(s) => json_to_py(
                py,
                &sj::json!({"root_candidates": s.root_candidates, "screened_candidates": s.screened_candidates, "reply_world_rollouts": s.reply_world_rollouts,
                    "plan_reused": s.plan_reused, "budget_fallbacks": s.budget_fallbacks, "search_nodes": s.search_nodes, "lookahead_cut": s.lookahead_cut,
                    "chased_roots": s.chased_roots, "deepened_roots": s.deepened_roots, "lookahead_lines": s.lookahead_lines,
                    "decision_gap": if s.decision_gap.is_finite() { sj::Value::from(s.decision_gap) } else { sj::Value::Null }}),
            ),
        }
    }
}

/// Play one game between two bots from their specs. Returns the record: winner, reason, turns, the action log, and
/// with `features` (a feature set name) the positions as the self-play recorder keeps them: every decision's state
/// from the mover's side at a turn start, and every afterstate as the learned path would score it.
#[pyfunction]
#[pyo3(signature = (engine, deck_a, deck_b, seed, spec_a, spec_b, first_player=None, features=None, epsilon=0.0, evaluator_a=None, evaluator_b=None, record_events=false))]
#[allow(clippy::too_many_arguments)]
fn play_game(
    py: Python<'_>,
    engine: &Engine,
    deck_a: Vec<String>,
    deck_b: Vec<String>,
    seed: i64,
    spec_a: &str,
    spec_b: &str,
    first_player: Option<String>,
    features: Option<String>,
    epsilon: f64,
    evaluator_a: Option<&str>,
    evaluator_b: Option<&str>,
    record_events: bool,
) -> PyResult<Py<PyAny>> {
    let ids = |d: &Vec<String>| -> PyResult<Vec<CardId>> { d.iter().map(|n| engine.g.cards.id_of(n).ok_or_else(|| err(format!("unknown card {n:?}")))).collect() };
    let a = ids(&deck_a)?;
    let b = ids(&deck_b)?;
    let fp = first_player.map(|s| player_from(&s));
    let mut st = State::new_game(engine.g.clone(), &a, &b, seed, fp, false);
    st.record_events = record_events;
    let ev = |s: Option<&str>| -> PyResult<Option<sj::Value>> { s.map(|x| sj::from_str::<sj::Value>(x).map_err(|e| err(e.to_string()))).transpose() };
    let eva = ev(evaluator_a)?;
    let evb = ev(evaluator_b)?;
    let mut bots = [bots::Bot::from_spec(spec_a, seed * 2, eva.as_ref()).map_err(err)?, bots::Bot::from_spec(spec_b, seed * 2 + 1, evb.as_ref()).map_err(err)?];
    let mut eps_rng = rng::PyRandom::seeded(seed);
    let mut xs: Vec<Vec<f64>> = Vec::new();
    let mut seats: Vec<Player> = Vec::new();
    let mut turns: Vec<i32> = Vec::new();
    let fs = features.clone();
    let log = py.detach(|| {
        bots::play_out(&mut st, &mut bots, epsilon, &mut eps_rng, |s, actor, before| {
            let Some(fs) = &fs else { return };
            if before {
                if s.pending.is_none() && s.actions_taken_this_turn == 0 && s.turn_counter > 0 {
                    xs.push(bots::features::extract(s, actor, fs));
                    seats.push(actor);
                    turns.push(s.turn_counter);
                }
            } else {
                let mut c = s.clone();
                xs.push(bots::features::extract_as_scored(&mut c, actor, fs));
                seats.push(actor);
                turns.push(s.turn_counter);
            }
        })
    });
    let result = rules::is_terminal(&st);
    let ys: Vec<f64> = seats.iter().map(|&seat| match &result {
        Some(r) => match r.winner {
            None => 0.5,
            Some(w) => (w == seat) as i32 as f64,
        },
        None => 0.5,
    }).collect();
    let out = sj::json!({
        "winner": result.as_ref().and_then(|r| r.winner.map(player_name)),
        "reason": result.as_ref().map(|r| r.reason.clone()),
        "turns": st.turn_counter,
        "first_player": player_name(st.first_player),
        "actions": log,
        "x": xs, "y": ys, "turn": turns, "seat": seats.iter().map(|s| player_name(*s)).collect::<Vec<_>>(),
        "food": {"A": st.food[0], "B": st.food[1]},
        "events": if record_events { sj::Value::Array(st.events.iter().map(|m| value::Value::Map(m.clone()).to_json()).collect()) } else { sj::Value::Null },
    });
    json_to_py(py, &out)
}

#[pymodule]
fn ak_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Engine>()?;
    m.add_class::<PyState>()?;
    m.add_class::<PyBot>()?;
    m.add_function(wrap_pyfunction!(play_game, m)?)?;
    Ok(())
}
