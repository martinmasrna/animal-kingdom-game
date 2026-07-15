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

from rich.console import Console

from .bots.greedy_bot import GreedyBot
from .bots.random_bot import RandomBot
from .bots.referee_bot import RefereeBot
from .bots.turn_bot import TurnBot
from .decks import PREMADE_DECKS, load_premade_deck, make_vanilla_deck
from .engine import rules
from .engine import strength as strength_mod
from .engine.actions import SKIP, Action, ChoiceAction, DrawAction, PlaceAction
from .engine.config import load_config_overrides
from .engine.state import GameState, StateView, new_game
from .render.text import HIGHLIGHT_STYLE, SEAT_STYLE, describe_action, parse_cr, render

# highlight=False: Rich's default ReprHighlighter would auto-color bare numbers/punctuation
# (board coordinates, region food values) on top of our own markup - noise, not signal.
_console_out = Console(highlight=False)
_console_err = Console(stderr=True, highlight=False)


def _console_for(stream) -> Console:
    return _console_err if stream is sys.stderr else _console_out


# One-line deck identities for the interactive picker (presentation only; the source of
# truth is docs/cards/decks/README.md, which isn't shipped as data). Keep the slugs in sync
# with engine.cards.DECK_SLUGS.
_DECK_BLURBS = {
    "cats_midrange": "mono-Cat tempo / removal",
    "egg_control": "Snake/Bird/Egg draw-shuffle-remove into food",
    "colony_food_swarm": "mono-Colony swarm into food",
    "ramp": "ramp food into huge 'Costs 15' bodies",
    "food_otk": "sacrifice + Deathrattle food OTK",
    "aggro_hq_rush": "cheap chained bodies + reach to capture the HQ",
    "canine_buff_tempo": "mono-Canine persistent strength buffs",
}

# Opponent levels, in menu order: label -> bot kind understood by _make_controller.
_OPPONENT_LEVELS = [
    ("Easy — random bot", "random"),
    ("Normal — greedy bot (board heuristic + 1-ply lookahead)", "greedy"),
    ("Hard — turn bot (plans a whole turn; determinized, no opponent rollout)", "turn"),
    ("Expert — referee bot (determinized adversarial search; thinks a few seconds)", "referee"),
]


def _banner_width() -> int:
    return max(72, shutil.get_terminal_size(fallback=(100, 24)).columns)


def _banner(label: str, style: str | None = None) -> str:
    label = f" {label.strip()} "
    pad = _banner_width() - len(label)
    left = max(0, pad) // 2
    right = max(0, pad - left)
    styled = f"[{style}]{label}[/{style}]" if style else label
    return "\n" + "#" * left + styled + "#" * right


def _turn_banner(turn: int, actor: str, human_seats: set[str]) -> str:
    suffix = ""  # in a spectated bot-vs-bot game neither seat is "you"/"opponent"
    if human_seats:
        suffix = " (you)" if actor in human_seats else " (opponent)"
    return _banner(f"TURN {turn} — seat {actor}{suffix}", SEAT_STYLE[actor])


class HumanController:
    """Reads a choice from stdin. Lives in the CLI (not bots/) so the engine stays I/O-free.

    A turn decision (draw vs. place a card) is a two-step pick: choose a card first, then
    see that card's legal targets highlighted on the board and choose one - closer to how a
    real board-game UI flows than a single flat list of every (card, target) pair. A
    sub-decision mid-effect-resolution (which enemy to remove, etc.) has no "which card"
    step, so it stays a flat numbered list.
    """

    def __init__(self, console: Console):
        self.console = console

    def choose(self, view: StateView, legal: Sequence[Action],
               state: GameState | None = None) -> Action:
        legal = list(legal)
        if legal and isinstance(legal[0], ChoiceAction):
            return self._choose_pending(view, legal)
        return self._choose_turn_action(view, legal, state)

    def _read(self, prompt: str, n: int, extra: Sequence[str] = ()) -> int | str:
        """Read an integer 0..n-1, or one of the single-letter `extra` options, from stdin."""
        while True:
            try:
                raw = input(prompt).strip().lower()
            except EOFError:
                raise SystemExit("\nno input; aborting.")
            if raw in extra:
                return raw
            if raw.isdigit() and 0 <= int(raw) < n:
                return int(raw)
            opts = f"0..{n - 1}" + (f", or {'/'.join(extra)}" if extra else "")
            self.console.print(f"  enter {opts}")

    def _choose_pending(self, view: StateView, legal: list[ChoiceAction]) -> Action:
        for i, a in enumerate(legal):
            label = "decline" if a.choice == SKIP else str(a.choice)
            self.console.print(f"  [bold]{i}[/bold] {label}")
        i = self._read(f"player {view.player} choose #: ", len(legal))
        return legal[i]

    def _choose_turn_action(self, view: StateView, legal: list[Action],
                             state: GameState) -> Action:
        draw = next((a for a in legal if isinstance(a, DrawAction)), None)
        by_card: dict[str, list[PlaceAction]] = {}
        for a in legal:
            if isinstance(a, PlaceAction):
                by_card.setdefault(a.card_id, []).append(a)
        # Menu order follows hand order, so it lines up with the card boxes on screen.
        card_ids = [u.card_id for u in state.hands[view.player] if u.card_id in by_card]

        while True:
            entries: list[tuple[str, PlaceAction | None]] = []
            if draw is not None:
                entries.append(("draw a card", None))
            for cid in card_ids:
                targets = by_card[cid]
                n = len(targets)
                hq_note = " (can capture HQ!)" if any(a.is_hq_capture for a in targets) else ""
                entries.append(
                    (f"{state.cards[cid].name} — {n} legal target{'s' if n != 1 else ''}{hq_note}",
                     cid))
            for i, (label, _) in enumerate(entries):
                self.console.print(f"  [bold]{i}[/bold] {label}")
            i = self._read(f"player {view.player} choose a card #: ", len(entries))
            _, picked = entries[i]
            if picked is None:
                return draw
            action = self._choose_target(view, state, picked, by_card[picked])
            if action is not None:
                return action
            # 'b'ack: redraw the card menu (the caller already re-renders the board plainly
            # next time round; here we just re-print the menu, no need to touch the screen).

    def _choose_target(self, view: StateView, state: GameState, card_id: str,
                        targets: list[PlaceAction]) -> PlaceAction | None:
        """Show the board with `targets` highlighted and let the player pick one, or 'b'ack."""
        crs = sorted((a for a in targets if not a.is_hq_capture),
                     key=lambda a: parse_cr(a.crossroad))
        hq = [a for a in targets if a.is_hq_capture]
        ordered = crs + hq  # HQ capture listed last - it's the highest-impact option
        highlight_hq = hq[0].target[1] if hq else None

        self.console.print(_banner(f"{state.cards[card_id].name} — choose a target",
                                    HIGHLIGHT_STYLE))
        self.console.print(render(state, reveal_hands={view.player},
                                   highlight_crs={a.crossroad for a in crs},
                                   highlight_hq=highlight_hq))
        self.console.print()
        for i, a in enumerate(ordered):
            dest = f"HQ {a.target[1]} — capture and win!" if a.is_hq_capture else a.crossroad
            self.console.print(f"  [bold]{i}[/bold] {dest}")
        choice = self._read(f"player {view.player} choose a target # ('b' to pick a "
                             "different card): ", len(ordered), extra=("b",))
        return None if choice == "b" else ordered[choice]


def _make_controller(kind: str, seat: str, seed: int, console: Console):
    kind = kind.strip().lower()
    seat_seed = seed + (1 if seat == "A" else 2)
    if kind == "random":
        return RandomBot(seed=seat_seed)
    if kind == "greedy":
        return GreedyBot(seed=seat_seed)
    if kind == "referee":
        return RefereeBot(seed=seat_seed)
    if kind == "turn":
        return TurnBot(seed=seat_seed)
    if kind == "human":
        return HumanController(console)
    raise SystemExit(
        f"unknown bot kind {kind!r} "
        "(expected 'random', 'greedy', 'turn', 'referee', or 'human')")


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
    _console_out.print(f"[bold]{title}[/bold]")
    for i, (label, _) in enumerate(options):
        _console_out.print(f"  [bold cyan]{i}[/bold cyan] {label}")
    while True:
        try:
            raw = input("  choose #: ").strip()
        except EOFError:
            raise SystemExit("\nno input; aborting setup.")
        if raw.isdigit() and 0 <= int(raw) < len(options):
            return options[int(raw)][1]
        _console_out.print(f"  enter a number 0..{len(options) - 1}")


def _interactive_setup() -> tuple[str, str]:
    """Ask for the player's deck, the opponent's deck, then the opponent's level.

    Returns (bot_spec, deck_spec) strings for play(); the human always takes seat A.
    """
    deck_options = [(f"{slug}  —  {_DECK_BLURBS[slug]}", slug) for slug in sorted(PREMADE_DECKS)]
    deck_options.append(("vanilla  —  random legal singleton pool", "vanilla"))

    _console_out.print("\n[bold]=== New game ===[/bold]\n")
    my_deck = _prompt_menu("Your deck:", deck_options)
    opp_deck = _prompt_menu("\nOpponent's deck:", deck_options)
    level = _prompt_menu("\nOpponent level:", _OPPONENT_LEVELS)
    _console_out.print()
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
        _console_for(sys.stderr if log_arg == "-" else sys.stdout).print(f"\ngame log saved to {dest}")
        return
    if quiet:
        return
    try:
        raw = input("\nSave agent-friendly game log (JSON)? [y/N]: ").strip().lower()
    except EOFError:
        return
    if raw.startswith("y"):
        dest = _save_log(log, str(_default_log_path(seed)))
        _console_out.print(f"game log saved to {dest} — hand this to an agent for review.")


def play(bot_spec: str, seed: int, map_id: str, quiet: bool, decks: str,
          log_arg: str | None = None, config_arg: str | None = None) -> None:
    kinds = bot_spec.split(",")
    if len(kinds) != 2:
        raise SystemExit("--bots expects two comma-separated kinds, e.g. random,random")
    # '--log -' reserves stdout for the JSON dump; the normal play-by-play goes to stderr instead.
    out = sys.stderr if log_arg == "-" else sys.stdout
    console = _console_for(out)
    controllers = {"A": _make_controller(kinds[0], "A", seed, console),
                   "B": _make_controller(kinds[1], "B", seed, console)}
    human_seats = {seat for seat, kind in zip(("A", "B"), kinds) if kind.strip().lower() == "human"}

    deck_specs = decks.split(",")
    if len(deck_specs) != 2:
        raise SystemExit("--decks expects two comma-separated decks, e.g. ramp,egg_control")
    deck_rng = random.Random(seed)
    deck_a = _make_deck(deck_specs[0], deck_rng)
    deck_b = _make_deck(deck_specs[1], deck_rng)
    state = new_game(deck_a, deck_b, seed, map_id=map_id,
                     config=load_config_overrides(config_arg))

    log = {
        "meta": {"seed": seed, "map_id": map_id, "config": config_arg,
                 "decks": {"A": deck_specs[0].strip(), "B": deck_specs[1].strip()},
                 "bots": {"A": kinds[0].strip().lower(), "B": kinds[1].strip().lower()},
                 "opening_hands": {p: [u.card_id for u in state.hands[p]] for p in ("A", "B")}},
        "turns": [],
    }
    turn_no = state.turn_counter
    turn_owner = state.current
    turn_actions: list[dict] = []

    # Bot-vs-bot (no human) is a debug/spectate log: render every step, scrolling, so the
    # full history stays in the terminal's scrollback. A human game instead redraws a fresh
    # screen right before *that* seat must decide - like a real client's board view - with
    # a short trail of what just happened (mostly the opponent's moves, which otherwise
    # wouldn't get a full board redraw of their own). turn_counter drives the per-turn banner.
    spectate = not human_seats
    recent: list[str] = []
    _RECENT_MAX = 6
    last_banner_turn = None
    while True:
        result = rules.is_terminal(state)
        if result is not None:
            break
        actor = state.player_to_act()
        my_turn = actor in human_seats

        if not quiet and (spectate or my_turn):
            if my_turn:
                console.clear()
                console.print(_turn_banner(state.turn_counter, actor, human_seats))
                last_banner_turn = state.turn_counter
                if recent:
                    console.print("[dim]" + "\n".join(recent) + "[/dim]")
                    console.print()
            elif state.turn_counter != last_banner_turn:
                console.print(_turn_banner(state.turn_counter, actor, human_seats))
                last_banner_turn = state.turn_counter
            console.print(render(state, reveal_hands=human_seats))
            console.print()

        legal = rules.legal_actions(state)
        action = controllers[actor].choose(state.view_for(actor), legal, state)
        narration = describe_action(state, action)
        rules.apply_action(state, action)
        if not quiet:
            tag = f"{actor}" + (" (you)" if actor in human_seats else "")
            line = f"  → {tag} {narration}"
            recent.append(line)
            del recent[:-_RECENT_MAX]
            console.print(line)

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
        if human_seats:
            console.clear()
        console.print(_banner("GAME OVER", SEAT_STYLE.get(result.winner) or "bold yellow"))
    console.print(render(state, reveal_hands=human_seats))
    console.print(f"\nFINAL: winner={result.winner or 'draw'} reason={result.reason} "
                  f"turns={state.turn_counter}")

    log["result"] = {"winner": result.winner, "reason": result.reason, "turns": state.turn_counter}
    _maybe_save_log(log, seed, log_arg, quiet)


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Play an Animal Kingdom game in the terminal.")
    p.add_argument("--bots", default=None,
                   help="two comma-separated controllers: random|greedy|turn|referee|human "
                        "(default: interactive setup, else random,random)")
    p.add_argument("--seed", type=int, default=None,
                   help="omit for a fresh random shuffle each run; pass a value to replay a game")
    p.add_argument("--map", dest="map_id", default="map_b")
    p.add_argument("--config", default=None,
                   help="JSON file of Config field overrides (rule/balance dials); "
                        "'none' clears a wrapper-injected preset")
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
        _console_out.print(f"[dim](seed={seed} — pass --seed {seed} to replay this exact game)[/dim]")
    else:
        seed = args.seed
    play(bots, seed, args.map_id, args.quiet, decks, log_arg=args.log_path,
         config_arg=args.config)


if __name__ == "__main__":
    main(sys.argv[1:])
