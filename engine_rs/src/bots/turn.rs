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
//!
//! Before any search it looks for a win this turn (`win_search`): a line that ends the game for it through the rules,
//! with no hidden card on the way, followed nearest-first and never cut by a width.
//!
//! With `reply=K` a finished turn is not scored where it ends but after the opponent's answer (`search_with_replies`):
//! the K best finished turns are each played out in a few hands the opponent may hold, the opponent takes a win if
//! they have one and otherwise plays the turn their own search likes best, and the turn's score is the mean of the
//! bot's chance of winning from where that leaves it.

use std::collections::{HashMap, VecDeque};

use crate::actions::Action;
use crate::bots::eval::{evaluate, greedy_evaluate, hand_raid, RaidOdds, Weights, WIN};
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
    /// Positions a look for a win may make (`win_search`); 0 never looks. Unset, a sixteenth of the budget.
    pub win: Option<u64>,
    /// The reply level: how many of my best finished turns are scored against the opponent's reply; 0 scores a turn where
    /// it ends, with no reply.
    pub reply: usize,
    /// Of those turns, at most this many that play the same cards on other tiles; 0: the K best whatever they play.
    pub per: usize,
    /// Hands the opponent may hold that each of those turns is scored against.
    pub hands: usize,
    /// Of a search's positions, the share (in hundredths) that plans my own turn; the rest is the replies'.
    pub own: u64,
    /// Deal the opponent's imagined hands spread over their cards' costs (`seat::redeal`).
    pub spread: bool,
    /// The evaluation as a chance of winning: 1 / (1 + exp(-(score ± tempo) / scale)), the tempo taken off the player who
    /// has just moved (`bot_bench evalfit` fits both).
    pub scale: f32,
    pub tempo: f32,
    /// Above 0: score a turn by the mean of the raw evaluation after the reply instead, a game won or lost counting as
    /// this much. The way the old game's bot averaged; kept to measure it against the chance of winning.
    pub decisive: f32,
    /// Score finished turns with the shipped greedy bot's evaluation instead (`eval=greedy`): what the search alone is
    /// worth, with the evaluation held fixed.
    pub greedy_eval: bool,
    pub weights: Weights,
}

impl Default for TurnSpec {
    fn default() -> TurnSpec {
        TurnSpec { budget: 20_000, worlds: 4, width: 16_384, samples: 12, win: None, reply: 0, per: 0, hands: 3, own: 25, spread: false, scale: 15.0,
                   tempo: 10.0, decisive: 0.0, greedy_eval: false, weights: Weights::default() }
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
                "win" => spec.win = Some(int()?),
                "reply" => spec.reply = int()? as usize,
                "per" => spec.per = int()? as usize,
                "hands" => spec.hands = int()?.max(1) as usize,
                "own" => spec.own = int()?.clamp(1, 99),
                "spread" => spec.spread = int()? != 0,
                "scale" => spec.scale = v.parse::<f32>().ok().filter(|x| *x > 0.0).ok_or_else(|| format!("bot spec: {k}={v:?} is not a positive number"))?,
                "tempo" => spec.tempo = v.parse::<f32>().map_err(|_| format!("bot spec: {k}={v:?} is not a number"))?,
                "decisive" => spec.decisive = v.parse::<f32>().map_err(|_| format!("bot spec: {k}={v:?} is not a number"))?,
                "eval" => spec.greedy_eval = match v {
                    "greedy" => true,
                    "food" => false,
                    _ => return Err(format!("bot spec: eval={v:?} (food, greedy)")),
                },
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
/// The fewest positions a reply search is worth running on.
const MIN_REPLY: u64 = 500;

/// A position of one layer: the best finished turn at or below it, and where that goes.
#[derive(Clone, Copy)]
struct Meta {
    best: f32,
    best_edge: u32,
    e0: u32,
    e1: u32,
    /// The position of the layer above it was first reached from, and by which action.
    parent: u32,
    via: Action,
    /// What has been played to reach it, whatever the order and the tiles: the cards from hand and the leader's power.
    plays: u64,
}

impl Meta {
    fn new(best: f32, parent: u32, via: Action, plays: u64) -> Meta {
        Meta { best, best_edge: if best > NEG { PASS_EDGE } else { NO_EDGE }, e0: 0, e1: 0, parent, via, plays }
    }
}

/// `plays` with the action `a` added: a card from hand or the power counts, a choice or the end of the turn does not.
#[inline]
fn played(plays: u64, a: &Action) -> u64 {
    let x = match a {
        Action::Place { card, target } => 0x9E37_79B9_7F4A_7C15u64.wrapping_mul(2 * *card as u64 + 3 + matches!(target, crate::actions::Target::Den(_)) as u64),
        Action::Leader => 0xC2B2_AE3D_27D4_EB4F,
        _ => 0,
    };
    plays.wrapping_add(x ^ (x >> 29))
}

/// A finished turn found by a pass: its score, the position it ends from (layer, index), and the action that ends it
/// (none: ending the turn there).
type Finished = (f32, u32, u32, Option<Action>);

/// The best finished turns of a pass, apart by what they play: for each set of plays (which cards, the power, a raid or
/// not; wherever they go) the `per` best-scored.
#[derive(Default)]
struct Top {
    sets: Vec<(u64, Vec<Finished>)>,
}

impl Top {
    fn keep(&mut self, per: usize, plays: u64, item: Finished) {
        if per == 0 {
            return;
        }
        let at = match self.sets.iter().position(|s| s.0 == plays) {
            Some(at) => at,
            None => {
                self.sets.push((plays, Vec::with_capacity(per)));
                self.sets.len() - 1
            }
        };
        let top = &mut self.sets[at].1;
        if top.len() == per && item.0 <= top[per - 1].0 {
            return;
        }
        let i = top.iter().position(|t| item.0 > t.0).unwrap_or(top.len());
        top.insert(i, item);
        top.truncate(per);
    }

    /// The `k` best of what was kept.
    fn best(self, k: usize) -> Vec<Finished> {
        let mut all: Vec<Finished> = self.sets.into_iter().flat_map(|s| s.1).collect();
        all.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        all.truncate(k);
        all
    }
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
    greedy_eval: bool,
    /// How many of the best finished turns a search keeps as whole lines (for the reply level); 0 keeps only the best.
    keep: usize,
    /// Of those, at most this many that play the same cards (on other tiles); 0: no such limit.
    per: usize,
}

impl Ctx<'_> {
    /// How many finished turns a pass keeps for each set of plays.
    #[inline]
    fn per_set(&self) -> usize {
        if self.keep == 0 { 0 } else if self.per == 0 { self.keep } else { self.per }
    }

    /// `plays` as the kept turns are told apart by: all one set when there is no limit.
    #[inline]
    fn set_of(&self, plays: u64) -> u64 {
        if self.per == 0 { 0 } else { plays }
    }
}

impl Ctx<'_> {
    #[inline]
    fn eval(&self, st: &State) -> f32 {
        if self.greedy_eval { greedy_evaluate(st, self.me) as f32 } else { evaluate(st, self.me, self.w, self.odds) }
    }
}

/// The search of one world: its first actions and the best finished turn found behind each.
struct WorldSearch {
    root: State,
    actions: Vec<Action>,
    values: Vec<f32>,
    /// The best line found, as actions from the root.
    line: Vec<Action>,
    line_value: f32,
    /// The best finished turns found, best first: each its score and its whole line (`Ctx::keep` of them).
    turns: Vec<(f32, Vec<Action>)>,
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
        WorldSearch { root, actions, values, line: Vec::new(), line_value: NEG, turns: Vec::new(), hidden: false, exhaustive: false, positions: 0,
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
            Ok(()) => ctx.eval(&p),
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
        let mut top = Top::default();
        if root_best > NEG {
            top.keep(ctx.per_set(), 0, (root_best, 0, 0, None));
        }
        metas.push(vec![Meta::new(root_best, u32::MAX, Action::Pass, 0)]);
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
                        metas[depth][i].best = ctx.eval(&st);
                    }
                    continue;
                }
                let e0 = layer_edges.len() as u32;
                let deck = st.decks[me as usize].len();
                let plays = metas[depth][i].plays;
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
                        let v = ctx.eval(&c);
                        top.keep(ctx.per_set(), ctx.set_of(played(plays, &a)), (v, depth as u32, i as u32, Some(a)));
                        layer_edges.push(Edge { action: a, child: LEAF, value: v });
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
                                if v > NEG {
                                    top.keep(ctx.per_set(), ctx.set_of(played(plays, &a)), (v, depth as u32 + 1, at, None));
                                }
                                next_metas.push(Meta::new(v, i as u32, a, played(plays, &a)));
                                ranks.push(v + ctx.w.mana_rank * rules::mana_left(&c, me) as f32);
                                live += 1;
                            } else {
                                // a choice is waiting: never dropped by the width
                                next_metas.push(Meta::new(NEG, i as u32, a, played(plays, &a)));
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
        // the best finished turns as whole lines, with those of the passes before
        for (v, d, i, last) in top.best(ctx.keep) {
            let mut line = vec![last.unwrap_or(Action::Pass)];
            let (mut d, mut i) = (d as usize, i as usize);
            while d > 0 {
                let m = metas[d][i];
                line.push(m.via);
                i = m.parent as usize;
                d -= 1;
            }
            line.reverse();
            match self.turns.iter_mut().find(|t| t.1 == line) {
                Some(t) => t.0 = t.0.max(v),
                None => self.turns.push((v, line)),
            }
        }
        self.turns.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        self.turns.truncate(ctx.keep);
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

/// What a search for a win found.
pub struct WinSearch {
    /// A line of this turn, from the root, that wins the game with nothing hidden on the way.
    pub line: Option<Vec<Action>>,
    /// It followed every line that meets nothing hidden, so no such win exists when `line` is none.
    pub complete: bool,
    pub positions: u64,
}

/// Is there a turn from `root` that wins the game for `me` now, whatever the hidden cards are?
///
/// The rules decide what wins: a line is a win when playing it through them ends the game for `me`, by an action of
/// the turn (food gained to the winning food, the enemy den emptied) or by ending the turn (the regions' food). The
/// search follows the closest position first (how near `me` is to the winning food if the turn ended there, or the
/// enemy to none), merges positions reached by different orders, keeps every position (no width), and stops at `limit`
/// positions. A line that draws a card or looks at the deck is left out: what follows it rests on an imagined deck.
pub fn win_search(root: &State, me: Player, limit: u64) -> WinSearch {
    use std::cmp::Reverse;
    use std::collections::{BinaryHeap, HashSet};
    struct Node {
        st: State,
        parent: u32,
        action: Action,
    }
    let mut out = WinSearch { line: None, complete: false, positions: 0 };
    if root.result.is_some() || root.player_to_act() != me {
        out.complete = true;
        return out;
    }
    let root_current = root.current;
    let win = root.g.map.win_food;
    // How near a position is: the food short of the win if the turn ended there, less the most food one more tile
    // would add (the regions a single empty tile completes), or the enemy's food less what the hand could raid for
    // now, if that is less; and among equals the
    // tiles held in regions no enemy stands in, a region two tiles in counting more than two regions one tile in. So a
    // line that clears or fills what a region still lacks is followed before one that does neither.
    let near = |st: &State| -> i32 {
        let own = st.food[me as usize] + rules::region_income(st, me) - win;
        let (mine, theirs, occ) = (st.board.own[me as usize], st.board.own[other(me) as usize], st.board.occ);
        let mut progress = 0i32;
        let mut one_more = [0i32; 64];
        for r in &st.g.map.regions {
            if r.mask & theirs == 0 {
                let held = (r.mask & mine).count_ones() as i32;
                progress += held * held;
            }
            let missing = r.mask & !mine;
            if missing.count_ones() == 1 && missing & occ == 0 {
                one_more[missing.trailing_zeros() as usize] += r.food;
            }
        }
        let best = one_more.iter().copied().max().unwrap_or(0);
        // the enemy's food, less what the hand's raids would destroy with the mana left, from where the board stands
        let raid = (hand_raid(st, me, rules::mana_left(st, me)) - st.food[other(me) as usize]).min(0);
        (own + best).min(0).max(raid) * 1000 + progress
    };
    let line_of = |nodes: &[Node], mut at: u32, last: Action| -> Vec<Action> {
        let mut line = vec![last];
        while at != 0 {
            line.push(nodes[at as usize].action);
            at = nodes[at as usize].parent;
        }
        line.reverse();
        line
    };
    let mut nodes: Vec<Node> = vec![Node { st: root.clone(), parent: 0, action: Action::Pass }];
    let mut seen: HashSet<u64> = HashSet::new();
    seen.insert(position_key(root, me, true));
    // the closest first; among equals the earliest made
    let mut open: BinaryHeap<(i32, Reverse<u32>)> = BinaryHeap::new();
    open.push((near(root), Reverse(0)));
    while let Some((_, Reverse(at))) = open.pop() {
        let st = nodes[at as usize].st.clone();
        let deck = st.decks[me as usize].len();
        // ending the turn first: where the regions' food wins it, that is the whole search
        let mut actions: Vec<Action> = Vec::new();
        if may_pass(&st, me) {
            actions.push(Action::Pass);
        }
        actions.extend(rules::legal_actions(&st).into_iter().filter(|a| *a != Action::Pass));
        for a in actions {
            if out.positions >= limit {
                return out;
            }
            let mut c = st.clone();
            if rules::apply_action(&mut c, &a, false).is_err() {
                continue;
            }
            out.positions += 1;
            if let Some(r) = c.result {
                if r.winner == Some(me) {
                    out.line = Some(line_of(&nodes, at, a));
                    return out;
                }
                continue;
            }
            if c.player_to_act() != me || c.current != root_current {
                continue; // the turn ended without the win
            }
            if c.decks[me as usize].len() != deck || matches!(&c.pending, Some(p) if matches!(p.options, Options::Deck(_))) {
                continue; // a card drawn or looked at: hidden
            }
            if seen.insert(position_key(&c, me, true)) {
                let at_new = nodes.len() as u32;
                // a choice waiting is half a play: followed at once, so the play is ranked by where its choices land
                let rank = if c.pending.is_some() { i32::MAX } else { near(&c) };
                open.push((rank, Reverse(at_new)));
                nodes.push(Node { st: c, parent: at, action: a });
            }
        }
    }
    out.complete = true;
    out
}

pub struct TurnBot {
    spec: TurnSpec,
    rng: PyRandom,
    stats: BotStats,
    turn_seen: i32,
    /// Positions made this turn, and searches run.
    used: u64,
    searches: u32,
    /// The newest card my hand held when I last chose, and whether to look for a win at the next search.
    newest: i32,
    look: bool,
    /// The rest of the line a search handed over: each action with the key of the position it expects to stand on.
    plan: VecDeque<(u64, Action)>,
}

impl TurnBot {
    pub fn new(spec: TurnSpec, seed: u64) -> TurnBot {
        TurnBot { spec, rng: PyRandom::seeded_u64(seed), stats: BotStats::default(), turn_seen: -1, used: 0, searches: 0, newest: -1, look: true, plan: VecDeque::new() }
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

        // a win this turn comes before any search: looked for at the turn's start, again when a card has come into
        // the hand, and again while the last look ran out of positions before it had followed everything
        let win_limit = self.spec.win.unwrap_or(self.spec.budget / 16);
        if win_limit > 0 && self.look {
            let left = self.spec.budget.saturating_sub(self.used);
            let won = win_search(&world, me, win_limit.min(left / 2).max(1));
            positions += won.positions;
            if let Some(line) = won.line {
                self.plan = Self::keyed(&world, me, &line);
                self.count(positions);
                return self.plan.pop_front().map_or(Action::Pass, |(_, a)| a);
            }
            self.look = !won.complete;
        }

        let allowance = (self.spec.budget.saturating_sub(self.used + positions) / 2).max(1);
        if self.spec.reply > 0 {
            return self.search_with_replies(me, &seen, world, &odds, allowance, positions, first);
        }
        let can_draw = !world.decks[me as usize].is_empty();
        let k = if can_draw { self.spec.worlds.max(1) as u64 } else { 1 };
        let ctx = Ctx { me, w: &self.spec.weights, odds: &odds, max_width: self.spec.width, greedy_eval: self.spec.greedy_eval, keep: 0, per: 0 };
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

    /// The search with the reply level. My own turn is planned in one world on `own` hundredths of `allowance`; its
    /// best `reply` finished turns are then each played out in `hands` worlds (the same world with the opponent's hidden
    /// cards dealt afresh), where the opponent takes a win if they have one and otherwise plays the turn their own
    /// search likes best, and the turn's score is the mean, over those worlds, of my chance of winning from where their
    /// reply leaves me. What is left of `allowance` after my own turn is split evenly over the replies. A turn that wins
    /// outright is played without asking.
    #[allow(clippy::too_many_arguments)]
    fn search_with_replies(&mut self, me: Player, seen: &Unseen, world: State, odds: &RaidOdds, allowance: u64,
                           mut positions: u64, first: bool) -> Action {
        let opp = other(me);
        let spec = self.spec.clone();
        let ctx = Ctx { me, w: &spec.weights, odds, max_width: spec.width, greedy_eval: spec.greedy_eval, keep: spec.reply, per: spec.per };
        let mut s0 = WorldSearch::new(world, me);
        s0.run(&ctx, (allowance * spec.own / 100).max(1));
        positions += s0.positions;
        if first {
            self.stats.turns_cut += !s0.exhaustive as u64;
            self.stats.turns_hidden += s0.hidden as u64;
        }
        let fallback = |s0: &WorldSearch| -> Action {
            let mut best = 0usize;
            for (i, v) in s0.values.iter().enumerate() {
                if *v > s0.values[best] {
                    best = i;
                }
            }
            s0.actions.get(best).copied().unwrap_or(Action::Pass)
        };
        self.plan.clear();
        if s0.turns.len() < 2 || s0.line_value >= WIN {
            // one turn to play, or a win found: nothing to ask the reply
            let action = s0.line.first().copied().unwrap_or_else(|| fallback(&s0));
            if !s0.hidden && s0.line.first() == Some(&action) {
                self.plan = Self::keyed(&s0.root, me, &s0.line);
                self.plan.pop_front();
            }
            self.count(positions);
            return action;
        }

        // my candidate turns, each where it ends in the search's own world; two that end on one position are one
        struct Cand {
            line: Vec<Action>,
            hidden: bool,
            sum: f32,
            n: u32,
        }
        let mut cands: Vec<Cand> = Vec::new();
        let mut ends: Vec<u64> = Vec::new();
        for (_, line) in &s0.turns {
            let mut st = s0.root.clone();
            let deck = st.decks[me as usize].len();
            let (mut hidden, mut legal) = (false, true);
            for a in line {
                if rules::apply_action(&mut st, a, false).is_err() {
                    legal = false;
                    break;
                }
                positions += 1;
                hidden |= st.decks[me as usize].len() != deck || matches!(&st.pending, Some(p) if matches!(p.options, Options::Deck(_)));
            }
            let key = position_key(&st, me, true);
            if legal && !ends.contains(&key) {
                ends.push(key);
                cands.push(Cand { line: line.clone(), hidden, sum: 0.0, n: 0 });
            }
        }
        // A reply is worth asking only with enough positions to follow the opponent's turn some way (MIN_REPLY): where
        // the search has too few left for every turn in every hand, it asks about fewer turns, then in fewer hands,
        // and with too few for two turns in one hand it plays its own search's best.
        let limit = positions - s0.positions + allowance;
        let affordable = (limit.saturating_sub(positions) / MIN_REPLY) as usize;
        let mut worlds = spec.hands.max(1);
        if cands.len() * worlds > affordable {
            cands.truncate((affordable / worlds).max(2).min(cands.len()));
            worlds = (affordable / cands.len().max(1)).clamp(1, worlds);
        }
        if cands.len() < 2 || cands.len() * worlds > affordable {
            let action = s0.line.first().copied().unwrap_or_else(|| fallback(&s0));
            if !s0.hidden && s0.line.first() == Some(&action) {
                self.plan = Self::keyed(&s0.root, me, &s0.line);
                self.plan.pop_front();
            }
            self.count(positions);
            return action;
        }
        // each reply gets an even share of what is left when its turn comes, so one that runs over is paid for by those
        // after it
        let mut to_come = (cands.len() * worlds) as u64;
        // what the opponent can count of my hidden cards, for the raids their own evaluation fears
        let odds_opp = RaidOdds::sample(&s0.root, opp, &seat::unseen(&s0.root, opp), spec.samples, &mut self.rng);
        let ctx_opp = Ctx { me: opp, w: &spec.weights, odds: &odds_opp, max_width: spec.width, greedy_eval: spec.greedy_eval, keep: 0, per: 0 };
        let chance = |st: &State, e: f32| -> f32 {
            if spec.decisive > 0.0 {
                return e.clamp(-spec.decisive, spec.decisive);
            }
            let tempo = if st.current == me { spec.tempo } else { -spec.tempo };
            1.0 / (1.0 + (-(e + tempo) / spec.scale).exp())
        };
        // a game decided, as a score: won, lost, drawn
        let decided = |winner: Option<Player>| -> f32 {
            let (won, lost) = if spec.decisive > 0.0 { (spec.decisive, -spec.decisive) } else { (1.0, 0.0) };
            match winner {
                Some(p) if p == me => won,
                Some(_) => lost,
                None => (won + lost) / 2.0,
            }
        };
        for h in 0..worlds {
            let mut w = s0.root.clone();
            if h > 0 {
                seat::redeal(&mut w, me, seen, &mut self.rng, spec.spread);
            }
            for c in cands.iter_mut() {
                let mut st = w.clone();
                let mut legal = true;
                for a in &c.line {
                    if rules::apply_action(&mut st, a, false).is_err() {
                        legal = false;
                        break;
                    }
                    positions += 1;
                }
                if !legal {
                    continue;
                }
                let p = if let Some(r) = st.result {
                    decided(r.winner)
                } else if st.player_to_act() != opp {
                    chance(&st, ctx.eval(&st)) // my turn did not end (a choice still waiting): scored as it stands
                } else {
                    // their win, if they have one; else the turn their own search likes best
                    let each = (limit.saturating_sub(positions) / to_come.max(1)).max(1);
                    let look = win_search(&st, opp, (each / 8).max(1));
                    positions += look.positions;
                    if look.line.is_some() {
                        decided(Some(opp))
                    } else {
                        let mut reply = WorldSearch::new(st.clone(), opp);
                        reply.run(&ctx_opp, each.saturating_sub(look.positions).max(1));
                        positions += reply.positions;
                        self.stats.replies += 1;
                        for a in &reply.line {
                            if rules::apply_action(&mut st, a, false).is_err() {
                                break;
                            }
                            positions += 1;
                        }
                        if st.result.is_none() && may_pass(&st, opp) {
                            let _ = rules::apply_action(&mut st, &Action::Pass, false); // a reply the budget cut short still ends
                            positions += 1;
                        }
                        match st.result {
                            Some(r) => decided(r.winner),
                            None => chance(&st, ctx.eval(&st)),
                        }
                    }
                };
                c.sum += p;
                c.n += 1;
                to_come = to_come.saturating_sub(1);
            }
        }
        let mut best = 0usize;
        for (i, c) in cands.iter().enumerate() {
            let mean = |c: &Cand| if c.n > 0 { c.sum / c.n as f32 } else { NEG };
            if mean(c) > mean(&cands[best]) {
                best = i;
            }
        }
        if first {
            self.stats.reply_turns += 1;
            self.stats.repicks += (best != 0) as u64;
        }
        self.count(positions);
        let Some(pick) = cands.get(best) else { return fallback(&s0) };
        let action = pick.line.first().copied().unwrap_or(Action::Pass);
        if !pick.hidden {
            self.plan = Self::keyed(&s0.root, me, &pick.line);
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
                self.look = true;
            }
            let newest = real.hands[me as usize].iter().map(|u| u.iid).max().unwrap_or(-1);
            if newest > self.newest {
                self.look = true; // a card came into my hand
            }
            self.newest = newest;
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
        let mut s = format!("turn:budget={},worlds={},width={},samples={},win={},eval={}", self.spec.budget, self.spec.worlds, self.spec.width, self.spec.samples,
                            self.spec.win.unwrap_or(self.spec.budget / 16), if self.spec.greedy_eval { "greedy" } else { "food" });
        if self.spec.reply > 0 {
            s.push_str(&format!(",reply={},per={},hands={},own={},spread={},scale={},tempo={}", self.spec.reply, self.spec.per, self.spec.hands, self.spec.own, self.spec.spread as u8,
                                self.spec.scale, self.spec.tempo));
        }
        s
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
