"""The evening read of Martin's games against the bot: one command after a play day.

    .venv/bin/python tools/evening_read.py [--since 2026-10-31] [--profile 73fc9b588392c875]

Over every logged game of his profile's decks since the date (results/human_games/web/*.jsonl, human vs expert):
- den blunders: a bot turn after which Martin could take the den in his next turn with the hand he really held, when some
  other full bot turn would have held it (the pruned den walk of bots/referee_bot._far_capture, full information). A
  count per deck of his and per deck of the bot's, and the earliest example per game.
- the card census per deck: how often each card was played, how often it sat in his hand at the end, what was drawn but
  never played.
A game a later card or rule change made unreplayable is skipped and counted. Prints markdown; --json writes the records.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sqlite3
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from animal_kingdom.engine import rules  # noqa: E402
from animal_kingdom.engine.cards import load_cards  # noqa: E402
from animal_kingdom.engine.config import Config  # noqa: E402
from animal_kingdom.engine.state import new_game  # noqa: E402
from animal_kingdom.bots.referee_bot import _den_distance, _far_capture  # noqa: E402

PROFILE = "73fc9b588392c875"


def full_turns(s, cap=3000):
    who = s.player_to_act(); out = []; stack = [(s, [])]
    while stack and len(out) < cap:
        cur, seq = stack.pop()
        if cur.result is not None or cur.player_to_act() != who:
            out.append((seq, cur)); continue
        for a in rules.legal_actions(cur):
            n = cur.clone(); rules.apply_action(n, a, validate=False); stack.append((n, seq + [a]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default=time.strftime("%Y-%m-%d"))
    ap.add_argument("--profile", default=PROFILE)
    ap.add_argument("--json")
    a = ap.parse_args()
    C = load_cards()
    saved = json.load(open(f"{ROOT}/results/web_decks.json"))
    names = {k: v["name"] for k, v in saved.items()}
    db = sqlite3.connect(f"{ROOT}/results/web.db")
    own = {json.dumps(sorted(c for c, n in json.loads(raw).items() for _ in range(n))) for (raw,) in db.execute("select cards from decks where profile=?", (a.profile,))}
    mine = {slug for slug, v in saved.items() if json.dumps(sorted(v["list"])) in own}
    day = a.since.replace("-", "")
    rows = [json.loads(l) for f in sorted(glob.glob(f"{ROOT}/results/human_games/web/web_*.jsonl")) if os.path.basename(f)[4:12] >= day for l in open(f) if l.strip()]
    games = [r for r in rows if r["deck_a"] in mine and r["bots"] == ["human", "expert"]]
    per_game = []; census = collections.defaultdict(lambda: collections.defaultdict(lambda: {"played": 0, "games_played": 0, "wins_played": 0, "held_at_end": 0, "drawn_games": 0})); unreplayable = 0
    for g in games:
        st = new_game(list(g["lists"][0]), list(g["lists"][1]), g["seed"], map_id=g.get("map_id", "map_b"), config=Config.default().for_log(g), first_player=g["first_player"])
        deck = names[g["deck_a"]]; win = g["winner"] == "A"; played = collections.Counter(); drawn = set(); starts = []
        try:
            for k, act in enumerate(g["actions"]):
                if act["kind"] != "choice" and st.player_to_act() == "B" and st.actions_taken_this_turn == 0 and st.pending is None and (not starts or starts[-1][0] != k):
                    starts.append((k, st.clone()))
                if act["kind"] == "place" and st.player_to_act() == "A":
                    played[act["card_id"]] += 1
                rules.apply_logged(st, act)
                for u in st.hands["A"]: drawn.add(u.card_id)
        except Exception:
            unreplayable += 1; continue
        for cid in set(g["lists"][0]):
            c = census[deck][cid]
            if played[cid]: c["played"] += played[cid]; c["games_played"] += 1; c["wins_played"] += win
            if cid in drawn: c["drawn_games"] += 1
        for u in st.hands["A"]: census[deck][u.card_id]["held_at_end"] += 1
        dist = _den_distance(st.game_map, "B"); found = []
        for k, s0 in starts:
            s1 = s0.clone(); j = k; acts = g["actions"]
            while j < len(acts) and (acts[j]["kind"] == "choice" or s1.player_to_act() == "B") and s1.result is None:
                rules.apply_logged(s1, acts[j]); j += 1
            if s1.result is not None or s1.player_to_act() != "A" or not _far_capture(s1, "A", dist, [20000]):
                continue
            holds = [seq for seq, end in full_turns(s0) if not (end.result is not None and end.result.winner == "A") and (end.result is not None or not _far_capture(end, "A", dist, [20000]))]
            found.append({"turn": s0.turn_counter, "bot_played": " + ".join(str(x) for x in acts[k:j] if x["kind"] != "choice"), "holds": len(holds),
                          "hold_example": " + ".join(str(x) for x in holds[0]) if holds else None, "martin_hand": [u.card_id for u in s0.hands["A"]]})
        per_game.append({"deck": deck, "opp": names.get(g["deck_b"], g["deck_b"]), "win": win, "reason": g["reason"], "turns": g["turns"], "exposed": found, "match": g.get("match_id"), "game": g.get("game_no")})
    if a.json:
        json.dump({"per_game": per_game, "census": census, "unreplayable": unreplayable}, open(a.json, "w"), indent=1, default=dict)
    print(f"# Evening read since {a.since}: {len(per_game)} games of Martin's decks against the Expert ({unreplayable} unreplayable under today's rules)\n")
    by = collections.defaultdict(lambda: [0, 0, 0, 0, 0])
    for g in per_game:
        b = by[g["deck"]]; bl = sum(1 for f in g["exposed"] if f["holds"]); b[0] += 1; b[1] += g["win"]; b[2] += len(g["exposed"]); b[3] += bl; b[4] += bl > 0
    print("| Martin's deck | games | wins | bot turns leaving the den open | with a holding turn | games with one |\n|---|---|---|---|---|---|")
    for k, v in sorted(by.items(), key=lambda kv: -kv[1][3]): print(f"| {k} | {v[0]} | {v[1]} | {v[2]} | {v[3]} | {v[4]} |")
    byo = collections.defaultdict(lambda: [0, 0, 0])
    for g in per_game:
        b = byo[g["opp"]]; b[0] += 1; b[1] += sum(1 for f in g["exposed"] if f["holds"]); b[2] += g["win"] and g["reason"] == "hq_capture"
    print("\n| Bot's deck | games | den blunders | Martin's den wins |\n|---|---|---|---|")
    for k, v in sorted(byo.items(), key=lambda kv: -kv[1][1]): print(f"| {k} | {v[0]} | {v[1]} | {v[2]} |")
    print("\n## Card census\n")
    for deck, cards in census.items():
        n = by[deck][0]
        if n < 5: continue
        rows_ = sorted(cards.items(), key=lambda kv: -kv[1]["played"])
        never = [C[c].name for c, v in rows_ if v["played"] == 0 and v["drawn_games"] > 0]
        print(f"**{deck}** ({n} games). Most played: " + ", ".join(f"{C[c].name} {v['played']}" for c, v in rows_[:6]) + ". Held at the end most: "
              + ", ".join(f"{C[c].name} {v['held_at_end']}" for c, v in sorted(cards.items(), key=lambda kv: -kv[1]['held_at_end'])[:4]) + ". Drawn but never played: " + (", ".join(never) or "none") + ".\n")


if __name__ == "__main__":
    main()
