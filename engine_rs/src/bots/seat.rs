//! What a seat knows, and positions made from only that.
//!
//! A seat sees its own hand, the board, the Remove Pile, the food, how many cards the opponent holds and how many are
//! left in each deck, and it knows both decklists. It does not see the opponent's hand or the order of either deck.
//! A bot never searches the real position: it searches a `world`, the real position with every hidden part dealt
//! afresh from what the seat knows. Two real positions that look the same from the seat give the same worlds.

use crate::data::*;
use crate::rng::{CowRng, PyRandom};
use crate::state::{Options, State};

/// The hidden cards of the opponent as the seat can count them.
#[derive(Clone, Debug)]
pub struct Unseen {
    /// The opponent's cards that are in their hand or deck, as a sorted multiset: their decklist less every card of
    /// theirs the seat has seen leave it (on the board, in the Remove Pile).
    pub pool: Vec<CardId>,
    /// The opponent's hand slots whose card the seat cannot know.
    pub unknown_slots: Vec<usize>,
}

/// The opponent's unseen cards from `me`'s seat.
///
/// A card in their hand that their decklist does not hold was made by an effect both players watched (a token put
/// into the hand), so it is known; every other hand card is unknown.
pub fn unseen(real: &State, me: Player) -> Unseen {
    let opp = other(me);
    let list = &real.starting_decks[opp as usize];
    let mut pool: Vec<CardId> = list.clone();
    pool.sort_unstable();
    let mut take = |card: CardId| {
        if let Ok(i) = pool.binary_search(&card) {
            pool.remove(i);
        }
    };
    for (_, u) in real.board.units() {
        if u.owner == opp {
            take(u.card);
        }
    }
    for (i, &card) in real.remove_pile.iter().enumerate() {
        if real.pile_owners[i] == opp {
            take(card);
        }
    }
    let unknown_slots: Vec<usize> = real.hands[opp as usize].iter().enumerate()
        .filter(|(_, u)| list.contains(&u.card)).map(|(i, _)| i).collect();
    // The pool is exactly their unknown hand cards and their deck. If an effect ever breaks that count (a copy of a
    // deck card made into a hand), keep the sizes right: trim, or pad from the decklist.
    let need = unknown_slots.len() + real.decks[opp as usize].len();
    pool.truncate(need);
    let mut i = 0;
    while pool.len() < need && !list.is_empty() {
        pool.push(list[i % list.len()]);
        i += 1;
    }
    pool.sort_unstable();
    Unseen { pool, unknown_slots }
}

/// The real position with every part hidden from `me` dealt afresh: the opponent's unknown hand cards and their deck
/// from their unseen pool, `me`'s own deck reshuffled, and a random stream of its own. The cards `me` is looking at
/// while choosing from the top of its deck (Scout) stay where they are.
pub fn world(real: &State, me: Player, seen: &Unseen, rng: &mut PyRandom) -> State {
    let mut w = real.fork();
    w.events.on = false;
    let (m, o) = (me as usize, other(me) as usize);
    // my deck: I know what is in it, never its order
    let looking = match &w.pending {
        Some(p) if p.chooser == me => match p.options {
            Options::Deck(n) => n as usize,
            _ => 0,
        },
        _ => 0,
    };
    let below = w.decks[m].len() - looking.min(w.decks[m].len());
    w.decks[m][..below].sort_unstable();
    rng.shuffle(&mut w.decks[m][..below]);
    // their hand and deck
    let mut pool = seen.pool.clone();
    rng.shuffle(&mut pool);
    let mut next = pool.into_iter();
    for &slot in &seen.unknown_slots {
        if let Some(card) = next.next() {
            w.hands[o][slot].card = card;
        }
    }
    let n = w.decks[o].len();
    w.decks[o].clear();
    w.decks[o].extend(next.take(n));
    w.rng = CowRng::new(PyRandom::seeded_u64(rng.getrandbits(64)));
    w
}
