//! Effective strength (engine/strength.py): base or dynamic + global growth + the instance's counter + live anthems,
//! never below 0.

use crate::data::*;
use crate::state::{State, Unit};

pub fn count_units_controlled(st: &State, player: Player) -> i32 {
    st.owned_mask(player).count_ones() as i32
}

fn dynamic_strength(st: &State, rule: &str) -> i32 {
    match rule {
        "removed_units_count" => st.remove_pile.len() as i32,
        "removed_eggs_count" => st.cfg().egg_eater_growth * st.remove_pile.iter().filter(|c| st.card(**c).has_tag(T_EGG)).count() as i32,
        _ => panic!("unknown dynamic strength rule {rule:?}"),
    }
}

fn base_or_dynamic(st: &State, card: &Card) -> i32 {
    match card.base {
        Some(b) => b,
        None => dynamic_strength(st, card.dynamic.as_deref().unwrap_or("")),
    }
}

/// The family auras on the board: (owner, iid, kind).
pub type Sources = smallvec::SmallVec<[(Player, i64, u8); 4]>;

pub fn aura_sources(st: &State) -> Sources {
    st.cache.aura[..st.cache.aura_n as usize].iter().copied().collect()
}

fn aura_applies(st: &State, kind: u8, owner: Player, src_owner: Player, src_iid: i64, self_iid: Option<i64>, card: &Card, their_turn: bool) -> Option<i32> {
    let (fam, key, opp_only) = match kind {
        1 => (T_FISH, "mahi_mahi_anthem", false),
        2 => (T_HOOFED, "buffalo_anthem", true),
        _ => return None,
    };
    if src_owner != owner || Some(src_iid) == self_iid || !card.has_tag(fam) || st.is_inked(src_iid) || (opp_only && !their_turn) {
        return None;
    }
    Some(st.cfg().int(key))
}

pub fn small_starting_deck(st: &State, owner: Player, but: CardId) -> bool {
    if owner > B {
        return true;
    }
    let cap = st.cfg().capybara_small_max;
    st.starting_decks[owner as usize].iter().all(|&c| c == but || st.card(c).base.map(|s| s <= cap).unwrap_or(true))
}

/// The live "has +X" bonus for a unit of `card` controlled by `owner` (`self_iid` None: a prospective placement).
pub fn anthem_bonus(st: &State, card: &Card, owner: Player, self_iid: Option<i64>, sources: Option<&Sources>) -> i32 {
    anthem_bonus_turn(st, card, owner, self_iid, sources, st.current != owner)
}

/// The anthem as it stands on a chosen turn (`their_turn`: the owner's opponent to move), for an evaluation that asks
/// both (Giraffe, Crocodile and the Cape Buffalo's aura change with whose turn it is).
pub fn anthem_bonus_turn(st: &State, card: &Card, owner: Player, self_iid: Option<i64>, sources: Option<&Sources>, their_turn: bool) -> i32 {
    anthem_bonus_turn_cards(st, card, owner, self_iid, sources, their_turn) + guard_bonus(st, owner, their_turn)
}

/// [ACTION 8] (the actions prototype): +bonus to every animal of `owner` during the opponent's turn it was used for. On a
/// chosen `their_turn` while `owner` is still to move, it is the turn after this one.
pub fn guard_bonus(st: &State, owner: Player, their_turn: bool) -> i32 {
    if owner > B || !their_turn {
        return 0;
    }
    match st.action_guard[owner as usize] {
        Some((t, n)) => {
            let turn = if st.current == owner { st.turn_counter + 1 } else { st.turn_counter };
            if t == turn { n } else { 0 }
        }
        None => 0,
    }
}

fn anthem_bonus_turn_cards(st: &State, card: &Card, owner: Player, self_iid: Option<i64>, sources: Option<&Sources>, their_turn: bool) -> i32 {
    let cfg = st.cfg();
    const AURA_FAMILIES: u32 = T_FISH | T_HOOFED;
    if card.anthem_kind == 0 {
        if card.tags & AURA_FAMILIES == 0 {
            return 0;
        }
        let mut bonus = 0;
        let owned;
        let srcs: &Sources = match sources {
            Some(s) => s,
            None => {
                owned = aura_sources(st);
                &owned
            }
        };
        for &(so, si, kind) in srcs {
            if let Some(b) = aura_applies(st, kind, owner, so, si, self_iid, card, their_turn) {
                bonus += b;
            }
        }
        return bonus;
    }
    let tops: Vec<&Unit> = st.tops().filter(|(_, u)| u.owner == owner).map(|(_, u)| u).collect();
    let count = |tag: u32, include_self: bool| -> i32 {
        tops.iter().filter(|u| st.card(u.card).has_tag(tag) && (include_self || Some(u.iid) != self_iid)).count() as i32
    };
    let mut bonus = 0;
    let self_inked = self_iid.map(|i| st.is_inked(i)).unwrap_or(false);
    if !self_inked {
        match card.anthem_kind {
            1 => {
                if count(T_COLONY, true) >= cfg.int("guard_hornet_colony_threshold") {
                    bonus += cfg.int("guard_hornet_bonus");
                }
            }
            2 => {
                bonus += cfg.int("tuna_per_fish") * crate::statics::fish_count(st, owner, None, self_iid);
            }
            3 => bonus += cfg.int("marmot_per_step") * (st.food[owner.min(1) as usize] / cfg.int("marmot_food_step")),
            4 => bonus += cfg.int("hand_per_card") * st.hands[owner.min(1) as usize].len() as i32,
            5 => {
                if their_turn {
                    bonus += cfg.int("giraffe_bonus");
                }
            }
            6 => {
                if their_turn {
                    bonus -= cfg.int("crocodile_penalty");
                }
            }
            7 => {
                if owner <= B && !st.starting_decks[owner as usize].is_empty() && small_starting_deck(st, owner, card.idx) {
                    bonus += cfg.int("capybara_strength") - card.base.unwrap_or(0);
                }
            }
            _ => {}
        }
    }
    for u in &tops {
        let kind = st.card(u.card).family_aura;
        if kind == 0 {
            continue;
        }
        if let Some(b) = aura_applies(st, kind, owner, u.owner, u.iid, self_iid, card, their_turn) {
            bonus += b;
        }
    }
    bonus
}

/// Strength of a unit in play, below 0 too (an animal below 0 dies: effects::resolve removes it).
pub fn raw_strength(st: &State, unit: &Unit, sources: Option<&Sources>) -> i32 {
    let card = st.card(unit.card);
    if st.is_inked(unit.iid) {
        let base = card.base.unwrap_or(0);
        return base + st.growth(unit.owner, card.idx) + unit.strength_counter as i32 + anthem_bonus(st, card, unit.owner, Some(unit.iid), sources);
    }
    base_or_dynamic(st, card) + st.growth(unit.owner, card.idx) + unit.strength_counter as i32 + anthem_bonus(st, card, unit.owner, Some(unit.iid), sources)
}

/// `raw_strength` on a chosen turn (see `anthem_bonus_turn`).
pub fn raw_strength_turn(st: &State, unit: &Unit, sources: Option<&Sources>, their_turn: bool) -> i32 {
    let card = st.card(unit.card);
    let base = if st.is_inked(unit.iid) { card.base.unwrap_or(0) } else { base_or_dynamic(st, card) };
    base + st.growth(unit.owner, card.idx) + unit.strength_counter as i32 + anthem_bonus_turn(st, card, unit.owner, Some(unit.iid), sources, their_turn)
}

/// Strength of a unit in play, >= 0.
pub fn effective_strength(st: &State, unit: &Unit, sources: Option<&Sources>) -> i32 {
    raw_strength(st, unit, sources).max(0)
}

/// Strength of a unit of `card` for `owner` as a prospective placement, without any instance counter.
pub fn card_strength(st: &State, card: CardId, owner: Player) -> i32 {
    let c = st.card(card);
    (base_or_dynamic(st, c) + st.growth(owner, card) + anthem_bonus(st, c, owner, None, None)).max(0)
}

/// Effective strength of a hand instance if it were placed now.
pub fn placement_strength(st: &State, inst: &Unit) -> i32 {
    (card_strength(st, inst.card, inst.owner) + inst.strength_counter as i32).max(0)
}

/// Where a unit's strength comes from, for the player to see (engine/strength.py `strength_breakdown`, the same JSON):
/// printed, base, base_bonus, growth, changes [[source, n]], auras [[source, n]] (its own first, then allies' sorted), total.
pub fn breakdown(st: &State, unit: &Unit) -> serde_json::Value {
    use serde_json::{json, Value as J};
    let card = st.card(unit.card);
    let base = if st.is_inked(unit.iid) { card.base.unwrap_or(0) } else { base_or_dynamic(st, card) };
    let name = |c: Option<CardId>| c.map(|c| J::String(st.cname(c).to_string())).unwrap_or(J::Null);
    let mut base_bonus = 0;
    let mut changes: Vec<J> = Vec::new();
    let mut given = 0;
    for e in st.strength_sources.iter().filter(|e| e.iid == unit.iid) {
        if e.base {
            base_bonus += e.n as i32;
        } else {
            given += e.n as i32;
            changes.push(json!([name(e.src), e.n]));
        }
    }
    let rest = unit.strength_counter as i32 - base_bonus - given;
    if rest != 0 {
        changes.push(json!([J::Null, rest]));
    }
    let their_turn = st.current != unit.owner;
    let mut allies: Vec<(&'static str, i32)> = Vec::new();
    for (so, si, kind) in aura_sources(st) {
        if let Some(b) = aura_applies(st, kind, unit.owner, so, si, Some(unit.iid), card, their_turn) {
            let src = st.find_instance(si).map(|u| u.card).unwrap_or(unit.card);
            allies.push((st.cname(src), b));
        }
    }
    allies.sort();
    let guard = guard_bonus(st, unit.owner, their_turn);   // [ACTION 8], last (strength.py strength_breakdown)
    if guard != 0 {
        allies.push(("action_8", guard));
    }
    let own = anthem_bonus(st, card, unit.owner, Some(unit.iid), None) - allies.iter().map(|(_, b)| b).sum::<i32>();
    let mut auras: Vec<J> = Vec::new();
    if own != 0 {
        auras.push(json!([st.cname(unit.card), own]));
    }
    auras.extend(allies.into_iter().map(|(c, b)| json!([c, b])));
    json!({
        "printed": card.base, "base": base, "base_bonus": base_bonus, "growth": st.growth(unit.owner, card.idx),
        "changes": changes, "auras": auras, "total": raw_strength(st, unit, None),
    })
}
