//! The evaluation as a race to the winning food.
//!
//! A game is won at the winning food and nearly always by the regions' pay, so a position is a race: what each side has,
//! what its regions pay, how long the race still runs, and what each side's next turn can do to the other's pay. The
//! position is read as a list of numbers (`features`), each from quantities the rules compute: food, the regions' pay,
//! which tiles a side may place on, the strength an animal has, and, for the cards a seat cannot see, how often a hand
//! dealt from the opponent's unseen cards holds a card that pays for itself and is strong enough (`RaidOdds`). Nothing
//! here names a card. The score is the weighted sum; the weights are fitted to who won (`bot_bench fit`, which writes
//! `race_weights.json`), in food: a weight says how many food of lead one unit of its number is worth.
//!
//! The numbers are taken from the side that has just moved (M) against the side to move next (N), because the two are
//! not alike: N's next turn comes first.

use std::sync::OnceLock;

use crate::bots::eval::{hand_raid_from, RaidOdds, WIN};
use crate::data::*;
use crate::effects;
use crate::rules;
use crate::state::State;

/// Strengths the cover odds tell apart (0 to 15; stronger reads as 15).
pub const MAX_S: usize = 16;
/// Mana the odds are kept for (0 to 12; more reads as 12).
pub const MAX_M: usize = 13;

macro_rules! features {
    ($($name:ident $sign:literal: $doc:literal,)*) => {
        #[allow(non_camel_case_types, clippy::upper_case_acronyms)]
        #[derive(Clone, Copy)]
        #[repr(usize)]
        enum F { $($name,)* COUNT }
        pub const N_FEAT: usize = F::COUNT as usize;
        /// Each number's name and what it counts.
        pub const FEATURES: [(&str, &str); N_FEAT] = [$((stringify!($name), $doc),)*];
        /// The sign each number's weight must have, from what it means for M (+1 good for M, -1 bad, 0 either): the fit
        /// keeps a weight that comes out against its meaning at 0, since such a weight reads a coincidence of the games
        /// (a deck that both holds fliers and loses) that the search would then play for.
        pub const SIGNS: [i8; N_FEAT] = [$($sign,)*];
    };
}

features! {
    bias 0: "1: having just moved",
    first 1: "M's mana on its next turn less N's on the turn it is about to play (1 while M is the one who went first)",
    food 1: "M's food less N's",
    income 1: "M's regions' pay less N's",
    race 1: "the pay lead times the turns the race still runs",
    need 1: "how much nearer M is to the winning food, as a share of the way",
    swing_n1 -1: "the most pay N's next card can move: regions it completes on one tile plus M's regions that tile holds, times the chance N has the card",
    swing_n2 -1: "the same for N's second-best tile",
    swing_m1 1: "the most pay M's next card can move, as the board stands",
    swing_m2 1: "the same for M's second-best tile",
    swing_n_rest -1: "the same summed over N's third- to sixth-best tiles: what a turn of several cards can move",
    swing_m_rest 1: "the same for M",
    reach_n -1: "how near N's food, its regions' pay and the pay its three best tiles would add come to the winning food at the end of its next turn (0 at three short, 1 there)",
    reach_m 1: "the same for M at the end of its own next turn",
    near 1: "food of regions one tile short with no enemy on them, M's less N's",
    far 1: "the same for regions two tiles short",
    bodies 1: "animals on the board, M's less N's",
    strength 1: "their strength, M's less N's",
    risk_m -1: "M's animals N's next turn can cover, each by the chance N has the card",
    risk_n 1: "N's animals M's next turn can cover",
    hand 1: "cards in hand, M's less N's",
    raid_n -1: "food N's hand destroys in M's den next turn",
    raid_m 1: "food M's hand destroys in N's den on its next turn",
    lethal_n -1: "the chance N's raids empty M's den next turn",
    lethal_m 1: "the chance M's raids empty N's den on its next turn",
    close_n -1: "how near N's pay brings it to the winning food at the end of its next turn (0 at eight short, 1 there)",
    close_m 1: "the same for M at the end of its own next turn",
    room 1: "empty tiles a side may place on, M's less N's",
    cut_off -1: "animals not connected to their base, M's less N's",
    bodies_race 1: "the lead in animals times the turns the race still runs",
    strength_race 1: "the lead in strength times the turns the race still runs",
}

/// The fitted weights, in food, and the food that halves the odds (`scale`: the chance of winning is
/// 1 / (1 + exp(-score / scale))).
#[derive(Clone, Debug)]
pub struct RaceWeights {
    pub w: [f32; N_FEAT],
    pub scale: f32,
    /// N's regions pay it to the winning food at the end of the turn it is about to play.
    pub their_win: f32,
    /// M's last food goes to the card its empty deck cannot give it at the start of its next turn (fatigue).
    pub starve: f32,
}

impl RaceWeights {
    /// The weights the fit was started from: the hand-set evaluation's, carried over to these numbers.
    pub fn prior() -> RaceWeights {
        let mut w = [0.0; N_FEAT];
        w[F::food as usize] = 1.0;
        w[F::income as usize] = 2.5;
        w[F::near as usize] = 0.5;
        w[F::far as usize] = 0.1;
        w[F::bodies as usize] = 3.0;
        w[F::strength as usize] = 1.2;
        w[F::hand as usize] = 0.4;
        w[F::raid_n as usize] = -0.6;
        w[F::lethal_n as usize] = -25.0;
        w[F::lethal_m as usize] = 6.0;
        w[F::bias as usize] = -10.0;
        RaceWeights { w, scale: 15.0, their_win: 200.0, starve: 200.0 }
    }

    /// From the JSON `bot_bench fit` writes: {"scale": S, "weights": {name: food, ...}}. A name it lacks is 0.
    pub fn from_json(text: &str) -> Result<RaceWeights, String> {
        let v: serde_json::Value = serde_json::from_str(text).map_err(|e| format!("race weights: {e}"))?;
        let mut out = RaceWeights { w: [0.0; N_FEAT], ..RaceWeights::prior() };
        out.scale = v["scale"].as_f64().filter(|s| *s > 0.0).ok_or("race weights: no scale")? as f32;
        let ws = v["weights"].as_object().ok_or("race weights: no weights")?;
        for (i, (name, _)) in FEATURES.iter().enumerate() {
            out.w[i] = ws.get(*name).and_then(|x| x.as_f64()).unwrap_or(0.0) as f32;
        }
        Ok(out)
    }

    pub fn set(&mut self, name: &str, v: f32) -> Result<(), String> {
        match name {
            "scale" if v > 0.0 => self.scale = v,
            "their_win" => self.their_win = v,
            "starve" => self.starve = v,
            _ => match FEATURES.iter().position(|f| f.0 == name) {
                Some(i) => self.w[i] = v,
                None => return Err(format!("no race weight named {name:?}")),
            },
        }
        Ok(())
    }
}

/// The weights in `race_weights.json`, as the engine was built.
impl Default for RaceWeights {
    fn default() -> RaceWeights {
        static FITTED: OnceLock<RaceWeights> = OnceLock::new();
        FITTED.get_or_init(|| RaceWeights::from_json(include_str!("race_weights.json")).expect("race_weights.json")).clone()
    }
}

/// What a side's next turn can put on a tile: the chance it holds a card it can pay for that is stronger than s (`g`
/// any such card, `f` one that flies and so lands anywhere), and one that may take an empty tile.
#[derive(Clone, Copy, Debug)]
pub(crate) struct Cover {
    g: [f32; MAX_S],
    f: [f32; MAX_S],
    any_g: f32,
    any_f: f32,
}

/// From the hand `player` holds, with `mana`.
fn cover_of_hand(st: &State, player: Player, mana: i32) -> Cover {
    let (mut max_g, mut max_f, mut any_g, mut any_f) = (-1i32, -1i32, false, false);
    for u in &st.hands[player as usize] {
        if effects::unit_cost(st, u) > mana {
            continue;
        }
        let c = st.card(u.card);
        let s = effects::effective_strength(st, u);
        max_g = max_g.max(s);
        any_g |= !c.has(HUNGRY);
        if c.has(FLIGHT) {
            max_f = max_f.max(s);
            any_f |= !c.has(HUNGRY);
        }
    }
    let mut cov = Cover { g: [0.0; MAX_S], f: [0.0; MAX_S], any_g: any_g as u8 as f32, any_f: any_f as u8 as f32 };
    for s in 0..MAX_S as i32 {
        cov.g[s as usize] = (max_g > s) as u8 as f32;
        cov.f[s as usize] = (max_f > s) as u8 as f32;
    }
    cov
}

/// From the hands the opponent may hold (`odds`), with `mana`, when they will hold `cards`. The same few are asked for
/// all through a search, so each is worked out once (`RaidOdds::covers`).
fn cover_of_odds(odds: &RaidOdds, mana: i32, cards: f32) -> Cover {
    let m = mana.clamp(0, MAX_M as i32 - 1) as usize;
    let key = (m as u32, cards.to_bits());
    if let Some(c) = odds.covers.borrow().iter().find(|c| c.0 == key) {
        return c.1;
    }
    let cov = cover_of_odds_now(odds, m, cards);
    odds.covers.borrow_mut().push((key, cov));
    cov
}

fn cover_of_odds_now(odds: &RaidOdds, m: usize, cards: f32) -> Cover {
    let mut cov = Cover { g: odds.cover_g[m], f: odds.cover_f[m], any_g: odds.any_g[m], any_f: odds.any_f[m] };
    if odds.cards > 0.0 && (cards - odds.cards).abs() > 0.5 {
        // the odds were counted over hands of another size: one card in `odds.cards` misses with the same chance
        let k = (cards / odds.cards).max(0.0);
        let fix = |p: &mut f32| *p = 1.0 - (1.0 - *p).max(0.0).powf(k);
        cov.g.iter_mut().chain(cov.f.iter_mut()).for_each(fix);
        fix(&mut cov.any_g);
        fix(&mut cov.any_f);
    }
    cov
}

/// The position as numbers, from the side that has just moved (M, the one not to move) against the side to move (N).
/// `me` is the seat reading it: its own hand it reads as held, the opponent's through `odds`.
pub fn features(st: &State, me: Player, odds: &RaidOdds) -> [f32; N_FEAT] {
    features_inc(st, me, odds).0
}

/// The numbers, and N's regions' pay (which `evaluate` reads again).
fn features_inc(st: &State, me: Player, odds: &RaidOdds) -> ([f32; N_FEAT], i32) {
    let mut x = [0.0f32; N_FEAT];
    let n = st.current;
    let m = other(n);
    let pl = [m, n];
    let map = &st.g.map;
    let win = map.win_food as f32;
    let food = [st.food[m as usize] as f32, st.food[n as usize] as f32];
    let inc_n = rules::region_income(st, n);
    let inc = [rules::region_income(st, m) as f32, inc_n as f32];
    let own = [st.board.own[m as usize], st.board.own[n as usize]];
    let occ = st.board.occ;
    let all = map.all_tiles();

    // the animals
    let mut strength_at = [0u8; MAX_TILES];
    let (mut bodies, mut strength) = ([0.0f32; 2], [0.0f32; 2]);
    let mut left = occ;
    while left != 0 {
        let t = left.trailing_zeros() as usize;
        left &= left - 1;
        let u = st.board.top(t as Tile).unwrap();
        let s = effects::effective_strength(st, &u);
        strength_at[t] = s.clamp(0, MAX_S as i32 - 1) as u8;
        let k = (u.owner == n) as usize;
        bodies[k] += 1.0;
        strength[k] += s as f32;
    }

    // the regions: what each tile holds for its side, and what it would complete
    let (mut hold, mut gain) = ([[0.0f32; MAX_TILES]; 2], [[0.0f32; MAX_TILES]; 2]);
    let (mut held, mut base, mut near, mut far) = ([0.0f32; 2], [0.0f32; 2], [0.0f32; 2], [0.0f32; 2]);
    for r in &map.regions {
        let size = r.mask.count_ones();
        for k in 0..2 {
            let mine = r.mask & own[k];
            let c = mine.count_ones();
            if c == size {
                held[k] += 1.0;
                base[k] += r.food as f32;
                let mut ts = r.mask;
                while ts != 0 {
                    hold[k][ts.trailing_zeros() as usize] += r.food as f32;
                    ts &= ts - 1;
                }
            } else if c + 1 == size {
                gain[k][(r.mask & !mine).trailing_zeros() as usize] += r.food as f32;
                if r.mask & own[1 - k] == 0 {
                    near[k] += r.food as f32;
                }
            } else if c + 2 == size && r.mask & own[1 - k] == 0 {
                far[k] += r.food as f32;
            }
        }
    }
    // a side whose regions pay more than their own food (a card on the board that says so) is paid that for each
    let extra = [if held[0] > 0.0 { (inc[0] - base[0]) / held[0] } else { 0.0 }, if held[1] > 0.0 { (inc[1] - base[1]) / held[1] } else { 0.0 }];

    // each side's next turn: its mana, where it may place, and the cards it may have
    let conn = [st.connected_occupied(m), st.connected_occupied(n)];
    let reach = [st.connectable(m, conn[0]), st.connectable(n, conn[1])];
    let mana = [rules::mana_total(st, m), rules::mana_left(st, n)];
    let cover = |k: usize| -> Cover {
        if pl[k] == me {
            cover_of_hand(st, me, mana[k])
        } else {
            // they draw a card before their next turn unless that turn has begun
            let draws = if k == 1 { 0 } else { (st.cfg().turn_draw_count.max(0) as usize).min(st.decks[pl[k] as usize].len()) };
            cover_of_odds(odds, mana[k], (st.hands[pl[k] as usize].len() + draws) as f32)
        }
    };
    let covers = [cover(0), cover(1)];
    let (mut swing, mut risk, mut rest, mut gains) = ([[0.0f32; 2]; 2], [0.0f32; 2], [0.0f32; 2], [0.0f32; 2]);
    for a in 0..2 {
        let d = 1 - a;
        let cov = &covers[a];
        // the six best tiles by the pay they move, and by the pay they add to a's own
        let (mut best, mut own_best) = ([0.0f32; 6], [0.0f32; 3]);
        let push = |list: &mut [f32], v: f32| {
            if v > list[list.len() - 1] {
                let mut i = list.len() - 1;
                while i > 0 && list[i - 1] < v {
                    list[i] = list[i - 1];
                    i -= 1;
                }
                list[i] = v;
            }
        };
        let mut ts = !own[a] & all;
        while ts != 0 {
            let t = ts.trailing_zeros() as usize;
            ts &= ts - 1;
            let bit = 1u64 << t;
            let ground = reach[a] & bit != 0;
            let (v, mine) = if occ & bit == 0 {
                let p = if ground { cov.any_g } else { cov.any_f };
                (p * gain[a][t] * (1.0 + extra[a]), p * gain[a][t] * (1.0 + extra[a]))
            } else {
                let s = strength_at[t] as usize;
                let p = if ground { cov.g[s] } else { cov.f[s] };
                risk[d] += p;
                (p * (gain[a][t] * (1.0 + extra[a]) + hold[d][t] * (1.0 + extra[d])), p * gain[a][t] * (1.0 + extra[a]))
            };
            push(&mut best, v);
            push(&mut own_best, mine);
        }
        swing[a] = [best[0], best[1]];
        rest[a] = best[2..].iter().sum();
        gains[a] = own_best.iter().sum();
    }

    // the raids each side's next turn could make
    let mut raid = [0.0f32; 2];
    let mut lethal = [0.0f32; 2];
    // the food a side's raids must take to end the game (less than the den holds where raids steal)
    let need = [effects::raid_to_win(st, m) as f32, effects::raid_to_win(st, n) as f32];
    for a in 0..2 {
        let d = 1 - a;
        let through = map.hq_front[pl[d] as usize] & conn[a] != 0;
        if pl[a] == me {
            let v = hand_raid_from(st, me, mana[a], conn[a]) as f32;
            raid[a] = v.min(food[d]);
            lethal[a] = (v >= need[a]) as u8 as f32;
        } else {
            let table = if through { &odds.raid_reach } else { &odds.raid_fly };
            let row = &table[mana[a].clamp(0, MAX_M as i32 - 1) as usize];
            if !row.is_empty() {
                let (mut sum, mut dead) = (0.0f32, 0.0f32);
                for &v in row.iter() {
                    sum += (v as f32).min(food[d]);
                    dead += (v as f32 >= need[a]) as u8 as f32;
                }
                raid[a] = sum / row.len() as f32;
                lethal[a] = dead / row.len() as f32;
            }
        }
    }

    let turns_left = ((win - food[0]) / (inc[0] + 1.0)).min((win - food[1]) / (inc[1] + 1.0)).clamp(0.0, 8.0);
    let free = |k: usize| (reach[k] & !occ).count_ones() as f32;
    let cut = |k: usize| (own[k] & !conn[k]).count_ones() as f32;
    x[F::bias as usize] = 1.0;
    x[F::first as usize] = (rules::mana_total(st, m) - rules::mana_total(st, n)) as f32;
    x[F::food as usize] = food[0] - food[1];
    x[F::income as usize] = inc[0] - inc[1];
    x[F::race as usize] = (inc[0] - inc[1]) * turns_left;
    x[F::need as usize] = (food[0] - food[1]) / (2.0 * win - food[0] - food[1]).max(1.0);
    x[F::swing_n1 as usize] = swing[1][0];
    x[F::swing_n2 as usize] = swing[1][1];
    x[F::swing_m1 as usize] = swing[0][0];
    x[F::swing_m2 as usize] = swing[0][1];
    x[F::swing_n_rest as usize] = rest[1];
    x[F::swing_m_rest as usize] = rest[0];
    x[F::reach_n as usize] = (1.0 - (win - food[1] - inc[1] - gains[1]) / 3.0).clamp(0.0, 1.0);
    x[F::reach_m as usize] = (1.0 - (win - food[0] - inc[0] - gains[0]) / 3.0).clamp(0.0, 1.0);
    x[F::near as usize] = near[0] - near[1];
    x[F::far as usize] = far[0] - far[1];
    x[F::bodies as usize] = bodies[0] - bodies[1];
    x[F::strength as usize] = strength[0] - strength[1];
    x[F::risk_m as usize] = risk[0];
    x[F::risk_n as usize] = risk[1];
    x[F::hand as usize] = st.hands[m as usize].len() as f32 - st.hands[n as usize].len() as f32;
    x[F::raid_n as usize] = raid[1];
    x[F::raid_m as usize] = raid[0];
    x[F::lethal_n as usize] = lethal[1];
    x[F::lethal_m as usize] = lethal[0];
    x[F::close_n as usize] = (1.0 - (win - food[1] - inc[1]) / 8.0).clamp(0.0, 1.0);
    x[F::close_m as usize] = (1.0 - (win - food[0] - inc[0]) / 8.0).clamp(0.0, 1.0);
    x[F::room as usize] = free(0) - free(1);
    x[F::cut_off as usize] = cut(0) - cut(1);
    x[F::bodies_race as usize] = (bodies[0] - bodies[1]) * turns_left;
    x[F::strength_race as usize] = (strength[0] - strength[1]) * turns_left;
    (x, inc_n)
}

/// Is the position one the weights do not score: over, or N's regions pay it to the winning food as it stands?
pub fn decided(st: &State) -> bool {
    st.result.is_some() || st.food[st.current as usize] + rules::region_income(st, st.current) >= st.g.map.win_food
}

/// How good `st` is for `me`, in food.
pub fn evaluate(st: &State, me: Player, w: &RaceWeights, odds: &RaidOdds) -> f32 {
    if let Some(r) = st.result {
        return match r.winner {
            Some(p) if p == me => WIN,
            Some(_) => -WIN,
            None => 0.0,
        };
    }
    let n = st.current;
    let m = other(n);
    let (x, inc_n) = features_inc(st, me, odds);
    let mut e = 0.0f32;
    for i in 0..N_FEAT {
        e += w.w[i] * x[i];
    }
    // N's regions pay it over the line when it ends the turn
    if st.food[n as usize] + inc_n >= st.g.map.win_food {
        e -= if n == me { 0.9 * WIN } else { w.their_win };
    }
    // fatigue: M draws at the start of its next turn, and an empty deck takes food instead
    let due = effects::fatigue_due(st, m, st.cfg().turn_draw_count);
    if due > 0 {
        e -= w.w[F::food as usize] * due.min(st.food[m as usize]) as f32;
        if due >= effects::raid_to_win(st, n) {
            e -= w.starve;
        }
    }
    if me == m { e } else { -e }
}
