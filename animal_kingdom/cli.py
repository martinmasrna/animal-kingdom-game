"""Terminal driver: play a game bot-vs-bot or hotseat, rendering each step.

Examples:
  python -m animal_kingdom.cli --bots random,random --seed 1
  python -m animal_kingdom.cli --bots human,random --seed 7

This is a thin caller of the engine - the same legal_actions / apply_action / is_terminal
loop a sim or a future web server would use. The engine itself does no I/O.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Sequence

from .bots.greedy_bot import GreedyBot
from .bots.random_bot import RandomBot
from .bots.referee_bot import RefereeBot
from .decks import PREMADE_DECKS, load_premade_deck, make_vanilla_deck
from .engine import rules
from .engine import strength as strength_mod
from .engine.actions import SKIP, Action, ChoiceAction, DrawAction, PlaceAction
from .engine.state import GameState, StateView, new_game
from .render.text import render


# One-line deck identities for the interactive picker (presentation only; the source of
# truth is docs/decks/README.md, which isn't shipped as data). Keep the slugs in sync
# with engine.cards.DECK_SLUGS.
_DECK_BLURBS = {
    "cats_midrange": "mono-Cat tempo / removal",
    "egg_control": "Snake/Bird/Egg draw-shuffle-remove into food",
    "colony_food_swarm": "mono-Colony swarm into food",
    "ramp": "ramp food into huge 'Costs 20' bodies",
    "food_otk": "sacrifice + Deathrattle food OTK",
    "aggro_hq_rush": "cheap chained bodies + reach to capture the HQ",
    "canine_buff_tempo": "mono-Canine persistent strength buffs",
}

# Opponent levels, in menu order: label -> bot kind understood by _make_controller.
_OPPONENT_LEVELS = [
    ("Easy — random bot", "random"),
    ("Normal — greedy bot (board heuristic + 1-ply lookahead)", "greedy"),
    ("Hard — referee bot (determinized adversarial search; thinks a few seconds)", "referee"),
]


def _fmt_action(a: Action, state: GameState | None = None) -> str:
    if isinstance(a, DrawAction):
        return "draw"
    if isinstance(a, PlaceAction):
        name = state.cards[a.card_id].name if state is not None else a.card_id
        dest = f"HQ {a.target[1]}" if a.is_hq_capture else a.target[1]
        return f"place {name} -> {dest}"
    return repr(a)


def _describe_action(state: GameState, a: Action) -> str:
    """Past-tense narration of a resolved action, for the turn log (card ids -> names)."""
    if isinstance(a, DrawAction):
        return "drew a card"
    if isinstance(a, PlaceAction):
        name = state.cards[a.card_id].name
        if a.is_hq_capture:
            return f"played {name} and captured HQ {a.target[1]}!"
        return f"played {name} onto {a.target[1]}"
    if isinstance(a, ChoiceAction):
        return "declined an optional effect" if a.choice == SKIP else f"chose {a.choice}"
    return repr(a)


def _banner_width() -> int:
    return max(72, shutil.get_terminal_size(fallback=(100, 24)).columns)


def _banner(label: str) -> str:
    label = f" {label.strip()} "
    pad = _banner_width() - len(label)
    left = max(0, pad) // 2
    return "\n" + "#" * left + label + "#" * max(0, pad - left)


def _turn_banner(turn: int, actor: str, human_seats: set[str]) -> str:
    suffix = ""  # in a spectated bot-vs-bot game neither seat is "you"/"opponent"
    if human_seats:
        suffix = " (you)" if actor in human_seats else " (opponent)"
    return _banner(f"TURN {turn} — seat {actor}{suffix}")


class HumanController:
    """Reads a choice from stdin. Lives in the CLI (not bots/) so the engine stays I/O-free."""

    def choose(self, view: StateView, legal: Sequence[Action],
               state: GameState | None = None) -> Action:
        legal = list(legal)
        for i, a in enumerate(legal):
            print(f"  [{i}] {_fmt_action(a, state)}")
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
    if kind == "referee":
        return RefereeBot(seed=seat_seed)
    if kind == "human":
        return HumanController()
    raise SystemExit(
        f"unknown bot kind {kind!r} (expected 'random', 'greedy', 'referee', or 'human')")


def _make_deck(spec: str, deck_rng: random.Random) -> list[str]:
    """A premade deck by slug, or a random vanilla deck when spec is 'vanilla'/empty."""
    spec = spec.strip()
    if spec in ("", "vanilla"):
        return make_vanilla_deck(seed=deck_rng.randrange(1 << 30))
    if spec not in PREMADE_DECKS:
        raise SystemExit(f"unknown deck {spec!r}; expected 'vanilla' or one of {sorted(PREMADE_DECKS)}")
    return load_premade_deck(spec)


def _prompt_menu(title: str, options: Sequence[tuple[str, str]]) -> str:
    """Print a numbered menu of (label, value) pairs and return the chosen value."""
    print(title)
    for i, (label, _) in enumerate(options):
        print(f"  [{i}] {label}")
    while True:
        try:
            raw = input("  choose #: ").strip()
        except EOFError:
            raise SystemExit("\nno input; aborting setup.")
        if raw.isdigit() and 0 <= int(raw) < len(options):
            return options[int(raw)][1]
        print(f"  enter a number 0..{len(options) - 1}")


def _interactive_setup() -> tuple[str, str]:
    """Ask for the player's deck, the opponent's deck, then the opponent's level.

    Returns (bot_spec, deck_spec) strings for play(); the human always takes seat A.
    """
    deck_options = [(f"{slug}  —  {_DECK_BLURBS[slug]}", slug) for slug in sorted(PREMADE_DECKS)]
    deck_options.append(("vanilla  —  random legal singleton pool", "vanilla"))

    print("\n=== New game ===\n")
    my_deck = _prompt_menu("Your deck:", deck_options)
    opp_deck = _prompt_menu("\nOpponent's deck:", deck_options)
    level = _prompt_menu("\nOpponent level:", _OPPONENT_LEVELS)
    print()
    return f"human,{level}", f"{my_deck},{opp_deck}"


def _board_snapshot(state: GameState) -> dict:
    """Compact board state: cr -> stack (bottom->top), each unit as id/owner/effective strength."""
    return {
        cr: [{"card_id": u.card_id, "owner": u.owner, "str": strength_mod.effective_strength(state, u)}
             for u in stack]
        for cr, stack in state.board.items() if stack
    }


def _default_log_path(seed: int) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("results") / "games" / f"{ts}_seed{seed}.json"


def _save_log(log: dict, path: str) -> str:
    """Writes the log to `path` (or stdout for '-'); returns a description for the user."""
    if path == "-":
        print(json.dumps(log, indent=2))
        return "stdout"
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(log, indent=2))
    return str(p)


def _maybe_save_log(log: dict, seed: int, log_arg: str | None, quiet: bool) -> None:
    """Honors an explicit --log path, or (interactively, unless --quiet) offers to save one."""
    if log_arg is not None:
        dest = _save_log(log, log_arg)
        print(f"\ngame log saved to {dest}", file=sys.stderr if log_arg == "-" else sys.stdout)
        return
    if quiet:
        return
    try:
        raw = input("\nSave agent-friendly game log (JSON)? [y/N]: ").strip().lower()
    except EOFError:
        return
    if raw.startswith("y"):
        dest = _save_log(log, str(_default_log_path(seed)))
        print(f"game log saved to {dest} — hand this to an agent for review.")


def play(bot_spec: str, seed: int, map_id: str, quiet: bool, decks: str,
          log_arg: str | None = None) -> None:
    kinds = bot_spec.split(",")
    if len(kinds) != 2:
        raise SystemExit("--bots expects two comma-separated kinds, e.g. random,random")
    controllers = {"A": _make_controller(kinds[0], "A", seed),
                   "B": _make_controller(kinds[1], "B", seed)}
    human_seats = {seat for seat, kind in zip(("A", "B"), kinds) if kind.strip().lower() == "human"}

    deck_specs = decks.split(",")
    if len(deck_specs) != 2:
        raise SystemExit("--decks expects two comma-separated decks, e.g. ramp,egg_control")
    deck_rng = random.Random(seed)
    deck_a = _make_deck(deck_specs[0], deck_rng)
    deck_b = _make_deck(deck_specs[1], deck_rng)
    state = new_game(deck_a, deck_b, seed, map_id=map_id)

    # '--log -' reserves stdout for the JSON dump; the normal play-by-play goes to stderr instead.
    out = sys.stderr if log_arg == "-" else sys.stdout

    log = {
        "meta": {"seed": seed, "map_id": map_id,
                 "decks": {"A": deck_specs[0].strip(), "B": deck_specs[1].strip()},
                 "bots": {"A": kinds[0].strip().lower(), "B": kinds[1].strip().lower()},
                 "opening_hands": {p: [u.card_id for u in state.hands[p]] for p in ("A", "B")}},
        "turns": [],
    }
    turn_no = state.turn_counter
    turn_owner = state.current
    turn_actions: list[dict] = []

    # In a human game we only draw the full board on the human's own turn; the opponent's
    # moves scroll by as one-line log entries. With no human (bot vs bot) we render every
    # step so a spectator sees the whole game. turn_counter drives the per-turn banner.
    spectate = not human_seats
    last_banner_turn = None
    while True:
        result = rules.is_terminal(state)
        if result is not None:
            break
        actor = state.player_to_act()

        if not quiet and state.turn_counter != last_banner_turn:
            print(_turn_banner(state.turn_counter, actor, human_seats), file=out)
            last_banner_turn = state.turn_counter
        if not quiet and (spectate or actor in human_seats):
            print(render(state, reveal_hands=human_seats), file=out)
            print(file=out)

        legal = rules.legal_actions(state)
        action = controllers[actor].choose(state.view_for(actor), legal, state)
        narration = _describe_action(state, action)
        rules.apply_action(state, action)
        if not quiet:
            tag = f"{actor}" + (" (you)" if actor in human_seats else "")
            print(f"  → {tag} {narration}", file=out)

        turn_actions.append({"actor": actor, "action": action.to_dict(), "narration": narration})
        if state.result is not None or state.turn_counter != turn_no:
            log["turns"].append({
                "turn": turn_no, "actor": turn_owner, "actions": turn_actions,
                "board": _board_snapshot(state), "food": dict(state.food),
                "hands": {p: [u.card_id for u in state.hands[p]] for p in ("A", "B")},
                "deck_counts": {p: len(state.decks[p]) for p in ("A", "B")},
                "remove_pile": list(state.remove_pile),
            })
            turn_no, turn_owner, turn_actions = state.turn_counter, state.current, []

    if not quiet:
        print(_banner("GAME OVER"), file=out)
    print(render(state, reveal_hands=human_seats), file=out)
    print(f"\nFINAL: winner={result.winner or 'draw'} reason={result.reason} "
          f"turns={state.turn_counter}", file=out)

    log["result"] = {"winner": result.winner, "reason": result.reason, "turns": state.turn_counter}
    _maybe_save_log(log, seed, log_arg, quiet)


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Play an Animal Kingdom game in the terminal.")
    p.add_argument("--bots", default=None,
                   help="two comma-separated controllers: random|greedy|human "
                        "(default: interactive setup, else random,random)")
    p.add_argument("--seed", type=int, default=None,
                   help="omit for a fresh random shuffle each run; pass a value to replay a game")
    p.add_argument("--map", dest="map_id", default="map_a")
    p.add_argument("--decks", default=None,
                   help="two comma-separated decks: 'vanilla' or a premade slug "
                        "(e.g. ramp,egg_control); default: interactive setup, else vanilla,vanilla")
    p.add_argument("--quiet", action="store_true", help="only print the final board/result")
    p.add_argument("--log", dest="log_path", default=None,
                   help="save an agent-friendly JSON game log to this path ('-' for stdout); "
                        "omit to be asked interactively at game end (skipped under --quiet)")
    args = p.parse_args(argv)

    # Bare `./run` (no bots/decks, interactive) walks the player through setup: your deck,
    # opponent's deck, opponent level. Any explicit flag skips it for scripted/bot-vs-bot runs.
    if args.bots is None and args.decks is None and not args.quiet:
        bots, decks = _interactive_setup()
    else:
        bots = args.bots if args.bots is not None else "random,random"
        decks = args.decks if args.decks is not None else "vanilla,vanilla"

    if args.seed is None:
        seed = random.SystemRandom().randrange(1 << 30)
        print(f"(seed={seed} — pass --seed {seed} to replay this exact game)")
    else:
        seed = args.seed
    play(bots, seed, args.map_id, args.quiet, decks, log_arg=args.log_path)


if __name__ == "__main__":
    main(sys.argv[1:])
