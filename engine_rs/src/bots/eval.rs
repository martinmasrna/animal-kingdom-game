//! How good a position is for one seat, in food.
//!
//! Every number comes from the rules: the food each side has, the food its regions pay as the rules compute it, the
//! food its hand could destroy in the enemy den next turn as a raid computes it, the animals on the board at the
//! strength the rules give them, and the cards in hand at the cost the rules ask. Nothing here names a card.

use smallvec::SmallVec;

use crate::bots::seat::Unseen;
use crate::data::*;
use crate::effects;
use crate::rng::PyRandom;
use crate::rules;
use crate::state::{State, Unit};

/// A game won; a game lost is its negative.
pub const WIN: f32 = 1000.0;

/// The evaluation's weights, each the food one unit of its term is worth.
#[derive(Clone, Debug)]
pub struct Weights {
    /// A food of lead.
    pub food: f32,
    /// A food of income lead, each turn: how many turns a board's income is expected to last.
    pub income: f32,
    /// A food the opponent's hand could destroy in my den on their next turn.
    pub threat_theirs: f32,
    /// The chance their hand empties my den on their next turn.
    pub lethal_theirs: f32,
    /// A food my hand could destroy in their den on my next turn.
    pub threat_mine: f32,
    /// My hand could empty their den on my next turn.
    pub lethal_mine: f32,
    /// Their regions pay them to the winning food at the end of their coming turn.
    pub income_win_theirs: f32,
    /// My regions would pay me to the winning food at the end of my next turn.
    pub income_win_mine: f32,
    /// An animal on the board.
    pub body: f32,
    /// A point of its strength.
    pub strength: f32,
    /// A food of a region one tile short of mine, with no enemy on it.
    pub region_near: f32,
    /// A food of a region two tiles short of mine, with no enemy on it.
    pub region_far: f32,
    /// The player whose turn comes next loses their last food to the card their empty deck cannot give them (fatigue).
    pub starve: f32,
    /// A card in hand.
    pub hand_card: f32,
    /// A mana of its cost.
    pub hand_cost: f32,
    /// Ranking unfinished turns only (when the width cap must choose which to follow): a mana still unspent.
    pub mana_rank: f32,
}

/// The numbers are a first guess corrected by one scan (2026-11-22, `tools/bot_bench/README.md`): each weight at 0, a
/// half, double and four times its guess against the guess itself, 2,000 games each on Martin's five decks. The scan
/// moved three things: an animal on the board is worth about eight times the guess (body 0.4 and strength 0.15 a point
/// lost to 3.0 and 1.2 by 55% to 45%); a raid my hand could make next turn is worth nothing until it is made (counted, the
/// bot held a flier all game for the threat); and a hand card's cost says nothing its count does not. Everything else
/// played the same from a half to four times its guess. Nobody has tuned these against each other.
impl Default for Weights {
    fn default() -> Weights {
        Weights {
            food: 1.0,
            income: 2.5,
            threat_theirs: 0.6,
            lethal_theirs: 25.0,
            threat_mine: 0.0,
            lethal_mine: 6.0,
            income_win_theirs: 200.0,
            income_win_mine: 0.0,
            body: 3.0,
            strength: 1.2,
            region_near: 0.5,
            region_far: 0.1,
            starve: 200.0,
            hand_card: 0.4,
            hand_cost: 0.0,
            mana_rank: 0.3,
        }
    }
}

impl Weights {
    pub fn set(&mut self, name: &str, v: f32) -> Result<(), String> {
        let slot = match name {
            "food" => &mut self.food,
            "income" => &mut self.income,
            "threat_theirs" => &mut self.threat_theirs,
            "lethal_theirs" => &mut self.lethal_theirs,
            "threat_mine" => &mut self.threat_mine,
            "lethal_mine" => &mut self.lethal_mine,
            "income_win_theirs" => &mut self.income_win_theirs,
            "income_win_mine" => &mut self.income_win_mine,
            "body" => &mut self.body,
            "strength" => &mut self.strength,
            "region_near" => &mut self.region_near,
            "region_far" => &mut self.region_far,
            "starve" => &mut self.starve,
            "hand_card" => &mut self.hand_card,
            "hand_cost" => &mut self.hand_cost,
            "mana_rank" => &mut self.mana_rank,
            _ => return Err(format!("no weight named {name:?}")),
        };
        *slot = v;
        Ok(())
    }
}

/// May this card be played into a den: with a connected animal on the enemy's base (`reach`), or flying.
#[inline]
fn raids(st: &State, card: CardId, reach: bool) -> bool {
    let c = st.card(card);
    !c.has(HUNGRY) && (reach || c.has(FLIGHT))
}

/// The most food a set of (cost, food) raids destroys for `mana`.
fn best_raids(items: &[(i32, i32)], mana: i32) -> i32 {
    let cap = mana.clamp(0, 31) as usize;
    let mut best = [0i32; 32];
    for &(cost, food) in items {
        let cost = cost.max(0) as usize;
        if cost > cap || food <= 0 {
            continue;
        }
        for m in (cost..=cap).rev() {
            best[m] = best[m].max(best[m - cost] + food);
        }
    }
    best[cap]
}

/// What the opponent's unseen hand could destroy in my den on their next turn, over sampled hands: for each sample the
/// food with a connected animal on my base, and the food its fliers alone destroy. Made once a search, from what the
/// seat knows; the same for every position of the turn (their hand and mana do not change while I play).
#[derive(Clone, Debug, Default)]
pub struct RaidOdds {
    pub reach: SmallVec<[i32; 16]>,
    pub fly: SmallVec<[i32; 16]>,
    /// The average cost of a card in their unseen pool.
    pub avg_cost: f32,
}

impl RaidOdds {
    /// From `samples` hands dealt from their unseen pool: the cards they hold, and the one their turn will draw.
    pub fn sample(st: &State, me: Player, seen: &Unseen, samples: usize, rng: &mut PyRandom) -> RaidOdds {
        let opp = other(me);
        let hand = &st.hands[opp as usize];
        // their coming turn's mana: this turn's when it is already theirs
        let mana = rules::mana_total(st, opp);
        let draws = (st.cfg().turn_draw_count.max(0) as usize).min(st.decks[opp as usize].len());
        let mut odds = RaidOdds::default();
        let total: i32 = seen.pool.iter().map(|&c| st.card(c).cost).sum();
        odds.avg_cost = if seen.pool.is_empty() { 0.0 } else { total as f32 / seen.pool.len() as f32 };
        let mut pool = seen.pool.clone();
        let mut held: SmallVec<[Unit; 16]> = SmallVec::new();
        for _ in 0..samples.max(1) {
            rng.shuffle(&mut pool);
            held.clear();
            let mut next = pool.iter();
            for (i, u) in hand.iter().enumerate() {
                let mut u = *u;
                if seen.unknown_slots.contains(&i) {
                    match next.next() {
                        Some(&c) => u.card = c,
                        None => continue,
                    }
                }
                held.push(u);
            }
            for _ in 0..draws {
                if let Some(&c) = next.next() {
                    held.push(Unit::new(c, opp, -1));
                }
            }
            let (mut all, mut fly): (SmallVec<[(i32, i32); 16]>, SmallVec<[(i32, i32); 16]>) = (SmallVec::new(), SmallVec::new());
            for u in &held {
                if !raids(st, u.card, true) {
                    continue;
                }
                let item = (effects::unit_cost(st, u), effects::raid_food(st, opp, u.card, effects::effective_strength(st, u)));
                all.push(item);
                if raids(st, u.card, false) {
                    fly.push(item);
                }
            }
            odds.reach.push(best_raids(&all, mana));
            odds.fly.push(best_raids(&fly, mana));
        }
        odds
    }
}

/// The food `player`'s own hand could destroy in the enemy den with `mana`, from where the position stands.
pub fn hand_raid(st: &State, player: Player, mana: i32) -> i32 {
    let enemy = other(player);
    let reach = st.g.map.hq_front[enemy as usize] & st.connected_occupied(player) != 0;
    let mut items: SmallVec<[(i32, i32); 16]> = SmallVec::new();
    for u in &st.hands[player as usize] {
        if raids(st, u.card, reach) {
            items.push((effects::unit_cost(st, u), effects::raid_food(st, player, u.card, effects::effective_strength(st, u))));
        }
    }
    best_raids(&items, mana)
}

/// How good `st` is for `me`, in food. Meant for a position where `me` has just ended its turn; it reads any position.
pub fn evaluate(st: &State, me: Player, w: &Weights, odds: &RaidOdds) -> f32 {
    if let Some(r) = st.result {
        return match r.winner {
            Some(p) if p == me => WIN,
            Some(_) => -WIN,
            None => 0.0,
        };
    }
    let opp = other(me);
    let (m, o) = (me as usize, opp as usize);
    let (food_me, food_opp) = (st.food[m], st.food[o]);
    let (inc_me, inc_opp) = (rules::region_income(st, me), rules::region_income(st, opp));
    let win = st.g.map.win_food;
    let mut s = w.food * (food_me - food_opp) as f32 + w.income * (inc_me - inc_opp) as f32;

    // the food race: whose regions pay them over the line first
    let my_turn = st.current == me;
    if my_turn {
        if food_me + inc_me >= win {
            s += 0.9 * WIN; // ending the turn now wins
        }
    } else {
        if food_opp + inc_opp >= win {
            s -= w.income_win_theirs;
        } else if food_me + inc_me >= win {
            s += w.income_win_mine;
        }
    }

    // fatigue: the player whose turn comes next draws its card at the start of it, and an empty deck takes food instead
    let next = other(st.current);
    let due = effects::fatigue_due(st, next, st.cfg().turn_draw_count);
    if due > 0 {
        let sign = if next == me { -1.0 } else { 1.0 };
        s += sign * w.food * due.min(st.food[next as usize]) as f32;
        if due >= st.food[next as usize] {
            s += sign * w.starve;
        }
    }

    // their raids on their next turn, from the hands they may hold
    let their_reach = st.g.map.hq_front[m] & st.connected_occupied(opp) != 0;
    let theirs = if their_reach { &odds.reach } else { &odds.fly };
    if !theirs.is_empty() {
        let (mut sum, mut lethal) = (0i32, 0i32);
        for &v in theirs.iter() {
            sum += v.min(food_me);
            lethal += (v >= food_me) as i32;
        }
        let n = theirs.len() as f32;
        s -= w.threat_theirs * sum as f32 / n + w.lethal_theirs * lethal as f32 / n;
    }

    // my raids on my next turn (this turn, while it is still mine)
    let mana = if my_turn { rules::mana_left(st, me) } else { rules::mana_total(st, me) };
    let mine = hand_raid(st, me, mana);
    s += w.threat_mine * mine.min(food_opp) as f32;
    if mine >= food_opp {
        s += w.lethal_mine;
    }

    // the board: animals, and regions close to paying
    let (own_me, own_opp) = (st.board.own[m], st.board.own[o]);
    let mut occ = st.board.occ;
    while occ != 0 {
        let t = occ.trailing_zeros() as Tile;
        occ &= occ - 1;
        let u = st.board.top(t).unwrap();
        let v = w.body + w.strength * effects::effective_strength(st, &u) as f32;
        s += if u.owner == me { v } else { -v };
    }
    for r in &st.g.map.regions {
        let size = r.mask.count_ones();
        let (a, b) = ((r.mask & own_me).count_ones(), (r.mask & own_opp).count_ones());
        for (held, enemy, sign) in [(a, b, 1.0f32), (b, a, -1.0f32)] {
            if enemy == 0 && held < size {
                if held + 1 == size {
                    s += sign * w.region_near * r.food as f32;
                } else if held + 2 == size {
                    s += sign * w.region_far * r.food as f32;
                }
            }
        }
    }

    // the hands: mine as I hold it, theirs by its size and their unseen pool's average card
    let my_cost: i32 = st.hands[m].iter().map(|u| effects::unit_cost(st, u)).sum();
    let (n_me, n_opp) = (st.hands[m].len() as f32, st.hands[o].len() as f32);
    s += w.hand_card * (n_me - n_opp) + w.hand_cost * (my_cost as f32 - n_opp * odds.avg_cost);
    s
}

/// The evaluation of the greedy bot Practice plays (`animal_kingdom/bot.py`), term for term.
pub fn greedy_evaluate(st: &State, me: Player) -> f64 {
    const GREEDY_WIN: f64 = 1_000_000.0;
    let opp = other(me);
    if let Some(r) = st.result {
        return match r.winner {
            Some(p) if p == me => GREEDY_WIN,
            Some(_) => -GREEDY_WIN,
            None => 0.0,
        };
    }
    let (m, o) = (me as usize, opp as usize);
    let mut score = (st.food[m] - st.food[o]) as f64;
    score += 2.0 * (rules::region_income(st, me) - rules::region_income(st, opp)) as f64;
    let mut occ = st.board.occ;
    while occ != 0 {
        let t = occ.trailing_zeros() as Tile;
        occ &= occ - 1;
        let top = st.board.top(t).unwrap();
        let sign = if top.owner == me { 1.0 } else { -1.0 };
        score += sign * (1.0 + 0.3 * effects::effective_strength(st, &top) as f64);
    }
    // a connected animal on the other side's base can raid next turn
    for (p, sign) in [(me, 1.0), (opp, -1.0)] {
        let on_base = st.g.map.hq_front[other(p) as usize] & st.connected_occupied(p);
        score += sign * 4.0 * on_base.count_ones() as f64;
    }
    score + 0.8 * (st.hands[m].len() as f64 - st.hands[o].len() as f64)
}
