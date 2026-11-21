//! Animal Kingdom's rules engine: the position, the rules, every card's effect. The Python package reaches it through
//! the module `ak_engine` (py.rs) and holds no rules of its own.

#[cfg(not(target_arch = "wasm32"))]
#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

pub mod actions;
pub mod bots;
pub mod cards;
pub mod data;
pub mod effects;
pub mod events;
pub mod json;
pub mod rng;
pub mod rules;
pub mod state;
pub mod view;

#[cfg(feature = "python")]
mod py;
