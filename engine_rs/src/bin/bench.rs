//! A whole game between two bots from the command line, for timing and profiling:
//!   bench <cards.json> <maps.json> <config.json> <deck_a ids,comma> <deck_b ids,comma> <seed> <spec_a> <spec_b> [games]
use std::sync::Arc;
use std::time::Instant;

use ak_engine::bots::{self, Bot};
use ak_engine::data::{Cards, Config, GameMap};
use ak_engine::rng::PyRandom;
use ak_engine::rules;
use ak_engine::state::{Game, State};

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let cards_raw: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(&args[1]).unwrap()).unwrap();
    let maps_raw: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(&args[2]).unwrap()).unwrap();
    let cfg_raw: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(&args[3]).unwrap()).unwrap();
    let cards = Cards::from_json(&cards_raw).unwrap();
    let rec = maps_raw["maps"].as_array().unwrap().iter().find(|m| m["id"].as_str() == Some("map_b")).unwrap();
    let map = GameMap::from_json(rec).unwrap();
    let cfg = Config::from_json(&cfg_raw).unwrap();
    let g = Arc::new(Game::new(cards, map, cfg));
    let deck = |s: &str| -> Vec<u16> { s.split(',').map(|n| g.cards.id_of(n).unwrap()).collect() };
    let a = deck(&args[4]);
    let b = deck(&args[5]);
    let seed: i64 = args[6].parse().unwrap();
    let games: usize = args.get(9).and_then(|x| x.parse().ok()).unwrap_or(1);
    let t0 = Instant::now();
    let mut actions = 0;
    for k in 0..games {
        let s = seed + k as i64;
        let mut st = State::new_game(g.clone(), &a, &b, s, None, false);
        st.record_events = false;
        let mut bots: [Bot; 2] = [Bot::from_spec(&args[7], s * 2, None).unwrap(), Bot::from_spec(&args[8], s * 2 + 1, None).unwrap()];
        let mut eps = PyRandom::seeded(s);
        let log = bots::play_out(&mut st, &mut bots, 0.0, &mut eps, |_, _, _| {});
        actions += log.len();
        let r = rules::is_terminal(&st).unwrap();
        println!("game {k}: {:?} by {} in {} turns, {} actions", r.winner, r.reason, st.turn_counter, log.len());
    }
    let dt = t0.elapsed().as_secs_f64();
    println!("{games} games, {actions} actions in {dt:.2}s ({:.1} ms/action)", 1000.0 * dt / actions as f64);
}
