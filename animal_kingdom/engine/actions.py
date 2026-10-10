"""Action types - the single interface a player (bot or future human) uses to act.

A turn is exactly one action (overview.md §5): either draw or place one unit. Actions
are immutable, value-equal, hashable (so legal_actions can dedupe), and JSON-serializable
(same representation for sim logs, replays, and a future API payload).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional, Union


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
    # Which copy in hand, when copies of the card differ in strength (a buffed one beside a plain one): the iid of the
    # first copy of that strength in hand. None when every playable copy is alike, which is nearly always.
    iid: Optional[int] = None
    kind: ClassVar[str] = "place"  # a tag, not part of value identity

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "card_id": self.card_id, "target": list(self.target)}
        if self.iid is not None:
            d["iid"] = self.iid
        return d

    @property
    def is_hq_capture(self) -> bool:
        return self.target[0] == "hq"

    @property
    def crossroad(self) -> str:
        """The destination crossroad (only valid when not an HQ capture)."""
        return self.target[1]


@dataclass(frozen=True)
class RoamAction:
    """Roam (keywords.md): move the animal on top of `origin` to an adjacent crossroad, or onto the enemy
    den next to it. Costs one of the turn's actions, unless the player holds a free roam.

    `target` has PlaceAction's shape: ("cr", "<crossroad>") or ("hq", "<player>") for a den capture.
    """

    origin: str
    target: tuple[str, str]
    kind: ClassVar[str] = "roam"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "from": self.origin, "target": list(self.target)}

    @property
    def is_hq_capture(self) -> bool:
        return self.target[0] == "hq"

    @property
    def crossroad(self) -> str:
        """The destination crossroad (only valid when not an HQ capture)."""
        return self.target[1]


@dataclass(frozen=True)
class PassAction:
    """End the turn early, declining the remaining actions (overview.md §5). Legal only after the
    turn's first action and outside effect resolution; never offered by legal_actions (see rules.can_pass)."""

    kind: ClassVar[str] = "pass"

    def to_dict(self) -> dict:
        return {"kind": self.kind}


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

Action = Union[DrawAction, PlaceAction, RoamAction, PassAction, ChoiceAction]


def action_from_dict(d: dict) -> Action:
    kind = d["kind"]
    if kind == "draw":
        return DrawAction()
    if kind == "place":
        return PlaceAction(card_id=d["card_id"], target=tuple(d["target"]), iid=d.get("iid"))
    if kind == "roam":
        return RoamAction(origin=d["from"], target=tuple(d["target"]))
    if kind == "choice":
        return ChoiceAction(choice=d["choice"])
    if kind == "pass":
        return PassAction()
    raise ValueError(f"unknown action kind {kind!r}")
