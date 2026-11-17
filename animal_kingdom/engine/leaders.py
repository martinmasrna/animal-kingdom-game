"""Leaders (the leaders prototype, branch `leaders`; Martin, 2026-11-15): a deck may name one of its legendaries as its
leader. The leader sits on its player's den for the whole match and gives the deck a standing ability, in the manner of
Hearthstone Battlegrounds heroes; the legendary's own card stays in the deck as a normal card. Public information: both
players see both leaders and their state from the first turn.

A leader's ability is one of three kinds:
  - "power": a hero power. Pressing the den costs one of the turn's actions; it may be pressed again the same turn.
  - "once": the same, usable once in the match.
  - "passive": always on; nothing to press.

The data lives here (no engine imports); the behaviour is in effects.py (`legal_leader`, `do_leader` and the passives'
hooks), strength.py (the strength passives) and the Rust twin (engine_rs/src/leaders.rs). A deck with no leader plays as
it always has.

State (GameState.leaders): player -> {"id": the leader's card id, "kills": the enemies its power counts (Grimm: every
enemy removed from the board),
"stage": how many Dawns Xanthe's leader has evolved (0 Egg .. 4 Monarch), or how many of her three uses Yuki has spent, "spent": whether a once-per-game power was
used}. Every key is there for every leader, so the two engines serialise it alike.
"""

from __future__ import annotations

ADIRA = "lion_legend_4"
THERON = "lion_legend_3"
JULIETTE = "bee_legend_2"
BUMBLETON = "bumblebee_legend"
MELISSIA = "bee_legend"
SOLENIA = "army_ant_legend"
BABAJI = "baboon_legend"
XANTHE = "butterfly_legend"
ARNE = "eagle_legend"
GORILLA = "gorilla_legend_2"
GRIMM = "raven_legend"
MOLE = "mole_legend"
SANTO = "macaque_legend"
YUKI = "squirrel_legend"
ASH = "honey_badger_legend"

# card id -> (kind, the ability as the player reads it)
LEADERS: dict[str, tuple[str, str]] = {
    # The two Cat leaders (Martin, 2026-11-17): the same deck, Adira slowly to food, Theron fast and on the attack.
    ADIRA: ("passive", "When one of your Cats covers an enemy, gain 5 food."),
    THERON: ("passive", "When one of your Cats covers an enemy, give it +1 strength."),
    JULIETTE: ("passive", "If your starting deck has no animals of strength 4 or more, your animals have +1 strength."),
    BUMBLETON: ("passive", "Whenever you gain food, gain 1 food."),
    MELISSIA: ("power", "Scout a Worker, Soldier or Nurse Colony animal."),
    SOLENIA: ("passive", "Dusk: gain 1 food for each animal you control."),
    BABAJI: ("power", "Scout an animal and give it +1 strength."),
    XANTHE: ("once", "Evolves at each of your Dawns: Egg, Caterpillar, Chrysalis, Butterfly, Monarch. Use it once, for what its stage offers then."),
    ARNE: ("passive", "Copies of the same animal in your hand share their strength."),
    GORILLA: ("passive", "The first animal you play each turn has +1 strength."),
    # the den-rush leader (Martin, 2026-11-17): it pays only through the cards that give an extra play
    MOLE: ("passive", "When you play your third animal in a turn, draw an animal."),
    # the empty-hand berserker, den rush led the other way (Martin, 2026-11-17: "You last animal in hand has +3 strength")
    SANTO: ("passive", "Your last animal in hand has +3 strength."),
    # the one big turn (Martin, 2026-11-17): three uses a match, shown as "Left: 3/3"
    YUKI: ("power", "Choose a connected ally. It can't be covered until your next turn."),
    # the wall that pays for standing (Martin, 2026-11-17: his wording)
    ASH: ("passive", "Dusk: gain 1 food for each Poison, Spikes, Armor and Stealth on your animals. Animals adjacent to enemies earn double."),
    GRIMM: ("power", "Draw 2 animals. Draws one more animal for every 5 enemies removed this match."),   # Adira's first power, without the Cats (Martin, 2026-11-17)
}

# Xanthe's leader, stage by stage: (name, what her once-per-game power does then, or None: nothing to use).
XANTHE_STAGES: tuple[tuple[str, str | None], ...] = (
    ("Egg", None),
    ("Caterpillar", "Draw an animal."),
    ("Chrysalis", None),
    ("Butterfly", "Draw an animal, then give an animal in your hand +1 strength."),
    ("Monarch", "Draw an animal and give all animals in your hand +1 strength."),
)

# Melissia's power: a Colony animal that is a Worker, a Soldier or a Nurse (effects._matches: "|" is "or").
MELISSIA_SPEC = "tag:Colony&tag:Worker|tag:Colony&tag:Soldier|tag:Colony&tag:Nurse"

# Lady Juliette's card: the twelve small animals her wish shows three of (Martin, 2026-11-15), made for the occasion.
JULIETTE_WISHES: tuple[str, ...] = (
    "honey_badger", "hercules_beetle", "electric_eel", "capybara", "dart_frog", "impala",
    "hummingbird", "meerkat", "magpie", "flying_squirrel", "macaw", "cuckoo",
)


def leader_state(card_id: str) -> dict:
    """A leader at the start of a match."""
    return {"id": card_id, "kills": 0, "stage": 0, "spent": False}


def leader_problem(card_id: str | None, decklist) -> str | None:
    """Why `card_id` can't lead `decklist`, or None when it can (None leads nothing: always fine)."""
    if card_id is None:
        return None
    if card_id not in LEADERS:
        return f"{card_id!r} is not a leader"
    if card_id not in decklist:
        return f"the leader {card_id!r} must be in its deck"
    return None


def kind_of(card_id: str) -> str:
    return LEADERS[card_id][0]
