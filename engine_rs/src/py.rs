//! The Python module `ak_engine`: `Engine` (the card table, the map and the config, built once) and `State` (a position),
//! speaking the Python engine's dicts: actions, the saved position, events.

use std::sync::Arc;

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};
use serde_json as sj;

use crate::actions::Action;
use crate::data::*;
use crate::state::State;
use crate::{effects, rules};

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
        let mut m = sj::Map::default();
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

fn seat(s: &str) -> PyResult<Player> {
    player_from(s).map_err(err)
}

#[pyclass]
pub struct Engine {
    g: Arc<Game>,
}

#[pymethods]
impl Engine {
    /// `cards_json` and `maps_json` are the bundled data files' text, `config_json` is `dataclasses.asdict(Config())`.
    #[new]
    #[pyo3(signature = (cards_json, maps_json, config_json, map_id="map_hex19"))]
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

    /// A fresh game. `seed` is any int, read as `random.Random(seed)` reads it; `leaders` is {"A": card id, "B": card id}.
    #[pyo3(signature = (deck_a, deck_b, seed, first_player=None, leaders=None))]
    fn new_game(&self, deck_a: Vec<String>, deck_b: Vec<String>, seed: i128, first_player: Option<String>, leaders: Option<&Bound<'_, PyDict>>) -> PyResult<PyState> {
        let mut unknown: Vec<&String> = deck_a.iter().chain(deck_b.iter()).filter(|n| self.g.cards.id_of(n).is_none()).collect();
        if !unknown.is_empty() {
            unknown.sort();
            unknown.dedup();
            return Err(err(format!("unknown card {}", unknown.iter().map(|s| s.as_str()).collect::<Vec<_>>().join(", "))));
        }
        let ids = |d: &Vec<String>| -> Vec<CardId> { d.iter().map(|n| self.g.cards.id_of(n).unwrap()).collect() };
        let fp = first_player.map(|s| seat(&s)).transpose()?;
        let mut lead = [None, None];
        if let Some(d) = leaders {
            for (k, v) in d.iter() {
                if v.is_none() {
                    continue;
                }
                let name: String = v.extract()?;
                let id = self.g.cards.id_of(&name).ok_or_else(|| err(format!("{name:?} is not a leader")))?;
                lead[seat(&k.extract::<String>()?)? as usize] = Some(id);
            }
        }
        let st = State::new_game(self.g.clone(), &ids(&deck_a), &ids(&deck_b), seed.unsigned_abs(), fp, lead).map_err(err)?;
        Ok(PyState { st })
    }

    /// A position from its saved dict (`State.to_dict`, or the Python engine's `GameState.to_dict`).
    fn from_dict(&self, d: &Bound<'_, PyAny>) -> PyResult<PyState> {
        let v = py_to_json(d)?;
        Ok(PyState { st: State::from_json(self.g.clone(), &v).map_err(err)? })
    }

    fn from_json(&self, text: &str) -> PyResult<PyState> {
        let v: sj::Value = sj::from_str(text).map_err(|e| err(e.to_string()))?;
        Ok(PyState { st: State::from_json(self.g.clone(), &v).map_err(err)? })
    }

    /// Every card id the engine knows, sorted.
    fn card_ids(&self) -> Vec<String> {
        self.g.cards.list.iter().map(|c| c.id.clone()).collect()
    }
}

#[pyclass(name = "State")]
pub struct PyState {
    st: State,
}

impl PyState {
    fn action(&self, d: &Bound<'_, PyAny>) -> PyResult<Action> {
        Action::from_json(&self.st.g, &py_to_json(d)?).map_err(err)
    }
}

#[pymethods]
impl PyState {
    /// An independent copy, with no events on record.
    fn clone(&self) -> PyState {
        PyState { st: self.st.fork() }
    }

    fn to_dict(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        json_to_py(py, &self.st.to_json())
    }

    fn to_json(&self) -> String {
        self.st.to_json().to_string()
    }

    /// Every legal action for the player to act, as dicts; ending the turn is listed only when nothing else is legal
    /// (it is legal whenever `can_pass()`).
    fn legal_actions(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let acts: Vec<sj::Value> = rules::legal_actions(&self.st).iter().map(|a| a.to_json(&self.st.g)).collect();
        json_to_py(py, &sj::Value::Array(acts))
    }

    fn can_pass(&self) -> bool {
        rules::can_pass(&self.st)
    }

    #[pyo3(signature = (action, validate=true))]
    fn apply_action(&mut self, action: &Bound<'_, PyAny>, validate: bool) -> PyResult<()> {
        let a = self.action(action)?;
        rules::apply_action(&mut self.st, &a, validate).map_err(err)
    }

    /// Apply one action as a game log records it: one marked "by" a player is their mulligan choice made while the other
    /// was choosing theirs.
    fn apply_logged(&mut self, action: &Bound<'_, PyAny>) -> PyResult<()> {
        let a = self.action(action)?;
        let by = match action.get_item("by") {
            Ok(b) if !b.is_none() => Some(seat(&b.extract::<String>()?)?),
            _ => None,
        };
        rules::apply_logged(&mut self.st, &a, by).map_err(err)
    }

    /// Where `player`'s mulligan waits under the one being chosen now (its index on the effect stack), else None.
    fn early_mulligan(&self, player: &str) -> PyResult<Option<usize>> {
        Ok(rules::early_mulligan(&self.st, seat(player)?))
    }

    fn apply_early_mulligan(&mut self, player: &str, action: &Bound<'_, PyAny>) -> PyResult<()> {
        let a = self.action(action)?;
        rules::apply_early_mulligan(&mut self.st, seat(player)?, &a).map_err(err)
    }

    /// The game's result as {"winner", "reason"} if it is over, else None.
    fn is_terminal(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match rules::is_terminal(&self.st) {
            Some(r) => json_to_py(py, &sj::json!({"winner": r.winner.map(pname), "reason": r.reason.name()})),
            None => Ok(py.None()),
        }
    }

    fn player_to_act(&self) -> &'static str {
        pname(self.st.player_to_act())
    }

    /// Turn the event record on or off (off by default: a search never needs it).
    fn record_events(&mut self, on: bool) {
        self.st.events.on = on;
    }

    /// What happened since the last call, in order, as the Python engine's event dicts.
    fn take_events(&mut self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let evs: Vec<sj::Value> = self.st.events.list.drain(..).map(|e| e.to_json(&self.st.g)).collect();
        json_to_py(py, &sj::Value::Array(evs))
    }

    fn own_turn_number(&self, player: &str) -> PyResult<i32> {
        Ok(rules::own_turn_number(&self.st, seat(player)?))
    }

    fn mana_total(&self, player: &str) -> PyResult<i32> {
        Ok(rules::mana_total(&self.st, seat(player)?))
    }

    fn mana_left(&self, player: &str) -> PyResult<i32> {
        Ok(rules::mana_left(&self.st, seat(player)?))
    }

    /// What playing `card_id` from hand costs `player` (the current player by default).
    #[pyo3(signature = (card_id, player=None))]
    fn mana_cost(&self, card_id: &str, player: Option<&str>) -> PyResult<i32> {
        let p = match player {
            Some(p) => seat(p)?,
            None => self.st.current,
        };
        Ok(effects::mana_cost(&self.st, self.st.g.cards.need(card_id).map_err(err)?, p))
    }

    fn power_cost(&self, player: &str) -> PyResult<i32> {
        Ok(effects::power_cost(&self.st, seat(player)?))
    }

    fn leader_usable(&self, player: &str) -> PyResult<bool> {
        Ok(effects::leader_usable(&self.st, seat(player)?))
    }

    fn region_income(&self, player: &str) -> PyResult<i32> {
        Ok(rules::region_income(&self.st, seat(player)?))
    }

    /// The strength a unit of `card_id` has for `owner` now: on the board, or as it would be played from hand.
    fn card_strength(&self, card_id: &str, owner: &str) -> PyResult<i32> {
        Ok(effects::card_strength(&self.st, self.st.g.cards.need(card_id).map_err(err)?, seat(owner)?))
    }

    /// The strength of the unit `iid`, on the board or in a hand; None when it is in neither.
    fn effective_strength(&self, iid: i32) -> Option<i32> {
        let u = self.st.board.find(iid).map(|(_, u)| u).or_else(|| self.st.hands.iter().flatten().find(|u| u.iid == iid).copied())?;
        Some(effects::effective_strength(&self.st, &u))
    }

    /// A timing loop, for the speed comparison with the Python engine: `reps` times over, every action that is legal
    /// here (ending the turn too, where it is legal) is applied to its own clone of this position. Returns the number
    /// of clone-and-apply pairs and the seconds they took.
    fn bench_clone_apply(&self, py: Python<'_>, reps: usize) -> (usize, f64) {
        let mut acts = rules::legal_actions(&self.st);
        if rules::can_pass(&self.st) && !acts.contains(&Action::Pass) {
            acts.push(Action::Pass);
        }
        let st = &self.st;
        py.detach(|| {
            let t = std::time::Instant::now();
            let mut n = 0usize;
            let mut sink = 0i64;
            for _ in 0..reps {
                for a in &acts {
                    let mut c = st.clone();
                    let _ = rules::apply_action(&mut c, a, false);
                    sink += c.food[0] as i64 + c.turn_counter as i64;
                    n += 1;
                }
            }
            std::hint::black_box(sink);
            (n, t.elapsed().as_secs_f64())
        })
    }
}

#[pymodule]
fn ak_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Engine>()?;
    m.add_class::<PyState>()?;
    Ok(())
}
