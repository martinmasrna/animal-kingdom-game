//! The saved position: `State::to_json` and `State::from_json`, in the shape of the Python engine's `GameState.to_dict`
//! (a match saved by either engine loads in the other).

use std::sync::Arc;

use serde_json::{json, Map, Value};
use smallvec::SmallVec;

use crate::actions::{choice_from_json, choice_to_json};
use crate::data::*;
use crate::events::Events;
use crate::rng::{CowRng, PyRandom};
use crate::state::*;

fn unit_to_json(g: &Game, u: &Unit) -> Value {
    json!({"card_id": g.cards.name_of(u.card), "owner": pname(u.owner), "iid": u.iid, "retaliation_used": u.retaliation_used,
           "strength_mod": u.strength_mod, "cost_mod": u.cost_mod, "made": u.made})
}

fn unit_from_json(g: &Game, v: &Value) -> Result<Unit, String> {
    Ok(Unit {
        card: g.cards.need(v["card_id"].as_str().unwrap_or(""))?,
        owner: player_from(v["owner"].as_str().unwrap_or(""))?,
        iid: v["iid"].as_i64().ok_or("a unit with no iid")? as i32,
        retaliation_used: v["retaliation_used"].as_bool().unwrap_or(false),
        strength_mod: v["strength_mod"].as_i64().unwrap_or(0) as i32,
        cost_mod: v["cost_mod"].as_i64().unwrap_or(0) as i32,
        made: v["made"].as_bool().unwrap_or(false),
    })
}

fn tiles_to_json(g: &Game, ts: &[Tile]) -> Value {
    Value::Array(ts.iter().map(|&t| Value::from(g.map.tile_name(t))).collect())
}

fn tiles_from_json(g: &Game, v: &Value) -> Result<Tiles, String> {
    v.as_array().ok_or("options must be a list")?.iter()
        .map(|x| g.map.tile_of(x.as_str().unwrap_or("")).ok_or_else(|| format!("unknown tile {x}")))
        .collect()
}

fn player_of(v: &Value) -> Result<Player, String> {
    player_from(v.as_str().unwrap_or(""))
}

fn int(v: &Value) -> i32 {
    v.as_i64().unwrap_or(0) as i32
}

pub fn step_to_json(g: &Game, s: &Step) -> Value {
    let card = |c: CardId| Value::from(g.cards.name_of(c));
    let mut m = Map::new();
    let mut put = |k: &str, v: Value| {
        m.insert(k.to_string(), v);
    };
    match &s.kind {
        StepKind::Mulligan { player, returned } => {
            put("op", "mulligan".into());
            put("player", pname(*player).into());
            put("returned", Value::Array(returned.iter().map(|c| card(*c)).collect()));
        }
        StepKind::CoverRemove { cr } => {
            put("op", "cover_remove".into());
            put("cr", g.map.tile_name(*cr).into());
        }
        StepKind::HungryFood { player, prey } => {
            put("op", "hungry_food".into());
            put("player", pname(*player).into());
            put("prey", (*prey).into());
        }
        StepKind::GainFood { player, amount } => {
            put("op", "gain_food".into());
            put("player", pname(*player).into());
            put("amount", (*amount).into());
        }
        StepKind::LeaderTrigger { player, card } => {
            put("op", "leader_trigger".into());
            put("player", pname(*player).into());
            put("card", g.cards.name_of(*card).into());
        }
        StepKind::Draw { player, n } => {
            put("op", "draw".into());
            put("player", pname(*player).into());
            put("n", (*n).into());
        }
        StepKind::DrawIfGone { player, prey, n } => {
            put("op", "draw_if_gone".into());
            put("player", pname(*player).into());
            put("prey", (*prey).into());
            put("n", (*n).into());
        }
        StepKind::Scout { player } => {
            put("op", "scout".into());
            put("player", pname(*player).into());
        }
        StepKind::PlaceToken { player, card: c, options } => {
            put("op", "place_token".into());
            put("player", pname(*player).into());
            put("card", card(*c));
            put("options", tiles_to_json(g, options));
        }
        StepKind::ToHand { player, card: c, n } => {
            put("op", "to_hand".into());
            put("player", pname(*player).into());
            put("card", card(*c));
            put("n", (*n).into());
        }
        StepKind::RemoveIid { iid, by_player } => {
            put("op", "remove_iid".into());
            put("iid", (*iid).into());
            put("by_player", by_player.map(pname).into());
        }
        StepKind::RemoveChoice { chooser, options, optional } => {
            put("op", "remove_choice".into());
            put("chooser", pname(*chooser).into());
            put("options", tiles_to_json(g, options));
            put("optional", (*optional).into());
        }
        StepKind::WeakenChoice { chooser, options, amount } => {
            put("op", "weaken_choice".into());
            put("chooser", pname(*chooser).into());
            put("options", tiles_to_json(g, options));
            put("amount", (*amount).into());
        }
    }
    if let Some(c) = s.by_card {
        put("by_card", card(c));
    }
    if let Some(i) = s.by_iid {
        put("by_iid", i.into());
    }
    if let Some(c) = s.choice {
        put("choice", choice_to_json(g, c));
    }
    Value::Object(m)
}

pub fn step_from_json(g: &Game, v: &Value) -> Result<Step, String> {
    let card = |x: &Value| g.cards.need(x.as_str().unwrap_or(""));
    let kind = match v["op"].as_str().unwrap_or("") {
        "mulligan" => StepKind::Mulligan {
            player: player_of(&v["player"])?,
            returned: v["returned"].as_array().map(|a| a.iter().map(&card).collect::<Result<_, _>>()).transpose()?.unwrap_or_default(),
        },
        "cover_remove" => StepKind::CoverRemove { cr: g.map.tile_of(v["cr"].as_str().unwrap_or("")).ok_or("cover_remove: unknown tile")? },
        "hungry_food" => StepKind::HungryFood { player: player_of(&v["player"])?, prey: int(&v["prey"]) },
        "gain_food" => StepKind::GainFood { player: player_of(&v["player"])?, amount: int(&v["amount"]) },
        "leader_trigger" => StepKind::LeaderTrigger { player: player_of(&v["player"])?, card: card(&v["card"])? },
        "draw" => StepKind::Draw { player: player_of(&v["player"])?, n: int(&v["n"]) },
        "draw_if_gone" => StepKind::DrawIfGone { player: player_of(&v["player"])?, prey: int(&v["prey"]), n: int(&v["n"]) },
        "scout" => StepKind::Scout { player: player_of(&v["player"])? },
        "place_token" => StepKind::PlaceToken { player: player_of(&v["player"])?, card: card(&v["card"])?, options: tiles_from_json(g, &v["options"])? },
        "to_hand" => StepKind::ToHand { player: player_of(&v["player"])?, card: card(&v["card"])?, n: int(&v["n"]) },
        "remove_iid" => StepKind::RemoveIid { iid: int(&v["iid"]), by_player: if v["by_player"].is_null() { None } else { Some(player_of(&v["by_player"])?) } },
        "remove_choice" => StepKind::RemoveChoice { chooser: player_of(&v["chooser"])?, options: tiles_from_json(g, &v["options"])?, optional: v["optional"].as_bool().unwrap_or(false) },
        "weaken_choice" => StepKind::WeakenChoice { chooser: player_of(&v["chooser"])?, options: tiles_from_json(g, &v["options"])?, amount: int(&v["amount"]) },
        other => return Err(format!("unknown effect step {other:?}")),
    };
    Ok(Step {
        by_card: match v.get("by_card") { Some(x) if !x.is_null() => Some(card(x)?), _ => None },
        by_iid: v.get("by_iid").and_then(|x| x.as_i64()).map(|i| i as i32),
        choice: match v.get("choice") { Some(x) => Some(choice_from_json(g, x)?), None => None },
        kind,
    })
}

pub fn pending_to_json(g: &Game, p: &Pending) -> Value {
    let options: Value = match &p.options {
        Options::Iids(v) => Value::Array(v.iter().map(|&i| Value::from(i)).collect()),
        Options::Tiles(v) => tiles_to_json(g, v),
        Options::Deck(n) => Value::Array((0..*n).map(|k| Value::from(format!("deck:{k}"))).collect()),
    };
    let mut v = json!({"mode": "choice", "chooser": pname(p.chooser), "optional": p.optional, "options": options});
    if p.mulligan {
        v["kind"] = "mulligan".into();
    }
    v
}

fn pending_from_json(g: &Game, v: &Value) -> Result<Pending, String> {
    let opts = v["options"].as_array().ok_or("pending: options must be a list")?;
    let options = if opts.iter().all(|o| o.is_i64()) {
        Options::Iids(opts.iter().map(|o| o.as_i64().unwrap() as i32).collect())
    } else if opts.iter().all(|o| o.as_str().map_or(false, |s| s.starts_with("deck:"))) {
        Options::Deck(opts.len() as u8)
    } else {
        Options::Tiles(tiles_from_json(g, &v["options"])?)
    };
    Ok(Pending {
        chooser: player_of(&v["chooser"])?,
        optional: v["optional"].as_bool().unwrap_or(false),
        mulligan: v.get("kind").and_then(|k| k.as_str()) == Some("mulligan"),
        options,
    })
}

fn cards_to_json(g: &Game, cs: &[CardId]) -> Value {
    Value::Array(cs.iter().map(|&c| Value::from(g.cards.name_of(c))).collect())
}

fn cards_from_json<C: FromIterator<CardId>>(g: &Game, v: &Value) -> Result<C, String> {
    v.as_array().ok_or("expected a list of card ids")?.iter().map(|x| g.cards.need(x.as_str().unwrap_or(""))).collect()
}

fn pair<T>(v: &Value, f: impl Fn(&Value) -> Result<T, String>) -> Result<[T; 2], String> {
    Ok([f(&v["A"])?, f(&v["B"])?])
}

impl State {
    pub fn to_json(&self) -> Value {
        let g = &*self.g;
        let mut board = Map::new();
        for &t in self.board.tiles() {
            board.insert(g.map.tile_name(t).to_string(), Value::Array(self.board.stack(t).iter().map(|u| unit_to_json(g, u)).collect()));
        }
        let ab = |f: &dyn Fn(usize) -> Value| json!({"A": f(0), "B": f(1)});
        let mut leaders = Map::new();
        for p in 0..2 {
            if let Some(l) = self.leaders[p] {
                leaders.insert(pname(p as Player).to_string(), json!({"id": g.cards.name_of(l)}));
            }
        }
        json!({
            "map_id": g.map.id,
            "board": board,
            "hands": ab(&|p| Value::Array(self.hands[p].iter().map(|u| unit_to_json(g, u)).collect())),
            "decks": ab(&|p| cards_to_json(g, &self.decks[p])),
            "starting_decks": ab(&|p| cards_to_json(g, &self.starting_decks[p])),
            "remove_pile": cards_to_json(g, &self.remove_pile),
            "made": ab(&|p| cards_to_json(g, &self.made[p])),
            "pile_owners": self.pile_owners.iter().map(|&o| if o == NO_OWNER { Value::Null } else { Value::from(pname(o)) }).collect::<Vec<_>>(),
            "leaders": leaders,
            "food": ab(&|p| self.food[p].into()),
            "current": pname(self.current),
            "first_player": pname(self.first_player),
            "rng": {"version": 3, "state": self.rng.state_words(), "gauss": Value::Null},
            "turn_counter": self.turn_counter,
            "mana_spent": self.mana_spent,
            "applied_this_turn": self.applied_this_turn,
            "played_this_turn": self.played_this_turn,
            "power_used": self.power_used,
            "power_discount": ab(&|p| self.power_discount[p].into()),
            "fatigue": ab(&|p| self.fatigue[p].into()),
            "food_lost": ab(&|p| self.food_lost[p].into()),
            "food_produced": ab(&|p| self.food_produced[p].into()),
            "raids": ab(&|p| self.raids[p].into()),
            "leeroy_growth": ab(&|p| self.leeroy_growth[p].into()),
            "scorched": g.map.regions.iter().enumerate().filter(|(i, _)| self.scorched & (1u64 << i) != 0).map(|(_, r)| Value::from(r.id.clone())).collect::<Vec<_>>(),
            "effect_steps_this_turn": self.effect_steps_this_turn,
            "caps": self.caps.iter().map(|c| json!({"cap": c.cap.name(), "player": pname(c.player), "turn": c.turn, "cards": cards_to_json(g, &c.cards)})).collect::<Vec<_>>(),
            "next_iid": self.next_iid,
            "effect_stack": self.effect_stack.iter().map(|s| step_to_json(g, s)).collect::<Vec<_>>(),
            "pending": self.pending.as_ref().map(|p| pending_to_json(g, p)),
            "scheduled": self.scheduled.iter().map(|s| json!({"iid": s.iid, "owner": pname(s.owner), "remaining": s.remaining, "step": step_to_json(g, &s.step)})).collect::<Vec<_>>(),
            "result": self.result.map(|r| json!({"winner": r.winner.map(pname), "reason": r.reason.name()})),
        })
    }

    pub fn from_json(g: Arc<Game>, d: &Value) -> Result<State, String> {
        if d["map_id"].as_str() != Some(g.map.id.as_str()) {
            return Err(format!("this engine plays {:?}, the position is on {}", g.map.id, d["map_id"]));
        }
        let gr = &*g;
        let mut board = Board::default();
        for (name, stack) in d["board"].as_object().ok_or("no board")? {
            let t = gr.map.tile_of(name).ok_or_else(|| format!("unknown tile {name:?}"))?;
            for u in stack.as_array().ok_or("a stack must be a list")? {
                board.push(t, unit_from_json(gr, u)?);
            }
        }
        let units = |v: &Value| -> Result<Hand, String> { v.as_array().ok_or("a hand must be a list")?.iter().map(|u| unit_from_json(gr, u)).collect() };
        let remove_pile: SmallVec<[CardId; 64]> = cards_from_json(gr, &d["remove_pile"])?;
        let pile_owners: SmallVec<[u8; 64]> = match d.get("pile_owners").and_then(|v| v.as_array()) {
            Some(a) => a.iter().map(|o| o.as_str().and_then(|s| player_from(s).ok()).unwrap_or(NO_OWNER)).collect(),
            None => remove_pile.iter().map(|_| NO_OWNER).collect(),
        };
        let made = match d.get("made") {
            Some(v) if v.is_object() => pair(v, |x| cards_from_json(gr, x))?,
            _ => [SmallVec::new(), SmallVec::new()], // a position saved before it was kept
        };
        let mut leaders = [None, None];
        if let Some(m) = d.get("leaders").and_then(|v| v.as_object()) {
            for (p, lead) in m {
                leaders[player_from(p)? as usize] = Some(gr.cards.need(lead["id"].as_str().unwrap_or(""))?);
            }
        }
        let starting: [Vec<CardId>; 2] = match d.get("starting_decks") {
            Some(v) if v.is_object() => [
                v.get("A").map(|x| cards_from_json(gr, x)).transpose()?.unwrap_or_default(),
                v.get("B").map(|x| cards_from_json(gr, x)).transpose()?.unwrap_or_default(),
            ],
            _ => [Vec::new(), Vec::new()],
        };
        let words: Vec<i64> = d["rng"]["state"].as_array().ok_or("no rng state")?.iter().map(|w| w.as_i64().unwrap_or(0)).collect();
        if words.len() != 625 {
            return Err("the rng state must hold 625 words".into());
        }
        let mut caps = Vec::new();
        for c in d.get("caps").and_then(|v| v.as_array()).map(|a| a.as_slice()).unwrap_or(&[]) {
            caps.push(Cap {
                cap: if c["cap"].as_str() == Some("actions") { CapKind::Actions } else { CapKind::EffectSteps },
                player: player_of(&c["player"])?,
                turn: int(&c["turn"]),
                cards: cards_from_json(gr, &c["cards"])?,
            });
        }
        let mut effect_stack = SmallVec::new();
        for s in d.get("effect_stack").and_then(|v| v.as_array()).map(|a| a.as_slice()).unwrap_or(&[]) {
            effect_stack.push(step_from_json(gr, s)?);
        }
        let mut scheduled = SmallVec::new();
        for s in d.get("scheduled").and_then(|v| v.as_array()).map(|a| a.as_slice()).unwrap_or(&[]) {
            scheduled.push(Scheduled { iid: int(&s["iid"]), owner: player_of(&s["owner"])?, remaining: int(&s["remaining"]), step: step_from_json(gr, &s["step"])? });
        }
        let pending = match d.get("pending") {
            Some(p) if !p.is_null() => Some(pending_from_json(gr, p)?),
            _ => None,
        };
        let result = match d.get("result") {
            Some(r) if !r.is_null() => Some(GameResult {
                winner: if r["winner"].is_null() { None } else { Some(player_of(&r["winner"])?) },
                reason: Reason::from(r["reason"].as_str().unwrap_or(""))?,
            }),
            _ => None,
        };
        let discount = match d.get("power_discount") {
            Some(v) if v.is_object() => [int(&v["A"]), int(&v["B"])],
            _ => [0, 0],
        };
        let fatigue = match d.get("fatigue") {
            Some(v) if v.is_object() => [int(&v["A"]), int(&v["B"])],
            _ => [0, 0], // a position saved before the rule
        };
        let food_lost = match d.get("food_lost") {
            Some(v) if v.is_object() => [int(&v["A"]), int(&v["B"])],
            _ => [0, 0], // a position saved before the Burn Djinn
        };
        let food_produced = match d.get("food_produced") {
            Some(v) if v.is_object() => [int(&v["A"]), int(&v["B"])],
            _ => [0, 0], // a position saved before the Food Djinn
        };
        let scorched = d.get("scorched").and_then(|v| v.as_array()).map_or(0u64, |ids| {
            gr.map.regions.iter().enumerate().filter(|(_, r)| ids.iter().any(|x| x.as_str() == Some(r.id.as_str()))).fold(0u64, |m, (i, _)| m | 1u64 << i)
        });
        let leeroy_growth = match d.get("leeroy_growth") {
            Some(v) if v.is_object() => [int(&v["A"]), int(&v["B"])],
            _ => [0, 0],
        };
        let raids = match d.get("raids") {
            Some(v) if v.is_object() => [int(&v["A"]), int(&v["B"])],
            _ => [0, 0], // a position saved before the Raider's power
        };
        let geti = |k: &str| d.get(k).map(int).unwrap_or(0);
        Ok(State {
            board,
            hands: pair(&d["hands"], units)?,
            decks: pair(&d["decks"], |v| cards_from_json(gr, v))?,
            starting_decks: Arc::new(starting),
            remove_pile,
            pile_owners,
            made,
            leaders,
            food: [int(&d["food"]["A"]), int(&d["food"]["B"])],
            current: player_of(&d["current"])?,
            first_player: player_of(&d["first_player"])?,
            rng: CowRng::new(PyRandom::from_state(&words)),
            turn_counter: geti("turn_counter"),
            mana_spent: geti("mana_spent"),
            applied_this_turn: geti("applied_this_turn"),
            played_this_turn: geti("played_this_turn"),
            power_used: d.get("power_used").and_then(|v| v.as_bool()).unwrap_or(false),
            power_discount: discount,
            fatigue,
            food_lost,
            food_produced,
            raids,
            scorched,
            leeroy_growth,
            effect_steps_this_turn: geti("effect_steps_this_turn"),
            caps,
            next_iid: geti("next_iid"),
            effect_stack,
            pending,
            scheduled,
            result,
            events: Events::default(),
            cause: None,
            cause_iid: None,
            g,
        })
    }
}
