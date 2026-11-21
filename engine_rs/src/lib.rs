//! Animal Kingdom's rules engine: the position, the rules, every card's effect. The Python package's `engine/` is the
//! same game; `tools/engine_rs/fuzz.py` proves the two agree position by position.

#[cfg(not(target_arch = "wasm32"))]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

pub mod actions;
pub mod cards;
pub mod data;
pub mod effects;
pub mod events;
pub mod json;
pub mod rng;
pub mod rules;
pub mod state;

#[cfg(feature = "python")]
mod py;
