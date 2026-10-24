"""Archetypes for the Meta tab (Martin, 2026-10-24): lists grouped by the cards they share, then variants within each group.

Two lists' overlap is the share of their 30 cards they have in common, copies counted. Groups form by average linkage:
the two closest groups merge while the average overlap between their lists is at least ARCHETYPE; inside an archetype
the same rule at VARIANT gives its variants. A list is a player's exact 30 cards and never changes, so a list's
archetype is a label over its games: regrouping never touches a game, only how the games are summed.
"""

from __future__ import annotations

import collections
from typing import Sequence

ARCHETYPE = 0.6
VARIANT = 0.85


def overlap(a: collections.Counter, b: collections.Counter) -> float:
    return sum((a & b).values()) / max(1, min(sum(a.values()), sum(b.values())))


def groups(lists: dict[str, Sequence[str]], threshold: float) -> list[list[str]]:
    """Average-linkage groups of the lists' slugs, biggest first; each group's slugs in their given order."""
    cs = {s: collections.Counter(l) for s, l in lists.items()}
    order = {s: i for i, s in enumerate(lists)}
    sim = {(a, b): overlap(cs[a], cs[b]) for a in cs for b in cs if a < b}
    pair = lambda a, b: sim[(a, b) if a < b else (b, a)]
    out = [[s] for s in lists]
    while True:
        best, bi, bj = threshold, -1, -1
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                avg = sum(pair(a, b) for a in out[i] for b in out[j]) / (len(out[i]) * len(out[j]))
                if avg >= best:
                    best, bi, bj = avg, i, j
        if bi < 0:
            break
        out[bi] = sorted(out[bi] + out.pop(bj), key=order.get)
    return sorted(out, key=lambda g: (-len(g), order[g[0]]))


def medoid(group: Sequence[str], lists: dict[str, Sequence[str]]) -> str:
    """The list closest on average to the rest of its group: the one that stands for it."""
    cs = {s: collections.Counter(lists[s]) for s in group}
    return max(group, key=lambda s: sum(overlap(cs[s], cs[t]) for t in group if t != s))


def archetypes(lists: dict[str, Sequence[str]]) -> list[dict]:
    """[{"lists": [...], "medoid": slug, "variants": [[...], ...]}], biggest archetype first."""
    out = []
    for g in groups(lists, ARCHETYPE):
        sub = {s: lists[s] for s in g}
        out.append({"lists": g, "medoid": medoid(g, lists), "variants": groups(sub, VARIANT)})
    return out
