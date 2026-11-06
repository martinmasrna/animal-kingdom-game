"""The den-reach dial (`den_reach`, on top of `den_open`): two of the Expert's four misses among the den captures mined
from Martin's games (knowledge/audit/forced-captures-2026-11-05.md, tools/puzzles/expert_finds.py), rebuilt by hand on
map_b with only the units the line needs.

- The egg under the Hyena (OXHIXA line 21, puzzle 3): a Hornet onto A's Cockroach removes A's Hyena, which uncovers
  B's own Snake Egg and joins B's chain to 2,2; then a Mole onto the Locust Swarm, whose Roar plays the Egg Eater onto
  A's den. The opener needs the right removal target, and the second action takes the den only through its Roar, so
  `den_open` alone (capture legal right after the opener, sub-choices settled by the fast policy) keeps neither half.
- The Bush Dog steps forward (ZXMEHG line 8, puzzle 4): roam the Bush Dog onto A's Termite King, its Pup refills 2,2,
  then the Wolverine walks into A's den. A roam opener, which `den_open` already keeps; it stays found with den_reach.

The bot is the referee with the Expert's widths and node budget, on the hand evaluation with no time budget, so the
result does not depend on the machine. In the egg position the line dies where the budget hands the turn to the fast
policy, which picks the Hornet's target and the second action one at a time (`_den_reach_move` now finishes it).
"""
from __future__ import annotations

from animal_kingdom.bots.referee_bot import RefereeBot
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import PlaceAction, RoamAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.maps import load_map
from animal_kingdom.engine.state import GameState, UnitInstance


def _state(board: dict, hand: list, deck: list, me: str, turn: int, opp_hand: list) -> GameState:
    opp = "A" if me == "B" else "B"
    s = GameState(load_map("map_b"), load_cards(), Config.default(), board={}, hands={"A": [], "B": []},
                  decks={me: list(deck), opp: ["mouse"] * 10}, remove_pile=[], food={"A": 0, "B": 0},
                  current=me, first_player="A", turn_counter=turn)
    for c in hand:
        s.add_to_hand(me, c)
    for c in opp_hand:
        s.add_to_hand(opp, c)
    for cr, stack in board.items():
        for card_id, owner, counter in stack:
            u = UnitInstance(card_id, owner, s.new_iid(), placed_on_turn=turn - 2)
            u.strength_counter = counter
            s.stamp_played(u)
            s.board.setdefault(cr, []).append(u)
    return s


def egg_under_the_hyena() -> GameState:
    return _state({
        "1,1": [("tarantula", "A", 5)],
        "1,2": [("cockroach_legend", "A", 4), ("locust_swarm", "wild", 0)],
        "2,2": [("cockroach", "A", 0)],
        "2,3": [("praying_mantis", "A", 0)],
        "3,2": [("snake_egg", "B", 2), ("hyena", "A", 0)],
        "4,2": [("capybara", "B", 2)],
        "5,1": [("raven_legend", "B", 2)],
        "5,2": [("bee_legend_2", "B", 2)],
    }, hand=["python", "python", "hornet", "egg_eater", "tortoise_legend", "mole"],
        deck=["hornet", "owl", "capybara", "honey_badger", "snake_egg", "bird_egg", "python"],
        me="B", turn=16, opp_hand=["mouse", "mouse"])


def bush_dog_steps_forward() -> GameState:
    return _state({
        "1,1": [("nurse_bee", "A", 0)],
        "1,2": [("worker_wasp", "A", 0), ("dhole", "B", 0)],
        "1,3": [("army_ant_legend", "A", 0)],
        "2,1": [("termite_queen", "A", 0)],
        "2,2": [("queen_ant", "A", 0), ("african_wild_dog", "B", 3), ("hornet_legend", "A", 0), ("bush_dog", "B", 3)],
        "2,3": [("young_ant", "A", 0)],
        "3,2": [("street_dog", "B", 0), ("termite_king", "A", 0)],
        "3,3": [("termite_king", "A", 0)],
        "4,2": [("street_dog", "B", 0)],
        "5,2": [("pup", "B", 0)],
    }, hand=["wolverine"], deck=["fox", "jackal", "wolf", "coyote", "dhole", "orca"],
        me="B", turn=7, opp_hand=["mouse"] * 5)


def _bot(seed: int, reach: bool) -> RefereeBot:
    # the Expert's widths and staged node budget (sim.runner: REFEREE_*), the hand evaluation, one turn of sight
    return RefereeBot(seed=seed, determinizations=5, beam_width=8, root_width=5, reply_width=8, max_search_nodes=150,
                      quiesce=True, den_open=True, den_reach=reach)


def _plays_turn(state: GameState, bot: RefereeBot) -> tuple[bool, list]:
    me, turn, moves = state.current, state.turn_counter, []
    for _ in range(20):
        if rules.is_terminal(state) is not None or state.turn_counter != turn:
            break
        assert state.player_to_act() == me
        action = bot.choose(state.view_for(me), rules.legal_actions(state), state)
        moves.append(action)
        rules.apply_action(state, action)
    res = rules.is_terminal(state)
    return bool(res is not None and res.winner == me and res.reason == "hq_capture"), moves


def test_the_line_is_there():
    s = egg_under_the_hyena()
    assert PlaceAction("hornet", ("cr", "2,2")) in rules.legal_actions(s)
    assert not any(isinstance(a, (PlaceAction, RoamAction)) and a.is_hq_capture for a in rules.legal_actions(s))
    s = bush_dog_steps_forward()
    assert RoamAction("2,2", ("cr", "3,2")) in rules.legal_actions(s)


def test_den_reach_finds_the_egg_under_the_hyena():
    for seed in (0, 1):
        captured, moves = _plays_turn(egg_under_the_hyena(), _bot(seed, True))
        assert captured, moves
        assert moves[0] == PlaceAction("hornet", ("cr", "2,2"))


def test_den_open_alone_misses_the_egg_under_the_hyena():
    captured, moves = _plays_turn(egg_under_the_hyena(), _bot(0, False))
    assert not captured, moves


def test_den_reach_keeps_the_bush_dog_roam():
    for seed in (0, 1):
        captured, moves = _plays_turn(bush_dog_steps_forward(), _bot(seed, True))
        assert captured, moves
        assert moves[0] == RoamAction("2,2", ("cr", "3,2"))


def test_den_reach_needs_den_open():
    assert not RefereeBot(den_reach=True).den_reach
    assert RefereeBot(den_open=True, den_reach=True).den_reach
