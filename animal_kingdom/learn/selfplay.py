"""Self-play data for the value network: games between two copies of one pilot (TurnBot by default, any
`sim.runner` bot spec with `--pilot`, e.g. the Expert) across every pairing of the decks (the seven starters and
the goodstuff pile by default, the bot pool with `--pool`), recording the positions the search scores, labelled
with who won.

Recorded per decision of each seat: the afterstate as the search scores it (`extract_as_scored`:
raw mid-turn, reframed to my next turn once control passes), plus, at every turn start, the
position from the mover's side (what RefereeBot scores after the sampled reply). Exploration: a
uniformly random legal move with probability `epsilon`, recorded like any other.

    python -m animal_kingdom.learn.selfplay OUT.npz [--eval PATH] [--games-per-pair 110] \\
        [--seed 0] [--jobs 8] [--decks den_rush,goodstuff] [--pilot "referee:depth=1,..."] [--pool]
"""

from __future__ import annotations

import argparse
import itertools
import json
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

FEATURE_SET = "rung2"   # the default; `--features` picks another (features.FEATURE_SETS)


@dataclass(frozen=True)
class GameSpec:
    deck_a: str
    deck_b: str
    seed: int
    eval_path: Optional[str]
    epsilon: float = 0.05
    pilot: str = "turn"
    pilot_b: str = ""        # a different pilot for seat B ("" means the same as A): two styles in one pool
    feature_set: str = FEATURE_SET
    extra_path: str = ""      # a JSON of extra decks ({slug: {"list": [...]}}), Martin's own decks in the pool


def pairings(pool: bool = False, extra: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    if pool:
        from ..decks import BOT_DECKS
        decks = sorted(BOT_DECKS)
    else:
        decks = sorted(DECK_SLUGS) + ["goodstuff"]
    return list(itertools.combinations_with_replacement(decks + list(extra), 2))


_extra_cache: dict[str, dict] = {}


def deck_for(slug: str, extra_path: str) -> list[str]:
    """The 30 cards of `slug`: a shipped deck, or one from the extra-deck file (loaded once per process)."""
    if extra_path:
        if extra_path not in _extra_cache:
            with open(extra_path) as fh:
                _extra_cache[extra_path] = json.load(fh)
        rec = _extra_cache[extra_path].get(slug)
        if rec is not None:
            return list(rec["list"])
    return load_premade_deck(slug)


def play(spec: GameSpec) -> dict:
    evaluator = load_eval(spec.eval_path) if spec.eval_path else None
    state = new_game(deck_for(spec.deck_a, spec.extra_path), deck_for(spec.deck_b, spec.extra_path), spec.seed,
                     map_id="map_b")
    if spec.pilot == "turn":
        bots = {s: TurnBot(seed=spec.seed * 2 + i, evaluator=evaluator) for i, s in enumerate("AB")}
    else:
        from ..sim.runner import make_bot
        specs_by_seat = {"A": spec.pilot, "B": spec.pilot_b or spec.pilot}
        if spec.pilot_b and spec.seed % 2:          # the two pilots swap seats every other game
            specs_by_seat = {"A": spec.pilot_b, "B": spec.pilot}
        bots = {s: make_bot(specs_by_seat[s], spec.seed * 2 + i, extra={"evaluator": evaluator} if evaluator else None)
                for i, s in enumerate("AB")}
    rng = random.Random(spec.seed)
    rows: list[tuple[str, list[float], int]] = []     # (seat, features, turn)
    while (result := rules.is_terminal(state)) is None:
        actor = state.player_to_act()
        if state.pending is None and state.actions_taken_this_turn == 0 and state.turn_counter > 0:
            rows.append((actor, features.extract(state, actor, spec.feature_set), state.turn_counter))
        legal = rules.legal_actions(state)
        if len(legal) > 1 and rng.random() < spec.epsilon:
            action = rng.choice(legal)
        else:
            action = bots[actor].choose(state.view_for(actor), legal, state)
        turn = state.turn_counter
        rules.apply_action(state, action, validate=False)
        if rules.is_terminal(state) is None:
            rows.append((actor, extract_as_scored(state, actor, spec.feature_set), turn))
    decks = {"A": spec.deck_a, "B": spec.deck_b}
    return {
        "x": [r[1] for r in rows],
        "y": [0.5 if result.winner is None else float(result.winner == r[0]) for r in rows],
        "turn": [r[2] for r in rows],
        "deck": [decks[r[0]] for r in rows],
        "opp": [decks[other_player(r[0])] for r in rows],
        "game": [spec.seed] * len(rows),
        "reason": [result.reason] * len(rows),
    }


def generate(out: str, eval_path: Optional[str], games_per_pair: int, seed: int, jobs: int,
             epsilon: float = 0.05, decks: Optional[list[str]] = None, pilot: str = "turn", pool: bool = False,
             pilot_b: str = "", feature_set: str = FEATURE_SET, extra_path: str = "", max_games: int = 0) -> None:
    """`decks`, if given, keeps only the pairings that include one of them; `feature_set` names what is recorded;
    `extra_path` adds decks to the pool (Martin's own, `results/netlearn/martin_decks.json`); `max_games` keeps a
    random sample of the games when the pairings outgrow the time."""
    import numpy as np

    extra: tuple[str, ...] = ()
    if extra_path:
        with open(extra_path) as fh:
            extra = tuple(sorted(json.load(fh)))
    pairs = [(i, (a, b)) for i, (a, b) in enumerate(pairings(pool, extra))
             if not decks or a in decks or b in decks]
    specs = [GameSpec(a, b, seed + i * 1000 + k, eval_path, epsilon, pilot, pilot_b, feature_set, extra_path)
             for i, (a, b) in pairs for k in range(games_per_pair)]
    random.Random(seed).shuffle(specs)          # mixed decks in every progress slice
    if max_games and len(specs) > max_games:
        specs = specs[:max_games]
    cols: dict[str, list] = {k: [] for k in ("x", "y", "turn", "deck", "opp", "game", "reason")}
    t0 = time.time()

    def save(path: str) -> None:
        np.savez_compressed(path, x=np.array(cols["x"], dtype=np.float32), y=np.array(cols["y"]),
                            turn=np.array(cols["turn"]), deck=np.array(cols["deck"]),
                            opp=np.array(cols["opp"]), game=np.array(cols["game"]),
                            reason=np.array(cols["reason"]),
                            features=np.array(features.feature_names(feature_set)), feature_set=np.array(feature_set),
                            eval_path=np.array(eval_path or ""), pilot=np.array(pilot), pilot_b=np.array(pilot_b))

    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for n, rec in enumerate(ex.map(play, specs, chunksize=4), 1):
            for k in cols:
                cols[k].extend(rec[k])
            if n % 200 == 0:
                print(f"  {n}/{len(specs)} games  {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
            if n % 400 == 0:          # a checkpoint every 400 games: a run that dies keeps what it played (2026-10-23)
                save(out.replace(".npz", "") + ".partial.npz")
    save(out)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("out")
    p.add_argument("--eval", default=None, help="net/linear artifact the pilots use (default: hand eval)")
    p.add_argument("--games-per-pair", type=int, default=110)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--epsilon", type=float, default=0.05)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    p.add_argument("--decks", default=None,
                   help="comma-separated: only the pairings that include one of these decks")
    p.add_argument("--pilot", default="turn", help="the bot spec both seats play (sim.runner.make_bot); default TurnBot")
    p.add_argument("--pool", action="store_true", help="pair the bot pool (decks.BOT_DECKS) instead of the starters and goodstuff")
    p.add_argument("--pilot-b", default="", help="a different pilot for the other seat (the seats swap every other game)")
    p.add_argument("--features", default=FEATURE_SET, help="the feature set recorded (features.FEATURE_SETS: rung2, board)")
    p.add_argument("--extra-decks", default="", help="a JSON of extra decks for the pool ({slug: {'list': [...]}})")
    p.add_argument("--max-games", type=int, default=0, help="play a random sample of this many games of the pairings")
    a = p.parse_args(argv)
    generate(a.out, a.eval, a.games_per_pair, a.seed, a.jobs, a.epsilon,
             a.decks.split(",") if a.decks else None, a.pilot, a.pool, a.pilot_b, a.features, a.extra_decks, a.max_games)


if __name__ == "__main__":
    main(sys.argv[1:])
