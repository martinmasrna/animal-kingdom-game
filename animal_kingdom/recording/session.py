"""Authoritative human-vs-bot session with decision-level durable recording."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..bots.base import Bot
from ..decks import load_premade_deck
from ..engine import rules
from ..engine import strength as strength_mod
from ..engine.actions import SKIP, Action, ChoiceAction, DrawAction, PlaceAction
from ..engine.config import Config
from ..engine.state import GameState, Result, new_game, other_player
from ..sim.runner import BOT_KINDS, make_bot
from .provenance import build_game_provenance
from .writer import JsonlGameWriter


@dataclass(frozen=True)
class GameSetup:
    human_deck: str
    opponent_deck: str
    human_seat: str = "A"
    opponent_kind: str = "greedy"
    seed: int = 0
    map_id: str = "map_b"
    config: Config = Config()
    player_id: str = "human-1"
    cohort_id: str = "ad-hoc"
    scheduled_game_id: Optional[str] = None

    def validate(self) -> None:
        load_premade_deck(self.human_deck)
        load_premade_deck(self.opponent_deck)
        if self.human_seat not in ("A", "B"):
            raise ValueError(f"human_seat must be A or B, got {self.human_seat!r}")
        if self.opponent_kind not in BOT_KINDS:
            raise ValueError(f"unknown bot kind {self.opponent_kind!r}")
        if not self.player_id:
            raise ValueError("player_id must not be empty")


def describe_action(state: GameState, action: Action) -> str:
    if isinstance(action, DrawAction):
        return "drew cards"
    if isinstance(action, PlaceAction):
        name = state.cards[action.card_id].name
        if action.is_hq_capture:
            return f"played {name} and captured HQ {action.target[1]}"
        return f"played {name} on {action.crossroad}"
    if isinstance(action, ChoiceAction):
        return "declined an optional effect" if action.choice == SKIP else f"chose {action.choice}"
    return repr(action)


def visible_state_to_dict(state: GameState, player: str) -> dict:
    """Training-ready information set with public unit and own-hand instance details."""
    view = state.view_for(player).to_dict()
    view["board_units"] = {
        cr: [
            {
                **unit.to_dict(),
                "effective_strength": strength_mod.effective_strength(state, unit),
            }
            for unit in stack
        ]
        for cr, stack in state.board.items()
    }
    view["own_hand_units"] = [
        {
            **unit.to_dict(),
            "placement_strength": strength_mod.placement_strength(state, unit),
        }
        for unit in state.hands[player]
    ]
    return view


def default_recording_path(root: Path, setup: GameSetup) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    attempt = uuid.uuid4().hex[:8]
    safe_cohort = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in setup.cohort_id)
    game = setup.scheduled_game_id or "ad-hoc"
    return Path(root) / safe_cohort / f"{game}_{stamp}_{attempt}.jsonl"


class RecorderSession:
    """Game orchestration shared by the Textual UI and headless tests."""

    schema_version = 1

    def __init__(
        self,
        setup: GameSetup,
        *,
        output_root: Path | str = Path("results/human_games"),
        writer: Optional[JsonlGameWriter] = None,
        state: Optional[GameState] = None,
        bot: Optional[Bot] = None,
    ):
        setup.validate()
        self.setup = setup
        deck_human = load_premade_deck(setup.human_deck)
        deck_opponent = load_premade_deck(setup.opponent_deck)
        deck_a, deck_b = (
            (deck_human, deck_opponent)
            if setup.human_seat == "A"
            else (deck_opponent, deck_human)
        )
        self.state = state or new_game(
            deck_a,
            deck_b,
            setup.seed,
            map_id=setup.map_id,
            config=setup.config,
        )
        opponent_seat = other_player(setup.human_seat)
        bot_seed = setup.seed * 2 + (1 if opponent_seat == "A" else 2)
        self.bot = bot or make_bot(setup.opponent_kind, bot_seed)
        self.controllers = {
            setup.human_seat: "human",
            opponent_seat: setup.opponent_kind,
        }
        self.path = (
            writer.path
            if writer is not None
            else default_recording_path(Path(output_root), setup)
        )
        self.writer = writer or JsonlGameWriter(self.path)
        self.recent: list[str] = []
        self.decision_count = 0
        self.human_decisions: list[int] = []
        self.decision_validity: dict[int, bool] = {}
        self.game_valid = True
        self._closed = False
        self._result_written = False
        self._decision_started = time.monotonic()
        self._write_meta()
        self._finish_if_terminal()

    @property
    def human_turn(self) -> bool:
        return (
            self.result is None
            and self.state.player_to_act() == self.setup.human_seat
        )

    @property
    def result(self) -> Optional[Result]:
        return rules.is_terminal(self.state)

    @property
    def legal_actions(self) -> tuple[Action, ...]:
        return tuple(rules.legal_actions(self.state))

    def _write_meta(self) -> None:
        self.writer.append({
            "type": "meta",
            "schema_version": self.schema_version,
            "game_id": uuid.uuid4().hex,
            "scheduled_game_id": self.setup.scheduled_game_id,
            "cohort_id": self.setup.cohort_id,
            "player_id": self.setup.player_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seed": self.setup.seed,
            "map_id": self.setup.map_id,
            "human_seat": self.setup.human_seat,
            "decks": {
                self.setup.human_seat: self.setup.human_deck,
                other_player(self.setup.human_seat): self.setup.opponent_deck,
            },
            "controllers": dict(self.controllers),
            "initial_state": self.state.to_dict(),
            "provenance": build_game_provenance(
                self.bot, self.setup.opponent_kind, self.setup.config
            ),
        })

    def choose_bot_action(self) -> tuple[Action, float]:
        """Compute the current bot action; safe to call from a worker thread."""
        if self.result is not None or self.human_turn:
            raise RuntimeError("it is not the bot's turn")
        actor = self.state.player_to_act()
        legal = self.legal_actions
        start = time.monotonic()
        action = self.bot.choose(self.state.view_for(actor), legal, self.state)
        return action, (time.monotonic() - start) * 1000.0

    def submit_human_action(self, action: Action) -> None:
        if not self.human_turn:
            raise RuntimeError("it is not the human's turn")
        elapsed = (time.monotonic() - self._decision_started) * 1000.0
        self.submit_action(action, elapsed_ms=elapsed)

    def submit_bot_action(self, action: Action, elapsed_ms: float) -> None:
        if self.human_turn:
            raise RuntimeError("it is not the bot's turn")
        self.submit_action(action, elapsed_ms=elapsed_ms)

    def submit_action(self, action: Action, *, elapsed_ms: float) -> None:
        if self.result is not None:
            raise RuntimeError("cannot act after game over")
        actor = self.state.player_to_act()
        legal = self.legal_actions
        if action not in legal:
            raise ValueError(f"stale or illegal action {action!r}")

        before = self.state
        after = before.clone()
        narration = describe_action(before, action)
        rules.apply_action(after, action)
        result = rules.is_terminal(after)
        decision_id = self.decision_count
        controller = self.controllers[actor]
        record = {
            "type": "decision",
            "schema_version": self.schema_version,
            "decision_id": decision_id,
            "turn": before.turn_counter,
            "actor": actor,
            "controller": controller,
            "human": controller == "human",
            "elapsed_ms": round(float(elapsed_ms), 3),
            "state": before.to_dict(),
            "view": visible_state_to_dict(before, actor),
            "legal_actions": [candidate.to_dict() for candidate in legal],
            "action": action.to_dict(),
            "narration": narration,
        }
        # Durability is the commit point: the live UI advances only after this succeeds.
        self.writer.append(record)
        self.state = after
        self.decision_count += 1
        self.decision_validity[decision_id] = True
        if controller == "human":
            self.human_decisions.append(decision_id)
        self.recent.append(f"{actor}: {narration}")
        del self.recent[:-6]
        self._decision_started = time.monotonic()
        if result is not None:
            self._write_result(result)

    def toggle_latest_human_decision(self) -> Optional[bool]:
        if not self.human_decisions:
            return None
        decision_id = self.human_decisions[-1]
        valid = not self.decision_validity[decision_id]
        self.decision_validity[decision_id] = valid
        self.writer.append({
            "type": "annotation",
            "annotation": "decision_validity",
            "decision_id": decision_id,
            "valid": valid,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return valid

    def toggle_game_validity(self) -> bool:
        self.game_valid = not self.game_valid
        self.writer.append({
            "type": "annotation",
            "annotation": "game_validity",
            "valid": self.game_valid,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return self.game_valid

    def _finish_if_terminal(self) -> None:
        result = rules.is_terminal(self.state)
        if result is not None:
            self._write_result(result)

    def _write_result(self, result: Result) -> None:
        if self._result_written:
            return
        self.writer.append({
            "type": "result",
            "winner": result.winner,
            "reason": result.reason,
            "turns": self.state.turn_counter,
            "final_state": self.state.to_dict(),
            "game_valid": self.game_valid,
            "invalid_decisions": sorted(
                decision_id
                for decision_id, valid in self.decision_validity.items()
                if not valid
            ),
        })
        self._result_written = True

    def close(self, *, reason: str = "quit") -> None:
        if self._closed:
            return
        if not self._result_written:
            self.writer.append({
                "type": "abort",
                "reason": reason,
                "turn": self.state.turn_counter,
                "decision_count": self.decision_count,
            })
        self.writer.close()
        self._closed = True
