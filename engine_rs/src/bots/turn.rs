//! The whole-turn bot: it plans its complete turn and scores only finished turns.
//!
//! From the position it stands on it follows every action, then every action after that, layer by layer, until each
//! line has ended the turn; ending the turn is an option at every quiet point, so holding a card or mana back is a turn
//! like any other. Lines that reach the same position by different orders are one line (`key`). A finished turn is
//! scored where the opponent is to move (`eval`), and each position takes the best finished turn below it.
//!
//! The budget is a count of positions for the turn, never a clock. A search gets half of what the turn has left. It
//! runs at a small width first (how many unfinished positions a layer keeps, ranked by the turn that ends there) and
//! again four times wider while the next pass is affordable, until a pass follows everything; every pass's lines are
//! real turns, so each action keeps the best one any pass found. A search that followed everything hands over its
//! whole line; one that did not hands over its first action only, and the bot searches again from where that lands.
//!
//! What it cannot see it never reads: it searches worlds dealt from the seat's knowledge (`seat`). A draw inside its
//! turn is the card of an imagined deck, so when a search meets one, each first action is scored as its average over
//! `worlds` imagined decks, only the first action is played, and the bot searches again once the real card is in hand.

use std::collections::{HashMap, VecDeque};

use crate::actions::{Action, Target};
use crate::bots::eval::{evaluate, RaidOdds, Weights};
use crate::bots::key::position_key;
use crate::bots::seat::{self, Unseen};
use crate::bots::{Bot, BotStats, Timer};
use crate::data::*;
use crate::rng::PyRandom;
use crate::rules;
use crate::state::{Choice, Options, State};

#[derive(Clone, Debug)]
pub struct TurnSpec {
    /// Positions a turn may make.
    pub budget: u64,
    /// Imagined decks a first action is averaged over when the turn can draw.
    pub worlds: usize,
    /// The most unfinished positions a layer keeps, however large the budget.
    pub width: usize,
    /// Sampled enemy hands behind the raid odds.
    pub samples: usize,
    pub weights: Weights,
}

impl Default for TurnSpec {
    fn default() -> TurnSpec {
        TurnSpec { budget: 20_000, worlds: 4, width: 16_384, samples: 12, weights: Weights::default() }
    }
}

impl TurnSpec {
    pub fn parse(settings: &[(&str, &str)]) -> Result<TurnSpec, String> {
        let mut spec = TurnSpec::default();
        for &(k, v) in settings {
            let int = || v.parse::<u64>().map_err(|_| format!("bot spec: {k}={v:?} is not a whole number"));
            match k {
                "budget" => spec.budget = int()?.max(1),
                "worlds" => spec.worlds = int()?.max(1) as usize,
                "width" => spec.width = int()?.max(1) as usize,
                "samples" => spec.samples = int()?.max(1) as usize,
                _ => match k.strip_prefix("w.") {
                    Some(name) => spec.weights.set(name, v.parse::<f32>().map_err(|_| format!("bot spec: {k}={v:?} is not a number"))?)?,
                    None => return Err(format!("bot spec: turn has no setting {k:?}")),
                },
            }
        }
        Ok(spec)
    }
}

const NEG: f32 = f32::NEG_INFINITY;
const LEAF: u32 = u32::MAX;
const NO_EDGE: u32 = u32::MAX;
const PASS_EDGE: u32 = u32::MAX - 1;
const FIRST_WIDTH: usize = 16;

/// A position of one layer: the best finished turn at or below it, and where that goes.
#[derive(Clone, Copy)]
struct Meta {
    best: f32,
    best_edge: u32,
    e0: u32,
    e1: u32,
}

#[derive(Clone, Copy)]
struct Edge {
    action: Action,
    /// The position it reaches in the next layer, or LEAF when the action ended the turn or the game.
    child: u32,
    value: f32,
}

struct Ctx<'a> {
    me: Player,
    w: &'a Weights,
    odds: &'a RaidOdds,
    max_width: usize,
}

/// The search of one world: its first actions and the best finished turn found behind each.
struct WorldSearch {
    root: State,
    actions: Vec<Action>,
    values: Vec<f32>,
    /// The best line found, as actions from the root.
    line: Vec<Action>,
    line_value: f32,
    /// A draw or a look at the deck happened somewhere in the search: its values rest on an imagined deck.
    hidden: bool,
    /// A pass followed every line to the end of the turn.
    exhaustive: bool,
    positions: u64,
    next_width: usize,
    last_cost: u64,
}

fn may_pass(st: &State, me: Player) -> bool {
    st.current == me && rules::can_pass(st)
}

impl WorldSearch {
    fn new(root: State, me: Player) -> WorldSearch {
        let mut actions: Vec<Action> = rules::legal_actions(&root).into_iter().filter(|a| *a != Action::Pass).collect();
        if may_pass(&root, me) || actions.is_empty() {
            actions.push(Action::Pass);
        }
        let values = vec![NEG; actions.len()];
        WorldSearch { root, actions, values, line: Vec::new(), line_value: NEG, hidden: false, exhaustive: false, positions: 0,
                      next_width: FIRST_WIDTH, last_cost: 0 }
    }

    /// Widen pass by pass until one follows everything, the width cap is reached, or the next pass would not fit under
    /// `limit` positions in all.
    fn run(&mut self, ctx: &Ctx, limit: u64) {
        while !self.exhaustive && self.next_width <= ctx.max_width.max(FIRST_WIDTH) {
            if self.last_cost > 0 && self.positions + 2 * self.last_cost > limit {
                break;
            }
            let before = self.positions;
            self.pass(ctx, self.next_width.min(ctx.max_width), limit);
            self.last_cost = (self.positions - before).max(1);
            self.next_width *= 4;
        }
    }

    /// The value of ending the turn at the quiet position `st`.
    fn pass_value(&mut self, ctx: &Ctx, st: &State) -> f32 {
        let mut p = st.clone();
        self.positions += 1;
        match rules::apply_action(&mut p, &Action::Pass, false) {
            Ok(()) => evaluate(&p, ctx.me, ctx.w, ctx.odds),
            Err(_) => NEG,
        }
    }

    fn pass(&mut self, ctx: &Ctx, width: usize, limit: u64) {
        let me = ctx.me;
        let root_current = self.root.current;
        let ended = |c: &State| c.result.is_some() || c.player_to_act() != me || c.current != root_current;
        let mut metas: Vec<Vec<Meta>> = Vec::new();
        let mut edges: Vec<Vec<Edge>> = Vec::new();
        let (mut cut, mut truncated) = (false, false);

        let root = self.root.clone();
        let root_best = if may_pass(&root, me) { self.pass_value(ctx, &root) } else { NEG };
        metas.push(vec![Meta { best: root_best, best_edge: if root_best > NEG { PASS_EDGE } else { NO_EDGE }, e0: 0, e1: 0 }]);
        let mut cur: Vec<Option<State>> = vec![Some(root)];

        loop {
            let depth = metas.len() - 1;
            let mut next_states: Vec<Option<State>> = Vec::new();
            let mut next_metas: Vec<Meta> = Vec::new();
            let mut ranks: Vec<f32> = Vec::new();
            let mut index: HashMap<u64, u32> = HashMap::new();
            let mut layer_edges: Vec<Edge> = Vec::new();
            let mut live = 0usize;
            for i in 0..cur.len() {
                let Some(st) = cur[i].take() else { continue };
                if depth > 0 && self.positions >= limit {
                    // out of budget: the turn ends here in this pass (a position with a choice waiting is scored as it stands)
                    truncated = true;
                    if metas[depth][i].best == NEG {
                        metas[depth][i].best = evaluate(&st, me, ctx.w, ctx.odds);
                    }
                    continue;
                }
                let e0 = layer_edges.len() as u32;
                let deck = st.decks[me as usize].len();
                for a in rules::legal_actions(&st) {
                    if a == Action::Pass {
                        continue;
                    }
                    let mut c = st.clone();
                    if rules::apply_action(&mut c, &a, false).is_err() {
                        continue;
                    }
                    self.positions += 1;
                    if c.decks[me as usize].len() != deck || matches!(&c.pending, Some(p) if matches!(p.options, Options::Deck(_))) {
                        self.hidden = true;
                    }
                    if ended(&c) {
                        layer_edges.push(Edge { action: a, child: LEAF, value: evaluate(&c, me, ctx.w, ctx.odds) });
                        continue;
                    }
                    let key = position_key(&c, me, true);
                    let child = match index.get(&key) {
                        Some(&at) => at,
                        None => {
                            let at = next_metas.len() as u32;
                            let quiet = c.pending.is_none() && c.effect_stack.is_empty();
                            if quiet {
                                let v = self.pass_value(ctx, &c);
                                next_metas.push(Meta { best: v, best_edge: if v > NEG { PASS_EDGE } else { NO_EDGE }, e0: 0, e1: 0 });
                                ranks.push(v + ctx.w.mana_rank * rules::mana_left(&c, me) as f32);
                                live += 1;
                            } else {
                                // a choice is waiting: never dropped by the width
                                next_metas.push(Meta { best: NEG, best_edge: NO_EDGE, e0: 0, e1: 0 });
                                ranks.push(f32::INFINITY);
                            }
                            next_states.push(Some(c));
                            index.insert(key, at);
                            at
                        }
                    };
                    layer_edges.push(Edge { action: a, child, value: 0.0 });
                }
                metas[depth][i].e0 = e0;
                metas[depth][i].e1 = layer_edges.len() as u32;
                if live > 2 * width {
                    live = keep_best(&mut next_states, &ranks, width);
                    cut = true;
                }
            }
            edges.push(layer_edges);
            if next_metas.is_empty() {
                break;
            }
            if live > width {
                keep_best(&mut next_states, &ranks, width);
                cut = true;
            }
            metas.push(next_metas);
            cur = next_states;
        }

        // each position takes the best finished turn below it
        for d in (0..metas.len()).rev() {
            let (here, below) = metas.split_at_mut(d + 1);
            let here = &mut here[d];
            for m in here.iter_mut() {
                for e in m.e0..m.e1 {
                    let edge = &edges[d][e as usize];
                    let v = if edge.child == LEAF { edge.value } else { below[0][edge.child as usize].best };
                    if v > m.best {
                        m.best = v;
                        m.best_edge = e;
                    }
                }
            }
        }

        // the first actions' values
        let root = metas[0][0];
        for e in root.e0..root.e1 {
            let edge = &edges[0][e as usize];
            let v = if edge.child == LEAF { edge.value } else { metas[1][edge.child as usize].best };
            if let Some(at) = self.actions.iter().position(|a| *a == edge.action) {
                self.values[at] = self.values[at].max(v);
            }
        }
        if root_best > NEG {
            if let Some(at) = self.actions.iter().position(|a| *a == Action::Pass) {
                self.values[at] = self.values[at].max(root_best);
            }
        }
        if root.best > self.line_value {
            self.line_value = root.best;
            self.line.clear();
            let (mut d, mut i) = (0usize, 0usize);
            loop {
                let m = metas[d][i];
                match m.best_edge {
                    NO_EDGE => break,
                    PASS_EDGE => {
                        self.line.push(Action::Pass);
                        break;
                    }
                    e => {
                        let edge = edges[d][e as usize];
                        self.line.push(edge.action);
                        if edge.child == LEAF {
                            break;
                        }
                        d += 1;
                        i = edge.child as usize;
                    }
                }
            }
        }
        if !cut && !truncated {
            self.exhaustive = true;
        }
    }
}

/// Drop all but the `width` best-ranked positions still to follow; a position with a choice waiting (rank infinite) is
/// kept. How many ranked positions are left.
fn keep_best(states: &mut [Option<State>], ranks: &[f32], width: usize) -> usize {
    let mut live: Vec<(f32, usize)> = states.iter().enumerate()
        .filter(|(i, s)| s.is_some() && ranks[*i].is_finite()).map(|(i, _)| (ranks[i], i)).collect();
    if live.len() <= width {
        return live.len();
    }
    live.sort_unstable_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal).then(a.1.cmp(&b.1)));
    for &(_, i) in &live[width..] {
        states[i] = None;
    }
    width
}

/// A turn of raids alone that empties the enemy den, if the hand holds one now and no draw is needed for it.
fn raid_win(st: &State, me: Player, left: &mut i64, positions: &mut u64, line: &mut Vec<Action>) -> bool {
    if st.pending.is_some() || st.current != me {
        return false;
    }
    for a in rules::legal_actions(st) {
        if !matches!(a, Action::Place { target: Target::Den(_), .. }) {
            continue;
        }
        if *left <= 0 {
            return false;
        }
        let mut c = st.clone();
        if rules::apply_action(&mut c, &a, false).is_err() {
            continue;
        }
        *left -= 1;
        *positions += 1;
        if matches!(c.result, Some(r) if r.winner == Some(me)) {
            line.push(a);
            return true;
        }
        if c.result.is_some() || c.player_to_act() != me || c.decks[me as usize].len() != st.decks[me as usize].len() {
            continue;
        }
        line.push(a);
        if raid_win(&c, me, left, positions, line) {
            return true;
        }
        line.pop();
    }
    false
}

pub struct TurnBot {
    spec: TurnSpec,
    rng: PyRandom,
    stats: BotStats,
    turn_seen: i32,
    /// Positions made this turn, and searches run.
    used: u64,
    searches: u32,
    /// The rest of the line a search handed over: each action with the key of the position it expects to stand on.
    plan: VecDeque<(u64, Action)>,
}

impl TurnBot {
    pub fn new(spec: TurnSpec, seed: u64) -> TurnBot {
        TurnBot { spec, rng: PyRandom::seeded_u64(seed), stats: BotStats::default(), turn_seen: -1, used: 0, searches: 0, plan: VecDeque::new() }
    }

    /// `line` from the world `root`, each action with the key of what the seat sees before it.
    fn keyed(root: &State, me: Player, line: &[Action]) -> VecDeque<(u64, Action)> {
        let mut out = VecDeque::new();
        let mut st = root.clone();
        for a in line {
            out.push_back((position_key(&st, me, false), *a));
            if rules::apply_action(&mut st, a, false).is_err() {
                out.pop_back();
                break;
            }
        }
        out
    }

    fn search(&mut self, real: &State, me: Player) -> Action {
        let seen: Unseen = seat::unseen(real, me);
        let world = seat::world(real, me, &seen, &mut self.rng);
        let odds = RaidOdds::sample(&world, me, &seen, self.spec.samples, &mut self.rng);
        let first = self.searches == 0;
        self.searches += 1;
        self.stats.searches += 1;
        let mut positions = 0u64;

        // a win on the spot comes before any search
        let mut line = Vec::new();
        if raid_win(&world, me, &mut 2000, &mut positions, &mut line) {
            self.plan = Self::keyed(&world, me, &line);
            self.count(positions);
            return self.plan.pop_front().map_or(Action::Pass, |(_, a)| a);
        }

        let allowance = (self.spec.budget.saturating_sub(self.used + positions) / 2).max(1);
        let can_draw = !world.decks[me as usize].is_empty();
        let k = if can_draw { self.spec.worlds.max(1) as u64 } else { 1 };
        let ctx = Ctx { me, w: &self.spec.weights, odds: &odds, max_width: self.spec.width };
        let mut s0 = WorldSearch::new(world, me);
        s0.run(&ctx, (allowance / k).max(1));
        if !s0.hidden && k > 1 {
            s0.run(&ctx, allowance); // nothing hidden in this turn: the one world is the truth, and takes the whole allowance
        }
        positions += s0.positions;
        let mut sums: Vec<f32> = s0.values.clone();
        let mut exhaustive = s0.exhaustive;
        if s0.hidden {
            let mut n = 1.0f32;
            for _ in 1..k {
                let w = seat::world(real, me, &seen, &mut self.rng);
                let mut s = WorldSearch::new(w, me);
                s.run(&ctx, (allowance / k).max(1));
                positions += s.positions;
                exhaustive &= s.exhaustive;
                if s.actions == s0.actions {
                    for (sum, v) in sums.iter_mut().zip(&s.values) {
                        *sum += *v;
                    }
                    n += 1.0;
                }
            }
            for sum in sums.iter_mut() {
                *sum /= n;
            }
        }
        if first {
            self.stats.turns_cut += !exhaustive as u64;
            self.stats.turns_hidden += s0.hidden as u64;
        }
        self.count(positions);

        let mut best = 0usize;
        for (i, v) in sums.iter().enumerate() {
            if *v > sums[best] {
                best = i;
            }
        }
        let action = s0.actions.get(best).copied().unwrap_or(Action::Pass);
        self.plan.clear();
        if !s0.hidden && s0.exhaustive && s0.line.first() == Some(&action) {
            self.plan = Self::keyed(&s0.root, me, &s0.line);
            self.plan.pop_front();
        }
        action
    }

    fn count(&mut self, positions: u64) {
        self.used += positions;
        self.stats.positions += positions;
        self.stats.max_turn_positions = self.stats.max_turn_positions.max(self.used);
    }
}

fn legal_now(st: &State, me: Player, a: &Action) -> bool {
    match a {
        Action::Pass => may_pass(st, me),
        _ => rules::legal_actions(st).contains(a),
    }
}

impl Bot for TurnBot {
    fn choose(&mut self, real: &State) -> Action {
        let timer = Timer::start();
        let me = real.player_to_act();
        let action = if real.pending.as_ref().map_or(false, |p| p.mulligan) {
            Action::Choice(Choice::Skip) // it keeps its opening hand
        } else {
            if real.current == me && real.turn_counter != self.turn_seen {
                self.turn_seen = real.turn_counter;
                self.used = 0;
                self.searches = 0;
                self.plan.clear();
                self.stats.turns += 1;
            }
            let planned = match self.plan.front() {
                Some(&(key, a)) if key == position_key(real, me, false) && legal_now(real, me, &a) => Some(a),
                _ => None,
            };
            match planned {
                Some(a) => {
                    self.plan.pop_front();
                    a
                }
                None => {
                    self.plan.clear();
                    self.search(real, me)
                }
            }
        };
        timer.stop(&mut self.stats);
        action
    }

    fn stats(&self) -> BotStats {
        self.stats
    }

    fn spec(&self) -> String {
        format!("turn:budget={},worlds={},width={},samples={}", self.spec.budget, self.spec.worlds, self.spec.width, self.spec.samples)
    }
}

/// How large one turn is, for the turn-size statistics: every action followed from `root` with no width and no budget
/// but `cap` positions. (positions made with equal positions merged, distinct finished turns, whether the cap cut it)
pub fn turn_size(root: &State, cap: u64) -> (u64, u64, bool) {
    let me = root.player_to_act();
    let root_current = root.current;
    let mut positions = 0u64;
    let mut ends: std::collections::HashSet<u64> = std::collections::HashSet::new();
    let mut cur: Vec<State> = vec![root.clone()];
    while !cur.is_empty() {
        let mut next: Vec<State> = Vec::new();
        let mut index: std::collections::HashSet<u64> = std::collections::HashSet::new();
        for st in &cur {
            let mut actions = rules::legal_actions(st);
            if may_pass(st, me) && !actions.contains(&Action::Pass) {
                actions.push(Action::Pass);
            }
            for a in actions {
                if positions >= cap {
                    return (positions, ends.len() as u64, true);
                }
                let mut c = st.clone();
                if rules::apply_action(&mut c, &a, false).is_err() {
                    continue;
                }
                positions += 1;
                let key = position_key(&c, me, true);
                if c.result.is_some() || c.player_to_act() != me || c.current != root_current {
                    ends.insert(key);
                } else if index.insert(key) {
                    next.push(c);
                }
            }
        }
        cur = next;
    }
    (positions, ends.len() as u64, false)
}

/// The same turn with nothing merged: every sequence of actions counted on its own, up to `cap` positions.
pub fn turn_size_unmerged(root: &State, cap: u64) -> (u64, bool) {
    fn walk(st: &State, me: Player, root_current: Player, positions: &mut u64, cap: u64) -> bool {
        let mut actions = rules::legal_actions(st);
        if may_pass(st, me) && !actions.contains(&Action::Pass) {
            actions.push(Action::Pass);
        }
        for a in actions {
            if *positions >= cap {
                return false;
            }
            let mut c = st.clone();
            if rules::apply_action(&mut c, &a, false).is_err() {
                continue;
            }
            *positions += 1;
            if c.result.is_some() || c.player_to_act() != me || c.current != root_current {
                continue;
            }
            if !walk(&c, me, root_current, positions, cap) {
                return false;
            }
        }
        true
    }
    let mut positions = 0u64;
    let whole = walk(root, root.player_to_act(), root.current, &mut positions, cap);
    (positions, !whole)
}
