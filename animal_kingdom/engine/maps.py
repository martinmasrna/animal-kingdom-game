"""Map registry: load board data from data/maps.json, validate it, and expose
graph/region helpers used by the rules (connection, adjacency, region control).

A GameMap is immutable board geometry; per-game occupancy lives in GameState (later
milestones). Helpers here answer purely-geometric questions:
  - neighbors(cr)        : crossroads one edge away from cr
  - adjacent(a, b)       : are a and b connected by a single edge?
  - hq_front(player)     : the crossroads an HQ connects to (its "front")
Region geometry is read directly off `regions[rid]` (corners, food).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .resources import load_bundled_json


class MapDataError(ValueError):
    """Raised when map data fails validation."""


@dataclass(frozen=True)
class Region:
    id: str
    corners: tuple[str, ...]
    food: int


@dataclass(frozen=True)
class GameMap:
    id: str
    name: str
    crossroads: frozenset[str]
    # Undirected adjacency among crossroads: cr -> frozenset(neighbor crs).
    _adjacency: dict[str, frozenset[str]]
    # player ("A"/"B") -> frozenset of front crossroads the HQ connects to.
    hq_connects: dict[str, frozenset[str]]
    regions: dict[str, Region]
    win_food: int
    edges: tuple[tuple[str, str], ...] = field(default=())

    # --- geometric helpers ---
    def neighbors(self, crossroad: str) -> frozenset[str]:
        """Crossroads one edge away from `crossroad`."""
        return self._adjacency.get(crossroad, frozenset())

    def adjacent(self, a: str, b: str) -> bool:
        """True if `a` and `b` are connected by a single edge (overview.md §3.3)."""
        return b in self._adjacency.get(a, frozenset())

    def hq_front(self, player: str) -> frozenset[str]:
        """The crossroads in front of `player`'s HQ (its defended approaches)."""
        return self.hq_connects[player]

    @property
    def players(self) -> tuple[str, ...]:
        return tuple(sorted(self.hq_connects))


REQUIRED_MAP_FIELDS = ("id", "name", "crossroads", "edges", "hqs", "regions", "win_food")


def validate_map_record(rec: dict) -> None:
    """Check that a raw map record is well-formed; raise MapDataError on the first problem.

    Kept separate from construction (the "parse, don't validate" split): this is the
    trust boundary, so the rules engine can treat any constructed GameMap as provably
    valid and stay free of defensive checks. Directly unit-testable on its own.
    """
    for key in REQUIRED_MAP_FIELDS:
        if key not in rec:
            raise MapDataError(f"map {rec.get('id', rec)!r} missing required field {key!r}")

    mid = rec["id"]
    crossroad_set = set(rec["crossroads"])
    if len(crossroad_set) != len(rec["crossroads"]):
        raise MapDataError(f"map {mid!r}: duplicate crossroads")

    for edge in rec["edges"]:
        if len(edge) != 2:
            raise MapDataError(f"map {mid!r}: edge {edge!r} must have exactly 2 endpoints")
        a, b = edge
        if a not in crossroad_set or b not in crossroad_set:
            raise MapDataError(f"map {mid!r}: edge {edge!r} references unknown crossroad")
        if a == b:
            raise MapDataError(f"map {mid!r}: self-loop edge {edge!r}")

    for player, hq in rec["hqs"].items():
        connects = hq.get("connects", [])
        if not connects:
            raise MapDataError(f"map {mid!r}: HQ {player!r} has no front crossroads")
        for cr in connects:
            if cr not in crossroad_set:
                raise MapDataError(f"map {mid!r}: HQ {player!r} connects to unknown crossroad {cr!r}")

    for rid, region in rec["regions"].items():
        for cr in region["corners"]:
            if cr not in crossroad_set:
                raise MapDataError(f"map {mid!r}: region {rid!r} corner {cr!r} is not a crossroad")
        food = region["food"]
        if not isinstance(food, int) or food < 0:
            raise MapDataError(f"map {mid!r}: region {rid!r} has bad food {food!r}")

    win_food = rec["win_food"]
    if not isinstance(win_food, int) or win_food <= 0:
        raise MapDataError(f"map {mid!r}: win_food must be a positive int, got {win_food!r}")


def _build_map(rec: dict) -> GameMap:
    """Construct a GameMap from a record assumed valid (run validate_map_record first)."""
    adjacency: dict[str, set[str]] = {cr: set() for cr in rec["crossroads"]}
    edges: list[tuple[str, str]] = []
    for a, b in rec["edges"]:
        adjacency[a].add(b)
        adjacency[b].add(a)  # undirected: symmetric by construction
        edges.append((a, b))

    return GameMap(
        id=rec["id"],
        name=rec["name"],
        crossroads=frozenset(rec["crossroads"]),
        _adjacency={cr: frozenset(ns) for cr, ns in adjacency.items()},
        hq_connects={player: frozenset(hq["connects"]) for player, hq in rec["hqs"].items()},
        regions={
            rid: Region(id=rid, corners=tuple(r["corners"]), food=r["food"])
            for rid, r in rec["regions"].items()
        },
        win_food=rec["win_food"],
        edges=tuple(edges),
    )


def load_maps(raw: Optional[dict] = None, *, validate: bool = True) -> dict[str, GameMap]:
    """Return a dict id -> GameMap. Loads bundled data/maps.json by default.

    `validate` defaults to True (the loader is the trust boundary). Pass validate=False
    only for data already known to be well-formed; it skips the checks, not construction.
    """
    if raw is None:
        raw = load_bundled_json("maps.json")

    records = raw.get("maps")
    if not isinstance(records, list) or not records:
        raise MapDataError("maps.json must contain a non-empty 'maps' list")

    registry: dict[str, GameMap] = {}
    for rec in records:
        if validate:
            validate_map_record(rec)
        game_map = _build_map(rec)
        if game_map.id in registry:
            raise MapDataError(f"duplicate map id {game_map.id!r}")
        registry[game_map.id] = game_map
    return registry


def load_map(map_id: str) -> GameMap:
    """Convenience: load a single bundled map by id."""
    maps = load_maps()
    if map_id not in maps:
        raise MapDataError(f"no such map {map_id!r}; available: {sorted(maps)}")
    return maps[map_id]
