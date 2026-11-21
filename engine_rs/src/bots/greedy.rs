//! The greedy bot Practice plays (`animal_kingdom/bot.py`), here as the benchmark's fixed baseline: for each decision it tries
//! every legal action on a copy of the position and keeps the one whose position it scores best, ties at random. It
//! keeps its opening hand, and it ends its turn only when nothing else is legal.

use crate::actions::Action;
use crate::bots::eval::greedy_evaluate;
use crate::bots::seat;
use crate::bots::{Bot, BotStats, Timer};
use crate::rng::PyRandom;
use crate::rules;
use crate::state::{Choice, State};

pub struct GreedyBot {
    rng: PyRandom,
    stats: BotStats,
    turn_seen: i32,
}

impl GreedyBot {
    pub fn new(seed: u64) -> GreedyBot {
        GreedyBot { rng: PyRandom::seeded_u64(seed), stats: BotStats::default(), turn_seen: -1 }
    }
}

impl Bot for GreedyBot {
    fn choose(&mut self, real: &State) -> Action {
        let timer = Timer::start();
        let me = real.player_to_act();
        let action = if real.pending.as_ref().map_or(false, |p| p.mulligan) {
            Action::Choice(Choice::Skip)
        } else {
            if real.current == me && real.turn_counter != self.turn_seen {
                self.turn_seen = real.turn_counter;
                self.stats.turns += 1;
            }
            // it scores what the seat can see: a card it draws on the way is a card of an imagined deck
            let seen = seat::unseen(real, me);
            let world = seat::world(real, me, &seen, &mut self.rng);
            let legal = rules::legal_actions(&world);
            let mut best: Vec<Action> = Vec::new();
            let mut best_score = f64::NEG_INFINITY;
            for a in &legal {
                let mut next = world.clone();
                if rules::apply_action(&mut next, a, false).is_err() {
                    continue;
                }
                self.stats.positions += 1;
                let score = greedy_evaluate(&next, me);
                if score > best_score {
                    best_score = score;
                    best.clear();
                    best.push(*a);
                } else if score == best_score {
                    best.push(*a);
                }
            }
            match best.len() {
                0 => Action::Pass,
                1 => best[0],
                n => best[self.rng.choice_index(n)],
            }
        };
        timer.stop(&mut self.stats);
        action
    }

    fn stats(&self) -> BotStats {
        self.stats
    }

    fn spec(&self) -> String {
        "greedy".into()
    }
}
