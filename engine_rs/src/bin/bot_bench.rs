//! The bot benchmark: one bot against another over a set of decks, every deal played twice with the pilots swapped.
//!
//!   bot_bench run   --x SPEC --y SPEC [--decks FILE | --random-decks N] [--seeds N] [--name NAME] ...
//!   bot_bench show  --x SPEC --y SPEC [--decks FILE] --a DECK --b DECK --seed S     one game, readable
//!   bot_bench turns [--bot SPEC] [--games N]                                         how large a turn is
//!
//! A bot's budget is a count of positions, never a clock, and every bot is seeded from the deal, so a run with the
//! same arguments on the same commit plays the same games on any machine at any load. `tools/bot_bench/README.md`.

use std::collections::HashMap;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use serde_json::{json, Value};

use ak_engine::actions::{Action, Target};
use ak_engine::bots::turn::{turn_size, turn_size_unmerged};
use ak_engine::bots::{make_bot, Bot, BotStats};
use ak_engine::data::*;
use ak_engine::effects;
use ak_engine::rng::PyRandom;
use ak_engine::rules;
use ak_engine::state::State;

const DECK_SIZE: usize = 25;

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

struct Args {
    cmd: String,
    opts: HashMap<String, String>,
}

impl Args {
    fn parse() -> Result<Args, String> {
        let mut it = std::env::args().skip(1);
        let cmd = it.next().ok_or("usage: bot_bench run|show|turns [--option value ...]")?;
        let mut opts = HashMap::new();
        while let Some(k) = it.next() {
            let key = k.strip_prefix("--").ok_or_else(|| format!("unexpected argument {k:?}"))?.to_string();
            if key == "log-actions" || key == "swap" {
                opts.insert(key, "1".into());
            } else {
                opts.insert(key, it.next().ok_or_else(|| format!("--{k} needs a value"))?);
            }
        }
        Ok(Args { cmd, opts })
    }

    fn get(&self, k: &str) -> Option<&str> {
        self.opts.get(k).map(|s| s.as_str())
    }

    fn num(&self, k: &str, default: u64) -> Result<u64, String> {
        match self.get(k) {
            Some(v) => v.parse().map_err(|_| format!("--{k} {v:?} is not a whole number")),
            None => Ok(default),
        }
    }
}

/// The folder holding the card table and the map: `--data`, or the package's own, found from where the binary runs or
/// from where it was built.
fn data_dir(args: &Args) -> PathBuf {
    if let Some(d) = args.get("data") {
        return PathBuf::from(d);
    }
    for base in [PathBuf::from("."), PathBuf::from(".."), Path::new(env!("CARGO_MANIFEST_DIR")).join("..")] {
        let d = base.join("animal_kingdom").join("data");
        if d.join("maps.json").exists() {
            return d;
        }
    }
    PathBuf::from("animal_kingdom/data")
}

/// The game (cards, map, the default Config) and a hash of the card table and the map it was read from.
fn load_game(args: &Args) -> Result<(Arc<Game>, String), String> {
    let dir = data_dir(args);
    let read = |name: &str| std::fs::read(dir.join(name)).map_err(|e| format!("{}: {e}", dir.join(name).display()));
    let (cards_raw, maps_raw) = (read(&format!("{}.json", "cards"))?, read("maps.json")?);
    let cards: Value = serde_json::from_slice(&cards_raw).map_err(|e| e.to_string())?;
    let maps: Value = serde_json::from_slice(&maps_raw).map_err(|e| e.to_string())?;
    let map_id = args.get("map").unwrap_or("map_hex19");
    let rec = maps["maps"].as_array().and_then(|l| l.iter().find(|m| m["id"].as_str() == Some(map_id)))
        .ok_or_else(|| format!("no map {map_id:?}"))?;
    let game = Game::new(Cards::from_json(&cards)?, GameMap::from_json(rec)?, Config::default());
    let hash = fnv(&maps_raw, fnv(&cards_raw, 0xcbf2_9ce4_8422_2325));
    Ok((Arc::new(game), format!("{hash:016x}")))
}

#[derive(Clone)]
struct DeckList {
    name: String,
    leader: CardId,
    cards: Vec<CardId>,
}

/// What makes a deck illegal (`animal_kingdom/decks.py`): 25 collectible cards, two copies at most and one of a
/// legendary, led by a leader that is in it.
fn deck_problem(g: &Game, d: &DeckList) -> Option<String> {
    if d.cards.len() != DECK_SIZE {
        return Some(format!("{} cards, not {DECK_SIZE}", d.cards.len()));
    }
    for &c in &d.cards {
        let card = g.cards.get(c);
        let n = d.cards.iter().filter(|&&x| x == c).count();
        if !card.collectible {
            return Some(format!("{:?} is not collectible", card.id));
        }
        if n > if card.legendary { 1 } else { 2 } {
            return Some(format!("{n} copies of {:?}", card.id));
        }
    }
    if g.cards.get(d.leader).beh.leader.is_none() || !d.cards.contains(&d.leader) {
        return Some(format!("{:?} cannot lead it", g.cards.name_of(d.leader)));
    }
    None
}

/// Decks from a file: `{"decks": [{"name", "leader", "cards": [25 ids]}]}`.
fn decks_from_file(g: &Game, path: &str) -> Result<Vec<DeckList>, String> {
    let raw: Value = serde_json::from_slice(&std::fs::read(path).map_err(|e| format!("{path}: {e}"))?).map_err(|e| format!("{path}: {e}"))?;
    let mut out = Vec::new();
    for d in raw["decks"].as_array().ok_or("the deck file needs a \"decks\" list")? {
        let name = d["name"].as_str().ok_or("a deck with no name")?.to_string();
        let cards: Vec<CardId> = d["cards"].as_array().ok_or("a deck with no cards")?.iter()
            .map(|c| g.cards.need(c.as_str().unwrap_or(""))).collect::<Result<_, _>>()?;
        let deck = DeckList { leader: g.cards.need(d["leader"].as_str().unwrap_or(""))?, cards, name };
        if let Some(bad) = deck_problem(g, &deck) {
            return Err(format!("deck {:?}: {bad}", deck.name));
        }
        out.push(deck);
    }
    Ok(out)
}

/// `n` random legal decks from a seed: a random leader, then random collectible cards at two copies each (one of a
/// legendary) until the deck is full.
fn random_decks(g: &Game, n: usize, seed: u64) -> Vec<DeckList> {
    let mut rng = PyRandom::seeded_u64(mix(seed ^ 0xDEC5));
    let all: Vec<CardId> = (0..g.cards.list.len() as CardId).filter(|&c| g.cards.get(c).collectible).collect();
    let leaders: Vec<CardId> = all.iter().copied().filter(|&c| g.cards.get(c).beh.leader.is_some()).collect();
    (0..n).map(|i| {
        let leader = leaders[rng.randbelow(leaders.len())];
        let mut rest: Vec<CardId> = all.iter().copied().filter(|&c| c != leader).collect();
        rng.shuffle(&mut rest);
        let mut cards = vec![leader];
        for c in rest {
            let copies = if g.cards.get(c).legendary { 1 } else { 2 };
            for _ in 0..copies.min(DECK_SIZE - cards.len()) {
                cards.push(c);
            }
            if cards.len() == DECK_SIZE {
                break;
            }
        }
        DeckList { name: format!("random{}", i + 1), leader, cards }
    }).collect()
}

fn load_decks(g: &Game, args: &Args) -> Result<(Vec<DeckList>, String), String> {
    if let Some(n) = args.get("random-decks") {
        let n: usize = n.parse().map_err(|_| "--random-decks needs a number")?;
        let seed = args.num("deck-seed", 1)?;
        return Ok((random_decks(g, n, seed), format!("{n} random decks, deck seed {seed}")));
    }
    let path = args.get("decks").unwrap_or("tools/bot_bench/martin_decks.json");
    Ok((decks_from_file(g, path)?, path.to_string()))
}

fn deck_json(g: &Game, d: &DeckList) -> Value {
    json!({"name": d.name, "leader": g.cards.name_of(d.leader), "cards": d.cards.iter().map(|&c| g.cards.name_of(c)).collect::<Vec<_>>()})
}

/// One game's record. Pilot 0 is the bot X, pilot 1 the bot Y.
struct GameRec {
    deal: usize,
    a: usize,
    b: usize,
    seed: u64,
    /// The pilot in seat A.
    pilot_a: usize,
    first: Player,
    winner: Option<Player>,
    reason: String,
    turns: i32,
    capped: bool,
    food: [i32; 2],
    stats: [BotStats; 2],
    actions: Vec<Value>,
}

impl GameRec {
    fn winner_pilot(&self) -> Option<usize> {
        self.winner.map(|w| if w == 0 { self.pilot_a } else { 1 - self.pilot_a })
    }

    fn to_json(&self, decks: &[DeckList], log_actions: bool) -> Value {
        let pilot = |p: usize| if p == 0 { "x" } else { "y" };
        let stats = |s: &BotStats| json!({"turns": s.turns, "decisions": s.decisions, "positions": s.positions, "ms": s.nanos as f64 / 1e6,
            "searches": s.searches, "turns_cut": s.turns_cut, "turns_hidden": s.turns_hidden, "max_turn_positions": s.max_turn_positions});
        let mut v = json!({
            "deal": self.deal, "deck_a": decks[self.a].name, "deck_b": decks[self.b].name, "seed": self.seed,
            "pilot_a": pilot(self.pilot_a), "pilot_b": pilot(1 - self.pilot_a), "first": pname(self.first),
            "winner": self.winner.map(pname), "winner_pilot": self.winner_pilot().map(pilot), "reason": self.reason,
            "turns": self.turns, "capped": self.capped, "food": {"A": self.food[0], "B": self.food[1]},
            "x": stats(&self.stats[0]), "y": stats(&self.stats[1]),
        });
        if log_actions {
            v["actions"] = Value::Array(self.actions.clone());
        }
        v
    }
}

fn bot_seed(deal_seed: u64, pilot: usize) -> u64 {
    mix(deal_seed ^ mix(0xB07 + pilot as u64))
}

/// Play one game: deck `a` in seat A against deck `b` in seat B from `seed`, the bot `specs[pilot_a]` in seat A.
fn play(g: &Arc<Game>, decks: &[DeckList], deal: usize, a: usize, b: usize, seed: u64, specs: [&str; 2], pilot_a: usize,
        log_actions: bool, mut watch: Option<&mut dyn FnMut(&State, Option<&Action>)>) -> Result<GameRec, String> {
    let mut st = State::new_game(g.clone(), &decks[a].cards, &decks[b].cards, seed as u128, None, [Some(decks[a].leader), Some(decks[b].leader)])?;
    // the bot of each pilot, seeded from the deal: the same bot in both of the deal's games
    let mut bots: [Box<dyn Bot>; 2] = [make_bot(specs[0], bot_seed(seed, 0))?, make_bot(specs[1], bot_seed(seed, 1))?];
    let first = st.first_player;
    let mut actions = Vec::new();
    let mut applied = 0u32;
    if let Some(w) = watch.as_mut() {
        w(&st, None);
    }
    let result = loop {
        if let Some(r) = rules::is_terminal(&st) {
            break r;
        }
        let seat = st.player_to_act();
        let pilot = if seat == 0 { pilot_a } else { 1 - pilot_a };
        let action = bots[pilot].choose(&st);
        rules::apply_action(&mut st, &action, true)
            .map_err(|e| format!("deal {deal} ({} v {}, seed {seed}): {} chose {}: {e}", decks[a].name, decks[b].name, specs[pilot], action.to_json(g)))?;
        if log_actions {
            actions.push(action.to_json(g));
        }
        if let Some(w) = watch.as_mut() {
            w(&st, Some(&action));
        }
        applied += 1;
        if applied > 100_000 {
            return Err(format!("deal {deal}: the game never ended"));
        }
    };
    Ok(GameRec {
        deal, a, b, seed, pilot_a, first, winner: result.winner, reason: result.reason.name().to_string(), turns: st.turn_counter,
        capped: !st.caps.is_empty(), food: st.food, stats: [bots[0].stats(), bots[1].stats()], actions,
    })
}

fn threads(args: &Args) -> Result<usize, String> {
    let default = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(4).saturating_sub(2).max(1);
    Ok(args.num("threads", default as u64)?.max(1) as usize)
}

fn git(args: &[&str]) -> String {
    std::process::Command::new("git").args(args).output().ok()
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).unwrap_or_default()
}

fn pct(x: f64) -> String {
    format!("{:.1}%", 100.0 * x)
}

/// A share and its 95% interval from per-cluster scores.
fn interval(scores: &[f64]) -> (f64, f64, f64) {
    let n = scores.len() as f64;
    if scores.is_empty() {
        return (0.0, 0.0, 0.0);
    }
    let mean = scores.iter().sum::<f64>() / n;
    let var = scores.iter().map(|s| (s - mean).powi(2)).sum::<f64>() / (n - 1.0).max(1.0);
    let half = 1.96 * (var / n).sqrt();
    (mean, mean - half, mean + half)
}

fn run(args: &Args) -> Result<(), String> {
    let (g, pool_hash) = load_game(args)?;
    let (decks, decks_source) = load_decks(&g, args)?;
    let x = args.get("x").ok_or("--x SPEC: the bot under test")?.to_string();
    let y = args.get("y").ok_or("--y SPEC: the bot it is measured against")?.to_string();
    make_bot(&x, 0)?;
    make_bot(&y, 0)?;
    let seeds = args.num("seeds", 20)? as usize;
    let run_seed = args.num("seed", 1)?;
    let log_actions = args.get("log-actions").is_some();
    let n_threads = threads(args)?;
    let name = args.get("name").unwrap_or("run").to_string();
    let dir = PathBuf::from(args.get("out").unwrap_or("results/bot_bench")).join(&name);
    std::fs::create_dir_all(&dir).map_err(|e| format!("{}: {e}", dir.display()))?;

    // every ordered pairing of decks, mirrors included; each deal twice, the pilots swapped
    let mut deals: Vec<(usize, usize, u64)> = Vec::new();
    for a in 0..decks.len() {
        for b in 0..decks.len() {
            for n in 0..seeds {
                deals.push((a, b, mix(run_seed ^ mix((a * 1000 + b) as u64) ^ mix(0x5EED + n as u64)) >> 1));
            }
        }
    }
    let run_json = json!({
        "name": name, "commit": git(&["rev-parse", "HEAD"]), "engine_dirty": !git(&["status", "--porcelain", "--", "."]).is_empty(),
        "card_pool_hash": pool_hash, "x": x, "y": y, "decks_source": decks_source,
        "decks": decks.iter().map(|d| deck_json(&g, d)).collect::<Vec<_>>(),
        "seeds_per_pairing": seeds, "seed": run_seed, "deals": deals.len(), "games": 2 * deals.len(), "threads": n_threads,
        "started_unix": std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0),
    });
    std::fs::write(dir.join("run.json"), serde_json::to_string_pretty(&run_json).unwrap()).map_err(|e| e.to_string())?;
    eprintln!("{name}: {x}  against  {y}; {} decks ({decks_source}), {} deals, {} games, {n_threads} threads", decks.len(), deals.len(), 2 * deals.len());

    let games_file = Mutex::new(std::fs::File::create(dir.join("games.jsonl")).map_err(|e| e.to_string())?);
    let next = AtomicUsize::new(0);
    let done = AtomicUsize::new(0);
    let recs: Mutex<Vec<GameRec>> = Mutex::new(Vec::new());
    let failed: Mutex<Option<String>> = Mutex::new(None);
    let started = Instant::now();
    let total = 2 * deals.len();
    std::thread::scope(|scope| {
        for _ in 0..n_threads {
            scope.spawn(|| loop {
                let job = next.fetch_add(1, Ordering::Relaxed);
                if job >= total || failed.lock().unwrap().is_some() {
                    return;
                }
                let (deal, pilot_a) = (job / 2, job % 2);
                let (a, b, seed) = deals[deal];
                match play(&g, &decks, deal, a, b, seed, [x.as_str(), y.as_str()], pilot_a, log_actions, None) {
                    Ok(rec) => {
                        let line = rec.to_json(&decks, log_actions).to_string();
                        let _ = writeln!(games_file.lock().unwrap(), "{line}");
                        recs.lock().unwrap().push(rec);
                        let n = done.fetch_add(1, Ordering::Relaxed) + 1;
                        if n % (total / 20).max(1) == 0 {
                            eprintln!("  {n}/{total} games, {:.0}s", started.elapsed().as_secs_f64());
                        }
                    }
                    Err(e) => *failed.lock().unwrap() = Some(e),
                }
            });
        }
    });
    if let Some(e) = failed.into_inner().unwrap() {
        return Err(e);
    }
    let mut recs = recs.into_inner().unwrap();
    recs.sort_by_key(|r| (r.deal, r.pilot_a));
    let wall = started.elapsed().as_secs_f64();

    // X's share: a deal's two games count as one observation (a win 1, a draw a half)
    let score = |r: &GameRec| match r.winner_pilot() {
        Some(0) => 1.0,
        Some(_) => 0.0,
        None => 0.5,
    };
    let mut by_deal: Vec<f64> = vec![0.0; deals.len()];
    for r in &recs {
        by_deal[r.deal] += score(r) / 2.0;
    }
    let (share, lo, hi) = interval(&by_deal);
    let mut out = String::new();
    let mut say = |s: String| {
        println!("{s}");
        out.push_str(&s);
        out.push('\n');
    };
    say(format!("{name}: X = {x}   Y = {y}"));
    say(format!("{} games ({} deals, each played twice with the pilots swapped), {}, {:.0}s", recs.len(), deals.len(), decks_source, wall));
    say(format!("X wins {} of games (95% interval {} to {}); 50% is equal", pct(share), pct(lo), pct(hi)));

    // by deck: the same deck in the hands of each bot
    say(String::new());
    say(format!("{:<14} {:>10} {:>10} {:>8}", "deck", "X pilots", "Y pilots", "X - Y"));
    let mut deck_rows = Vec::new();
    for (d, deck) in decks.iter().enumerate() {
        let mut won = [0.0f64; 2];
        let mut n = [0.0f64; 2];
        for r in &recs {
            for (seat, deck_at) in [(0u8, r.a), (1u8, r.b)] {
                if deck_at == d {
                    let pilot = if seat == 0 { r.pilot_a } else { 1 - r.pilot_a };
                    n[pilot] += 1.0;
                    won[pilot] += match r.winner {
                        Some(w) if w == seat => 1.0,
                        Some(_) => 0.0,
                        None => 0.5,
                    };
                }
            }
        }
        let (xr, yr) = (won[0] / n[0].max(1.0), won[1] / n[1].max(1.0));
        say(format!("{:<14} {:>10} {:>10} {:>+7.1}", deck.name, pct(xr), pct(yr), 100.0 * (xr - yr)));
        deck_rows.push(json!({"deck": deck.name, "x": xr, "y": yr}));
    }

    // by seat, how games ended, and what a turn cost
    let seat_share = |first: bool| {
        let v: Vec<f64> = recs.iter().filter(|r| ((if r.first == 0 { r.pilot_a } else { 1 - r.pilot_a }) == 0) == first).map(score).collect();
        v.iter().sum::<f64>() / (v.len() as f64).max(1.0)
    };
    let (x_first, x_second) = (seat_share(true), seat_share(false));
    let first_wins = recs.iter().filter(|r| r.winner == Some(r.first)).count() as f64 / recs.len().max(1) as f64;
    say(String::new());
    say(format!("X going first wins {}, going second {}; the first player wins {} of all games", pct(x_first), pct(x_second), pct(first_wins)));
    let mut reasons: Vec<(String, usize)> = Vec::new();
    for r in &recs {
        match reasons.iter_mut().find(|(k, _)| *k == r.reason) {
            Some(e) => e.1 += 1,
            None => reasons.push((r.reason.clone(), 1)),
        }
    }
    reasons.sort();
    let ends = reasons.iter().map(|(k, n)| format!("{k} {n}")).collect::<Vec<_>>().join(", ");
    let capped = recs.iter().filter(|r| r.capped).count();
    let avg_turns = recs.iter().map(|r| r.turns as f64).sum::<f64>() / recs.len().max(1) as f64;
    say(format!("games ended: {ends}; {capped} games had a turn ended by a cap; {avg_turns:.1} turns a game on average (both players')"));
    let mut bot_rows = Vec::new();
    for (p, spec) in [(0usize, &x), (1usize, &y)] {
        let mut t = BotStats::default();
        for r in &recs {
            let s = &r.stats[p];
            t.turns += s.turns;
            t.positions += s.positions;
            t.nanos += s.nanos;
            t.searches += s.searches;
            t.turns_cut += s.turns_cut;
            t.turns_hidden += s.turns_hidden;
            t.decisions += s.decisions;
            t.max_turn_positions = t.max_turn_positions.max(s.max_turn_positions);
        }
        let turns = (t.turns as f64).max(1.0);
        say(format!("{} {spec}: {:.0} positions and {:.2} ms a turn (most in one turn {}), {:.2} searches a turn; {} of turns cut short of a full search, {} met a draw",
            if p == 0 { "X" } else { "Y" }, t.positions as f64 / turns, t.nanos as f64 / 1e6 / turns, t.max_turn_positions, t.searches as f64 / turns,
            pct(t.turns_cut as f64 / turns), pct(t.turns_hidden as f64 / turns)));
        bot_rows.push(json!({"spec": spec, "positions_per_turn": t.positions as f64 / turns, "ms_per_turn": t.nanos as f64 / 1e6 / turns,
            "max_turn_positions": t.max_turn_positions, "searches_per_turn": t.searches as f64 / turns,
            "turns_cut": t.turns_cut as f64 / turns, "turns_hidden": t.turns_hidden as f64 / turns}));
    }
    let summary = json!({"x_share": share, "interval": [lo, hi], "games": recs.len(), "deals": deals.len(), "decks": deck_rows,
        "x_first": x_first, "x_second": x_second, "first_player_wins": first_wins, "ended": reasons.iter().map(|(k, n)| json!([k, n])).collect::<Vec<_>>(),
        "capped_games": capped, "avg_turns": avg_turns, "x": bot_rows[0], "y": bot_rows[1], "wall_seconds": wall});
    std::fs::write(dir.join("summary.json"), serde_json::to_string_pretty(&summary).unwrap()).map_err(|e| e.to_string())?;
    std::fs::write(dir.join("summary.txt"), out).map_err(|e| e.to_string())?;
    // the games in deal order, so two runs of the same arguments give the same file
    let mut f = std::fs::File::create(dir.join("games.jsonl")).map_err(|e| e.to_string())?;
    for r in &recs {
        writeln!(f, "{}", r.to_json(&decks, log_actions)).map_err(|e| e.to_string())?;
    }
    eprintln!("written to {}", dir.display());
    Ok(())
}

fn deck_named(decks: &[DeckList], name: &str) -> Result<usize, String> {
    decks.iter().position(|d| d.name.eq_ignore_ascii_case(name))
        .or_else(|| name.parse::<usize>().ok().filter(|i| *i < decks.len()))
        .ok_or_else(|| format!("no deck {name:?} (have: {})", decks.iter().map(|d| d.name.as_str()).collect::<Vec<_>>().join(", ")))
}

fn board_line(st: &State) -> String {
    let g = &st.g;
    let mut tiles: Vec<String> = Vec::new();
    for t in 0..g.map.n_tiles() as Tile {
        if let Some(u) = st.board.top(t) {
            tiles.push(format!("{}:{}{}({})", g.map.tile_name(t), pname(u.owner), g.cards.name_of(u.card), effects::effective_strength(st, &u)));
        }
    }
    tiles.join(" ")
}

fn hand_line(st: &State, p: Player) -> String {
    st.hands[p as usize].iter().map(|u| format!("{}[{}]", st.g.cards.name_of(u.card), effects::unit_cost(st, u))).collect::<Vec<_>>().join(" ")
}

/// One game, turn by turn: each turn's hand and mana, the actions, and the board and food it left.
fn show(args: &Args) -> Result<(), String> {
    let (g, _) = load_game(args)?;
    let (decks, _) = load_decks(&g, args)?;
    let x = args.get("x").ok_or("--x SPEC")?;
    let y = args.get("y").unwrap_or(x);
    let a = deck_named(&decks, args.get("a").unwrap_or("0"))?;
    let b = deck_named(&decks, args.get("b").unwrap_or("0"))?;
    let seed = args.num("seed", 1)?;
    let pilot_a = if args.get("swap").is_some() { 1 } else { 0 };
    let specs = [x, y];
    println!("seat A: {} piloted by {}    seat B: {} piloted by {}    seed {seed}", decks[a].name, specs[pilot_a], decks[b].name, specs[1 - pilot_a]);
    let mut turn = -1;
    let mut watch = |st: &State, action: Option<&Action>| {
        if let Some(a) = action {
            let what = match a {
                Action::Place { card, target: Target::Tile(t) } => format!("place {} on {}", st.g.cards.name_of(*card), st.g.map.tile_name(*t)),
                Action::Place { card, target: Target::Den(_) } => format!("RAID with {}", st.g.cards.name_of(*card)),
                Action::Leader => "leader power".to_string(),
                Action::Pass => "end turn".to_string(),
                Action::Choice(c) => format!("choose {}", ak_engine::actions::choice_to_json(&st.g, *c)),
            };
            println!("    {what}");
            if matches!(a, Action::Pass) || st.result.is_some() {
                println!("  board: {}", board_line(st));
                println!("  food A {} B {}   income A {} B {}", st.food[0], st.food[1], rules::region_income(st, 0), rules::region_income(st, 1));
            }
        }
        if st.result.is_none() && st.pending.is_none() && st.turn_counter != turn {
            turn = st.turn_counter;
            let p = st.current;
            println!("turn {} — {} ({} mana)  hand: {}", turn + 1, pname(p), rules::mana_left(st, p), hand_line(st, p));
        }
    };
    let rec = play(&g, &decks, 0, a, b, seed, specs, pilot_a, false, Some(&mut watch))?;
    println!("winner: {} ({}), after {} turns, food A {} B {}", rec.winner.map_or("nobody", pname), rec.reason, rec.turns, rec.food[0], rec.food[1]);
    Ok(())
}

/// How large a turn is: at every turn start of games the bot plays against itself, the whole turn counted with equal
/// positions merged and with nothing merged.
fn turns(args: &Args) -> Result<(), String> {
    let (g, _) = load_game(args)?;
    let (decks, source) = load_decks(&g, args)?;
    let spec = args.get("bot").unwrap_or("turn:budget=20000").to_string();
    let games = args.num("games", 20)? as usize;
    let cap = args.num("cap", 3_000_000)?;
    let run_seed = args.num("seed", 1)?;
    let n_threads = threads(args)?;
    // (own turn number, merged positions, finished turns, merged cut, unmerged positions, unmerged cut)
    let rows: Mutex<Vec<(i32, u64, u64, bool, u64, bool)>> = Mutex::new(Vec::new());
    let next = AtomicUsize::new(0);
    let failed: Mutex<Option<String>> = Mutex::new(None);
    std::thread::scope(|scope| {
        for _ in 0..n_threads {
            scope.spawn(|| loop {
                let job = next.fetch_add(1, Ordering::Relaxed);
                if job >= games {
                    return;
                }
                let (a, b) = (job % decks.len(), (job / decks.len() + job) % decks.len());
                let seed = mix(run_seed ^ mix(0x7045 + job as u64)) >> 1;
                let mut seen_turn = -1;
                let mut local = Vec::new();
                let mut watch = |st: &State, _: Option<&Action>| {
                    if st.result.is_none() && st.pending.is_none() && st.effect_stack.is_empty() && st.turn_counter != seen_turn {
                        seen_turn = st.turn_counter;
                        let (merged, finished, cut) = turn_size(st, cap);
                        let (unmerged, cut2) = turn_size_unmerged(st, cap);
                        local.push((rules::own_turn_number(st, st.current), merged, finished, cut, unmerged, cut2));
                    }
                };
                if let Err(e) = play(&g, &decks, job, a, b, seed, [spec.as_str(), spec.as_str()], 0, false, Some(&mut watch)) {
                    *failed.lock().unwrap() = Some(e);
                }
                rows.lock().unwrap().extend(local);
            });
        }
    });
    if let Some(e) = failed.into_inner().unwrap() {
        return Err(e);
    }
    let rows = rows.into_inner().unwrap();
    println!("turn sizes: {} turn starts from {games} games of {spec} against itself, {source}; counts stop at {cap} positions", rows.len());
    println!("{:<10} {:>6} | {:>30} | {:>24} | {:>36}", "own turn", "turns", "positions, merged (med/p90/max)", "finished turns (med/p90)", "positions, unmerged (med/p90/max)");
    let q = |v: &mut Vec<u64>, f: f64| -> u64 {
        v.sort_unstable();
        if v.is_empty() { 0 } else { v[((v.len() - 1) as f64 * f).round() as usize] }
    };
    for (lo, hi) in [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 999)] {
        let b: Vec<_> = rows.iter().filter(|r| r.0 >= lo && r.0 <= hi).collect();
        if b.is_empty() {
            continue;
        }
        let mut merged: Vec<u64> = b.iter().map(|r| r.1).collect();
        let mut finished: Vec<u64> = b.iter().map(|r| r.2).collect();
        let mut unmerged: Vec<u64> = b.iter().map(|r| r.4).collect();
        let cut = b.iter().filter(|r| r.5).count();
        let label = if hi > 100 { format!("{lo}+") } else { format!("{lo}-{hi}") };
        println!("{:<10} {:>6} | {:>30} | {:>24} | {:>36}", label, b.len(),
            format!("{} / {} / {}", q(&mut merged, 0.5), q(&mut merged, 0.9), q(&mut merged, 1.0)),
            format!("{} / {}", q(&mut finished, 0.5), q(&mut finished, 0.9)),
            format!("{} / {} / {}{}", q(&mut unmerged, 0.5), q(&mut unmerged, 0.9), q(&mut unmerged, 1.0), if cut > 0 { format!(" ({cut} stopped at the cap)") } else { String::new() }));
    }
    Ok(())
}

fn main() {
    let result = Args::parse().and_then(|args| match args.cmd.as_str() {
        "run" => run(&args),
        "show" => show(&args),
        "turns" => turns(&args),
        other => Err(format!("unknown command {other:?} (run, show, turns)")),
    });
    if let Err(e) = result {
        eprintln!("bot_bench: {e}");
        std::process::exit(1);
    }
}
