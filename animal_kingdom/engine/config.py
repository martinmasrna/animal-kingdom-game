"""Tunable constants in one place (handoff §11; memory data-architecture-decision).

These are deliberately *untuned placeholders* for the reworked pool (decisions G/H are a
sim job - see docs/balance/backlog.md). The whole point of the simulator is to sweep them together on one
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
    squirrel_food: int = 10              # trimmed from 12 in the 2026-07-05 balance pass
    chipmunk_food_now: int = 10          # decision H: doubled, same reasoning
    chipmunk_food_later: int = 10        # paid at the start of the owner's next turn (doubled)
    flying_squirrel_food: int = 8        # decision H: doubled, same reasoning
    hedgehog_food: int = 5               # Immovable wall that also feeds (food_otk 2026-07-05)
    rat_king_per_rodent: int = 4         # Battlecry: gain N food per OTHER Rodent you control
    worker_ant_food: int = 12            # trimmed from 15 in the 2026-07-05 balance pass
    worker_bee_food: int = 10            # 5→10; +worker_bee_extra if you control another Worker
    worker_bee_extra: int = 10           # 5→10
    worker_wasp_food: int = 3            # at end of your turn
    methuselah_food: int = 5             # at end of your turn (decision H: 10 was 2x any other
                                          # recurring passive in the pool - ruled down 2026-07-02)
    greywhisker_food: int = 1            # Battlecry: gain 1 food (+ draw 1, + play 1 more)
    opossum_food: int = 5                # food_otk OTK-lean pass 2026-07-04: Battlecry now also
                                          # gains food (was draw-1 only) - recyclable via its own
                                          # Deathrattle-return, so this compounds through Carmilla/
                                          # Black Widow sac loops into what Scrooge later doubles
    queen_marabunta_per_colony: int = 4  # per other friendly Colony unit
    queen_honoria_per_play: int = 4      # per Colony unit you play (5→4, 2026-07-05)
    falstaff_food_rider: int = 3         # extra food whenever you gain food

    # --- "Food gained this turn" signature mechanic (food_otk pure-OTK overhaul 2026-07-05) ---
    # A shared threshold read by Hamster/Muskrat/Groundhog; Scrooge instead doubles the raw haul.
    fed_threshold: int = 10              # food gained this turn to arm Hamster/Muskrat/Groundhog
    hamster_draw: int = 2               # Hamster: draw N if fed this turn
    groundhog_strength: int = 5         # Groundhog: +N strength (stored) if fed this turn
    scrooge_gain_multiplier: int = 1    # Scrooge: gain (food gained this turn) x this
    chinchilla_bonus_actions: int = 1   # Chinchilla: extra top-level actions on your NEXT turn

    # --- Food-event engine reactors (decision F2/F9; magnitudes are dials) ---
    eon_food: int = 1                    # per draw/shuffle/remove event
    vulture_food: int = 5                # per card removed
    egg_eater_food: int = 10             # per Egg removed
    jackal_food: int = 5                 # per adjacent removal (3→5, 2026-07-05; body 3→5)

    # --- Deathrattle / payoff food ---
    gazelle_food: int = 30               # Deathrattle: gain food. Was 40 (doubled 2026-07-02);
                                          # trimmed 2026-07-04 as part of the OTK-lean pass - the
                                          # single-hit swing overshadowed Impala's draw-2 payoff,
                                          # and the budget moved into Opossum/Tortoise/Porcupine/
                                          # Pufferfish so the deck survives to cash in Scrooge at all
    fig_tree_food: int = 20              # Landmark: gain food next turn

    # --- Strength anthems ("has +X", live; decision E) ---
    anthem_lobo_per: int = 2             # per other Canine you control
    anthem_verminus_per: int = 1         # per other unit you control
    anthem_vesper_per: int = 2           # per other friendly Colony unit
    raksha_anthem: int = 1               # your other Canines have +X (2→1, 2026-07-05; body 4→5 to compensate)
    guard_hornet_bonus: int = 5          # while >= threshold Colony units
    guard_hornet_colony_threshold: int = 5

    # --- Strength counters ("give +X", stored on the instance; decision E) ---
    dhole_grant: int = 3                 # to adjacent friendly Canines (2→3, 2026-07-05); reserve
    clarion_grant: int = 2               # to all other friendly Canines on board (+1→+2, body 4→2, 2026-07-05)
    red_wolf_grant: int = 1              # to each other Canine that enters play (reworked 2026-07-05)
    dingo_grant: int = 1                 # to a friendly adjacent Canine, end of turn
    bush_dog_grant: int = 1              # to friendly adjacent Canines, on gaining strength
    shuck_grant: int = 2                 # to the Canine returned from the Remove Pile; reserve

    # --- Token spawns (Canine go-wide; 2026-07-05) ---
    alpha_pups: int = 2                  # Pups Alpha places on adjacent empty crossroads
    awd_pups: int = 1                    # Pups African Wild Dog spawns on placement

    # --- Thresholds / strength gates ---
    coyote_draw_threshold: int = 5       # draw if Coyote has >= this strength
    colony_synergy_threshold: int = 5    # Guard Hornet / Soldier Ant / Nurse Bumblebee "5+ Colony"

    # --- Removal-strength caps on Battlecry removals ---
    jaguar_max: int = 5
    serval_min: int = 6                  # removes an enemy of strength >= this
    stoop_max: int = 4                   # card-balance-todo: Stoop moved to egg_control as a rare,
                                          # 6→4 (id kept as "stoop"; printed name "Peregrine Falcon")
    rhinoceros_max: int = 3              # proactive Battlecry mirror of Hippopotamus (5→3, 2026-07-05)
    hippopotamus_max: int = 3

    # --- Placement costs (decision F) ---
    costs_20_food: int = 20              # the "Costs 20 food" bodies (Borealis/Aquila/Bulwark/Elephant)

    # --- Delayed / multi-turn effects (scheduler; "your turns" are 2 apart) ---
    egg_hatch_delay: int = 2             # Bird/Snake Egg: turns until hatch
    egg_hatch_draw: int = 2              # cards drawn when an Egg hatches
    black_bear_delay: int = 2           # turns until Black Bear draws
    black_bear_draw: int = 1
    grizzly_bear_delay: int = 2         # turns until Grizzly Bear's random adjacent removal

    # --- Once-per-turn caps (decision G; dials for the sim - see docs/balance/backlog.md for the
    # per-card default ruling and the data behind it) ---
    cap_queen_adira: bool = False
    # Fox draws on EVERY strength gain (printed cap dropped 2026-07-05); set True to restore the
    # old once-per-turn cap. Fox draws only, so uncapping cannot create a grant->gain->grant loop.
    fox_gain_once: bool = False
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
    draw_action_count: int = 1           # cards drawn by one Draw action (overview.md §5)
    actions_per_turn: int = 2            # top-level actions (place/draw) per turn (overview.md §5)

    # --- Engine safety / sim hygiene ---
    max_turns: int = 400                 # hard cap so fuzz games always terminate (M1)

    @staticmethod
    def default() -> "Config":
        """The v0 placeholder constants for the reworked pool (untuned; see docs/balance/backlog.md G/H)."""
        return Config()

    def sweep(self, **overrides) -> "Config":
        """Return a copy with the given fields overridden (for balance sweeps)."""
        return replace(self, **overrides)


def load_config_overrides(path: Optional[str]) -> Optional[Config]:
    """Load a JSON dict of `Config` field overrides; unspecified fields keep defaults.

    Shared by every CLI's `--config` flag. `None`, `''`, and `'none'` mean "no overrides"
    (return None ⇒ callers fall back to `Config.default()`, the shipped ruleset).
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
