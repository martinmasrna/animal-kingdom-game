//! Actions (engine/actions.py): draw, place, roam, pass, and a sub-choice; the same dict shape at the edge.

use crate::data::*;
use crate::state::State;
use crate::value::Value;
use serde_json as sj;

#[derive(Clone, Debug, PartialEq)]
pub enum Target {
    Cr(Cr),
    Hq(Player),
}

#[derive(Clone, Debug, PartialEq)]
pub enum Action {
    Draw,
    Place { card: CardId, target: Target, iid: Option<i64> },
    Roam { origin: Cr, target: Target },
    Pass,
    Choice(Value),
}

pub const SKIP: &str = "__skip__";

impl Action {
    pub fn is_skip(&self) -> bool {
        matches!(self, Action::Choice(Value::Str(s)) if *s == SKIP)
    }
    pub fn skip() -> Action {
        Action::Choice(Value::s(SKIP))
    }

    pub fn target_json(st: &State, t: &Target) -> sj::Value {
        match t {
            Target::Cr(c) => sj::json!(["cr", st.crname(*c)]),
            Target::Hq(p) => sj::json!(["hq", player_name(*p)]),
        }
    }

    pub fn to_json(&self, st: &State) -> sj::Value {
        match self {
            Action::Draw => sj::json!({"kind": "draw"}),
            Action::Pass => sj::json!({"kind": "pass"}),
            Action::Place { card, target, iid } => {
                let mut m = sj::json!({"kind": "place", "card_id": st.cname(*card), "target": Action::target_json(st, target)});
                if let Some(i) = iid {
                    m["iid"] = sj::Value::from(*i);
                }
                m
            }
            Action::Roam { origin, target } => sj::json!({"kind": "roam", "from": st.crname(*origin), "target": Action::target_json(st, target)}),
            Action::Choice(v) => sj::json!({"kind": "choice", "choice": v.to_json()}),
        }
    }

    pub fn target_from(st: &State, v: &sj::Value) -> Result<Target, String> {
        let kind = v[0].as_str().ok_or("bad target")?;
        let where_ = v[1].as_str().ok_or("bad target")?;
        match kind {
            "cr" => Ok(Target::Cr(st.map().cr(where_).ok_or_else(|| format!("unknown crossroad {where_:?}"))?)),
            "hq" => Ok(Target::Hq(player_from(where_))),
            _ => Err(format!("bad target kind {kind:?}")),
        }
    }

    pub fn from_json(st: &State, d: &sj::Value) -> Result<Action, String> {
        let kind = d["kind"].as_str().ok_or("action without kind")?;
        match kind {
            "draw" => Ok(Action::Draw),
            "pass" => Ok(Action::Pass),
            "place" => Ok(Action::Place {
                card: st.card_id(d["card_id"].as_str().ok_or("place without card")?).ok_or_else(|| format!("unknown card {:?}", d["card_id"]))?,
                target: Action::target_from(st, &d["target"])?,
                iid: d.get("iid").and_then(|i| i.as_i64()),
            }),
            "roam" => Ok(Action::Roam {
                origin: st.map().cr(d["from"].as_str().ok_or("roam without from")?).ok_or("unknown crossroad")?,
                target: Action::target_from(st, &d["target"])?,
            }),
            "choice" => Ok(Action::Choice(Value::from_json(&d["choice"]))),
            _ => Err(format!("unknown action kind {kind:?}")),
        }
    }
}
