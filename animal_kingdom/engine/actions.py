"""Action types - the single interface a player (bot or future human) uses to act.

A turn is exactly one action (overview.md §5): either draw or place one unit. Actions
are immutable, value-equal, hashable (so legal_actions can dedupe), and JSON-serializable
(same representation for sim logs, replays, and a future API payload).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Union


@dataclass(frozen=True)
class DrawAction:
    """Draw cards (count/limits resolved by the rules, per config)."""

    kind: ClassVar[str] = "draw"  # a tag, not part of value identity

    def to_dict(self) -> dict:
        return {"kind": self.kind}


@dataclass(frozen=True)
class PlaceAction:
    """Place one unit from hand onto a target.

    `target` is one of:
      ("cr", "<crossroad>")  - place on a crossroad (empty / own / covering an enemy)
      ("hq", "<player>")     - place onto an enemy HQ (captures it)
    """

    card_id: str
    target: tuple[str, str]
    kind: ClassVar[str] = "place"  # a tag, not part of value identity

    def to_dict(self) -> dict:
        return {"kind": self.kind, "card_id": self.card_id, "target": list(self.target)}

    @property
    def is_hq_capture(self) -> bool:
        return self.target[0] == "hq"

    @property
    def crossroad(self) -> str:
        """The destination crossroad (only valid when not an HQ capture)."""
        return self.target[1]


@dataclass(frozen=True)
class ChoiceAction:
    """A sub-decision during effect resolution (which target/card/option to pick).

    `choice` is a JSON-serializable, hashable value: a crossroad string, a unit iid,
    a card id, a yes/no option, or the literal SKIP for declining an optional effect.
    Surfaced by legal_actions only while `state.pending` is set.
    """

    choice: object
    kind: ClassVar[str] = "choice"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "choice": self.choice}


SKIP = "__skip__"  # the ChoiceAction value that declines an optional effect

Action = Union[DrawAction, PlaceAction, ChoiceAction]


def action_from_dict(d: dict) -> Action:
    kind = d["kind"]
    if kind == "draw":
        return DrawAction()
    if kind == "place":
        return PlaceAction(card_id=d["card_id"], target=tuple(d["target"]))
    if kind == "choice":
        return ChoiceAction(choice=d["choice"])
    raise ValueError(f"unknown action kind {kind!r}")
