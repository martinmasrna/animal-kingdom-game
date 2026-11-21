//! What the server and the tools read off the game beyond the rules themselves: a seat's view of a position, how a
//! unit shows on the board, the leaders, and the deck rules.

use serde_json::{json, Value};

use crate::cards::{LeaderKind, LEADERS};
use crate::data::*;
use crate::effects;
use crate::json::pending_to_json;
use crate::state::State;

/// Every leader in the game's order: {"id", "kind": "power" | "passive", "text", and a power's price as "cost"}.
pub fn leaders_json(cfg: &Config) -> Value {
    Value::Array(LEADERS.iter().map(|&(id, text)| {
        let power = crate::cards::behaviour(id).leader == Some(LeaderKind::Power);
        let mut o = json!({"id": id, "kind": if power { "power" } else { "passive" }, "text": text});
        if power {
            o["cost"] = Value::from(power_price(cfg, id));
        }
        o
    }).collect())
}

/// What a leader's power costs: the Elf's its own, every other the config's.
pub fn power_price(cfg: &Config, leader_id: &str) -> i32 {
    if leader_id == crate::cards::ELF { cfg.elf_power_cost } else { cfg.leader_power_cost }
}

/// Why `leader` can't lead `deck`, if it can't.
pub fn leader_problem(leader: Option<&str>, deck: &[String]) -> Option<String> {
    let Some(id) = leader else { return Some("a deck needs a leader".into()) };
    if crate::cards::behaviour(id).leader.is_none() {
        return Some(format!("'{id}' is not a leader"));
    }
    if !deck.iter().any(|c| c == id) {
        return Some(format!("the leader '{id}' must be in its deck"));
    }
    None
}

/// What makes a deck illegal; empty when it is legal. A deck is DECK_SIZE cards: collectible cards only, at most two
/// copies of a card and one of a legendary, and a leader, one of its own cards that can lead.
pub fn deck_problems(cards: &Cards, deck: &[String], leader: Option<&str>) -> Vec<String> {
    let mut problems = Vec::new();
    if deck.len() != DECK_SIZE {
        problems.push(format!("a deck has {DECK_SIZE} cards, not {}", deck.len()));
    }
    let mut counts: Vec<(&String, usize)> = Vec::new(); // in the order the list first names each card
    for cid in deck {
        match counts.iter_mut().find(|(c, _)| *c == cid) {
            Some((_, n)) => *n += 1,
            None => counts.push((cid, 1)),
        }
    }
    for (cid, n) in counts {
        match cards.id_of(cid).map(|c| cards.get(c)) {
            Some(card) if card.collectible => {
                let limit = copy_limit(card.legendary);
                if n > limit {
                    problems.push(format!("at most {limit} {}", card.name));
                }
            }
            _ => problems.push(format!("'{cid}' is not a collectible card")),
        }
    }
    if let Some(bad) = leader_problem(leader, deck) {
        problems.push(bad);
    }
    problems
}

/// What one seat may see: the opponent's hand and both decks as counts only.
pub fn seat_view(st: &State, player: Player) -> Value {
    let g = &*st.g;
    let opp = other(player) as usize;
    let me = player as usize;
    let mut board = serde_json::Map::new();
    for &t in st.board.tiles() {
        board.insert(g.map.tile_name(t).to_string(), Value::Array(st.board.stack(t).iter().map(|u| json!([g.cards.name_of(u.card), pname(u.owner)])).collect()));
    }
    json!({
        "player": pname(player), "to_act": pname(st.player_to_act()), "current": pname(st.current), "turn_counter": st.turn_counter,
        "board": board,
        "own_hand": st.hands[me].iter().map(|u| g.cards.name_of(u.card)).collect::<Vec<_>>(),
        "opponent_hand_count": st.hands[opp].len(), "own_deck_count": st.decks[me].len(), "opponent_deck_count": st.decks[opp].len(),
        "remove_pile": st.remove_pile.iter().map(|&c| g.cards.name_of(c)).collect::<Vec<_>>(),
        "food": {"A": st.food[0], "B": st.food[1]},
        "pending": st.pending.as_ref().map(|p| pending_to_json(g, p)),
        "result": st.result.map(|r| json!({"winner": r.winner.map(pname), "reason": r.reason.name()})),
    })
}

/// How the unit `iid` stands, on the board or in a hand: its strength, its cost from hand, and the marks a board piece
/// shows: "hidden" (the enemy can't choose it: Stealth), "spikes" until spent, "poison", "armor" (no ability removes it).
pub fn unit_view(st: &State, iid: i32) -> Option<Value> {
    let u = st.board.find(iid).map(|(_, u)| u).or_else(|| st.hands.iter().flatten().find(|u| u.iid == iid).copied())?;
    let card = st.card(u.card);
    Some(json!({
        "str": effects::effective_strength(st, &u), "cost": effects::unit_cost(st, &u),
        "hidden": !effects::can_be_chosen(st, &u, other(u.owner)),
        "spikes": card.has(SPIKES) && !u.retaliation_used,
        "poison": card.has(POISON),
        "armor": !effects::can_be_removed(st, &u),
    }))
}
