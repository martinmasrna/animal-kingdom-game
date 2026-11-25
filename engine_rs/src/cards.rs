//! Card behaviour, keyed by card id (the EFFECTS, DJINN and DOUBLE_RAIDERS tables of the Python `engine/effects.py`):
//! what a card does when it is played (its Roar), when it covers an enemy, when it is removed, after it raids. The
//! effects themselves are in effects.rs; a card's numbers are in the card table or the Config, never here.

use crate::data::Count;

pub const WARLORD: &str = "warlord_legend";
pub const RAIDER: &str = "raider_legend";
pub const SAGE: &str = "sage_legend";
pub const ELF: &str = "elf_legend";
pub const ASSASSIN: &str = "assassin_legend";
pub const ANGEL: &str = "angel_legend";
pub const RENO: &str = "reno_legend";
pub const PYROMANCER: &str = "pyromancer_legend";
pub const MANA_EATER: &str = "mana_eater_legend";
/// What the Mage's card becomes once its owner's deck is empty.
pub const MAGE_TRANSFORMED: &str = "mage_transformed";
/// Gorrak's power summons it.
pub const DELICIOUS_FOOD: &str = "delicious_food";
/// The Fireballs, Baby to Elder: the Pyromancer's power gives one, his card upgrades them a step.
pub const FIREBALLS: [&str; 4] = ["flight_1", "flight_3", "flight_6", "flight_10"];
/// The Spores' token: in no deck, made by the Duplicating Spore and Mama Spore.
pub const SPORE: &str = "spore";
/// The Flight 1, which the Bird Egg hatches.
pub const FLIGHT_1: &str = "flight_1";

/// Every leader, in the order the game lists them, with its two abilities as the player reads them: its passive, always
/// on, and its power, used for its mana once a turn (Martin's list of 2026-11-25; Nightmare is the card raider_legend,
/// Mother Nature elf_legend, the Rogue assassin_legend, the Mage sage_legend, Gorrak warlord_legend). Either may be
/// missing.
pub const LEADERS: [(&str, Option<&str>, Option<&str>); 9] = [
    (RAIDER, Some("Nightmare starts on the bottom of your deck. Dusk: Gain +1 strength."), Some("Swap Nightmare with the card above.")),
    (ELF, Some("Your regions produce 1 more food."), Some("Gain 1 food for each region you control.")),
    (ANGEL, Some("After your ally removes an enemy, give it +1 strength."), Some("Give an ally +2 strength.")),
    (ASSASSIN, Some("Every third card you play costs 1 less."), Some("Give a card in your hand +1 strength for each card you played this turn.")),
    (SAGE, Some("Fatigue gains you food instead of losing it."), Some("Draw a card.")),
    (RENO, Some("If your deck has no duplicates, your \"draw a card\" effects Scout instead."), Some("Draw a card.")),
    (PYROMANCER, Some("Upgrade your hero power after 3 uses."), Some("Add a Fireball to your hand.")),
    (WARLORD, Some("Your Hungry allies cost 1 more, but gain 3 strength."), Some("Summon Delicious Food on a random empty crossroad.")),
    (MANA_EATER, Some("Start the game with 0 cards but 3 empty mana crystals."), Some("Next turn, gain 2 more mana.")),
];

/// Whether the leader `id` has a power.
pub fn has_power(id: &str) -> bool {
    LEADERS.iter().any(|&(l, _, power)| l == id && power.is_some())
}

/// The cards a card makes, which a card read large shows beside it (Martin, 2026-11-21: "same way it was in the original
/// game").
pub fn makes(id: &str) -> &'static [&'static str] {
    match id {
        "duplicating_spore" | "mama_spore" => &[SPORE],
        "bird_egg" => &[FLIGHT_1],
        SAGE => &[MAGE_TRANSFORMED],
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
    /// "Roar: put 2 Spores into your hand."
    MamaSpore,
    /// "Roar: If you played 3 or more cards this turn, draw 3 cards." (the Rogue's card)
    RogueCard,
    /// "Roar: Scout 2 cards." (Reno's card: Scout twice)
    ScoutTwice,
    /// "Roar: upgrade all Fireballs in your hand. They keep their cost." (the Pyromancer's card)
    UpgradeFireballs,
    /// "Hungry. Roar: destroy all your mana crystals. Gain 1 food for each." (the Mana Eater's card)
    EatCrystals,
    /// "Roar: double your food." (Mage, Transformed)
    DoubleFood,
    /// "Roar: gain 2 mana."
    GainMana,
    /// "Roar: adjacent units get -1 strength. Adjacent regions produce no food for the rest of the game." (the regions
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
    /// "Fall: gain 1 food." (Delicious Food)
    GainFood,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum OnRaid {
    /// "After it raids, draw a card."
    Draw,
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
    /// Whether the card may lead a deck.
    pub leader: bool,
    /// "Dawn: give all connected allies +1 strength." (the Angel Warrior's card)
    pub angel_dawn: bool,
    /// "Adjacent regions produce double food." while it is on the board (Mother Nature's card)
    pub double_regions: bool,
    /// "If your deck is empty, transform into Mage, Transformed." (the Mage's card)
    pub transforms: bool,
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
        ASSASSIN => Some(Roar::RogueCard),
        RENO => Some(Roar::ScoutTwice),
        PYROMANCER => Some(Roar::UpgradeFireballs),
        MANA_EATER => Some(Roar::EatCrystals),
        MAGE_TRANSFORMED => Some(Roar::DoubleFood),
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
        DELICIOUS_FOOD => Some(OnDeath::GainFood),
        _ => None,
    };
    b.on_raid = match id {
        "raid_draw_5" => Some(OnRaid::Draw),
        _ => None,
    };
    b.double_raider = id == RAIDER;                  // Nightmare: "Double strength when raiding." (Martin, 2026-11-22)
    b.djinn = match id {
        "djinn_hand" => Some(Count::Hand),
        "djinn_ally" => Some(Count::Ally),
        "djinn_combo" => Some(Count::Played),
        "djinn_region" => Some(Count::FoodProduced),
        "djinn_burn" => Some(Count::EnemyFoodLost),
        _ => None,
    };
    b.leader = LEADERS.iter().any(|&(l, _, _)| l == id);
    b.angel_dawn = id == ANGEL;
    b.double_regions = id == ELF;
    b.transforms = id == SAGE;
    b.draw_on_draw = id == "golden_egg";
    b.spikes_aura = id == "porcupine";
    b.raid_draw_aura = id == "plunderer";
    b
}
