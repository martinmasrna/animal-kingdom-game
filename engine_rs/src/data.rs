//! What never changes during a game: the card table, the map and the rules' numbers. Built once from the same JSON the
//! Python package bundles (`data/cards.json`, `data/maps.json`) and a Config dict, shared by every position behind an Arc.

use std::collections::HashMap;

use serde_json::Value;

use crate::cards::{behaviour, Behaviour};

pub type CardId = u16;
pub type Tile = u8;
/// A seat: 0 is "A", 1 is "B".
pub type Player = u8;

/// Tiles are bits of a u64 and slots of a fixed array; a map may hold this many.
pub const MAX_TILES: usize = 40;

pub fn pname(p: Player) -> &'static str {
    if p == 0 { "A" } else { "B" }
}

pub fn player_from(s: &str) -> Result<Player, String> {
    match s {
        "A" => Ok(0),
        "B" => Ok(1),
        _ => Err(format!("unknown player {s:?}")),
    }
}

#[inline]
pub fn other(p: Player) -> Player {
    1 - p
}

pub const FLIGHT: u8 = 1;
pub const ARMOR: u8 = 2;
pub const STEALTH: u8 = 4;
pub const SPIKES: u8 = 8;
pub const POISON: u8 = 16;
pub const HUNGRY: u8 = 32;

fn keyword_bit(k: &str) -> Result<u8, String> {
    Ok(match k {
        "Flight" => FLIGHT,
        "Armor" => ARMOR,
        "Stealth" => STEALTH,
        "Spikes" => SPIKES,
        "Poison" => POISON,
        "Hungry" => HUNGRY,
        _ => return Err(format!("unknown keyword {k:?}")),
    })
}

/// What a count counts for a player: a dynamic strength ("+N for each ...") and the Djinn's discounts read the same four.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Count {
    Hand,
    Ally,
    Region,
    Played,
}

#[derive(Clone, Debug)]
pub struct Card {
    pub id: String,
    pub cost: i32,
    /// None: the strength is a live count (`dynamic`).
    pub base_strength: Option<i32>,
    pub dynamic: Option<Count>,
    pub keywords: u8,
    pub collectible: bool,
    pub legendary: bool,
    pub beh: Behaviour,
}

impl Card {
    #[inline]
    pub fn has(&self, kw: u8) -> bool {
        self.keywords & kw != 0
    }
}

/// The card table, in the order of the ids as strings: a CardId compares as its id does, so "sorted card ids" is a
/// numeric sort.
#[derive(Debug)]
pub struct Cards {
    pub list: Vec<Card>,
    index: HashMap<String, CardId>,
}

impl Cards {
    pub fn from_json(raw: &Value) -> Result<Cards, String> {
        let recs = raw["cards"].as_array().ok_or("cards.json must contain a 'cards' list")?;
        let mut list: Vec<Card> = Vec::new();
        for rec in recs {
            if rec["status"].as_str() == Some("planned") {
                continue;
            }
            let id = rec["id"].as_str().ok_or("a card with no id")?.to_string();
            let (base_strength, dynamic) = match &rec["base_strength"] {
                Value::Number(n) => (Some(n.as_i64().ok_or_else(|| format!("card {id:?}: bad base_strength"))? as i32), None),
                _ => (None, Some(match rec["dynamic_strength"].as_str() {
                    Some("hand_count") => Count::Hand,
                    Some("ally_count") => Count::Ally,
                    Some("region_count") => Count::Region,
                    Some("played_count") => Count::Played,
                    other => return Err(format!("card {id:?}: unknown dynamic strength rule {other:?}")),
                })),
            };
            let mut keywords = 0u8;
            if let Some(ks) = rec["keywords"].as_array() {
                for k in ks {
                    keywords |= keyword_bit(k.as_str().unwrap_or(""))?;
                }
            }
            list.push(Card {
                beh: behaviour(&id),
                cost: rec["cost"].as_i64().ok_or_else(|| format!("card {id:?}: bad cost"))? as i32,
                base_strength,
                dynamic,
                keywords,
                collectible: rec["status"].as_str() == Some("collectible"),
                legendary: rec["rarity"].as_str() == Some("legendary"),
                id,
            });
        }
        list.sort_by(|a, b| a.id.cmp(&b.id));
        let mut index = HashMap::new();
        for (i, c) in list.iter().enumerate() {
            if index.insert(c.id.clone(), i as CardId).is_some() {
                return Err(format!("duplicate card id {:?}", c.id));
            }
        }
        Ok(Cards { list, index })
    }

    #[inline]
    pub fn get(&self, c: CardId) -> &Card {
        &self.list[c as usize]
    }

    pub fn id_of(&self, name: &str) -> Option<CardId> {
        self.index.get(name).copied()
    }

    pub fn need(&self, name: &str) -> Result<CardId, String> {
        self.id_of(name).ok_or_else(|| format!("unknown card {name:?}"))
    }

    pub fn name_of(&self, c: CardId) -> &str {
        &self.list[c as usize].id
    }
}

#[derive(Debug)]
pub struct Region {
    pub mask: u64,
    pub food: i32,
}

/// The board's geometry. A Tile is the tile's place among the tile names sorted as strings, so "sorted tiles" and
/// "sorted neighbours" are numeric order.
#[derive(Debug)]
pub struct GameMap {
    pub id: String,
    pub tiles: Vec<String>,
    index: HashMap<String, Tile>,
    /// tile -> its neighbours, ascending
    pub neighbors: Vec<Vec<Tile>>,
    pub nb_mask: Vec<u64>,
    /// player -> the tiles in front of their den: where their connection starts, and through which their den is raided
    pub hq_front: [u64; 2],
    pub regions: Vec<Region>,
    pub win_food: i32,
}

impl GameMap {
    pub fn from_json(rec: &Value) -> Result<GameMap, String> {
        let id = rec["id"].as_str().ok_or("a map with no id")?.to_string();
        let mut tiles: Vec<String> = rec["crossroads"].as_array().ok_or("map: no crossroads")?.iter().map(|v| v.as_str().unwrap_or("").to_string()).collect();
        tiles.sort();
        if tiles.len() > MAX_TILES {
            return Err(format!("map {id:?} has {} tiles, the engine holds {MAX_TILES}", tiles.len()));
        }
        let index: HashMap<String, Tile> = tiles.iter().enumerate().map(|(i, t)| (t.clone(), i as Tile)).collect();
        let tile = |v: &Value| -> Result<Tile, String> {
            index.get(v.as_str().unwrap_or("")).copied().ok_or_else(|| format!("map {id:?}: unknown tile {v}"))
        };
        let mut nb_mask = vec![0u64; tiles.len()];
        for e in rec["edges"].as_array().ok_or("map: no edges")? {
            let (a, b) = (tile(&e[0])?, tile(&e[1])?);
            nb_mask[a as usize] |= 1 << b;
            nb_mask[b as usize] |= 1 << a;
        }
        let neighbors = nb_mask.iter().map(|&m| (0..tiles.len() as Tile).filter(|&t| m >> t & 1 == 1).collect()).collect();
        let mut hq_front = [0u64; 2];
        for (p, name) in ["A", "B"].iter().enumerate() {
            for c in rec["hqs"][*name]["connects"].as_array().ok_or_else(|| format!("map {id:?}: no den for {name}"))? {
                hq_front[p] |= 1 << tile(c)?;
            }
        }
        let mut regions = Vec::new();
        for (_rid, r) in rec["regions"].as_object().ok_or("map: no regions")? {
            let mut mask = 0u64;
            for c in r["corners"].as_array().ok_or("region: no corners")? {
                mask |= 1 << tile(c)?;
            }
            regions.push(Region { mask, food: r["food"].as_i64().unwrap_or(0) as i32 });
        }
        let win_food = rec["win_food"].as_i64().ok_or("map: no win_food")? as i32;
        Ok(GameMap { id, tiles, index, neighbors, nb_mask, hq_front, regions, win_food })
    }

    pub fn tile_of(&self, name: &str) -> Option<Tile> {
        self.index.get(name).copied()
    }

    pub fn tile_name(&self, t: Tile) -> &str {
        &self.tiles[t as usize]
    }

    #[inline]
    pub fn n_tiles(&self) -> usize {
        self.tiles.len()
    }
}

macro_rules! config {
    ($($name:ident : $ty:ty = $default:expr),* $(,)?) => {
        /// The rules' numbers (the Python `Config`, field for field).
        #[derive(Clone, Debug)]
        pub struct Config { $(pub $name: $ty),* }

        impl Default for Config {
            fn default() -> Config { Config { $($name: $default),* } }
        }

        impl Config {
            /// From `dataclasses.asdict(Config())`: a key the dict lacks keeps its default.
            pub fn from_json(v: &Value) -> Result<Config, String> {
                let mut c = Config::default();
                let obj = v.as_object().ok_or("the config must be a dict")?;
                $(if let Some(x) = obj.get(stringify!($name)) { c.$name = ConfigValue::read(x).ok_or_else(|| format!("config: bad {}", stringify!($name)))?; })*
                for k in obj.keys() {
                    if ![$(stringify!($name)),*].contains(&k.as_str()) {
                        return Err(format!("config: the Rust engine has no {k:?}"));
                    }
                }
                Ok(c)
            }
        }
    };
}

trait ConfigValue: Sized {
    fn read(v: &Value) -> Option<Self>;
}

impl ConfigValue for i32 {
    fn read(v: &Value) -> Option<i32> {
        v.as_i64().map(|x| x as i32)
    }
}

impl ConfigValue for bool {
    fn read(v: &Value) -> Option<bool> {
        v.as_bool()
    }
}

config! {
    mana_cap: i32 = 10,
    leader_power_cost: i32 = 3,
    start_food: i32 = 15,
    hand_limit: i32 = 10,
    first_player_opening_draw: i32 = 3,
    second_player_opening_draw: i32 = 4,
    mulligan: bool = true,
    turn_draw_count: i32 = 1,
    hungry_food: i32 = 1,
    shade_growth: i32 = 2,
    combo_djinn_discount: i32 = 2,
    region_djinn_discount: i32 = 2,
    warlord_leader_food: i32 = 1,
    elf_card_region_bonus: i32 = 1,
    assassin_card_discount: i32 = 1,
    mana_blob_mana: i32 = 2,
    sage_card_power_discount: i32 = 1,
    elf_power_cost: i32 = 2,
    elf_food_per_region: i32 = 1,
    assassin_nth_card: i32 = 3,
    raider_leader_bonus: i32 = 1,
    mama_spores: i32 = 2,
    crush_max: i32 = 5,
    crush_albatross_max: i32 = 4,
    crush_young_max: i32 = 3,
    crush_young_albatross_max: i32 = 2,
    scout_look: i32 = 3,
    double_raid_factor: i32 = 2,
    max_actions_per_turn: i32 = 30,
    max_effect_steps_per_turn: i32 = 1000,
    max_turns: i32 = 400,
}

impl Config {
    /// Cards a player may return in the mulligan: as many as their opening hand.
    pub fn mulligan_cap(&self, player: Player, first_player: Player) -> i32 {
        if player == first_player { self.first_player_opening_draw } else { self.second_player_opening_draw }
    }
}

/// The five leaders' card ids and the Spore token's, looked up once; None when the card table lacks the card.
#[derive(Debug, Default)]
pub struct Named {
    pub warlord: Option<CardId>,
    pub raider: Option<CardId>,
    pub sage: Option<CardId>,
    pub elf: Option<CardId>,
    pub assassin: Option<CardId>,
    pub spore: Option<CardId>,
}

#[derive(Debug)]
pub struct Game {
    pub cards: Cards,
    pub map: GameMap,
    pub cfg: Config,
    pub named: Named,
}

impl Game {
    pub fn new(cards: Cards, map: GameMap, cfg: Config) -> Game {
        let named = Named {
            warlord: cards.id_of(crate::cards::WARLORD),
            raider: cards.id_of(crate::cards::RAIDER),
            sage: cards.id_of(crate::cards::SAGE),
            elf: cards.id_of(crate::cards::ELF),
            assassin: cards.id_of(crate::cards::ASSASSIN),
            spore: cards.id_of(crate::cards::SPORE),
        };
        Game { cards, map, cfg, named }
    }
}
