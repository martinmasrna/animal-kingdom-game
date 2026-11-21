//! What happened, in order: the server hands these to the players. Recorded only when asked (a search never asks), in
//! the shape the Python engine's `state.events` has.

use serde_json::{json, Map, Value};

use crate::data::*;
use crate::state::CapKind;

#[derive(Clone, Debug)]
pub enum Ev {
    TurnEnd { player: Player },
    TurnStart { player: Player, turn: i32 },
    Mulligan { player: Player, returned: i32, drawn: (i32, CardId) },
    TurnCapped { cap: CapKind, player: Player, turn: i32, cards: Vec<CardId> },
    Raid { player: Player, iid: i32, card: CardId, den: Player, strength: i32, n: i32 },
    Place { player: Player, iid: i32, card: CardId, cr: Tile },
    Cover { cr: Tile, iid: i32, card: CardId, owner: Player, by: i32 },
    Poisoned { iid: i32, card: CardId, owner: Player, by: i32 },
    Remove { cr: Tile, iid: i32, card: CardId, owner: Player, by: Option<Player> },
    /// A card burned from hand, past the hand limit.
    Burn { iid: i32, card: CardId, owner: Player },
    Food { player: Player, n: i32, income: bool },
    Draw { player: Player, cards: Vec<(i32, CardId)> },
    Strength { iid: i32, card: CardId, owner: Player, n: i32 },
    LeaderPower { player: Player, card: CardId },
}

#[derive(Debug)]
pub struct Recorded {
    pub cause: Option<CardId>,
    pub cause_iid: Option<i32>,
    pub ev: Ev,
}

#[derive(Debug, Default)]
pub struct Events {
    pub on: bool,
    pub list: Vec<Recorded>,
}

/// A clone of a position starts with no events on record (and keeps whether it records).
impl Clone for Events {
    fn clone(&self) -> Events {
        Events { on: self.on, list: Vec::new() }
    }
}

impl Events {
    pub fn push(&mut self, cause: Option<CardId>, cause_iid: Option<i32>, ev: Ev) {
        self.list.push(Recorded { cause, cause_iid, ev });
    }
}

impl Recorded {
    pub fn to_json(&self, g: &Game) -> Value {
        let card = |c: CardId| Value::from(g.cards.name_of(c));
        let tile = |t: Tile| Value::from(g.map.tile_name(t));
        let mut v = match &self.ev {
            Ev::TurnEnd { player } => json!({"e": "turn_end", "player": pname(*player)}),
            Ev::TurnStart { player, turn } => json!({"e": "turn_start", "player": pname(*player), "turn": turn}),
            Ev::Mulligan { player, returned, drawn } => json!({"e": "mulligan", "player": pname(*player), "returned": returned, "drawn": [drawn.0, card(drawn.1)]}),
            Ev::TurnCapped { cap, player, turn, cards } => json!({"e": "turn_capped", "cap": cap.name(), "player": pname(*player), "turn": turn,
                "cards": cards.iter().map(|c| card(*c)).collect::<Vec<_>>()}),
            Ev::Raid { player, iid, card: c, den, strength, n } => json!({"e": "raid", "player": pname(*player), "iid": iid, "card": card(*c), "den": pname(*den), "str": strength, "n": n}),
            Ev::Place { player, iid, card: c, cr } => json!({"e": "place", "player": pname(*player), "iid": iid, "card": card(*c), "cr": tile(*cr), "from_hand": true}),
            Ev::Cover { cr, iid, card: c, owner, by } => json!({"e": "cover", "cr": tile(*cr), "iid": iid, "card": card(*c), "owner": pname(*owner), "by": by}),
            Ev::Poisoned { iid, card: c, owner, by } => json!({"e": "poisoned", "iid": iid, "card": card(*c), "owner": pname(*owner), "by": by}),
            Ev::Remove { cr, iid, card: c, owner, by } => json!({"e": "remove", "cr": tile(*cr), "iid": iid, "card": card(*c), "owner": pname(*owner), "by": by.map(pname)}),
            Ev::Burn { iid, card: c, owner } => json!({"e": "remove", "zone": "hand", "iid": iid, "card": card(*c), "owner": pname(*owner)}),
            Ev::Food { player, n, income } => {
                let mut m = json!({"e": "food", "player": pname(*player), "n": n});
                if *income {
                    m["income"] = Value::Bool(true);
                }
                m
            }
            Ev::Draw { player, cards } => json!({"e": "draw", "player": pname(*player), "cards": cards.iter().map(|(i, c)| json!([i, card(*c)])).collect::<Vec<_>>()}),
            Ev::Strength { iid, card: c, owner, n } => json!({"e": "strength", "iid": iid, "card": card(*c), "owner": pname(*owner), "n": n}),
            Ev::LeaderPower { player, card: c } => json!({"e": "leader_power", "player": pname(*player), "card": card(*c)}),
        };
        let m: &mut Map<String, Value> = v.as_object_mut().unwrap();
        if let Some(c) = self.cause {
            m.insert("cause".into(), card(c));
            if let Some(i) = self.cause_iid {
                m.insert("cause_iid".into(), Value::from(i));
            }
        }
        v
    }
}
