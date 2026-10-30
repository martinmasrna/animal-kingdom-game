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
    let cfg = st.cfg();
    let their_turn = st.current != owner;
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
