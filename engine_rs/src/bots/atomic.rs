//! bots/atomic_bot.py: the turn is the unit of play, for both sides (Martin, 2026-10-31).
//!
//! Every whole turn is scored only once it is complete, never in mid-turn: in each hand the opponent may hold (every
//! distinct one at its odds, `spread`), against the opponent's best whole reply turn, by the evaluation of the board
//! after it; the hands are averaged as chances to win (`mix`). `rounds` 1 is my turn and their best reply (depth 1); 2 adds my best next turn and their best reply to that
//! (depth 2). Each level is iterative deepening: who goes a level deeper is chosen by the best score in hand.
//!
//! The same search as the Python one, step for step and in the same order, so the two give the same numbers; the
//! (turn, imagined hand) jobs of a level are spread over threads, each with its own copy of the searcher.

use rustc_hash::{FxHashMap, FxHashSet};

use crate::actions::Action;
use crate::bots::search::{observation_key, Searcher};
use crate::bots::features::Evaluator;
use crate::bots::world::determinize;
use crate::rng::PyRandom;
use crate::state::Unit;
use crate::data::*;
use crate::rules;
use crate::state::State;
use crate::strength::effective_strength;
use crate::value::m_get_s;

#[derive(Clone, Copy, PartialEq)]
enum LeafMode {
    Board,
    Plain,
    Deep,
    Remembered,
}

/// What a finished turn is worth inside `tree`: its board (recording it, by the cards drawn on the way), its board
/// alone, the line followed further when it is among those `followed`, or the remembered value in an imagined hand.
struct Leaf {
    mode: LeafMode,
    plies: usize,
    hand: i64,
    ends: Vec<(Vec<i64>, Vec<(Vec<i64>, f64)>, FxHashSet<Vec<i64>>)>,
    index: FxHashMap<Vec<i64>, usize>,
    followed: FxHashMap<Vec<i64>, FxHashSet<Vec<i64>>>,
}

impl Leaf {
    fn new(mode: LeafMode, plies: usize, hand: i64) -> Leaf {
        Leaf { mode, plies, hand, ends: Vec::new(), index: FxHashMap::default(), followed: FxHashMap::default() }
    }
}

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
    pub hands: usize,
    pub temperature: f64,
    pub draws: usize,
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
    pub fn new(base: Searcher, rounds: usize, widths: Vec<usize>, inner: usize, cap: usize, threads: usize, hands: usize, temperature: f64, draws: usize) -> AtomicBot {
        AtomicBot { base, rounds, widths, inner, cap, threads, hands, temperature, draws, memo: FxHashMap::default(), plan: Vec::new(), plan_key: None, last_ranking: Vec::new() }
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

    /// The ways action `a`, which takes `k` cards from the actor's deck, can come out (atomic_bot._outcomes): every
    /// distinct set of cards it can take, with its odds; more than `draws` of them, the likeliest that many.
    fn outcomes(&self, st: &State, actor: Player, a: &Action, k: usize) -> Vec<(f64, State, Vec<i64>)> {
        let ai = actor as usize;
        let deck: Vec<CardId> = st.decks[ai].iter().copied().collect();
        let mut sorted = deck.clone();
        sorted.sort_by(|x, y| st.cname(*x).cmp(st.cname(*y)));
        let mut kinds: Vec<CardId> = Vec::new();
        let mut counts: Vec<usize> = Vec::new();
        for &c in &sorted {
            if kinds.last() == Some(&c) {
                *counts.last_mut().unwrap() += 1;
            } else {
                kinds.push(c);
                counts.push(1);
            }
        }
        fn walk(i: usize, left: usize, ks: &mut Vec<usize>, counts: &[usize], found: &mut Vec<Vec<usize>>) {
            if i == counts.len() {
                if left == 0 {
                    found.push(ks.clone());
                }
                return;
            }
            for n in 0..=counts[i].min(left) {
                ks.push(n);
                walk(i + 1, left - n, ks, counts, found);
                ks.pop();
            }
        }
        let mut found: Vec<Vec<usize>> = Vec::new();
        walk(0, k, &mut Vec::new(), &counts, &mut found);
        let mut scored: Vec<(f64, Vec<usize>)> = found
            .into_iter()
            .map(|ks| {
                let mut w = 1.0f64;
                for (&c, &n) in counts.iter().zip(ks.iter()) {
                    w *= comb(c, n) as f64;
                }
                (w, ks)
            })
            .collect();
        scored.sort_by(|x, y| y.0.partial_cmp(&x.0).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(self.draws);
        let mut total = 0.0;
        for (w, _) in &scored {
            total += w;
        }
        let mut out = Vec::with_capacity(scored.len());
        for (w, ks) in scored {
            let mut taken: Vec<CardId> = Vec::new();
            for (&c, &n) in kinds.iter().zip(ks.iter()) {
                for _ in 0..n {
                    taken.push(c);
                }
            }
            let mut want = taken.clone();
            let mut rest: Vec<CardId> = Vec::new();
            for &c in deck.iter().rev() {
                if let Some(i) = want.iter().position(|&x| x == c) {
                    want.remove(i);
                } else {
                    rest.push(c);
                }
            }
            rest.reverse();
            rest.extend(taken.iter().copied());
            let mut x = st.clone();
            x.decks[ai] = crate::state::Deck::from_slice(&rest);
            let _ = rules::apply_action(&mut x, a, false);
            out.push((w / total, x, taken.iter().map(|&c| c as i64).collect()));
        }
        out
    }

    fn leaf(&mut self, ctx: &mut Leaf, e: &State, hist: &[i64], me: Player) -> Option<f64> {
        match ctx.mode {
            LeafMode::Board => {
                let v = self.value(e, me);
                let k = key(e);
                let i = match ctx.index.get(hist) {
                    Some(&i) => i,
                    None => {
                        ctx.ends.push((hist.to_vec(), Vec::new(), FxHashSet::default()));
                        ctx.index.insert(hist.to_vec(), ctx.ends.len() - 1);
                        ctx.ends.len() - 1
                    }
                };
                let g = &mut ctx.ends[i];
                if g.2.insert(k.clone()) {
                    g.1.push((k, v));
                }
                Some(v)
            }
            LeafMode::Plain => Some(self.value(e, me)),
            LeafMode::Deep => {
                let k = key(e);
                if ctx.followed.get(hist).map_or(false, |f| f.contains(&k)) {
                    Some(self.line_value(e, me, ctx.plies))
                } else {
                    None
                }
            }
            LeafMode::Remembered => Some(self.remembered(e, me, ctx.plies, ctx.hand)),
        }
    }

    /// The value of `actor`'s best whole turn from `s` and its actions up to the first draw (atomic_bot._tree): a
    /// decision is the best of its actions for the actor, a draw the average over what it may bring, a finished turn
    /// the leaf (None: not followed, so never chosen). `hist` is the cards drawn so far.
    fn tree(&mut self, mut s: State, actor: Player, me: Player, ctx: &mut Leaf, hist: &mut Vec<i64>,
            memo: &mut FxHashMap<(Vec<i64>, Vec<i64>), Option<(f64, Vec<Action>)>>) -> Option<(f64, Vec<Action>)> {
        self.resolve_others(&mut s, actor);
        if rules::is_terminal(&s).is_some() || s.player_to_act() != actor {
            return self.leaf(ctx, &s, hist, me).map(|v| (v, Vec::new()));
        }
        let mk = (key(&s), hist.clone());
        if let Some(r) = memo.get(&mk) {
            return r.clone();
        }
        let mine = actor == me;
        let ai = actor as usize;
        let mut best: Option<(f64, Vec<Action>)> = None;
        for a in rules::legal_actions(&s) {
            let mut nxt = s.clone();
            let _ = rules::apply_action(&mut nxt, &a, false);
            let before = s.decks[ai].len();
            let after = nxt.decks[ai].len();
            let (v, path) = if after < before {
                let outs = self.outcomes(&s, actor, &a, before - after);
                let mut vals: Vec<f64> = Vec::with_capacity(outs.len());
                let mut ws: Vec<f64> = Vec::with_capacity(outs.len());
                for (w, x, taken) in outs.iter() {
                    let n = hist.len();
                    hist.push(-1);
                    hist.extend(taken.iter().copied());
                    let r = self.tree(x.clone(), actor, me, ctx, hist, memo);
                    hist.truncate(n);
                    match r {
                        Some((v, _)) => {
                            vals.push(v);
                            ws.push(*w);
                        }
                        None => break,
                    }
                }
                if vals.len() < outs.len() {
                    continue;
                }
                (self.mix(&vals, &ws), vec![a.clone()])
            } else {
                match self.tree(nxt, actor, me, ctx, hist, memo) {
                    Some((v, p)) => {
                        let mut path = vec![a.clone()];
                        path.extend(p);
                        (v, path)
                    }
                    None => continue,
                }
            };
            let better = match &best {
                None => true,
                Some((b, _)) => if mine { v > *b } else { v < *b },
            };
            if better {
                best = Some((v, path));
            }
        }
        memo.insert(mk, best.clone());
        best
    }

    fn run_tree(&mut self, s: &State, actor: Player, me: Player, ctx: &mut Leaf) -> Option<(f64, Vec<Action>)> {
        let mut memo = FxHashMap::default();
        self.tree(s.clone(), actor, me, ctx, &mut Vec::new(), &mut memo)
    }

    pub fn line_value(&mut self, s: &State, me: Player, plies: usize) -> f64 {
        self.best_line(s, me, plies).0
    }

    /// (the value, the actions of the first turn up to its first draw of) the line followed `plies` whole turns deep
    /// (atomic_bot.best_line): the last turn judged on the board, the earlier ones by following, for every set of cards
    /// drawn, the best `inner` of their finished turns for that side further.
    pub fn best_line(&mut self, s: &State, me: Player, plies: usize) -> (f64, Vec<Action>) {
        if plies == 0 || rules::is_terminal(s).is_some() {
            return (self.value(s, me), Vec::new());
        }
        let actor = s.player_to_act();
        let mine = actor == me;
        let mut ctx = Leaf::new(LeafMode::Board, 0, -1);
        let first = match self.run_tree(s, actor, me, &mut ctx) {
            Some(r) => r,
            None => return (self.value(s, me), Vec::new()),
        };
        if plies == 1 {
            return first;
        }
        let mut followed: FxHashMap<Vec<i64>, FxHashSet<Vec<i64>>> = FxHashMap::default();
        for (h, es, _) in &ctx.ends {
            let mut es = es.clone();
            if mine {
                es.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
            } else {
                es.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
            }
            followed.insert(h.clone(), es.into_iter().take(self.inner).map(|(k, _)| k).collect());
        }
        let mut deep = Leaf::new(LeafMode::Deep, plies - 1, -1);
        deep.followed = followed;
        self.run_tree(s, actor, me, &mut deep).unwrap_or(first)
    }

    /// The value of my turn ending in `s`, `plies` turns past it; a turn a draw left open is finished in this imagined
    /// hand by its best continuation for the cards drawn there (atomic_bot._after_my_turn).
    fn after_my_turn(&mut self, s: &State, me: Player, open: bool, plies: usize, hand: i64) -> f64 {
        if !open || rules::is_terminal(s).is_some() || s.player_to_act() != me {
            return self.remembered(s, me, plies, hand);
        }
        let mut ctx = Leaf::new(LeafMode::Remembered, plies, hand);
        match self.run_tree(s, me, me, &mut ctx) {
            Some((v, _)) => v,
            None => self.remembered(s, me, plies, hand),
        }
    }

    /// The board a turn a draw left open reaches, in this imagined hand, by its best continuation.
    fn best_board(&mut self, e: &State, me: Player) -> f64 {
        let mut ctx = Leaf::new(LeafMode::Plain, 0, -1);
        match self.run_tree(e, me, me, &mut ctx) {
            Some((v, _)) => v,
            None => self.value(e, me),
        }
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

    /// The value over the imagined hands, each by its odds, averaged as chances to win (atomic_bot._mix).
    pub fn mix(&self, vs: &[f64], ws: &[f64]) -> f64 {
        let scale = match &self.base.evaluator {
            Evaluator::Slot(n) => n.scale,
            Evaluator::Net(n) => n.scale,
            _ => 0.0,
        } * self.temperature;
        if scale == 0.0 {
            let mut s = 0.0;
            for (v, w) in vs.iter().zip(ws.iter()) {
                s += v * w;
            }
            return s;
        }
        let mut p = 0.0;
        for (v, w) in vs.iter().zip(ws.iter()) {
            p += w / (1.0 + (-v / scale).exp());
        }
        let cap = self.base.decisive;
        if p <= 0.0 {
            return -cap;
        }
        if p >= 1.0 {
            return cap;
        }
        (scale * (p / (1.0 - p)).ln()).max(-cap).min(cap)
    }

    /// The hands the opponent may hold, as imagined worlds with their odds (atomic_bot.spread): every distinct hand
    /// their unseen cards can make, weighted by the ways it can be dealt; more than `hands` of them, that many at random.
    pub fn spread(&mut self, st: &State, me: Player) -> (Vec<State>, Vec<f64>) {
        let opp = other(me);
        let (m, o) = (me as usize, opp as usize);
        let kept: Vec<Unit> = st.hands[o].iter().filter(|u| u.locked_until_turn as i32 > st.turn_counter).cloned().collect();
        let hidden = st.hands[o].len() - kept.len();
        let mut pool: Vec<CardId> = st.hands[o].iter().filter(|u| !(u.locked_until_turn as i32 > st.turn_counter)).map(|u| u.card).collect();
        pool.extend(st.decks[o].iter().copied());
        pool.sort_by(|a, b| st.cname(*a).cmp(st.cname(*b)));
        let mut kinds: Vec<CardId> = Vec::new();
        let mut counts: Vec<usize> = Vec::new();
        for &c in &pool {
            if kinds.last() == Some(&c) {
                *counts.last_mut().unwrap() += 1;
            } else {
                kinds.push(c);
                counts.push(1);
            }
        }
        fn walk(i: usize, left: usize, ks: &mut Vec<usize>, counts: &[usize], found: &mut Vec<Vec<usize>>, cap: usize) -> bool {
            if found.len() > cap {
                return false;
            }
            if i == counts.len() {
                if left == 0 {
                    found.push(ks.clone());
                }
                return true;
            }
            for k in 0..=counts[i].min(left) {
                ks.push(k);
                let ok = walk(i + 1, left - k, ks, counts, found, cap);
                ks.pop();
                if !ok {
                    return false;
                }
            }
            true
        }
        let mut found: Vec<Vec<usize>> = Vec::new();
        let complete = walk(0, hidden, &mut Vec::new(), &counts, &mut found, self.hands);
        if !complete || found.len() > self.hands {
            let worlds: Vec<State> = (0..self.hands).map(|_| determinize(st, me, &mut self.base.det_rng)).collect();
            let n = worlds.len() as f64;
            return (worlds, vec![1.0 / n; self.hands]);
        }
        let rng = &mut self.base.det_rng;
        let mut worlds = Vec::with_capacity(found.len());
        let mut weights = Vec::with_capacity(found.len());
        for ks in &found {
            let mut x = st.clone();
            let mut mine = std::mem::take(&mut x.decks[m]);
            mine.sort_by(|a, b| st.cname(*a).cmp(st.cname(*b)));
            rng.shuffle(&mut mine);
            x.decks[m] = mine;
            let mut cards: Vec<CardId> = Vec::new();
            for (c, &k) in kinds.iter().zip(ks.iter()) {
                for _ in 0..k {
                    cards.push(*c);
                }
            }
            let mut rest: Vec<CardId> = Vec::new();
            for (c, (&n, &k)) in kinds.iter().zip(counts.iter().zip(ks.iter())) {
                for _ in 0..(n - k) {
                    rest.push(*c);
                }
            }
            rng.shuffle(&mut rest);
            let mut hand: crate::state::Hand = kept.iter().cloned().collect();
            for &c in &cards {
                let iid = x.new_iid();
                hand.push(Unit::new(c, opp, iid));
            }
            x.hands[o] = hand;
            x.decks[o] = crate::state::Deck::from_slice(&rest);
            x.rng = PyRandom::seeded_u64(rng.getrandbits(64)).into();
            let mut weight = 1.0f64;
            for (&n, &k) in counts.iter().zip(ks.iter()) {
                weight *= comb(n, k) as f64;
            }
            worlds.push(x);
            weights.push(weight);
        }
        let mut total = 0.0;
        for w in &weights {
            total += w;
        }
        (worlds, weights.iter().map(|w| w / total).collect())
    }

    /// Every whole turn for `me`, best first (atomic_bot.rank).
    pub fn rank(&mut self, st: &State, me: Player, worlds: &[State], weights: &[f64]) -> Vec<Row> {
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
            let mut vals: Vec<f64> = Vec::with_capacity(ends.len());
            for e in &ends {
                vals.push(if open { self.best_board(e, me) } else { self.value(e, me) });
            }
            let board = self.mix(&vals, weights);
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
                rows[i].levels[lv] = Some(self.mix(&vs, weights));
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
        let (worlds, weights) = self.spread(st, me);
        let ranking = self.rank(st, me, &worlds, &weights);
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

fn comb(n: usize, k: usize) -> u64 {
    let mut r: u64 = 1;
    for i in 0..k {
        r = r * (n - i) as u64 / (i + 1) as u64;
    }
    r
}
