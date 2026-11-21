//! Actions: the one interface a player (bot or person) acts through, in the JSON shape game logs and the web API use.

use serde_json::{json, Value};

use crate::data::*;
use crate::state::Choice;

pub const SKIP: &str = "__skip__";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Target {
    Tile(Tile),
    /// A raid on that player's den.
    Den(Player),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Action {
    /// Play a card from hand.
    Place { card: CardId, target: Target },
    /// Use your leader's power.
    Leader,
    /// End the turn.
    Pass,
    /// A sub-decision while an effect resolves.
    Choice(Choice),
}

pub fn choice_to_json(g: &Game, c: Choice) -> Value {
    match c {
        Choice::Skip => Value::from(SKIP),
        Choice::Iid(i) => Value::from(i),
        Choice::Tile(t) => Value::from(g.map.tile_name(t)),
        Choice::Deck(k) => Value::from(format!("deck:{k}")),
    }
}

pub fn choice_from_json(g: &Game, v: &Value) -> Result<Choice, String> {
    if let Some(i) = v.as_i64() {
        return Ok(Choice::Iid(i as i32));
    }
    let s = v.as_str().ok_or_else(|| format!("bad choice {v}"))?;
    if s == SKIP {
        return Ok(Choice::Skip);
    }
    if let Some(k) = s.strip_prefix("deck:") {
        return k.parse::<u8>().map(Choice::Deck).map_err(|_| format!("bad choice {s:?}"));
    }
    g.map.tile_of(s).map(Choice::Tile).ok_or_else(|| format!("bad choice {s:?}"))
}

impl Action {
    pub fn to_json(&self, g: &Game) -> Value {
        match *self {
            Action::Place { card, target } => {
                let t = match target {
                    Target::Tile(t) => json!(["cr", g.map.tile_name(t)]),
                    Target::Den(p) => json!(["hq", pname(p)]),
                };
                json!({"kind": "place", "card_id": g.cards.name_of(card), "target": t})
            }
            Action::Leader => json!({"kind": "leader"}),
            Action::Pass => json!({"kind": "pass"}),
            Action::Choice(c) => json!({"kind": "choice", "choice": choice_to_json(g, c)}),
        }
    }

    pub fn from_json(g: &Game, d: &Value) -> Result<Action, String> {
        match d["kind"].as_str() {
            Some("place") => {
                let card = g.cards.need(d["card_id"].as_str().unwrap_or(""))?;
                let where_ = d["target"][1].as_str().unwrap_or("");
                let target = match d["target"][0].as_str() {
                    Some("cr") => Target::Tile(g.map.tile_of(where_).ok_or_else(|| format!("unknown tile {where_:?}"))?),
                    Some("hq") => Target::Den(player_from(where_)?),
                    other => return Err(format!("unknown target kind {other:?}")),
                };
                Ok(Action::Place { card, target })
            }
            Some("leader") => Ok(Action::Leader),
            Some("pass") => Ok(Action::Pass),
            Some("choice") => Ok(Action::Choice(choice_from_json(g, &d["choice"])?)),
            other => Err(format!("unknown action kind {other:?}")),
        }
    }
}
