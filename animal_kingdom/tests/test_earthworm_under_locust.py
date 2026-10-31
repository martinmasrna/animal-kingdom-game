"""The Earthworm's Worms land unless an enemy holds the crossroad: a Wild Locust on top is no enemy (Martin, 2026-10-31,
Cockroach gauntlet OXHIXA: a Locust that ate the Earthworm, and his Mantis removing it from under a Locust, left no Worms)."""

from animal_kingdom.engine import effects
from animal_kingdom.engine.state import WILD, UnitInstance

from ._helpers import make_state, put


def _locust_on(s, cr):
    locust = UnitInstance("locust_swarm", WILD, s.new_iid())
    s.board[cr].append(locust)
    return locust


def test_worms_land_when_the_earthworm_is_removed_from_under_a_wild_locust():
    s = make_state(decks={"A": ["lion"] * 3, "B": []})
    worm = put(s, "1,2", "earthworm", "A")
    _locust_on(s, "1,2")
    effects._remove_specific(s, "1,2", worm, by_player="A", by_card="praying_mantis")
    assert [u.card_id for u in s.board["1,2"]] == ["locust_swarm", "worm", "worm"]


def test_a_locust_that_eats_the_earthworm_flies_off_and_leaves_the_worms():
    s = make_state(decks={"A": ["lion"] * 3, "B": []})
    put(s, "1,2", "earthworm", "A")
    locust = _locust_on(s, "1,2")
    effects._op_locust_eat(s, {"op": "locust_eat", "iid": locust.iid, "by_player": "B"})
    assert [u.card_id for u in s.board["1,2"]] == ["worm", "worm"]


def test_no_worms_under_an_enemy():
    s = make_state(decks={"A": ["lion"] * 3, "B": []})
    worm = put(s, "1,2", "earthworm", "A")
    put(s, "1,2", "lion", "B")
    effects._remove_specific(s, "1,2", worm, by_player="B", by_card="praying_mantis")
    assert [u.card_id for u in s.board["1,2"]] == ["lion"]
