//! A position's key: two positions with the same key are the same position for everything still to come this turn,
//! so a search follows only one of them. Playing A then B and B then A reach one key.
//!
//! The key covers what the rules read: the board (each tile's animal with what effects changed on it, and anything
//! still beneath it), both hands as sets, the decks, the Remove Pile, food, whose turn, the turn's mana and counts, the
//! leaders' state, Poison's timers, and whatever is still resolving. It leaves out what differs between two orders of
//! the same plays and cannot change what follows from a quiet position in practice: the instance ids, the order the
//! tiles were taken in (read only to order removals at 0 strength) and the count of actions applied (read only by the
//! 30-action cap). A position with something still resolving is keyed exactly, ids and order included.

use std::hash::{BuildHasherDefault, Hash};

use crate::data::*;
use crate::state::{State, Unit};

#[inline]
fn mix(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9E37_79B9_7F4A_7C15);
    x = (x ^ (x >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    x ^ (x >> 31)
}

/// Folds values in with one multiply each (rotate, xor, multiply by an odd constant: a bijection of the running value
/// for each value added) and mixes once at the end; a full mix for every value was a fifth of a search's time.
struct Hasher(u64);

impl Hasher {
    #[inline]
    fn add(&mut self, v: u64) {
        self.0 = (self.0.rotate_left(26) ^ v).wrapping_mul(0x9E37_79B9_7F4A_7C15);
    }

    #[inline]
    fn finish(&self) -> u64 {
        mix(self.0)
    }
}

/// The steps still resolving, the choice waited on and the timers are hashed field by field (`#[derive(Hash)]`), each
/// integer folded in as one value.
impl std::hash::Hasher for Hasher {
    #[inline]
    fn write(&mut self, bytes: &[u8]) {
        self.write_bytes(bytes);
    }
    #[inline]
    fn write_u8(&mut self, v: u8) {
        self.add(v as u64 | 1 << 62);
    }
    #[inline]
    fn write_u16(&mut self, v: u16) {
        self.add(v as u64 | 2 << 60);
    }
    #[inline]
    fn write_u32(&mut self, v: u32) {
        self.add(v as u64 | 3 << 58);
    }
    #[inline]
    fn write_u64(&mut self, v: u64) {
        self.add(v);
    }
    #[inline]
    fn write_usize(&mut self, v: usize) {
        self.add(v as u64 ^ 0x5A5A_0000_0000_0000);
    }
    #[inline]
    fn write_i32(&mut self, v: i32) {
        self.write_u32(v as u32);
    }
    #[inline]
    fn write_isize(&mut self, v: isize) {
        self.write_usize(v as usize);
    }
    fn finish(&self) -> u64 {
        Hasher::finish(self)
    }
}

impl Hasher {
    fn write_bytes(&mut self, bytes: &[u8]) {
        for chunk in bytes.chunks(8) {
            let mut v = 0u64;
            for (i, &b) in chunk.iter().enumerate() {
                v |= (b as u64) << (8 * i);
            }
            self.add(v ^ ((chunk.len() as u64) << 60));
        }
    }
}

/// A unit as the rules read it, without its instance id.
#[inline]
fn unit_bits(u: &Unit) -> u64 {
    u.card as u64 | (u.owner as u64) << 16 | (u.retaliation_used as u64) << 17
        | ((u.strength_mod as i16 as u16) as u64) << 20 | ((u.cost_mod as i16 as u16) as u64) << 36
}

/// The key of `st`. `hidden`: with the parts `me` cannot see (the order of its own deck, the opponent's hand cards),
/// which a search within one imagined world must tell apart; without them it is the key of what `me` sees, the same
/// for the real position and for any world made from it.
pub fn position_key(st: &State, me: Player, hidden: bool) -> u64 {
    let mut h = Hasher(0x5EED);
    let quiet = st.pending.is_none() && st.effect_stack.is_empty();
    let n = st.g.map.n_tiles() as Tile;
    let mut occ = st.board.occ;
    while occ != 0 {
        let t = occ.trailing_zeros() as Tile;
        occ &= occ - 1;
        h.add((t as u64) << 56 ^ unit_bits(&st.board.top(t).unwrap()));
    }
    if st.board.has_buried() {
        let mut sum = 0u64;
        for t in 0..n {
            let under = st.board.buried_of(t);
            for (depth, u) in under.iter().enumerate() {
                sum = sum.wrapping_add(mix((t as u64) << 56 ^ (depth as u64) << 52 ^ unit_bits(u)));
            }
        }
        h.add(sum);
    }
    for p in 0..2u8 {
        let mine = p == me;
        let mut sum = 0u64;
        for u in &st.hands[p as usize] {
            // the opponent's cards are unseen: only what effects did to each slot shows
            let bits = if mine || hidden { unit_bits(u) } else { unit_bits(u) & !0xFFFF };
            sum = sum.wrapping_add(mix(bits));
        }
        h.add(sum);
        h.add(st.hands[p as usize].len() as u64);
        let deck = &st.decks[p as usize];
        h.add(deck.len() as u64);
        if mine && hidden {
            // the order matters: four cards a fold (the length is keyed above)
            for chunk in deck.chunks(4) {
                let mut v = 0u64;
                for (i, &c) in chunk.iter().enumerate() {
                    v |= (c as u64) << (16 * i);
                }
                h.add(v);
            }
        }
        h.add(st.food[p as usize] as u32 as u64);
        h.add(st.power_discount[p as usize] as u32 as u64 | (st.fatigue[p as usize] as u32 as u64) << 32);
        h.add(st.crystals[p as usize] as u32 as u64 | (st.next_mana[p as usize] as u32 as u64) << 32);
        h.add(st.power_uses[p as usize] as u32 as u64 | (st.leeroy_growth[p as usize] as u32 as u64) << 32);
    }
    let mut pile = 0u64;
    for (i, &c) in st.remove_pile.iter().enumerate() {
        pile = pile.wrapping_add(mix(c as u64 | (st.pile_owners[i] as u64) << 16));
    }
    h.add(pile);
    h.add(st.remove_pile.len() as u64);
    h.add(st.current as u64 | (st.power_used as u64) << 1 | (st.turn_counter as u32 as u64) << 2);
    h.add(st.mana_spent as u32 as u64 | (st.played_this_turn as u32 as u64) << 32);
    if let Some(r) = st.result {
        h.add(0xE0D ^ (r.winner.map_or(2, |w| w as u64)) << 12 ^ (r.reason as u64) << 16);
    }
    if !st.scheduled.is_empty() {
        let mut sum = 0u64;
        for s in &st.scheduled {
            let at = st.board.find(s.iid).map_or(63, |(t, _)| t as u64);
            sum = sum.wrapping_add(mix(at | (s.owner as u64) << 8 | (s.remaining as u32 as u64) << 16));
        }
        h.add(sum);
    }
    if !quiet {
        // mid-resolution: the steps name units by id and the rules will read the order, so key all of it
        for &t in st.board.tiles() {
            h.add(t as u64);
            for u in st.board.stack(t) {
                h.add(u.iid as u32 as u64);
            }
        }
        for u in &st.hands[me as usize] {
            h.add(u.iid as u32 as u64);
        }
        st.effect_stack.hash(&mut h);
        st.pending.hash(&mut h);
        st.scheduled.hash(&mut h);
        h.add(st.next_iid as u32 as u64);
    }
    h.finish()
}

/// A key is already mixed: a map or set of keys hashes it as it is.
#[derive(Default)]
pub struct KeyHash(u64);

impl std::hash::Hasher for KeyHash {
    #[inline]
    fn write(&mut self, bytes: &[u8]) {
        for &b in bytes {
            self.0 = (self.0 << 8 | self.0 >> 56) ^ b as u64;
        }
    }
    #[inline]
    fn write_u64(&mut self, v: u64) {
        self.0 = v;
    }
    #[inline]
    fn finish(&self) -> u64 {
        self.0
    }
}

pub type KeyMap<V> = std::collections::HashMap<u64, V, BuildHasherDefault<KeyHash>>;
pub type KeySet = std::collections::HashSet<u64, BuildHasherDefault<KeyHash>>;
