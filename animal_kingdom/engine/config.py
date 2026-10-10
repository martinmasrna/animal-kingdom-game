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
    # --- One-off food gains on placement (Roar "gain N food") ---
    squirrel_food: int = 10              # trimmed from 12 in the 2026-07-05 balance pass
    chipmunk_food_now: int = 10          # Chipmunk: gain 10 now...
    chipmunk_food_later: int = 10         # ...and 10 more at the start of the owner's next turn
    flying_squirrel_food: int = 10       # synced to card text "gain 10 food" (was 8; text/const desync broke groundhog fed-threshold combo, 2026-07-09)
    hedgehog_food: int = 5               # Hedgehog: a spiny body that also feeds
    rat_king_per_rodent: int = 4         # Roar: gain N food per OTHER Rodent you control
    worker_ant_food: int = 12            # trimmed from 15 in the 2026-07-05 balance pass
    worker_bee_food: int = 10            # 5→10; +worker_bee_extra if you control another Worker
    worker_bee_extra: int = 10           # 5→10
    worker_wasp_food: int = 3            # at end of your turn
    methuselah_food: int = 5             # at end of your turn (decision H: 10 was 2x any other
                                          # recurring passive in the pool - ruled down 2026-07-02)
    methuselah_food_cap: int = 20        # Methuselah: each player gains at most this much food per turn
    greywhisker_food: int = 1            # Roar: gain 1 food (+ draw 1, + play 1 more, then discard 1)
    queen_marabunta_per_colony: int = 4  # per other friendly Colony unit
    queen_honoria_per_play: int = 4      # per Colony unit you play (5→4, 2026-07-05)
    falstaff_food_rider: int = 3         # extra food whenever you gain food

    # --- "Food gained this turn" signature mechanic (food_otk pure-OTK overhaul 2026-07-05) ---
    # A shared threshold read by Gopher/Muskrat/Groundhog; Scrooge instead doubles the raw haul.
    fed_threshold: int = 10              # food gained this turn to arm Gopher/Muskrat/Groundhog
    gopher_draw: int = 2                # Gopher: draw N if fed this turn
    groundhog_food: int = 10            # Groundhog: gain N food if fed this turn (was +5 str)
    scrooge_gain_multiplier: int = 1    # Scrooge: gain (food gained this turn) x this
    beaver_bonus_actions: int = 1       # Beaver: extra top-level actions on your NEXT turn

    # --- Food-event engine reactors (decision F2/F9; magnitudes are dials) ---
    eon_food: int = 1                    # per draw/shuffle/remove event
    egg_eater_growth: int = 2            # Egg Eater: +strength for each removed Egg

    # --- Payoff food ---
    gazelle_food: int = 5                # Gazelle: Roar: gain 5 food (its Flee brings the Roar back)
    sloth_food: int = 30                 # Sloth: gain food when its timer comes due
    sloth_delay: int = 2                 # owner-turns until Sloth pays out (ticks only while it is
                                          # top of its crossroad - see rules overview.md 9.1)

    # --- Strength anthems ("has +X", live; decision E) ---
    anthem_verminus_per: int = 1         # per other unit you control
    raksha_anthem: int = 1               # your other Canines have +X (2→1, 2026-07-05; body 4→5 to compensate)
    guard_hornet_bonus: int = 5          # while >= threshold Colony units
    guard_hornet_colony_threshold: int = 4
    mackerel_anthem: int = 1             # Mackerel: your other Fish have +1
    tuna_per_fish: int = 1               # Tuna: +1 for each other Fish you control
    grizzly_per_card: int = 1            # Grizzly Bear: +1 for each card in your hand
    giraffe_bonus: int = 5               # Giraffe: +5 during your opponent's turn
    moose_anthem: int = 1                # Moose: your other Hoofed animals have +1 during your opponent's turn
    boar_grazing_bonus: int = 3          # Boar: +3 while grazing

    # --- Strength counters ("give +X", stored on the instance; decision E) ---
    dingo_grant: int = 1                 # to every friendly adjacent Canine, end of turn
    bush_dog_grant: int = 3              # Bush Dog: Roar: give an adjacent Canine +3
    shuck_grant: int = 2                 # to the Canine returned from the Remove Pile; reserve
    raccoon_dog_grant: int = 1           # Raccoon Dog: an allied Canine that roams gets +1
    wolf_legend_grant: int = 2           # the legendary Wolf: when it roams, your adjacent animals gain +2
    stray_dog_grant: int = 2             # Stray Dog: give an ally with Roam +2, then it roams
    wild_dog_grant: int = 1              # African Wild Dog: Dusk: your adjacent animals +1
    mahi_mahi_grant: int = 1             # Mahi-mahi: Roar: your other Fish +1
    silverback_grant: int = 1            # Silverback: Roar: every animal in your hand +1
    baboon_grant: int = 1                # Baboon: Roar: 2 animals in your hand +1...
    baboon_count: int = 2                # ...this many of them
    baboon_legend_grant: int = 1         # the legendary Baboon: Dusk: 2 random animals in your hand +1...
    baboon_legend_count: int = 2         # ...this many
    tarsier_grant: int = 1               # Tarsier: the Primate it Scouts gets +1
    butterfly_grant: int = 1             # Butterfly (and the Chrysalis stage): an animal in your hand +1
    butterfly_legend_stage4_grant: int = 1   # the Butterfly stage: every animal in your hand +1
    butterfly_legend_stage5_grant: int = 2   # the Monarch stage: every animal in your hand +2
    butterfly_legend_stage5_draw: int = 2    # the Monarch stage: draw 2
    serval_set: int = 1                  # Serval: an adjacent enemy's strength becomes this

    # --- Token spawns (Canine go-wide; 2026-07-05) ---
    alpha_pups: int = 2                  # Pups Scarlett places on adjacent empty crossroads
    stork_younglings: int = 2            # Stork: random younglings added to your hand
    cuckoo_eggs: int = 2                 # Cuckoo: Cuckoo Eggs shuffled into your opponent's deck
    earthworm_worms: int = 2             # Earthworm: Worms placed on its crossroad when it's removed

    # --- Thresholds / strength gates ---
    unnamed_canine_draw_threshold: int = 5   # draw if Unnamed Canine has >= this strength
    colony_synergy_threshold: int = 4    # Guard Wasp / Soldier Ant / Nurse Bumblebee "4+ Colony"
    hare_played_min: int = 3             # Hare: draw if you played this many animals this turn
    macaque_hand_min: int = 5            # Macaque: remove if you have this many cards in hand
    gorilla_min: int = 8                 # Gorilla: draw if this has this much strength
    manta_legend_regions: int = 2        # the legendary Manta Ray: draw at Dusk with this many regions...
    manta_legend_draw: int = 2           # ...this many cards
    oxpecker_min: int = 8                # Oxpecker: count starting-deck animals of strength >= this

    # --- Removal-strength caps on Roar removals ---
    jaguar_max: int = 4
    honey_badger_min: int = 6            # Honey Badger removes an enemy of strength >= this
    stoop_max: int = 3                   # baseline-ruler tuning 2026-07-13: str 4→3, remove ≤4→≤3
                                          # (id kept as "stoop"; printed name "Hawk")
    rhinoceros_max: int = 2              # baseline-ruler tuning 2026-07-13: remove-all ≤3→≤2
    hippopotamus_max: int = 3
    cuckoo_legend_max: int = 4           # the legendary Cuckoo: removes an adjacent animal of strength <= this
    city_spider_max: int = 2             # City Spider: removes an animal of strength <= this placed adjacent
    calib_rm4_max: int = 4               # the calibration bodies' "strength 4 or less" (reserve, sim tools)
    calib_rm6_min: int = 6               # the calibration bodies' "strength 6 or more"

    # --- Draws, food and other magnitudes of the launch decks ---
    mantis_draw: int = 2                 # Praying Mantis: remove an adjacent ally to draw 2
    hyena_food_per: int = 3              # Hyena: Dusk: 3 food for each of your animals removed this turn
    hummingbird_draw: int = 2            # Hummingbird: Roar: draw 2
    termite_king_draw: int = 2           # Termite King: Roar: draw 2 if you control a Colony Queen
    mole_food: int = 5                   # Mole: gain 5 food...
    mole_draw: int = 2                   # ...and draw 2 if your hand is empty
    dormouse_food: int = 10              # Dormouse: Dusk: gain 10 if your hand is empty
    tuna_legend_food: int = 5            # the legendary Tuna: per region you control, a card and 5 food
    tortoise_per_armor: int = 5          # Tortoise: 5 food for each of your animals with Armor
    wildebeest_food: int = 5             # Wildebeest: at the end of your turn, if grazing, gain 5
    dung_beetle_per: int = 2             # Dung Beetle: 2 food for each Hungry animal you control
    otk_squirrel_multiplier: int = 3     # the legendary Squirrel: in 2 turns, gain three times the food it lost...
    otk_squirrel_delay: int = 2          # ...after this many of your turns (covering pauses it)
    migration_bonus: int = 5             # the legendary Wildebeest: your regions produce 5 more food
    boar_penalty: int = 5                # the legendary Boar: your opponent's regions produce 5 less food
    shark_reach: int = 3                 # Great White Shark: Reach 3 if an animal was removed this turn
    mosquito_drain: int = 2              # Mosquito: an adjacent enemy -2 strength

    # --- Placement costs (decision F) ---
    # NOTE: there is deliberately no constant here. A printed "Costs X food" is a card-intrinsic
    # field (`food_cost` in cards.json, gated in effects.py), like base_strength - tune it there.
    # A vestigial `costs_20_food = 20` lived here until 2026-07-15, unread by any code and stale
    # since a27f0df cut those bodies to 15; it could only mislead a Decision H re-derivation.

    # --- Delayed / multi-turn effects (scheduler; "your turns" are 2 apart) ---
    snake_egg_draw: int = 1              # Snake Egg's Roar: Snakes drawn at once
    egg_hatch_delay: int = 2             # Snake Egg: turns until it hatches
    egg_hatch_draw: int = 2              # Snakes drawn when a Snake Egg hatches
    bird_egg_hatch_delay: int = 1        # Bird Egg: turns until it hatches (and Scouts again)
    scout_count: int = 3                 # Scout: cards looked at, one drawn, the rest shuffled back
    black_bear_delay: int = 2           # turns until Black Bear draws
    black_bear_draw: int = 2            # baseline-ruler tuning 2026-07-13: 1→2 (draw-1 too weak vs draw-2 default)
    raven_draw: int = 3                 # Raven's Roar: cards drawn...
    raven_shuffle: int = 2              # ...then shuffled back from the hand
    nurse_bee_draw: int = 2             # Nurse Bee: drawn with two of the same Colony animal
    nurse_bumblebee_draw: int = 2       # Nurse Bumblebee: drawn with 4 or more Colony animals
    test_draw: int = 2                  # the mock and calibration cards' "draw 2 cards" (test fixtures)
    viper_poison: int = 3               # Viper's permanent strength loss on the bitten enemy
    black_mamba_max: int = 5                 # Black Mamba removes an adjacent enemy of at most this strength
    eon_decay: int = 1                  # Eon's strength lost each time it shuffles itself back

    # --- Once-per-turn caps (decision G; dials for the sim - see docs/balance/backlog.md for the
    # per-card default ruling and the data behind it) ---
    cap_queen_adira: bool = False
    cap_eon: bool = False
    cap_queen_honoria: bool = False
    cap_falstaff: bool = False
    cap_king_theron: bool = False

    # Region outputs and win_food are map-defined (data/maps.json) and intentionally not
    # duplicated here - maps are the single source of truth for board food.

    # --- Core rules constants (overview.md) ---
    hand_limit: int = 10                 # max hand size (overview.md §3.5)
    first_player_opening_draw: int = 3   # overview.md §4.3
    second_player_opening_draw: int = 4
    mulligan: bool = True                # overview.md §4.4: blacklist mulligan, first player first
    mulligan_max: Optional[int] = None   # returns per mulligan; None: as many as the player's opening hand, 3 first and 4
                                          # second (Hearthstone's rule, Martin 2026-10-01; was 3 for both)

    def mulligan_cap(self, player: str, first_player: str) -> int:
        if self.mulligan_max is not None:
            return self.mulligan_max
        return self.first_player_opening_draw if player == first_player else self.second_player_opening_draw
    draw_action_count: int = 2           # cards drawn by one Draw action (overview.md §5); 1→2
                                          # 2026-07-12 after a 42-game human draw-2 cohort — plays
                                          # better and de-fangs free "draw 1" riders (they no longer
                                          # strictly beat the default action)
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
