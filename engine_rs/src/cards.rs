//! Card behaviour, keyed by card id (the EFFECTS, DJINN and DOUBLE_RAIDERS tables of the Python `engine/effects.py`):
//! what a card does when it is played (its Roar), when it covers an enemy, when it is removed, after it raids. The
//! effects themselves are in effects.rs; a card's numbers are in the card table or the Config, never here.

use crate::data::Count;

pub const WARLORD: &str = "warlord_legend";
pub const RAIDER: &str = "raider_legend";
pub const SAGE: &str = "sage_legend";
pub const ELF: &str = "elf_legend";
pub const ASSASSIN: &str = "assassin_legend";
/// The Spores' token: in no deck, made by the Duplicating Spore and Mama Spore.
pub const SPORE: &str = "spore";
/// The Flight 1, which the Bird Egg hatches.
pub const FLIGHT_1: &str = "flight_1";

/// Every leader, in the order the game lists them, with its ability as the player reads it. Whether an ability is a power
/// or a passive is in `behaviour`.
pub const LEADERS: [(&str, &str); 5] = [
    (WARLORD, "Your Hungry cards have +2 strength."),                          // Martin, 2026-11-24: "from hand" too
    (RAIDER, "Your opponent loses 1 food, and 1 more for every 3 raids you made this game."),   // Martin, 2026-11-24: 2 mana, a test
    (SAGE, "Draw a card."),
    (ELF, "Your regions produce 1 more food."),                               // Martin, 2026-11-23: the card's and the power's texts swapped
    (ASSASSIN, "After every third card you play in a turn, draw a card."),    // Martin, 2026-11-21: "multiple times a turn"
];

/// The cards a card makes, which a card read large shows beside it (Martin, 2026-11-21: "same way it was in the original
/// game").
pub fn makes(id: &str) -> &'static [&'static str] {
    match id {
        "duplicating_spore" | "mama_spore" => &[SPORE],
        "bird_egg" => &[FLIGHT_1],
        _ => &[],
    }
}

/// Which Config number a "remove all adjacent enemies with strength N or less" reads.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CrushLimit {
    Rhino,
    Albatross,
    YoungRhino,
    YoungAlbatross,
}

/// A Roar: what a card does as it lands from hand.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Roar {
    /// "Roar: give an adjacent enemy -N strength."
    Weaken(i32),
    /// "Roar: remove an adjacent enemy."
    RemoveAdjacent,
    /// "Roar: remove all adjacent enemies with strength N or less."
    Crush(CrushLimit),
    /// "Roar: draw a card."
    Draw,
    /// "Roar: Scout a card."
    Scout,
    /// "Roar: place a Spore on a random adjacent empty crossroad."
    Duplicate,
    /// "Roar: gain 2 food for each region you control." (the Elf's card)
    ElfCard,
    /// "Roar: put 2 Spores into your hand."
    MamaSpore,
    /// "Roar: reduce the cost of cards in your hand by 1."
    AssassinCard,
    /// "Roar: reduce the cost of your hero power by 1."
    SageCard,
    /// "Roar: gain 2 mana."
    GainMana,
    /// "Roar: adjacent enemies get -1 strength. Adjacent regions produce no food for the rest of the game." (the regions
    /// its tile is part of)
    Scorch,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OnCover {
    /// "Roar: if this removes an enemy, draw a card."
    DrawIfItRemoves,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OnDeath {
    /// "Death: draw a card."
    Draw,
    /// "Fall: add two [Flight 1] to your hand." (the Bird Egg)
    Hatch,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OnRaid {
    /// "After it raids, draw a card."
    Draw,
}

/// A leader's ability: a power is used for its mana once a turn, a passive is always on.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LeaderKind {
    Power,
    Passive,
}

#[derive(Clone, Copy, Debug, Default)]
pub struct Behaviour {
    pub on_place: Option<Roar>,
    pub on_cover: Option<OnCover>,
    pub on_death: Option<OnDeath>,
    /// "When you draw this, draw a card." (the Golden Egg)
    pub draw_on_draw: bool,
    /// "Adjacent allies have Spikes." while it is on the board (the Porcupine)
    pub spikes_aura: bool,
    /// "Whenever you raid, draw a card." while it is on the board (the Plunderer)
    pub raid_draw_aura: bool,
    pub on_raid: Option<OnRaid>,
    /// "Its raids destroy double food."
    pub double_raider: bool,
    /// A Djinn: "Costs N less for each ...".
    pub djinn: Option<Count>,
    /// Some when the card may lead a deck.
    pub leader: Option<LeaderKind>,
}

pub fn behaviour(id: &str) -> Behaviour {
    let mut b = Behaviour::default();
    b.on_place = match id {
        // The Hunters 1 to 6: each id is one above its number.
        "hunter_2" => Some(Roar::Weaken(1)),
        "hunter_3" => Some(Roar::Weaken(2)),
        "hunter_4" => Some(Roar::Weaken(3)),
        "hunter_5" => Some(Roar::Weaken(4)),
        "hunter_6" => Some(Roar::Weaken(5)),
        "hunter_7" => Some(Roar::Weaken(6)),
        WARLORD => Some(Roar::Weaken(7)),                // Gorrak One-Eye (Martin, 2026-11-22)
        "giant_hunter" => Some(Roar::RemoveAdjacent),
        "cantrip_2" | "cantrip_3" | "cantrip_4" => Some(Roar::Draw),
        "scout_3" => Some(Roar::Scout),
        "duplicating_spore" => Some(Roar::Duplicate),
        "assassin_legend" => Some(Roar::AssassinCard),
        "sage_legend" => Some(Roar::SageCard),
        ELF => Some(Roar::ElfCard),
        "mana_blob" => Some(Roar::GainMana),
        "scorch" => Some(Roar::Scorch),
        "rhino" => Some(Roar::Crush(CrushLimit::Rhino)),
        "albatross" => Some(Roar::Crush(CrushLimit::Albatross)),
        "young_rhino" => Some(Roar::Crush(CrushLimit::YoungRhino)),
        "young_albatross" => Some(Roar::Crush(CrushLimit::YoungAlbatross)),
        "mama_spore" => Some(Roar::MamaSpore),
        _ => None,
    };
    b.on_cover = match id {
        "kill_draw_2" => Some(OnCover::DrawIfItRemoves),
        _ => None,
    };
    b.on_death = match id {
        "death_draw_1" => Some(OnDeath::Draw),
        "bird_egg" => Some(OnDeath::Hatch),
        _ => None,
    };
    b.on_raid = match id {
        "raid_draw_5" => Some(OnRaid::Draw),
        _ => None,
    };
    b.double_raider = id == RAIDER;                  // Leeroy: "Double strength when raiding." (Martin, 2026-11-22)
    b.djinn = match id {
        "djinn_hand" => Some(Count::Hand),
        "djinn_ally" => Some(Count::Ally),
        "djinn_combo" => Some(Count::Played),
        "djinn_region" => Some(Count::FoodProduced),
        "djinn_burn" => Some(Count::EnemyFoodLost),
        _ => None,
    };
    b.leader = match id {
        WARLORD | ASSASSIN | ELF => Some(LeaderKind::Passive),
        SAGE | RAIDER => Some(LeaderKind::Power),
        _ => None,
    };
    b.draw_on_draw = id == "golden_egg";
    b.spikes_aura = id == "porcupine";
    b.raid_draw_aura = id == "plunderer";
    b
}
