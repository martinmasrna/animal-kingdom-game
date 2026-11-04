//! The raw position (bots/raw_position.py) and the raw-position network (learn/rawnet.py), for the search.
//!
//! Written in the Python extractor's exact order, field for field, so `test_raw_position.py` can hold both engines
//! to the same numbers. Card ids stay the engine's; the network's card table is reordered to them when it loads.

use serde_json as sj;

use crate::data::*;
use crate::rules;
use crate::state::{State, Unit};
use crate::statics;
use crate::strength::{aura_sources, card_strength, placement_strength, raw_strength, raw_strength_turn};
use crate::value::{m_flag, m_get_i, m_get_s, Map};

pub const N_CROSSROADS: usize = 15;
pub const N_TOP: usize = 25;
pub const N_UNDER: usize = 9;
pub const N_GLOBALS: usize = 32;
pub const N_BAGS: usize = 23;
pub const N_OWNER: usize = 4;
const OWNER_NONE: usize = 0;
const OWNER_MINE: usize = 1;
const OWNER_THEIRS: usize = 2;
const OWNER_WILD: usize = 3;
const SCHED_OPS: [&str; 8] = ["remove_iid", "gain_food", "draw", "grant_action", "cap_actions", "egg_hatch", "bird_egg_hatch", "locust_eat"];

pub const BAGS: [&str; N_BAGS] = [
    "hand", "hand_w", "deck", "deck_w", "pool", "pool_w", "opp_hand", "opp_hand_w", "opp_deck", "opp_deck_w",
    "pile_mine", "pile_mine_w", "pile_theirs", "pile_theirs_w", "pile_unknown", "locked_mine", "locked_theirs",
    "played_mine", "played_theirs", "deep_mine", "deep_theirs", "macaw_mine", "macaw_theirs",
];

#[derive(Clone, Debug, Default)]
pub struct RawPos {
    pub cr_card: [[Option<CardId>; 2]; N_CROSSROADS],
    pub cr_owner: [[usize; 2]; N_CROSSROADS],
    pub top_num: [[f64; N_TOP]; N_CROSSROADS],
    pub under_num: [[f64; N_UNDER]; N_CROSSROADS],
    pub bags: Vec<Vec<(CardId, f64)>>,
    pub globals: [f64; N_GLOBALS],
}

fn owner_code(owner: Player, me: Player) -> usize {
    if owner == me { OWNER_MINE } else if owner == WILD { OWNER_WILD } else { OWNER_THEIRS }
}

fn pidx(p: Player) -> usize {
    p.min(1) as usize
}

/// The crossroads in slot order: rows flipped for B so my den front is always row 1.
pub fn mirrored_crossroads(st: &State, me: Player) -> Vec<Cr> {
    let map = &st.g.map;
    let mut crs: Vec<(i32, i32, Cr)> = (0..map.crossroads.len())
        .map(|i| {
            let name = &map.crossroads[i];
            let mut it = name.split(',');
            let r: i32 = it.next().unwrap().parse().unwrap();
            let c: i32 = it.next().unwrap().parse().unwrap();
            (if me == B { 6 - r } else { r }, c, i as Cr)
        })
        .collect();
    crs.sort();
    crs.into_iter().map(|(_, _, cr)| cr).collect()
}

fn sched_on<'a>(st: &'a State, iid: i64) -> Vec<&'a Map> {
    st.scheduled.iter().filter(|s| m_get_i(s, "iid") == Some(iid)).collect()
}

fn step_op(s: &Map) -> Option<&'static str> {
    s.get("step").and_then(|v| v.as_map()).and_then(|m| m_get_s(m, "op"))
}

fn sched_features(entries: &[&Map], me: Player, out: &mut [f64]) {
    if entries.is_empty() {
        return;
    }
    let me_name = player_name(me);
    let mut ticks_mine = 0.0;
    let mut ticks_theirs = 0.0;
    let mut ticks_every = 0.0;
    let mut ops = [0.0; 8];
    let mut other = 0.0;
    let mut amount = 0.0;
    let mut any_buried = false;
    let mut min_rem = i64::MAX;
    for s in entries {
        let owner = m_get_s(s, "owner").unwrap_or("A");
        if owner == me_name {
            ticks_mine += 1.0;
        } else if owner == "wild" {
            ticks_every += 1.0;
        } else {
            ticks_theirs += 1.0;
        }
        match step_op(s).and_then(|op| SCHED_OPS.iter().position(|o| *o == op)) {
            Some(i) => ops[i] += 1.0,
            None => other += 1.0,
        }
        if let Some(step) = s.get("step").and_then(|v| v.as_map()) {
            amount += m_get_i(step, "amount").or_else(|| m_get_i(step, "n")).unwrap_or(0) as f64;
        }
        any_buried |= m_flag(s, "while_buried");
        min_rem = min_rem.min(m_get_i(s, "remaining").unwrap_or(0));
    }
    out[0] = entries.len() as f64;
    out[1] = min_rem as f64 / 3.0;
    out[2] = ticks_mine;
    out[3] = ticks_theirs;
    out[4] = ticks_every;
    out[5] = if any_buried { 1.0 } else { 0.0 };
    out[6..14].copy_from_slice(&ops);
    out[14] = other;
    out[15] = amount / 10.0;
}

fn pool_price(st: &State, owner: Player, cid: CardId) -> f64 {
    card_strength(st, st.eaten_form(owner, cid), owner) as f64 / 10.0
}

fn jelly_copies(st: &State, owner: Player, cid: CardId) -> (i32, f64) {
    if owner > B {
        return (0, 0.0);
    }
    match st.jelly[owner as usize].get(&cid) {
        Some(&(left, counter)) => (left, counter as f64),
        None => (0, 0.0),
    }
}

fn deck_bags(st: &State, owner: Player, cids: &[CardId], plain: &mut Vec<(CardId, f64)>, weighted: &mut Vec<(CardId, f64)>) {
    let mut left: Vec<(CardId, i32)> = Vec::new();
    for &cid in cids {
        let form = st.eaten_form(owner, cid);
        plain.push((form, 1.0));
        let mut price = pool_price(st, owner, cid);
        let slot = match left.iter().position(|(c, _)| *c == cid) {
            Some(i) => i,
            None => {
                left.push((cid, jelly_copies(st, owner, cid).0));
                left.len() - 1
            }
        };
        if left[slot].1 > 0 {
            left[slot].1 -= 1;
            price += jelly_copies(st, owner, cid).1 / 10.0;
        }
        weighted.push((form, price));
    }
}

pub fn extract(st: &State, me: Player) -> RawPos {
    let opp = other(me);
    let tc = st.turn_counter;
    let flags = &st.turn_flags;
    let sources = aura_sources(st);
    let mut pos = RawPos { bags: vec![Vec::new(); N_BAGS], ..Default::default() };
    let bag = |name: &str| BAGS.iter().position(|b| *b == name).unwrap();
    let (b_hand, b_hand_w, b_deck, b_deck_w) = (bag("hand"), bag("hand_w"), bag("deck"), bag("deck_w"));
    let (b_pool, b_pool_w, b_oh, b_oh_w, b_od, b_od_w) = (bag("pool"), bag("pool_w"), bag("opp_hand"), bag("opp_hand_w"), bag("opp_deck"), bag("opp_deck_w"));
    let (b_pm, b_pm_w, b_pt, b_pt_w, b_pu) = (bag("pile_mine"), bag("pile_mine_w"), bag("pile_theirs"), bag("pile_theirs_w"), bag("pile_unknown"));
    let (b_lm, b_lt, b_plm, b_plt, b_dm, b_dt, b_mm, b_mt) = (bag("locked_mine"), bag("locked_theirs"), bag("played_mine"), bag("played_theirs"), bag("deep_mine"), bag("deep_theirs"), bag("macaw_mine"), bag("macaw_theirs"));

    // play-order rank among each owner's top pieces
    let mut rank: Vec<(i64, f64)> = Vec::new();
    for owner in [me, opp, WILD] {
        let mut mine: Vec<&Unit> = st.tops().filter(|(_, u)| u.owner == owner).map(|(_, u)| u).collect();
        mine.sort_by_key(|u| u.play_seq);
        for (r, u) in mine.iter().enumerate() {
            rank.push((u.iid, r as f64 / 10.0));
        }
    }
    let rank_of = |iid: i64| rank.iter().find(|(i, _)| *i == iid).map(|(_, r)| *r).unwrap_or(0.0);

    let mut deep_removals = [0.0, 0.0];
    for (k, cr) in mirrored_crossroads(st, me).into_iter().enumerate() {
        let stack = st.stack(cr);
        if stack.is_empty() {
            pos.cr_card[k] = [None, None];
            pos.cr_owner[k] = [OWNER_NONE, OWNER_NONE];
            continue;
        }
        let top = stack.last().unwrap();
        let s_my = raw_strength_turn(st, top, Some(&sources), false).max(0) as f64 / 10.0;
        let s_their = raw_strength_turn(st, top, Some(&sources), true).max(0) as f64 / 10.0;
        let sched = sched_on(st, top.iid);
        let t = &mut pos.top_num[k];
        t[0] = s_my;
        t[1] = s_their;
        t[2] = top.strength_counter as f64 / 5.0;
        t[3] = if st.is_inked(top.iid) { 1.0 } else { 0.0 };
        t[4] = if top.retaliation_used { 1.0 } else { 0.0 };
        t[5] = if top.granted_roam { 1.0 } else { 0.0 };
        t[6] = if flags.roamed.contains(&top.iid) { 1.0 } else { 0.0 };
        t[7] = rank_of(top.iid);
        t[8] = (stack.len() - 1) as f64 / 4.0;
        sched_features(&sched, me, &mut t[9..]);
        if stack.len() >= 2 {
            let under = &stack[stack.len() - 2];
            let usched = sched_on(st, under.iid);
            let u = &mut pos.under_num[k];
            u[0] = raw_strength(st, under, Some(&sources)).max(0) as f64 / 10.0;
            u[1] = under.strength_counter as f64 / 5.0;
            u[2] = if st.is_inked(under.iid) { 1.0 } else { 0.0 };
            u[3] = if under.retaliation_used { 1.0 } else { 0.0 };
            u[4] = if under.granted_roam { 1.0 } else { 0.0 };
            u[5] = usched.len() as f64;
            u[6] = if usched.is_empty() { 0.0 } else { usched.iter().map(|s| m_get_i(s, "remaining").unwrap_or(0)).min().unwrap() as f64 / 3.0 };
            u[7] = if usched.iter().any(|s| step_op(s) == Some("remove_iid")) { 1.0 } else { 0.0 };
            u[8] = (stack.len() - 2) as f64 / 3.0;
            pos.cr_card[k] = [Some(top.card), Some(under.card)];
            pos.cr_owner[k] = [owner_code(top.owner, me), owner_code(under.owner, me)];
        } else {
            pos.cr_card[k] = [Some(top.card), None];
            pos.cr_owner[k] = [owner_code(top.owner, me), OWNER_NONE];
        }
        for deep in &stack[..stack.len().saturating_sub(2)] {
            if deep.owner == WILD {
                continue;
            }
            pos.bags[if deep.owner == me { b_dm } else { b_dt }].push((deep.card, 1.0));
            if sched_on(st, deep.iid).iter().any(|s| step_op(s) == Some("remove_iid")) {
                deep_removals[if deep.owner == me { 0 } else { 1 }] += 1.0;
            }
        }
    }

    // my hand and deck
    for u in st.hands[pidx(me)].iter() {
        pos.bags[b_hand].push((u.card, 1.0));
        pos.bags[b_hand_w].push((u.card, placement_strength(st, u) as f64 / 10.0));
        if u.locked_until_turn as i32 > tc {
            pos.bags[b_lm].push((u.card, 1.0));
        }
    }
    {
        let deck: Vec<CardId> = st.decks[pidx(me)].iter().copied().collect();
        let (mut plain, mut weighted) = (Vec::new(), Vec::new());
        deck_bags(st, me, &deck, &mut plain, &mut weighted);
        pos.bags[b_deck] = plain;
        pos.bags[b_deck_w] = weighted;
    }

    // the opponent's cards, from public state only
    let revealed = statics::hand_revealed(st, opp);
    let opp_hand = &st.hands[pidx(opp)];
    let locked: Vec<&Unit> = opp_hand.iter().filter(|u| u.locked_until_turn as i32 > tc).collect();
    for u in &locked {
        pos.bags[b_lt].push((u.card, 1.0));
    }
    if revealed {
        for u in opp_hand.iter() {
            if locked.iter().any(|l| l.iid == u.iid) {
                continue;
            }
            pos.bags[b_oh].push((u.card, 1.0));
            pos.bags[b_oh_w].push((u.card, placement_strength(st, u) as f64 / 10.0));
        }
        let deck: Vec<CardId> = st.decks[pidx(opp)].iter().copied().collect();
        let (mut plain, mut weighted) = (Vec::new(), Vec::new());
        deck_bags(st, opp, &deck, &mut plain, &mut weighted);
        pos.bags[b_od] = plain;
        pos.bags[b_od_w] = weighted;
    } else {
        let mut pool: Vec<CardId> = opp_hand.iter().map(|u| u.card).collect();
        pool.extend(st.decks[pidx(opp)].iter().copied());
        for l in &locked {
            if let Some(i) = pool.iter().position(|c| *c == l.card) {
                pool.remove(i);
            }
        }
        let (mut plain, mut weighted) = (Vec::new(), Vec::new());
        deck_bags(st, opp, &pool, &mut plain, &mut weighted);
        pos.bags[b_pool] = plain;
        pos.bags[b_pool_w] = weighted;
    }

    for (i, &cid) in st.remove_pile.iter().enumerate() {
        match st.pile_owners.get(i).copied().flatten() {
            Some(o) if o == me => {
                pos.bags[b_pm].push((cid, 1.0));
                pos.bags[b_pm_w].push((cid, pool_price(st, me, cid)));
            }
            Some(o) if o == opp => {
                pos.bags[b_pt].push((cid, 1.0));
                pos.bags[b_pt_w].push((cid, pool_price(st, opp, cid)));
            }
            _ => pos.bags[b_pu].push((cid, 1.0)),
        }
    }
    for &(_iid, cid) in flags.played[pidx(me)].iter() {
        pos.bags[b_plm].push((cid, 1.0));
    }
    for &(_iid, cid) in flags.played[pidx(opp)].iter() {
        pos.bags[b_plt].push((cid, 1.0));
    }
    if let Some(c) = st.last_roar[pidx(me)] {
        pos.bags[b_mm].push((c, 1.0));
    }
    if let Some(c) = st.last_roar[pidx(opp)] {
        pos.bags[b_mt].push((c, 1.0));
    }

    let actions_left = if st.current == me { (rules::turn_actions(st) - st.actions_taken_this_turn) as f64 } else { 0.0 };
    let (im, io) = (pidx(me), pidx(opp));
    let g = &mut pos.globals;
    g[0] = st.food[im] as f64 / 50.0;
    g[1] = st.food[io] as f64 / 50.0;
    g[2] = if st.current == me { 1.0 } else { 0.0 };
    g[3] = actions_left / 2.0;
    g[4] = st.idle_turns as f64;
    g[5] = st.units_placed_this_turn as f64 / 2.0;
    g[6] = flags.food_gained[im] as f64 / 20.0;
    g[7] = flags.food_gained[io] as f64 / 20.0;
    g[8] = flags.lost[im] as f64 / 2.0;
    g[9] = flags.lost[io] as f64 / 2.0;
    g[10] = flags.lost[2] as f64 / 2.0;
    g[11] = if flags.removed_any { 1.0 } else { 0.0 };
    g[12] = flags.roams[im] as f64 / 2.0;
    g[13] = flags.roams[io] as f64 / 2.0;
    g[14] = flags.free_roams[im] as f64;
    g[15] = flags.free_roams_used[im] as f64;
    g[16] = flags.free_roams[io] as f64;
    g[17] = flags.free_roams_used[io] as f64;
    g[18] = if flags.titan_discount[im] { 1.0 } else { 0.0 };
    g[19] = if flags.titan_discount[io] { 1.0 } else { 0.0 };
    g[20] = if st.roar_twice[im] == Some(tc) { 1.0 } else { 0.0 };
    g[21] = if st.roar_twice[io] == Some(tc) { 1.0 } else { 0.0 };
    g[22] = st.hungry_eaten[im] as f64 / 20.0;
    g[23] = st.hungry_eaten[io] as f64 / 20.0;
    g[24] = st.hands[im].len() as f64 / 8.0;
    g[25] = st.hands[io].len() as f64 / 8.0;
    g[26] = st.decks[im].len() as f64 / 30.0;
    g[27] = st.decks[io].len() as f64 / 30.0;
    g[28] = if revealed { 1.0 } else { 0.0 };
    g[29] = deep_removals[0];
    g[30] = deep_removals[1];
    g[31] = st.remove_pile.len() as f64 / 10.0;
    pos
}

/// The raw-position network: one learned vector per card, a shared crossroad encoder pooled by sum and max, the bags
/// as weighted sums of card vectors, a two-layer trunk, the winner logit (learn/rawnet.py's RawNet, dropout off).
#[derive(Clone, Debug)]
pub struct RawEval {
    pub dim: usize,
    pub names: Vec<String>,        // the artifact's card names, row by row
    pub src: Vec<Vec<f64>>,        // the artifact's card table, by name
    pub table: std::sync::OnceLock<Vec<Vec<f64>>>,      // by engine CardId, built at first use; the padding row is zeros
    pub slot_pos: Vec<Vec<f64>>,   // [15][8]
    pub slot_w1: Vec<Vec<f64>>,    // [in][hidden]
    pub slot_b1: Vec<f64>,
    pub slot_w2: Vec<Vec<f64>>,    // [hidden][out]
    pub slot_b2: Vec<f64>,
    pub trunk_w1: Vec<Vec<f64>>,
    pub trunk_b1: Vec<f64>,
    pub trunk_w2: Vec<Vec<f64>>,
    pub trunk_b2: Vec<f64>,
    pub out_w: Vec<Vec<f64>>,      // [hidden][2]
    pub out_b: Vec<f64>,
    pub scale: f64,
}

fn rows(d: &sj::Value, k: &str) -> Vec<Vec<f64>> {
    d[k].as_array().map(|rs| rs.iter().map(|r| r.as_array().unwrap().iter().map(|x| x.as_f64().unwrap_or(0.0)).collect()).collect()).unwrap_or_default()
}

fn vec(d: &sj::Value, k: &str) -> Vec<f64> {
    d[k].as_array().map(|a| a.iter().map(|x| x.as_f64().unwrap_or(0.0)).collect()).unwrap_or_default()
}

fn linear(x: &[f64], w: &[Vec<f64>], b: &[f64], relu: bool) -> Vec<f64> {
    let mut h = b.to_vec();
    for (i, &xi) in x.iter().enumerate() {
        if xi != 0.0 {
            let row = &w[i];
            for j in 0..h.len() {
                h[j] += xi * row[j];
            }
        }
    }
    if relu {
        for v in h.iter_mut() {
            if *v < 0.0 {
                *v = 0.0;
            }
        }
    }
    h
}

impl RawEval {
    pub fn from_json(d: &sj::Value) -> Result<RawEval, String> {
        let dim = d["dim"].as_u64().ok_or("rawnet artifact without dim")? as usize;
        let names: Vec<String> = d["cards"].as_array().ok_or("rawnet artifact without cards")?.iter().map(|x| x.as_str().unwrap_or("").to_string()).collect();
        let src = rows(d, "card_table");
        let bags: Vec<String> = d["bags"].as_array().map(|a| a.iter().map(|x| x.as_str().unwrap_or("").to_string()).collect()).unwrap_or_default();
        if bags != BAGS.iter().map(|s| s.to_string()).collect::<Vec<_>>() {
            return Err("rawnet artifact's bags differ from the engine's".into());
        }
        Ok(RawEval {
            dim,
            names,
            src,
            table: std::sync::OnceLock::new(),
            slot_pos: rows(d, "slot_pos"),
            slot_w1: rows(d, "slot_w1"), slot_b1: vec(d, "slot_b1"),
            slot_w2: rows(d, "slot_w2"), slot_b2: vec(d, "slot_b2"),
            trunk_w1: rows(d, "trunk_w1"), trunk_b1: vec(d, "trunk_b1"),
            trunk_w2: rows(d, "trunk_w2"), trunk_b2: vec(d, "trunk_b2"),
            out_w: rows(d, "out_w"), out_b: vec(d, "out_b"),
            scale: d.get("scale").and_then(|s| s.as_f64()).unwrap_or(1.0),
        })
    }

    /// The card table by engine id; a name the engine lacks gets the padding row (zeros).
    pub fn table(&self, cards: &Cards) -> &Vec<Vec<f64>> {
        self.table.get_or_init(|| {
            let mut table = vec![vec![0.0; self.dim]; cards.list.len()];
            for (i, name) in self.names.iter().enumerate() {
                if let Some(id) = cards.id_of(name) {
                    table[id as usize] = self.src[i].clone();
                }
            }
            table
        })
    }

    pub fn logit_of(&self, p: &RawPos, cards: &Cards) -> f64 {
        self.heads(p, cards)[0]
    }

    /// Both outputs: the winner logit and the den-lost-in-three logit.
    pub fn heads(&self, p: &RawPos, cards: &Cards) -> Vec<f64> {
        let dim = self.dim;
        let table = self.table(cards);
        let zero = vec![0.0; dim];
        let slot_out = self.slot_b2.len();
        let mut sum = vec![0.0; slot_out];
        let mut max = vec![f64::NEG_INFINITY; slot_out];
        let mut x: Vec<f64> = Vec::with_capacity(2 * (dim + N_OWNER) + N_TOP + N_UNDER + 8);
        for k in 0..N_CROSSROADS {
            x.clear();
            for layer in 0..2 {
                let e = match p.cr_card[k][layer] { Some(c) => &table[c as usize], None => &zero };
                x.extend_from_slice(e);
                let mut own = [0.0; N_OWNER];
                own[p.cr_owner[k][layer]] = 1.0;
                x.extend_from_slice(&own);
                if layer == 0 {
                    x.extend_from_slice(&p.top_num[k]);
                } else {
                    x.extend_from_slice(&p.under_num[k]);
                }
            }
            x.extend_from_slice(&self.slot_pos[k]);
            let h = linear(&x, &self.slot_w1, &self.slot_b1, true);
            let s = linear(&h, &self.slot_w2, &self.slot_b2, true);
            for j in 0..slot_out {
                sum[j] += s[j];
                if s[j] > max[j] {
                    max[j] = s[j];
                }
            }
        }
        let mut t: Vec<f64> = Vec::with_capacity(N_GLOBALS + 2 * slot_out + N_BAGS * dim);
        t.extend_from_slice(&p.globals);
        t.extend_from_slice(&sum);
        t.extend_from_slice(&max);
        for bag in &p.bags {
            let mut v = vec![0.0; dim];
            for &(c, w) in bag {
                let e = &table[c as usize];
                for j in 0..dim {
                    v[j] += w * e[j];
                }
            }
            t.extend_from_slice(&v);
        }
        let h1 = linear(&t, &self.trunk_w1, &self.trunk_b1, true);
        let h2 = linear(&h1, &self.trunk_w2, &self.trunk_b2, true);
        linear(&h2, &self.out_w, &self.out_b, false)
    }
}
