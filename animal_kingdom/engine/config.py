"""Tunable constants in one place (handoff §11).

These are deliberately *untuned placeholders* (cards.md §4.5, todo.md). The whole
point of the simulator is to sweep these together on one shared food scale, so every
magic number that a card effect or rule depends on lives here - never hard-coded in
effect logic. `win_food` and region outputs are map-defined (see data/maps.json); the
mirror here is only a fallback/default for maps that omit them.

Build a Config once (usually `Config.default()`) and thread it through the engine.
The sim can construct variant Configs to sweep balance dials.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Config:
    # --- One-off food values on cards (cards.md §4.5 "Food Economy Constants") ---
    f_plain: int = 4          # Army Ant, Vervet Monkey, Caracal
    f_low: int = 3            # Wild Boar
    f_med: int = 5            # Chipmunk
    f_high: int = 8           # Squirrel, Honeybee (base)
    honeybee_insect_bonus: int = 4    # Honeybee, extra if you control another Insect
    queen_bee_bonus: int = 3          # additive, per food-gain event  (⚠ stacking dial)
    driver_ant_per_unit: int = 2      # Driver Ant Queen, per unit you control (⚠ scaling dial)
    raven_cost: int = 12              # Raven, food cost to play

    # --- Delayed / multi-turn effects ---
    hibernating_bear_multiplier: int = 2   # payout = stored_food * multiplier
    hibernating_bear_delay: int = 2        # turns (of the owner) until payout
    egg_delay: int = 2                     # turns until Egg hatches
    egg_draw: int = 2                      # cards drawn when Egg hatches
    rabbit_draw_delay: int = 1             # Rabbit: draw a Rabbit at start of next turn

    # --- Threshold dials (sim should sweep) ---
    spotted_hyena_threshold: int = 4   # other units controlled to unlock "cover any" (sweep ~3-5)

    # Region outputs and win_food are map-defined (data/maps.json) and intentionally
    # not duplicated here - maps are the single source of truth for board food.

    # --- Core rules constants (overview.md) ---
    hand_limit: int = 8                # max hand size (overview.md §3.5)
    first_player_opening_draw: int = 3 # overview.md §4.3
    second_player_opening_draw: int = 4
    draw_action_count: int = 2         # "Draw 2 cards" (overview.md §5)

    # --- Engine safety / sim hygiene ---
    max_turns: int = 400               # hard cap so fuzz games always terminate (M1)

    @staticmethod
    def default() -> "Config":
        """The v0 placeholder constants (cards.md §4.5)."""
        return Config()

    def sweep(self, **overrides) -> "Config":
        """Return a copy with the given fields overridden (for balance sweeps)."""
        return replace(self, **overrides)
