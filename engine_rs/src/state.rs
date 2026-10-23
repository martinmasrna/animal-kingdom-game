//! The position: a port of engine/state.py. Crossroads, cards and players are indexes; the board keeps the Python
//! dict's insertion order (effects iterate it), hands and decks are lists (hand order and deck top matter), and the
//! effect machinery (stack, pending, scheduled, turn flags) is plain `Value` data shaped as the Python dicts are.

use std::collections::BTreeSet;
use std::sync::Arc;

use rustc_hash::FxHashMap;
use serde_json as sj;
use smallvec::SmallVec;

pub type Stack = SmallVec<[Unit; 4]>;

/// What the board says at a glance, recomputed whenever a unit lands, leaves or changes card: the top-owner masks,
/// the den-connected masks, the family auras on top and whether a side has a keyword aura on top.
#[derive(Clone, Copy, Debug, Default)]
pub struct BoardCache {
    pub mine: [u32; 2],
    pub conn: [u32; 2],
    pub aura: [(Player, i64, u8); 4],
    pub aura_n: u8,
    pub kw_aura: [bool; 2],
}
pub type Hand = SmallVec<[Unit; 12]>;
pub type Deck = SmallVec<[CardId; 32]>;

use crate::data::*;
use crate::rng::PyRandom;
use crate::value::{Map, Value};

#[macro_export]
macro_rules! emit {
    ($st:expr, $e:expr, $m:expr) => {
        if $st.record_events {
            $st.emit($e, $m);
        }
    };
}

#[derive(Clone, Copy, Debug)]
pub struct Unit {
    pub card: CardId,
    pub owner: Player,
    pub iid: i64,
    pub placed_on_turn: i32,
    pub strength_counter: i32,
    pub locked_until_turn: i32,
    pub retaliation_used: bool,
    pub play_seq: i32,
}

impl Unit {
    pub fn new(card: CardId, owner: Player, iid: i64) -> Unit {
        Unit { card, owner, iid, placed_on_turn: 0, strength_counter: 0, locked_until_turn: 0, retaliation_used: false, play_seq: 0 }
    }
}

/// The once-per-turn flags (Python's `turn_flags` dict), typed. `to_json`/`from_json` keep the dict's shape.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct TurnFlags {
    pub played: [Vec<(i64, CardId)>; 2],
    pub lost: [i32; 3],
    pub removed_any: bool,
    pub food_gained: [i32; 2],
    pub roamed: Vec<i64>,
    pub roams: [i32; 2],
    pub free_roams: [i32; 2],
    pub free_roams_used: [i32; 2],
    pub free_roam_iid: Vec<(i64, i64)>,
    pub bonus_actions: [i32; 2],
    pub action_cap: [Option<i32>; 2],
    pub gain_str: Vec<i64>,
    pub falstaff: [bool; 2],
    pub caps: Vec<(&'static str, i64)>,
}

impl TurnFlags {
    pub fn to_json(&self, st: &State) -> sj::Value {
        let mut m = sj::Map::default();
        for p in 0..2 {
            let pn = player_name(p as Player);
            if !self.played[p].is_empty() {
                m.insert(format!("played_{pn}"), sj::Value::Array(self.played[p].iter().map(|(iid, c)| sj::json!([iid, st.cname(*c)])).collect()));
            }
            if self.food_gained[p] != 0 {
                m.insert(format!("food_gained_{pn}"), sj::Value::from(self.food_gained[p]));
            }
            if self.roams[p] != 0 {
                m.insert(format!("roams_{pn}"), sj::Value::from(self.roams[p]));
            }
            if self.free_roams[p] != 0 {
                m.insert(format!("free_roams_{pn}"), sj::Value::from(self.free_roams[p]));
            }
            if self.free_roams_used[p] != 0 {
                m.insert(format!("free_roams_used_{pn}"), sj::Value::from(self.free_roams_used[p]));
            }
            if self.bonus_actions[p] != 0 {
                m.insert(format!("bonus_actions_{pn}"), sj::Value::from(self.bonus_actions[p]));
            }
            if let Some(c) = self.action_cap[p] {
                m.insert(format!("action_cap_{pn}"), sj::Value::from(c));
            }
            if self.falstaff[p] {
                m.insert(format!("falstaff_{pn}"), sj::Value::Bool(true));
            }
        }
        for p in 0..3 {
            if self.lost[p] != 0 {
                m.insert(format!("lost_{}", player_name(p as Player)), sj::Value::from(self.lost[p]));
            }
        }
        if self.removed_any {
            m.insert("removed_any".into(), sj::Value::Bool(true));
        }
        for iid in &self.roamed {
            m.insert(format!("roamed_{iid}"), sj::Value::Bool(true));
        }
        for (iid, n) in &self.free_roam_iid {
            m.insert(format!("free_roam_iid_{iid}"), sj::Value::from(*n));
        }
        for iid in &self.gain_str {
            m.insert(format!("gain_str_{iid}"), sj::Value::Bool(true));
        }
        for (flag, iid) in &self.caps {
            m.insert(format!("{flag}_{iid}"), sj::Value::Bool(true));
        }
        sj::Value::Object(m)
    }

    pub fn from_json(st: &State, v: &sj::Value) -> TurnFlags {
        let mut t = TurnFlags::default();
        let Some(obj) = v.as_object() else { return t };
        for (k, val) in obj {
            let p_of = |s: &str| -> usize { player_from(s) as usize };
            if let Some(rest) = k.strip_prefix("played_") {
                let p = p_of(rest);
                if p < 2 {
                    t.played[p] = val.as_array().map(|a| a.iter().map(|e| (e[0].as_i64().unwrap_or(0), st.card_id(e[1].as_str().unwrap_or("")).unwrap_or(0))).collect()).unwrap_or_default();
                }
            } else if let Some(rest) = k.strip_prefix("food_gained_") {
                t.food_gained[p_of(rest).min(1)] = val.as_i64().unwrap_or(0) as i32;
            } else if let Some(rest) = k.strip_prefix("lost_") {
                t.lost[p_of(rest)] = val.as_i64().unwrap_or(0) as i32;
            } else if k == "removed_any" {
                t.removed_any = val.as_bool().unwrap_or(false);
            } else if let Some(rest) = k.strip_prefix("roamed_") {
                if let Ok(i) = rest.parse::<i64>() {
                    t.roamed.push(i);
                }
            } else if let Some(rest) = k.strip_prefix("roams_") {
                t.roams[p_of(rest).min(1)] = val.as_i64().unwrap_or(0) as i32;
            } else if let Some(rest) = k.strip_prefix("free_roams_used_") {
                t.free_roams_used[p_of(rest).min(1)] = val.as_i64().unwrap_or(0) as i32;
            } else if let Some(rest) = k.strip_prefix("free_roam_iid_") {
                if let Ok(i) = rest.parse::<i64>() {
                    t.free_roam_iid.push((i, val.as_i64().unwrap_or(1)));
                }
            } else if let Some(rest) = k.strip_prefix("free_roams_") {
                t.free_roams[p_of(rest).min(1)] = val.as_i64().unwrap_or(0) as i32;
            } else if let Some(rest) = k.strip_prefix("bonus_actions_") {
                t.bonus_actions[p_of(rest).min(1)] = val.as_i64().unwrap_or(0) as i32;
            } else if let Some(rest) = k.strip_prefix("action_cap_") {
                t.action_cap[p_of(rest).min(1)] = val.as_i64().map(|x| x as i32);
            } else if let Some(rest) = k.strip_prefix("gain_str_") {
                if let Ok(i) = rest.parse::<i64>() {
                    t.gain_str.push(i);
                }
            } else if let Some(rest) = k.strip_prefix("falstaff_") {
                t.falstaff[p_of(rest).min(1)] = val.as_bool().unwrap_or(false);
            } else if k.starts_with("cap_") {
                if let Some((flag, iid)) = k.rsplit_once('_') {
                    if let Ok(i) = iid.parse::<i64>() {
                        t.caps.push((crate::value::intern(flag), i));
                    }
                }
            }
        }
        t
    }

    /// A canonical rendering for the search's observation key.
    pub fn canon_into(&self, st: &State, out: &mut String) {
        out.push_str(&self.to_json(st).to_string());
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct GameResult {
    pub winner: Option<Player>,
    pub reason: String,
}

/// The immutable data every state shares.
pub struct Game {
    pub cards: Cards,
    pub map: GameMap,
    pub cfg: Config,
    pub known: Known,
    /// Which hooks each card has (cards::hook_mask), by card index.
    pub hook_masks: Vec<u32>,
}

impl Game {
    pub fn new(cards: Cards, map: GameMap, cfg: Config) -> Game {
        let known = Known::build(&cards);
        let hook_masks = cards.list.iter().map(|c| crate::cards::hook_mask(&c.id)).collect();
        Game { cards, map, cfg, known, hook_masks }
    }
    pub fn has_hook(&self, card: CardId, hook: crate::cards::Hook) -> bool {
        self.hook_masks[card as usize] & (1 << hook as u32) != 0
    }
}

pub struct State {
    pub g: Arc<Game>,
    pub stacks: SmallVec<[Stack; 16]>, // by crossroad index
    pub order: SmallVec<[Cr; 16]>,     // occupied crossroads in insertion order (Python's dict order)
    pub hands: [Hand; 2],
    pub decks: [Deck; 2], // top = last
    pub starting_decks: [Deck; 2],
    pub remove_pile: Deck,
    pub pile_owners: SmallVec<[Option<Player>; 32]>,
    pub food: [i32; 2],
    pub current: Player,
    pub first_player: Player,
    pub rng: PyRandom,
    pub turn_counter: i32,
    pub units_placed_this_turn: i32,
    pub actions_taken_this_turn: i32,
    pub idle_turns: i32,
    pub next_iid: i64,
    pub play_seq: i32,
    pub effect_stack: Vec<Map>,
    pub pending: Option<Map>,
    pub scheduled: Vec<Map>,
    pub turn_flags: TurnFlags,
    pub card_strength_counters: [FxHashMap<CardId, i32>; 2],
    pub result: Option<GameResult>,
    pub inked: BTreeSet<i64>,
    pub roar_twice: [Option<i32>; 2],
    pub last_roar: [Option<CardId>; 2],
    pub jelly: [FxHashMap<CardId, (i32, i32)>; 2],
    /// Whether `jelly[p]` exists at all (Python keeps the player's dict once the legendary Bee roared, empty or not).
    pub jelly_set: [bool; 2],
    pub cache: BoardCache,
    pub events: Vec<Map>,
    pub cause: Option<CardId>,
    pub cause_iid: Option<i64>,
    pub record_events: bool,
}

impl Clone for State {
    /// An independent copy. Events are not recorded on a copy: the search clones a position for every line it imagines
    /// and nothing reads a copy's events (the live game's are read by the server).
    fn clone(&self) -> State {
        State {
            g: self.g.clone(),
            stacks: self.stacks.clone(),
            order: self.order.clone(),
            hands: self.hands.clone(),
            decks: self.decks.clone(),
            starting_decks: self.starting_decks.clone(),
            remove_pile: self.remove_pile.clone(),
            pile_owners: self.pile_owners.clone(),
            food: self.food,
            current: self.current,
            first_player: self.first_player,
            rng: self.rng.clone(),
            turn_counter: self.turn_counter,
            units_placed_this_turn: self.units_placed_this_turn,
            actions_taken_this_turn: self.actions_taken_this_turn,
            idle_turns: self.idle_turns,
            next_iid: self.next_iid,
            play_seq: self.play_seq,
            effect_stack: self.effect_stack.clone(),
            pending: self.pending.clone(),
            scheduled: self.scheduled.clone(),
            turn_flags: self.turn_flags.clone(),
            card_strength_counters: self.card_strength_counters.clone(),
            result: self.result.clone(),
            inked: self.inked.clone(),
            roar_twice: self.roar_twice,
            last_roar: self.last_roar,
            jelly: self.jelly.clone(),
            jelly_set: self.jelly_set,
            cache: self.cache,
            events: Vec::new(),
            cause: None,
            cause_iid: None,
            record_events: false,
        }
    }
}

impl State {
    // ---------------------------------------------------------------- shared data
    pub fn card(&self, id: CardId) -> &Card {
        self.g.cards.get(id)
    }
    pub fn cfg(&self) -> &Config {
        &self.g.cfg
    }
    pub fn map(&self) -> &GameMap {
        &self.g.map
    }
    pub fn card_id(&self, name: &str) -> Option<CardId> {
        self.g.cards.id_of(name)
    }
    pub fn cname(&self, id: CardId) -> &'static str {
        self.g.cards.name_of(id)
    }
    pub fn crname(&self, cr: Cr) -> &'static str {
        self.g.map.name(cr)
    }

    // ---------------------------------------------------------------- events
    pub fn emit(&mut self, e: &'static str, fields: Map) {
        if !self.record_events {
            return;
        }
        let mut m = Map::default();
        m.insert("e".into(), Value::s(e));
        for (k, v) in fields {
            m.insert(k, v);
        }
        if let Some(c) = self.cause {
            m.insert("cause".into(), Value::s(self.cname(c)));
            if let Some(i) = self.cause_iid {
                m.insert("cause_iid".into(), Value::Int(i));
            }
        }
        self.events.push(m);
    }

    // ---------------------------------------------------------------- the Remove Pile
    pub fn pile_add(&mut self, card: CardId, owner: Option<Player>) {
        self.remove_pile.push(card);
        self.pile_owners.push(owner);
    }
    pub fn pile_cards_of(&self, owner: Player) -> Vec<CardId> {
        self.remove_pile.iter().zip(self.pile_owners.iter()).filter(|(_, o)| **o == Some(owner)).map(|(c, _)| *c).collect()
    }
    pub fn pile_take(&mut self, card: CardId, owner: Option<Player>) -> bool {
        for i in (0..self.remove_pile.len()).rev() {
            if self.remove_pile[i] == card && (owner.is_none() || self.pile_owners[i] == owner || self.pile_owners[i].is_none()) {
                self.remove_pile.remove(i);
                self.pile_owners.remove(i);
                return true;
            }
        }
        false
    }

    pub fn stamp_played(&mut self, unit: &mut Unit) {
        self.play_seq += 1;
        unit.play_seq = self.play_seq;
    }
    pub fn new_iid(&mut self) -> i64 {
        let i = self.next_iid;
        self.next_iid += 1;
        i
    }

    // ---------------------------------------------------------------- card movement
    pub fn draw(&mut self, player: Player, n: i32) -> Vec<Unit> {
        let mut drawn = Vec::new();
        let take = (n.max(0) as usize).min(self.decks[player as usize].len());
        for _ in 0..take {
            let cid = self.decks[player as usize].pop().unwrap();
            let inst = self.deck_instance(player, cid);
            self.hands[player as usize].push(inst.clone());
            drawn.push(inst);
        }
        drawn
    }

    pub fn jelly_take(&mut self, player: Player, card: CardId) -> Option<i32> {
        let (left, counter) = match self.jelly[player as usize].get(&card) {
            Some(v) => *v,
            None => return None,
        };
        if left == 0 {
            return None;
        }
        if left == 1 {
            self.jelly[player as usize].remove(&card);
        } else {
            self.jelly[player as usize].insert(card, (left - 1, counter));
        }
        Some(counter)
    }

    pub fn jelly_counter(&self, player: Player, card: CardId) -> i32 {
        let base = self.card(card).base.unwrap_or(0);
        self.cfg().jelly_strength - base - self.growth(player, card)
    }

    pub fn growth(&self, player: Player, card: CardId) -> i32 {
        if player > B {
            return 0;
        }
        *self.card_strength_counters[player as usize].get(&card).unwrap_or(&0)
    }

    pub fn deck_instance(&mut self, player: Player, card: CardId) -> Unit {
        let iid = self.new_iid();
        let mut inst = Unit::new(card, player, iid);
        if let Some(c) = self.jelly_take(player, card) {
            inst.strength_counter = c;
        }
        inst
    }

    pub fn add_to_hand(&mut self, player: Player, card: CardId, strength_counter: i32) -> Unit {
        let iid = self.new_iid();
        let mut inst = Unit::new(card, player, iid);
        inst.strength_counter = strength_counter;
        self.hands[player as usize].push(inst.clone());
        let f = crate::vmap!("player" => Value::s(player_name(player)), "iid" => Value::Int(iid), "card" => Value::s(self.cname(card)));
        if self.record_events {
            self.emit("to_hand", f);
        }
        self.ensure_mates(player, Some(vec![inst.clone()]));
        inst
    }

    /// A card that brings its mate (the legendary Eagle) and has just entered `player`'s hand brings it unless it's
    /// there already; the whole hand when `entered` is None.
    pub fn ensure_mates(&mut self, player: Player, entered: Option<Vec<Unit>>) {
        let list: Vec<Unit> = entered.unwrap_or_else(|| self.hands[player as usize].to_vec());
        for u in list {
            let card = self.card(u.card);
            if let Some(mate) = card.mate {
                if card.status != "token" && !self.hands[player as usize].iter().any(|h| h.card == mate) {
                    self.add_to_hand(player, mate, 0);
                }
            }
        }
    }

    // ---------------------------------------------------------------- board
    pub fn stack(&self, cr: Cr) -> &[Unit] {
        &self.stacks[cr as usize]
    }
    pub fn occupied(&self, cr: Cr) -> bool {
        !self.stacks[cr as usize].is_empty()
    }
    pub fn top(&self, cr: Cr) -> Option<&Unit> {
        self.stacks[cr as usize].last()
    }
    pub fn top_mut(&mut self, cr: Cr) -> Option<&mut Unit> {
        self.stacks[cr as usize].last_mut()
    }
    pub fn owner_of(&self, cr: Cr) -> Option<Player> {
        self.top(cr).map(|u| u.owner)
    }
    /// Append a unit on `cr` (bottom..top), keeping the insertion order of occupied crossroads.
    pub fn push_unit(&mut self, cr: Cr, unit: Unit) {
        if self.stacks[cr as usize].is_empty() {
            self.order.push(cr);
        }
        self.stacks[cr as usize].push(unit);
        self.recache();
    }

    /// Recompute `cache` from the board.
    pub fn recache(&mut self) {
        let gm = &self.g.map;
        let mut c = BoardCache::default();
        for &cr in &self.order {
            let Some(top) = self.stacks[cr as usize].last() else { continue };
            if top.owner <= B {
                c.mine[top.owner as usize] |= 1 << cr;
                let card = self.g.cards.get(top.card);
                if card.family_aura != 0 && (c.aura_n as usize) < c.aura.len() {
                    c.aura[c.aura_n as usize] = (top.owner, top.iid, card.family_aura);
                    c.aura_n += 1;
                }
                if card.keyword_aura != 0 {
                    c.kw_aura[top.owner as usize] = true;
                }
            }
        }
        for p in 0..2 {
            let mine = c.mine[p];
            let mut seen = mine & gm.front_masks[p];
            let mut frontier = seen;
            while frontier != 0 {
                let cr = frontier.trailing_zeros() as Cr;
                frontier &= frontier - 1;
                for &nb in gm.neighbors(cr) {
                    let bit = 1u32 << nb;
                    if seen & bit == 0 && mine & bit != 0 {
                        seen |= bit;
                        frontier |= bit;
                    }
                }
            }
            c.conn[p] = seen;
        }
        self.cache = c;
    }
    pub fn insert_unit(&mut self, cr: Cr, at: usize, unit: Unit) {
        if self.stacks[cr as usize].is_empty() {
            self.order.push(cr);
        }
        let st = &mut self.stacks[cr as usize];
        let at = at.min(st.len());
        st.insert(at, unit);
        self.recache();
    }
    /// Take the unit with `iid` out of `cr`'s stack; the crossroad leaves the order when empty.
    pub fn take_unit(&mut self, cr: Cr, iid: i64) -> Option<Unit> {
        let st = &mut self.stacks[cr as usize];
        let pos = st.iter().position(|u| u.iid == iid)?;
        let u = st.remove(pos);
        if st.is_empty() {
            self.order.retain(|c| *c != cr);
        }
        self.recache();
        Some(u)
    }
    pub fn pop_top(&mut self, cr: Cr) -> Option<Unit> {
        let u = self.stacks[cr as usize].pop()?;
        if self.stacks[cr as usize].is_empty() {
            self.order.retain(|c| *c != cr);
        }
        self.recache();
        Some(u)
    }
    /// The crossroad and stack position of a unit on the board.
    pub fn find_unit(&self, iid: i64) -> Option<(Cr, usize)> {
        for &cr in &self.order {
            if let Some(p) = self.stacks[cr as usize].iter().position(|u| u.iid == iid) {
                return Some((cr, p));
            }
        }
        None
    }
    pub fn unit_at(&self, cr: Cr, pos: usize) -> &Unit {
        &self.stacks[cr as usize][pos]
    }
    pub fn unit_by_iid(&self, iid: i64) -> Option<&Unit> {
        self.find_unit(iid).map(|(cr, p)| &self.stacks[cr as usize][p])
    }
    pub fn unit_by_iid_mut(&mut self, iid: i64) -> Option<&mut Unit> {
        let (cr, p) = self.find_unit(iid)?;
        Some(&mut self.stacks[cr as usize][p])
    }
    /// An instance by iid: the board first, then both hands.
    pub fn find_instance_mut(&mut self, iid: i64) -> Option<&mut Unit> {
        if let Some((cr, p)) = self.find_unit(iid) {
            return Some(&mut self.stacks[cr as usize][p]);
        }
        for h in 0..2 {
            if let Some(p) = self.hands[h].iter().position(|u| u.iid == iid) {
                return Some(&mut self.hands[h][p]);
            }
        }
        None
    }
    pub fn find_instance(&self, iid: i64) -> Option<&Unit> {
        if let Some((cr, p)) = self.find_unit(iid) {
            return Some(&self.stacks[cr as usize][p]);
        }
        for h in 0..2 {
            if let Some(p) = self.hands[h].iter().position(|u| u.iid == iid) {
                return Some(&self.hands[h][p]);
            }
        }
        None
    }
    /// Top units in board order.
    pub fn tops(&self) -> impl Iterator<Item = (Cr, &Unit)> {
        self.order.iter().map(move |&cr| (cr, self.stacks[cr as usize].last().unwrap()))
    }
    /// Occupied crossroads in name order (Python's `sorted(state.board)`).
    pub fn sorted_occupied(&self) -> Vec<Cr> {
        self.g.map.sorted.iter().copied().filter(|&c| !self.stacks[c as usize].is_empty()).collect()
    }
    pub fn is_inked(&self, iid: i64) -> bool {
        !self.inked.is_empty() && self.inked.contains(&iid)
    }

    /// Player-occupied crossroads connected to the player's den (overview.md §8), as a bitmask.
    pub fn connected_occupied(&self, player: Player) -> u32 {
        if player > B {
            return 0;
        }
        self.cache.conn[player as usize]
    }
    /// The crossroads `player` tops, as a bitmask.
    pub fn owned_mask(&self, player: Player) -> u32 {
        if player > B {
            return 0;
        }
        self.cache.mine[player as usize]
    }

    pub fn is_connected(&self, player: Player, cr: Cr, occ: u32) -> bool {
        let gm = &self.g.map;
        if gm.in_front(player, cr) {
            return true;
        }
        if occ & (1 << cr) != 0 {
            return true;
        }
        gm.neighbors(cr).iter().any(|&nb| occ & (1 << nb) != 0)
    }

    pub fn player_to_act(&self) -> Player {
        if let Some(p) = &self.pending {
            return player_from(p.get("chooser").and_then(|v| v.as_str()).unwrap_or("A"));
        }
        self.current
    }

    pub fn decided(&self) -> bool {
        self.result.is_some()
    }

    // ---------------------------------------------------------------- serialisation
    fn unit_json(&self, u: &Unit) -> sj::Value {
        sj::json!({
            "card_id": self.cname(u.card), "owner": player_name(u.owner), "iid": u.iid,
            "placed_on_turn": u.placed_on_turn, "strength_counter": u.strength_counter,
            "locked_until_turn": u.locked_until_turn, "retaliation_used": u.retaliation_used, "play_seq": u.play_seq,
        })
    }

    fn unit_from(&self, d: &sj::Value) -> Unit {
        let card = self.card_id(d["card_id"].as_str().unwrap()).expect("unknown card in saved state");
        Unit {
            card,
            owner: player_from(d["owner"].as_str().unwrap()),
            iid: d["iid"].as_i64().unwrap(),
            placed_on_turn: d.get("placed_on_turn").and_then(|x| x.as_i64()).unwrap_or(0) as i32,
            strength_counter: d.get("strength_counter").and_then(|x| x.as_i64()).unwrap_or(0) as i32,
            locked_until_turn: d.get("locked_until_turn").and_then(|x| x.as_i64()).unwrap_or(0) as i32,
            retaliation_used: d.get("retaliation_used").and_then(|x| x.as_bool()).unwrap_or(false),
            play_seq: d.get("play_seq").and_then(|x| x.as_i64()).unwrap_or(0) as i32,
        }
    }

    pub fn to_json(&self) -> sj::Value {
        let mut board = sj::Map::default();
        for &cr in &self.order {
            board.insert(self.crname(cr).to_string(), sj::Value::Array(self.stacks[cr as usize].iter().map(|u| self.unit_json(u)).collect()));
        }
        let hands = |p: usize| sj::Value::Array(self.hands[p].iter().map(|u| self.unit_json(u)).collect());
        let deck = |d: &[CardId]| sj::Value::Array(d.iter().map(|c| sj::Value::String(self.cname(*c).to_string())).collect());
        let counters = |p: usize| {
            let mut m: Vec<(String, i32)> = self.card_strength_counters[p].iter().map(|(c, n)| (self.cname(*c).to_string(), *n)).collect();
            m.sort();
            sj::Value::Object(m.into_iter().map(|(k, v)| (k, sj::Value::from(v))).collect())
        };
        let jelly = |p: usize| {
            let mut m: Vec<(String, (i32, i32))> = self.jelly[p].iter().map(|(c, v)| (self.cname(*c).to_string(), *v)).collect();
            m.sort();
            sj::Value::Object(m.into_iter().map(|(k, (a, b))| (k, sj::json!([a, b]))).collect())
        };
        let mut roar_twice = sj::Map::default();
        for p in 0..2 {
            if let Some(t) = self.roar_twice[p] {
                roar_twice.insert(player_name(p as Player).to_string(), sj::Value::from(t));
            }
        }
        let mut last_roar = sj::Map::default();
        for p in 0..2 {
            if let Some(c) = self.last_roar[p] {
                last_roar.insert(player_name(p as Player).to_string(), sj::Value::String(self.cname(c).to_string()));
            }
        }
        let mut jelly_m = sj::Map::default();
        for p in 0..2 {
            if self.jelly_set[p] {
                jelly_m.insert(player_name(p as Player).to_string(), jelly(p));
            }
        }
        sj::json!({
            "map_id": self.g.map.id,
            "board": board,
            "hands": {"A": hands(0), "B": hands(1)},
            "decks": {"A": deck(&self.decks[0]), "B": deck(&self.decks[1])},
            "starting_decks": {"A": deck(&self.starting_decks[0]), "B": deck(&self.starting_decks[1])},
            "remove_pile": deck(&self.remove_pile),
            "food": {"A": self.food[0], "B": self.food[1]},
            "current": player_name(self.current),
            "first_player": player_name(self.first_player),
            "rng": {"version": 3, "state": self.rng.state_words(), "gauss": sj::Value::Null},
            "turn_counter": self.turn_counter,
            "units_placed_this_turn": self.units_placed_this_turn,
            "actions_taken_this_turn": self.actions_taken_this_turn,
            "idle_turns": self.idle_turns,
            "next_iid": self.next_iid,
            "play_seq": self.play_seq,
            "effect_stack": self.effect_stack.iter().map(|m| Value::Map(m.clone()).to_json()).collect::<Vec<_>>(),
            "pending": self.pending.as_ref().map(|m| Value::Map(m.clone()).to_json()).unwrap_or(sj::Value::Null),
            "scheduled": self.scheduled.iter().map(|m| Value::Map(m.clone()).to_json()).collect::<Vec<_>>(),
            "turn_flags": self.turn_flags.to_json(self),
            "card_strength_counters": {"A": counters(0), "B": counters(1)},
            "result": self.result.as_ref().map(|r| sj::json!({"winner": r.winner.map(player_name), "reason": r.reason})).unwrap_or(sj::Value::Null),
            "pile_owners": self.pile_owners.iter().map(|o| o.map(|p| sj::Value::String(player_name(p).to_string())).unwrap_or(sj::Value::Null)).collect::<Vec<_>>(),
            "inked": self.inked.iter().copied().collect::<Vec<i64>>(),
            "roar_twice": roar_twice,
            "last_roar": last_roar,
            "jelly": jelly_m,
        })
    }

    pub fn from_json(g: Arc<Game>, d: &sj::Value) -> State {
        let n = g.map.n();
        let mut st = State::blank(g.clone());
        let cid = |name: &str| g.cards.id_of(name).expect("unknown card in saved state");
        let cards_of = |v: &sj::Value| -> Deck { v.as_array().map(|a| a.iter().map(|x| cid(x.as_str().unwrap())).collect()).unwrap_or_default() };
        st.stacks = (0..n).map(|_| Stack::new()).collect();
        for (crn, stack) in d["board"].as_object().unwrap() {
            let cr = g.map.cr(crn).expect("unknown crossroad in saved state");
            for u in stack.as_array().unwrap() {
                let unit = st.unit_from(u);
                st.push_unit(cr, unit);
            }
        }
        for p in 0..2 {
            let pn = player_name(p as Player);
            st.hands[p] = d["hands"][pn].as_array().unwrap().iter().map(|u| st.unit_from(u)).collect();
            st.decks[p] = cards_of(&d["decks"][pn]);
            st.starting_decks[p] = d.get("starting_decks").map(|s| cards_of(&s[pn])).unwrap_or_default();
            st.food[p] = d["food"][pn].as_i64().unwrap() as i32;
            if let Some(c) = d.get("card_strength_counters").and_then(|c| c.get(pn)).and_then(|c| c.as_object()) {
                for (k, v) in c {
                    st.card_strength_counters[p].insert(cid(k), v.as_i64().unwrap() as i32);
                }
            }
            if let Some(j) = d.get("jelly").and_then(|c| c.get(pn)).and_then(|c| c.as_object()) {
                st.jelly_set[p] = true;
                for (k, v) in j {
                    let (left, counter) = match v {
                        sj::Value::Array(a) => (a[0].as_i64().unwrap() as i32, a[1].as_i64().unwrap() as i32),
                        sj::Value::Number(nn) => {
                            let c = cid(k);
                            (nn.as_i64().unwrap() as i32, st.jelly_counter(p as Player, c))
                        }
                        _ => (0, 0),
                    };
                    st.jelly[p].insert(cid(k), (left, counter));
                }
            }
            if let Some(t) = d.get("roar_twice").and_then(|c| c.get(pn)).and_then(|c| c.as_i64()) {
                st.roar_twice[p] = Some(t as i32);
            }
            if let Some(c) = d.get("last_roar").and_then(|c| c.get(pn)).and_then(|c| c.as_str()) {
                st.last_roar[p] = Some(cid(c));
            }
        }
        st.remove_pile = cards_of(&d["remove_pile"]);
        st.pile_owners = match d.get("pile_owners").and_then(|p| p.as_array()) {
            Some(a) => a.iter().map(|o| o.as_str().map(player_from)).collect(),
            None => (0..st.remove_pile.len()).map(|_| None).collect(),
        };
        st.current = player_from(d["current"].as_str().unwrap());
        st.first_player = player_from(d["first_player"].as_str().unwrap());
        let words: Vec<i64> = d["rng"]["state"].as_array().unwrap().iter().map(|x| x.as_i64().unwrap()).collect();
        st.rng = PyRandom::from_state(&words);
        st.turn_counter = d["turn_counter"].as_i64().unwrap() as i32;
        st.units_placed_this_turn = d["units_placed_this_turn"].as_i64().unwrap() as i32;
        st.actions_taken_this_turn = d.get("actions_taken_this_turn").and_then(|x| x.as_i64()).unwrap_or(0) as i32;
        st.idle_turns = d.get("idle_turns").and_then(|x| x.as_i64()).unwrap_or(0) as i32;
        st.next_iid = d["next_iid"].as_i64().unwrap();
        st.play_seq = d.get("play_seq").and_then(|x| x.as_i64()).unwrap_or(0) as i32;
        st.effect_stack = d.get("effect_stack").and_then(|x| x.as_array()).map(|a| a.iter().map(|x| upgrade_step(Value::from_json(x).as_map().unwrap().clone())).collect()).unwrap_or_default();
        st.pending = d.get("pending").filter(|p| !p.is_null()).map(|p| Value::from_json(p).as_map().unwrap().clone());
        st.scheduled = d
            .get("scheduled")
            .and_then(|x| x.as_array())
            .map(|a| {
                a.iter()
                    .map(|x| {
                        let mut m = Value::from_json(x).as_map().unwrap().clone();
                        if !m.contains_key("while_buried") {
                            m.insert("while_buried".into(), Value::Bool(false));
                        }
                        let step = upgrade_step(m.get("step").unwrap().as_map().unwrap().clone());
                        m.insert("step".into(), Value::Map(step));
                        m
                    })
                    .collect()
            })
            .unwrap_or_default();
        st.turn_flags = d.get("turn_flags").filter(|t| !t.is_null()).map(|t| TurnFlags::from_json(&st, t)).unwrap_or_default();
        st.result = d.get("result").filter(|r| !r.is_null()).map(|r| GameResult {
            winner: r["winner"].as_str().map(player_from),
            reason: r["reason"].as_str().unwrap().to_string(),
        });
        if let Some(a) = d.get("inked").and_then(|x| x.as_array()) {
            for i in a {
                let v = match i {
                    sj::Value::Array(pair) => pair[0].as_i64().unwrap(),
                    other => other.as_i64().unwrap(),
                };
                st.inked.insert(v);
            }
        }
        st
    }

    pub fn blank(g: Arc<Game>) -> State {
        let n = g.map.n();
        State {
            g,
            stacks: (0..n).map(|_| Stack::new()).collect(),
            order: SmallVec::new(),
            hands: [Hand::new(), Hand::new()],
            decks: [Deck::new(), Deck::new()],
            starting_decks: [Deck::new(), Deck::new()],
            remove_pile: Deck::new(),
            pile_owners: SmallVec::new(),
            food: [0, 0],
            current: A,
            first_player: A,
            rng: PyRandom::seeded(0),
            turn_counter: 0,
            units_placed_this_turn: 0,
            actions_taken_this_turn: 0,
            idle_turns: 0,
            next_iid: 0,
            play_seq: 0,
            effect_stack: Vec::new(),
            pending: None,
            scheduled: Vec::new(),
            turn_flags: TurnFlags::default(),
            card_strength_counters: [FxHashMap::default(), FxHashMap::default()],
            result: None,
            inked: BTreeSet::new(),
            roar_twice: [None, None],
            last_roar: [None, None],
            jelly: [FxHashMap::default(), FxHashMap::default()],
            jelly_set: [false, false],
            cache: BoardCache::default(),
            events: Vec::new(),
            cause: None,
            cause_iid: None,
            record_events: true,
        }
    }

    /// `new_game`: shuffle, coin flip, deal, and the mulligan's first pending choice.
    pub fn new_game(g: Arc<Game>, deck_a: &[CardId], deck_b: &[CardId], seed: i64, first_player: Option<Player>, stacked: bool) -> State {
        let mut st = State::blank(g.clone());
        st.rng = PyRandom::seeded(seed);
        st.decks = [Deck::from_slice(deck_a), Deck::from_slice(deck_b)];
        st.starting_decks = [Deck::from_slice(deck_a), Deck::from_slice(deck_b)];
        if stacked {
            st.decks[0].reverse();
            st.decks[1].reverse();
        } else {
            let mut d0 = std::mem::take(&mut st.decks[0]);
            st.rng.shuffle(&mut d0);
            st.decks[0] = d0;
            let mut d1 = std::mem::take(&mut st.decks[1]);
            st.rng.shuffle(&mut d1);
            st.decks[1] = d1;
        }
        let coin = if st.rng.random() < 0.5 { A } else { B };
        let first = first_player.unwrap_or(coin);
        let second = other(first);
        st.current = first;
        st.first_player = first;
        let cfg_first = st.cfg().first_player_opening_draw;
        let cfg_second = st.cfg().second_player_opening_draw;
        st.draw(first, cfg_first);
        st.draw(second, cfg_second);
        if st.cfg().mulligan {
            for player in [second, first] {
                if !st.hands[player as usize].is_empty() {
                    st.effect_stack.push(crate::vmap!(
                        "op" => Value::s("mulligan"), "player" => Value::s(player_name(player)), "returned" => Value::List(vec![])));
                }
            }
            if let Some(top) = st.effect_stack.last() {
                let chooser = player_from(top.get("player").unwrap().as_str().unwrap());
                st.pending = Some(mulligan_request(&st, chooser));
            }
        }
        if st.effect_stack.is_empty() {
            for player in [first, second] {
                st.ensure_mates(player, None);
            }
        }
        st
    }
}

pub fn mulligan_request(st: &State, player: Player) -> Map {
    crate::vmap!(
        "mode" => Value::s("choice"), "chooser" => Value::s(player_name(player)), "optional" => Value::Bool(true),
        "kind" => Value::s("mulligan"),
        "options" => Value::List(st.hands[player as usize].iter().map(|u| Value::Int(u.iid)).collect()))
}

/// A step saved before its facts were required (2026-10-01) gets them as the engine used to assume them.
pub fn upgrade_step(mut step: Map) -> Map {
    let op = step.get("op").and_then(|o| o.as_str()).unwrap_or("").to_string();
    let set_default = |m: &mut Map, k: &'static str, v: Value| {
        if !m.contains_key(k) {
            m.insert(k, v);
        }
    };
    match op.as_str() {
        "remove_iid" => {
            set_default(&mut step, "by_effect", Value::Bool(true));
            set_default(&mut step, "source_iid", Value::Null);
        }
        "remove_choice" => set_default(&mut step, "optional", Value::Bool(false)),
        "play_extra" => {
            set_default(&mut step, "filter", Value::Map(Map::default()));
            set_default(&mut step, "optional", Value::Bool(false));
        }
        "scout" => set_default(&mut step, "spec", Value::Null),
        _ => {}
    }
    step
}
