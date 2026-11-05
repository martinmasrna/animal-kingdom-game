//! The browser module (feature `wasm`, built for wasm32-unknown-unknown by `engine_rs/wasm.sh`):
//! `Engine`, `State` and `Bot`, the same calls as the Python module (py.rs), with JSON strings at the edge. The state's
//! JSON is the dict the Python engine serialises (`GameState.to_dict`), an action is the dict a game log records.

use std::sync::Arc;

use serde_json as sj;
use wasm_bindgen::prelude::*;

use crate::data::*;
use crate::state::{Game, State};
use crate::{actions, bots, rules, value, view};

fn err(e: impl ToString) -> JsError {
    JsError::new(&e.to_string())
}

fn parse(s: &str) -> Result<sj::Value, JsError> {
    sj::from_str(s).map_err(err)
}

/// The hash of the sources this module was built from (build.rs), to match against the server's.
#[wasm_bindgen(js_name = sourceHash)]
pub fn source_hash() -> String {
    env!("AK_SOURCE_HASH").into()
}

#[wasm_bindgen]
pub struct Engine {
    g: Arc<Game>,
}

#[wasm_bindgen]
impl Engine {
    /// `cards.json`, `maps.json` and the Config (as a dict) as JSON text, and the map to play on.
    #[wasm_bindgen(constructor)]
    pub fn new(cards_json: &str, maps_json: &str, config_json: &str, map_id: &str) -> Result<Engine, JsError> {
        let cards = Cards::from_json(&parse(cards_json)?).map_err(err)?;
        let maps = parse(maps_json)?;
        let rec = maps["maps"].as_array().and_then(|a| a.iter().find(|m| m["id"].as_str() == Some(map_id))).ok_or_else(|| err(format!("no such map {map_id:?}")))?;
        let map = GameMap::from_json(rec).map_err(err)?;
        let cfg = Config::from_json(&parse(config_json)?).map_err(err)?;
        Ok(Engine { g: Arc::new(Game::new(cards, map, cfg)) })
    }

    /// A new game from two decklists (JSON arrays of card ids), a seed, the first player ("A", "B", or "" for the coin).
    #[wasm_bindgen(js_name = newGame)]
    pub fn new_game(&self, deck_a_json: &str, deck_b_json: &str, seed: f64, first_player: &str, stacked: bool) -> Result<GameState, JsError> {
        let ids = |s: &str| -> Result<Vec<CardId>, JsError> {
            let v: Vec<String> = sj::from_str(s).map_err(err)?;
            v.iter().map(|n| self.g.cards.id_of(n).ok_or_else(|| err(format!("unknown card {n:?}")))).collect()
        };
        let (a, b) = (ids(deck_a_json)?, ids(deck_b_json)?);
        let fp = if first_player.is_empty() { None } else { Some(player_from(first_player)) };
        let mut st = State::new_game(self.g.clone(), &a, &b, seed as i64, fp, stacked);
        st.record_events = true;
        Ok(GameState { st })
    }

    /// A position from the dict the Python engine serialises.
    #[wasm_bindgen(js_name = fromJson)]
    pub fn from_json(&self, state_json: &str) -> Result<GameState, JsError> {
        let mut st = State::from_json(self.g.clone(), &parse(state_json)?);
        st.record_events = true;
        Ok(GameState { st })
    }

    #[wasm_bindgen(js_name = cardIds)]
    pub fn card_ids(&self) -> Vec<String> {
        self.g.cards.list.iter().map(|c| c.id.clone()).collect()
    }
}

#[wasm_bindgen]
pub struct GameState {
    st: State,
}

#[wasm_bindgen]
impl GameState {
    #[wasm_bindgen(js_name = clone)]
    pub fn clone_state(&self) -> GameState {
        let mut st = self.st.clone();
        st.record_events = self.st.record_events;
        GameState { st }
    }

    #[wasm_bindgen(js_name = toJson)]
    pub fn to_json(&self) -> String {
        self.st.to_json().to_string()
    }

    /// The legal actions as a JSON array of action dicts.
    #[wasm_bindgen(js_name = legalActions)]
    pub fn legal_actions(&self) -> String {
        sj::Value::Array(rules::legal_actions(&self.st).iter().map(|a| a.to_json(&self.st)).collect()).to_string()
    }

    /// Apply one action (a JSON action dict), validated unless `validate` is false.
    #[wasm_bindgen(js_name = applyAction)]
    pub fn apply_action(&mut self, action_json: &str, validate: bool) -> Result<(), JsError> {
        let a = actions::Action::from_json(&self.st, &parse(action_json)?).map_err(err)?;
        rules::apply_action(&mut self.st, &a, validate).map_err(err)
    }

    /// An action dict as the engine writes it (`Action.to_dict`): what a game log keeps of a move the client sent.
    pub fn canonical(&self, action_json: &str) -> Result<String, JsError> {
        Ok(actions::Action::from_json(&self.st, &parse(action_json)?).map_err(err)?.to_json(&self.st).to_string())
    }

    /// Apply one action as a game log records it (a mulligan made while the other's is under way carries `by`).
    #[wasm_bindgen(js_name = applyLogged)]
    pub fn apply_logged(&mut self, action_json: &str) -> Result<(), JsError> {
        rules::apply_logged(&mut self.st, &parse(action_json)?).map_err(err)
    }

    /// Whether `player` has a mulligan waiting under the other's (both mulligan at once).
    #[wasm_bindgen(js_name = earlyMulligan)]
    pub fn early_mulligan(&self, player: &str) -> bool {
        rules::early_mulligan(&self.st, player_from(player)).is_some()
    }

    /// The game's result as JSON ({winner, reason}), or "null" while it goes on.
    #[wasm_bindgen(js_name = isTerminal)]
    pub fn is_terminal(&self) -> String {
        match rules::is_terminal(&self.st) {
            None => "null".into(),
            Some(r) => sj::json!({"winner": r.winner.map(player_name), "reason": r.reason}).to_string(),
        }
    }

    /// Set the result (match.py `_check_end`: the state keeps the terminal result, or a concession).
    #[wasm_bindgen(js_name = setResult)]
    pub fn set_result(&mut self, winner: &str, reason: &str) {
        self.st.result = Some(crate::state::GameResult { winner: if winner.is_empty() { None } else { Some(player_from(winner)) }, reason: reason.to_string() });
    }

    #[wasm_bindgen(js_name = playerToAct)]
    pub fn player_to_act(&self) -> String {
        player_name(self.st.player_to_act()).into()
    }

    #[wasm_bindgen(getter, js_name = turnCounter)]
    pub fn turn_counter(&self) -> i32 {
        self.st.turn_counter
    }

    #[wasm_bindgen(getter, js_name = firstPlayer)]
    pub fn first_player(&self) -> String {
        player_name(self.st.first_player).into()
    }

    /// The pending choice as JSON, or "null".
    pub fn pending(&self) -> String {
        self.st.pending.as_ref().map(|p| value::Value::Map(p.clone()).to_json()).unwrap_or(sj::Value::Null).to_string()
    }

    /// The engine's events since the last call, as a JSON array (and clears them).
    #[wasm_bindgen(js_name = takeEvents)]
    pub fn take_events(&mut self) -> String {
        let evs = std::mem::take(&mut self.st.events);
        sj::Value::Array(evs.iter().map(|m| value::Value::Map(m.clone()).to_json()).collect()).to_string()
    }

    /// The engine's part of seat `seat`'s game view (view.rs), as JSON.
    pub fn view(&self, seat: &str) -> String {
        view::game_view(&self.st, player_from(seat)).to_string()
    }
}

#[wasm_bindgen]
pub struct Bot {
    bot: bots::Bot,
}

#[wasm_bindgen]
impl Bot {
    /// A bot by spec string (`sim.runner` specs: `turn:w.hq_threat_reach=0.5`), with a learned evaluator's artifact
    /// as JSON for a `*_learned` kind ("" otherwise).
    #[wasm_bindgen(constructor)]
    pub fn new(spec: &str, seed: f64, evaluator_json: &str) -> Result<Bot, JsError> {
        let ev = if evaluator_json.is_empty() { None } else { Some(parse(evaluator_json)?) };
        Ok(Bot { bot: bots::Bot::from_spec(spec, seed as i64, ev.as_ref()).map_err(err)? })
    }

    /// The bot's action for the seat to act in `state`, as a JSON action dict.
    pub fn choose(&mut self, state: &GameState) -> Result<String, JsError> {
        let me = state.st.player_to_act();
        let legal = rules::legal_actions(&state.st);
        if legal.is_empty() {
            return Err(err("no legal actions"));
        }
        Ok(self.bot.choose(&state.st, me, &legal).to_json(&state.st).to_string())
    }
}
