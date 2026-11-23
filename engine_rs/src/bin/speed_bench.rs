//! How fast the engine and the bots are, and a digest of everything they did, so a change meant only for speed can be
//! checked to play exactly the same games.
//!
//!   speed_bench games [--map map_sq16] [--bot SPEC] [--n 20] [--seed 1]   whole bot-against-bot games on one thread
//!   speed_bench turn  [--map map_sq16] [--bot SPEC] [--n 12] [--seed 1]   one turn's choice on fixed mid-game positions
//!   speed_bench snapshot DIR                                              pin the card table and maps (then --data DIR)
//!   speed_bench sim   [--map map_sq16] [--n 200] [--seed 1]               random games, clone-and-apply pairs a second
//!
//! Every game is seeded, both seats play `--bot` on five seeded random decks, events are
//! recorded on the real position, and each game prints a digest of its actions, its events and its end. Two builds that
//! print the same digests played the same games. Times go to the last line only. Run from the game folder.

use std::sync::Arc;
use std::time::Instant;

use serde_json::Value;

use ak_engine::actions::Action;
use ak_engine::bots::make_bot;
use ak_engine::data::*;
use ak_engine::rng::PyRandom;
use ak_engine::rules;
use ak_engine::state::State;

const PRACTICE: &str = "turn:budget=200000,reply=12,per=2,eval=race,mull=2";

fn mix(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9E37_79B9_7F4A_7C15);
    x = (x ^ (x >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    x ^ (x >> 31)
}

fn fnv(bytes: &[u8], mut h: u64) -> u64 {
    for &b in bytes {
        h ^= b as u64;
        h = h.wrapping_mul(0x100_0000_01b3);
    }
    h
}

fn opt<'a>(args: &'a [String], k: &str, default: &'a str) -> &'a str {
    args.iter().position(|a| a == k).and_then(|i| args.get(i + 1)).map(|s| s.as_str()).unwrap_or(default)
}

/// The game from `--data DIR` (default: the package's data, read from the game folder).
fn load(args: &[String]) -> Arc<Game> {
    let dir = opt(args, "--data", "animal_kingdom/data").to_string();
    let map_id = opt(args, "--map", "map_sq16");
    let read = |name: &str| -> Value { serde_json::from_slice(&std::fs::read(format!("{dir}/{name}")).expect("run from the game folder")).unwrap() };
    let maps = read("maps.json");
    let rec = maps["maps"].as_array().unwrap().iter().find(|m| m["id"] == map_id).expect("no such map");
    Arc::new(Game::new(Cards::from_json(&read(&format!("{}.json", "cards"))).unwrap(), GameMap::from_json(rec).unwrap(), Config::default()))
}

/// Five random legal decks from a fixed seed (as `bot_bench --random-decks`): a random leader, then random collectible
/// cards, two copies each (one of a legendary), until 25.
fn decks(g: &Game) -> Vec<(CardId, Vec<CardId>)> {
    let mut rng = PyRandom::seeded_u64(mix(0xDEC5));
    let all: Vec<CardId> = (0..g.cards.list.len() as CardId).filter(|&c| g.cards.get(c).collectible).collect();
    let leaders: Vec<CardId> = all.iter().copied().filter(|&c| g.cards.get(c).beh.leader.is_some()).collect();
    (0..5).map(|_| {
        let leader = leaders[rng.randbelow(leaders.len())];
        let mut rest: Vec<CardId> = all.iter().copied().filter(|&c| c != leader).collect();
        rng.shuffle(&mut rest);
        let mut cards = vec![leader];
        for c in rest {
            let copies = if g.cards.get(c).legendary { 1 } else { 2 };
            for _ in 0..copies.min(25 - cards.len()) {
                cards.push(c);
            }
            if cards.len() == 25 {
                break;
            }
        }
        (leader, cards)
    }).collect()
}

/// Copy the card table and the maps into DIR, to pin a benchmark's data while the real table changes.
fn snapshot(args: &[String]) {
    let dir = args.get(2).expect("snapshot DIR");
    std::fs::create_dir_all(dir).unwrap();
    for name in [format!("{}.json", "cards"), "maps.json".to_string()] {
        std::fs::copy(format!("animal_kingdom/data/{name}"), format!("{dir}/{name}")).unwrap();
    }
}

/// Game `i`'s deal: two of the five decks and a seed.
fn deal(g: &Arc<Game>, ds: &[(CardId, Vec<CardId>)], seed: u64, i: u64) -> (State, u64) {
    let s = mix(seed ^ mix(i));
    let (a, b) = ((i % 5) as usize, ((i / 5) % 5) as usize);
    let st = State::new_game(g.clone(), &ds[a].1, &ds[b].1, s as u128, None, [Some(ds[a].0), Some(ds[b].0)]).unwrap();
    (st, s)
}

/// Play one game with events on; (digest, actions, winner, turns).
fn play(g: &Arc<Game>, mut st: State, s: u64, spec: &str) -> (u64, usize, String, i32) {
    st.events.on = true;
    let mut bots = [make_bot(spec, mix(s ^ 1)).unwrap(), make_bot(spec, mix(s ^ 2)).unwrap()];
    let mut h = 0xcbf2_9ce4_8422_2325u64;
    let mut n = 0usize;
    while rules::is_terminal(&st).is_none() {
        let seat = st.player_to_act();
        let a = bots[seat as usize].choose(&st);
        h = fnv(a.to_json(g).to_string().as_bytes(), h);
        rules::apply_action(&mut st, &a, true).unwrap();
        for e in st.events.list.drain(..) {
            h = fnv(e.to_json(g).to_string().as_bytes(), h);
        }
        n += 1;
    }
    h = fnv(st.to_json().to_string().as_bytes(), h);
    let r = st.result.unwrap();
    (h, n, format!("{}/{}", r.winner.map_or("-", pname), r.reason.name()), st.turn_counter)
}

fn games(args: &[String]) {
    let g = load(args);
    let spec = opt(args, "--bot", PRACTICE);
    let n: u64 = opt(args, "--n", "20").parse().unwrap();
    let seed: u64 = opt(args, "--seed", "1").parse().unwrap();
    let ds = decks(&g);
    let t0 = Instant::now();
    let mut all = 0xcbf2_9ce4_8422_2325u64;
    let mut actions = 0;
    for i in 0..n {
        let (st, s) = deal(&g, &ds, seed, i);
        let (h, k, res, turns) = play(&g, st, s, spec);
        println!("game {i:3} {res:12} turns {turns:3} actions {k:4} digest {h:016x}");
        all = fnv(&h.to_le_bytes(), all);
        actions += k;
    }
    let secs = t0.elapsed().as_secs_f64();
    println!("ALL {all:016x}");
    println!("time: {n} games, {actions} actions in {secs:.2}s: {:.3} games/s, {:.1} ms a game ({spec})", n as f64 / secs, 1000.0 * secs / n as f64);
}

/// Fixed mid-game positions: game `i` played by a quick bot to the start of turn 4 + i % 8, its player to act.
fn positions(g: &Arc<Game>, seed: u64, n: u64) -> Vec<State> {
    let ds = decks(g);
    let mut out = Vec::new();
    let mut i = 0;
    while (out.len() as u64) < n {
        let (mut st, s) = deal(g, &ds, seed ^ 0x7A, i);
        let target = 4 + (i % 8) as i32;
        let mut bots = [make_bot("turn:budget=2000,mull=2", mix(s ^ 3)).unwrap(), make_bot("turn:budget=2000,mull=2", mix(s ^ 4)).unwrap()];
        while st.result.is_none() && !(st.turn_counter == target && st.pending.is_none() && st.effect_stack.is_empty() && st.applied_this_turn == 0) {
            let a = bots[st.player_to_act() as usize].choose(&st);
            rules::apply_action(&mut st, &a, true).unwrap();
        }
        if st.result.is_none() {
            out.push(st);
        }
        i += 1;
    }
    out
}

fn turn(args: &[String]) {
    let g = load(args);
    let spec = opt(args, "--bot", PRACTICE);
    let n: u64 = opt(args, "--n", "12").parse().unwrap();
    let seed: u64 = opt(args, "--seed", "1").parse().unwrap();
    let reps: u32 = opt(args, "--reps", "3").parse().unwrap();
    let pos = positions(&g, seed, n);
    let mut all = 0xcbf2_9ce4_8422_2325u64;
    let mut total = 0.0f64;
    for (i, st) in pos.iter().enumerate() {
        let mut best = f64::MAX;
        let mut chosen = Action::Pass;
        let mut positions = 0;
        for _ in 0..reps {
            let mut bot = make_bot(spec, mix(seed ^ i as u64)).unwrap();
            let t0 = Instant::now();
            chosen = bot.choose(st);
            best = best.min(t0.elapsed().as_secs_f64());
            positions = bot.stats().positions;
        }
        let j = chosen.to_json(&g).to_string();
        println!("pos {i:2} turn {:2} positions {positions:7} chose {j}", st.turn_counter);
        all = fnv(j.as_bytes(), fnv(&positions.to_le_bytes(), all));
        total += best;
    }
    println!("ALL {all:016x}");
    println!("time: {} positions, {:.1} ms a decision (best of {reps}), {:.2}s in all ({spec})", pos.len(), 1000.0 * total / pos.len() as f64, total);
}

/// Random games: every action legal at a position applied to its own copy (the search's unit of work), then one played.
fn sim(args: &[String]) {
    let g = load(args);
    let n: u64 = opt(args, "--n", "200").parse().unwrap();
    let seed: u64 = opt(args, "--seed", "1").parse().unwrap();
    let ds = decks(&g);
    let mut rng = PyRandom::seeded_u64(seed);
    let mut pairs = 0u64;
    let mut h = 0xcbf2_9ce4_8422_2325u64;
    let t0 = Instant::now();
    for i in 0..n {
        let (mut st, _) = deal(&g, &ds, seed, i);
        let mut steps = 0;
        while st.result.is_none() && steps < 600 {
            let legal = rules::legal_actions(&st);
            for a in &legal {
                let mut c = st.clone();
                let _ = rules::apply_action(&mut c, a, false);
                pairs += 1;
            }
            let pass = rules::can_pass(&st) && rng.random() < 0.15;
            let a = if pass { Action::Pass } else { legal[rng.randbelow(legal.len())] };
            rules::apply_action(&mut st, &a, false).unwrap();
            steps += 1;
        }
        h = fnv(st.to_json().to_string().as_bytes(), h);
    }
    let secs = t0.elapsed().as_secs_f64();
    println!("ALL {h:016x}");
    println!("time: {n} random games, {pairs} clone-and-apply pairs in {secs:.2}s: {:.2} M pairs/s", pairs as f64 / secs / 1e6);
}

/// Nanoseconds for each piece of a search's work, over the fixed mid-game positions of `turn`: a copy, a copy into a
/// position already made, the legal actions, applying each, ending the turn, the key, the race evaluation.
fn parts(args: &[String]) {
    use ak_engine::bots::{eval::RaidOdds, key::position_key, race, seat};
    let g = load(args);
    let pos = positions(&g, 1, 24);
    let reps: u32 = opt(args, "--reps", "2000").parse().unwrap();
    let only = opt(args, "--only", "");
    let time = |name: &str, f: &mut dyn FnMut(&State) -> u64| {
        if !only.is_empty() && only != name {
            return;
        }
        let t0 = Instant::now();
        let mut n = 0u64;
        let mut sink = 0u64;
        for _ in 0..reps {
            for st in &pos {
                sink = sink.wrapping_add(f(st));
                n += 1;
            }
        }
        println!("{name:14} {:7.1} ns  ({sink:x})", t0.elapsed().as_nanos() as f64 / n as f64);
    };
    time("clone", &mut |st| st.clone().food[0] as u64);
    let mut spare = Box::new(pos[0].clone());
    time("clone_from", &mut |st| {
        (*spare).clone_from(st);
        spare.food[0] as u64
    });
    time("legal_actions", &mut |st| rules::legal_actions(st).len() as u64);
    time("clone+apply", &mut |st| {
        let a = rules::legal_actions(st)[0];
        let mut c = st.clone();
        let _ = rules::apply_action(&mut c, &a, false);
        c.food[0] as u64
    });
    time("clone+pass", &mut |st| {
        let mut c = st.clone();
        let _ = rules::apply_action(&mut c, &Action::Pass, false);
        c.food[0] as u64
    });
    time("position_key", &mut |st| position_key(st, st.current, true));
    let mut rng = PyRandom::seeded_u64(5);
    let odds: Vec<RaidOdds> = pos.iter().map(|st| RaidOdds::sample(st, st.current, &seat::unseen(st, st.current), 12, &mut rng)).collect();
    let w = race::RaceWeights::default();
    let mut i = 0;
    time("race::evaluate", &mut |st| {
        i = (i + 1) % pos.len();
        race::evaluate(st, st.current, &w, &odds[i]).to_bits() as u64
    });
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    match args.get(1).map(|s| s.as_str()) {
        Some("games") => games(&args),
        Some("turn") => turn(&args),
        Some("sim") => sim(&args),
        Some("snapshot") => snapshot(&args),
        Some("parts") => parts(&args),
        _ => eprintln!("usage: speed_bench games|turn|sim [--map ID] [--bot SPEC] [--n N] [--seed S]"),
    }
}
