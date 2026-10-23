//! Determinization (bots/determinize.py): a possible world with the hidden information re-dealt from one seat's view.

use crate::data::*;
use crate::rng::PyRandom;
use crate::state::{State, Unit};

pub fn determinize(st: &State, me: Player, rng: &mut PyRandom) -> State {
    let mut clone = st.clone();
    let opp = other(me);
    let m = me as usize;
    let o = opp as usize;
    let mut mine = std::mem::take(&mut clone.decks[m]);
    mine.sort_by(|a, b| st.cname(*a).cmp(st.cname(*b)));
    rng.shuffle(&mut mine);
    clone.decks[m] = mine;
    let hand = std::mem::take(&mut clone.hands[o]);
    let (kept, hidden): (Vec<Unit>, Vec<Unit>) = hand.into_iter().partition(|u| u.locked_until_turn > clone.turn_counter);
    let mut pool: Vec<CardId> = hidden.iter().map(|u| u.card).collect();
    pool.extend(clone.decks[o].iter().copied());
    pool.sort_by(|a, b| st.cname(*a).cmp(st.cname(*b)));
    rng.shuffle(&mut pool);
    let dealt = hidden.len();
    let mut new_hand: crate::state::Hand = kept.into_iter().collect();
    for &card in &pool[..dealt] {
        let iid = clone.new_iid();
        new_hand.push(Unit::new(card, opp, iid));
    }
    clone.hands[o] = new_hand;
    clone.decks[o] = crate::state::Deck::from_slice(&pool[dealt..]);
    clone.rng = PyRandom::seeded_u64(rng.getrandbits(64)).into();
    clone
}
