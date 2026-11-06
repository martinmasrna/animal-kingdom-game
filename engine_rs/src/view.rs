//! A seat's view of the game, as `web/match.py` `Match._game_view` builds it: the board with each unit's live strength
//! and marks, the seat's hand, counts, food and income, what the opponent may still hold, the Remove Pile, and the
//! decision with its legal places and pending choice. The match's own parts (the clock, the move history, the numbered
//! events) are the browser's to add (`static/local/match.js`), as the server's Match adds them. Only the seat's own
//! hidden cards are in it. `tools/engine_rs/wasm_oracle.mjs` holds it equal to the Python view after every action.

use serde_json as sj;
use sj::json;

use crate::actions::{Action, Target};
use crate::cards::roar_condition;
use crate::data::*;
use crate::rules;
use crate::state::State;
use crate::statics;
use crate::strength::{card_strength, effective_strength, placement_strength};
use crate::value::{m_get_s, Value};

/// match.py ASKS: what a pending choice asks, by the effect step asking it.
fn asks(k: &str) -> &'static str {
    match k {
        "mulligan" => "mulligan",
        "magpie_steal" | "discard" => "discard",
        "raven_dig" => "shuffle",
        _ => "effect",
    }
}

fn counter(items: impl Iterator<Item = &'static str>) -> sj::Map<String, sj::Value> {
    let mut m = sj::Map::new();
    for c in items {
        let n = m.get(c).and_then(|v| v.as_i64()).unwrap_or(0);
        m.insert(c.to_string(), sj::Value::from(n + 1));
    }
    m
}

fn target_list(st: &State, t: &Target) -> sj::Value {
    Action::target_json(st, t)
}

fn conditional_reach(st: &State, card: CardId) -> bool {
    st.card(card).keywords & K_REACH == 0 && statics::reach_of(st, card) > 0
}

fn jelly_peek(st: &State, owner: Player, card: CardId) -> i32 {
    if owner > B {
        return 0;
    }
    match st.jelly[owner as usize].get(&card) {
        Some((left, counter)) if *left != 0 => *counter,
        _ => 0,
    }
}

/// match.py `_describe_option`: what a choice's option is, for the client to draw.
fn describe_option(st: &State, o: &Value, owner: Option<Player>) -> sj::Value {
    if let Some(s) = o.as_str() {
        if st.map().cr(s).is_some() {
            return json!({"v": s, "kind": "cr"});
        }
        if s == "den" {
            return json!({"v": s, "kind": "hq"});
        }
    }
    if let Value::Int(i) = o {
        for p in [A, B] {
            if let Some(u) = st.hands[p as usize].iter().find(|u| u.iid == *i) {
                return json!({"v": i, "kind": "hand", "id": st.cname(u.card)});
            }
        }
        for &cr in st.order.iter() {
            if let Some(u) = st.stack(cr).iter().find(|u| u.iid == *i) {
                return json!({"v": i, "kind": "cr", "cr": st.crname(cr), "id": st.cname(u.card)});
            }
        }
    }
    if let Some(s) = o.as_str() {
        if let Some(c) = st.card_id(s) {
            let Some(owner) = owner else { return json!({"v": s, "kind": "card", "id": s}) };
            let form = st.eaten_form(owner, c);
            return json!({"v": s, "kind": "card", "id": st.cname(form), "str": card_strength(st, form, owner) + jelly_peek(st, owner, c)});
        }
    }
    json!({"v": o.to_json(), "kind": "other", "label": o.to_json().to_string()})
}

/// match.py `_decision`: the legal places, roams and draw, and the pending choice.
fn decision(st: &State) -> (sj::Value, sj::Value) {
    let legal = rules::legal_actions(st);
    let mut places = sj::Map::new();
    let mut copies: Vec<(i64, Vec<sj::Value>)> = Vec::new();
    let mut roams = sj::Map::new();
    let mut draw = false;
    for a in &legal {
        match a {
            Action::Place { card, target, iid } => {
                let t = target_list(st, target);
                let ts = places.entry(st.cname(*card).to_string()).or_insert_with(|| sj::Value::Array(vec![]));
                let arr = ts.as_array_mut().unwrap();
                if !arr.contains(&t) {
                    arr.push(t.clone());
                }
                if let Some(i) = iid {
                    match copies.iter_mut().find(|(k, _)| k == i) {
                        Some((_, v)) => v.push(t),
                        None => copies.push((*i, vec![t])),
                    }
                }
            }
            Action::Roam { origin, target } => {
                let e = roams.entry(st.crname(*origin).to_string()).or_insert_with(|| sj::Value::Array(vec![]));
                e.as_array_mut().unwrap().push(target_list(st, target));
            }
            Action::Draw => draw = true,
            _ => {}
        }
    }
    if !copies.is_empty() {
        let chooser = match &st.pending {
            Some(p) => player_from(m_get_s(p, "chooser").unwrap_or("A")),
            None => st.current,
        };
        let hand = &st.hands[chooser.min(1) as usize];
        for u in hand.iter() {
            if copies.iter().any(|(k, _)| *k == u.iid) {
                continue;
            }
            let rep = hand.iter().find(|v| copies.iter().any(|(k, _)| *k == v.iid) && v.card == u.card && v.strength_counter == u.strength_counter);
            if let Some(rep) = rep {
                let ts = copies.iter().find(|(k, _)| *k == rep.iid).unwrap().1.clone();
                copies.push((u.iid, ts));
            }
        }
    }
    let mut out = json!({"draw": draw, "place": places, "roam": roams});
    if !copies.is_empty() {
        let m: sj::Map<String, sj::Value> = copies.into_iter().map(|(k, v)| (k.to_string(), sj::Value::Array(v))).collect();
        out["copies"] = sj::Value::Object(m);
    }
    let Some(p) = &st.pending else { return (out, sj::Value::Null) };
    let empty = crate::value::Map::new();
    let step = st.effect_stack.last().unwrap_or(&empty);
    let op = m_get_s(step, "op");
    let kind = if op == Some("choose") { m_get_s(step, "then") } else { op };
    let is_mull = op == Some("mulligan");
    let source = m_get_s(step, "by_card").filter(|c| st.card_id(c).is_some());
    let mode = m_get_s(p, "mode").unwrap_or("");
    let mut pending = json!({
        "mode": mode,
        "optional": p.get("optional").map(|v| v.as_bool()).unwrap_or(false),
        "source": source,
        "kind": kind.map(asks).unwrap_or("effect"),
        "returned": if is_mull { step.get("returned").and_then(|v| v.as_list()).map_or(0, |l| l.len()) } else { 0 },
        "cap": if is_mull { st.cfg().mulligan_cap(player_from(m_get_s(step, "player").unwrap_or("A")), st.first_player) } else { 0 },
        "options": [],
    });
    if mode == "choice" {
        let owner = m_get_s(step, "from_owner").or_else(|| m_get_s(p, "chooser")).map(player_from);
        let opts = p.get("options").and_then(|v| v.as_list()).map(|l| l.iter().map(|o| describe_option(st, o, owner)).collect::<Vec<_>>()).unwrap_or_default();
        pending["options"] = sj::Value::Array(opts);
    }
    if pending["kind"] == "shuffle" {
        pending["left"] = sj::Value::from(step.get("remaining").and_then(|v| v.as_i64()).unwrap_or(0));
    }
    (out, pending)
}

/// The engine's part of `Match._game_view(s, opp)` for seat `s`.
pub fn game_view(st: &State, s: Player) -> sj::Value {
    let opp = other(s);
    let pn = |p: Player| player_name(p);
    let to_act = if st.result.is_none() { Some(st.player_to_act()) } else { None };
    let timers: Vec<(i64, sj::Value)> = st.scheduled.iter().filter_map(|x| Some((x.get("iid")?.as_i64()?, x.get("remaining")?.to_json()))).collect();
    let mut board = sj::Map::new();
    for &cr in st.order.iter() {
        let stack = st.stack(cr);
        if stack.is_empty() {
            continue;
        }
        let units: Vec<sj::Value> = stack
            .iter()
            .map(|u| {
                let mut m = json!({"iid": u.iid, "id": st.cname(u.card), "owner": pn(u.owner), "str": effective_strength(st, u, None)});
                // the last timer for an iid wins, as a dict comprehension keeps the last
                if let Some((_, t)) = timers.iter().rev().find(|(i, _)| *i == u.iid) {
                    m["timer"] = t.clone();
                }
                if !statics::can_be_chosen(st, u, other(u.owner), Some(cr)) {
                    m["hidden"] = json!(true);
                }
                if statics::has_keyword(st, u, K_SPIKES, Some(cr)) && !u.retaliation_used {
                    m["spikes"] = json!(true);
                }
                if st.cname(u.card) == "boar" && u.retaliation_used {
                    m["spent"] = json!(true);
                }
                if statics::has_keyword(st, u, K_POISON, Some(cr)) {
                    m["poison"] = json!(true);
                }
                if !statics::can_be_removed(st, u, Some(cr), false) {
                    m["armor"] = json!(true);
                }
                if statics::inked(st, u) {
                    m["inked"] = json!(true);
                }
                m
            })
            .collect();
        board.insert(st.crname(cr).to_string(), sj::Value::Array(units));
    }
    let both = |f: &dyn Fn(Player) -> sj::Value| json!({"A": f(A), "B": f(B)});
    let mut region_food = sj::Map::new();
    for p in [A, B] {
        let mut m = sj::Map::new();
        for (i, r) in st.map().regions.iter().enumerate() {
            m.insert(r.id.clone(), sj::Value::from(rules::region_yield(st, p, i)));
        }
        region_food.insert(pn(p).to_string(), sj::Value::Object(m));
    }
    let hand: Vec<sj::Value> = st.hands[s as usize]
        .iter()
        .map(|u| {
            let mut m = json!({"iid": u.iid, "id": st.cname(u.card), "str": placement_strength(st, u)});
            if roar_condition(st, s, st.cname(u.card), None) == Some(true) || conditional_reach(st, u.card) {
                m["ready"] = json!(true);
            }
            m
        })
        .collect();
    let mut unseen_items: Vec<&'static str> = st.decks[opp as usize].iter().map(|c| st.cname(*c)).collect();
    unseen_items.extend(st.hands[opp as usize].iter().map(|u| st.cname(u.card)));
    for step in &st.effect_stack {
        if m_get_s(step, "player") != Some(pn(opp)) {
            continue;
        }
        for k in ["returned", "pulled", "shuffled"] {
            if let Some(l) = step.get(k).and_then(|v| v.as_list()) {
                unseen_items.extend(l.iter().filter_map(|c| c.as_str()));
            }
        }
    }
    // Counter + Counter: deck cards first, then the hand's, then the steps', each counted once per card
    let unseen = counter(unseen_items.into_iter());
    let pile: Vec<sj::Value> = st
        .remove_pile
        .iter()
        .zip(st.pile_owners.iter())
        .map(|(c, o)| json!({"id": st.cname(*c), "owner": o.map(pn), "str": card_strength(st, *c, o.unwrap_or(s))}))
        .collect();
    let mut g = json!({
        "round": st.turn_counter / 2 + 1,
        "current": pn(st.current),
        "toAct": to_act.map(pn),
        "first": pn(st.first_player),
        "actionsLeft": rules::turn_actions(st) - st.actions_taken_this_turn,
        "actionsTotal": rules::turn_actions(st),
        "canPass": rules::can_pass(st),
        "food": both(&|p| sj::Value::from(st.food[p as usize])),
        "income": both(&|p| sj::Value::from(rules::region_income(st, p))),
        "regionFood": region_food,
        "winFood": st.map().win_food,
        "board": board,
        "hand": hand,
        "handCount": both(&|p| sj::Value::from(st.hands[p as usize].len())),
        "eaten": both(&|p| sj::Value::from(st.hungry_eaten[p as usize])),
        "handLimit": st.cfg().hand_limit,
        "deckCount": both(&|p| sj::Value::from(st.decks[p as usize].len())),
        "deckLeft": counter(st.decks[s as usize].iter().map(|c| st.cname(*c))),
        "unseen": unseen,
        "removed": st.remove_pile.iter().map(|c| st.cname(*c)).collect::<Vec<_>>(),
        "pile": pile,
        "result": st.result.as_ref().map(|r| json!({"winner": r.winner.map(pn), "reason": r.reason})).unwrap_or(sj::Value::Null),
        "legal": null,
        "pending": null,
    });
    if statics::hand_revealed(st, opp) {
        g["revealedHand"] = sj::Value::Array(st.hands[opp as usize].iter().map(|u| json!({"iid": u.iid, "id": st.cname(u.card), "str": placement_strength(st, u)})).collect());
    }
    if to_act == Some(s) {
        let (legal, pending) = decision(st);
        g["legal"] = legal;
        g["pending"] = pending;
    } else if st.result.is_none() {
        if let Some(i) = rules::early_mulligan(st, s) {
            g["toAct"] = json!(pn(s));
            g["legal"] = json!({"draw": false, "place": {}, "roam": {}});
            let returned = st.effect_stack[i].get("returned").and_then(|v| v.as_list()).map_or(0, |l| l.len());
            let options: Vec<sj::Value> = st.hands[s as usize].iter().map(|u| describe_option(st, &Value::Int(u.iid), None)).collect();
            g["pending"] = json!({"mode": "choice", "optional": true, "source": null, "kind": "mulligan", "returned": returned,
                "cap": st.cfg().mulligan_cap(s, st.first_player), "options": options});
        }
    }
    let mull = st.pending.as_ref().map_or(false, |p| m_get_s(p, "kind") == Some("mulligan"));
    let mine = g["toAct"] == json!(pn(s));
    g["decision"] = json!(if st.result.is_some() {
        "over"
    } else if mull {
        "mulligan"
    } else if mine {
        if st.pending.is_some() { "your_choice" } else { "yours" }
    } else if st.pending.is_some() {
        "their_choice"
    } else {
        "theirs"
    });
    g
}
