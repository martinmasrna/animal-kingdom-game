"""The engine speedups of 2026-10-20 change nothing a game can see: the Expert plays the same moves (checked on
22 recorded games: tools/engine_speed/record.py and compare.py), and the lazily copied random stream is the stream setstate would give."""
import pickle
import random

from animal_kingdom.engine.state import Rng, _copy_rng


def test_a_lazy_rng_clone_draws_the_same_stream_as_a_copied_state():
    parent = random.Random(7); parent.random()
    lazy, plain = _copy_rng(parent), random.Random()
    plain.setstate(parent.getstate())
    assert [lazy.random(), lazy.getrandbits(10), lazy.choice(range(9))] == [plain.random(), plain.getrandbits(10), plain.choice(range(9))]
    assert [lazy.random() for _ in range(5)] == [plain.random() for _ in range(5)]


def test_clones_share_the_parents_snapshot_until_the_parent_draws():
    parent = _copy_rng(random.Random(3))
    a, b = _copy_rng(parent), _copy_rng(parent)
    assert a.getstate() is b.getstate() is parent.getstate()   # one snapshot, taken once
    parent.shuffle(list(range(5)))                             # the parent moves on; the clones hold its old position
    c = _copy_rng(parent)
    assert c.getstate() is not a.getstate()
    assert [a.random() for _ in range(3)] == [b.random() for _ in range(3)] != [c.random() for _ in range(3)]


def test_a_lazy_rng_pickles_at_its_position():
    parent = _copy_rng(random.Random(11)); parent.random()
    lazy = _copy_rng(parent)
    thawed = pickle.loads(pickle.dumps(lazy))
    assert isinstance(thawed, Rng) and thawed.random() == lazy.random()
