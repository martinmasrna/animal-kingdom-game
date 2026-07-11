"""Decision G: once-per-turn caps on value/food triggers (docs/balance/backlog.md).

Every cap flag defaults False (uncapped/as printed); each test forces the flag on to prove
the *plumbing* actually limits the trigger to once per owner-turn per unit, independent of
whatever default docs/balance/backlog.md ends up recording. Two triggers (King Theron, Egg Eater) had
no cap wiring at all before this pass - the rest reuse the existing `_capped` helper.

"Once per turn" here means once per single top-level action's resolution cascade (a turn is
one placement/draw plus its pending sub-choices, per rules.py) - so these tests trigger the
reactor twice within ONE action (a mass effect removing two units, or a placement that opens
an extra-placement sub-choice), not across two separate top-level actions.

Map A geometry: A's HQ fronts are column 1, B's are column 4; a 4x3 grid, orthogonal
neighbours (see test_effects.py header).
"""

from __future__ import annotations

from dataclasses import replace

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ChoiceAction, PlaceAction
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.effects import gain_food

from ._helpers import make_state, put


# ------------------------------------------------------------------ King Theron (new cap)

def test_king_theron_uncapped_removes_on_every_cover_this_turn():
    cfg = Config.default()
    s = make_state(config=cfg, hands={"A": ["house_cat", "black_panther"]})
    put(s, "1,1", "king_theron", "A")
    put(s, "2,1", "mouse", "B")
    put(s, "2,2", "mouse", "B")
    # House Cat's battlecry offers "play another Cat" - use it to cover a second enemy
    # within the same placement's resolution.
    rules.apply_action(s, PlaceAction("house_cat", ("cr", "2,1")))
    assert s.pending is not None
    rules.apply_action(s, PlaceAction("black_panther", ("cr", "2,2")))
    assert len([c for c in s.remove_pile if c == "mouse"]) == 2


def test_king_theron_capped_fires_once_per_turn():
    cfg = replace(Config.default(), cap_king_theron=True)
    s = make_state(config=cfg, hands={"A": ["house_cat", "black_panther"]})
    put(s, "1,1", "king_theron", "A")
    put(s, "2,1", "mouse", "B")
    put(s, "2,2", "mouse", "B")
    rules.apply_action(s, PlaceAction("house_cat", ("cr", "2,1")))
    rules.apply_action(s, PlaceAction("black_panther", ("cr", "2,2")))
    assert len([c for c in s.remove_pile if c == "mouse"]) == 1
    # The second cover still lands normally - it's the free removal that's capped, not the cover.
    assert s.board["2,2"][-1].card_id == "black_panther"


# -------------------------------------------------------------------- Egg Eater (new cap)

def _pestis_double_egg_state(config: Config) -> GameState:
    """Egg Eater on board; Pestis wipes one whole crossroad, and stacking both Eggs on
    the same enemy crossroad means one Pestis activation fires two remove events in a
    single resolution cascade - exactly the "busy action" decision G is guarding against."""
    s = make_state(config=config, hands={"A": ["pestis"]})
    put(s, "1,1", "egg_eater", "A")
    put(s, "1,2", "mouse", "A")             # connection anchor, adjacent to "2,2"
    put(s, "2,1", "bird_egg", "B")
    put(s, "2,1", "snake_egg", "B")         # same crossroad, same owner: stacks freely
    rules.apply_action(s, PlaceAction("pestis", ("cr", "2,2")))
    assert s.pending is not None            # two adjacent occupied stacks: "1,2" (mine), "2,1"
    rules.apply_action(s, ChoiceAction("2,1"))
    return s


def test_egg_eater_uncapped_gains_on_every_egg_removed_this_turn():
    cfg = Config.default()
    s = _pestis_double_egg_state(cfg)
    assert s.food["A"] == 2 * cfg.egg_eater_food


def test_egg_eater_capped_fires_once_per_turn():
    cfg = replace(Config.default(), cap_egg_eater=True)
    s = _pestis_double_egg_state(cfg)
    assert s.food["A"] == cfg.egg_eater_food


# --------------------------------------------------------- existing caps, no prior tests

def test_eon_capped_fires_once_per_turn_across_multiple_events():
    # Reuse the same double-remove-in-one-action pattern: Pestis wiping a 2-unit enemy
    # stack fires two remove events in one resolution cascade, so an on-board Eon should
    # gain food only once when capped.
    cfg = replace(Config.default(), cap_eon=True)
    s = make_state(config=cfg, hands={"A": ["pestis"]})
    put(s, "1,1", "eon", "A")
    put(s, "1,2", "mouse", "A")             # connection anchor
    put(s, "2,1", "mouse", "B")
    put(s, "2,1", "rat", "B")               # same crossroad, same owner: stacks freely
    rules.apply_action(s, PlaceAction("pestis", ("cr", "2,2")))
    assert s.pending is not None
    rules.apply_action(s, ChoiceAction("2,1"))
    assert s.food["A"] == cfg.eon_food      # two remove events fired; only the first paid out


def test_falstaff_capped_limits_rider_to_one_gain_event_per_turn():
    cfg = replace(Config.default(), cap_falstaff=True)
    s = make_state(config=cfg, food={"A": 0, "B": 0})
    put(s, "1,1", "falstaff", "A")
    gain_food(s, "A", 1)
    gain_food(s, "A", 1)
    # Both gains apply, but the +3 rider only fires once (capped) instead of twice.
    assert s.food["A"] == 2 + cfg.falstaff_food_rider
