//! The Animal Kingdom engine in Rust: the rules and every card (state, rules, effects, cards, statics, strength),
//! the bots (bots), and, behind the `python` feature, the PyO3 module `ak_engine` (py) that the Python package uses.

pub mod actions;
pub mod bots;
pub mod cards;
pub mod data;
pub mod effects;
pub mod rng;
pub mod rules;
pub mod state;
pub mod statics;
pub mod strength;
pub mod value;

#[cfg(feature = "python")]
pub mod py;
