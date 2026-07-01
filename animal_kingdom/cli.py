"""Terminal driver: play a game bot-vs-bot or hotseat, rendering each step.

Examples:
  python -m animal_kingdom.cli --bots random,random --seed 1
  python -m animal_kingdom.cli --bots human,random --seed 7

This is a thin caller of the engine - the same legal_actions / apply_action / is_terminal
loop a sim or a future web server would use. The engine itself does no I/O.
"""

from __future__ import annotations

import argparse
import random
import sys
from typing import Sequence

from .bots.greedy_bot import GreedyBot
from .bots.random_bot import RandomBot
from .decks import PREMADE_DECKS, load_premade_deck, make_vanilla_deck
from .engine import rules
from .engine.actions import Action, DrawAction, PlaceAction
from .engine.state import GameState, StateView, new_game
from .render.text import render


def _fmt_action(a: Action) -> str:
    if isinstance(a, DrawAction):
        return "draw"
    if isinstance(a, PlaceAction):
        return f"place {a.card_id} -> {a.target[0]}:{a.target[1]}"
    return repr(a)


class HumanController:
    """Reads a choice from stdin. Lives in the CLI (not bots/) so the engine stays I/O-free."""

    def choose(self, view: StateView, legal: Sequence[Action],
               state: GameState | None = None) -> Action:
        legal = list(legal)
        for i, a in enumerate(legal):
            print(f"  [{i}] {_fmt_action(a)}")
        while True:
            raw = input(f"player {view.player} choose action #: ").strip()
            if raw.isdigit() and 0 <= int(raw) < len(legal):
                return legal[int(raw)]
            print(f"  enter a number 0..{len(legal) - 1}")


def _make_controller(kind: str, seat: str, seed: int):
    kind = kind.strip().lower()
    seat_seed = seed + (1 if seat == "A" else 2)
    if kind == "random":
        return RandomBot(seed=seat_seed)
    if kind == "greedy":
        return GreedyBot(seed=seat_seed)
    if kind == "human":
        return HumanController()
    raise SystemExit(f"unknown bot kind {kind!r} (expected 'random', 'greedy', or 'human')")


def _make_deck(spec: str, deck_rng: random.Random) -> list[str]:
    """A premade deck by slug, or a random vanilla deck when spec is 'vanilla'/empty."""
    spec = spec.strip()
    if spec in ("", "vanilla"):
        return make_vanilla_deck(seed=deck_rng.randrange(1 << 30))
    if spec not in PREMADE_DECKS:
        raise SystemExit(f"unknown deck {spec!r}; expected 'vanilla' or one of {sorted(PREMADE_DECKS)}")
    return load_premade_deck(spec)


def play(bot_spec: str, seed: int, map_id: str, quiet: bool, decks: str) -> None:
    kinds = bot_spec.split(",")
    if len(kinds) != 2:
        raise SystemExit("--bots expects two comma-separated kinds, e.g. random,random")
    controllers = {"A": _make_controller(kinds[0], "A", seed),
                   "B": _make_controller(kinds[1], "B", seed)}

    deck_specs = decks.split(",")
    if len(deck_specs) != 2:
        raise SystemExit("--decks expects two comma-separated decks, e.g. ramp,egg_control")
    deck_rng = random.Random(seed)
    deck_a = _make_deck(deck_specs[0], deck_rng)
    deck_b = _make_deck(deck_specs[1], deck_rng)
    state = new_game(deck_a, deck_b, seed, map_id=map_id)

    while True:
        result = rules.is_terminal(state)
        if result is not None:
            break
        if not quiet:
            print(render(state))
            print()
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        action = controllers[actor].choose(state.view_for(actor), legal, state)
        rules.apply_action(state, action)

    print(render(state))
    print(f"\nFINAL: winner={result.winner or 'draw'} reason={result.reason} "
          f"turns={state.turn_counter}")


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Play an Animal Kingdom game in the terminal.")
    p.add_argument("--bots", default="random,random",
                   help="two comma-separated controllers: random|greedy|human "
                        "(default random,random)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--map", dest="map_id", default="map_a")
    p.add_argument("--decks", default="vanilla,vanilla",
                   help="two comma-separated decks: 'vanilla' or a premade slug "
                        "(e.g. ramp,egg_control)")
    p.add_argument("--quiet", action="store_true", help="only print the final board/result")
    args = p.parse_args(argv)
    play(args.bots, args.seed, args.map_id, args.quiet, args.decks)


if __name__ == "__main__":
    main(sys.argv[1:])
