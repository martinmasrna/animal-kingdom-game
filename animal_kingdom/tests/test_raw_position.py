"""The raw position (bots/raw_position.py): the inventory test, and the Rust engine's extractor and network held to the
Python ones on replayed self-play positions."""
import json
import os

import pytest

from animal_kingdom.bots import raw_position as R
from animal_kingdom.engine import rules
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game
from animal_kingdom.decks import load_premade_deck

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(os.path.dirname(HERE))


def test_inventory_is_complete():
    """Every state field, piece field and turn-flag key is encoded or excluded with a reason."""
    if not rules.__file__.endswith(".py"):
        pytest.skip("the inventory reads the engine's source and slots; this engine is compiled (the deploy image)")
    assert R.inventory_check() == []


def _positions(n_games=6):
    """Quiet positions (every seat, every decision point) from a few bot games played here."""
    from animal_kingdom.bots.greedy_bot import GreedyBot
    decks = ["cats", "hoofed", "colony", "fish"]
    out = []
    for g in range(n_games):
        a, b = decks[g % 4], decks[(g + 1) % 4]
        st = new_game(load_premade_deck(a), load_premade_deck(b), 1000 + g, config=Config.default())
        bots = {"A": GreedyBot(seed=g), "B": GreedyBot(seed=g + 100)}
        for _ in range(400):
            if rules.is_terminal(st) is not None:
                break
            if st.pending is None and not st.effect_stack:
                out.append(st.clone())
            me = st.player_to_act()
            legal = rules.legal_actions(st)
            rules.apply_action(st, bots[me].choose(st.view_for(me), legal, st))
    return out


def test_extract_runs_on_every_quiet_position():
    for st in _positions(2):
        for me in ("A", "B"):
            r = R.extract(st, me)
            assert len(r["globals"]) == len(R.GLOBALS)
            assert len(r["cr_card"]) == R.N_CROSSROADS


@pytest.mark.skipif(not os.environ.get("AK_RUST_BOTS"), reason="needs the Rust engine (AK_RUST_BOTS=1)")
def test_rust_extractor_agrees():
    from animal_kingdom.bots.rust_bot import engine_for
    for st in _positions(4):
        rs = engine_for(st).from_dict(st.to_dict())
        for me in ("A", "B"):
            py = R.extract(st, me)
            ru = rs.raw_position(me)
            names = sorted(st.cards)
            assert [[names[c] if c >= 0 else None for c in l] for l in py["cr_card"]] == ru["cr_card"]
            assert py["cr_owner"] == ru["cr_owner"]
            for k in range(R.N_CROSSROADS):
                assert py["top_num"][k] == pytest.approx(ru["top_num"][k]), (k, R.TOP_NUM)
                assert py["under_num"][k] == pytest.approx(ru["under_num"][k]), (k, R.UNDER_NUM)
            assert py["globals"] == pytest.approx(ru["globals"]), R.GLOBALS
            for b in R.BAGS:
                assert [names[c] for c, _ in py["bags"][b]] == [n for n, _ in ru["bags"][b]], b
                assert [w for _, w in py["bags"][b]] == pytest.approx([w for _, w in ru["bags"][b]]), b


@pytest.mark.skipif(not os.environ.get("AK_RUST_BOTS"), reason="needs the Rust engine (AK_RUST_BOTS=1)")
def test_rust_network_agrees():
    from animal_kingdom.bots.raw_eval import RawEval
    from animal_kingdom.bots.rust_bot import engine_for
    path = os.environ.get("AK_RAWNET", os.path.join(ROOT, "results", "rawnet", "raw.json"))
    if not os.path.exists(path):
        pytest.skip(f"no rawnet artifact at {path}")
    net = RawEval.from_file(path)
    art = json.dumps(net.to_dict())
    for st in _positions(2):
        rs = engine_for(st).from_dict(st.to_dict())
        for me in ("A", "B"):
            assert net.heads(st, me) == pytest.approx(rs.raw_heads(me, art), abs=1e-6)
