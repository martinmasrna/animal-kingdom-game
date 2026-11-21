//! The bots' invariants: a bot's choice depends only on what its seat can see, a world holds exactly the cards the seat
//! can count, and a seeded game replays.

use std::path::Path;
use std::sync::Arc;

use crate::actions::Action;
use crate::bots::key::position_key;
use crate::bots::turn::{turn_size, turn_size_unmerged};
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
            for spec in ["greedy", "turn:budget=3000", "turn:budget=300,worlds=2"] {
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
        let mut bots = [make_bot("turn:budget=1500", seed).unwrap(), make_bot("turn:budget=150,worlds=1,width=4", seed).unwrap()];
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
