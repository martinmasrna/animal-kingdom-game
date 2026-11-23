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
    /// The opponent's cards that are in their hand or deck, as a sorted multiset: their decklist and the cards effects
    /// made into their hand, less every card of theirs the seat can see (on the board, in the Remove Pile, made in hand).
    pub pool: Vec<CardId>,
    /// The opponent's hand slots whose card the seat cannot know.
    pub unknown_slots: Vec<usize>,
}

/// The opponent's unseen cards from `me`'s seat.
///
/// A card an effect made into their hand (the Bird Egg's Flight 1s, Mama Spore's Spores) both players watched arrive,
/// so it is known; every other hand card is unknown.
pub fn unseen(real: &State, me: Player) -> Unseen {
    let opp = other(me);
    let mut pool: Vec<CardId> = real.starting_decks[opp as usize].clone();
    pool.extend(real.made[opp as usize].iter().copied());
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
    let mut unknown_slots: Vec<usize> = Vec::new();
    for (i, u) in real.hands[opp as usize].iter().enumerate() {
        if u.made {
            take(u.card);
        } else {
            unknown_slots.push(i);
        }
    }
    debug_assert_eq!(pool.len(), unknown_slots.len() + real.decks[opp as usize].len(), "the unseen pool is their hidden cards");
    Unseen { pool, unknown_slots }
}

/// The real position with every part hidden from `me` dealt afresh: the opponent's unknown hand cards and their deck
/// from their unseen pool, `me`'s own deck reshuffled, and a random stream of its own. The cards `me` is looking at
/// while choosing from the top of its deck (Scout) stay where they are.
pub fn world(real: &State, me: Player, seen: &Unseen, rng: &mut PyRandom) -> State {
    let mut w = real.fork();
    w.events.on = false;
    let m = me as usize;
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
    redeal(&mut w, me, seen, rng, false);
    w
}

/// Deal `me`'s opponent afresh in the world `w`: their unknown hand cards and their deck from their unseen pool, and a
/// random stream of its own. `me`'s own deck stays as `w` has it. `spread`: the hand is dealt one card from each of as
/// many equal runs of the pool in order of cost as it has unknown cards, so every dealt hand holds cheap and dear cards
/// in the pool's proportions; plain, it is a shuffle.
pub fn redeal(w: &mut State, me: Player, seen: &Unseen, rng: &mut PyRandom, spread: bool) {
    let o = other(me) as usize;
    let mut pool = seen.pool.clone();
    let slots = seen.unknown_slots.len().min(pool.len());
    let mut hand: Vec<CardId> = Vec::with_capacity(slots);
    if spread && slots > 0 {
        pool.sort_by_key(|&c| (w.card(c).cost, c));
        // one card from each run, taken from the last run back so the indices before it stay put
        let n = pool.len();
        for run in (0..slots).rev() {
            let (lo, hi) = (run * n / slots, (run + 1) * n / slots);
            hand.push(pool.remove(lo + rng.randbelow((hi - lo).max(1))));
        }
        rng.shuffle(&mut hand);
        rng.shuffle(&mut pool);
    } else {
        rng.shuffle(&mut pool);
        hand.extend(pool.drain(..slots));
    }
    for (&slot, card) in seen.unknown_slots.iter().zip(hand) {
        w.hands[o][slot].card = card;
    }
    let n = w.decks[o].len();
    w.decks[o].clear();
    w.decks[o].extend(pool.into_iter().take(n));
    w.rng = CowRng::new(PyRandom::seeded_u64(rng.getrandbits(64)));
}
