"""A game's card facts for the Meta tab (Martin, 2026-10-24): replayed from its action log, no bot compute.

Per seat: every card the mulligan showed (`seen`: the hand as dealt, then each replacement, which may itself go back), the
cards sent back (`back`), and every card that reached
the hand as [card, drawn, played]: `drawn` is the player's own turn it first came to hand (0 for the hand the game
started with, after the mulligan), `played` the own turn it was first placed from hand, or None. Copies are separate
entries. These are what the mulligan, drawn and played win rates are counted from; a replay stops working once a card
it used changes, so the runner keeps the facts at the end of every game rather than rebuilding them later.
"""

from __future__ import annotations

from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import SKIP, ChoiceAction
from ..engine.config import Config
from ..engine.state import new_game


def game_facts(list_a: Sequence[str], list_b: Sequence[str], seed: int, first_player: str, actions: Sequence[dict],
               config: Optional[Config] = None, map_id: str = "map_b") -> dict:
    state = new_game(list(list_a), list(list_b), seed, map_id=map_id, config=config or Config.default(),
                     first_player=first_player)
    out = {s: {"seen": [u.card_id for u in state.hands[s]], "back": [], "cards": []} for s in ("A", "B")}
    entry: dict[int, list] = {}            # iid -> its [card, drawn, played] in out[seat]["cards"]
    turn = {"A": 0, "B": 0}                # each player's own turns so far

    def hands() -> None:                   # a card new to a hand was drawn (or fetched) on its owner's current turn
        for s in ("A", "B"):
            for u in state.hands[s]:
                if u.iid not in entry:
                    entry[u.iid] = [u.card_id, turn[s], None]
                    out[s]["cards"].append(entry[u.iid])

    hands()
    state.events.clear()
    for adict in actions:
        while state.pending is not None and state.effect_stack and state.effect_stack[-1].get("op") == "mulligan" \
                and adict["kind"] != "choice":
            rules.apply_action(state, ChoiceAction(SKIP))
        rules.apply_logged(state, adict)
        for e in state.events:
            p = e.get("player")
            if e["e"] == "mulligan":       # a returned card leaves the starting hand; its replacement is part of it
                back = entry.pop(e["returned"])
                out[p]["back"].append(back[0]); out[p]["cards"].remove(back)
                entry[e["drawn"][0]] = [e["drawn"][1], 0, None]; out[p]["cards"].append(entry[e["drawn"][0]])
                out[p]["seen"].append(e["drawn"][1])
            elif e["e"] == "turn_start":
                hands(); turn[p] += 1      # whatever came to hand before this turn began belongs to the turn before
            elif e["e"] == "place" and e.get("from_hand") and e["iid"] in entry and entry[e["iid"]][2] is None:
                entry[e["iid"]][2] = turn[p]
        state.events.clear()
        hands()
    return out
