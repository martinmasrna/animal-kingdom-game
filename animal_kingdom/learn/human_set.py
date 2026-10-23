"""Martin's games against the bots as the value network's outside test set.

Every turn-start position of every replayable human game under `results/human_games/web/`, from the
mover's side (what the search scores), rung-2 features, labelled by who won, plus the hand
evaluation's score (the Expert's weights) in a `hand` column. `learn.net --test` reads the file and
reports log-loss and sign agreement for the hand formula, the linear fit and the network, so a round
is read on his games before its paired benchmark (a network that beats the self-play pool and reads
his games worse has learned the pool's blind spot, not the game; docs/bots.md, 2026-10-23).

    python -m animal_kingdom.learn.human_set results/netlearn/human_set.npz
"""
from __future__ import annotations

import glob
import zlib
import json
import os
import sys
from dataclasses import replace

from ..bots import features
from ..bots.greedy_bot import GreedyWeights, evaluate
from ..engine import rules
from ..engine.actions import SKIP, ChoiceAction
from ..engine.config import Config
from ..engine.state import new_game, other_player
from ..web.renamed import renamed

FEATURE_SET = "rung2"


def expert_weights() -> GreedyWeights:
    from ..sim.runner import parse_bot_spec
    from ..web.match import EXPERT
    _, kwargs = parse_bot_spec(EXPERT, "kind")
    return replace(GreedyWeights(), **{k[2:]: v for k, v in kwargs if k.startswith("w.")})


def positions(log: dict, weights: GreedyWeights):
    """(seat, features, turn, hand score) at every turn start of one logged game, or None if it no longer replays."""
    st = new_game(list(log["lists"][0]), list(log["lists"][1]), log["seed"], map_id=log.get("map_id", "map_b"),
                  config=Config.default().for_log(log), first_player=log["first_player"])
    rows, last = [], None
    try:
        for adict in log["actions"]:
            while st.pending is not None and st.effect_stack[-1].get("op") == "mulligan" and adict["kind"] != "choice":
                rules.apply_action(st, ChoiceAction(SKIP))
            if st.pending is None and rules.is_terminal(st) is None and st.turn_counter > 0:
                key = (st.turn_counter, st.player_to_act())
                if key != last:
                    seat = key[1]
                    rows.append((seat, features.extract(st, seat, FEATURE_SET), st.turn_counter, evaluate(st, seat, weights)))
                    last = key
            rules.apply_logged(st, adict)
    except Exception:
        return None
    return rows


def build(out: str, root: str = "results/human_games/web") -> tuple[int, int, int]:
    import numpy as np
    weights = expert_weights()
    cols = {k: [] for k in ("x", "y", "turn", "deck", "opp", "game", "hand")}
    games = kept = 0
    for path in sorted(glob.glob(os.path.join(root, "*.jsonl"))):
        with open(path) as fh:
            for line_no, line in enumerate(fh):
                if not line.strip():
                    continue
                g = renamed(json.loads(line))
                if "human" not in g.get("bots", []) or g.get("winner") is None or not g.get("lists"):
                    continue
                games += 1
                rows = positions(g, weights)
                if rows is None:
                    continue
                kept += 1
                decks = {"A": g["deck_a"], "B": g["deck_b"]}
                game_id = zlib.crc32(f"{os.path.basename(path)}:{line_no}".encode())   # one id a logged game, stable across runs
                for seat, x, t, h in rows:
                    cols["x"].append(x); cols["hand"].append(h); cols["y"].append(float(g["winner"] == seat))
                    cols["turn"].append(t); cols["deck"].append(decks[seat]); cols["opp"].append(decks[other_player(seat)])
                    cols["game"].append(game_id)
    np.savez_compressed(out, x=np.array(cols["x"], dtype=np.float32), y=np.array(cols["y"]), turn=np.array(cols["turn"]),
                        deck=np.array(cols["deck"]), opp=np.array(cols["opp"]), game=np.array(cols["game"]),
                        hand=np.array(cols["hand"], dtype=np.float32), features=np.array(features.feature_names(FEATURE_SET)),
                        eval_path=np.array(""), pilot=np.array("human"))
    return kept, games, len(cols["x"])


def main(argv=None) -> None:
    args = sys.argv[1:] if argv is None else argv
    out = args[0] if args else "results/netlearn/human_set.npz"
    kept, games, n = build(out)
    print(f"{kept} of {games} human games replay; {n} positions -> {out}")


if __name__ == "__main__":
    main()
