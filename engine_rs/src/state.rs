//! The position: everything that changes during a game. A clone is a few flat copies and no allocation in the usual
//! case (nothing resolving, no turn cap on record), because a bot's search clones a position for every line it imagines.

use std::sync::Arc;

use smallvec::SmallVec;

use crate::data::*;
use crate::events::{Ev, Events};
use crate::rng::{CowRng, PyRandom};

/// One card instance: the same instance moves from hand to board.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Unit {
    pub card: CardId,
    pub owner: Player,
    /// Spikes: spent on the first enemy that covers it.
    pub retaliation_used: bool,
    pub iid: i32,
    /// What effects have added to its strength, for good (the Hunters' -N).
    pub strength_mod: i32,
    /// What effects have added to its mana cost while in hand (the Assassin's -1).
    pub cost_mod: i32,
    /// Made into its owner's hand by an effect both players watched (the Bird Egg's Flight 1s): known to the opponent.
    pub made: bool,
}

impl Unit {
    pub fn new(card: CardId, owner: Player, iid: i32) -> Unit {
        Unit { card, owner, retaliation_used: false, iid, strength_mod: 0, cost_mod: 0, made: false }
    }
}

const NO_UNIT: Unit = Unit { card: 0, owner: 0, retaliation_used: false, iid: -1, strength_mod: 0, cost_mod: 0, made: false };

/// The board: each tile's stack of units, bottom to top; the top unit holds the tile. A stack is deeper than one only
/// between a cover and the removal of what it covered, so the tops
/// are a flat array and everything beneath them one short list. `order` is the order the occupied tiles were taken in,
/// which the rules read (the animals at 0 strength are removed in it).
#[derive(Debug)]
pub struct Board {
    tops: [Unit; MAX_TILES],
    /// The occupied tiles, as bits.
    pub occ: u64,
    /// player -> the tiles whose top unit is theirs.
    pub own: [u64; 2],
    order: [Tile; MAX_TILES],
    n_order: u8,
    /// (tile, unit) for every unit beneath a top, each tile's bottom to top in list order.
    buried: SmallVec<[(Tile, Unit); 4]>,
}

/// Copied as memory: the derived clone copies a short list item by item, which a search's millions of copies feel.
impl Clone for Board {
    #[inline]
    fn clone(&self) -> Board {
        Board { tops: self.tops, occ: self.occ, own: self.own, order: self.order, n_order: self.n_order, buried: SmallVec::from_slice(&self.buried) }
    }

    /// Into a board already made: the taken order and the list beneath only as long as they are.
    #[inline]
    fn clone_from(&mut self, src: &Board) {
        // a top is read only while its tile is occupied: the slots past the highest occupied tile need no copy
        let k = 64 - src.occ.leading_zeros() as usize;
        if k <= 16 {
            // a fixed-size copy, done inline: the square board's every tile, and most positions of larger ones
            self.tops[..16].copy_from_slice(&src.tops[..16]);
        } else {
            self.tops[..k].copy_from_slice(&src.tops[..k]);
        }
        self.occ = src.occ;
        self.own = src.own;
        let n = src.n_order as usize;
        self.order[..n].copy_from_slice(&src.order[..n]);
        self.n_order = src.n_order;
        copy_list(&mut self.buried, &src.buried);
    }
}

/// `dst` made equal to `src`, copying only the items it holds and keeping `dst`'s own buffer.
#[inline]
fn copy_list<A: smallvec::Array>(dst: &mut SmallVec<A>, src: &SmallVec<A>)
where
    A::Item: Copy,
{
    let n = src.len();
    dst.clear();
    dst.reserve(n);
    // SAFETY: `dst` holds room for `n` items after the reserve, the two lists are distinct, and the items are Copy.
    unsafe {
        std::ptr::copy_nonoverlapping(src.as_ptr(), dst.as_mut_ptr(), n);
        dst.set_len(n);
    }
}

impl Default for Board {
    fn default() -> Board {
        Board { tops: [NO_UNIT; MAX_TILES], occ: 0, own: [0; 2], order: [0; MAX_TILES], n_order: 0, buried: SmallVec::new() }
    }
}

impl Board {
    #[inline]
    pub fn top(&self, t: Tile) -> Option<Unit> {
        if self.occ >> t & 1 == 1 { Some(self.tops[t as usize]) } else { None }
    }

    #[inline]
    pub fn top_mut(&mut self, t: Tile) -> Option<&mut Unit> {
        if self.occ >> t & 1 == 1 { Some(&mut self.tops[t as usize]) } else { None }
    }

    #[inline]
    pub fn owner_of(&self, t: Tile) -> Option<Player> {
        if self.own[0] >> t & 1 == 1 { Some(0) } else if self.own[1] >> t & 1 == 1 { Some(1) } else { None }
    }

    fn set_top(&mut self, t: Tile, u: Unit) {
        self.tops[t as usize] = u;
        self.occ |= 1 << t;
        self.own[u.owner as usize] |= 1 << t;
        self.own[other(u.owner) as usize] &= !(1 << t);
    }

    /// `u` lands on `t`, on top of whatever stands there.
    pub fn push(&mut self, t: Tile, u: Unit) {
        if self.occ >> t & 1 == 1 {
            self.buried.push((t, self.tops[t as usize]));
        } else {
            self.order[self.n_order as usize] = t;
            self.n_order += 1;
        }
        self.set_top(t, u);
    }

    /// The occupied tiles, in the order they were taken.
    #[inline]
    pub fn tiles(&self) -> &[Tile] {
        &self.order[..self.n_order as usize]
    }

    #[inline]
    pub fn has_buried(&self) -> bool {
        !self.buried.is_empty()
    }

    /// Every unit beneath a top, in no particular order.
    #[inline]
    pub fn buried_units(&self) -> impl Iterator<Item = &Unit> {
        self.buried.iter().map(|(_, u)| u)
    }

    /// The units beneath the top of `t`, bottom first.
    pub fn buried_of(&self, t: Tile) -> SmallVec<[Unit; 4]> {
        self.buried.iter().filter(|(bt, _)| *bt == t).map(|(_, u)| *u).collect()
    }

    /// The unit directly beneath the top of `t`.
    pub fn under_mut(&mut self, t: Tile) -> Option<&mut Unit> {
        self.buried.iter_mut().rev().find(|(bt, _)| *bt == t).map(|(_, u)| u)
    }

    /// The stack on `t`, bottom to top.
    pub fn stack(&self, t: Tile) -> SmallVec<[Unit; 4]> {
        let mut s = self.buried_of(t);
        if let Some(u) = self.top(t) {
            s.push(u);
        }
        s
    }

    pub fn depth(&self, t: Tile) -> usize {
        if self.occ >> t & 1 == 0 {
            return 0;
        }
        1 + self.buried.iter().filter(|(bt, _)| *bt == t).count()
    }

    /// Every unit on the board with its tile: tiles in the order they were taken, each stack bottom to top.
    pub fn units(&self) -> SmallVec<[(Tile, Unit); 24]> {
        let mut out = SmallVec::new();
        for &t in self.tiles() {
            if !self.buried.is_empty() {
                for (bt, u) in &self.buried {
                    if *bt == t {
                        out.push((t, *u));
                    }
                }
            }
            out.push((t, self.tops[t as usize]));
        }
        out
    }

    pub fn find(&self, iid: i32) -> Option<(Tile, Unit)> {
        let mut m = self.occ;
        while m != 0 {
            let t = m.trailing_zeros() as Tile;
            m &= m - 1;
            if self.tops[t as usize].iid == iid {
                return Some((t, self.tops[t as usize]));
            }
        }
        self.buried.iter().find(|(_, u)| u.iid == iid).map(|(t, u)| (*t, *u))
    }

    /// Whether the unit `iid` is anywhere on the board.
    pub fn holds(&self, iid: i32) -> bool {
        self.find(iid).is_some()
    }

    /// Take the unit `iid` out of the stack on `t`, wherever in it; a tile left empty is no longer taken.
    pub fn remove(&mut self, t: Tile, iid: i32) -> Option<Unit> {
        if self.occ >> t & 1 == 0 {
            return None;
        }
        let top = self.tops[t as usize];
        if top.iid == iid {
            self.own[top.owner as usize] &= !(1 << t);
            match self.buried.iter().rposition(|(bt, _)| *bt == t) {
                Some(i) => {
                    let (_, below) = self.buried.remove(i);
                    self.set_top(t, below);
                }
                None => {
                    self.occ &= !(1 << t);
                    let n = self.n_order as usize;
                    let at = self.order[..n].iter().position(|&x| x == t).expect("an occupied tile is in the order");
                    self.order.copy_within(at + 1..n, at);
                    self.n_order -= 1;
                }
            }
            return Some(top);
        }
        let i = self.buried.iter().position(|(bt, u)| *bt == t && u.iid == iid)?;
        Some(self.buried.remove(i).1)
    }
}

/// A choice a player makes while an effect resolves, as an action carries it.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Choice {
    /// Decline an optional choice ("__skip__").
    Skip,
    /// A unit's instance id (the mulligan).
    Iid(i32),
    Tile(Tile),
    /// "deck:K", the Kth card from the top of the chooser's deck (Scout).
    Deck(u8),
}

pub type Tiles = SmallVec<[Tile; 6]>;

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum StepKind {
    Mulligan { player: Player, returned: SmallVec<[CardId; 4]> },
    CoverRemove { cr: Tile },
    HungryFood { player: Player, prey: i32 },
    GainFood { player: Player, amount: i32 },
    /// A leader's passive fires: its event, on the stack just above what it does.
    LeaderTrigger { player: Player, card: CardId },
    Draw { player: Player, n: i32 },
    DrawIfGone { player: Player, prey: i32, n: i32 },
    /// `from`: where in the deck the cards being looked at came from (indices before any was lifted), bottom first;
    /// empty until the look begins.
    Scout { player: Player, from: SmallVec<[u8; 4]> },
    PlaceToken { player: Player, card: CardId, options: Tiles },
    ToHand { player: Player, card: CardId, n: i32 },
    RemoveIid { iid: i32, by_player: Option<Player> },
    RemoveChoice { chooser: Player, options: Tiles, optional: bool },
    WeakenChoice { chooser: Player, options: Tiles, amount: i32 },
    /// The player picks an ally to give +N strength, for good (the Angel Warrior's power).
    BuffChoice { chooser: Player, options: Tiles, amount: i32 },
    /// The player picks a card in their hand to give +N strength, for good (the Rogue's power).
    HandBuffChoice { chooser: Player, options: SmallVec<[i32; 12]>, amount: i32 },
    /// One "draw a card" while Reno leads: a Scout if their deck then holds no duplicates, else a draw.
    DrawOrScout { player: Player, from: SmallVec<[u8; 4]> },
}

/// One step of an effect waiting on the stack. `by_card` and `by_iid` name the card and the very unit whose effect it is.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Step {
    pub by_card: Option<CardId>,
    pub by_iid: Option<i32>,
    pub choice: Option<Choice>,
    pub kind: StepKind,
}

impl Step {
    pub fn new(kind: StepKind) -> Step {
        Step { by_card: None, by_iid: None, choice: None, kind }
    }

    pub fn by(kind: StepKind, card: CardId) -> Step {
        Step { by_card: Some(card), by_iid: None, choice: None, kind }
    }

    pub fn by_unit(kind: StepKind, u: &Unit) -> Step {
        Step { by_card: Some(u.card), by_iid: Some(u.iid), choice: None, kind }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum Options {
    Iids(SmallVec<[i32; 12]>),
    Tiles(Tiles),
    /// "deck:0" .. "deck:N-1"
    Deck(u8),
}

/// The choice the game waits on.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Pending {
    pub chooser: Player,
    pub optional: bool,
    pub mulligan: bool,
    pub options: Options,
}

/// A delayed step: Poison's removal, at the start of its owner's next turn.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Scheduled {
    pub iid: i32,
    pub owner: Player,
    pub remaining: i32,
    pub step: Step,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CapKind {
    Actions,
    EffectSteps,
}

impl CapKind {
    pub fn name(self) -> &'static str {
        match self {
            CapKind::Actions => "actions",
            CapKind::EffectSteps => "effect_steps",
        }
    }
}

/// A turn that a safety cap ended.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Cap {
    pub cap: CapKind,
    pub player: Player,
    pub turn: i32,
    pub cards: Vec<CardId>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Reason {
    Food,
    Starved,
    MaxTurns,
    Concede,
    Timeout,
}

impl Reason {
    pub fn name(self) -> &'static str {
        match self {
            Reason::Food => "food",
            Reason::Starved => "starved",
            Reason::MaxTurns => "max_turns",
            Reason::Concede => "concede",
            Reason::Timeout => "timeout",
        }
    }

    pub fn from(s: &str) -> Result<Reason, String> {
        Ok(match s {
            "food" => Reason::Food,
            "starved" => Reason::Starved,
            "max_turns" => Reason::MaxTurns,
            "concede" => Reason::Concede,
            "timeout" => Reason::Timeout,
            _ => return Err(format!("unknown result reason {s:?}")),
        })
    }
}

/// The game's outcome; `winner` None is a draw.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct GameResult {
    pub winner: Option<Player>,
    pub reason: Reason,
}

pub type Hand = SmallVec<[Unit; 12]>;
pub type Deck = SmallVec<[CardId; 32]>;

#[derive(Debug)]
pub struct State {
    pub g: Arc<Game>,
    pub board: Board,
    pub hands: [Hand; 2],
    /// player -> their deck; the top is the end.
    pub decks: [Deck; 2],
    pub starting_decks: Arc<[Vec<CardId>; 2]>,
    /// Shared and public, with each card's owner in step (255: unknown).
    pub remove_pile: SmallVec<[CardId; 64]>,
    pub pile_owners: SmallVec<[u8; 64]>,
    /// player -> every card an effect made into their hand, in the order made: public, so their hidden cards are
    /// their decklist and these, less what both players have seen.
    pub made: [SmallVec<[CardId; 4]>; 2],
    pub leaders: [Option<CardId>; 2],
    pub food: [i32; 2],
    pub current: Player,
    pub first_player: Player,
    pub rng: CowRng,
    pub turn_counter: i32,
    /// This turn's mana spent so far.
    pub mana_spent: i32,
    /// Every action applied this turn, choices included (Config.max_actions_per_turn).
    pub applied_this_turn: i32,
    /// The cards its player has played from hand this turn.
    pub played_this_turn: i32,
    pub power_used: bool,
    /// Off each player's leader power, for good (the Sage's card).
    pub power_discount: [i32; 2],
    /// Fatigue: the cards each player has tried to draw from their own empty deck. The next one costs them one more
    /// food than this.
    pub fatigue: [i32; 2],
    /// The food each player has lost this game, to raids and fatigue (the Burn Djinn).
    pub food_lost: [i32; 2],
    /// The food each player's regions have produced this game (the Food Djinn).
    pub food_produced: [i32; 2],
    /// The raids each player has made this game (the Raider's power).
    pub raids: [i32; 2],
    /// The regions that produce no food for the rest of the game, a bit for each in the map's order (the Scorch).
    pub scorched: u64,
    /// What each player's Nightmare has grown by, wherever he is ("Dusk: Gain +1 strength.").
    pub leeroy_growth: [i32; 2],
    /// Each player's mana crystals: they gain one at the start of each of their turns, up to the cap, and have that much
    /// mana on it (the Mana Eater starts with some; his card destroys his).
    pub crystals: [i32; 2],
    /// The mana each player gains on top of their crystals on their next turn (the Mana Eater's power).
    pub next_mana: [i32; 2],
    /// How many times each player has used their leader's power this game (the Pyromancer's upgrades).
    pub power_uses: [i32; 2],
    pub effect_steps_this_turn: i32,
    pub caps: Vec<Cap>,
    pub next_iid: i32,
    pub effect_stack: SmallVec<[Step; 4]>,
    pub pending: Option<Pending>,
    pub scheduled: SmallVec<[Scheduled; 1]>,
    pub result: Option<GameResult>,
    /// What happened, in order, when recording is on. Never saved; a clone starts empty.
    pub events: Events,
    /// The card whose effect is running, and the very unit when known: stamped on each event.
    pub cause: Option<CardId>,
    pub cause_iid: Option<i32>,
}

/// Copied as memory where it can be (the lists of plain values), for the same reason as the board; every field is named,
/// so a new one cannot be forgotten.
impl Clone for State {
    #[inline]
    fn clone(&self) -> State {
        State {
            g: self.g.clone(),
            board: self.board.clone(),
            hands: [SmallVec::from_slice(&self.hands[0]), SmallVec::from_slice(&self.hands[1])],
            decks: [SmallVec::from_slice(&self.decks[0]), SmallVec::from_slice(&self.decks[1])],
            starting_decks: self.starting_decks.clone(),
            remove_pile: SmallVec::from_slice(&self.remove_pile),
            pile_owners: SmallVec::from_slice(&self.pile_owners),
            made: [SmallVec::from_slice(&self.made[0]), SmallVec::from_slice(&self.made[1])],
            leaders: self.leaders,
            food: self.food,
            current: self.current,
            first_player: self.first_player,
            rng: self.rng.clone(),
            turn_counter: self.turn_counter,
            mana_spent: self.mana_spent,
            applied_this_turn: self.applied_this_turn,
            played_this_turn: self.played_this_turn,
            power_used: self.power_used,
            power_discount: self.power_discount,
            fatigue: self.fatigue,
            food_lost: self.food_lost,
            food_produced: self.food_produced,
            raids: self.raids,
            scorched: self.scorched,
            leeroy_growth: self.leeroy_growth,
            crystals: self.crystals,
            next_mana: self.next_mana,
            power_uses: self.power_uses,
            effect_steps_this_turn: self.effect_steps_this_turn,
            caps: self.caps.clone(),
            next_iid: self.next_iid,
            effect_stack: self.effect_stack.clone(),
            pending: self.pending.clone(),
            scheduled: self.scheduled.clone(),
            result: self.result,
            events: self.events.clone(),
            cause: self.cause,
            cause_iid: self.cause_iid,
        }
    }

    /// Into a position already made, the same as a fresh clone: what a search does for every line it follows, reusing
    /// one position's memory for the next. Lists copy only what they hold, and a shared part (the game, the starting
    /// decks, the generator) is not touched when both already share it.
    fn clone_from(&mut self, src: &State) {
        if !Arc::ptr_eq(&self.g, &src.g) {
            self.g = src.g.clone();
        }
        self.board.clone_from(&src.board);
        for p in 0..2 {
            copy_list(&mut self.hands[p], &src.hands[p]);
            copy_list(&mut self.decks[p], &src.decks[p]);
        }
        if !Arc::ptr_eq(&self.starting_decks, &src.starting_decks) {
            self.starting_decks = src.starting_decks.clone();
        }
        copy_list(&mut self.remove_pile, &src.remove_pile);
        copy_list(&mut self.pile_owners, &src.pile_owners);
        copy_list(&mut self.made[0], &src.made[0]);
        copy_list(&mut self.made[1], &src.made[1]);
        self.leaders = src.leaders;
        self.food = src.food;
        self.current = src.current;
        self.first_player = src.first_player;
        self.rng.clone_from(&src.rng);
        self.turn_counter = src.turn_counter;
        self.mana_spent = src.mana_spent;
        self.applied_this_turn = src.applied_this_turn;
        self.played_this_turn = src.played_this_turn;
        self.power_used = src.power_used;
        self.power_discount = src.power_discount;
        self.fatigue = src.fatigue;
        self.food_lost = src.food_lost;
        self.food_produced = src.food_produced;
        self.raids = src.raids;
        self.scorched = src.scorched;
        self.leeroy_growth = src.leeroy_growth;
        self.crystals = src.crystals;
        self.next_mana = src.next_mana;
        self.power_uses = src.power_uses;
        self.effect_steps_this_turn = src.effect_steps_this_turn;
        if !(self.caps.is_empty() && src.caps.is_empty()) {
            self.caps.clone_from(&src.caps);
        }
        self.next_iid = src.next_iid;
        if !(self.effect_stack.is_empty() && src.effect_stack.is_empty()) {
            self.effect_stack.clone_from(&src.effect_stack);
        }
        if self.pending.is_some() || src.pending.is_some() {
            self.pending.clone_from(&src.pending);
        }
        if !(self.scheduled.is_empty() && src.scheduled.is_empty()) {
            self.scheduled.clone_from(&src.scheduled);
        }
        self.result = src.result;
        self.events.on = src.events.on; // a clone starts with no events on record
        self.events.list.clear();
        self.cause = src.cause;
        self.cause_iid = src.cause_iid;
    }
}

pub const NO_OWNER: u8 = 255;

impl State {
    #[inline]
    pub fn cfg(&self) -> &Config {
        &self.g.cfg
    }

    #[inline]
    pub fn card(&self, c: CardId) -> &Card {
        self.g.cards.get(c)
    }

    #[inline]
    pub fn emit(&mut self, e: Ev) {
        if self.events.on {
            let cause_iid = if self.cause.is_some() { self.cause_iid } else { None };
            self.events.push(self.cause, cause_iid, e);
        }
    }

    pub fn pile_add(&mut self, card: CardId, owner: Player) {
        self.remove_pile.push(card);
        self.pile_owners.push(owner);
    }

    pub fn new_iid(&mut self) -> i32 {
        let iid = self.next_iid;
        self.next_iid += 1;
        iid
    }

    /// Move up to n cards from the top of `player`'s deck into their hand; the instances drawn.
    pub fn draw(&mut self, player: Player, n: i32) -> SmallVec<[Unit; 4]> {
        let mut drawn = SmallVec::new();
        let p = player as usize;
        for _ in 0..n.max(0).min(self.decks[p].len() as i32) {
            let card = self.decks[p].pop().unwrap();
            let u = Unit::new(card, player, self.new_iid());
            self.hands[p].push(u);
            drawn.push(u);
        }
        drawn
    }

    /// The tiles `player` holds that are connected to their base through their own animals, as bits.
    pub fn connected_occupied(&self, player: Player) -> u64 {
        let own = self.board.own[player as usize];
        let mut seen = self.g.map.hq_front[player as usize] & own;
        let mut frontier = seen;
        while frontier != 0 {
            let mut next = 0u64;
            let mut m = frontier;
            while m != 0 {
                let t = m.trailing_zeros() as usize;
                m &= m - 1;
                next |= self.g.map.nb_mask[t];
            }
            frontier = next & own & !seen;
            seen |= frontier;
        }
        seen
    }

    /// The tiles `player` may place on without Flight: their base, and every tile held or touched by their connected
    /// animals (`occ`).
    pub fn connectable(&self, player: Player, occ: u64) -> u64 {
        let mut out = self.g.map.hq_front[player as usize] | occ;
        let mut m = occ;
        while m != 0 {
            let t = m.trailing_zeros() as usize;
            m &= m - 1;
            out |= self.g.map.nb_mask[t];
        }
        out
    }

    /// The seat that must act next: the pending chooser mid-resolution, else the current player.
    pub fn player_to_act(&self) -> Player {
        match &self.pending {
            Some(p) => p.chooser,
            None => self.current,
        }
    }

    /// An independent copy with no events on record.
    pub fn fork(&self) -> State {
        let mut s = self.clone();
        s.cause = None;
        s.cause_iid = None;
        s
    }

    pub fn leads(&self, player: Player, leader: Option<CardId>) -> bool {
        leader.is_some() && self.leaders[player as usize] == leader
    }

    /// A fresh game: both decks shuffled, the first player by coin flip (or `first_player`), the opening hands dealt and
    /// the mulligan waiting. `seed_abs` is the absolute value of the seed, as CPython's `random.Random(seed)` reads it.
    pub fn new_game(g: Arc<Game>, deck_a: &[CardId], deck_b: &[CardId], seed_abs: u128, first_player: Option<Player>,
                    leaders: [Option<CardId>; 2]) -> Result<State, String> {
        let mut rng = PyRandom::seeded_abs(seed_abs);
        let mut decks: [Deck; 2] = [deck_a.iter().copied().collect(), deck_b.iter().copied().collect()];
        rng.shuffle(&mut decks[0]);
        rng.shuffle(&mut decks[1]);
        let coin_flip: Player = if rng.random() < 0.5 { 0 } else { 1 };
        let first = first_player.unwrap_or(coin_flip);
        let second = other(first);
        let cfg = g.cfg.clone();
        let mut st = State {
            board: Board::default(),
            hands: [Hand::new(), Hand::new()],
            decks,
            starting_decks: Arc::new([deck_a.to_vec(), deck_b.to_vec()]),
            remove_pile: SmallVec::new(),
            pile_owners: SmallVec::new(),
            made: [SmallVec::new(), SmallVec::new()],
            leaders: [None, None],
            food: [cfg.start_food, cfg.start_food],
            current: first,
            first_player: first,
            rng: CowRng::new(rng),
            turn_counter: 0,
            mana_spent: 0,
            applied_this_turn: 0,
            played_this_turn: 0,
            power_used: false,
            power_discount: [0, 0],
            fatigue: [0, 0],
            food_lost: [0, 0],
            food_produced: [0, 0],
            raids: [0, 0],
            scorched: 0,
            leeroy_growth: [0, 0],
            crystals: [0, 0],
            next_mana: [0, 0],
            power_uses: [0, 0],
            effect_steps_this_turn: 0,
            caps: Vec::new(),
            next_iid: 0,
            effect_stack: SmallVec::new(),
            pending: None,
            scheduled: SmallVec::new(),
            result: None,
            events: Events::default(),
            cause: None,
            cause_iid: None,
            g,
        };
        for p in 0..2u8 {
            let Some(lid) = leaders[p as usize] else { continue };
            if !st.card(lid).beh.leader {
                return Err(format!("{:?} is not a leader", st.g.cards.name_of(lid)));
            }
            if !st.decks[p as usize].contains(&lid) {
                return Err(format!("the leader {:?} must be in its deck", st.g.cards.name_of(lid)));
            }
            st.leaders[p as usize] = Some(lid);
        }
        for p in 0..2u8 {
            // Nightmare "starts on the bottom of your deck"; the Mana Eater starts "with 0 cards but 3 empty mana crystals"
            st.bottom_nightmare(p);
            if st.leads(p, st.g.named.mana_eater) {
                st.crystals[p as usize] = cfg.mana_eater_start_crystals.min(cfg.mana_cap);
            }
        }
        let opening = |st: &State, p: Player, n: i32| if st.leads(p, st.g.named.mana_eater) { 0 } else { n };
        let (n_first, n_second) = (opening(&st, first, cfg.first_player_opening_draw), opening(&st, second, cfg.second_player_opening_draw));
        st.draw(first, n_first);
        st.draw(second, n_second);
        if cfg.mulligan {
            for player in [second, first] {
                if !st.hands[player as usize].is_empty() {
                    st.effect_stack.push(Step::new(StepKind::Mulligan { player, returned: SmallVec::new() }));
                }
            }
            if let Some(top) = st.effect_stack.last() {
                let StepKind::Mulligan { player: chooser, .. } = top.kind else { unreachable!() };
                st.pending = Some(Pending {
                    chooser,
                    optional: true,
                    mulligan: true,
                    options: Options::Iids(st.hands[chooser as usize].iter().map(|u| u.iid).collect()),
                });
            }
        }
        if st.effect_stack.is_empty() {
            // no mulligan: the first turn begins now, with its crystal and its card (the mulligan's end does it otherwise)
            st.begin_turn_mana(first);
            st.draw(first, cfg.turn_draw_count);
        }
        Ok(st)
    }

    /// Nightmare to the bottom of `player`'s deck while he leads it ("Nightmare starts on the bottom of your deck."): as
    /// the game's decks are dealt, and again after a mulligan shuffles the deck.
    pub fn bottom_nightmare(&mut self, player: Player) {
        let Some(n) = self.g.named.raider else { return };
        if !self.leads(player, Some(n)) {
            return;
        }
        let d = &mut self.decks[player as usize];
        if let Some(i) = d.iter().position(|&c| c == n) {
            let card = d.remove(i);
            d.insert(0, card); // the top is the end
        }
    }

    /// `player`'s turn begins: a crystal more, up to the cap, all of them full, and the mana the Mana Eater's power put
    /// aside for this turn on top.
    pub fn begin_turn_mana(&mut self, player: Player) {
        let p = player as usize;
        self.crystals[p] = (self.crystals[p] + 1).min(self.cfg().mana_cap);
        self.mana_spent = -self.next_mana[p];
        self.next_mana[p] = 0;
    }
}
