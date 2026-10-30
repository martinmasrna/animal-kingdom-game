//! Static game data: the cards (data/cards.json), the maps (data/maps.json) and the Config (the Python dataclass,
//! handed over as a dict), parsed once into index-addressed tables. Card ids, crossroads and players are small
//! integers inside the engine and strings at its edge.

use rustc_hash::FxHashMap;
use serde_json as sj;

pub type CardId = u16;
pub type Cr = u8;
pub type Player = u8;

pub const A: Player = 0;
pub const B: Player = 1;
pub const WILD: Player = 2;

pub fn other(p: Player) -> Player {
    if p == A {
        B
    } else {
        A
    }
}
pub fn player_name(p: Player) -> &'static str {
    match p {
        A => "A",
        B => "B",
        _ => "wild",
    }
}
pub fn player_from(s: &str) -> Player {
    match s {
        "A" => A,
        "B" => B,
        _ => WILD,
    }
}

// Tags and keywords as bit flags.
pub const TAGS: [&str; 19] = [
    "Cat", "Canine", "Colony", "Snake", "Lizard", "Bird", "Rodent", "Arachnid", "Bear", "Megafauna", "Egg", "Fish",
    "Primate", "Hoofed", "Queen", "Worker", "Soldier", "Nurse", "Beetle",
];
/// The tags the bots' trained networks read: the first 16, every tag but the castes (Soldier, Nurse) and Beetle, as
/// Python's `cards.BOT_TAGS`; those stay out of the features until a retrain.
pub const BOT_TAG_COUNT: usize = 16;
pub const KEYWORDS: [&str; 12] = [
    "Flight", "Armor", "Apex Predator", "Stealth", "Spikes", "Poison", "Roam", "Reach", "Hungry", "Titan", "Flee", "Wild",
];

pub fn tag_bit(name: &str) -> u32 {
    TAGS.iter().position(|t| *t == name).map(|i| 1u32 << i).unwrap_or(0)
}
pub fn kw_bit(name: &str) -> u32 {
    KEYWORDS.iter().position(|t| *t == name).map(|i| 1u32 << i).unwrap_or(0)
}

pub const T_CAT: u32 = 1 << 0;
pub const T_CANINE: u32 = 1 << 1;
pub const T_COLONY: u32 = 1 << 2;
pub const T_SNAKE: u32 = 1 << 3;
pub const T_BIRD: u32 = 1 << 5;
pub const T_RODENT: u32 = 1 << 6;
pub const T_EGG: u32 = 1 << 10;
pub const T_FISH: u32 = 1 << 11;
pub const T_PRIMATE: u32 = 1 << 12;
pub const T_HOOFED: u32 = 1 << 13;
pub const T_QUEEN: u32 = 1 << 14;
pub const T_WORKER: u32 = 1 << 15;

pub const K_FLIGHT: u32 = 1 << 0;
pub const K_ARMOR: u32 = 1 << 1;
pub const K_APEX: u32 = 1 << 2;
pub const K_STEALTH: u32 = 1 << 3;
pub const K_SPIKES: u32 = 1 << 4;
pub const K_POISON: u32 = 1 << 5;
pub const K_ROAM: u32 = 1 << 6;
pub const K_REACH: u32 = 1 << 7;
pub const K_HUNGRY: u32 = 1 << 8;
pub const K_TITAN: u32 = 1 << 9;
pub const K_FLEE: u32 = 1 << 10;

/// A sentence after a Roar that starts one of these is an ability of its own (features.py `_LASTING_STARTS`).
const LASTING_STARTS: [&str; 7] = ["When ", "Whenever ", "While ", "Dawn:", "Dusk:", "Deathrattle", "Evolves "];

const TRIGGER_STARTS: [&str; 6] = ["Roar:", "Dawn:", "Dusk:", "When ", "Whenever ", "Deathrattle"];
const PAYOFF_WORDS: [&[&str]; 6] = [&["food"], &["draw", "scout", "to your hand"], &["remove"], &["strength"], &["place "], &["action"]];

/// `pat` in `t` with a word boundary on both sides (a regex `\b`).
fn word_at(t: &str, pat: &str) -> bool {
    let b = t.as_bytes();
    let w = |i: usize| b[i].is_ascii_alphanumeric() || b[i] == b'_';
    t.match_indices(pat).any(|(i, m)| (i == 0 || !w(i - 1)) && (i + m.len() == b.len() || !w(i + m.len())))
}

/// features.py `_TIMER_WORDS`: "in N turns" or "next turn", any case.
fn has_timer_words(t: &str) -> bool {
    let low = t.to_lowercase();
    if word_at(&low, "next turn") {
        return true;
    }
    low.match_indices("in ").any(|(i, _)| {
        let b = low.as_bytes();
        if i > 0 && (b[i - 1].is_ascii_alphanumeric() || b[i - 1] == b'_') {
            return false;
        }
        let rest = &low[i + 3..];
        let digits = rest.bytes().take_while(|c| c.is_ascii_digit()).count();
        digits > 0 && rest[digits..].starts_with(" turns") && rest[digits + 6..].bytes().next().map_or(true, |c| !(c.is_ascii_alphanumeric() || c == b'_'))
    })
}

/// features.py `ability_profile`: when the ability fires, what it pays, whether it is conditional, read from the
/// printed text's shape.
fn profile_of(text: &str, kw_names: &[&str], lasting: bool) -> [f64; 12] {
    let mut sentences: Vec<(&str, bool)> = Vec::new();
    let mut in_roar = false;
    for t in text.split('.').map(|t| t.trim()).filter(|t| !t.is_empty()) {
        if t.starts_with("Roar:") {
            in_roar = true;
        } else if in_roar && LASTING_STARTS.iter().any(|s| t.starts_with(s)) {
            in_roar = false;
        }
        if (lasting && in_roar) || kw_names.contains(&t) || t.starts_with("Costs ") {
            continue;
        }
        sentences.push((t, in_roar));
    }
    let low: Vec<String> = sentences.iter().map(|(t, _)| t.to_lowercase()).collect();
    let mut out = [0.0; 12];
    let flag = |b: bool| if b { 1.0 } else { 0.0 };
    out[0] = flag(sentences.iter().any(|(t, _)| t.starts_with("Dawn:")));
    out[1] = flag(sentences.iter().any(|(t, _)| t.starts_with("Dusk:")));
    out[2] = flag(sentences.iter().any(|(t, _)| ["When ", "Whenever ", "Deathrattle"].iter().any(|s| t.starts_with(s))));
    out[3] = flag(sentences.iter().any(|(t, _)| has_timer_words(t)));
    out[4] = flag(sentences.iter().any(|(t, r)| !r && !TRIGGER_STARTS.iter().any(|s| t.starts_with(s))));
    for (k, words) in PAYOFF_WORDS.iter().enumerate() {
        out[5 + k] = flag(low.iter().any(|t| words.iter().any(|w| t.contains(w))));
    }
    out[11] = flag(low.iter().any(|t| t.starts_with("while ") || format!(" {t}").contains(" if ")));
    out
}

#[derive(Clone, Debug)]
pub struct Card {
    pub idx: CardId,
    pub id: String,
    pub name: String,
    pub status: String,
    pub rarity: String,
    pub tags: u32,
    pub tag_names: Vec<String>,
    pub base: Option<i32>, // None: dynamic
    pub dynamic: Option<String>,
    pub keywords: u32,
    pub food_cost: i32,
    pub text: String,
    pub hungry: i32,
    pub mate: Option<CardId>,
    pub has_roar: bool,
    /// Rules text beyond keywords and a food cost (features.has_ability).
    pub has_ability: bool,
    /// The ability once the Roar has fired: the text without the Roar's own sentences (features.lasting_ability).
    pub has_lasting_ability: bool,
    /// The ability as what it does (features.ability_profile, ABILITY_FEATURES order): in hand, and on the board
    /// without the Roar's own sentences.
    pub ability_profile: [f64; 12],
    pub lasting_profile: [f64; 12],
    /// The cards whose own text is a live "+X" (strength.py ANTHEM_CARDS): 0 none, 1 guard_wasp, 2 tuna, 3 marmot,
    /// 4 peacock, 5 giraffe, 6 crocodile, 7 capybara.
    pub anthem_kind: u8,
    /// Family auras (strength.py FAMILY_AURAS): 0 none, 1 mahi_mahi (Fish, always), 2 cape_buffalo (Hoofed, their turn).
    pub family_aura: u8,
    /// Keyword auras (statics.py KEYWORD_AURAS): 0 none, 1 armadillo (Armor), 2 porcupine (Spikes), 3 jellyfish
    /// (Poison).
    pub keyword_aura: u8,
}

pub const ANTHEM_KINDS: [&str; 8] = ["", "guard_wasp", "tuna", "marmot", "peacock", "giraffe", "crocodile", "capybara"];
pub const FAMILY_AURAS: [&str; 3] = ["", "mahi_mahi", "cape_buffalo"];
pub const KEYWORD_AURAS: [&str; 4] = ["", "armadillo", "porcupine", "jellyfish"];

/// The cards the engine's rules name (never a card's effect: those live with the card in effects): resolved once.
pub struct Known {
    pub hercules_beetle: Option<CardId>,
    pub bison: Option<CardId>,
    pub leopard: Option<CardId>,
    pub piranha: Option<CardId>,
    pub sardine_legend: Option<CardId>,
    pub moose: Option<CardId>,
    pub wolf_legend_3: Option<CardId>,
    pub great_white_shark: Option<CardId>,
    pub cougar: Option<CardId>,
    pub outrider: Option<CardId>,
    pub lion_legend_3: Option<CardId>,
    pub hornet_legend: Option<CardId>,
    pub python: Option<CardId>,
    pub bumblebee_legend: Option<CardId>,
    pub tortoise_legend: Option<CardId>,
    pub wildebeest_legend: Option<CardId>,
    pub boar_legend: Option<CardId>,
    pub giraffe_legend: Option<CardId>,
    pub sloth_legend: Option<CardId>,
    pub woodpecker: Option<CardId>,
    pub macaw: Option<CardId>,
    pub anaconda: Option<CardId>,
    pub leopard_legend: Option<CardId>,
    pub rattlesnake: Option<CardId>,
    pub vulture: Option<CardId>,
    pub locust_swarm: Option<CardId>,
}

impl Known {
    pub fn build(cards: &Cards) -> Known {
        let k = |n: &str| cards.id_of(n);
        Known {
            hercules_beetle: k("hercules_beetle"),
            bison: k("bison"),
            leopard: k("leopard"),
            piranha: k("piranha"),
            sardine_legend: k("sardine_legend"),
            moose: k("moose"),
            wolf_legend_3: k("wolf_legend_3"),
            great_white_shark: k("great_white_shark"),
            cougar: k("cougar"),
            outrider: k("outrider"),
            lion_legend_3: k("lion_legend_3"),
            hornet_legend: k("hornet_legend"),
            python: k("python"),
            bumblebee_legend: k("bumblebee_legend"),
            tortoise_legend: k("tortoise_legend"),
            wildebeest_legend: k("wildebeest_legend"),
            boar_legend: k("boar_legend"),
            giraffe_legend: k("giraffe_legend"),
            sloth_legend: k("sloth_legend"),
            woodpecker: k("woodpecker"),
            macaw: k("macaw"),
            anaconda: k("anaconda"),
            leopard_legend: k("leopard_legend"),
            rattlesnake: k("rattlesnake"),
            vulture: k("vulture"),
            locust_swarm: k("locust_swarm"),
        }
    }
}

impl Card {
    pub fn has_tag(&self, bit: u32) -> bool {
        self.tags & bit != 0
    }
    pub fn has_kw(&self, bit: u32) -> bool {
        self.keywords & bit != 0
    }
    pub fn base_int(&self) -> i32 {
        self.base.unwrap_or(0)
    }
}

pub struct Cards {
    pub list: Vec<Card>,
    pub by_id: FxHashMap<String, CardId>,
    /// Each card's id as a `&'static str` (leaked once per process), for the engine's step data.
    pub snames: Vec<&'static str>,
}

impl Cards {
    pub fn from_json(raw: &sj::Value) -> Result<Cards, String> {
        let recs = raw.get("cards").and_then(|c| c.as_array()).ok_or("cards.json must contain a 'cards' list")?;
        let mut list = Vec::new();
        let mut by_id = FxHashMap::default();
        let mut mates: Vec<(usize, String)> = Vec::new();
        for rec in recs {
            if rec.get("status").and_then(|s| s.as_str()) == Some("planned") {
                continue;
            }
            let id = rec["id"].as_str().ok_or("card without id")?.to_string();
            let tag_names: Vec<String> =
                rec.get("tags").and_then(|t| t.as_array()).map(|a| a.iter().filter_map(|x| x.as_str().map(String::from)).collect()).unwrap_or_default();
            let tags = tag_names.iter().fold(0u32, |acc, t| acc | tag_bit(t));
            let keywords = rec
                .get("keywords")
                .and_then(|t| t.as_array())
                .map(|a| a.iter().filter_map(|x| x.as_str()).fold(0u32, |acc, k| acc | kw_bit(k)))
                .unwrap_or(0);
            let base = match &rec["base_strength"] {
                sj::Value::Number(n) => Some(n.as_i64().unwrap_or(0) as i32),
                _ => None,
            };
            let text = rec.get("text").and_then(|t| t.as_str()).unwrap_or("").to_string();
            let idx = list.len() as CardId;
            let id_for_kind = id.clone();
            let id_for_kind = id_for_kind.as_str();
            if let Some(m) = rec.get("mate").and_then(|m| m.as_str()) {
                mates.push((list.len(), m.to_string()));
            }
            by_id.insert(id.clone(), idx);
            let kw_names: Vec<&str> = rec.get("keywords").and_then(|t| t.as_array()).map(|a| a.iter().filter_map(|x| x.as_str()).collect()).unwrap_or_default();
            let is_ability = |t: &str| !kw_names.contains(&t) && !t.starts_with("Costs ");
            let has_ability = text.split('.').map(|t| t.trim()).filter(|t| !t.is_empty()).any(is_ability);
            let mut in_roar = false;
            let has_lasting_ability = text.split('.').map(|t| t.trim()).filter(|t| !t.is_empty()).any(|t| {
                if t.starts_with("Roar:") {
                    in_roar = true;
                } else if in_roar && LASTING_STARTS.iter().any(|s| t.starts_with(s)) {
                    in_roar = false;
                }
                !in_roar && is_ability(t)
            });
            let ability_profile = profile_of(&text, &kw_names, false);
            let lasting_profile = profile_of(&text, &kw_names, true);
            list.push(Card {
                idx,
                has_roar: text.contains("Roar:"),
                has_ability,
                has_lasting_ability,
                ability_profile,
                lasting_profile,
                id,
                name: rec.get("name").and_then(|t| t.as_str()).unwrap_or("").to_string(),
                status: rec.get("status").and_then(|t| t.as_str()).unwrap_or("").to_string(),
                rarity: rec.get("rarity").and_then(|t| t.as_str()).unwrap_or("").to_string(),
                tags,
                tag_names,
                base,
                dynamic: rec.get("dynamic_strength").and_then(|t| t.as_str()).map(String::from),
                keywords,
                food_cost: rec.get("food_cost").and_then(|t| t.as_i64()).unwrap_or(0) as i32,
                text,
                hungry: rec.get("hungry").and_then(|t| t.as_i64()).unwrap_or(0) as i32,
                mate: None,
                anthem_kind: ANTHEM_KINDS.iter().position(|n| *n == id_for_kind).unwrap_or(0) as u8,
                family_aura: FAMILY_AURAS.iter().position(|n| *n == id_for_kind).unwrap_or(0) as u8,
                keyword_aura: KEYWORD_AURAS.iter().position(|n| *n == id_for_kind).unwrap_or(0) as u8,
            });
        }
        for (i, m) in mates {
            list[i].mate = by_id.get(&m).copied();
        }
        let snames = list.iter().map(|c| crate::value::intern(&c.id)).collect();
        Ok(Cards { list, by_id, snames })
    }
    pub fn get(&self, id: CardId) -> &Card {
        &self.list[id as usize]
    }
    pub fn id_of(&self, name: &str) -> Option<CardId> {
        self.by_id.get(name).copied()
    }
    pub fn name_of(&self, id: CardId) -> &'static str {
        self.snames[id as usize]
    }
}

#[derive(Clone, Debug)]
pub struct Region {
    pub id: String,
    pub corners: Vec<Cr>,
    pub food: i32,
}

pub struct GameMap {
    pub id: String,
    pub crossroads: Vec<String>, // index -> name
    pub snames: Vec<&'static str>,
    pub sorted: Vec<Cr>,         // crossroad indexes in name order (the Python engine iterates sorted names)
    pub by_name: FxHashMap<String, Cr>,
    pub adjacency: Vec<Vec<Cr>>, // sorted by neighbour name
    pub hq_front: [Vec<Cr>; 2],
    pub regions: Vec<Region>,
    pub region_masks: Vec<u32>,
    pub front_masks: [u32; 2],
    pub win_food: i32,
}

impl GameMap {
    pub fn from_json(rec: &sj::Value) -> Result<GameMap, String> {
        let names: Vec<String> = rec["crossroads"].as_array().ok_or("map without crossroads")?.iter().map(|x| x.as_str().unwrap().to_string()).collect();
        let mut by_name = FxHashMap::default();
        for (i, n) in names.iter().enumerate() {
            by_name.insert(n.clone(), i as Cr);
        }
        let mut adjacency: Vec<Vec<Cr>> = vec![Vec::new(); names.len()];
        for e in rec["edges"].as_array().unwrap() {
            let a = by_name[e[0].as_str().unwrap()];
            let b = by_name[e[1].as_str().unwrap()];
            adjacency[a as usize].push(b);
            adjacency[b as usize].push(a);
        }
        for adj in adjacency.iter_mut() {
            adj.sort_by(|x, y| names[*x as usize].cmp(&names[*y as usize]));
            adj.dedup();
        }
        let mut sorted: Vec<Cr> = (0..names.len() as Cr).collect();
        sorted.sort_by(|x, y| names[*x as usize].cmp(&names[*y as usize]));
        let front = |p: &str| -> Vec<Cr> {
            let mut v: Vec<Cr> = rec["hqs"][p]["connects"].as_array().unwrap().iter().map(|x| by_name[x.as_str().unwrap()]).collect();
            v.sort_by(|x, y| names[*x as usize].cmp(&names[*y as usize]));
            v
        };
        let mut regions = Vec::new();
        for (rid, r) in rec["regions"].as_object().unwrap() {
            regions.push(Region {
                id: rid.clone(),
                corners: r["corners"].as_array().unwrap().iter().map(|x| by_name[x.as_str().unwrap()]).collect(),
                food: r["food"].as_i64().unwrap() as i32,
            });
        }
        let fa = front("A");
        let fb = front("B");
        let front_masks = [fa.iter().fold(0u32, |m, c| m | (1 << c)), fb.iter().fold(0u32, |m, c| m | (1 << c))];
        Ok(GameMap {
            id: rec["id"].as_str().unwrap().to_string(),
            hq_front: [fa, fb],
            region_masks: regions.iter().map(|r| r.corners.iter().fold(0u32, |m, c| m | (1 << c))).collect(),
            front_masks,
            snames: names.iter().map(|n| crate::value::intern(n)).collect(),
            crossroads: names,
            sorted,
            by_name,
            adjacency,
            regions,
            win_food: rec["win_food"].as_i64().unwrap() as i32,
        })
    }
    pub fn n(&self) -> usize {
        self.crossroads.len()
    }
    pub fn name(&self, cr: Cr) -> &'static str {
        self.snames[cr as usize]
    }
    pub fn cr(&self, name: &str) -> Option<Cr> {
        self.by_name.get(name).copied()
    }
    pub fn neighbors(&self, cr: Cr) -> &[Cr] {
        &self.adjacency[cr as usize]
    }
    pub fn adjacent(&self, a: Cr, b: Cr) -> bool {
        self.adjacency[a as usize].contains(&b)
    }
    pub fn front(&self, p: Player) -> &[Cr] {
        &self.hq_front[p as usize]
    }
    pub fn in_front(&self, p: Player, cr: Cr) -> bool {
        self.hq_front[p as usize].contains(&cr)
    }
}

/// The Python Config dataclass as a name -> value table, with the hot fields cached.
pub struct Config {
    pub raw: sj::Map<String, sj::Value>,
    pub actions_per_turn: i32,
    pub first_turn_actions: i32,
    pub hand_limit: i32,
    pub draw_action_count: i32,
    pub max_turns: i32,
    pub reach: i32,
    pub mulligan: bool,
    pub mulligan_max: Option<i32>,
    pub first_player_opening_draw: i32,
    pub second_player_opening_draw: i32,
    pub jelly_grant: i32,
    pub egg_eater_growth: i32,
    pub capybara_small_max: i32,
}

impl Config {
    pub fn from_json(v: &sj::Value) -> Result<Config, String> {
        let raw = v.as_object().ok_or("config must be a dict")?.clone();
        let gi = |k: &str, d: i64| raw.get(k).and_then(|x| x.as_i64()).unwrap_or(d) as i32;
        Ok(Config {
            actions_per_turn: gi("actions_per_turn", 2),
            first_turn_actions: gi("first_turn_actions", 1),
            hand_limit: gi("hand_limit", 10),
            draw_action_count: gi("draw_action_count", 2),
            max_turns: gi("max_turns", 400),
            reach: gi("reach", 2),
            mulligan: raw.get("mulligan").and_then(|x| x.as_bool()).unwrap_or(true),
            mulligan_max: raw.get("mulligan_max").and_then(|x| x.as_i64()).map(|x| x as i32),
            first_player_opening_draw: gi("first_player_opening_draw", 4),
            second_player_opening_draw: gi("second_player_opening_draw", 4),
            jelly_grant: gi("jelly_grant", 2),
            egg_eater_growth: gi("egg_eater_growth", 2),
            capybara_small_max: gi("capybara_small_max", 3),
            raw,
        })
    }
    pub fn int(&self, k: &str) -> i32 {
        match self.raw.get(k) {
            Some(sj::Value::Number(n)) => n.as_i64().unwrap_or(0) as i32,
            Some(sj::Value::Bool(b)) => *b as i32,
            _ => panic!("unknown Config field {k:?}"),
        }
    }
    pub fn flag(&self, k: &str) -> bool {
        match self.raw.get(k) {
            Some(sj::Value::Bool(b)) => *b,
            Some(sj::Value::Number(n)) => n.as_i64().unwrap_or(0) != 0,
            _ => false,
        }
    }
    pub fn mulligan_cap(&self, player: Player, first: Player) -> i32 {
        if let Some(m) = self.mulligan_max {
            return m;
        }
        if player == first {
            self.first_player_opening_draw
        } else {
            self.second_player_opening_draw
        }
    }
}
