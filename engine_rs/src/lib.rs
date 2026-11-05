//! The Animal Kingdom engine in Rust: the rules and every card (state, rules, effects, cards, statics, strength),
//! the bots (bots), and, behind the `python` feature, the PyO3 module `ak_engine` (py) that the Python package uses.

pub mod actions;
pub mod bots;
pub mod cards;
pub mod clock;
pub mod data;
pub mod effects;
pub mod rng;
pub mod rules;
pub mod state;
pub mod statics;
pub mod strength;
pub mod value;
pub mod view;

#[cfg(feature = "python")]
pub mod py;

#[cfg(feature = "wasm")]
pub mod wasm;

// The search allocates and frees effect maps and action lists by the million; the system allocator on macOS was a
// quarter of the Expert's move in the profile (2026-10-23), mimalloc about halves that cost.
// Not on wasm32, where mimalloc's C does not build; the browser module uses Rust's own allocator.
#[cfg(not(target_arch = "wasm32"))]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;
