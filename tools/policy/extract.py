"""Decisions out of game logs, as the candidate network sees them: for every decision of the chosen seats, the position
(the board_live feature vector) and every legal action as a feature vector, with the index of the action taken.

Usage: extract.py OUT.npz {expert|human} LOG.jsonl [LOG.jsonl ...]
  expert: both seats' decisions; human: the human seat's only (logs whose `bots` name a human).
A game that stops replaying on today's cards contributes the decisions before the break. The mulligan is skipped.
"""
import json, sys
import numpy as np
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import action_from_dict
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game, other_player
from animal_kingdom.engine.strength import effective_strength, placement_strength
from animal_kingdom.bots import features as F

KINDS = ("place", "roam", "draw", "choice_cr", "choice_opt", "choice_skip")
CARD_N, SLOT_N, OPT_N = len(F.HAND_FEATURES), len(F.SLOT_FEATURES), 8


def slot_vec(state, me, cr):
    """The board slot's features for crossroad `cr` from `me`'s side (as board_features builds them)."""
    stack = state.board.get(cr)
    if not stack:
        return [0.0] * SLOT_N
    opp = other_player(me)
    top = stack[-1]
    sign = 1.0 if top.owner == me else -1.0 if top.owner == opp else 0.0
    out = [float(top.owner == me), float(top.owner == opp), sign * effective_strength(state, top) / 10.0,
           len(stack) / 4.0, sum(u.owner == me for u in stack[:-1]) / 3.0, sum(u.owner == opp for u in stack[:-1]) / 3.0,
           sign * float(top.placed_on_turn == state.turn_counter)]
    out.extend(F._properties(state.cards[top.card_id], sign, on_board_live=True))
    return out


def card_vec(state, u):
    card = state.cards[u.card_id]
    return [1.0, placement_strength(state, u) / 10.0, card.food_cost / 5.0] + F._properties(card, 1.0)


def action_vec(state, me, a, legal_index, crs):
    opp = other_player(me)
    gm = state.game_map
    kind = [0.0] * len(KINDS)
    card = [0.0] * CARD_N
    slot = [0.0] * SLOT_N
    where = [0.0] * F.BOARD_SLOTS
    extra = [0.0] * 8
    opt = [0.0] * OPT_N
    target = None
    strength = None
    if a.kind == "place":
        kind[0] = 1.0
        u = next(x for x in state.hands[me] if x.iid == a.iid) if getattr(a, "iid", None) else \
            next(x for x in state.hands[me] if x.card_id == a.card_id)
        card = card_vec(state, u)
        strength = placement_strength(state, u)
        target = a.target[1] if a.target[0] == "cr" else None
    elif a.kind == "roam":
        kind[1] = 1.0
        u = state.board[a.origin][-1]
        card = card_vec(state, u)
        strength = effective_strength(state, u)
        if a.target[0] == "cr":
            target = a.target[1]
        else:
            extra[7] = 1.0                                   # into the enemy den
    elif a.kind == "draw":
        kind[2] = 1.0
    else:
        c = a.choice
        if c == "__skip__":
            kind[5] = 1.0
        elif isinstance(c, str) and c in gm.crossroads:
            kind[3] = 1.0
            target = c
        else:
            kind[4] = 1.0
            opt[min(legal_index, OPT_N - 1)] = 1.0
    if target is not None:
        slot = slot_vec(state, me, target)
        where[crs.index(target)] = 1.0
        stack = state.board.get(target)
        top = stack[-1] if stack else None
        extra[0] = float(top is not None and top.owner == opp)
        if top is not None and strength is not None:
            extra[1] = (strength - effective_strength(state, top)) / 10.0
        extra[2] = float(top is None)
        extra[3] = float(target in gm.hq_connects[me])
        extra[4] = float(target in gm.hq_connects[opp])
        nb = [state.board.get(n) for n in gm.neighbors(target)]
        extra[5] = sum(1 for s in nb if s and s[-1].owner == opp) / 4.0
        extra[6] = sum(1 for s in nb if s and s[-1].owner == me) / 4.0
    return kind + card + slot + where + extra + opt


def same(a, b):
    da, db = a.to_dict(), b.to_dict()
    return all(da.get(k) == db.get(k) for k in set(da) | set(db) if k != "by")


def lists_of(g):
    if g.get("lists"):
        return list(g["lists"][0]), list(g["lists"][1])
    from animal_kingdom.decks import load_premade_deck            # a benchmark log names its decks (AK_EXTRA_DECKS set)
    return load_premade_deck(g["deck_a"]), load_premade_deck(g["deck_b"])


def decisions(g, seats):
    try:
        a_list, b_list = lists_of(g)
        st = new_game(a_list, b_list, g["seed"], map_id=g.get("map_id", "map_b"),
                      config=Config.default().for_log(g), first_player=g["first_player"])
    except Exception:                                              # a deck or card the game no longer has
        return
    crs = sorted(st.game_map.crossroads)
    for a in g["actions"]:
        if rules.is_terminal(st) is not None:
            break
        me = st.player_to_act()
        act = action_from_dict(a)
        try:
            row = None
            if me in seats and not (st.pending and st.pending.get("kind") == "mulligan"):
                legal = rules.legal_actions(st)
                if len(legal) >= 2:
                    chosen = next((i for i, x in enumerate(legal) if same(x, act)), None)
                    if chosen is not None:
                        row = (F.extract(st, me, "board_live"), [action_vec(st, me, x, i, crs) for i, x in enumerate(legal)],
                               chosen, st.turn_counter, me)
            if row is not None:
                yield row
            rules.apply_logged(st, a)
        except Exception:                                          # a card the game no longer has, or a rule that changed
            break


def main():
    out, mode, files = sys.argv[1], sys.argv[2], sys.argv[3:]
    pos, acts, offs, chosen, meta = [], [], [0], [], []
    games = 0
    for f in files:
        for line in open(f):
            if not line.strip():
                continue
            g = json.loads(line)
            bots = g.get("bots") or []
            if mode == "human":
                if "human" not in bots:
                    continue
                seats = {"A" if bots[0] == "human" else "B"}
            else:
                seats = {"A", "B"}
            for p, av, c, turn, me in decisions(g, seats):
                pos.append(p); acts.extend(av); offs.append(len(acts)); chosen.append(c)
                meta.append((games, turn, 0 if me == "A" else 1, len(av)))
            games += 1
            if games % 500 == 0:
                print(games, "games", len(chosen), "decisions", flush=True)
    np.savez_compressed(out, pos=np.array(pos, dtype=np.float32), act=np.array(acts, dtype=np.float32),
                        offs=np.array(offs, dtype=np.int64), chosen=np.array(chosen, dtype=np.int64),
                        meta=np.array(meta, dtype=np.int32))
    print("games", games, "decisions", len(chosen), "actions", len(acts), "->", out)


if __name__ == "__main__":
    main()
