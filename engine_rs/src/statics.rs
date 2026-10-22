//! Static modifiers (engine/statics.py): covering overrides, connection bypasses, removal immunity, the keywords an
//! animal has right now, grazing, region income modifiers, revealed hands.

use crate::data::*;
use crate::state::{State, Unit};
use crate::strength::{effective_strength, placement_strength};

pub fn inked(st: &State, unit: &Unit) -> bool {
    st.is_inked(unit.iid)
}
pub fn active(st: &State, unit: &Unit) -> bool {
    !st.is_inked(unit.iid)
}

/// `player`'s working top units of `card`: (crossroad, iid).
pub fn active_tops(st: &State, player: Player, card: Option<CardId>) -> Vec<(Cr, i64)> {
    let Some(card) = card else { return Vec::new() };
    st.tops().filter(|(_, u)| u.owner == player && u.card == card && active(st, u)).map(|(cr, u)| (cr, u.iid)).collect()
}

pub fn controls(st: &State, player: Player, card: Option<CardId>) -> bool {
    let Some(card) = card else { return false };
    st.tops().any(|(_, u)| u.owner == player && u.card == card && active(st, u))
}

pub fn crossroad_of(st: &State, iid: i64) -> Option<Cr> {
    st.find_unit(iid).map(|(cr, _)| cr)
}

fn keyword_aura(kind: u8) -> (u32, Option<u32>) {
    match kind {
        1 => (K_ARMOR, None),
        2 => (K_SPIKES, None),
        3 => (K_POISON, Some(T_FISH)),
        _ => (0, None),
    }
}

/// The keywords a board unit has right now: printed, plus any an adjacent ally's aura gives it; none while inked.
pub fn unit_keywords(st: &State, unit: &Unit, cr: Option<Cr>, as_top: bool) -> u32 {
    if st.is_inked(unit.iid) {
        return 0;
    }
    let card = st.card(unit.card);
    let kws = card.keywords;
    if !st.tops().any(|(_, t)| t.owner == unit.owner && st.card(t.card).keyword_aura != 0) {
        return kws;
    }
    let at = crossroad_of(st, unit.iid);
    let buried = !as_top && at.map(|a| st.top(a).map(|t| t.iid != unit.iid).unwrap_or(true)).unwrap_or(false);
    let cr = match cr.or(at) {
        Some(c) => c,
        None => return kws,
    };
    let mut extra = 0u32;
    for &nb in st.map().neighbors(cr) {
        let Some(top) = st.top(nb) else { continue };
        let kind = st.card(top.card).keyword_aura;
        if top.owner != unit.owner || kind == 0 || !active(st, top) {
            continue;
        }
        let (kw, family) = keyword_aura(kind);
        if buried && kw & (K_POISON | K_SPIKES) == 0 {
            continue;
        }
        if family.map(|f| card.has_tag(f)).unwrap_or(true) {
            extra |= kw;
        }
    }
    kws | extra
}

pub fn has_keyword(st: &State, unit: &Unit, kw: u32, cr: Option<Cr>) -> bool {
    unit_keywords(st, unit, cr, false) & kw != 0
}

/// May `placer` cover the enemy `target`? Strictly greater by default; the statics override it.
pub fn can_cover(st: &State, placer: &Unit, target: &Unit, roaming: bool) -> bool {
    let k = &st.g.known;
    let placer_card = st.card(placer.card);
    let owner = placer.owner;
    if Some(placer.card) == k.chameleon && (!roaming || active(st, placer)) {
        return true;
    }
    let placer_str = if roaming { effective_strength(st, placer, None) } else { placement_strength(st, placer) };
    let target_str = effective_strength(st, target, None);
    if roaming {
        if roam_covers_equal(st, owner) && placer_str >= target_str {
            return true;
        }
    } else {
        if placer_card.has_tag(T_CAT) && placer_str >= target_str && active_tops(st, owner, k.leopard).iter().any(|(_, iid)| *iid != placer.iid) {
            return true;
        }
        if placer_card.has_tag(T_FISH) && controls(st, owner, k.piranha_legend) {
            let fish = st.tops().filter(|(_, u)| u.owner == owner && st.card(u.card).has_tag(T_FISH)).count() as i32;
            if target_str <= fish {
                return true;
            }
        }
    }
    placer_str > target_str
}

pub fn can_roam(st: &State, unit: &Unit) -> bool {
    st.card(unit.card).has_kw(K_ROAM) && active(st, unit)
}

pub fn free_roams(st: &State, player: Player) -> i32 {
    let Some(card) = st.g.known.wolf_legend_3 else { return 0 };
    st.tops().filter(|(_, u)| u.owner == player && u.card == card && active(st, u)).count() as i32
}

pub fn roam_covers_equal(st: &State, owner: Player) -> bool {
    controls(st, owner, st.g.known.dhole)
}

pub fn reach_of(st: &State, card: CardId) -> i32 {
    if st.card(card).has_kw(K_REACH) || (Some(card) == st.g.known.great_white_shark && crate::value::m_flag(&st.turn_flags, "removed_any")) {
        st.cfg().reach
    } else {
        0
    }
}

/// Crossroads within `n` steps of a launch point (the den's front at 1, `occ` at 0), as a bitmask.
pub fn reach_crossroads(st: &State, player: Player, n: i32, occ: u32) -> u32 {
    let gm = st.map();
    let mut dist: Vec<i32> = vec![-1; gm.n()];
    let mut order: Vec<Cr> = Vec::new();
    for c in 0..gm.n() as Cr {
        if occ & (1 << c) != 0 {
            dist[c as usize] = 0;
            order.push(c);
        }
    }
    for &c in gm.front(player) {
        if dist[c as usize] < 0 {
            dist[c as usize] = 1;
            order.push(c);
        }
    }
    // Python: frontier sorted by distance (stable on dict order), then BFS.
    order.sort_by_key(|c| dist[*c as usize]);
    let mut qi = 0;
    while qi < order.len() {
        let cr = order[qi];
        qi += 1;
        let d = dist[cr as usize];
        if d >= n {
            continue;
        }
        for &nb in gm.neighbors(cr) {
            if dist[nb as usize] < 0 || dist[nb as usize] > d + 1 {
                dist[nb as usize] = d + 1;
                order.push(nb);
            }
        }
    }
    let mut mask = 0u32;
    for c in 0..gm.n() {
        if dist[c] >= 0 && dist[c] <= n {
            mask |= 1 << c;
        }
    }
    mask
}

pub fn ignores_connection(st: &State, card: CardId) -> bool {
    st.card(card).has_kw(K_FLIGHT)
}

fn neighbors_of_friendly_tag(st: &State, owner: Player, tag: u32) -> u32 {
    let mut out = 0u32;
    for (cr, top) in st.tops() {
        if top.owner == owner && st.card(top.card).has_tag(tag) {
            for &nb in st.map().neighbors(cr) {
                out |= 1 << nb;
            }
        }
    }
    out
}

pub fn extra_placement_crossroads(st: &State, card: CardId, owner: Player) -> u32 {
    let k = &st.g.known;
    let c = st.card(card);
    let mut out = 0u32;
    if Some(card) == k.cougar {
        out |= neighbors_of_friendly_tag(st, owner, T_CAT);
    }
    if c.has_tag(T_CANINE) && Some(card) != k.outrider && controls(st, owner, k.outrider) {
        out |= neighbors_of_friendly_tag(st, owner, T_CANINE);
    }
    out
}

pub fn can_be_removed(st: &State, unit: &Unit, cr: Option<Cr>, as_top: bool) -> bool {
    unit_keywords(st, unit, cr, as_top) & K_ARMOR == 0
}

pub fn can_be_chosen(st: &State, unit: &Unit, by_player: Player, cr: Option<Cr>) -> bool {
    if by_player != unit.owner {
        return unit_keywords(st, unit, cr, false) & K_STEALTH == 0;
    }
    true
}

/// Regions where `player` occupies every corner, as indexes into the map's regions.
pub fn regions_of(st: &State, player: Player) -> Vec<usize> {
    st.map().regions.iter().enumerate().filter(|(_, r)| r.corners.iter().all(|&c| st.owner_of(c) == Some(player))).map(|(i, _)| i).collect()
}

pub fn grazing(st: &State, unit: &Unit, cr: Option<Cr>) -> bool {
    let cr = match cr.or_else(|| crossroad_of(st, unit.iid)) {
        Some(c) => c,
        None => return false,
    };
    if st.top(cr).map(|t| t.iid != unit.iid).unwrap_or(true) {
        return false;
    }
    st.map().regions.iter().any(|r| r.corners.contains(&cr) && r.corners.iter().all(|&c| st.owner_of(c) == Some(unit.owner)))
}

pub fn region_food_modifier(st: &State, player: Player) -> i32 {
    let cfg = st.cfg();
    cfg.int("migration_bonus") * active_tops(st, player, st.g.known.wildebeest_legend).len() as i32
        - cfg.int("boar_penalty") * active_tops(st, other(player), st.g.known.boar_legend).len() as i32
}

pub fn food_cap(st: &State) -> Option<i32> {
    if !active_tops(st, A, st.g.known.tortoise_legend).is_empty() || !active_tops(st, B, st.g.known.tortoise_legend).is_empty() {
        return Some(st.cfg().int("tortoise_legend_food_cap"));
    }
    None
}

pub fn hand_revealed(st: &State, player: Player) -> bool {
    controls(st, other(player), st.g.known.giraffe_legend)
}
