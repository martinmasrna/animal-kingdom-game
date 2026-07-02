"""Tunable constants in one place (handoff §11; memory data-architecture-decision).

These are deliberately *untuned placeholders* for the reworked pool (decisions G/H are a
sim job - see todo.md). The whole point of the simulator is to sweep them together on one
shared food scale, so every magic number a card effect or rule depends on lives here -
never hard-coded in effect logic. Card text is the source of the *defaults*; the sim
re-derives the real values against `win_food` (100) and region output (data/maps.json).

Build a Config once (usually `Config.default()`) and thread it through the engine. The sim
constructs variant Configs via `sweep(**overrides)` to explore balance dials.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields, replace
from typing import Optional


@dataclass(frozen=True)
class Config:
    # --- One-off food gains on placement (Battlecry "gain N food") ---
    squirrel_food: int = 12              # decision H: doubled 2026-07-02 - food_otk's guaranteed
                                          # one-off floor was ~40% of the v0 "accelerant reaches
                                          # ~half of win_food" target; see docs/todo.md
    chipmunk_food_now: int = 10          # decision H: doubled, same reasoning
    chipmunk_food_later: int = 10        # paid at the start of the owner's next turn (doubled)
    flying_squirrel_food: int = 8        # decision H: doubled, same reasoning
    worker_ant_food: int = 8
    worker_bee_food: int = 5             # +worker_bee_extra if you control another Worker
    worker_bee_extra: int = 5
    worker_wasp_food: int = 3            # at end of your turn
    methuselah_food: int = 5             # at end of your turn (decision H: 10 was 2x any other
                                          # recurring passive in the pool - ruled down 2026-07-02)
    greywhisker_food: int = 1            # Battlecry: gain 1 food (+ draw 1, + play 1 more)
    queen_marabunta_per_colony: int = 4  # per other friendly Colony unit
    queen_honoria_per_play: int = 5      # per Colony unit you play
    falstaff_food_rider: int = 3         # extra food whenever you gain food

    # --- Food-event engine reactors (decision F2/F9; magnitudes are dials) ---
    eon_food: int = 1                    # per draw/shuffle/remove event
    vulture_food: int = 5                # per card removed
    egg_eater_food: int = 10             # per Egg removed
    jackal_food: int = 3                 # per adjacent removal

    # --- Deathrattle / payoff food ---
    gazelle_food: int = 40               # Deathrattle: gain food (decision H: doubled 2026-07-02,
                                          # same food_otk-buff reasoning as the rodent one-offs)
    fig_tree_food: int = 20              # Landmark: gain food next turn

    # --- Strength anthems ("has +X", live; decision E) ---
    anthem_lobo_per: int = 2             # per other Canine you control
    anthem_awd_per: int = 1              # African Wild Dog, per friendly Canine
    anthem_verminus_per: int = 1         # per other unit you control
    anthem_vesper_per: int = 2           # per other friendly Colony unit
    raksha_anthem: int = 2               # your other Canines have +X
    guard_hornet_bonus: int = 5          # while >= threshold Colony units
    guard_hornet_colony_threshold: int = 5

    # --- Strength counters ("give +X", stored on the instance; decision E) ---
    dhole_grant: int = 2                 # to adjacent friendly Canines
    clarion_grant: int = 1               # to other Canines in hand + battlefield
    red_wolf_grant: int = 1              # to Canines in hand
    dingo_grant: int = 1                 # to a friendly adjacent Canine, end of turn
    bush_dog_grant: int = 1              # to friendly adjacent Canines, on gaining strength
    shuck_grant: int = 2                 # to the Canine returned from the Remove Pile

    # --- Thresholds / strength gates ---
    coyote_draw_threshold: int = 5       # draw if Coyote has >= this strength
    colony_synergy_threshold: int = 5    # Guard Hornet / Soldier Ant / Nurse Bumblebee "5+ Colony"

    # --- Removal-strength caps on Battlecry removals ---
    jaguar_max: int = 5
    serval_min: int = 6                  # removes an enemy of strength >= this
    stoop_max: int = 6
    rhinoceros_max: int = 5
    hippopotamus_max: int = 3

    # --- Placement costs (decision F) ---
    costs_20_food: int = 20              # the "Costs 20 food" bodies (Borealis/Aquila/Bulwark/Elephant)

    # --- Delayed / multi-turn effects (scheduler; "your turns" are 2 apart) ---
    egg_hatch_delay: int = 2             # Bird/Snake Egg: turns until hatch
    egg_hatch_draw: int = 2              # cards drawn when an Egg hatches
    black_bear_delay: int = 2           # turns until Black Bear draws
    black_bear_draw: int = 1
    grizzly_bear_delay: int = 2         # turns until Grizzly Bear's random adjacent removal
    scrooge_delay: int = 2              # turns until Scrooge's banked food returns
    scrooge_multiplier: int = 2         # banked food returns x this

    # --- Once-per-turn caps (decision G; dials for the sim - see docs/todo.md for the
    # per-card default ruling and the data behind it) ---
    cap_queen_adira: bool = False
    cap_eon: bool = False
    cap_vulture: bool = False
    cap_jackal: bool = False
    cap_queen_honoria: bool = False
    cap_falstaff: bool = False
    cap_king_theron: bool = False
    cap_egg_eater: bool = False

    # Region outputs and win_food are map-defined (data/maps.json) and intentionally not
    # duplicated here - maps are the single source of truth for board food.

    # --- Core rules constants (overview.md) ---
    hand_limit: int = 8                  # max hand size (overview.md §3.5)
    first_player_opening_draw: int = 3   # overview.md §4.3
    second_player_opening_draw: int = 4
    draw_action_count: int = 2           # "Draw 2 cards" (overview.md §5)
    actions_per_turn: int = 1            # top-level actions (place/draw) per turn; the
                                          # 2-action variant pairs this with draw_action_count=1

    # --- Engine safety / sim hygiene ---
    max_turns: int = 400                 # hard cap so fuzz games always terminate (M1)

    @staticmethod
    def default() -> "Config":
        """The v0 placeholder constants for the reworked pool (untuned; see todo.md G/H)."""
        return Config()

    def sweep(self, **overrides) -> "Config":
        """Return a copy with the given fields overridden (for balance sweeps)."""
        return replace(self, **overrides)


def load_config_overrides(path: Optional[str]) -> Optional[Config]:
    """Load a JSON dict of `Config` field overrides; unspecified fields keep defaults.

    Shared by every CLI's `--config` flag. `None`, `''`, and `'none'` mean "no overrides"
    (return None ⇒ callers fall back to `Config.default()`), so wrapper scripts can inject
    a default preset that a later `--config none` still overrides back to baseline.
    """
    if path is None or path.strip().lower() in ("", "none"):
        return None
    with open(path) as f:
        raw = json.load(f)
    overrides = {k: v for k, v in raw.items() if not k.startswith("_")}  # "_comment" etc.
    valid = {f.name for f in fields(Config)}
    unknown = set(overrides) - valid
    if unknown:
        raise SystemExit(f"unknown Config field(s) in {path}: {sorted(unknown)}")
    return Config.default().sweep(**overrides)
