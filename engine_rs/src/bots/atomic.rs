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

use crate::actions::{Action, Target};
use crate::bots::search::{observation_key, Searcher};
use crate::bots::features::Evaluator;
use crate::bots::world::determinize;
use crate::rng::PyRandom;
use crate::state::Unit;
use crate::data::*;
use crate::rules;
use crate::state::{Game, State};
use std::sync::Arc;
use crate::strength::effective_strength;
use crate::value::m_get_s;
use serde_json as sj;

#[derive(Clone, Copy, PartialEq)]
enum LeafMode {
    Board,
    Plain,
    Deep,
    Remembered,
    Card,
    Kinds,
}

/// What a finished turn is worth inside `tree`: its board (recording it, by the cards drawn on the way), its board
/// alone, the line followed further when it is among those `followed`, or the remembered value in an imagined hand.
struct Leaf {
    mode: LeafMode,
    plies: usize,
    hand: i64,
    ends: Vec<(Vec<i64>, Vec<(Vec<i64>, f64)>, FxHashSet<Vec<i64>>, f64)>,
    index: FxHashMap<Vec<i64>, usize>,
    followed: FxHashMap<Vec<i64>, FxHashSet<Vec<i64>>>,
    // Deep: the window of the line above and the best this side is sure of so far (atomic_bot.best_line's `achieved`)
    mine: bool,
    alpha: f64,
    beta: f64,
    achieved: f64,
    // Card: which drawn card a line must play (-1: none of them), the drawn instances, whose they are, and whether a
    // line placed two of them
    card: i64,
    drawn: Vec<(i64, i64)>,
    actor: Player,
    chain: bool,
    kinds: Option<Box<KindsAcc>>,
}

/// What `by_card` gathers from one search after the opponent's draw, in a hand holding one of every card they could
/// have: their best play with each card (or with none of them), whatever their hand.
struct KindsAcc {
    ids: Vec<(i64, CardId)>, // the instances of that hand they might not hold
    pool: Vec<CardId>,       // every card they may hold or draw (sorted)
    kept: Vec<i64>,          // the cards in their hand I know (locked)
    n: usize,                // how many cards their hand really holds after the draw, without the known ones
    g: Arc<Game>,
    // the cards each line plays from that hand (sorted) -> the best value for them
    best: FxHashMap<Vec<CardId>, f64>,
}

pub static FALLBACKS: [std::sync::atomic::AtomicUsize; 2] = [std::sync::atomic::AtomicUsize::new(0), std::sync::atomic::AtomicUsize::new(0)];

impl Leaf {
    fn new(mode: LeafMode, plies: usize, hand: i64) -> Leaf {
        Leaf { mode, plies, hand, ends: Vec::new(), index: FxHashMap::default(), followed: FxHashMap::default(),
               mine: true, alpha: f64::NEG_INFINITY, beta: f64::INFINITY, achieved: 0.0, card: -1, drawn: Vec::new(),
               actor: 0, chain: false, kinds: None }
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
    pub by_card: bool,
    // >0: at a decision in mid-turn, only the `beam` most promising actions for the side choosing are searched on
    // (each scored on the board it leaves, a card drawn on the way as it came in this hand); actions that end the turn
    // and the Draw action are always searched
    pub beam: usize,
    // the candidate network: when set, the beam is chosen by its scores (one pass per decision) instead of by the
    // board each action leaves (an engine run and an evaluation per action)
    pub cand: Option<std::sync::Arc<super::cand::CandNet>>,
    roomy: Option<Arc<Game>>,
    // by_card's searches by what I see after the draw: (no card, the best with each card), None when a line plays two
    kinds_seen: FxHashMap<String, Option<Vec<(Vec<CardId>, f64)>>>,
    memo: FxHashMap<(i64, usize, Vec<i64>), f64>,
    // my turn's board pass by what I can see (`seen`): the turns scored and which are followed, the same whatever the
    // opponent holds, since my evaluation reads their hand only as its size
    passes: FxHashMap<String, ((f64, Vec<Action>), FxHashMap<Vec<i64>, FxHashSet<Vec<i64>>>)>,
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
        AtomicBot { base, rounds, widths, inner, cap, threads, hands, temperature, draws, by_card: true, beam: 0, cand: None, roomy: None, kinds_seen: FxHashMap::default(), memo: FxHashMap::default(), passes: FxHashMap::default(), plan: Vec::new(), plan_key: None, last_ranking: Vec::new() }
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
        let mut legal = rules::legal_actions(&st);
        if self.beam > 0 && legal.len() > self.beam {
            if let Some(net) = &self.cand {
                let net = net.clone();
                legal = self.cand_beam(&net, &st, actor, legal);
            }
        }
        for a in legal {
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
        if scored.len() > self.draws {
            // that many picked evenly across their odds (atomic_bot._outcomes: systematic sampling)
            let mut total = 0.0;
            for (w, _) in &scored {
                total += w;
            }
            let mut picked: Vec<(usize, usize)> = Vec::new();
            let mut run = scored[0].0 / total;
            let mut i = 0usize;
            for j in 0..self.draws {
                let point = (j as f64 + 0.5) / self.draws as f64;
                while run < point && i < scored.len() - 1 {
                    i += 1;
                    run += scored[i].0 / total;
                }
                match picked.iter_mut().find(|(x, _)| *x == i) {
                    Some(p) => p.1 += 1,
                    None => picked.push((i, 1)),
                }
            }
            picked.sort();
            scored = picked.into_iter().map(|(i, n)| (n as f64, scored[i].1.clone())).collect();
        }
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
            let x = dealt(st, actor, a, &taken);
            out.push((w / total, x, taken.iter().map(|&c| c as i64).collect()));
        }
        out
    }

    /// The opponent's draw in their last turn of a line, judged card by card (atomic_bot._by_card): their best play
    /// with each card type, searched once; the draw is worth, over every set of cards at its odds, the best of what they
    /// could do without the new cards and with each of them. None when a line could place two of the drawn cards.
    fn by_card(&mut self, s: &State, actor: Player, me: Player, a: &Action, k: usize) -> Option<f64> {
        let ai = actor as usize;
        let deck: Vec<CardId> = s.decks[ai].iter().copied().collect();
        let mut kinds: Vec<CardId> = deck.clone();
        kinds.sort_by(|x, y| s.cname(*x).cmp(s.cname(*y)));
        kinds.dedup();
        let before: Vec<i64> = s.hands[ai].iter().map(|u| u.iid).collect();
        // a draw that ends their turn changes nothing I can see but their hand's size: one position, whatever it brings
        {
            let mut taken: Vec<CardId> = deck[deck.len() - k.min(deck.len())..].to_vec();
            taken.truncate(k);
            let mut x = dealt(s, actor, a, &taken);
            self.resolve_others(&mut x, actor);
            if rules::is_terminal(&x).is_some() || x.player_to_act() != actor {
                return Some(self.value(&x, me));
            }
        }
        // what each card would do after the draw is the same in every hand they may hold: one search, in a hand
        // holding one of every card they could have, remembered by what I see; this hand then takes the best of its own
        // cards and of the cards each draw may bring
        let o = ai;
        let kept: Vec<i64> = s.hands[o].iter().filter(|u| u.locked_until_turn as i32 > s.turn_counter).map(|u| u.iid).collect();
        let mut hand: Vec<CardId> = s.hands[o].iter().filter(|u| !kept.contains(&u.iid)).map(|u| u.card).collect();
        hand.sort_unstable();
        let mut sdeck = deck.clone();
        sdeck.sort_unstable();
        let mut pool = hand.clone();
        pool.extend(sdeck.iter().copied());
        pool.sort_unstable();
        let mut every = pool.clone();
        every.dedup();
        let g = s.g.clone();
        if self.roomy.is_none() {
            let mut cfg = g.cfg.clone();
            cfg.hand_limit = 99;
            self.roomy = Some(Arc::new(Game { cards: g.cards.clone(), map: g.map.clone(), cfg, known: g.known.clone(), hook_masks: g.hook_masks.clone() }));
        }
        let mut u = s.clone();
        u.g = self.roomy.clone().unwrap();
        let mut uh: crate::state::Hand = s.hands[o].iter().filter(|x| kept.contains(&x.iid)).cloned().collect();
        for &c in &every {
            let iid = u.new_iid();
            uh.push(Unit::new(c, actor, iid));
        }
        u.hands[o] = uh;
        u.decks[o] = crate::state::Deck::from_slice(&pool);
        let _ = rules::apply_action(&mut u, a, false);
        let n = hand.len() + k.min(deck.len());
        let sk = format!("{}|{}", seen(&u, me), n);
        FALLBACKS[1].fetch_add(0, std::sync::atomic::Ordering::Relaxed);
        if std::env::var("AK_KEYS").is_ok() {
            eprintln!("BYCARD taken={} a={:?} k={} hand={} cur={} me={}", s.actions_taken_this_turn, a, k, s.hands[ai].len(), s.current, me);
        }
        if !self.kinds_seen.contains_key(&sk) {
            let ids: Vec<(i64, CardId)> = u.hands[o].iter().filter(|x| !kept.contains(&x.iid)).map(|x| (x.iid, x.card)).collect();
            let mut ctx = Leaf::new(LeafMode::Kinds, 0, -1);
            ctx.actor = actor;
            ctx.kinds = Some(Box::new(KindsAcc { ids, pool: pool.clone(), kept: kept.clone(), n, g: g.clone(), best: FxHashMap::default() }));
            let _ = self.run_tree(&u, actor, me, &mut ctx);
            let acc = ctx.kinds.unwrap();
            let got = if ctx.chain {
                None
            } else {
                let mut v: Vec<(Vec<CardId>, f64)> = acc.best.into_iter().collect();
                v.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal).then(a.0.cmp(&b.0)));
                Some(v)
            };
            FALLBACKS[if ctx.chain { 1 } else { 0 }].fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            self.kinds_seen.insert(sk.clone(), got);
        }
        let best = self.kinds_seen[&sk].clone()?;
        let (vals, ws) = draw_sets(&sdeck, k.min(sdeck.len()), |got| {
            let mut have = hand.clone();
            have.extend(got.iter().copied());
            have.sort_unstable();
            best.iter().find(|(need, _)| msubset(need, &have)).map(|(_, v)| *v)
        });
        if vals.is_empty() {
            return None;
        }
        Some(self.mix(&vals, &ws))
    }

    fn leaf(&mut self, ctx: &mut Leaf, e: &State, hist: &[i64], prob: f64, me: Player) -> Option<f64> {
        match ctx.mode {
            LeafMode::Board => {
                let v = self.value(e, me);
                let k = seen_key(e, me);
                let i = match ctx.index.get(hist) {
                    Some(&i) => i,
                    None => {
                        ctx.ends.push((hist.to_vec(), Vec::new(), FxHashSet::default(), prob));
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
                let k = seen_key(e, me);
                if !ctx.followed.get(hist).map_or(false, |f| f.contains(&k)) {
                    return None;
                }
                if !hist.is_empty() {
                    return Some(self.line_value(e, me, ctx.plies));     // after a draw: one of an average, so exact
                }
                let (a, b) = if ctx.mine { (ctx.achieved, ctx.beta) } else { (ctx.alpha, ctx.achieved) };
                let v = self.best_line(e, me, ctx.plies, a, b).0;
                ctx.achieved = if ctx.mine { ctx.achieved.max(v) } else { ctx.achieved.min(v) };
                Some(v)
            }
            LeafMode::Remembered => Some(self.remembered(e, me, ctx.plies, ctx.hand)),
            LeafMode::Card => {
                let held: Vec<i64> = e.hands[ctx.actor as usize].iter().map(|u| u.iid).collect();
                let gone: Vec<(i64, i64)> = ctx.drawn.iter().copied().filter(|(i, _)| !held.contains(i)).collect();
                if gone.len() > 1 {
                    ctx.chain = true;
                }
                let ok = if ctx.card < 0 { gone.is_empty() } else { gone.len() == 1 && gone[0].1 == ctx.card };
                if ok { Some(self.value(e, me)) } else { None }
            }
            LeafMode::Kinds => {
                let acc = ctx.kinds.as_mut().unwrap();
                let o = ctx.actor as usize;
                let mut gone: Vec<CardId> = acc.ids.iter().filter(|(i, _)| !e.hands[o].iter().any(|x| x.iid == *i)).map(|&(_, c)| c).collect();
                gone.sort_unstable();
                // the board as I see it: their hand as many cards as they really hold, hand and deck what is left
                let mut r = e.clone();
                r.g = acc.g.clone();
                let left = msub(&acc.pool, &gone);
                let m = (acc.n - gone.len()).min(left.len());
                let mut hand: crate::state::Hand = e.hands[o].iter().filter(|x| acc.kept.contains(&x.iid)).cloned().collect();
                for &c in &left[..m] {
                    let iid = r.new_iid();
                    hand.push(Unit::new(c, ctx.actor, iid));
                }
                r.hands[o] = hand;
                r.decks[o] = crate::state::Deck::from_slice(&left[m..]);
                let v = self.value(&r, me);
                let b = acc.best.entry(gone).or_insert(f64::INFINITY);
                *b = b.min(v);
                Some(v)
            }
        }
    }

    /// The value of `actor`'s best whole turn from `s` and its actions up to the first draw (atomic_bot._tree): a
    /// decision is the best of its actions for the actor, a draw the average over what it may bring, a finished turn
    /// the leaf (None: not followed, so never chosen). `hist` is the cards drawn so far.
    /// The candidate network's beam at a decision of `actor` in `s`: its `beam` likeliest of `legal`, in its order,
    /// plus a den capture, whatever it scored (the net ranks wins first anyway; checking every action for a win
    /// would cost an engine run each, which the net is there to save).
    fn cand_beam(&self, net: &super::cand::CandNet, s: &State, actor: Player, legal: Vec<Action>) -> Vec<Action> {
        let scores = net.scores(s, actor, &legal);
        let mut order: Vec<usize> = (0..legal.len()).collect();
        order.sort_by(|&i, &j| scores[j].partial_cmp(&scores[i]).unwrap_or(std::cmp::Ordering::Equal).then(i.cmp(&j)));
        let mut keep = vec![false; legal.len()];
        for &i in order.iter().take(self.beam) {
            keep[i] = true;
        }
        for (i, a) in legal.iter().enumerate() {
            if !keep[i] && matches!(a, Action::Roam { target: Target::Hq(_), .. }) {   // a den capture is never cut
                keep[i] = true;
            }
        }
        order.iter().filter(|&&i| keep[i]).map(|&i| legal[i].clone()).collect()
    }

    fn tree(&mut self, mut s: State, actor: Player, me: Player, ctx: &mut Leaf, hist: &mut Vec<i64>,
            memo: &mut FxHashMap<(Vec<i64>, Vec<i64>), Option<(f64, Vec<Action>)>>, prob: f64, alpha: f64, beta: f64) -> Option<(f64, Vec<Action>)> {
        self.resolve_others(&mut s, actor);
        if rules::is_terminal(&s).is_some() || s.player_to_act() != actor {
            return self.leaf(ctx, &s, hist, prob, me).map(|v| (v, Vec::new()));
        }
        let mk = (key(&s), hist.clone());
        if let Some(r) = memo.get(&mk) {
            return r.clone();
        }
        let mine = actor == me;
        let ai = actor as usize;
        let mut best: Option<(f64, Vec<Action>)> = None;
        let mut legal = rules::legal_actions(&s);
        let selective = self.beam > 0 && (self.cand.is_some() || !matches!(ctx.mode, LeafMode::Card | LeafMode::Kinds));   // the net's beam holds inside the draw searches too
        if selective && legal.len() > self.beam {
            if let Some(net) = &self.cand {
                // the candidate network's beam: its `beam` likeliest actions for the side choosing, plus any that
                // decide the game at once
                let net = net.clone();
                legal = self.cand_beam(&net, &s, actor, legal);
            } else {
            // the actions that leave the turn open, best first for the side choosing by the board they leave; the rest
            // of those are not searched on
            let mut open: Vec<(f64, Action)> = Vec::new();
            let mut kept: Vec<Action> = Vec::new();
            for a in legal.drain(..) {
                let mut nxt = s.clone();
                let _ = rules::apply_action(&mut nxt, &a, false);
                if matches!(a, Action::Draw) {
                    kept.push(a);
                    continue;
                }
                self.resolve_others(&mut nxt, actor);
                if rules::is_terminal(&nxt).is_some() || nxt.player_to_act() != actor {
                    kept.push(a);
                    continue;
                }
                open.push((self.value(&nxt, me), a));
            }
            if mine {
                open.sort_by(|x, y| y.0.partial_cmp(&x.0).unwrap_or(std::cmp::Ordering::Equal));
            } else {
                open.sort_by(|x, y| x.0.partial_cmp(&y.0).unwrap_or(std::cmp::Ordering::Equal));
            }
            let mut first: Vec<Action> = open.into_iter().take(self.beam).map(|(_, a)| a).collect();
            first.extend(kept);
            legal = first;
            }
        }
        for a in legal {
            let mut nxt = s.clone();
            let _ = rules::apply_action(&mut nxt, &a, false);
            let before = s.decks[ai].len();
            let after = nxt.decks[ai].len();
            let judged = if self.by_card && after < before && ctx.mode == LeafMode::Plain && actor != me {
                self.by_card(&s, actor, me, &a, before - after)
            } else {
                None
            };
            if ctx.mode == LeafMode::Kinds && after < before {
                // a second draw that ends their turn: one position, whatever it brings
                let mut x = nxt.clone();
                self.resolve_others(&mut x, actor);
                if rules::is_terminal(&x).is_some() || x.player_to_act() != actor {
                    ctx.kinds.as_mut().unwrap().n += before - after;
                    let r = self.leaf(ctx, &x, hist, prob, me);
                    ctx.kinds.as_mut().unwrap().n -= before - after;
                    if let Some(v) = r {
                        if best.as_ref().map_or(true, |(b, _)| v < *b) {
                            best = Some((v, vec![a.clone()]));
                        }
                    }
                    continue;
                }
                ctx.chain = true;     // a second draw: judged the old way
                continue;
            }
            let (v, path) = if let Some(v) = judged {
                (v, vec![a.clone()])
            } else if after < before {
                let outs = self.outcomes(&s, actor, &a, before - after);
                let mut vals: Vec<f64> = Vec::with_capacity(outs.len());
                let mut ws: Vec<f64> = Vec::with_capacity(outs.len());
                for (w, x, taken) in outs.iter() {
                    let n = hist.len();
                    hist.push(-1);
                    hist.extend(taken.iter().copied());
                    let r = self.tree(x.clone(), actor, me, ctx, hist, memo, prob * w, f64::NEG_INFINITY, f64::INFINITY);
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
                match self.tree(nxt, actor, me, ctx, hist, memo, prob, alpha, beta) {
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
                if ctx.mode == LeafMode::Kinds {
                    continue;     // every play is wanted, each for the card it uses
                }
                if if mine { v >= self.base.decisive } else { v <= -self.base.decisive } {
                    break;     // a decided win for the actor: nothing can beat it
                }
                if hist.is_empty() && if mine { v >= beta } else { v <= alpha } {
                    break;     // the side choosing above would never allow it (before any draw only)
                }
            }
        }
        memo.insert(mk, best.clone());
        best
    }

    fn run_tree(&mut self, s: &State, actor: Player, me: Player, ctx: &mut Leaf) -> Option<(f64, Vec<Action>)> {
        self.run_tree_in(s, actor, me, ctx, f64::NEG_INFINITY, f64::INFINITY)
    }

    fn run_tree_in(&mut self, s: &State, actor: Player, me: Player, ctx: &mut Leaf, alpha: f64, beta: f64) -> Option<(f64, Vec<Action>)> {
        let mut memo = FxHashMap::default();
        self.tree(s.clone(), actor, me, ctx, &mut Vec::new(), &mut memo, 1.0, alpha, beta)
    }

    pub fn line_value(&mut self, s: &State, me: Player, plies: usize) -> f64 {
        self.best_line(s, me, plies, f64::NEG_INFINITY, f64::INFINITY).0
    }

    /// (the value, the actions of the first turn up to its first draw of) the line followed `plies` whole turns deep
    /// (atomic_bot.best_line): the last turn judged on the board, the earlier ones by following, for every set of cards
    /// drawn, the best `inner` of their finished turns for that side further.
    pub fn best_line(&mut self, s: &State, me: Player, plies: usize, alpha: f64, beta: f64) -> (f64, Vec<Action>) {
        if plies == 0 || rules::is_terminal(s).is_some() {
            return (self.value(s, me), Vec::new());
        }
        let actor = s.player_to_act();
        let mine = actor == me;
        if plies == 1 {
            let mut ctx = Leaf::new(LeafMode::Plain, 0, -1);
            return match self.run_tree_in(s, actor, me, &mut ctx, alpha, beta) {
                Some(r) => r,
                None => (self.value(s, me), Vec::new()),
            };
        }
        let shared = if mine { Some(seen(s, me)) } else { None };
        let cached = shared.as_ref().and_then(|k| self.passes.get(k).cloned());
        let (first, followed) = match cached {
            Some(c) => c,
            None => {
                let mut ctx = Leaf::new(LeafMode::Board, 0, -1);
                let first = match self.run_tree(s, actor, me, &mut ctx) {
                    Some(r) => r,
                    None => return (self.value(s, me), Vec::new()),
                };
                let mut followed: FxHashMap<Vec<i64>, FxHashSet<Vec<i64>>> = FxHashMap::default();
                for (h, es, _, _) in &ctx.ends {
                    let mut es = es.clone();
                    if mine {
                        es.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
                    } else {
                        es.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
                    }
                    followed.insert(h.clone(), es.into_iter().take(self.inner).map(|(k, _)| k).collect());
                }
                if let Some(k) = shared {
                    self.passes.insert(k, (first.clone(), followed.clone()));
                }
                (first, followed)
            }
        };
        let mut deep = Leaf::new(LeafMode::Deep, plies - 1, -1);
        deep.followed = followed;
        deep.mine = mine;
        deep.alpha = alpha;
        deep.beta = beta;
        deep.achieved = if mine { alpha } else { beta };
        self.run_tree_in(s, actor, me, &mut deep, alpha, beta).unwrap_or(first)
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
        self.passes.clear();
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
            // a turn already won or lost outright in a hand one level up stays so deeper: nothing to search there
            let mut decided: FxHashMap<(usize, usize), f64> = FxHashMap::default();
            if lv > 0 {
                for &i in &go {
                    if let Some(prev) = &rows[i].per_hand[lv - 1] {
                        for (k, &v) in prev.iter().enumerate() {
                            if v.abs() >= self.base.decisive {
                                decided.insert((i, k), v);
                            }
                        }
                    }
                }
            }
            let jobs: Vec<(usize, usize)> = go.iter().flat_map(|&i| (0..worlds.len()).map(move |k| (i, k))).filter(|j| !decided.contains_key(j)).collect();
            let mut values = self.run_jobs(&rows, &jobs, me, plies);
            values.extend(decided);
            for &i in &go {
                let vs: Vec<f64> = (0..worlds.len()).map(|k| values[&(i, k)]).collect();
                rows[i].levels[lv] = Some(self.mix(&vs, weights));
                rows[i].per_hand[lv] = Some(vs);
            }
            let mut next = go.clone();
            next.sort_by(|&a, &b| rows[b].levels[lv].unwrap().partial_cmp(&rows[a].levels[lv].unwrap()).unwrap_or(std::cmp::Ordering::Equal));
            pool = next;
        }
        if std::env::var("AK_COUNT").is_ok() {
            eprintln!("KINDS searched={} fell_back={}", FALLBACKS[0].load(std::sync::atomic::Ordering::Relaxed), FALLBACKS[1].load(std::sync::atomic::Ordering::Relaxed));
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
        // one shared queue: a thread takes the next job when it is free, so no core waits on another's slow share
        let next = std::sync::atomic::AtomicUsize::new(0);
        let results: Vec<Vec<((usize, usize), f64)>> = std::thread::scope(|scope| {
            let handles: Vec<_> = (0..t)
                .map(|_| {
                    let mut me_bot = self.clone();
                    let next = &next;
                    scope.spawn(move || {
                        let mut done = Vec::new();
                        loop {
                            let n = next.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
                            if n >= jobs.len() {
                                break;
                            }
                            let (i, k) = jobs[n];
                            done.push(((i, k), me_bot.after_my_turn(&rows[i].ends[k], me, rows[i].open, plies, k as i64)));
                        }
                        done
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

/// The position after action `a` when the cards it takes from the actor's deck are `taken` (atomic_bot._dealt).
fn dealt(st: &State, actor: Player, a: &Action, taken: &[CardId]) -> State {
    let ai = actor as usize;
    let mut want: Vec<CardId> = taken.to_vec();
    let mut rest: Vec<CardId> = Vec::new();
    for &c in st.decks[ai].iter().rev() {
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
    x
}

/// `key` with the opponent's hand as its size only: what `me` can see of the position.
fn seen_key(s: &State, me: Player) -> Vec<i64> {
    let mut k = key(s);
    let o = other(me) as usize;
    // the hands follow the first -2 (A) and the second -2 (B) markers; replace the opponent's by its size
    let marks: Vec<usize> = k.iter().enumerate().filter(|(_, &x)| x == -2).map(|(i, _)| i).collect();
    let end = k.iter().position(|&x| x == -3).unwrap();
    let (from, to) = if o == 0 { (marks[0] + 1, marks[1]) } else { (marks[1] + 1, end) };
    let n = (to - from) as i64;
    k.splice(from..to, std::iter::once(1000 + n));
    k
}

/// The whole position as `me` sees it, as text: the opponent's hand as its size, both decks as their contents, no
/// unit ids, no random stream.
fn seen(s: &State, me: Player) -> String {
    let mut j = s.to_json();
    let opp = if other(me) == 0 { "A" } else { "B" };
    let n = j["hands"][opp].as_array().map_or(0, |a| a.len());
    j["hands"][opp] = sj::Value::from(n);
    for p in ["A", "B"] {
        if let Some(d) = j["decks"][p].as_array_mut() {
            d.sort_by(|a, b| a.as_str().cmp(&b.as_str()));
        }
    }
    if let Some(o) = j.as_object_mut() {
        o.remove("rng");
        o.remove("next_iid");
    }
    fn strip(v: &mut sj::Value) {
        match v {
            sj::Value::Object(m) => {
                m.remove("iid");
                for (_, x) in m.iter_mut() {
                    strip(x);
                }
            }
            sj::Value::Array(a) => {
                for x in a.iter_mut() {
                    strip(x);
                }
            }
            _ => {}
        }
    }
    strip(&mut j);
    j.to_string()
}

/// `a` without the cards of `b` (sorted multisets).
fn msub(a: &[CardId], b: &[CardId]) -> Vec<CardId> {
    let mut b: Vec<CardId> = b.to_vec();
    b.sort_unstable();
    let mut out = Vec::with_capacity(a.len());
    let mut j = 0;
    for &x in a {
        while j < b.len() && b[j] < x {
            j += 1;
        }
        if j < b.len() && b[j] == x {
            j += 1;
        } else {
            out.push(x);
        }
    }
    out
}

/// Every distinct set of `k` cards from `deck` (sorted) at its odds, each scored by `f` (None: left out).
fn draw_sets(deck: &[CardId], k: usize, mut f: impl FnMut(&[CardId]) -> Option<f64>) -> (Vec<f64>, Vec<f64>) {
    let mut kinds: Vec<CardId> = Vec::new();
    let mut counts: Vec<usize> = Vec::new();
    for &c in deck {
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
    let (mut vals, mut ws) = (Vec::new(), Vec::new());
    for ks in &found {
        let mut got: Vec<CardId> = Vec::new();
        let mut w = 1.0f64;
        for ((&c, &n), &cnt) in kinds.iter().zip(ks.iter()).zip(counts.iter()) {
            w *= comb(cnt, n) as f64;
            for _ in 0..n {
                got.push(c);
            }
        }
        if let Some(v) = f(&got) {
            vals.push(v);
            ws.push(w);
        }
    }
    let total: f64 = ws.iter().sum();
    (vals, ws.iter().map(|w| w / total).collect())
}

/// Whether every card of `a` is in `b` (sorted multisets).
fn msubset(a: &[CardId], b: &[CardId]) -> bool {
    let mut j = 0;
    for &x in a {
        while j < b.len() && b[j] < x {
            j += 1;
        }
        if j < b.len() && b[j] == x {
            j += 1;
        } else {
            return false;
        }
    }
    true
}
