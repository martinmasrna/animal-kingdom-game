"""Leaders: every deck names one of its legendaries as its leader. The leader stands beside its player's den for the whole
match with an ability of its own, public to both players; its card stays in the deck as a normal card.

An ability is a "power" (used for its mana, effects.power_cost, once a turn) or a "passive" (always on). The
behaviour is in effects.py. State (GameState.leaders): player -> {"id": the leader's card id}.
"""

from __future__ import annotations

WARLORD = "warlord_legend"
RAIDER = "raider_legend"
SAGE = "sage_legend"
ELF = "elf_legend"
ASSASSIN = "assassin_legend"

# card id -> (kind, the ability as the player reads it)
LEADERS: dict[str, tuple[str, str]] = {
    WARLORD: ("passive", "When you cover an enemy, gain 1 food."),
    RAIDER: ("passive", "Your raids destroy 1 more food."),
    SAGE: ("power", "Draw a card."),
    ELF: ("power", "Gain 1 food for each region you control."),                  # Martin, 2026-11-21: 2 mana
    ASSASSIN: ("passive", "After you play your third card in a turn, draw a card."),   # Martin, 2026-11-21
}


def leader_problem(card_id: str | None, decklist) -> str | None:
    """Why `card_id` can't lead `decklist`, or None when it can."""
    if card_id is None:
        return "a deck needs a leader"
    if card_id not in LEADERS:
        return f"{card_id!r} is not a leader"
    if card_id not in decklist:
        return f"the leader {card_id!r} must be in its deck"
    return None


def kind_of(card_id: str) -> str:
    return LEADERS[card_id][0]
