//! The Python module `ak_engine`: `Engine` (the card table, the map and the config, built once) and `State` (a position),
//! speaking plain dicts: actions, the saved position, events. A rule broken is a ValueError; a panic inside the engine
//! is caught here and raised as a RuntimeError, so it never takes the server down.

use std::sync::{Arc, Mutex};

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};
use serde_json as sj;

use crate::actions::Action;
use crate::bots;
use crate::data::*;
use crate::state::State;
use crate::{effects, rules, view};

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

/// Run `f`; a panic inside it becomes a RuntimeError naming what the engine said.
fn guard<T>(f: impl FnOnce() -> PyResult<T>) -> PyResult<T> {
    match std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)) {
        Ok(r) => r,
        Err(e) => {
            let msg = e.downcast_ref::<&str>().map(|s| s.to_string()).or_else(|| e.downcast_ref::<String>().cloned()).unwrap_or_else(|| "no message".into());
            Err(PyRuntimeError::new_err(format!("the engine panicked: {msg}")))
        }
    }
}

fn parse(text: &str) -> PyResult<sj::Value> {
    sj::from_str(text).map_err(|e| err(e.to_string()))
}

/// The rules' numbers as the engine ships them: {name: value}.
#[pyfunction]
fn default_config(py: Python<'_>) -> PyResult<Py<PyAny>> {
    json_to_py(py, &Config::default().to_json())
}

/// Raise ValueError on the first problem with a raw card record (a dict of the card table).
#[pyfunction(name = "validate_card_record")]
fn py_validate_card_record(rec: &Bound<'_, PyAny>) -> PyResult<()> {
    crate::data::validate_card_record(&py_to_json(rec)?).map_err(err)
}

/// The card table's own words: {"rarities", "statuses", "planned", "keywords", "dynamic_strengths", "copy_limits",
/// "deck_size"}.
#[pyfunction]
fn card_rules(py: Python<'_>) -> PyResult<Py<PyAny>> {
    json_to_py(py, &sj::json!({
        "rarities": RARITIES, "statuses": STATUSES, "planned": PLANNED,
        "keywords": KEYWORDS.iter().map(|(n, _)| *n).collect::<Vec<_>>(), "dynamic_strengths": DYNAMIC_STRENGTHS,
        "copy_limits": {"common": copy_limit(false), "legendary": copy_limit(true)}, "deck_size": DECK_SIZE,
    }))
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
        guard(|| {
            let (cards_raw, maps_raw, cfg_raw) = (parse(cards_json)?, parse(maps_json)?, parse(config_json)?);
            let cards = Cards::from_json(&cards_raw).map_err(err)?;
            let rec = maps_raw["maps"].as_array().and_then(|a| a.iter().find(|m| m["id"].as_str() == Some(map_id))).ok_or_else(|| err(format!("no such map {map_id:?}")))?;
            let map = GameMap::from_json(rec).map_err(err)?;
            let cfg = Config::from_json(&cfg_raw).map_err(err)?;
            Ok(Engine { g: Arc::new(Game::new(cards, map, cfg)) })
        })
    }

    /// Every card, in id order, as its record reads (plus "makes" and "weaken" where the card has them).
    fn cards(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        json_to_py(py, &sj::Value::Array(self.g.cards.list.iter().map(|c| c.to_json()).collect()))
    }

    /// The board: {"id", "name", "win_food", "crossroads", "edges", "bases", "regions"}.
    fn map(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        json_to_py(py, &self.g.map.to_json())
    }

    /// This engine's numbers: {name: value}.
    fn config(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        json_to_py(py, &self.g.cfg.to_json())
    }

    /// Every leader in the game's order: {"id", "kind", "text", and a power's "cost"}.
    fn leaders(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        json_to_py(py, &view::leaders_json(&self.g.cfg))
    }

    /// What makes a deck illegal, as sentences; empty when it is legal.
    #[pyo3(signature = (decklist, leader=None))]
    fn deck_problems(&self, decklist: Vec<String>, leader: Option<String>) -> Vec<String> {
        view::deck_problems(&self.g.cards, &decklist, leader.as_deref())
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
        let st = guard(|| State::new_game(self.g.clone(), &ids(&deck_a), &ids(&deck_b), seed.unsigned_abs(), fp, lead).map_err(err))?;
        Ok(PyState { st })
    }

    /// A position from its saved dict (`State.to_dict`, or the Python engine's `GameState.to_dict`).
    fn from_dict(&self, d: &Bound<'_, PyAny>) -> PyResult<PyState> {
        let v = py_to_json(d)?;
        guard(|| Ok(PyState { st: State::from_json(self.g.clone(), &v).map_err(err)? }))
    }

    fn from_json(&self, text: &str) -> PyResult<PyState> {
        let v = parse(text)?;
        guard(|| Ok(PyState { st: State::from_json(self.g.clone(), &v).map_err(err)? }))
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
        let acts: Vec<sj::Value> = guard(|| Ok(rules::legal_actions(&self.st).iter().map(|a| a.to_json(&self.st.g)).collect()))?;
        json_to_py(py, &sj::Value::Array(acts))
    }

    fn can_pass(&self) -> bool {
        rules::can_pass(&self.st)
    }

    #[pyo3(signature = (action, validate=true))]
    fn apply_action(&mut self, action: &Bound<'_, PyAny>, validate: bool) -> PyResult<()> {
        let a = self.action(action)?;
        guard(|| rules::apply_action(&mut self.st, &a, validate).map_err(err))
    }

    /// Apply one action as a game log records it: one marked "by" a player is their mulligan choice made while the other
    /// was choosing theirs.
    fn apply_logged(&mut self, action: &Bound<'_, PyAny>) -> PyResult<()> {
        let a = self.action(action)?;
        let by = match action.get_item("by") {
            Ok(b) if !b.is_none() => Some(seat(&b.extract::<String>()?)?),
            _ => None,
        };
        guard(|| rules::apply_logged(&mut self.st, &a, by).map_err(err))
    }

    /// Where `player`'s mulligan waits under the one being chosen now (its index on the effect stack), else None.
    fn early_mulligan(&self, player: &str) -> PyResult<Option<usize>> {
        Ok(rules::early_mulligan(&self.st, seat(player)?))
    }

    fn apply_early_mulligan(&mut self, player: &str, action: &Bound<'_, PyAny>) -> PyResult<()> {
        let a = self.action(action)?;
        let p = seat(player)?;
        guard(|| rules::apply_early_mulligan(&mut self.st, p, &a).map_err(err))
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

    /// What `player` pays for the copy `iid` in their hand; None when no hand holds it.
    fn unit_cost(&self, iid: i32) -> Option<i32> {
        let u = self.st.hands.iter().flatten().find(|u| u.iid == iid)?;
        Some(effects::unit_cost(&self.st, u))
    }

    /// How the unit `iid` stands, on the board or in a hand: {"str", "cost", "hidden", "spikes", "poison", "armor"};
    /// None when it is in neither.
    fn unit_view(&self, py: Python<'_>, iid: i32) -> PyResult<Py<PyAny>> {
        match view::unit_view(&self.st, iid) {
            Some(v) => json_to_py(py, &v),
            None => Ok(py.None()),
        }
    }

    /// What `player` may see of the position: the opponent's hand and both decks as counts only.
    fn view_for(&self, py: Python<'_>, player: &str) -> PyResult<Py<PyAny>> {
        json_to_py(py, &view::seat_view(&self.st, seat(player)?))
    }

    /// The cards `player` may return in the mulligan.
    fn mulligan_cap(&self, player: &str) -> PyResult<i32> {
        Ok(self.st.cfg().mulligan_cap(seat(player)?, self.st.first_player))
    }

    /// The tiles `player` holds that are connected to their base through their own animals.
    fn connected_occupied(&self, player: &str) -> PyResult<Vec<String>> {
        let m = self.st.connected_occupied(seat(player)?);
        Ok((0..self.st.g.map.n_tiles() as Tile).filter(|&t| m >> t & 1 == 1).map(|t| self.st.g.map.tile_name(t).to_string()).collect())
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

/// A bot (`engine_rs/src/bots/`), from its spec (`greedy`, `turn:budget=20000`, ...) and a seed. It keeps what it
/// planned between calls, so one game gets one Bot.
#[pyclass(name = "Bot")]
pub struct PyBot {
    bot: Mutex<Box<dyn bots::Bot>>,
}

#[pymethods]
impl PyBot {
    #[new]
    fn new(spec: &str, seed: u64) -> PyResult<PyBot> {
        Ok(PyBot { bot: Mutex::new(guard(|| bots::make_bot(spec, seed).map_err(err))?) })
    }

    /// The action for the seat to act in `state`, as a dict. The bot reads the position only as that seat may know it
    /// (`bots/seat.rs`). It thinks with the interpreter released, and a panic inside it is a RuntimeError.
    fn choose(&self, py: Python<'_>, state: &PyState) -> PyResult<Py<PyAny>> {
        if state.st.result.is_some() {
            return Err(err("the game is over".into()));
        }
        let st = &state.st;
        let action = py.detach(|| guard(|| {
            let mut bot = self.bot.lock().map_err(|_| PyRuntimeError::new_err("the bot panicked in an earlier move"))?;
            Ok(bot.choose(st))
        }))?;
        json_to_py(py, &action.to_json(&st.g))
    }

    fn spec(&self) -> PyResult<String> {
        Ok(self.bot.lock().map_err(|_| PyRuntimeError::new_err("the bot panicked in an earlier move"))?.spec())
    }

    /// What it has done so far: {decisions, turns, positions, ms, searches}.
    fn stats(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let s = self.bot.lock().map_err(|_| PyRuntimeError::new_err("the bot panicked in an earlier move"))?.stats();
        json_to_py(py, &sj::json!({"decisions": s.decisions, "turns": s.turns, "positions": s.positions, "ms": s.nanos as f64 / 1e6, "searches": s.searches}))
    }
}

#[pymodule]
fn ak_engine(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Engine>()?;
    m.add_class::<PyState>()?;
    m.add_class::<PyBot>()?;
    m.add_function(wrap_pyfunction!(default_config, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_card_record, m)?)?;
    m.add_function(wrap_pyfunction!(card_rules, m)?)?;
    Ok(())
}
