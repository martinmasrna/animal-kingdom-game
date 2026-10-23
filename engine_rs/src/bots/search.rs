//! The determinized own-turn search (bots/turn_search.py) with TurnBot's and RefereeBot's hooks (bots/turn_bot.py,
//! bots/referee_bot.py), and the searched mulligan (bots/mulligan.py). Every ordering, tie-break and RNG draw follows
//! the Python so the same seed plays the same move.

use std::time::Instant;

use crate::actions::{Action, Target};
use crate::bots::features::{capped, enabled_roar_count, opponent_lethal_next_turn, reframed_at_my_turn, roar_fizzled, Evaluator, Weights};
use crate::bots::greedy::GreedyBot;
use crate::bots::world::determinize;
use crate::data::*;
use crate::effects;
use crate::rng::PyRandom;
use crate::rules;
use crate::state::{State, Unit};
use crate::strength::card_strength;
use crate::value::{m_flag, m_get_s, Map, Value};

pub const DECISIVE: f64 = 1e9;
const DET_SEED_SALT: i64 = 0x9E3779B9;
const MAX_DEPTH: usize = 40;
const LOSS_TIEBREAK: f64 = 1e6;
const SEARCH_WORLDS: usize = 24;
const SEARCH_TURNS: i32 = 2;
const SEARCH_MARGIN: f64 = 0.5;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Kind {
    Turn,
    Referee,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Mulligan {
    Keep,
    Search,
}

type Branch = (State, f64);

#[derive(Clone, Default, Debug)]
pub struct Stats {
    pub root_candidates: usize,
    pub screened_candidates: usize,
    pub reply_world_rollouts: usize,
    pub plan_reused: usize,
    pub budget_fallbacks: usize,
    pub search_nodes: usize,
    pub lookahead_cut: usize,
    pub chased_roots: usize,
    pub deepened_roots: usize,
    pub lookahead_lines: usize,
    pub decision_gap: f64,
}

#[derive(Clone)]
pub struct Searcher {
    pub kind: Kind,
    pub weights: Weights,
    pub evaluator: Evaluator,
    pub rng: PyRandom,
    pub det_rng: PyRandom,
    pub determinizations: usize,
    pub beam_width: usize,
    pub deck_reveal_choice_width: usize,
    pub max_search_nodes: Option<usize>,
    pub policy: GreedyBot,
    pub quiesce: bool,
    pub mulligan: Mulligan,
    pub decisive: f64,
    // RefereeBot
    pub staged: bool,
    pub root_width: usize,
    pub reply_width: usize,
    pub depth: i32,
    pub next_width: usize,
    pub deepen_top: usize,
    pub deepen_roots: usize,
    pub time_budget: f64,
    pub den_sense: bool,
    pub reply_turns: usize,
    pub deepen_chase: bool,
    // run state
    search_nodes: usize,
    deepening: bool,
    screening: bool,
    move_started: Instant,
    pub stats: Stats,
    candidate_plans: Vec<(Action, Vec<(String, Action)>)>,
    active_plan: Option<Vec<(String, Action)>>,
    continuation_plan: Vec<(String, Action)>,
    pub last_root_scores: Vec<(Action, f64)>,
}

fn plan_set(plan: &mut Vec<(String, Action)>, key: String, action: Action) {
    if let Some(e) = plan.iter_mut().find(|(k, _)| *k == key) {
        e.1 = action;
    } else {
        plan.push((key, action));
    }
}

impl Searcher {
    #[allow(clippy::too_many_arguments)]
    pub fn new(kind: Kind, weights: Weights, evaluator: Evaluator, seed: i64, determinizations: usize, beam_width: usize, deck_reveal_choice_width: usize, max_search_nodes: Option<usize>, quiesce: bool, mulligan: Mulligan, decisive: f64) -> Searcher {
        Searcher {
            kind,
            policy: GreedyBot::new(weights.clone(), evaluator.clone(), seed + 1, 1, 8, 0.0, false),
            weights,
            evaluator,
            rng: PyRandom::seeded(seed),
            det_rng: PyRandom::seeded(seed + DET_SEED_SALT),
            determinizations,
            beam_width,
            deck_reveal_choice_width,
            max_search_nodes,
            quiesce,
            mulligan,
            decisive,
            staged: true,
            root_width: 5,
            reply_width: 4,
            depth: 0,
            next_width: 3,
            deepen_top: 4,
            deepen_roots: 3,
            time_budget: 0.0,
            den_sense: false,
            reply_turns: 0,
            deepen_chase: false,
            search_nodes: 0,
            deepening: false,
            screening: false,
            move_started: Instant::now(),
            stats: Stats::default(),
            candidate_plans: Vec::new(),
            active_plan: None,
            continuation_plan: Vec::new(),
            last_root_scores: Vec::new(),
        }
    }

    fn is_referee(&self) -> bool {
        self.kind == Kind::Referee
    }

    fn over_budget(&self) -> bool {
        self.time_budget != 0.0 && self.move_started.elapsed().as_secs_f64() > self.time_budget
    }

    // ------------------------------------------------------------------ evaluation

    fn eval(&self, st: &State, me: Player) -> f64 {
        self.evaluator.value(st, me, &self.weights)
    }

    pub fn clamped_eval(&self, st: &State, me: Player) -> f64 {
        self.eval(st, me).max(-self.decisive).min(self.decisive)
    }

    fn planning_eval(&self, st: &mut State, me: Player) -> f64 {
        let score = self.clamped_eval(st, me);
        if st.result.is_some() || st.current == me {
            return score;
        }
        if matches!(self.evaluator, Evaluator::Hand) && self.weights.effect_readiness == 0.0 {
            return score;
        }
        if !matches!(self.evaluator, Evaluator::Hand) {
            return reframed_at_my_turn(st, me, |s| self.clamped_eval(s, me));
        }
        let readiness = capped(&self.weights, reframed_at_my_turn(st, me, |s| enabled_roar_count(s, me)));
        (score + self.weights.effect_readiness * readiness as f64).max(-self.decisive).min(self.decisive)
    }

    fn settled(&mut self, st: &State, me: Player) -> State {
        let mut s = st.clone();
        if !self.quiesce {
            return s;
        }
        for _ in 0..MAX_DEPTH {
            if s.pending.is_none() || s.result.is_some() || s.player_to_act() != me {
                break;
            }
            let legal = rules::legal_actions(&s);
            if legal.is_empty() {
                break;
            }
            let a = self.policy.choose(&s, me, &legal);
            let _ = rules::apply_action(&mut s, &a, false);
        }
        s
    }

    fn pruning_eval(&mut self, st: &State, me: Player) -> f64 {
        let s = self.settled(st, me);
        self.clamped_eval(&s, me)
    }

    fn mean_planning_score(&self, branches: &mut [Branch], me: Player) -> f64 {
        let mut total = 0.0;
        for (s, penalty) in branches.iter_mut() {
            total += self.planning_eval(s, me) - *penalty;
        }
        total / branches.len() as f64
    }

    // ------------------------------------------------------------------ choose

    pub fn choose(&mut self, st: &State, me: Player, legal: &[Action]) -> Action {
        self.move_started = Instant::now();
        self.stats = Stats { root_candidates: legal.len(), screened_candidates: legal.len(), decision_gap: f64::INFINITY, ..Default::default() };
        if let Some(keep) = self.keep_hand(st, me, legal) {
            return keep;
        }
        self.search_nodes = 0;
        if self.is_referee() && self.staged {
            if let Some(c) = legal.iter().find(|a| matches!(a, Action::Place { target: Target::Hq(_), .. } | Action::Roam { target: Target::Hq(_), .. })) {
                self.continuation_plan.clear();
                self.stats.screened_candidates = 1;
                return c.clone();
            }
            if !self.continuation_plan.is_empty() {
                let key = observation_key(st, me);
                let planned = self.continuation_plan.iter().find(|(k, _)| *k == key).map(|(_, a)| a.clone());
                if let Some(p) = planned {
                    if legal.contains(&p) {
                        self.continuation_plan.retain(|(k, _)| *k != key);
                        self.stats.screened_candidates = 1;
                        self.stats.plan_reused = 1;
                        return p;
                    }
                }
                self.continuation_plan.clear();
            }
            self.candidate_plans.clear();
            self.active_plan = None;
        }
        if legal.len() == 1 {
            return legal[0].clone();
        }
        let worlds: Vec<State> = (0..self.determinizations).map(|_| determinize(st, me, &mut self.det_rng)).collect();
        let legal = self.safe_actions(&worlds[0], legal, me);
        let candidates = self.beam(&worlds[0], &legal, me);
        let candidates = self.select_root_candidates(&worlds, candidates, st, me);
        let complete = st.current == me;
        let mut root_scores: Vec<(Action, f64)> = Vec::new();
        for action in &candidates {
            self.begin_root_candidate();
            let mut branches = self.branches_after_action(&worlds, action, me, complete);
            let score = self.score_final_line(&mut branches, me);
            self.end_root_candidate(action);
            root_scores.push((action.clone(), score));
        }
        let root_scores = self.rescore_roots(&worlds, root_scores, st, me);
        let mut best_score = f64::NEG_INFINITY;
        let mut best: Vec<Action> = Vec::new();
        for (action, score) in &root_scores {
            if *score > best_score {
                best_score = *score;
                best = vec![action.clone()];
            } else if *score == best_score {
                best.push(action.clone());
            }
        }
        if self.is_referee() {
            let mut ranked: Vec<f64> = root_scores.iter().map(|(_, s)| *s).collect();
            ranked.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
            self.stats.decision_gap = if ranked.len() > 1 { ranked[0] - ranked[1] } else { f64::INFINITY };
        }
        self.last_root_scores = root_scores;
        let draws: Vec<&Action> = best.iter().filter(|a| matches!(a, Action::Draw)).collect();
        let chosen = if best.len() == 1 {
            best[0].clone()
        } else if let Some(d) = draws.first() {
            (*d).clone()
        } else {
            best[self.rng.choice_index(best.len())].clone()
        };
        self.record_chosen_root(&chosen);
        chosen
    }

    fn branches_after_action(&mut self, worlds: &[State], action: &Action, me: Player, complete_turn: bool) -> Vec<Branch> {
        let mut branches = Vec::with_capacity(worlds.len());
        for world in worlds {
            let mut nxt = world.clone();
            let _ = rules::apply_action(&mut nxt, action, false);
            let penalty = if roar_fizzled(world, &nxt, me, action) { self.weights.wasted_roar } else { 0.0 };
            branches.push((nxt, penalty));
        }
        if complete_turn {
            return self.complete_own_turn(branches, me, 0);
        }
        branches
    }

    fn partition_by_observation(&self, branches: Vec<Branch>, me: Player) -> (Vec<Branch>, Vec<(String, Vec<Branch>)>) {
        let mut completed = Vec::new();
        let mut groups: Vec<(String, Vec<Branch>)> = Vec::new();
        for (mut s, penalty) in branches {
            if let Some(r) = rules::is_terminal(&s) {
                s.result = Some(r);
                completed.push((s, penalty));
            } else if s.current != me {
                completed.push((s, penalty));
            } else {
                let key = observation_key(&s, me);
                match groups.iter_mut().find(|(k, _)| *k == key) {
                    Some(g) => g.1.push((s, penalty)),
                    None => groups.push((key, vec![(s, penalty)])),
                }
            }
        }
        (completed, groups)
    }

    // ------------------------------------------------------------- own-turn completion

    fn complete_own_turn(&mut self, branches: Vec<Branch>, me: Player, guard: usize) -> Vec<Branch> {
        if self.is_referee() {
            self.search_nodes += branches.len();
            self.stats.search_nodes = self.stats.search_nodes.max(self.search_nodes);
            if self.staged && self.max_search_nodes.map(|m| self.search_nodes > m).unwrap_or(false) {
                self.stats.budget_fallbacks += 1;
                return self.greedy_complete_turn(branches, me, guard);
            }
        } else if let Some(m) = self.max_search_nodes {
            self.search_nodes += branches.len();
            if self.search_nodes > m {
                return self.greedy_complete_turn(branches, me, guard);
            }
        }
        self.complete_own_turn_base(branches, me, guard)
    }

    fn complete_own_turn_base(&mut self, branches: Vec<Branch>, me: Player, guard: usize) -> Vec<Branch> {
        if branches.is_empty() || guard >= MAX_DEPTH {
            return branches;
        }
        let (mut completed, groups) = self.partition_by_observation(branches, me);
        for (key, group) in groups {
            let representative = group[0].0.clone();
            let actor = representative.player_to_act();
            let chosen_group: Vec<Branch>;
            if actor != me {
                chosen_group = self.resolve_opponent_subchoice(group, me, actor, guard);
            } else {
                let legal = self.safe_actions(&representative, &rules::legal_actions(&representative), me);
                let mut candidates = if self.is_collapsible_deck_reveal(&representative) {
                    self.greedy_topn(&representative, &legal, me, self.deck_reveal_choice_width)
                } else {
                    self.beam(&representative, &legal, me)
                };
                let compare = self.use_reply_comparison(&representative);
                if compare {
                    candidates = self.reply_candidates(&representative, candidates, me);
                }
                let mut best_score = f64::NEG_INFINITY;
                let mut best_action: Option<Action> = None;
                let mut chosen: Vec<Branch> = Vec::new();
                for action in &candidates {
                    let mut next_group = Vec::with_capacity(group.len());
                    for (s, penalty) in &group {
                        let mut nxt = s.clone();
                        let _ = rules::apply_action(&mut nxt, action, false);
                        let extra = if roar_fizzled(s, &nxt, me, action) { self.weights.wasted_roar } else { 0.0 };
                        next_group.push((nxt, penalty + extra));
                    }
                    let mut candidate_group = self.complete_own_turn(next_group, me, guard + 1);
                    let score = self.score_candidate_group(&mut candidate_group, me, compare);
                    if score > best_score {
                        best_score = score;
                        best_action = Some(action.clone());
                        chosen = candidate_group;
                    }
                }
                if let Some(a) = best_action {
                    self.record_planned_action(key, a);
                }
                chosen_group = chosen;
            }
            completed.extend(chosen_group);
        }
        completed
    }

    fn greedy_complete_turn(&mut self, branches: Vec<Branch>, me: Player, guard: usize) -> Vec<Branch> {
        if branches.is_empty() || guard >= MAX_DEPTH {
            return branches;
        }
        let (mut completed, groups) = self.partition_by_observation(branches, me);
        for (_, group) in groups {
            let representative = group[0].0.clone();
            let actor = representative.player_to_act();
            let mut advanced = Vec::with_capacity(group.len());
            if actor == me {
                let legal = self.safe_actions(&representative, &rules::legal_actions(&representative), me);
                let action = self.policy.choose(&representative, me, &legal);
                for (s, penalty) in &group {
                    let mut nxt = s.clone();
                    let _ = rules::apply_action(&mut nxt, &action, false);
                    let extra = if roar_fizzled(s, &nxt, me, &action) { self.weights.wasted_roar } else { 0.0 };
                    advanced.push((nxt, penalty + extra));
                }
            } else {
                for (mut s, penalty) in group {
                    let legal = rules::legal_actions(&s);
                    let action = self.policy.choose(&s, actor, &legal);
                    let _ = rules::apply_action(&mut s, &action, false);
                    advanced.push((s, penalty));
                }
            }
            completed.extend(self.greedy_complete_turn(advanced, me, guard + 1));
        }
        completed
    }

    // --------------------------------------------------------------- hooks

    fn select_root_candidates(&mut self, worlds: &[State], candidates: Vec<Action>, st: &State, me: Player) -> Vec<Action> {
        if !self.is_referee() {
            return candidates;
        }
        self.stats.root_candidates = candidates.len();
        if !self.staged || self.root_width == 0 || candidates.len() <= self.root_width {
            self.stats.screened_candidates = candidates.len();
            return candidates;
        }
        self.screening = true;
        let mut scored: Vec<(f64, i64, usize)> = Vec::new();
        for (index, action) in candidates.iter().enumerate() {
            let branches = self.branches_after_action(worlds, action, me, false);
            let mut settled: Vec<Branch> = branches.into_iter().map(|(s, p)| (self.settled(&s, me), p)).collect();
            let score = self.mean_planning_score(&mut settled, me);
            scored.push((score, -(index as i64), index));
        }
        self.screening = false;
        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal).then(b.1.cmp(&a.1)));
        let mut selected: Vec<usize> = scored.iter().take(self.root_width).map(|x| x.2).collect();
        if self.den_sense {
            for &cr in st.map().front(me) {
                let guards: Vec<usize> = candidates
                    .iter()
                    .enumerate()
                    .filter(|(_, a)| matches!(a, Action::Place { target: Target::Cr(c), .. } if *c == cr))
                    .map(|(i, _)| i)
                    .collect();
                if !guards.is_empty() {
                    let mut best = guards[0];
                    let mut best_s = i32::MIN;
                    for &i in &guards {
                        if let Action::Place { card, .. } = &candidates[i] {
                            let s = card_strength(st, *card, me);
                            if s > best_s {
                                best_s = s;
                                best = i;
                            }
                        }
                    }
                    if !selected.contains(&best) {
                        selected.push(best);
                    }
                }
            }
        }
        for (i, a) in candidates.iter().enumerate() {
            if matches!(a, Action::Draw) && !selected.contains(&i) {
                selected.push(i);
            }
        }
        let narrowed: Vec<Action> = candidates.iter().enumerate().filter(|(i, _)| selected.contains(i)).map(|(_, a)| a.clone()).collect();
        self.stats.screened_candidates = narrowed.len();
        narrowed
    }

    fn begin_root_candidate(&mut self) {
        if self.is_referee() {
            if self.staged {
                self.search_nodes = 0;
                self.active_plan = Some(Vec::new());
            }
        } else {
            self.search_nodes = 0;
        }
    }

    fn end_root_candidate(&mut self, action: &Action) {
        if self.is_referee() && self.staged {
            if let Some(plan) = self.active_plan.take() {
                match self.candidate_plans.iter_mut().find(|(a, _)| a == action) {
                    Some(e) => e.1 = plan,
                    None => self.candidate_plans.push((action.clone(), plan)),
                }
            }
        }
    }

    fn record_planned_action(&mut self, key: String, action: Action) {
        if self.is_referee() && self.staged && !self.screening {
            if let Some(plan) = self.active_plan.as_mut() {
                plan_set(plan, key, action);
            }
        }
    }

    fn record_chosen_root(&mut self, action: &Action) {
        if self.is_referee() && self.staged {
            self.continuation_plan = self.candidate_plans.iter().find(|(a, _)| a == action).map(|(_, p)| p.clone()).unwrap_or_default();
        }
    }

    fn score_final_line(&mut self, branches: &mut Vec<Branch>, me: Player) -> f64 {
        if self.is_referee() {
            self.mean_reply_score(branches, me)
        } else {
            self.mean_planning_score(branches, me)
        }
    }

    fn use_reply_comparison(&self, representative: &State) -> bool {
        self.is_referee() && !self.screening && representative.pending.is_none() && representative.actions_taken_this_turn >= representative.cfg().actions_per_turn - 1
    }

    fn score_candidate_group(&mut self, group: &mut Vec<Branch>, me: Player, compare: bool) -> f64 {
        if self.is_referee() && compare && !self.screening {
            let mut trial: Vec<Branch> = group.iter().map(|(s, p)| (s.clone(), *p)).collect();
            let scores = self.reply_scores(&mut trial, me);
            let mut total = 0.0;
            for s in &scores {
                total += s;
            }
            return total / scores.len() as f64;
        }
        self.mean_planning_score(group, me)
    }

    fn resolve_opponent_subchoice(&mut self, group: Vec<Branch>, me: Player, actor: Player, guard: usize) -> Vec<Branch> {
        if self.is_referee() {
            let mut advanced = Vec::with_capacity(group.len());
            for (mut s, penalty) in group {
                let legal = rules::legal_actions(&s);
                let action = self.policy.choose(&s, actor, &legal);
                let _ = rules::apply_action(&mut s, &action, false);
                advanced.push((s, penalty));
            }
            return self.complete_own_turn(advanced, me, guard + 1);
        }
        let representative = group[0].0.clone();
        let legal = rules::legal_actions(&representative);
        if legal.is_empty() {
            return self.complete_own_turn(group, me, guard + 1);
        }
        let mut worst = f64::INFINITY;
        let mut chosen: Vec<Branch> = Vec::new();
        for action in &legal {
            let mut next_group = Vec::with_capacity(group.len());
            for (s, penalty) in &group {
                let mut nxt = s.clone();
                let _ = rules::apply_action(&mut nxt, action, false);
                next_group.push((nxt, *penalty));
            }
            let mut candidate_group = self.complete_own_turn(next_group, me, guard + 1);
            let score = self.mean_planning_score(&mut candidate_group, me);
            if score < worst {
                worst = score;
                chosen = candidate_group;
            }
        }
        chosen
    }

    // ------------------------------------------------------------------ pruning

    fn beam(&mut self, world: &State, legal: &[Action], me: Player) -> Vec<Action> {
        if self.beam_width == 0 || legal.len() <= self.beam_width {
            return legal.to_vec();
        }
        let mut scored: Vec<(f64, usize)> = Vec::new();
        for (i, action) in legal.iter().enumerate() {
            let mut nxt = world.clone();
            let _ = rules::apply_action(&mut nxt, action, false);
            scored.push((self.pruning_eval(&nxt, me), i));
        }
        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal).then(a.1.cmp(&b.1)));
        let score_of = |i: usize| scored.iter().find(|(_, j)| *j == i).map(|(s, _)| *s).unwrap_or(f64::NEG_INFINITY);
        let mut reserved: Vec<usize> = Vec::new();
        for (i, a) in legal.iter().enumerate() {
            if matches!(a, Action::Draw) || matches!(a, Action::Place { target: Target::Hq(_), .. } | Action::Roam { target: Target::Hq(_), .. }) {
                reserved.push(i);
            }
        }
        let mut by_card: Vec<(CardId, Vec<usize>)> = Vec::new();
        for (i, a) in legal.iter().enumerate() {
            if let Action::Place { card, target: Target::Cr(_), .. } = a {
                match by_card.iter_mut().find(|(c, _)| c == card) {
                    Some(e) => e.1.push(i),
                    None => by_card.push((*card, vec![i])),
                }
            }
        }
        let opponent = other(me);
        let occ = world.connected_occupied(me);
        let cr_of = |i: usize| match &legal[i] {
            Action::Place { target: Target::Cr(c), .. } => *c,
            _ => 0,
        };
        for (card, idxs) in &by_card {
            let connected: Vec<usize> = idxs.iter().copied().filter(|&i| world.is_connected(me, cr_of(i), occ)).collect();
            let home_front: Vec<usize> = idxs.iter().copied().filter(|&i| world.map().in_front(me, cr_of(i))).collect();
            let covers: Vec<usize> = idxs.iter().copied().filter(|&i| world.owner_of(cr_of(i)) == Some(opponent)).collect();
            let mut live: Vec<usize> = Vec::new();
            if world.card(*card).has_roar {
                for &i in idxs {
                    let mut nxt = world.clone();
                    let _ = rules::apply_action(&mut nxt, &legal[i], false);
                    if !roar_fizzled(world, &nxt, me, &legal[i]) {
                        live.push(i);
                    }
                }
            }
            for group in [connected, home_front, covers, live] {
                if group.is_empty() {
                    continue;
                }
                let mut best = group[0];
                for &i in &group[1..] {
                    if score_of(i) > score_of(best) {
                        best = i;
                    }
                }
                if !reserved.contains(&best) {
                    reserved.push(best);
                }
            }
        }
        let mut kept: Vec<usize> = reserved.clone();
        let cap = self.beam_width.max(reserved.len());
        for &(_, i) in &scored {
            if kept.len() >= self.beam_width && !reserved.contains(&i) {
                continue;
            }
            if !kept.contains(&i) {
                kept.push(i);
            }
            if kept.len() >= cap {
                break;
            }
        }
        legal.iter().enumerate().filter(|(i, _)| kept.contains(i)).map(|(_, a)| a.clone()).collect()
    }

    fn is_collapsible_deck_reveal(&self, world: &State) -> bool {
        self.deck_reveal_choice_width > 0 && world.pending.as_ref().map(|p| m_flag(p, "from_deck_reveal")).unwrap_or(false)
    }

    fn greedy_topn(&mut self, world: &State, legal: &[Action], me: Player, n: usize) -> Vec<Action> {
        if legal.len() <= n {
            return legal.to_vec();
        }
        let mut scored: Vec<(f64, usize)> = Vec::new();
        for (i, action) in legal.iter().enumerate() {
            let mut nxt = world.clone();
            let _ = rules::apply_action(&mut nxt, action, false);
            scored.push((self.pruning_eval(&nxt, me), i));
        }
        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal).then(a.1.cmp(&b.1)));
        scored.iter().take(n).map(|(_, i)| legal[*i].clone()).collect()
    }

    fn safe_actions(&self, world: &State, legal: &[Action], me: Player) -> Vec<Action> {
        let opponent = other(me);
        let mut safe = Vec::new();
        for action in legal {
            let mut nxt = world.clone();
            let _ = rules::apply_action(&mut nxt, action, false);
            if nxt.result.is_some() || !opponent_lethal_next_turn(&nxt, opponent) {
                safe.push(action.clone());
            }
        }
        if safe.is_empty() {
            legal.to_vec()
        } else {
            safe
        }
    }

    // -------------------------------------------------------------- reply rollouts (RefereeBot)

    fn reply_candidates(&mut self, st: &State, candidates: Vec<Action>, me: Player) -> Vec<Action> {
        let limit = if self.staged { self.reply_width } else { 4 };
        if limit == 0 || candidates.len() <= limit {
            return candidates;
        }
        let mut scored: Vec<(f64, usize)> = Vec::new();
        let mut live: Vec<(f64, usize)> = Vec::new();
        for (index, action) in candidates.iter().enumerate() {
            let mut nxt = st.clone();
            let _ = rules::apply_action(&mut nxt, action, false);
            let mut settled = self.settled(&nxt, me);
            let score = self.planning_eval(&mut settled, me);
            scored.push((score, index));
            if let Action::Place { card, .. } = action {
                if st.card(*card).has_roar && !roar_fizzled(st, &nxt, me, action) {
                    live.push((score, index));
                }
            }
        }
        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal).then(a.1.cmp(&b.1)));
        let mut selected: Vec<usize> = vec![scored[0].1];
        for (i, a) in candidates.iter().enumerate() {
            if matches!(a, Action::Draw) && !selected.contains(&i) {
                selected.push(i);
            }
        }
        for (i, a) in candidates.iter().enumerate() {
            if matches!(a, Action::Place { target: Target::Hq(_), .. } | Action::Roam { target: Target::Hq(_), .. }) && !selected.contains(&i) {
                selected.push(i);
            }
        }
        let home = scored.iter().find(|(_, i)| matches!(&candidates[*i], Action::Place { target: Target::Cr(c), .. } if st.map().in_front(me, *c)));
        if let Some((_, i)) = home {
            if !selected.contains(i) {
                selected.push(*i);
            }
        }
        if !live.is_empty() {
            // max(live): the highest score, ties by the larger -index in Python (the smaller index)
            let mut best = live[0];
            for &(s, i) in &live[1..] {
                if s > best.0 || (s == best.0 && i < best.1) {
                    best = (s, i);
                }
            }
            if !selected.contains(&best.1) {
                selected.push(best.1);
            }
        }
        for &(_, i) in &scored {
            if selected.len() >= limit {
                break;
            }
            if !selected.contains(&i) {
                selected.push(i);
            }
        }
        candidates.iter().enumerate().filter(|(i, _)| selected.contains(i)).map(|(_, a)| a.clone()).collect()
    }

    fn reply_scores(&mut self, branches: &mut Vec<Branch>, me: Player) -> Vec<f64> {
        let mut scores = Vec::with_capacity(branches.len());
        let mut befores = Vec::with_capacity(branches.len());
        for (s, penalty) in branches.iter_mut() {
            let tiebreak = if self.decisive >= DECISIVE { LOSS_TIEBREAK } else { self.decisive / 10.0 };
            let before = self.planning_eval(s, me).max(-tiebreak).min(tiebreak);
            let threat = self.advance(s, me);
            let mut score = self.clamped_eval(s, me);
            if score == -self.decisive {
                score += before;
            }
            if threat != 0.0 {
                score = threat * (-self.decisive + before) + (1.0 - threat) * score;
            }
            scores.push(score - *penalty);
            befores.push(before);
            self.stats.reply_world_rollouts += 1;
        }
        if self.depth > 0 && self.deepening && !branches.is_empty() {
            let mut order: Vec<usize> = (0..scores.len()).collect();
            order.sort_by(|&a, &b| scores[b].partial_cmp(&scores[a]).unwrap_or(std::cmp::Ordering::Equal).then(a.cmp(&b)));
            for &i in order.iter().take(self.deepen_top) {
                if self.over_budget() {
                    self.stats.lookahead_cut += 1;
                    break;
                }
                if branches[i].0.result.is_some() {
                    continue;
                }
                let state = branches[i].0.clone();
                let mut score = self.leaf_score(&state, me, self.depth);
                if score == -self.decisive {
                    score += befores[i];
                }
                scores[i] = score - branches[i].1;
            }
        }
        scores
    }

    fn mean_reply_score(&mut self, branches: &mut Vec<Branch>, me: Player) -> f64 {
        let scores = self.reply_scores(branches, me);
        let mut total = 0.0;
        for s in &scores {
            total += s;
        }
        total / scores.len() as f64
    }

    fn rescore_roots(&mut self, worlds: &[State], root_scores: Vec<(Action, f64)>, st: &State, me: Player) -> Vec<(Action, f64)> {
        if !self.is_referee() || self.depth == 0 || root_scores.len() < 2 {
            return root_scores;
        }
        let mut ordered = root_scores.clone();
        // ties keep the candidate order; the key is rounded to 1e-9 as in Python, so float noise cannot flip it
        let key = |x: f64| (x * 1e9).round();
        ordered.sort_by(|a, b| key(b.1).partial_cmp(&key(a.1)).unwrap_or(std::cmp::Ordering::Equal));
        let mut deep: Vec<(Action, f64)> = Vec::new();
        for (k, (action, shallow)) in ordered.iter().enumerate() {
            if k >= self.deepen_roots {
                let best_deep = deep.iter().map(|(_, s)| *s).fold(f64::NEG_INFINITY, f64::max);
                if !self.deepen_chase || deep.is_empty() || best_deep >= *shallow {
                    break;
                }
                self.stats.chased_roots += 1;
            }
            if self.over_budget() {
                self.stats.lookahead_cut = 1;
                return root_scores;
            }
            self.begin_root_candidate();
            let mut branches = self.branches_after_action(worlds, action, me, st.current == me);
            self.deepening = true;
            let score = self.mean_reply_score(&mut branches, me);
            self.deepening = false;
            self.end_root_candidate(action);
            deep.push((action.clone(), score));
        }
        self.stats.deepened_roots = deep.len();
        deep
    }

    fn leaf_score(&mut self, st: &State, me: Player, depth: i32) -> f64 {
        if depth <= 0 || st.result.is_some() || st.pending.is_some() || st.player_to_act() != me {
            return self.clamped_eval(st, me);
        }
        let legal = rules::legal_actions(st);
        if legal.is_empty() {
            return self.clamped_eval(st, me);
        }
        let mut best: Option<f64> = None;
        for action in self.greedy_topn(st, &legal, me, self.next_width) {
            let mut nxt = st.clone();
            let _ = rules::apply_action(&mut nxt, &action, false);
            self.play_turn(&mut nxt, me);
            let threat = self.advance(&mut nxt, me);
            self.stats.lookahead_lines += 1;
            let mut value = self.leaf_score(&nxt, me, depth - 1);
            if threat != 0.0 {
                value = threat * -self.decisive + (1.0 - threat) * value;
            }
            best = Some(match best {
                None => value,
                Some(b) => b.max(value),
            });
        }
        let mut b = best.unwrap_or(0.0);
        if b.abs() >= self.decisive / 2.0 {
            b /= 2.0;
        }
        b
    }

    fn play_turn(&mut self, st: &mut State, me: Player) {
        for _ in 0..40 {
            if let Some(r) = rules::is_terminal(st) {
                st.result = Some(r);
                return;
            }
            if st.player_to_act() != me {
                return;
            }
            let legal = rules::legal_actions(st);
            if legal.is_empty() {
                return;
            }
            let a = self.policy.choose(st, me, &legal);
            let _ = rules::apply_action(st, &a, false);
        }
    }

    fn advance(&mut self, st: &mut State, me: Player) -> f64 {
        let mut threat = 0.0;
        for _ in 0..40 {
            if let Some(r) = rules::is_terminal(st) {
                st.result = Some(r);
                return threat;
            }
            if st.player_to_act() == me && st.pending.is_none() {
                return threat;
            }
            let actor = st.player_to_act();
            let legal = rules::legal_actions(st);
            if self.den_sense && actor != me && st.pending.is_none() && st.actions_taken_this_turn == 0 && threat == 0.0 {
                threat = self.den_threat(st, actor, me);
            }
            if self.reply_turns > 0 && (self.deepening || self.depth == 0) && actor != me && st.pending.is_none() && st.actions_taken_this_turn == 0 {
                if let Some(opening) = self.reply_opening(st, actor, &legal) {
                    let _ = rules::apply_action(st, &opening, false);
                    continue;
                }
            }
            let a = self.policy.choose(st, actor, &legal);
            let _ = rules::apply_action(st, &a, false);
        }
        threat
    }

    fn den_threat(&self, st: &State, opp: Player, me: Player) -> f64 {
        let gm = st.map();
        let front = gm.front(me);
        let occ = st.connected_occupied(opp);
        let hand = st.hands[opp as usize].len();
        let deck = st.decks[opp as usize].len();
        if front.iter().any(|&cr| occ & (1 << cr) != 0) && (hand > 0 || (deck > 0 && st.cfg().actions_per_turn >= 2)) {
            return 1.0;
        }
        if hand < 2 || st.cfg().actions_per_turn < 2 {
            return 0.0;
        }
        let reach: Vec<Cr> = front.iter().copied().filter(|&cr| gm.neighbors(cr).iter().any(|&nb| occ & (1 << nb) != 0)).collect();
        if reach.is_empty() {
            return 0.0;
        }
        // Counter over the unseen pool, in first-seen order
        let unseen = crate::bots::features::opponent_unseen(st, opp);
        let mut counts: Vec<(CardId, u64)> = Vec::new();
        for c in &unseen {
            match counts.iter_mut().find(|(x, _)| x == c) {
                Some(e) => e.1 += 1,
                None => counts.push((*c, 1)),
            }
        }
        let total: u64 = counts.iter().map(|(_, n)| n).sum();
        if total < hand as u64 {
            return 0.0;
        }
        let filler = counts.iter().map(|(c, _)| *c).find(|c| !st.card(*c).has_kw(K_APEX));
        let mut enabling: u64 = 0;
        for &(cid, count) in &counts {
            let mut probe = st.clone();
            probe.hands[opp as usize] = smallvec::smallvec![Unit::new(cid, opp, 900001), Unit::new(filler.unwrap_or(cid), opp, 900002)];
            for a in rules::legal_actions(&probe) {
                if let Action::Place { target: Target::Cr(c), .. } = &a {
                    if reach.contains(c) {
                        let mut nxt = probe.clone();
                        let _ = rules::apply_action(&mut nxt, &a, false);
                        if nxt.pending.is_none()
                            && nxt.player_to_act() == opp
                            && rules::is_terminal(&nxt).is_none()
                            && rules::legal_actions(&nxt).iter().any(|b| matches!(b, Action::Place { target: Target::Hq(_), .. } | Action::Roam { target: Target::Hq(_), .. }))
                        {
                            enabling += count;
                            break;
                        }
                    }
                }
            }
        }
        if enabling == 0 {
            return 0.0;
        }
        1.0 - comb_f(total - enabling, hand as u64) / comb_f(total, hand as u64)
    }

    fn reply_opening(&mut self, st: &State, opp: Player, legal: &[Action]) -> Option<Action> {
        if legal.len() < 2 {
            return None;
        }
        let mut best: Option<Action> = None;
        let mut best_score: Option<f64> = None;
        for opening in self.greedy_topn(st, legal, opp, self.reply_turns) {
            let mut nxt = st.clone();
            let _ = rules::apply_action(&mut nxt, &opening, false);
            self.play_turn(&mut nxt, opp);
            let score = self.clamped_eval(&nxt, opp);
            if best_score.map(|b| score > b).unwrap_or(true) {
                best = Some(opening);
                best_score = Some(score);
            }
        }
        best
    }

    // ------------------------------------------------------------------ mulligan

    fn keep_hand(&mut self, st: &State, me: Player, legal: &[Action]) -> Option<Action> {
        let p = st.pending.as_ref()?;
        if m_get_s(p, "kind") != Some("mulligan") {
            return None;
        }
        if self.mulligan == Mulligan::Keep {
            return legal.iter().find(|a| a.is_skip()).cloned();
        }
        Some(self.search_mulligan(st, me, legal))
    }

    fn search_mulligan(&mut self, st: &State, me: Player, legal: &[Action]) -> Action {
        let keep = legal.iter().find(|a| a.is_skip()).cloned().unwrap_or_else(Action::skip);
        let options: Vec<i64> = st.hands[me as usize].iter().map(|u| u.iid).filter(|iid| legal.contains(&Action::Choice(Value::Int(*iid)))).collect();
        if options.is_empty() {
            return keep;
        }
        let base: Vec<State> = (0..SEARCH_WORLDS).map(|_| determinize(st, me, &mut self.det_rng)).collect();
        let mut score = |this: &mut Searcher, choice: Option<i64>| -> f64 {
            let mut total = 0.0;
            for b in &base {
                let mut world = b.clone();
                if let Some(iid) = choice {
                    let _ = rules::apply_action(&mut world, &Action::Choice(Value::Int(iid)), false);
                }
                let mut guard = 0;
                while world.pending.is_some() && world.effect_stack.last().map(|s| m_get_s(s, "op") == Some("mulligan")).unwrap_or(false) && guard < 12 {
                    let _ = rules::apply_action(&mut world, &Action::skip(), false);
                    guard += 1;
                }
                let target = world.turn_counter + 2 * SEARCH_TURNS;
                let mut steps = 0;
                while world.turn_counter < target && rules::is_terminal(&world).is_none() && steps < 80 {
                    let actor = world.player_to_act();
                    let lg = rules::legal_actions(&world);
                    if lg.is_empty() {
                        break;
                    }
                    let a = this.policy.choose(&world, actor, &lg);
                    let _ = rules::apply_action(&mut world, &a, false);
                    steps += 1;
                }
                if let Some(r) = rules::is_terminal(&world) {
                    world.result = Some(r);
                }
                total += this.clamped_eval(&world, me).max(-DECISIVE).min(DECISIVE);
            }
            total / SEARCH_WORLDS as f64
        };
        let kept = score(self, None);
        let mut best_score = kept;
        let mut best: Option<i64> = None;
        for iid in options {
            let s = score(self, Some(iid));
            if s > best_score {
                best_score = s;
                best = Some(iid);
            }
        }
        match best {
            Some(iid) if best_score >= kept + SEARCH_MARGIN => Action::Choice(Value::Int(iid)),
            _ => keep,
        }
    }
}

fn comb_f(n: u64, k: u64) -> f64 {
    if k > n {
        return 0.0;
    }
    let k = k.min(n - k);
    let mut r: u128 = 1;
    for i in 0..k {
        r = r * (n - i) as u128 / (i + 1) as u128;
    }
    r as f64
}

// ------------------------------------------------------------------ observation key

fn canon(v: &Value, out: &mut String) {
    match v {
        Value::Null => out.push_str("N"),
        Value::Bool(b) => out.push_str(if *b { "T" } else { "F" }),
        Value::Int(i) => {
            out.push_str(&i.to_string());
        }
        Value::Str(s) => {
            out.push('"');
            out.push_str(s);
            out.push('"');
        }
        Value::List(l) => {
            out.push('[');
            for x in l {
                canon(x, out);
                out.push(',');
            }
            out.push(']');
        }
        Value::Map(m) => {
            let mut keys: Vec<&'static str> = m.keys().collect();
            keys.sort();
            out.push('{');
            for k in keys {
                out.push_str(k);
                out.push(':');
                canon(&m[k], out);
                out.push(',');
            }
            out.push('}');
        }
    }
}

/// The public and own-visible state, canonically (turn_search._observation_key).
pub fn observation_key(st: &State, me: Player) -> String {
    let opp = other(me);
    let mut out = String::with_capacity(512);
    out.push_str(player_name(st.current));
    out.push('|');
    out.push_str(player_name(st.player_to_act()));
    out.push('|');
    out.push_str(&format!("{}|{}|{}|", st.turn_counter, st.actions_taken_this_turn, st.units_placed_this_turn));
    for cr in st.sorted_occupied() {
        out.push_str(st.crname(cr));
        out.push(':');
        for u in st.stack(cr) {
            out.push_str(&format!("{}/{}/{}/{}/{};", st.cname(u.card), player_name(u.owner), u.strength_counter, u.placed_on_turn, u.locked_until_turn));
        }
        out.push('|');
    }
    out.push('H');
    for u in &st.hands[me as usize] {
        out.push_str(&format!("{}/{}/{};", st.cname(u.card), u.strength_counter, u.locked_until_turn));
    }
    out.push_str(&format!("|{}|{}|{}|", st.hands[opp as usize].len(), st.decks[me as usize].len(), st.decks[opp as usize].len()));
    for c in &st.remove_pile {
        out.push_str(st.cname(*c));
        out.push(',');
    }
    out.push_str(&format!("|{}|{}|", st.food[0], st.food[1]));
    match &st.pending {
        Some(p) => canon(&Value::Map(p.clone()), &mut out),
        None => out.push('N'),
    }
    out.push('|');
    canon(&Value::List(st.effect_stack.iter().map(|m| Value::Map(m.clone())).collect()), &mut out);
    out.push('|');
    canon(&Value::List(st.scheduled.iter().map(|m| Value::Map(m.clone())).collect()), &mut out);
    out.push('|');
    for p in 0..2 {
        let mut items: Vec<(String, i32)> = st.card_strength_counters[p].iter().map(|(c, n)| (st.cname(*c).to_string(), *n)).collect();
        items.sort();
        for (c, n) in items {
            out.push_str(&format!("{c}={n},"));
        }
        out.push(';');
    }
    out.push('|');
    st.turn_flags.canon_into(st, &mut out);
    out.push('|');
    match &st.result {
        Some(r) => out.push_str(&format!("{:?}/{}", r.winner.map(player_name), r.reason)),
        None => out.push('N'),
    }
    out
}

pub fn effects_unused() {
    let _ = effects::pn;
    let _: Option<Map> = None;
}
