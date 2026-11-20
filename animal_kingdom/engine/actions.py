"""Action types: the one interface a player (bot or person) acts through. Immutable, value-equal, hashable (legal_actions
dedupes them) and JSON-serializable (the same shape in game logs, replays and the web API)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Union


@dataclass(frozen=True)
class PlaceAction:
    """Play an animal from hand. `target` is ("cr", "<tile>") or ("hq", "<player>"): a raid on that player's den."""

    card_id: str
    target: tuple[str, str]
    kind: ClassVar[str] = "place"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "card_id": self.card_id, "target": list(self.target)}


@dataclass(frozen=True)
class LeaderAction:
    """Use your leader's power (engine/leaders.py); it costs Config.leader_power_cost mana."""

    kind: ClassVar[str] = "leader"

    def to_dict(self) -> dict:
        return {"kind": self.kind}


@dataclass(frozen=True)
class PassAction:
    """End the turn. Legal whenever nothing is resolving (rules.can_pass); offered by legal_actions only when nothing else
    is."""

    kind: ClassVar[str] = "pass"

    def to_dict(self) -> dict:
        return {"kind": self.kind}


@dataclass(frozen=True)
class ChoiceAction:
    """A sub-decision while an effect resolves: a tile, a unit iid, or SKIP to decline an optional one."""

    choice: object
    kind: ClassVar[str] = "choice"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "choice": self.choice}


SKIP = "__skip__"

Action = Union[PlaceAction, LeaderAction, PassAction, ChoiceAction]


def action_from_dict(d: dict) -> Action:
    kind = d["kind"]
    if kind == "place":
        return PlaceAction(card_id=d["card_id"], target=tuple(d["target"]))
    if kind == "leader":
        return LeaderAction()
    if kind == "choice":
        return ChoiceAction(choice=d["choice"])
    if kind == "pass":
        return PassAction()
    raise ValueError(f"unknown action kind {kind!r}")
