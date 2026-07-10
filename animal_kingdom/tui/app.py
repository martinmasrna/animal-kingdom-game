"""Persistent, low-friction Textual UI for recording human-vs-bot games."""

from __future__ import annotations

import argparse
import random
import sys
import textwrap
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from rich.markup import escape
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Click, Key, Leave, MouseMove, Resize
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Input, Label, Select, Static

from ..decks import PREMADE_DECKS
from ..engine import strength as strength_mod
from ..engine.actions import SKIP, Action, ChoiceAction, DrawAction, PlaceAction
from ..engine.config import Config, load_config_overrides
from ..recording.cohort import CohortManifest, ScheduledGame, config_drift, load_manifest
from ..recording.session import GameSetup, RecorderSession
from ..recording.writer import CohortProgress, summarize_cohort
from ..render.text import BoardRender, Hitbox, RARITY_STYLE, SEAT_STYLE, render_board
from ..sim.runner import BOT_KINDS


class DeckTracker(Static):
    """Known deck composition without exposing an opponent's hidden zones."""

    CONTENT_WIDTH = 29

    def __init__(self, *, id: str):
        super().__init__("", id=id, markup=True)
        self.starting_counts: Counter[str] = Counter()
        self.remaining_counts: Counter[str] = Counter()

    def set_counts(
        self,
        state,
        *,
        title: str,
        subtitle: str,
        starting: Counter[str],
        remaining: Counter[str],
        title_style: str,
    ) -> None:
        self.starting_counts = Counter(starting)
        self.remaining_counts = Counter({
            card_id: max(0, min(total, remaining.get(card_id, 0)))
            for card_id, total in starting.items()
        })
        total_remaining = sum(self.remaining_counts.values())
        lines = [
            f"[{title_style}]{escape(title)} · {total_remaining}[/{title_style}]",
            f"[dim]{escape(subtitle)}[/dim]",
        ]
        rarity_order = {"legendary": 0, "rare": 1, "common": 2}
        card_ids = sorted(
            starting,
            key=lambda card_id: (
                rarity_order[state.cards[card_id].rarity],
                state.cards[card_id].name,
            ),
        )
        for card_id in card_ids:
            card = state.cards[card_id]
            left = self.remaining_counts[card_id]
            count = f"(x{left})"
            prefix_width = len(count) + 1
            max_name_width = self.CONTENT_WIDTH - prefix_width
            name = card.name
            if len(name) > max_name_width:
                name = name[: max_name_width - 1].rstrip() + "…"
            if left == 0:
                lines.append(f"[dim]{count} {escape(name)}[/dim]")
                continue
            name_style = RARITY_STYLE.get(card.rarity)
            styled_name = (
                f"[{name_style}]{escape(name)}[/{name_style}]"
                if name_style
                else escape(name)
            )
            lines.append(f"{count} {styled_name}")
        self.update("\n".join(lines))


class RecentActionIcon(Static):
    """One compact public-history glyph with the narration available on hover."""

    def __init__(self, narration: str, index: int):
        actor, separator, action = narration.partition(": ")
        action_text = action if separator else narration
        symbol = (
            "⚑" if "captured HQ" in action_text
            else "↓" if "drew" in action_text
            else "◆" if "played" in action_text
            else "×" if "declined" in action_text
            else "◇" if "chose" in action_text
            else "•"
        )
        style = SEAT_STYLE.get(actor, "bold")
        label = f"{actor}{symbol}" if separator else symbol
        super().__init__(
            f"[{style}]{label}[/{style}]",
            id=f"recent-{index}",
            markup=True,
        )
        self.tooltip = narration


class RecentLog(Vertical):
    """Newest-first action icons; full public text lives in per-icon tooltips."""

    entries: reactive[tuple[str, ...]] = reactive(tuple, recompose=True)

    def __init__(self) -> None:
        super().__init__(id="recent-log")

    def compose(self) -> ComposeResult:
        for index, narration in enumerate(reversed(self.entries)):
            yield RecentActionIcon(narration, index)

    def set_entries(self, entries: Sequence[str]) -> None:
        self.entries = tuple(entries[-6:])


class BoardWidget(Static):
    """Board markup with visible-coordinate target hitboxes."""

    can_focus = True

    class TargetClicked(Message):
        def __init__(self, target: tuple[str, str]):
            super().__init__()
            self.target = target

    class TargetHovered(Message):
        def __init__(self, target: tuple[str, str] | None):
            super().__init__()
            self.target = target

    def __init__(self) -> None:
        super().__init__("", id="board", markup=True)
        self.board_render: Optional[BoardRender] = None
        self._state = None
        self._hovered_target: tuple[str, str] | None = None

    def _set_hovered_target(self, target: tuple[str, str] | None) -> None:
        if target == self._hovered_target:
            return
        self._hovered_target = target
        self.post_message(self.TargetHovered(target))

    def set_position(
        self,
        state,
        targets: set[tuple[str, str]],
        focused: tuple[str, str] | None,
        perspective_player: str,
    ) -> None:
        self._state = state
        crs = {value for kind, value in targets if kind == "cr"}
        hqs = [value for kind, value in targets if kind == "hq"]
        width = max(1, self.size.width or self.content_size.width or 80)
        height = max(1, self.size.height)
        # Keep a little air around the map when the pane allows it. The renderer still
        # receives the constrained inner dimensions, so compact terminals retain the
        # same fit guarantees as before.
        inner_width = max(1, width - 2)
        inner_height = max(1, height - 2)
        board = render_board(
            state,
            highlight_crs=crs,
            highlight_hq=hqs[0] if hqs else None,
            focus_target=focused,
            max_width=inner_width,
            vertical_gap=1 if height < 18 else 3,
            perspective_player=perspective_player,
            max_height=inner_height,
            show_coords=False,
        )
        x_offset = max(0, (width - board.width) // 2)
        y_offset = max(0, (height - board.height) // 2)
        markup = "\n" * y_offset + "\n".join(
            " " * x_offset + line for line in board.markup.splitlines()
        )
        self.board_render = BoardRender(
            markup=markup,
            hitboxes={
                target: Hitbox(
                    hitbox.x + x_offset,
                    hitbox.y + y_offset,
                    hitbox.width,
                    hitbox.height,
                )
                for target, hitbox in board.hitboxes.items()
            },
            width=x_offset + board.width,
            height=y_offset + board.height,
        )
        self.update(self.board_render.markup)

    def on_mouse_move(self, event: MouseMove) -> None:
        if self.board_render is None or self._state is None:
            self.tooltip = None
            self._set_hovered_target(None)
            return
        x, y = event.offset
        hovered = next(
            (
                target
                for target, hitbox in self.board_render.hitboxes.items()
                if hitbox.contains(x, y)
            ),
            None,
        )
        self._set_hovered_target(hovered)
        if hovered is None:
            self.tooltip = None
            return
        kind, value = hovered
        if kind == "hq":
            self.tooltip = f"HQ {value}"
            return
        stack = self._state.board.get(value, ())
        if not stack:
            self.tooltip = f"Crossroad {value}\n(empty)"
            return
        lines = [f"Crossroad {value} — bottom → top"]
        for unit in stack:
            card = self._state.cards[unit.card_id]
            tags = "/".join(sorted(card.tags))
            header = f"{unit.owner}  {card.name}  —  STR {strength_mod.effective_strength(self._state, unit)}"
            if tags:
                header += f"  ({tags})"
            lines.append(header)
            if card.text:
                lines.append(card.text)
        self.tooltip = "\n".join(lines)

    def on_leave(self, _event: Leave) -> None:
        self.tooltip = None
        self._set_hovered_target(None)

    def on_resize(self, _event: Resize) -> None:
        if self._state is not None:
            self.call_after_refresh(self.app.refresh_game)

    def on_click(self, event: Click) -> None:
        if self.board_render is None:
            return
        x, y = event.offset
        for target, hitbox in self.board_render.hitboxes.items():
            if hitbox.contains(x, y):
                self.post_message(self.TargetClicked(target))
                event.stop()
                return


@dataclass(frozen=True)
class ActionEntry:
    label: str
    payload: Any
    enabled: bool = True
    selected: bool = False
    effect: str = ""
    stats: str = ""


class ActionCard(Static):
    """One fully clickable compact card with the information needed to decide."""

    can_focus = True

    def __init__(self, entry: ActionEntry, index: int):
        is_draw = isinstance(entry.payload, DrawAction)
        inner = 12 if is_draw else 20
        super().__init__(self._markup(entry, inner), id=f"action-{index}", markup=True)
        self.entry = entry
        self.set_class(is_draw, "draw")
        self.tooltip = "\n".join(
            part for part in (entry.label, entry.effect, entry.stats) if part
        )
        self.set_class(not entry.enabled, "disabled")
        self.set_class(entry.selected, "selected")

    @classmethod
    def _markup(cls, entry: ActionEntry, inner: int) -> str:
        effect_lines = textwrap.wrap(entry.effect, inner) if entry.effect else []
        if len(effect_lines) > 3:
            effect_lines = effect_lines[:3]
            effect_lines[-1] = effect_lines[-1][: inner - 1].rstrip() + "…"
        effect_lines += [""] * (3 - len(effect_lines))
        stats = entry.stats
        if len(stats) > inner:
            stats = stats[: inner - 1] + "…"
        marker = "▶ " if entry.selected else "× " if not entry.enabled else ""
        full_name = marker + entry.label
        name = full_name if len(full_name) <= inner else full_name[: inner - 1] + "…"
        border_style = (
            "bold yellow" if entry.selected
            else "blue" if entry.enabled
            else "grey42"
        )
        body_style = "dim" if not entry.enabled else ""

        def border(line: str) -> str:
            return f"[{border_style}]{line}[/{border_style}]"

        def body(line: str) -> str:
            escaped = escape(line.ljust(inner))
            return f"[{body_style}]{escaped}[/{body_style}]" if body_style else escaped

        return "\n".join([
            border("┌" + "─" * inner + "┐"),
            border("│") + body(name.center(inner)) + border("│"),
            border("│") + body(effect_lines[0]) + border("│"),
            border("│") + body(effect_lines[1]) + border("│"),
            border("│") + body(effect_lines[2]) + border("│"),
            border("│") + body(stats) + border("│"),
            border("└" + "─" * inner + "┘"),
        ])

    def on_click(self, event: Click) -> None:
        if self.entry.enabled:
            self.post_message(CardShelf.EntryClicked(self.entry.payload))
            event.stop()


class CardShelf(Horizontal):
    """A persistent horizontally scrollable shelf of information-rich cards."""

    CARD_WIDTH = 22
    DRAW_WIDTH = 14
    CARD_MARGIN = 1

    entries: reactive[tuple[ActionEntry, ...]] = reactive(tuple, recompose=True)

    class EntryClicked(Message):
        def __init__(self, payload: Any):
            super().__init__()
            self.payload = payload

    def __init__(self) -> None:
        super().__init__(id="actions")

    def compose(self) -> ComposeResult:
        for index, entry in enumerate(self.entries):
            yield ActionCard(entry, index)

    def set_entries(self, entries: Sequence[ActionEntry]) -> None:
        self.entries = tuple(entries)
        self._update_fit_class()

    def on_resize(self, _event: Resize) -> None:
        self._update_fit_class()

    def _update_fit_class(self) -> None:
        content_width = sum(
            (
                self.DRAW_WIDTH
                if isinstance(entry.payload, DrawAction)
                else self.CARD_WIDTH
            )
            + self.CARD_MARGIN
            for entry in self.entries
        )
        self.set_class(bool(self.entries) and content_width <= self.size.width, "fits")


class SetupScreen(Screen[GameSetup]):
    """Compact ad-hoc game setup; scheduled cohorts bypass this screen."""

    CSS = """
    SetupScreen { align: center middle; }
    #setup { width: 64; height: auto; border: round $primary; padding: 1 2; }
    .setup-row { height: 3; width: 100%; }
    .setup-row Label { width: 18; padding-top: 1; }
    .setup-row Select, .setup-row Input { width: 1fr; }
    #start { width: 100%; }
    """

    def __init__(self, *, config: Config, map_id: str, player_id: str):
        super().__init__()
        self.config = config
        self.map_id = map_id
        self.player_id = player_id

    def compose(self) -> ComposeResult:
        deck_options = [(slug, slug) for slug in sorted(PREMADE_DECKS)]
        bot_options = [(kind, kind) for kind in BOT_KINDS]
        with Vertical(id="setup"):
            yield Label(f"New recorded game — {self.map_id}")
            with Horizontal(classes="setup-row"):
                yield Label("Your deck")
                yield Select(deck_options, value=deck_options[0][1], id="human-deck")
            with Horizontal(classes="setup-row"):
                yield Label("Opponent deck")
                yield Select(deck_options, value=deck_options[1][1], id="opponent-deck")
            with Horizontal(classes="setup-row"):
                yield Label("Opponent bot")
                yield Select(bot_options, value="greedy", id="opponent-kind")
            with Horizontal(classes="setup-row"):
                yield Label("Your seat")
                yield Select([("Seat A", "A"), ("Seat B", "B")], value="A", id="human-seat")
            with Horizontal(classes="setup-row"):
                yield Label("Seed")
                yield Input(str(random.SystemRandom().randrange(1 << 30)), id="seed")
            yield Label("", id="setup-error")
            yield Button("Start", id="start", variant="primary")

    @on(Button.Pressed, "#start")
    def start_game(self) -> None:
        try:
            seed = int(self.query_one("#seed", Input).value)
            setup = GameSetup(
                human_deck=str(self.query_one("#human-deck", Select).value),
                opponent_deck=str(self.query_one("#opponent-deck", Select).value),
                opponent_kind=str(self.query_one("#opponent-kind", Select).value),
                human_seat=str(self.query_one("#human-seat", Select).value),
                seed=seed,
                map_id=self.map_id,
                config=self.config,
                player_id=self.player_id,
            )
            setup.validate()
        except (TypeError, ValueError) as exc:
            self.query_one("#setup-error", Label).update(str(exc))
            return
        self.dismiss(setup)


class HelpScreen(ModalScreen[None]):
    """Compact command reference; recorder-only controls stay out of the main footer."""

    CSS = """
    HelpScreen { align: center middle; }
    #help {
        width: 62;
        height: auto;
        max-height: 90%;
        padding: 1 2;
        border: round $primary;
        background: $panel;
    }
    """
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Static(
            "\n".join([
                "[bold]HOW TO PLAY[/bold]",
                "[bold]D[/bold]        Draw",
                "[bold]1–9[/bold]      Select a card",
                "[bold]Arrows[/bold]   Move between legal targets",
                "[bold]Enter[/bold]    Confirm target / continue after a game",
                "[bold]Esc[/bold]      Cancel card selection",
                "",
                "[bold]GAME & RECORDING[/bold]",
                "[bold]O[/bold]        Open the completed game's JSONL log",
                "[bold]M[/bold]        Exclude / restore the latest human decision",
                "[bold]G[/bold]        Exclude / restore the entire game",
                "[bold]Q[/bold]        Quit safely",
                "",
                "[dim]Every action is saved to JSONL as it happens.[/dim]",
                "[dim]Press ? or Esc to close.[/dim]",
            ]),
            id="help",
            markup=True,
        )


class RecorderApp(App[None]):
    """One-screen recorder with direct board actions and durable transition logging."""

    TITLE = "Animal Kingdom — Human Benchmark Recorder"
    # Disable Textual's terminal text-selection: the recorder never needs it, and a
    # double-click on a parentless widget (e.g. an ActionCard) crashes Textual 8.2.8's
    # selection path (screen.py:1914 dereferences a None container). Gated off here.
    ALLOW_SELECT = False
    HORIZONTAL_BREAKPOINTS = [
        (0, "layout-narrow"),
        (110, "layout-inspector"),
        (130, "layout-trackers"),
        (170, "layout-wide"),
    ]
    VERTICAL_BREAKPOINTS = [
        (0, "height-compact"),
        (32, "height-full"),
    ]
    CSS = """
    Screen { layout: vertical; }
    #status {
        height: 1;
        padding: 0 2;
        background: $panel;
        text-align: center;
    }
    #opponent, #player {
        height: 1;
        padding: 0 2;
        background: $boost;
    }
    #opponent { text-align: center; }
    #player { text-align: center; }
    #main { height: 1fr; min-height: 14; }
    #board { width: 1fr; height: 100%; overflow: hidden hidden; }
    #recent-log {
        width: 5;
        height: 100%;
        padding-top: 1;
        align-horizontal: center;
        background: $background;
        overflow: hidden hidden;
    }
    RecentActionIcon {
        width: 4;
        height: 1;
        margin-bottom: 1;
        text-align: center;
        background: $boost;
    }
    DeckTracker {
        width: 31;
        height: 100%;
        padding: 1;
        background: $surface;
        overflow: hidden hidden;
    }
    #opponent-deck { background: $panel; }
    #side {
        width: 31;
        height: 100%;
        padding: 1 2;
        background: $panel;
        overflow: hidden hidden;
    }
    #notice {
        height: 1;
        padding: 0 2;
        background: $primary-background;
        text-align: center;
        text-style: bold;
    }
    #actions {
        height: 7;
        layout: horizontal;
        overflow-x: auto;
        overflow-y: hidden;
        scrollbar-size-horizontal: 0;
    }
    #actions.fits { align-horizontal: center; }
    ActionCard { width: 22; height: 7; margin-right: 1; }
    ActionCard.draw { width: 14; }
    ActionCard:focus { background: $boost; }
    Footer { height: 1; }
    .layout-narrow DeckTracker, .layout-narrow #side { display: none; }
    .layout-inspector DeckTracker { display: none; }
    .layout-trackers #side { display: none; }
    .height-compact DeckTracker,
    .height-compact #status,
    .height-compact #opponent,
    .height-compact Footer { display: none; }
    """
    BINDINGS = [
        ("q", "quit_recorder", "Quit"),
        ("d", "draw", "Draw"),
        ("escape", "cancel_selection", "Cancel"),
        ("left", "previous_target", "Previous target"),
        ("up", "previous_target", "Previous target"),
        ("right", "next_target", "Next target"),
        ("down", "next_target", "Next target"),
        ("enter", "confirm_target", "Confirm/next"),
        Binding("m", "mark_decision", "Mark decision", show=False),
        Binding("g", "mark_game", "Mark game", show=False),
        Binding("o", "open_recording", "Open game log", show=False),
        Binding("question_mark", "show_help", "Help"),
    ]

    def __init__(
        self,
        *,
        manifest: CohortManifest | None = None,
        output_root: Path = Path("results/human_games"),
        player_id: str = "human-1",
        ad_hoc_config: Config | None = None,
        ad_hoc_map: str = "map_b",
    ):
        super().__init__()
        self.manifest = manifest
        self.output_root = Path(output_root)
        self.player_id = player_id
        self.ad_hoc_config = ad_hoc_config or Config.default()
        self.ad_hoc_map = ad_hoc_map
        self.session: RecorderSession | None = None
        self.cohort_progress: CohortProgress = CohortProgress()
        self.selected_card: str | None = None
        self.target_map: dict[tuple[str, str], Action] = {}
        self.target_order: list[tuple[str, str]] = []
        self.target_index = 0
        self.entry_shortcuts: list[Any] = []
        self.bot_busy = False
        self.hovered_target: tuple[str, str] | None = None
        self.revealed_cards: dict[str, Counter[str]] = {
            "A": Counter(),
            "B": Counter(),
        }
        self._seen_board_iids: set[int] = set()

    def compose(self) -> ComposeResult:
        yield Static("Starting…", id="status", markup=True)
        yield Static("", id="opponent", markup=True)
        with Horizontal(id="main"):
            yield DeckTracker(id="own-deck")
            yield BoardWidget()
            yield RecentLog()
            yield DeckTracker(id="opponent-deck")
            yield Static("", id="side", markup=True)
        yield Static("", id="notice", markup=True)
        yield Static("", id="player", markup=True)
        yield CardShelf()
        yield Footer()

    def on_mount(self) -> None:
        if self.manifest is not None:
            self.start_next_scheduled_game()
        else:
            self.push_screen(
                SetupScreen(
                    config=self.ad_hoc_config,
                    map_id=self.ad_hoc_map,
                    player_id=self.player_id,
                ),
                self.start_game,
            )

    def on_ready(self) -> None:
        # The initial session may render during on_mount before final widget dimensions
        # exist; redraw once layout has assigned the real 80x24/wide-pane sizes.
        self.refresh_game()

    def _scheduled_setup(self, game: ScheduledGame) -> GameSetup:
        assert self.manifest is not None
        return GameSetup(
            human_deck=game.human_deck,
            opponent_deck=game.opponent_deck,
            human_seat=game.human_seat,
            opponent_kind=game.opponent_kind,
            seed=game.seed,
            map_id=self.manifest.map_id,
            config=self.manifest.config,
            player_id=self.player_id,
            cohort_id=self.manifest.cohort_id,
            scheduled_game_id=game.game_id,
        )

    def start_next_scheduled_game(self) -> None:
        assert self.manifest is not None
        if self.session is not None:
            self.session.close(reason="next_game")
            self.session = None
        cohort_dir = self.output_root / self.manifest.cohort_id
        progress = summarize_cohort(cohort_dir.glob("*.jsonl") if cohort_dir.exists() else [])
        self.cohort_progress = progress
        game = next((g for g in self.manifest.games if g.game_id not in progress.completed_ids), None)
        if game is None:
            self.query_one("#status", Static).update(
                f"[bold green]Cohort complete[/bold green] · {self._record_text(progress)}")
            self.query_one("#notice", Static).update(self._per_opponent_text(progress) + "  ·  Q quits.")
            self.query_one(CardShelf).set_entries([])
            return
        self.start_game(self._scheduled_setup(game))

    @staticmethod
    def _record_text(prog: CohortProgress) -> str:
        rec = f"{prog.win}–{prog.loss}" + (f"–{prog.draw}" if prog.draw else "")
        return f"you {rec} ({prog.win_pct:.0f}%)" if prog.decided else "you 0–0"

    @staticmethod
    def _per_opponent_text(prog: CohortProgress) -> str:
        parts = []
        for opp in sorted(prog.per_opponent):
            w, l, d = prog.per_opponent[opp]
            dec = w + l
            pct = f" {100 * w / dec:.0f}%" if dec else ""
            parts.append(f"{opp.split('_')[0]} {w}–{l}" + (f"–{d}" if d else "") + pct)
        return "   ".join(parts)

    def start_game(self, setup: GameSetup | None) -> None:
        if setup is None:
            return
        if self.session is not None:
            self.session.close(reason="new_game")
        self.session = RecorderSession(setup, output_root=self.output_root)
        self.selected_card = None
        self.target_map.clear()
        self.target_order.clear()
        self.target_index = 0
        self.bot_busy = False
        self.hovered_target = None
        self.revealed_cards = {"A": Counter(), "B": Counter()}
        self._seen_board_iids.clear()
        self.refresh_game()
        self.maybe_start_bot()

    def _food_progress(self, state, player: str) -> str:
        value = state.food[player]
        target = state.game_map.win_food
        width = 18 if self.size.width >= 130 else 10
        filled = max(0, min(width, round(width * value / target)))
        empty = width - filled
        style = SEAT_STYLE.get(player, "bold")
        bar = (
            f"[{style}]{'█' * filled}[/{style}]"
            f"[dim]{'░' * empty}[/dim]"
        )
        return f"Food {value}/{target} ▕{bar}▏"

    def refresh_game(self) -> None:
        session = self.session
        if session is None:
            return
        state = session.state
        result = session.result
        actor = state.player_to_act()
        human = session.setup.human_seat
        opponent = next(player for player in state.game_map.players if player != human)
        invalid = " [bold red]GAME EXCLUDED[/bold red]" if not session.game_valid else ""
        cohort_text = ""
        if self.manifest is not None and session.setup.scheduled_game_id:
            index = next(
                i for i, game in enumerate(self.manifest.games, start=1)
                if game.game_id == session.setup.scheduled_game_id
            )
            cohort_text = f" · Game {index}/{len(self.manifest.games)}"
            prog = self.cohort_progress
            if prog.played:
                cohort_text += f" · {self._record_text(prog)}"
                w, l, d = prog.per_opponent.get(session.setup.opponent_deck, [0, 0, 0])
                if w + l + d:
                    cohort_text += f" · vs {session.setup.opponent_deck.split('_')[0]} {w}–{l}"

        if result:
            winner = "Draw" if result.winner is None else (
                "You win" if result.winner == human else "Opponent wins"
            )
            phase = f"{winner} · {escape(result.reason)}"
        elif self.bot_busy:
            phase = "Opponent thinking…"
        elif actor == human and state.pending:
            phase = "Resolve effect"
        elif actor == human:
            phase = "Your turn"
        else:
            phase = "Opponent turn"
        self.query_one("#status", Static).update(
            f"[bold]{phase}[/bold] · Turn {state.turn_counter + 1}{cohort_text}{invalid}"
        )

        self.query_one("#opponent", Static).update(
            f"{self._food_progress(state, opponent)}"
            f"  ·  Hand {len(state.hands[opponent])}"
            f"  ·  Deck {len(state.decks[opponent])}"
        )
        actions_remaining = max(
            0,
            state.config.actions_per_turn - state.actions_taken_this_turn,
        )
        action_text = (
            f"  ·  Actions {actions_remaining}"
            if actor == human and result is None
            else ""
        )
        self.query_one("#player", Static).update(
            f"{self._food_progress(state, human)}"
            f"  ·  Cards {len(state.hands[human])}"
            f"  ·  Deck {len(state.decks[human])}"
            f"{action_text}"
        )
        self._update_deck_trackers()

        self._build_action_state()
        focused = self.target_order[self.target_index] if self.target_order else None
        self.query_one(BoardWidget).set_position(
            state,
            set(self.target_map),
            focused,
            session.setup.human_seat,
        )
        self.query_one(CardShelf).set_entries(self._action_entries())
        self.query_one(RecentLog).set_entries(session.recent)
        self._update_side(focused)
        self._update_prompt()

    def _observe_public_cards(self) -> None:
        """Remember cards revealed on the board without reading hidden opponent zones."""
        assert self.session is not None
        state = self.session.state
        for stack in state.board.values():
            for unit in stack:
                if unit.iid in self._seen_board_iids:
                    continue
                self._seen_board_iids.add(unit.iid)
                self.revealed_cards[unit.owner][unit.card_id] += 1

        # The Remove Pile is public but stores card ids without owners. Card ids identify
        # their premade deck exactly when the players brought different decks; in a mirror,
        # attribution would leak/guess ownership, so leave those copies conservatively unseen.
        if self.setup.human_deck == self.setup.opponent_deck:
            return
        deck_by_player = {
            self.setup.human_seat: self.setup.human_deck,
            next(
                player
                for player in state.game_map.players
                if player != self.setup.human_seat
            ): self.setup.opponent_deck,
        }
        removed = Counter(state.remove_pile)
        for player, deck_slug in deck_by_player.items():
            for card_id, count in removed.items():
                if state.cards[card_id].deck == deck_slug:
                    self.revealed_cards[player][card_id] = max(
                        self.revealed_cards[player][card_id],
                        count,
                    )

    def _update_deck_trackers(self) -> None:
        assert self.session is not None
        state = self.session.state
        human = self.setup.human_seat
        opponent = next(player for player in state.game_map.players if player != human)
        self._observe_public_cards()

        own_starting = Counter(state.starting_decks[human])
        own_remaining = Counter(state.decks[human])
        opponent_starting = Counter(state.starting_decks[opponent])
        opponent_remaining = Counter({
            card_id: max(
                0,
                total - self.revealed_cards[opponent].get(card_id, 0),
            )
            for card_id, total in opponent_starting.items()
        })
        self.query_one("#own-deck", DeckTracker).set_counts(
            state,
            title="YOUR DECK",
            subtitle="copies remaining",
            starting=own_starting,
            remaining=own_remaining,
            title_style=SEAT_STYLE.get(human, "bold"),
        )
        self.query_one("#opponent-deck", DeckTracker).set_counts(
            state,
            title="OPPONENT UNSEEN",
            subtitle="remaining in deck + hand",
            starting=opponent_starting,
            remaining=opponent_remaining,
            title_style=SEAT_STYLE.get(opponent, "bold"),
        )

    def _update_prompt(self) -> None:
        assert self.session is not None
        session = self.session
        state = session.state
        if session.result:
            next_game = (
                "start the next game"
                if self.manifest is not None
                else "open a new game"
            )
            prompt = (
                "[bold green]Game recorded[/bold green] · "
                f"{self._recording_link('Open JSONL log (O)')} · "
                f"Press Enter to {next_game}"
            )
        elif self.bot_busy or not session.human_turn:
            prompt = "Opponent is thinking…"
        elif state.pending:
            board_hint = "a highlighted location or " if self.target_map else ""
            prompt = f"Resolve effect · Choose {board_hint}an option below"
        elif self.selected_card:
            card_name = escape(state.cards[self.selected_card].name)
            prompt = f"Place [bold]{card_name}[/bold] · Choose a highlighted location"
        else:
            prompt = "Choose a card from your hand or draw"
        self.query_one("#notice", Static).update(prompt)

    def _recording_link(self, label: str | None = None) -> str:
        assert self.session is not None
        path = self.session.path.resolve()
        link_label = label if label is not None else str(path)
        return f"[@click=app.open_recording underline]{escape(link_label)}[/]"

    def _build_action_state(self) -> None:
        self.target_map.clear()
        self.target_order.clear()
        session = self.session
        if session is None or session.result is not None or not session.human_turn:
            return
        state = session.state
        legal = session.legal_actions
        if state.pending and state.pending["mode"] == "choice":
            for action in legal:
                if (
                    isinstance(action, ChoiceAction)
                    and isinstance(action.choice, str)
                    and action.choice in state.game_map.crossroads
                ):
                    self.target_map[("cr", action.choice)] = action
        elif self.selected_card is not None:
            placements = [
                action for action in legal
                if isinstance(action, PlaceAction) and action.card_id == self.selected_card
            ]
            if not placements:
                self.selected_card = None
            else:
                for action in placements:
                    self.target_map[action.target] = action
        self.target_order = sorted(
            self.target_map,
            key=lambda target: (target[0] == "hq", target[1]),
        )
        if self.target_order:
            self.target_index %= len(self.target_order)
        else:
            self.target_index = 0

    @property
    def setup(self) -> GameSetup:
        assert self.session is not None
        return self.session.setup

    def _choice_label(self, action: ChoiceAction) -> str:
        assert self.session is not None
        state = self.session.state
        choice = action.choice
        if choice == SKIP:
            return "Decline"
        if isinstance(choice, int):
            for unit in state.hands[self.setup.human_seat]:
                if unit.iid == choice:
                    return state.cards[unit.card_id].name
        if isinstance(choice, str) and choice in state.cards:
            return state.cards[choice].name
        return str(choice)

    def _action_entries(self) -> list[ActionEntry]:
        session = self.session
        self.entry_shortcuts = []
        if session is None or session.result is not None:
            return []
        state = session.state
        legal = session.legal_actions
        if not session.human_turn or self.bot_busy:
            return []
        entries: list[ActionEntry] = []
        if state.pending and state.pending["mode"] == "choice":
            board_choices = set(self.target_map.values())
            for action in legal:
                if action not in board_choices:
                    label = f"{len(entries) + 1} {self._choice_label(action)}"
                    entries.append(ActionEntry(label, action))
                    self.entry_shortcuts.append(action)
            return entries

        draw = next((action for action in legal if isinstance(action, DrawAction)), None)
        if draw is not None:
            draw_count = state.config.draw_action_count
            entries.append(ActionEntry(
                "D DRAW",
                draw,
                effect=f"Draw {draw_count} card{'s' if draw_count != 1 else ''}",
            ))
        playable = {action.card_id for action in legal if isinstance(action, PlaceAction)}
        seen: set[str] = set()
        card_number = 0
        for unit in state.hands[self.setup.human_seat]:
            if unit.card_id in seen:
                continue
            seen.add(unit.card_id)
            card_number += 1
            count = sum(u.card_id == unit.card_id for u in state.hands[self.setup.human_seat])
            card = state.cards[unit.card_id]
            name = card.name
            label = f"{card_number} {name}" + (f" ×{count}" if count > 1 else "")
            payload = ("card", unit.card_id)
            strength = strength_mod.placement_strength(state, unit)
            tags = "/".join(sorted(card.tags))
            entries.append(ActionEntry(
                label,
                payload,
                enabled=unit.card_id in playable,
                selected=unit.card_id == self.selected_card,
                effect=card.text,
                stats=f"STR {strength}   {tags}",
            ))
            self.entry_shortcuts.append(payload if unit.card_id in playable else None)
        return entries

    def _update_side(self, focused: tuple[str, str] | None = None) -> None:
        assert self.session is not None
        state = self.session.state
        lines: list[str] = []
        if self.session.result is None and self.selected_card:
            unit = next(
                u for u in state.hands[self.setup.human_seat]
                if u.card_id == self.selected_card
            )
            card = state.cards[self.selected_card]
            stats = f"STR {strength_mod.placement_strength(state, unit)}"
            if card.food_cost:
                stats += f" · Costs {card.food_cost} food"
            if card.tags:
                stats += f" · {escape(' / '.join(sorted(card.tags)))}"
            lines.extend([
                "[bold]SELECTED CARD[/bold]",
                f"[bold]{escape(card.name)}[/bold] · "
                f"{escape(card.rarity.title())} {escape(card.type.title())}",
                stats,
                escape(card.text),
            ])
        inspected = None if self.session.result else self.hovered_target or focused
        if inspected:
            if lines:
                lines.append("")
            kind, value = inspected
            is_legal = inspected in self.target_map
            lines.append("[bold]LOCATION[/bold]")
            if kind == "hq":
                relationship = "Yours" if value == self.setup.human_seat else "Opponent"
                lines.append(f"[bold]HQ {escape(value)}[/bold] · {relationship}")
            else:
                lines.append(f"[bold]Crossroad {escape(value)}[/bold]")
            if is_legal:
                lines.append("[bold green]LEGAL TARGET[/bold green]")

            stack = state.board.get(value, []) if kind == "cr" else []
            if kind == "cr" and not stack:
                lines.append("Empty")
            elif stack:
                count = len(stack)
                lines.append(f"STACK · {count} card{'s' if count != 1 else ''} · top first")
                for unit in reversed(stack):
                    card = state.cards[unit.card_id]
                    owner_style = SEAT_STYLE.get(unit.owner, "bold")
                    lines.append(
                        f"[{owner_style}]{unit.owner}[/{owner_style}] "
                        f"{escape(card.name)} · STR "
                        f"{strength_mod.effective_strength(state, unit)}"
                    )
        self.query_one("#side", Static).update("\n".join(lines))

    def _submit(self, action: Action) -> None:
        if self.session is None or self.bot_busy or not self.session.human_turn:
            return
        try:
            self.session.submit_human_action(action)
        except (RuntimeError, ValueError) as exc:
            self.query_one("#notice", Static).update(f"[bold red]{escape(str(exc))}[/bold red]")
            return
        self.selected_card = None
        self.target_index = 0
        self.refresh_game()
        self.maybe_start_bot()

    @on(BoardWidget.TargetClicked)
    def board_target_clicked(self, event: BoardWidget.TargetClicked) -> None:
        action = self.target_map.get(event.target)
        if action is not None:
            self._submit(action)

    @on(BoardWidget.TargetHovered)
    def board_target_hovered(self, event: BoardWidget.TargetHovered) -> None:
        self.hovered_target = event.target
        if self.session is None:
            return
        focused = self.target_order[self.target_index] if self.target_order else None
        self._update_side(focused)

    @on(CardShelf.EntryClicked)
    def action_entry_clicked(self, event: CardShelf.EntryClicked) -> None:
        payload = event.payload
        if isinstance(payload, tuple) and payload and payload[0] == "card":
            self.selected_card = payload[1]
            self.target_index = 0
            self.refresh_game()
        elif isinstance(payload, (DrawAction, PlaceAction, ChoiceAction)):
            self._submit(payload)

    def on_key(self, event: Key) -> None:
        if not event.character or not event.character.isdigit() or event.character == "0":
            return
        index = int(event.character) - 1
        if 0 <= index < len(self.entry_shortcuts):
            payload = self.entry_shortcuts[index]
            if isinstance(payload, tuple) and payload[0] == "card":
                self.selected_card = payload[1]
                self.target_index = 0
                self.refresh_game()
            elif isinstance(payload, (PlaceAction, ChoiceAction)):
                self._submit(payload)
            event.stop()

    def action_draw(self) -> None:
        if self.session is None:
            return
        draw = next(
            (action for action in self.session.legal_actions if isinstance(action, DrawAction)),
            None,
        )
        if draw is not None:
            self._submit(draw)

    def action_cancel_selection(self) -> None:
        self.selected_card = None
        self.target_index = 0
        self.refresh_game()

    def action_previous_target(self) -> None:
        if self.target_order:
            self.target_index = (self.target_index - 1) % len(self.target_order)
            self.refresh_game()

    def action_next_target(self) -> None:
        if self.target_order:
            self.target_index = (self.target_index + 1) % len(self.target_order)
            self.refresh_game()

    def action_confirm_target(self) -> None:
        if self.session is None:
            return
        if self.session.result is not None:
            if self.manifest is not None:
                self.start_next_scheduled_game()
            else:
                self.session.close(reason="next_game")
                self.session = None
                self.push_screen(
                    SetupScreen(
                        config=self.ad_hoc_config,
                        map_id=self.ad_hoc_map,
                        player_id=self.player_id,
                    ),
                    self.start_game,
                )
            return
        if self.target_order:
            self._submit(self.target_map[self.target_order[self.target_index]])

    def action_mark_decision(self) -> None:
        if self.session is None:
            return
        valid = self.session.toggle_latest_human_decision()
        message = (
            "No human decision to mark." if valid is None
            else "Latest human decision restored." if valid
            else "Latest human decision excluded."
        )
        self.query_one("#notice", Static).update(message)

    def action_mark_game(self) -> None:
        if self.session is None:
            return
        valid = self.session.toggle_game_validity()
        self.refresh_game()
        self.query_one("#notice", Static).update(
            "Game restored." if valid else "Game excluded; its scheduled entry will be replayed."
        )

    def action_open_recording(self) -> None:
        if self.session is None or self.session.result is None:
            return
        self.open_url(self.session.path.resolve().as_uri())

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def maybe_start_bot(self) -> None:
        if (
            self.session is None
            or self.session.result is not None
            or self.session.human_turn
            or self.bot_busy
        ):
            return
        self.bot_busy = True
        self.refresh_game()
        self.run_bot(self.session)

    @work(thread=True, exclusive=True, group="bot")
    def run_bot(self, session: RecorderSession) -> None:
        try:
            action, elapsed = session.choose_bot_action()
        except Exception as exc:
            try:
                self.call_from_thread(self._bot_failed, session, exc)
            except RuntimeError:
                pass  # the app was closed while this CPU-bound worker was finishing
            return
        try:
            self.call_from_thread(self._apply_bot_action, session, action, elapsed)
        except RuntimeError:
            pass  # the app was closed while this CPU-bound worker was finishing

    def _apply_bot_action(self, session: RecorderSession, action: Action, elapsed_ms: float) -> None:
        if session is not self.session:
            return
        try:
            session.submit_bot_action(action, elapsed_ms)
        except Exception as exc:
            self._bot_failed(session, exc)
            return
        self.bot_busy = False
        self.refresh_game()
        self.maybe_start_bot()

    def _bot_failed(self, session: RecorderSession, exc: Exception) -> None:
        if session is not self.session:
            return
        self.bot_busy = False
        self.query_one("#notice", Static).update(
            f"[bold red]Bot failed: {escape(str(exc))}[/bold red]"
        )

    def action_quit_recorder(self) -> None:
        if self.session is not None:
            self.session.close(reason="quit")
            self.session = None
        self.exit()

    def on_unmount(self) -> None:
        if self.session is not None:
            self.session.close(reason="app_unmounted")
            self.session = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Record human-vs-bot benchmark games.")
    parser.add_argument("--schedule", type=Path)
    parser.add_argument("--player-id", default="human-1")
    parser.add_argument("--out", type=Path, default=Path("results/human_games"))
    parser.add_argument("--map", dest="map_id", default="map_b")
    parser.add_argument(
        "--config",
        default="none",
        help="Ad-hoc config override JSON; use 'none' for defaults.",
    )
    return parser


def _warn_config_drift(manifest: CohortManifest) -> None:
    """Loudly flag (and gate on) a schedule whose pinned rules no longer match the code.

    Textual takes over the screen, so an in-app toast would flash past; instead we print to
    stderr before the app mounts and, on a TTY, require an explicit keypress so the operator
    can't unknowingly record a session with stale balance constants (the flying_squirrel 8-vs-10
    incident, 2026-07-10). Aborting here lets them regenerate the schedule first."""
    drift = config_drift(manifest.config)
    if not drift:
        return
    lines = "\n".join(
        f"    - {name}: schedule pins {pinned!r}, code default is {current!r}"
        for name, pinned, current in drift
    )
    sys.stderr.write(
        f"\n⚠️  SCHEDULE CONFIG DRIFT — {manifest.cohort_id}\n"
        f"  This schedule's pinned rules differ from the current code in {len(drift)} value(s):\n"
        f"{lines}\n"
        "  Games recorded from it use the PINNED (stale) values, not your latest code.\n"
        "  Regenerate the schedule (or resync its config block) to record with current rules.\n\n"
    )
    if sys.stdin.isatty():
        try:
            input("  Press Enter to record with the pinned rules anyway, or Ctrl-C to abort... ")
        except (EOFError, KeyboardInterrupt):
            sys.stderr.write("\nAborted.\n")
            raise SystemExit(1)


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    manifest = load_manifest(args.schedule) if args.schedule else None
    if manifest is not None:
        _warn_config_drift(manifest)
    config = load_config_overrides(args.config) or Config.default()
    RecorderApp(
        manifest=manifest,
        output_root=args.out,
        player_id=args.player_id,
        ad_hoc_config=config,
        ad_hoc_map=args.map_id,
    ).run()
