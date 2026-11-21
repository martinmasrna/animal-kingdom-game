//! The bots. Each chooses one action for the seat that must act, from what that seat may know (`seat`): its own hand,
//! the board, the Remove Pile, the food, how many cards the opponent holds and both decklists. Never the opponent's
//! hand or the order of either deck. A bot reads no card id, name or text: what a card does it learns by playing it
//! through the rules on a copy of the position.
//!
//! `greedy`: one action at a time, the bot the game shipped with (the fixed baseline).
//! `turn`: plans its whole turn and scores only finished turns.

use std::time::Instant;

use crate::actions::Action;
use crate::state::State;

pub mod eval;
pub mod greedy;
pub mod key;
pub mod seat;
pub mod turn;

/// What a bot did so far, for the benchmark.
#[derive(Clone, Copy, Debug, Default)]
pub struct BotStats {
    /// Actions chosen.
    pub decisions: u64,
    /// Own turns it acted in.
    pub turns: u64,
    /// Positions it made on the way (every action applied to a copy).
    pub positions: u64,
    pub nanos: u64,
    /// Searches run (a turn has one, or more when a draw or a cut search makes it look again).
    pub searches: u64,
    /// Turns whose first search stopped short of every whole turn (the width cap or the budget cut it).
    pub turns_cut: u64,
    /// Turns whose first search met a draw or another hidden outcome and was averaged over sampled decks.
    pub turns_hidden: u64,
    /// The most positions one turn took.
    pub max_turn_positions: u64,
}

pub trait Bot: Send {
    /// The action for the seat to act in `real`. The bot may read `real` only through `seat`.
    fn choose(&mut self, real: &State) -> Action;
    fn stats(&self) -> BotStats;
    fn spec(&self) -> String;
}

/// A bot from its spec: `greedy`, or `turn` with `key=value` settings after a colon, comma-separated
/// (`turn:budget=20000,worlds=4,w.income=2.5`).
pub fn make_bot(spec: &str, seed: u64) -> Result<Box<dyn Bot>, String> {
    let (kind, rest) = spec.split_once(':').unwrap_or((spec, ""));
    let mut settings: Vec<(&str, &str)> = Vec::new();
    for part in rest.split(',').filter(|p| !p.is_empty()) {
        settings.push(part.split_once('=').ok_or_else(|| format!("bot spec: {part:?} is not key=value"))?);
    }
    match kind {
        "greedy" => {
            if !settings.is_empty() {
                return Err("bot spec: greedy takes no settings".into());
            }
            Ok(Box::new(greedy::GreedyBot::new(seed)))
        }
        "turn" => Ok(Box::new(turn::TurnBot::new(turn::TurnSpec::parse(&settings)?, seed))),
        _ => Err(format!("bot spec: unknown bot {kind:?} (greedy, turn)")),
    }
}

/// Times one `choose` into `stats`.
pub(crate) struct Timer(Instant);

impl Timer {
    pub fn start() -> Timer {
        Timer(Instant::now())
    }

    pub fn stop(self, stats: &mut BotStats) {
        stats.nanos += self.0.elapsed().as_nanos() as u64;
        stats.decisions += 1;
    }
}

#[cfg(test)]
mod tests;
