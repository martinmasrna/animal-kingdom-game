"""Tactical regression puzzles for the bots: positions with a known-good move, asserted directly
(not inferred from aggregate win-rate deltas, which can hide a bot that regressed on one obvious
tactic while improving on average).

Two kinds: hand-built boards (the constructed-state helpers from test_greedy_bot.py), and real
positions from RefereeBot games against the goodstuff pile, saved as GameState snapshots in
tests/puzzles/, each asserting the set of moves Martin accepts there.
"""

from __future__ import annotations

import json
import os

import pytest

from animal_kingdom.bots.greedy_bot import GreedyBot, GreedyWeights, evaluate
from animal_kingdom.bots.referee_bot import RefereeBot
from animal_kingdom.bots.turn_bot import TurnBot
from animal_kingdom.engine.state import GameState
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import DrawAction, PlaceAction

from ._helpers import make_state, put

W = GreedyWeights()


def _puzzle(name: str) -> GameState:
    path = os.path.join(os.path.dirname(__file__), "puzzles", f"{name}.json")
    with open(path, encoding="utf-8") as fh:
        return GameState.from_dict(json.load(fh))


def _choices(bot_cls, s: GameState, seeds=range(5)):
    """The bot's move on each seed. Near-tied moves make one seed a coin flip, so a puzzle
    holds only if the accepted move wins on every seed."""
    return [bot_cls(seed=seed).choose(s.view_for(s.player_to_act()), rules.legal_actions(s), s)
            for seed in seeds]


def test_blocks_imminent_hq_threat_over_unrelated_offense():
    # B has a connected chain of weak units running all the way onto "1,2" (A's own HQ
    # front) - if left alone, B captures A's HQ next turn. A also has an unrelated,
    # perfectly fine offensive play available ("1,1", another empty HQ-front cell). A must
    # cover "1,2" (breaking B's connection) rather than chase the unrelated offense.
    s = make_state(current="A", hands={"A": ["lion", "mouse"]})
    for cr in ("4,2", "3,2", "2,2", "1,2"):
        put(s, cr, "mouse", "B")

    legal = rules.legal_actions(s)
    block = PlaceAction("lion", ("cr", "1,2"))
    offense = PlaceAction("lion", ("cr", "1,1"))
    assert block in legal and offense in legal

    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert chosen == block


def test_prefers_big_food_gain_over_marginal_board_presence():
    # Worker Ant's roar (gain 12 food, non-lethal here) trades a strong body (Lion, 7
    # strength) for a weak one (1 strength) - the food swing should win out over the
    # marginal board-presence loss.
    s = make_state(hands={"A": ["worker_ant", "lion"]}, food={"A": 50, "B": 0})
    legal = rules.legal_actions(s)

    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert chosen.card_id == "worker_ant"


def test_prefers_region_richer_hq_front_tile():
    # Same card, same connection/presence value either way - "1,2" is a corner of two
    # regions (R1 + R4) while "1,1" is a corner of only one (R1), so region_control should
    # be the deciding factor between two otherwise-tied HQ-front placements.
    s = make_state(hands={"A": ["lion"]})
    legal = rules.legal_actions(s)
    richer = PlaceAction("lion", ("cr", "1,2"))
    poorer = PlaceAction("lion", ("cr", "1,1"))
    assert richer in legal and poorer in legal

    chosen = GreedyBot(seed=0).choose(s.view_for("A"), legal, s)
    assert chosen == richer


def test_recognizes_black_bear_delayed_draw_as_better_than_a_vanilla_body():
    # Retired xfail (2026-07-04): GreedyWeights.pending_payoff credits owned scheduled effects, so a
    # delayed effect outscores a plain vanilla body even on a smaller body (Black Bear 5 vs Lion 7; it
    # was the old Grizzly Bear's delayed removal until the launch decks). The tripwire for the
    # scheduled/delayed-effect blind spot.
    s = make_state(hands={"A": ["black_bear", "lion"]}, decks={"A": ["lion"] * 4, "B": []})   # bear str 5 + effect vs lion 7
    put(s, "2,2", "mouse", "B")                              # a free future target

    bear = s.clone()
    rules.apply_action(bear, PlaceAction("black_bear", ("cr", "1,2")))
    vanilla_twin = s.clone()
    rules.apply_action(vanilla_twin, PlaceAction("lion", ("cr", "1,2")))

    assert bear.scheduled, "Black Bear's roar should schedule the delayed draw"
    assert evaluate(bear, "A", W) > evaluate(vanilla_twin, "A", W)


@pytest.mark.parametrize("bot_cls", [TurnBot, RefereeBot])
def test_last_action_spends_an_extra_play_roar(bot_cls):
    # The turn's last action. Jerboa ("Roar: play another unit") lands two units for one
    # action; Lion alone lands one and keeps Jerboa in hand. Nothing threatens either line,
    # so the two-unit play is simply better. From Martin's reverse gauntlet, where RefereeBot
    # piloting the Roar-heavy decks (Egg, Colony, Cats) kept its effect cards in hand while
    # he played them.
    deck = ["lion"] * 10
    s = make_state(hands={"A": ["jerboa", "lion", "tiger", "lynx", "caracal", "cheetah"],
                          "B": ["lion"] * 3},
                   decks={"A": list(deck), "B": list(deck)})
    s.actions_taken_this_turn = 1
    put(s, "1,2", "mouse", "A")
    put(s, "3,2", "lion", "B")

    chosen = bot_cls(seed=0).choose(s.view_for("A"), rules.legal_actions(s), s)
    assert chosen.card_id == "jerboa"


@pytest.mark.parametrize("bot_cls", [TurnBot, RefereeBot])
def test_canine_develops_instead_of_drawing_a_full_hand(bot_cls):
    # From a RefereeBot game (Canine vs the goodstuff pile, round 2): Dhole on Canine's den
    # front, the pile drew twice and has nothing on the board, Canine already drew with its
    # first action and holds six. The bot drew again. Martin: the move is Dhole,
    # Fox or Dingo; drawing is the worst and a vanilla Wolf the second worst (Jackal and
    # Raksha, a deleted card whose slot holds a second Jackal now, are wrong too); that Fox's card is `african_wild_dog` now. One good line is a second Dhole in the middle row, then Fox into a
    # corner next turn (+2 from each Dhole, a draw for each), then Dingo beside them.
    for chosen in _choices(bot_cls, _puzzle("canine_develop")):
        assert isinstance(chosen, PlaceAction) and chosen.card_id in {"dhole", "african_wild_dog", "dingo"}, chosen


@pytest.mark.parametrize("bot_cls", [TurnBot,
    pytest.param(RefereeBot, marks=pytest.mark.xfail(strict=False, reason="recorded against the old goodstuff pile, whose cards changed with the launch decks (Brutus, the Rhinoceros and the Elephant are Hungry, the Wolf roams): the search reads a different opponent now; re-record (2026-10-08)"))])   # RefereeBot played Owl since single targets are asked
@pytest.mark.slow
def test_egg_plays_owl_before_drawing(bot_cls):
    # Egg vs the pile, round 5, first action: Magpie, Eagle, Owl and Ember on the board, their
    # Lion in the middle under a Taipan timer; hand Viper, Python, Lemming, Viper, Owl. Martin
    # plays Owl first.
    for chosen in _choices(bot_cls, _puzzle("egg_owl")):
        assert isinstance(chosen, PlaceAction) and chosen.card_id == "owl", chosen


@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason="the search draws with five Cats in hand (2026-09-30)")
@pytest.mark.parametrize("bot_cls", [TurnBot, RefereeBot])
def test_cats_plays_lynx_in_the_middle(bot_cls):
    # Cats vs the pile, round 2, first action: Lion on the den front, their Wolf on theirs;
    # hand Cougar, Princess Lea, House Cat, Prince Leo, Lynx. Martin: "Lynx in the middle,
    # almost for sure" (2,2, next to the Lion, so its Roar draws).
    for chosen in _choices(bot_cls, _puzzle("cats_lynx")):
        assert chosen == PlaceAction("lynx", ("cr", "2,2")), chosen


@pytest.mark.parametrize("bot_cls", [TurnBot, pytest.param(RefereeBot, marks=pytest.mark.xfail(strict=False, reason="recorded against the old goodstuff pile, whose cards changed with the launch decks (Brutus, the Rhinoceros and the Elephant are Hungry, the Wolf roams): the search reads a different opponent now; re-record (2026-10-08)"))])
def test_aggro_draws_on_its_opening(bot_cls):
    # Aggro vs the pile, its first turn, second action, empty board, hand Falcon, Falcon, Rat,
    # Rat, Skunk. Martin draws here too. A guard: the fix for drawing too much must not stop
    # this - the bot that flew a Falcon to their den front instead lost these games.
    s = _puzzle("aggro_opening_draw")
    s.turn_counter += 2                  # recorded when the first turn had two actions; the same opening, a turn later
    for chosen in _choices(bot_cls, s):
        assert isinstance(chosen, DrawAction), chosen


def test_hoofed_holds_the_zebra_for_a_bigger_draw():
    # Martin, 2026-10-17: the Expert played the legendary Zebra ("draw a card for each different Hoofed animal you
    # control") on turn one, for one card, with a hand of Hoofed animals. The one-turn search can't see that two Hoofed
    # now and the Zebra next turn draw three; a second turn of sight (depth 1) can. Depth 0 plays the Zebra in 5 of 5
    # seeds, depth 1 in 0 of 5 (measured 2026-10-17).
    from animal_kingdom.engine.maps import load_map
    from animal_kingdom.sim.runner import make_bot
    for seed in range(3):
        s = make_state(current="A", hands={"A": ["zebra_legend", "okapi", "deer", "gazelle", "giraffe", "wildebeest"],
                                           "B": ["lion", "serval", "lynx", "bobcat"]},
                       decks={"A": ["moose", "boar", "zebra", "cape_buffalo", "okapi", "deer"] * 3, "B": ["tiger", "lion", "cougar"] * 5})
        s.game_map = load_map("map_b")
        put(s, next(iter(s.game_map.hq_front("B"))), "serval", "B")
        bot, turn = make_bot("referee", seed, extra={"depth": 1}), []
        while s.result is None and s.current == "A":
            turn.append(bot.choose(s.view_for(s.player_to_act()), rules.legal_actions(s), s))
            rules.apply_action(s, turn[-1])
        assert "zebra_legend" not in [getattr(a, "card_id", None) for a in turn], (seed, turn)


def test_taipan_marks_the_python():
    # Goodstuff vs Martin's Egg Control, his game of 2026-09-30, the bot's turn with 0 food: hand
    # Elephant, Tiger, Brutus, Wolf, Taipan; his Python (8) in the middle, his Raven beside it.
    # Wolf on 4,2 opens 3,2, and Taipan there must mark the Python. Martin: the only right play;
    # Taipan with no target, marking the Raven, or drawing and holding Taipan are all wrong.
    # Solved by the target-aware candidate weights (2026-10-17): the mark is worth what it removes, and
    # covering the Python (what the bot did) is not removing it. With either term alone it still fails.
    # The position is kept as played: the Python at 8 (the card is a 0 that grows since), and the Elephant
    # and Brutus out of the bot's hand (the Elephant cost 15 food then; Brutus was a plain Armor 8, and
    # today's Roar wipes the Python outright: with it in hand, depth 1 finds a near-forced den capture
    # instead, 893 of Martin's 894 replies losing). A second turn of sight alone (depth 1, default
    # weights) draws and holds the Cottonmouth, one of the named wrong plays; depth 1 with these weights
    # marks the Python in 4 of 5 seeds.
    from animal_kingdom.sim.runner import make_bot
    from animal_kingdom.bots.greedy_bot import TARGET_AWARE_WEIGHTS
    for seed in range(5):
        s, bot, turn = _puzzle("ramp_taipan_target"), make_bot("referee", seed, weights=TARGET_AWARE_WEIGHTS), []
        python = s.top_unit("3,3").iid
        while s.result is None and s.current == "B":
            turn.append(bot.choose(s.view_for(s.player_to_act()), rules.legal_actions(s), s))
            rules.apply_action(s, turn[-1])
        assert [x for x in s.scheduled if x["step"].get("by_card") == "gaboon_viper" and x["step"]["iid"] == python], (seed, turn)


DEN_SENSE_CANDIDATE = {"depth": 1, "w.pending_target": 1.5, "w.buried_presence": 0.25, "den_sense": True}


def _opponent_captures_in_two(s):
    """Can A take B's den within two actions from here (A to act)?"""
    for a1 in rules.legal_actions(s):
        if getattr(a1, "is_hq_capture", False):
            return True
        n = s.clone()
        rules.apply_action(n, a1, validate=False)
        if n.player_to_act() == "A" and any(getattr(a2, "is_hq_capture", False) for a2 in rules.legal_actions(n)):
            return True
    return False


def test_the_groundhog_guards_the_den():
    # Martin's Hoofed vs the Expert's Food Aggro, 17 October (web match HWENGG), the bot's turn 6 with a Groundhog in
    # hand and a Chipmunk alone in front of its den, Martin's Zebra and Warthog beside it with two cards in hand. He
    # covers the Chipmunk and walks in unless something stronger stands on 5,2. Today's Expert drew twice and lost
    # the game there. Two blindnesses: its reply model plays the opponent one action at a time, so the cover-then-
    # capture never appeared in any world; and its root screen ranked a Meerkat above the Groundhog on that square,
    # so the only guard was never searched. With den sense it guards in every seed (draw first, then the guard, or
    # the guard first).
    from animal_kingdom.sim.runner import make_bot
    for seed in range(5):
        s, bot = _puzzle("den_guard_cover"), make_bot("referee", seed, extra=dict(DEN_SENSE_CANDIDATE))
        while s.result is None and s.current == "B":
            rules.apply_action(s, bot.choose(s.view_for("B"), rules.legal_actions(s), s))
        assert s.top_unit("5,2").card_id != "chipmunk", seed
        assert not _opponent_captures_in_two(s), seed


def test_the_hoofed_bot_covers_its_gazelle():
    # The same evening, Martin's Cats vs the Expert's Hoofed (web match HDUPLA, first game), the bot's turn 6: a
    # Gazelle alone on 5,2, Martin's Tiger and Lynx next to it with six cards in hand, the bot holding Giraffe, Cape
    # Buffalo, Boar, Giraffe, Deer. Today's Expert drew and put the Buffalo on 5,3; Martin covered the Gazelle and
    # captured. With den sense the bot's turn leaves no two-action capture.
    from animal_kingdom.sim.runner import make_bot
    for seed in range(3):
        s, bot = _puzzle("den_guard_hoofed"), make_bot("referee", seed, extra=dict(DEN_SENSE_CANDIDATE))
        while s.result is None and s.current == "B":
            rules.apply_action(s, bot.choose(s.view_for("B"), rules.legal_actions(s), s))
        assert not _opponent_captures_in_two(s), seed
