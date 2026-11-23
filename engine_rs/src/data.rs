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
    /// The food the opponent lost this game (the Burn Djinn).
    EnemyFoodLost,
    /// The food your regions produced this game (the Food Djinn).
    FoodProduced,
}

pub const KEYWORDS: [(&str, u8); 6] = [("Flight", FLIGHT), ("Armor", ARMOR), ("Stealth", STEALTH), ("Spikes", SPIKES), ("Poison", POISON), ("Hungry", HUNGRY)];
pub const RARITIES: [&str; 2] = ["common", "legendary"];
/// "collectible": a deck may hold it. "reserve": benched, out of every deck. A "planned" record is no card yet: the
/// loader skips it.
pub const STATUSES: [&str; 2] = ["collectible", "reserve"];
pub const PLANNED: &str = "planned";
pub const DYNAMIC_STRENGTHS: [&str; 4] = ["ally_count", "hand_count", "played_count", "region_count"];

/// A deck: this many cards, collectible ones only, at most `copy_limit` of each, and a leader that is one of them.
pub const DECK_SIZE: usize = 25;

pub fn copy_limit(legendary: bool) -> usize {
    if legendary { 1 } else { 2 }
}

/// A value as an error message shows it (the way the card tools have always printed one).
fn shown(v: &Value) -> String {
    match v {
        Value::String(s) => format!("'{s}'"),
        Value::Null => "None".into(),
        Value::Bool(b) => if *b { "True".into() } else { "False".into() },
        other => other.to_string(),
    }
}

fn shown_list(items: &[&str]) -> String {
    let mut v: Vec<&str> = items.to_vec();
    v.sort();
    format!("[{}]", v.iter().map(|s| format!("'{s}'")).collect::<Vec<_>>().join(", "))
}

/// The first problem with a raw card record, if it has one.
pub fn validate_card_record(rec: &Value) -> Result<(), String> {
    let obj = rec.as_object().ok_or("a card record must be an object")?;
    for key in ["id", "name", "status", "rarity", "base_strength", "cost"] {
        if !obj.contains_key(key) {
            let who = obj.get("id").map(shown).unwrap_or_else(|| "?".into());
            return Err(format!("card {who} missing required field '{key}'"));
        }
    }
    let cid = shown(&rec["id"]);
    if !rec["id"].is_string() {
        return Err(format!("card {cid}: the id must be text"));
    }
    if !rec["rarity"].as_str().map_or(false, |r| RARITIES.contains(&r)) {
        return Err(format!("card {cid}: bad rarity {}, expected one of {}", shown(&rec["rarity"]), shown_list(&RARITIES)));
    }
    if !rec["status"].as_str().map_or(false, |r| STATUSES.contains(&r)) {
        return Err(format!("card {cid}: bad status {}, expected one of {}", shown(&rec["status"]), shown_list(&STATUSES)));
    }
    let strength = &rec["base_strength"];
    if strength.as_str() == Some("dynamic") {
        if !rec.get("dynamic_strength").and_then(|v| v.as_str()).map_or(false, |d| DYNAMIC_STRENGTHS.contains(&d)) {
            return Err(format!("card {cid}: base_strength 'dynamic' needs a 'dynamic_strength' of {}", shown_list(&DYNAMIC_STRENGTHS)));
        }
    } else if !strength.as_i64().map_or(false, |n| n >= 0) {
        return Err(format!("card {cid}: base_strength must be an int >= 0 or 'dynamic', got {}", shown(strength)));
    }
    if let Some(ks) = rec.get("keywords").and_then(|v| v.as_array()) {
        for k in ks {
            if !k.as_str().map_or(false, |k| KEYWORDS.iter().any(|(n, _)| *n == k)) {
                let names: Vec<&str> = KEYWORDS.iter().map(|(n, _)| *n).collect();
                return Err(format!("card {cid}: unknown keyword {}, expected one of {}", shown(k), shown_list(&names)));
            }
        }
    }
    if !rec["cost"].as_i64().map_or(false, |n| n >= 0) {
        return Err(format!("card {cid}: cost must be a whole number of 0 or more, got {}", shown(&rec["cost"])));
    }
    Ok(())
}

#[derive(Clone, Debug)]
pub struct Card {
    pub id: String,
    pub name: String,
    pub text: String,
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

    pub fn keyword_names(&self) -> Vec<&'static str> {
        let mut v: Vec<&str> = KEYWORDS.iter().filter(|(_, bit)| self.has(*bit)).map(|(n, _)| *n).collect();
        v.sort();
        v
    }

    /// The card as its record in the card table reads, plus what it does that others read: the cards it makes, and the
    /// strength its Roar takes off an enemy.
    pub fn to_json(&self) -> Value {
        let dynamic = self.dynamic.map(|c| match c {
            Count::Hand => "hand_count",
            Count::Ally => "ally_count",
            Count::Region => "region_count",
            Count::Played => "played_count",
            Count::EnemyFoodLost => "enemy_food_lost",
            Count::FoodProduced => "food_produced",
        });
        let mut o = serde_json::json!({
            "id": self.id, "name": self.name, "status": if self.collectible { "collectible" } else { "reserve" },
            "rarity": if self.legendary { "legendary" } else { "common" },
            "base_strength": match self.base_strength { Some(v) => Value::from(v), None => Value::from("dynamic") },
            "cost": self.cost, "keywords": self.keyword_names(), "dynamic_strength": dynamic, "text": self.text,
        });
        let makes = crate::cards::makes(&self.id);
        if !makes.is_empty() {
            o["makes"] = Value::from(makes.to_vec());
        }
        if let Some(crate::cards::Roar::Weaken(n)) = self.beh.on_place {
            o["weaken"] = Value::from(n);
        }
        o
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
        let recs = raw["cards"].as_array().filter(|a| !a.is_empty()).ok_or("cards.json must contain a non-empty 'cards' list")?;
        let mut list: Vec<Card> = Vec::new();
        for rec in recs {
            if rec["status"].as_str() == Some(PLANNED) {
                continue;
            }
            validate_card_record(rec)?;
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
                name: rec["name"].as_str().unwrap_or("").to_string(),
                text: rec.get("text").and_then(|v| v.as_str()).unwrap_or("").to_string(),
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
    pub id: String,
    /// Its tiles as the map lists them.
    pub corners: Vec<Tile>,
    pub mask: u64,
    pub food: i32,
}

/// The board's geometry. A Tile is the tile's place among the tile names sorted as strings, so "sorted tiles" and
/// "sorted neighbours" are numeric order.
#[derive(Debug)]
pub struct GameMap {
    pub id: String,
    pub name: String,
    /// The edges as the map lists them.
    pub edges: Vec<(Tile, Tile)>,
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
        if tiles.windows(2).any(|w| w[0] == w[1]) {
            return Err(format!("map {id:?}: duplicate crossroads"));
        }
        if tiles.len() > MAX_TILES {
            return Err(format!("map {id:?} has {} tiles, the engine holds {MAX_TILES}", tiles.len()));
        }
        let index: HashMap<String, Tile> = tiles.iter().enumerate().map(|(i, t)| (t.clone(), i as Tile)).collect();
        let tile = |v: &Value| -> Result<Tile, String> {
            index.get(v.as_str().unwrap_or("")).copied().ok_or_else(|| format!("map {id:?}: unknown tile {v}"))
        };
        let mut nb_mask = vec![0u64; tiles.len()];
        let mut edges = Vec::new();
        for e in rec["edges"].as_array().ok_or("map: no edges")? {
            if e.as_array().map_or(true, |x| x.len() != 2) {
                return Err(format!("map {id:?}: edge {e} must have exactly 2 endpoints"));
            }
            let (a, b) = (tile(&e[0])?, tile(&e[1])?);
            if a == b {
                return Err(format!("map {id:?}: self-loop edge {e}"));
            }
            nb_mask[a as usize] |= 1 << b;
            nb_mask[b as usize] |= 1 << a;
            edges.push((a, b));
        }
        let neighbors = nb_mask.iter().map(|&m| (0..tiles.len() as Tile).filter(|&t| m >> t & 1 == 1).collect()).collect();
        let mut hq_front = [0u64; 2];
        for (p, name) in ["A", "B"].iter().enumerate() {
            for c in rec["hqs"][*name]["connects"].as_array().ok_or_else(|| format!("map {id:?}: no den for {name}"))? {
                hq_front[p] |= 1 << tile(c)?;
            }
            if hq_front[p] == 0 {
                return Err(format!("map {id:?}: the den of {name} has no front tiles"));
            }
        }
        let mut regions = Vec::new();
        for (rid, r) in rec["regions"].as_object().ok_or("map: no regions")? {
            let mut mask = 0u64;
            let mut corners = Vec::new();
            for c in r["corners"].as_array().ok_or("region: no corners")? {
                corners.push(tile(c)?);
                mask |= 1 << tile(c)?;
            }
            let food = r["food"].as_i64().filter(|f| *f >= 0).ok_or_else(|| format!("map {id:?}: region {rid:?} has bad food {}", r["food"]))? as i32;
            regions.push(Region { id: rid.clone(), corners, mask, food });
        }
        let win_food = rec["win_food"].as_i64().filter(|f| *f > 0).ok_or_else(|| format!("map {id:?}: win_food must be a positive int, got {}", rec["win_food"]))? as i32;
        let name = rec["name"].as_str().unwrap_or("").to_string();
        Ok(GameMap { id, name, edges, tiles, index, neighbors, nb_mask, hq_front, regions, win_food })
    }

    /// The board as the client and the tools read it: its tiles, edges and regions as the map lists them, each
    /// player's base (the tiles in front of their den), the food that wins.
    pub fn to_json(&self) -> Value {
        let names = |m: u64| -> Vec<&str> { (0..self.tiles.len() as Tile).filter(|&t| m >> t & 1 == 1).map(|t| self.tile_name(t)).collect() };
        serde_json::json!({
            "id": self.id, "name": self.name, "win_food": self.win_food, "crossroads": self.tiles,
            "edges": self.edges.iter().map(|&(a, b)| [self.tile_name(a), self.tile_name(b)]).collect::<Vec<_>>(),
            "bases": {"A": names(self.hq_front[0]), "B": names(self.hq_front[1])},
            "regions": self.regions.iter().map(|r| serde_json::json!({"id": r.id, "food": r.food, "corners": r.corners.iter().map(|&t| self.tile_name(t)).collect::<Vec<_>>()})).collect::<Vec<_>>(),
        })
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

    /// Every tile, as bits.
    #[inline]
    pub fn all_tiles(&self) -> u64 {
        if self.tiles.len() >= 64 { u64::MAX } else { (1u64 << self.tiles.len()) - 1 }
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

            /// Every number by name: what Python and the tools read.
            pub fn to_json(&self) -> Value {
                let mut m = serde_json::Map::new();
                $(m.insert(stringify!($name).to_string(), Value::from(self.$name));)*
                Value::Object(m)
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

// The rules' numbers in one place; the map holds the board's own (each region's food, the food that wins).
config! {
    // Mana: on a player's Nth own turn they have min(N, mana_cap), lost at the end of the turn. Playing a card from hand
    // costs its card's cost; a leader's power costs leader_power_cost.
    mana_cap: i32 = 10,                   // Martin, 2026-11-20: "Mana cap at 10 of course"
    leader_power_cost: i32 = 3,
    // The food race (Martin, 2026-11-20: "both players starting at 15, you need 30 to win, and if you drop to 0 you
    // lost"): a raid destroys food; each region a player holds pays its food at the end of their turn.
    start_food: i32 = 15,
    hand_limit: i32 = 10,                 // past it, the newest cards drawn burn
    first_player_opening_draw: i32 = 3,   // Martin, 2026-11-20: "make it 3 for first and 4 for second"
    second_player_opening_draw: i32 = 4,
    mulligan: bool = true,                // a blacklist mulligan, both players at once
    // Fatigue (Martin, 2026-11-22: "we just add fatigue exactly like in hearthstone, losing energy -1, -2, -3, ..."): a card
    // a player would draw from their own empty deck costs them food instead, this much more each time.
    fatigue_step: i32 = 1,
    turn_draw_count: i32 = 1,             // the free card at the start of each turn, the first player's first included (Martin, 2026-11-21)
    hungry_food: i32 = 1,                 // Hungry: the food its prey's removal gains (Martin, 2026-11-20)
    shade_growth: i32 = 2,                // a strength that is a count: +2 for each (Martin, 2026-11-21)
    combo_djinn_discount: i32 = 2,        // the Combo Djinn: "Costs 2 less for each card you played this turn."
    warlord_leader_food: i32 = 1,         // the Warlord: "When you cover an enemy, gain 1 food."
    elf_region_bonus: i32 = 1,            // the Elf: "Your regions produce 1 more food." (Martin, 2026-11-23)
    assassin_card_discount: i32 = 1,      // the Assassin's card: "Roar: reduce the cost of cards in your hand by 1."
    mana_blob_mana: i32 = 2,              // the Mana Blob: "Roar: gain 2 mana." (Martin, 2026-11-21)
    sage_card_power_discount: i32 = 1,    // the Sage's card: "Roar: reduce the cost of your hero power by 1."
    elf_food_per_region: i32 = 2,         // the Elf's card: "Roar: gain 2 food for each region you control." (Martin, 2026-11-23)
    assassin_nth_card: i32 = 3,           // the Assassin: "After every third card you play in a turn, draw a card."
    raider_leader_bonus: i32 = 1,         // the Raider: "Your raids destroy 1 more food." (Martin, 2026-11-21: "only +1")
    mama_spores: i32 = 2,                 // Mama Spore: "Roar: put 2 Spores into your hand." (Martin, 2026-11-21)
    bird_egg_flights: i32 = 2,            // the Bird Egg: "Fall: add two [Flight 1] to your hand." (Martin, 2026-11-22)
    golden_egg_draws: i32 = 1,            // the Golden Egg: "When you draw this, draw a card." (Martin, 2026-11-22)
    crush_max: i32 = 5,                   // the Rhino: "remove all adjacent enemies with strength 5 or less"
    crush_albatross_max: i32 = 4,         // the Albatross: "... with strength 4 or less" (Martin, 2026-11-21)
    crush_young_max: i32 = 3,             // the Young Rhino: "... with strength 3 or less" (Martin, 2026-11-21)
    crush_young_albatross_max: i32 = 2,   // the Young Albatross: "... with strength 2 or less" (Martin, 2026-11-21)
    scout_look: i32 = 3,                  // Scout: the cards of your deck's top it looks at (Martin, 2026-11-21)
    double_raid_factor: i32 = 2,          // Leeroy: "Double strength when raiding." (Martin, 2026-11-22)
    // Safety caps, so a loop of effects can never hang a game.
    max_actions_per_turn: i32 = 30,       // a turn ends after this many applied actions, choices included (Martin, 2026-11-18)
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
    pub flight_1: Option<CardId>,
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
            flight_1: cards.id_of(crate::cards::FLIGHT_1),
        };
        Game { cards, map, cfg, named }
    }
}
