"""Self-play data for the value network: TurnBot games (hand eval or the current net) across
every pairing of the seven premades and the goodstuff pile, recording the positions the search
scores, labelled with who won.

Recorded per decision of each seat: the afterstate as the search scores it (`extract_as_scored`:
raw mid-turn, reframed to my next turn once control passes), plus, at every turn start, the
position from the mover's side (what RefereeBot scores after the sampled reply). Exploration: a
uniformly random legal move with probability `epsilon`, recorded like any other.

    python -m animal_kingdom.learn.selfplay OUT.npz [--eval PATH] [--games-per-pair 110] \\
        [--seed 0] [--jobs 8]
"""

from __future__ import annotations

import argparse
import itertools
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Optional

from ..bots import features
from ..bots.learned_eval import load_eval
from ..bots.turn_bot import TurnBot
from ..decks import load_premade_deck
from ..engine import rules
from ..engine.cards import DECK_SLUGS
from ..engine.state import new_game, other_player
from .episodes import extract_as_scored

FEATURE_SET = "rung2"


@dataclass(frozen=True)
class GameSpec:
    deck_a: str
    deck_b: str
    seed: int
    eval_path: Optional[str]
    epsilon: float = 0.05


def pairings() -> list[tuple[str, str]]:
    decks = sorted(DECK_SLUGS) + ["goodstuff"]
    return list(itertools.combinations_with_replacement(decks, 2))


def play(spec: GameSpec) -> dict:
    evaluator = load_eval(spec.eval_path) if spec.eval_path else None
    state = new_game(load_premade_deck(spec.deck_a), load_premade_deck(spec.deck_b), spec.seed,
                     map_id="map_b")
    bots = {s: TurnBot(seed=spec.seed * 2 + i, evaluator=evaluator) for i, s in enumerate("AB")}
    rng = random.Random(spec.seed)
    rows: list[tuple[str, list[float], int]] = []     # (seat, features, turn)
    while (result := rules.is_terminal(state)) is None:
        actor = state.player_to_act()
        if state.pending is None and state.actions_taken_this_turn == 0 and state.turn_counter > 0:
            rows.append((actor, features.extract(state, actor, FEATURE_SET), state.turn_counter))
        legal = rules.legal_actions(state)
        if len(legal) > 1 and rng.random() < spec.epsilon:
            action = rng.choice(legal)
        else:
            action = bots[actor].choose(state.view_for(actor), legal, state)
        turn = state.turn_counter
        rules.apply_action(state, action, validate=False)
        if rules.is_terminal(state) is None:
            rows.append((actor, extract_as_scored(state, actor, FEATURE_SET), turn))
    decks = {"A": spec.deck_a, "B": spec.deck_b}
    return {
        "x": [r[1] for r in rows],
        "y": [0.5 if result.winner is None else float(result.winner == r[0]) for r in rows],
        "turn": [r[2] for r in rows],
        "deck": [decks[r[0]] for r in rows],
        "opp": [decks[other_player(r[0])] for r in rows],
        "game": [spec.seed] * len(rows),
        "reason": result.reason,
    }


def generate(out: str, eval_path: Optional[str], games_per_pair: int, seed: int, jobs: int,
             epsilon: float = 0.05) -> None:
    import numpy as np

    specs = [GameSpec(a, b, seed + i * 1000 + k, eval_path, epsilon)
             for i, (a, b) in enumerate(pairings()) for k in range(games_per_pair)]
    random.Random(seed).shuffle(specs)          # mixed decks in every progress slice
    cols: dict[str, list] = {k: [] for k in ("x", "y", "turn", "deck", "opp", "game")}
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for n, rec in enumerate(ex.map(play, specs, chunksize=4), 1):
            for k in cols:
                cols[k].extend(rec[k])
            if n % 200 == 0:
                print(f"  {n}/{len(specs)} games  {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    np.savez_compressed(out, x=np.array(cols["x"], dtype=np.float32), y=np.array(cols["y"]),
                        turn=np.array(cols["turn"]), deck=np.array(cols["deck"]),
                        opp=np.array(cols["opp"]), game=np.array(cols["game"]),
                        features=np.array(features.feature_names(FEATURE_SET)),
                        eval_path=np.array(eval_path or ""))


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("out")
    p.add_argument("--eval", default=None, help="net/linear artifact the pilots use (default: hand eval)")
    p.add_argument("--games-per-pair", type=int, default=110)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--epsilon", type=float, default=0.05)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    a = p.parse_args(argv)
    generate(a.out, a.eval, a.games_per_pair, a.seed, a.jobs, a.epsilon)


if __name__ == "__main__":
    main(sys.argv[1:])
