"""The rules' numbers in one place. Build a Config once (`Config()`) and thread it through the engine; the map holds the
board's own numbers (each region's food, the food that wins: data/maps.json)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class Config:
    # Mana: on a player's Nth own turn they have min(N, mana_cap), lost at the end of the turn. Playing a card from hand
    # costs its card's `cost`; a leader's power costs leader_power_cost.
    mana_cap: int = 10                   # Martin, 2026-11-20: "Mana cap at 10 of course"
    leader_power_cost: int = 3

    # The food race (Martin, 2026-11-20: "both players starting at 15, you need 30 to win, and if you drop to 0 you
    # lost"): a raid destroys food; each region a player holds pays its food at the end of their turn.
    start_food: int = 15

    hand_limit: int = 10                 # past it, the newest cards drawn burn
    first_player_opening_draw: int = 3   # Martin, 2026-11-20: "make it 3 for first and 4 for second"
    second_player_opening_draw: int = 4
    mulligan: bool = True                # a blacklist mulligan, both players at once
    turn_draw_count: int = 1             # the free card at the start of each turn, the first player's first included (Martin, 2026-11-21)

    hungry_food: int = 1                 # Hungry: the food its prey's removal gains (Martin, 2026-11-20)
    shade_growth: int = 1                # the Shades: +1 strength for each of their count
    warlord_leader_food: int = 1         # the Warlord: "When you cover an enemy, gain 1 food."
    elf_power_cost: int = 2              # the Elf's power: "Gain 1 food for each region you control." (Martin, 2026-11-21)
    elf_food_per_region: int = 1
    assassin_nth_card: int = 3           # the Assassin: "After you play your third card in a turn, draw a card."
    raider_leader_bonus: int = 1         # the Raider: "Your raids destroy 1 more food." (Martin, 2026-11-21: "only +1")
    mama_spores: int = 2                 # Mama Spore: "Roar: put 2 Spores into your hand." (Martin, 2026-11-21)
    crush_max: int = 5                   # the Rhino: "remove all adjacent enemies with strength 5 or less"
    crush_albatross_max: int = 4         # the Albatross: "... with strength 4 or less" (Martin, 2026-11-21)
    crush_young_max: int = 3             # the Young Rhino: "... with strength 3 or less" (Martin, 2026-11-21)
    crush_young_albatross_max: int = 2   # the Young Albatross: "... with strength 2 or less" (Martin, 2026-11-21)
    scout_look: int = 3                  # Scout: the cards of your deck's top it looks at (the old game's Scout, Martin, 2026-11-21)
    double_raid_factor: int = 2          # "Its raids destroy double food." (Martin, 2026-11-21, his paper cards)

    # Safety caps, so a loop of effects can never hang a game.
    max_actions_per_turn: int = 30       # a turn ends after this many applied actions, choices included (Martin, 2026-11-18)
    max_effect_steps_per_turn: int = 1000
    max_turns: int = 400

    def mulligan_cap(self, player: str, first_player: str) -> int:
        """Cards a player may return in the mulligan: as many as their opening hand."""
        return self.first_player_opening_draw if player == first_player else self.second_player_opening_draw

    def sweep(self, **overrides) -> "Config":
        return replace(self, **overrides)


def for_log(log: Optional[dict] = None) -> Config:
    """The config a game log was played under (every log of these rules plays the defaults)."""
    return Config()
