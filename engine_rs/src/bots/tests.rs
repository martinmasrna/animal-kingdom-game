//! The bots' invariants: a bot's choice depends only on what its seat can see, a world holds exactly the cards the seat
//! can count, and a seeded game replays.

use std::path::Path;
use std::sync::Arc;

use crate::actions::Action;
use crate::bots::key::position_key;
use crate::bots::turn::{turn_size, turn_size_unmerged, win_search};
use crate::bots::{make_bot, seat};
use crate::data::*;
use crate::rng::{CowRng, PyRandom};
use crate::rules;
use crate::state::{Options, State};

fn game() -> Arc<Game> {
    let dir = Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join("animal_kingdom").join("data");
    let read = |name: &str| -> serde_json::Value { serde_json::from_slice(&std::fs::read(dir.join(name)).unwrap()).unwrap() };
    let maps = read("maps.json");
    let map = maps["maps"].as_array().unwrap().iter().find(|m| m["id"] == "map_hex19").unwrap();
    Arc::new(Game::new(Cards::from_json(&read(&format!("{}.json", "cards"))).unwrap(), GameMap::from_json(map).unwrap(), Config::default()))
}

/// A random legal deck: a leader and two copies of random collectible cards.
fn deck(g: &Game, rng: &mut PyRandom) -> (Vec<CardId>, CardId) {
    let all: Vec<CardId> = (0..g.cards.list.len() as CardId).filter(|&c| g.cards.get(c).collectible).collect();
    let leaders: Vec<CardId> = all.iter().copied().filter(|&c| g.cards.get(c).beh.leader.is_some()).collect();
    let leader = leaders[rng.randbelow(leaders.len())];
    let mut rest: Vec<CardId> = all.into_iter().filter(|&c| c != leader).collect();
    rng.shuffle(&mut rest);
    let mut cards = vec![leader];
    for c in rest {
        for _ in 0..(if g.cards.get(c).legendary { 1 } else { 2 }).min(25 - cards.len()) {
            cards.push(c);
        }
    }
    (cards, leader)
}

fn new_game(g: &Arc<Game>, seed: u64) -> State {
    let mut rng = PyRandom::seeded_u64(seed);
    let ((a, la), (b, lb)) = (deck(g, &mut rng), deck(g, &mut rng));
    State::new_game(g.clone(), &a, &b, seed as u128, None, [Some(la), Some(lb)]).unwrap()
}

/// Every position of a game between `specs`, with each action taken.
fn positions(g: &Arc<Game>, seed: u64, specs: [&str; 2]) -> Vec<(State, Action)> {
    let mut st = new_game(g, seed);
    let mut bots = [make_bot(specs[0], seed).unwrap(), make_bot(specs[1], seed + 1).unwrap()];
    let mut out = Vec::new();
    while rules::is_terminal(&st).is_none() && out.len() < 600 {
        let action = bots[st.player_to_act() as usize].choose(&st);
        out.push((st.clone(), action));
        rules::apply_action(&mut st, &action, true).unwrap();
    }
    out
}

/// The same position as `me` sees it, with everything `me` cannot see dealt differently: the opponent's unknown hand
/// cards and deck reshuffled among themselves, `me`'s own deck in another order, another random stream.
fn twin(st: &State, me: Player, rng: &mut PyRandom) -> State {
    let mut t = st.clone();
    let (m, o) = (me as usize, other(me) as usize);
    let seen = seat::unseen(st, me);
    let mut hidden: Vec<CardId> = seen.unknown_slots.iter().map(|&i| t.hands[o][i].card).collect();
    hidden.extend(t.decks[o].iter().copied());
    rng.shuffle(&mut hidden);
    let mut next = hidden.into_iter();
    for &i in &seen.unknown_slots {
        t.hands[o][i].card = next.next().unwrap();
    }
    let n = t.decks[o].len();
    t.decks[o].clear();
    t.decks[o].extend(next.take(n));
    let looking = match &t.pending {
        Some(p) if p.chooser == me => match p.options {
            Options::Deck(k) => k as usize,
            _ => 0,
        },
        _ => 0,
    };
    let below = t.decks[m].len() - looking.min(t.decks[m].len());
    rng.shuffle(&mut t.decks[m][..below]);
    t.rng = CowRng::new(PyRandom::seeded_u64(rng.getrandbits(64)));
    t
}

fn multiset(mut v: Vec<CardId>) -> Vec<CardId> {
    v.sort_unstable();
    v
}

#[test]
fn a_world_holds_exactly_what_the_seat_can_count() {
    let g = game();
    let mut rng = PyRandom::seeded_u64(5);
    let mut checked = 0;
    for seed in 0..40 {
        for (st, _) in positions(&g, seed, ["greedy", "greedy"]) {
            for me in 0..2u8 {
                let (m, o) = (me as usize, other(me) as usize);
                let seen = seat::unseen(&st, me);
                // the pool the seat counts is the opponent's unknown hand cards and deck, card for card
                let mut hidden: Vec<CardId> = seen.unknown_slots.iter().map(|&i| st.hands[o][i].card).collect();
                hidden.extend(st.decks[o].iter().copied());
                assert_eq!(multiset(hidden.clone()), seen.pool, "seed {seed}: the unseen pool is not the opponent's hidden cards");
                let w = seat::world(&st, me, &seen, &mut rng);
                assert_eq!(w.hands[m], st.hands[m]);
                assert_eq!(multiset(w.decks[m].to_vec()), multiset(st.decks[m].to_vec()));
                assert_eq!((w.hands[o].len(), w.decks[o].len()), (st.hands[o].len(), st.decks[o].len()));
                let mut dealt: Vec<CardId> = seen.unknown_slots.iter().map(|&i| w.hands[o][i].card).collect();
                dealt.extend(w.decks[o].iter().copied());
                assert_eq!(multiset(dealt), multiset(hidden));
                assert_eq!(position_key(&w, me, false), position_key(&st, me, false), "a world looks like the position from the seat");
                checked += 1;
            }
        }
    }
    assert!(checked > 1000);
}

#[test]
fn a_bot_chooses_from_what_its_seat_sees_only() {
    // Deal the hidden cards another way and the same bot, from the same seed, must choose the same action.
    let g = game();
    let mut rng = PyRandom::seeded_u64(11);
    let mut checked = 0;
    for seed in 0..12 {
        for (i, (st, _)) in positions(&g, 100 + seed, ["turn:budget=3000", "greedy"]).into_iter().enumerate() {
            let me = st.player_to_act();
            let other_deal = twin(&st, me, &mut rng);
            // the last two ask the reply level: the opponent's hands it imagines are dealt from what the seat can count
            for spec in ["greedy", "turn:budget=3000", "turn:budget=300,worlds=2", "turn:budget=8000,reply=3,hands=2", "turn:budget=8000,reply=2,hands=3,spread=1"] {
                let a = make_bot(spec, 77 + i as u64).unwrap().choose(&st);
                let b = make_bot(spec, 77 + i as u64).unwrap().choose(&other_deal);
                assert_eq!(a, b, "seed {seed}, action {i}: {spec} read a hidden card");
                checked += 1;
            }
        }
    }
    assert!(checked > 500);
}

#[test]
fn a_seeded_game_replays() {
    let g = game();
    for seed in 0..4 {
        let a: Vec<Action> = positions(&g, 300 + seed, ["turn:budget=2000", "turn:budget=500"]).into_iter().map(|(_, a)| a).collect();
        let b: Vec<Action> = positions(&g, 300 + seed, ["turn:budget=2000", "turn:budget=500"]).into_iter().map(|(_, a)| a).collect();
        assert_eq!(a, b);
    }
}

#[test]
fn every_action_a_bot_chooses_is_legal_and_games_end() {
    let g = game();
    for seed in 0..30 {
        let mut st = new_game(&g, 500 + seed);
        let second = if seed % 3 == 0 { "turn:budget=6000,reply=4,hands=2" } else { "turn:budget=150,worlds=1,width=4" };
        let mut bots = [make_bot("turn:budget=1500", seed).unwrap(), make_bot(second, seed).unwrap()];
        let mut n = 0;
        while rules::is_terminal(&st).is_none() {
            let action = bots[st.player_to_act() as usize].choose(&st);
            rules::apply_action(&mut st, &action, true).unwrap_or_else(|e| panic!("seed {seed}: {e}"));
            n += 1;
            assert!(n < 20_000, "seed {seed}: the game never ended");
        }
    }
}

#[test]
fn two_orders_of_the_same_plays_are_one_position() {
    // Somewhere in a few games there is a turn with two plays that can go in either order: merged, it is smaller.
    let g = game();
    let mut smaller = 0;
    for seed in 0..6 {
        for (st, _) in positions(&g, 700 + seed, ["greedy", "greedy"]) {
            if st.pending.is_some() || !st.effect_stack.is_empty() {
                continue;
            }
            let (merged, _, cut) = turn_size(&st, 20_000);
            let (unmerged, cut2) = turn_size_unmerged(&st, 20_000);
            if !cut && !cut2 {
                assert!(merged <= unmerged);
                smaller += (merged < unmerged) as u32;
            }
        }
    }
    assert!(smaller > 10);
}

#[test]
fn fatigue_is_public_and_part_of_the_position() {
    // The count of empty draws is seen by both seats: a world keeps it, and two positions that differ only in it are two.
    let g = game();
    let st = new_game(&g, 41);
    let mut tired = st.clone();
    tired.fatigue[1] = 2;
    for me in 0..2u8 {
        assert_ne!(position_key(&st, me, false), position_key(&tired, me, false));
        let seen = seat::unseen(&tired, me);
        let w = seat::world(&tired, me, &seen, &mut PyRandom::seeded_u64(9));
        assert_eq!(w.fatigue, tired.fatigue);
        assert_eq!(position_key(&w, me, false), position_key(&tired, me, false));
    }
}

/// A position saved from a game (`bot_bench show --dump TURN`). None when today's cards no longer hold one of its cards.
fn saved(g: &Arc<Game>, text: &str) -> Option<State> {
    State::from_json(g.clone(), &serde_json::from_str(text).unwrap()).ok()
}

/// The bot's turn from `st`: the position it leaves.
fn play_turn(st: &State, spec: &str, seed: u64) -> State {
    let mut st = st.clone();
    let (me, turn) = (st.player_to_act(), st.turn_counter);
    let mut bot = make_bot(spec, seed).unwrap();
    while st.result.is_none() && st.turn_counter == turn && st.player_to_act() == me {
        let action = bot.choose(&st);
        rules::apply_action(&mut st, &action, true).unwrap();
    }
    st
}

#[test]
fn a_win_in_hand_is_taken() {
    // Two turns the whole-turn search lost its way in, each with a win that needs no hidden card:
    // - Food Token against itself, seed 7479377187389669384, turn 8 (B on 18 food, 4 mana, A one food from winning): two
    //   Spores fill regions, then the Elf's power and the regions' food make 30. The search kept the lines that spent
    //   the 2 mana of the power on a card, because it ranks an unfinished turn by ending it there, and played one.
    // - Control against Aggro, seed 5424489383026342908, turn 14 (A on 26): the Giant Hunter removes the flier standing
    //   in four of A's regions and a Mama Spore takes its tile.
    let g = game();
    for (name, text) in [("elf_power_win", include_str!("positions/elf_power_win.json")), ("clear_and_fill_win", include_str!("positions/clear_and_fill_win.json"))] {
        let Some(st) = saved(&g, text) else {
            eprintln!("{name}: today's cards no longer hold this position; skipped");
            continue;
        };
        let me = st.player_to_act();
        let found = win_search(&st, me, 20_000);
        assert!(found.line.is_some(), "{name}: the position holds a win");
        let mut rng = PyRandom::seeded_u64(5);
        for seed in 0..4 {
            // whatever the hidden cards are
            let real = if seed == 0 { st.clone() } else { twin(&st, me, &mut rng) };
            let after = play_turn(&real, "turn:budget=20000", seed);
            assert_eq!(after.result.and_then(|r| r.winner), Some(me), "{name}, seed {seed}: the bot did not take the win");
        }
    }
}

#[test]
fn a_look_for_a_win_reads_nothing_hidden() {
    // The look finds the same line in the real position and in any world dealt from the seat's knowledge, and never a
    // line through a drawn card.
    let g = game();
    let mut rng = PyRandom::seeded_u64(77);
    let mut found = 0;
    for seed in 0..12 {
        for (st, _) in positions(&g, 900 + seed, ["turn:budget=1500", "greedy"]) {
            if st.pending.is_some() || !st.effect_stack.is_empty() || st.current != st.player_to_act() {
                continue;
            }
            let me = st.player_to_act();
            let a = win_search(&st, me, 3_000);
            let b = win_search(&twin(&st, me, &mut rng), me, 3_000);
            assert_eq!(a.line, b.line, "seed {seed}: the look read a hidden card");
            assert_eq!(a.positions, b.positions);
            if let Some(line) = a.line {
                found += 1;
                let mut c = st.clone();
                let deck = c.decks[me as usize].len();
                for action in &line {
                    assert_eq!(c.decks[me as usize].len(), deck, "the line drew a card");
                    rules::apply_action(&mut c, action, true).unwrap();
                }
                assert_eq!(c.result.and_then(|r| r.winner), Some(me));
            }
        }
    }
    assert!(found > 0);
}
