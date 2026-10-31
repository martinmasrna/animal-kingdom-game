//! bots/atomic_bot.py: the turn is the unit of play, for both sides (Martin, 2026-10-31).
//!
//! Every whole turn is scored only once it is complete, never in mid-turn: in each hand imagined for the opponent (the
//! Expert's own determinizations), against the opponent's best whole reply turn, by the evaluation of the board after
//! it. `rounds` 1 is my turn and their best reply (depth 1); 2 adds my best next turn and their best reply to that
//! (depth 2). Each level is iterative deepening: who goes a level deeper is chosen by the best score in hand.
//!
//! The same search as the Python one, step for step and in the same order, so the two give the same numbers; the
//! (turn, imagined hand) jobs of a level are spread over threads, each with its own copy of the searcher.

use rustc_hash::{FxHashMap, FxHashSet};

use crate::actions::Action;
use crate::bots::search::{observation_key, Searcher};
use crate::bots::world::determinize;
use crate::data::*;
use crate::rules;
use crate::state::State;
use crate::strength::effective_strength;
use crate::value::m_get_s;

/// One whole turn of mine and what the search made of it.
#[derive(Clone)]
pub struct Row {
    pub turn: Vec<Action>,
    pub ends: Vec<State>,
    pub open: bool,
    pub board: f64,
    pub levels: Vec<Option<f64>>,
    pub per_hand: Vec<Option<Vec<f64>>>,
}

#[derive(Clone)]
pub struct AtomicBot {
    pub base: Searcher,
    pub rounds: usize,
    pub widths: Vec<usize>,
    pub inner: usize,
    pub cap: usize,
    pub threads: usize,
    memo: FxHashMap<(i64, usize, Vec<i64>), f64>,
    plan: Vec<Action>,
    plan_key: Option<String>,
    pub last_ranking: Vec<Row>,
}

/// A position, for merging turns that reach it by different orders: the board's stacks, both hands, food, decks, the
/// side to move and whether the game is decided (atomic_bot._key). Unit ids are left out.
fn key(s: &State) -> Vec<i64> {
    let mut k: Vec<i64> = Vec::with_capacity(96);
    for cr in 0..s.stacks.len() {
        let st = s.stack(cr as Cr);
        if st.is_empty() {
            continue;
        }
        k.push(-1);
        k.push(cr as i64);
        for u in st.iter() {
            k.push(u.card as i64);
            k.push(u.owner as i64);
            k.push(effective_strength(s, u, None) as i64);
        }
    }
    for p in 0..2 {
        let mut h: Vec<i64> = s.hands[p].iter().map(|u| u.card as i64).collect();
        h.sort_unstable();
        k.push(-2);
        k.extend(h);
    }
    k.push(-3);
    k.push(s.food[0] as i64);
    k.push(s.food[1] as i64);
    k.push(s.decks[0].len() as i64);
    k.push(s.decks[1].len() as i64);
    k.push(s.current as i64);
    k.push(match rules::is_terminal(s) {
        Some(r) => r.winner.map(|w| w as i64).unwrap_or(9),
        None => -9,
    });
    k
}

impl AtomicBot {
    pub fn new(base: Searcher, rounds: usize, widths: Vec<usize>, inner: usize, cap: usize, threads: usize) -> AtomicBot {
        AtomicBot { base, rounds, widths, inner, cap, threads, memo: FxHashMap::default(), plan: Vec::new(), plan_key: None, last_ranking: Vec::new() }
    }

    // ------------------------------------------------------------------ evaluation

    fn value(&self, s: &State, me: Player) -> f64 {
        if s.result.is_none() {
            if let Some(r) = rules::is_terminal(s) {
                let mut t = s.clone();
                t.result = Some(r);
                return self.base.clamped_eval(&t, me);
            }
        }
        self.base.clamped_eval(s, me)
    }

    /// A choice the other side must make inside `actor`'s turn: theirs by the base's fast policy.
    fn resolve_others(&mut self, s: &mut State, actor: Player) {
        for _ in 0..20 {
            if rules::is_terminal(s).is_some() || s.pending.is_none() || s.player_to_act() == actor || s.current != actor {
                return;
            }
            let who = s.player_to_act();
            let legal = rules::legal_actions(s);
            let a = self.base.policy.choose(s, who, &legal);
            let _ = rules::apply_action(s, &a, false);
        }
    }

    /// Every whole turn `actor` can play from `s`, one per position it ends on. Without `through_draws`, anything taken
    /// from the actor's own deck ends the listing there (the rest is played per imagined hand).
    pub fn turns(&mut self, s: &State, actor: Player, through_draws: bool) -> Vec<(Vec<Action>, State)> {
        let mut seen: FxHashSet<Vec<i64>> = FxHashSet::default();
        let mut out: Vec<(Vec<Action>, State)> = Vec::new();
        let mut path: Vec<Action> = Vec::new();
        self.walk(s.clone(), &mut path, actor, through_draws, &mut seen, &mut out);
        out
    }

    fn walk(&mut self, mut st: State, path: &mut Vec<Action>, actor: Player, through_draws: bool,
            seen: &mut FxHashSet<Vec<i64>>, out: &mut Vec<(Vec<Action>, State)>) {
        if out.len() >= self.cap {
            return;
        }
        self.resolve_others(&mut st, actor);
        if rules::is_terminal(&st).is_some() || st.player_to_act() != actor {
            let k = key(&st);
            if seen.insert(k) {
                out.push((path.clone(), st));
            }
            return;
        }
        let a_idx = actor as usize;
        for a in rules::legal_actions(&st) {
            let mut nxt = st.clone();
            let _ = rules::apply_action(&mut nxt, &a, false);
            if !through_draws && (matches!(a, Action::Draw) || nxt.decks[a_idx].len() != st.decks[a_idx].len()) {
                let mut p = path.clone();
                p.push(a);
                out.push((p, nxt));
                continue;
            }
            path.push(a);
            self.walk(nxt, path, actor, through_draws, seen, out);
            path.pop();
        }
    }

    pub fn line_value(&mut self, s: &State, me: Player, plies: usize) -> f64 {
        self.best_line(s, me, plies).0
    }

    /// (the value, the actions of the first turn of) the line followed `plies` whole turns deep, each side playing its
    /// best turn: the last one the best of all its turns on the board, the earlier ones the best `inner` followed further.
    pub fn best_line(&mut self, s: &State, me: Player, plies: usize) -> (f64, Vec<Action>) {
        if plies == 0 || rules::is_terminal(s).is_some() {
            return (self.value(s, me), Vec::new());
        }
        let actor = s.player_to_act();
        let ends = self.turns(s, actor, true);
        if ends.is_empty() {
            return (self.value(s, me), Vec::new());
        }
        let mine = actor == me;
        let mut scored: Vec<(f64, Vec<Action>, State)> = ends.into_iter().map(|(p, e)| (self.value(&e, me), p, e)).collect();
        if mine {
            scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        } else {
            scored.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
        }
        if plies == 1 {
            let (v, p, _) = scored.swap_remove(0);
            return (v, p);
        }
        let mut best: Option<(f64, Vec<Action>)> = None;
        let n = self.inner.min(scored.len());
        for (_, p, e) in scored.into_iter().take(n) {
            let v = self.line_value(&e, me, plies - 1);
            let better = match &best {
                None => true,
                Some((b, _)) => if mine { v > *b } else { v < *b },
            };
            if better {
                best = Some((v, p));
            }
        }
        best.unwrap()
    }

    /// The value of my turn ending in `s`, `plies` turns past it; a turn a draw left open is finished in this imagined
    /// hand by the best of every continuation for the cards drawn there (atomic_bot._after_my_turn).
    fn after_my_turn(&mut self, s: &State, me: Player, open: bool, plies: usize, hand: i64) -> f64 {
        if !open || rules::is_terminal(s).is_some() || s.player_to_act() != me {
            return self.remembered(s, me, plies, hand);
        }
        let rest = self.turns(s, me, true);
        if rest.is_empty() {
            return self.remembered(s, me, plies, hand);
        }
        let mut best = f64::NEG_INFINITY;
        for (_, e) in rest {
            let v = self.remembered(&e, me, plies, hand);
            if v > best {
                best = v;
            }
        }
        best
    }

    fn remembered(&mut self, s: &State, me: Player, plies: usize, hand: i64) -> f64 {
        if hand < 0 {
            return self.line_value(s, me, plies);
        }
        let k = (hand, plies, key(s));
        if let Some(v) = self.memo.get(&k) {
            return *v;
        }
        let v = self.line_value(s, me, plies);
        self.memo.insert(k, v);
        v
    }

    // ------------------------------------------------------------------ the search

    pub fn worlds(&mut self, st: &State, me: Player) -> Vec<State> {
        (0..self.base.determinizations).map(|_| determinize(st, me, &mut self.base.det_rng)).collect()
    }

    /// Every whole turn for `me`, best first (atomic_bot.rank).
    pub fn rank(&mut self, st: &State, me: Player, worlds: &[State]) -> Vec<Row> {
        self.memo.clear();
        let mut rows: Vec<Row> = Vec::new();
        for (path, _) in self.turns(st, me, false) {
            let mut ends: Vec<State> = Vec::with_capacity(worlds.len());
            let mut ok = true;
            for w in worlds {
                let mut x = w.clone();
                for a in &path {
                    if rules::apply_action(&mut x, a, false).is_err() {
                        ok = false;
                        break;
                    }
                }
                if !ok {
                    break;
                }
                self.resolve_others(&mut x, me);
                ends.push(x);
            }
            if !ok || ends.len() < worlds.len() {
                continue;
            }
            let open = rules::is_terminal(&ends[0]).is_none() && ends[0].player_to_act() == me;
            let mut total = 0.0;
            for e in &ends {
                total += if open {
                    let cont = self.turns(e, me, true);
                    let mut best: Option<f64> = None;
                    for (_, end) in &cont {
                        let v = self.value(end, me);
                        if best.map_or(true, |b| v > b) {
                            best = Some(v);
                        }
                    }
                    best.unwrap_or_else(|| self.value(e, me))
                } else {
                    self.value(e, me)
                };
            }
            let board = total / ends.len() as f64;
            rows.push(Row { turn: path, ends, open, board, levels: vec![None; self.rounds], per_hand: vec![None; self.rounds] });
        }
        let mut pool: Vec<usize> = (0..rows.len()).collect();
        pool.sort_by(|&a, &b| rows[b].board.partial_cmp(&rows[a].board).unwrap_or(std::cmp::Ordering::Equal));
        for lv in 0..self.rounds {
            let width = self.widths[lv.min(self.widths.len() - 1)];
            let go: Vec<usize> = pool.iter().take(width).copied().collect();
            let plies = 2 * lv + 1;
            let jobs: Vec<(usize, usize)> = go.iter().flat_map(|&i| (0..worlds.len()).map(move |k| (i, k))).collect();
            let values = self.run_jobs(&rows, &jobs, me, plies);
            for &i in &go {
                let vs: Vec<f64> = (0..worlds.len()).map(|k| values[&(i, k)]).collect();
                let mut sum = 0.0;
                for v in &vs {
                    sum += *v;
                }
                rows[i].levels[lv] = Some(sum / vs.len() as f64);
                rows[i].per_hand[lv] = Some(vs);
            }
            let mut next = go.clone();
            next.sort_by(|&a, &b| rows[b].levels[lv].unwrap().partial_cmp(&rows[a].levels[lv].unwrap()).unwrap_or(std::cmp::Ordering::Equal));
            pool = next;
        }
        let rounds = self.rounds;
        let order_key = |r: &Row| -> (i64, f64) {
            for lv in (0..rounds).rev() {
                if let Some(v) = r.levels[lv] {
                    return (-(lv as i64 + 1), -v);
                }
            }
            (0, -r.board)
        };
        rows.sort_by(|a, b| {
            let (ka, kb) = (order_key(a), order_key(b));
            ka.0.cmp(&kb.0).then(ka.1.partial_cmp(&kb.1).unwrap_or(std::cmp::Ordering::Equal))
        });
        for r in rows.iter_mut() {
            r.ends.clear();
        }
        rows
    }

    fn run_jobs(&mut self, rows: &[Row], jobs: &[(usize, usize)], me: Player, plies: usize) -> FxHashMap<(usize, usize), f64> {
        let mut out: FxHashMap<(usize, usize), f64> = FxHashMap::default();
        let t = self.threads.max(1).min(jobs.len().max(1));
        if t <= 1 {
            for &(i, k) in jobs {
                let v = self.after_my_turn(&rows[i].ends[k], me, rows[i].open, plies, k as i64);
                out.insert((i, k), v);
            }
            return out;
        }
        let chunks: Vec<Vec<(usize, usize)>> = (0..t).map(|n| jobs.iter().skip(n).step_by(t).copied().collect()).collect();
        let results: Vec<Vec<((usize, usize), f64)>> = std::thread::scope(|scope| {
            let handles: Vec<_> = chunks
                .into_iter()
                .map(|chunk| {
                    let mut me_bot = self.clone();
                    scope.spawn(move || {
                        chunk.into_iter().map(|(i, k)| ((i, k), me_bot.after_my_turn(&rows[i].ends[k], me, rows[i].open, plies, k as i64))).collect::<Vec<_>>()
                    })
                })
                .collect();
            handles.into_iter().map(|h| h.join().unwrap()).collect()
        });
        for r in results {
            for (job, v) in r {
                out.insert(job, v);
            }
        }
        out
    }

    pub fn choose(&mut self, st: &State, me: Player, legal: &[Action]) -> Action {
        if legal.len() == 1 {
            return legal[0].clone();
        }
        let mulligan = st.pending.as_ref().map_or(false, |p| m_get_s(p, "kind") == Some("mulligan")) || rules::early_mulligan(st, me).is_some();
        if mulligan {
            return self.base.choose(st, me, legal);
        }
        let k = observation_key(st, me);
        if !self.plan.is_empty() && self.plan_key.as_deref() == Some(k.as_str()) && legal.contains(&self.plan[0]) {
            let a = self.plan.remove(0);
            self.plan_key = if self.plan.is_empty() { None } else { Some(self.next_key(st, &a, me)) };
            return a;
        }
        let worlds = self.worlds(st, me);
        let ranking = self.rank(st, me, &worlds);
        let best = ranking[0].turn.clone();
        self.last_ranking = ranking;
        let a = best[0].clone();
        self.plan = best[1..].to_vec();
        if matches!(a, Action::Draw) {
            self.plan.clear();     // what follows a draw is planned once the cards are seen
        }
        self.plan_key = if self.plan.is_empty() { None } else { Some(self.next_key(st, &a, me)) };
        a
    }

    fn next_key(&self, st: &State, a: &Action, me: Player) -> String {
        let mut nxt = st.clone();
        let _ = rules::apply_action(&mut nxt, a, false);
        observation_key(&nxt, me)
    }
}
