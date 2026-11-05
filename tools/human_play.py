"""How people play: card, deck, ending and opening counts from the recorded human games. Analysis only; nothing in the game changes.

Reads every web game log under results/human_games/ (one JSON line a game; the older ad-hoc recorder files have no
`actions` and are skipped). A seat is a person where the log's `bots` field says "human"; the other seat is a bot
(easy / normal / expert) or a second person. Old card ids are read as today's with `web/renamed.py`.

Each game is replayed as tools/puzzles/mine.py replays it (`new_game` from the logged lists and seed, the mulligan
skip for logs older than the mulligan, `rules.apply_logged`). A game "replays on today's cards" when every action
applies and the replay ends the way the log does (same winner and reason; still undecided for a concession, quit or
timeout). For those games the replay gives who took each action, on which turn, and every card that passed through a
person's hand. For the others, a placement is credited to the seat whose list holds that card; one both lists hold is
left uncredited, and counted, as is a token neither list holds.

Outputs: markdown tables on stdout, one per question in knowledge/analysis/human-play-2026-11-05.md, and with
--json FILE the per-game records it built them from.

Usage:
  .venv/bin/python tools/human_play.py                       # tables to stdout
  .venv/bin/python tools/human_play.py --workers 4 --json /tmp/human_play.json
  .venv/bin/python tools/human_play.py --limit 100           # a quick look at the first 100 games

Definitions the tables use:
  turn          a player's turn, counted per player: a person's turn 1 is their first turn, whoever went first. The
                log's `turns` is the engine's turn counter at the end, both players' turns together.
  row           where a placement lands, counted from the placer's own den: row 1 is the column in front of their
                den, row 5 the column in front of the opponent's, "den" a placement onto the opponent's den.
  played        a placement of the card by that seat, from any source (a turn action or one an effect grants); a
                placement of an evolved form the placer's list lacks counts for the card it grew from (GREW_FROM).
  den fell within five turns    the opponent captured the person's den before the person's sixth turn began.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import multiprocessing as mp
import os
import statistics
import sys
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from animal_kingdom.decks import load_premade_deck  # noqa: E402
from animal_kingdom.engine import rules  # noqa: E402
from animal_kingdom.engine.actions import SKIP, ChoiceAction  # noqa: E402
from animal_kingdom.engine.config import Config  # noqa: E402
from animal_kingdom.engine.state import EngineError, new_game  # noqa: E402
from animal_kingdom.web.renamed import CARDS, renamed  # noqa: E402

SEATS = ("A", "B")
# A card that evolves (the Caterpillar, the legendary Butterfly and Dung Beetle) is placed under its evolved form's id;
# a placement of a form counts as a play of the card it grew from.
GREW_FROM = {f: c.id for c in CARDS.values() if c.evolves for f in c.related}
UNDECIDED = {"concede", "quit", "timeout", None}


def _row(seat: str, target) -> Optional[str]:
    if not target:
        return None
    if target[0] == "hq":
        return "den"
    col = int(str(target[1]).split(",")[0])
    return str(col if seat == "A" else 6 - col)


def _lists(log: dict):
    if log.get("lists"):
        return [list(x) for x in log["lists"]]
    try:
        return [load_premade_deck(log["deck_a"]), load_premade_deck(log["deck_b"])]
    except Exception:  # noqa: BLE001 - a premade slug that no longer exists
        return None


def game_record(task: tuple) -> dict:
    path, lineno, raw = task
    log = renamed(raw)
    bots = list(log.get("bots") or [])
    kind = {p: (bots[i] if i < len(bots) else "unknown") for i, p in enumerate(SEATS)}
    lists = _lists(log)
    rec = {
        "path": path, "line": lineno, "date": os.path.basename(path).split("_")[1][:8],
        "kind": kind, "deck": {"A": log.get("deck_a"), "B": log.get("deck_b")},
        "lists": {"A": sorted(lists[0]), "B": sorted(lists[1])} if lists else None,
        "winner": log.get("winner"), "reason": log.get("reason"), "turns": log.get("turns"),
        "first": log.get("first_player"),
        "replayed": False, "error": None, "plays": [], "in_hand": None, "opening": None,
        "end_turn_counter": None, "end_food": None, "uncredited": 0,
    }
    actions = log.get("actions") or []
    # ---- replay
    plays, opening = [], []
    seen_hand = {p: set() for p in SEATS}
    state = None
    try:
        if lists is None:
            raise ValueError("no lists")
        state = new_game(list(lists[0]), list(lists[1]), log["seed"], map_id=log.get("map_id", "map_b"),
                         config=Config.default().for_log(log), first_player=log["first_player"])

        def look():
            for p in SEATS:
                seen_hand[p].update(u.card_id for u in state.hands[p])
        look()
        for adict in actions:
            while state.pending is not None and state.effect_stack[-1].get("op") == "mulligan" \
                    and adict["kind"] != "choice":
                rules.apply_action(state, ChoiceAction(SKIP))
                look()
            tc, owner = state.turn_counter, state.current
            actor = adict.get("by") or state.player_to_act()
            sub = state.pending is not None
            rules.apply_logged(state, adict)
            look()
            k = adict["kind"]
            if k == "place":
                c = adict["card_id"]
                if c not in lists[SEATS.index(actor)]:
                    c = GREW_FROM.get(c, c)
                plays.append({"seat": actor, "card": c, "own_turn": tc // 2 + 1, "sub": sub})
            if k in ("place", "draw", "roam") and actor == owner and tc < 4:
                opening.append({"seat": actor, "own_turn": tc // 2 + 1, "kind": k, "sub": sub,
                                "row": _row(actor, adict.get("target")) if k != "draw" else None,
                                "card": adict.get("card_id")})
        res = rules.is_terminal(state)
        if log.get("reason") in UNDECIDED:
            ok = res is None
        else:
            ok = res is not None and res.winner == log.get("winner") and \
                (res.reason == log.get("reason") or {res.reason, log.get("reason")} == {"passes", "exhaustion"})
        if not ok:
            raise ValueError(f"ends differently: replay {res and (res.winner, res.reason)}, "
                             f"log {(log.get('winner'), log.get('reason'))}")
        rec.update(replayed=True, plays=plays, opening=opening,
                   in_hand={p: sorted(seen_hand[p]) for p in SEATS},
                   end_turn_counter=state.turn_counter, end_food=dict(state.food))
        return rec
    except (EngineError, KeyError, ValueError, IndexError, TypeError, AttributeError) as e:
        rec["error"] = f"{type(e).__name__}: {e}"[:200]
        if state is not None and state.turn_counter >= 4:     # both players' first two turns applied before it broke
            rec["opening"] = opening
    # ---- no replay: credit placements by list membership
    if lists:
        sets = {"A": set(lists[0]), "B": set(lists[1])}
        for adict in actions:
            if adict.get("kind") != "place":
                continue
            c = adict["card_id"]
            owners = [p for p in SEATS if c in sets[p]]
            if not owners and c in GREW_FROM:
                c = GREW_FROM[c]
                owners = [p for p in SEATS if c in sets[p]]
            if len(owners) == 1:
                plays.append({"seat": owners[0], "card": c, "own_turn": None, "sub": None})
            else:
                rec["uncredited"] += 1
    rec["plays"] = plays
    return rec


def load_tasks(root: str, limit: Optional[int]):
    tasks, skipped = [], 0
    for f in sorted(glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)):
        with open(f, encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if not line.strip():
                    continue
                d = json.loads(line)
                if "actions" not in d:
                    skipped += 1
                    continue
                tasks.append((os.path.relpath(f, ROOT), i, d))
    return (tasks[:limit] if limit else tasks), skipped


# ------------------------------------------------------------------ tables

def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f}% ({a}/{b})" if b else "– (0/0)"


def table(head: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


def name(c: str) -> str:
    card = CARDS.get(c)
    return f"{card.name} (`{c}`)" if card else f"`{c}` (no card today)"


def person_seats(g: dict) -> list[str]:
    return [p for p in SEATS if g["kind"][p] == "human"]


def opp(p: str) -> str:
    return "B" if p == "A" else "A"


def shipped(slug: Optional[str]) -> bool:
    """A deck the game ships (a bot or starter slug), not a player's saved one."""
    return bool(slug) and not slug.startswith(("custom_", "martin_", "deck_"))


def label(lst) -> str:
    """A list read by its two most common tags, by copies: what kind of deck it is."""
    tags = collections.Counter(t for c in lst if c in CARDS for t in CARDS[c].tags)
    return "/".join(t for t, _ in tags.most_common(2)) or "?"


def own_turns(g: dict, p: str) -> int:
    """The turns seat `p` had begun when the game ended (the log's `turns` is the engine's counter, from 0)."""
    t = g["turns"] or 0
    return t // 2 + 1 if g["first"] == p else (t + 1) // 2


def report(games: list[dict], skipped_files_lines: int) -> str:
    out = []
    rp = [g for g in games if g["replayed"]]
    errs = collections.Counter((g["error"] or "").split(":")[0] for g in games if not g["replayed"])
    kinds = collections.Counter("/".join(g["kind"][p] for p in SEATS) for g in games)
    out.append("## Corpus\n")
    out.append(table(["", "games"], [
        ["web game logs", len(games)],
        ["dates", f"{min(g['date'] for g in games)} to {max(g['date'] for g in games)}"],
        *[[f"seats {k}", v] for k, v in kinds.most_common()],
        ["replay on today's cards", pct(len(rp), len(games))],
        *[[f"no replay: {k}", v] for k, v in errs.most_common()],
        ["placements credited by list (no replay)", sum(1 for g in games if not g["replayed"] for _ in g["plays"])],
        ["placements left uncredited (no replay; card in both lists, or in neither: a token)", sum(g["uncredited"] for g in games)],
        ["ad-hoc recorder lines skipped (no actions)", skipped_files_lines],
    ]))

    # ---- per card
    pg = [(g, p) for g in games for p in person_seats(g) if g["lists"]]
    deck_n = collections.Counter()      # person-games with the card in the deck
    deck_w = collections.Counter()
    att_n = collections.Counter()       # person-games where a play of the card can be credited (replayed, or only this seat's list holds it)
    att_w = collections.Counter()
    play_n = collections.Counter()      # ... and played at least once
    play_w = collections.Counter()
    hand_n = collections.Counter()      # replayed person-games where the card was in hand
    hand_play = collections.Counter()   # ... and played
    copies = collections.Counter()      # copies in decks summed
    for g, p in pg:
        won = g["winner"] == p
        dk = set(g["lists"][p])
        for c in dk:
            deck_n[c] += 1
            deck_w[c] += won
        for c in g["lists"][p]:
            copies[c] += 1
        played = {x["card"] for x in g["plays"] if x["seat"] == p}
        other = set(g["lists"][opp(p)])
        for c in dk:
            if g["replayed"] or c not in other:
                att_n[c] += 1
                att_w[c] += won
                if c in played:
                    play_n[c] += 1
                    play_w[c] += won
        if g["replayed"]:
            for c in set(g["in_hand"][p]) & dk:
                hand_n[c] += 1
                hand_play[c] += c in played
    npg = len(pg)
    rows = []
    for c in sorted(deck_n, key=lambda c: (-deck_n[c], c)):
        dr = deck_w[c] / deck_n[c]
        pr = play_w[c] / play_n[c] if play_n[c] else None
        ar = att_w[c] / att_n[c] if att_n[c] else None
        rows.append([name(c), CARDS[c].status if c in CARDS else "gone", pct(deck_n[c], npg),
                     f"{copies[c] / deck_n[c]:.1f}", pct(play_n[c], att_n[c]), pct(hand_play[c], hand_n[c]),
                     pct(play_w[c], play_n[c]), pct(att_w[c], att_n[c]),
                     f"{100 * (pr - ar):+.0f}" if pr is not None and ar is not None else "–"])
    out.append("\n## Cards in people's decks\n")
    out.append(f"{npg} person-games with a known list (a game between two people counts twice). "
               "In a deck: share of those person-games whose list held the card; copies: mean copies when held. "
               "Played in the game: of the person-games that held it and where a play can be credited (the game "
               "replays, or the opponent's list lacks the card), how many played it at least once. Played when in "
               "hand: of the replayed person-games where it reached the hand, how many played it. Win rate when "
               "played and deck win rate are the person's, over the same creditable person-games.\n")
    out.append(table(["card", "status today", "in a deck", "copies", "played in the game", "played when in hand",
                      "win rate when played", "deck win rate", "played − deck (pts)"], rows))

    # ---- never played
    never = [c for c in deck_n if play_n[c] == 0]
    rows = [[name(c), CARDS[c].status if c in CARDS else "gone", deck_n[c], att_n[c], hand_n[c]]
            for c in sorted(never, key=lambda c: (-deck_n[c], c))]
    out.append("\n## Cards people put in a deck and never played\n")
    out.append(table(["card", "status today", "person-games in deck", "creditable person-games", "replayed games in hand"], rows))
    low = [c for c in deck_n if hand_n[c] >= 20 and hand_play[c] / hand_n[c] < 0.25]
    rows = [[name(c), pct(hand_play[c], hand_n[c]), deck_n[c]] for c in sorted(low, key=lambda c: hand_play[c] / hand_n[c])]
    out.append("\n## Cards held at least 20 times and played from under a quarter of those hands\n")
    out.append(table(["card", "played when in hand", "person-games in deck"], rows))
    coll = [c for c, card in CARDS.items() if card.status == "collectible" and deck_n[c] == 0]
    out.append(f"\n## Collectible cards today in no person's deck ({len(coll)})\n")
    out.append(", ".join(sorted(CARDS[c].name for c in coll)) or "none")

    # ---- decks
    lists_ct = collections.Counter()
    lists_w = collections.Counter()
    lists_name = collections.defaultdict(collections.Counter)
    lists_dates = collections.defaultdict(set)
    for g, p in pg:
        key = tuple(g["lists"][p])
        lists_ct[key] += 1
        lists_w[key] += g["winner"] == p
        lists_name[key][g["deck"][p]] += 1
        lists_dates[key].add(g["date"])
    bot_all = [(g, p) for g in games for p in SEATS if g["kind"][p] in ("easy", "normal", "expert") and g["lists"]]
    bot_pg = [(g, p) for g, p in bot_all if shipped(g["deck"][p])]
    bot_lists = collections.Counter(tuple(g["lists"][p]) for g, p in bot_pg)
    shipped_names = set(bot_lists)
    out.append(f"\n## Decks people built ({len(lists_ct)} distinct lists over {npg} person-games)\n")
    buckets = collections.Counter()
    for k, v in lists_ct.items():
        buckets["1 game" if v == 1 else "2–4" if v < 5 else "5–19" if v < 20 else "20+"] += 1
    out.append(table(["games played with the list", "lists", "person-games"],
                     [[b, buckets[b], sum(v for k, v in lists_ct.items()
                                           if ("1 game" if v == 1 else "2–4" if v < 5 else "5–19" if v < 20 else "20+") == b)]
                      for b in ("20+", "5–19", "2–4", "1 game")]))
    rows = []
    for key, n in lists_ct.most_common(25):
        top = collections.Counter(key).most_common()
        rows.append([n, pct(lists_w[key], n), lists_name[key].most_common(1)[0][0], label(key),
                     "yes" if key in shipped_names else "no",
                     f"{min(lists_dates[key])}–{max(lists_dates[key])}",
                     ", ".join(f"{k2}×{CARDS[c].name if c in CARDS else c}" for c, k2 in top[:6]) + " …"])
    out.append("\nThe 25 most played lists:\n")
    out.append(table(["games", "person win rate", "deck name", "tags", "a shipped bot list", "dates",
                      "most copies"], rows))

    # ---- people vs bots: card makeup
    def makeup(pairs):
        per = collections.Counter()
        tags = collections.Counter()
        rar = collections.Counter()
        strs = []
        legs = 0
        for g, p in pairs:
            for c in g["lists"][p]:
                per[c] += 1
                card = CARDS.get(c)
                if card:
                    rar[card.rarity] += 1
                    if isinstance(card.base_strength, int):
                        strs.append(card.base_strength)
                    for t in card.tags:
                        tags[t] += 1
        n = len(pairs)
        return per, tags, rar, strs, n
    own_pg = [(g, p) for g, p in pg if tuple(g["lists"][p]) not in {tuple(g2["lists"][p2]) for g2, p2 in bot_pg}]
    hp, ht, hr, hs, hn = makeup(own_pg)
    bp, bt, br, bs, bn = makeup(bot_pg)
    one = {}                                   # each distinct own list once, so a list played 250 times weighs as one
    for g, p in own_pg:
        one.setdefault(tuple(g["lists"][p]), (g, p))
    lp, lt, lr, ls, ln = makeup(list(one.values()))
    out.append("\n## People's decks against the bots' decks\n")
    out.append(f"People: {hn} person-games on a list of their own ({len(pg) - hn} more on a shipped bot list "
               f"are left out). Bots: {bn} bot seats on a shipped deck "
               f"({len(bot_lists)} distinct lists; the {len(bot_all) - bn} bot seats on a player's saved deck, "
               "from the gauntlet, are left out). Copies per deck, averaged over games.\n")
    rows = [["mean printed strength", f"{statistics.mean(hs):.2f}", f"{statistics.mean(ls):.2f}", f"{statistics.mean(bs):.2f}"]]
    for r in sorted(set(hr) | set(br)):
        rows.append([f"{r} copies per deck", f"{hr[r] / hn:.1f}", f"{lr[r] / ln:.1f}", f"{br[r] / bn:.1f}"])
    for st in range(0, 11):
        rows.append([f"strength {st} copies per deck", f"{sum(1 for x in hs if x == st) / hn:.1f}",
                     f"{sum(1 for x in ls if x == st) / ln:.1f}", f"{sum(1 for x in bs if x == st) / bn:.1f}"])
    out.append(table(["", "people, by game", f"people, each list once ({ln})", "bots, by game"], rows))
    diff = sorted(set(hp) | set(bp), key=lambda c: -(abs(hp[c] / hn - bp[c] / bn)))
    rows = [[name(c), f"{hp[c] / hn:.2f}", f"{lp[c] / ln:.2f}", f"{bp[c] / bn:.2f}", f"{hp[c] / hn - bp[c] / bn:+.2f}"]
            for c in diff[:30]]
    out.append("\nThe 30 cards whose copies per deck differ most between people and bots (by game):\n")
    out.append(table(["card", "people, by game", "people, each list once", "bots, by game", "people − bots"], rows))
    rows = [[t, f"{ht[t] / hn:.1f}", f"{lt[t] / ln:.1f}", f"{bt[t] / bn:.1f}"]
            for t in sorted(set(ht) | set(bt), key=lambda t: -abs(ht[t] / hn - bt[t] / bn))[:15]]
    out.append("\nTags, copies per deck (the 15 that differ most by game):\n")
    out.append(table(["tag", "people, by game", "people, each list once", "bots, by game"], rows))

    # ---- endings
    out.append("\n## How a person's game ends\n")
    out.append("Turn: the person's own turns begun when the game ended. "
               "Every person-game.\n")
    allpg = [(g, p) for g in games for p in person_seats(g)]
    end = collections.defaultdict(list)
    for g, p in allpg:
        res = "won" if g["winner"] == p else "lost" if g["winner"] in SEATS else "no winner"
        end[(g["reason"], res)].append(own_turns(g, p))
    rows = []
    for (reason, res), ts in sorted(end.items(), key=lambda kv: -len(kv[1])):
        q = statistics.quantiles(ts, n=4) if len(ts) >= 4 else [min(ts), statistics.median(ts), max(ts)]
        rows.append([reason, res, pct(len(ts), len(allpg)), statistics.median(ts), f"{q[0]:.0f}–{q[2]:.0f}",
                     f"{min(ts)}–{max(ts)}"])
    out.append(table(["ended by", "person", "games", "median turn", "middle half", "range"], rows))
    out.append("\nBy turn (person's own turns), every person-game:\n")
    bt_ = collections.defaultdict(collections.Counter)
    for g, p in allpg:
        t = own_turns(g, p)
        b = f"{t}" if t <= 10 else "11–13" if t <= 13 else "14+"
        res = "won" if g["winner"] == p else "lost" if g["winner"] in SEATS else "none"
        bt_[b][(g["reason"], res)] += 1
    cols = [("hq_capture", "won"), ("hq_capture", "lost"), ("food", "won"), ("food", "lost"), ("concede", "lost")]
    order = [str(i) for i in range(0, 11)] + ["11–13", "14+"]
    rows = [[b, sum(bt_[b].values())] + [bt_[b][c] for c in cols] + [sum(bt_[b].values()) - sum(bt_[b][c] for c in cols)]
            for b in order if bt_[b]]
    out.append(table(["turn", "games", "took den", "lost den", "won on food", "lost on food", "conceded", "other"], rows))
    out.append("\nBy opponent:\n")
    byo = collections.defaultdict(collections.Counter)
    for g, p in allpg:
        o = g["kind"][opp(p)]
        byo[o]["n"] += 1
        byo[o]["won"] += g["winner"] == p
        byo[o][g["reason"] + ("_won" if g["winner"] == p else "_lost")] += 1
        byo[o]["turns"] += own_turns(g, p)
    rows = [[o, c["n"], pct(c["won"], c["n"]), pct(c["hq_capture_won"], c["n"]), pct(c["hq_capture_lost"], c["n"]),
             pct(c["food_won"], c["n"]), pct(c["food_lost"], c["n"]), f"{c['turns'] / c['n']:.1f}"]
            for o, c in sorted(byo.items(), key=lambda kv: -kv[1]["n"])]
    out.append(table(["opponent", "person-games", "person won", "took den", "lost den", "won on food", "lost on food",
                      "mean turn"], rows))

    # ---- concessions
    out.append("\n## Concessions\n")
    conc = [(g, p) for g, p in allpg if g["reason"] in ("concede", "quit", "timeout", None) and g["winner"] != p]
    rows = []
    for o in sorted({g["kind"][opp(p)] for g, p in allpg}):
        n = sum(1 for g, p in allpg if g["kind"][opp(p)] == o)
        c = sum(1 for g, p in conc if g["kind"][opp(p)] == o and g["reason"] == "concede")
        rows.append([o, pct(c, n)])
    out.append("How often a person concedes, by opponent:\n")
    out.append(table(["opponent", "person conceded"], rows))
    ct = collections.Counter()
    for g, p in conc:
        if g["reason"] != "concede":
            continue
        t = own_turns(g, p)
        ct[f"{t}" if t <= 10 else "11–13" if t <= 13 else "14+"] += 1
    nconc = sum(ct.values())
    early = sum(1 for g, p in conc if g["reason"] == "concede" and (g["turns"] or 0) <= 1)
    out.append(f"\nConceded before both players had finished a turn (turn counter 0 or 1): {pct(early, nconc)}.\n")
    out.append("\nThe turn a person conceded on (their own turns begun):\n")
    out.append(table(["turn", "concessions"], [[b, pct(ct[b], nconc)] for b in order if ct[b]]))
    rows = []
    for g, p in conc:
        if g["reason"] == "concede" and g["replayed"] and (g["turns"] or 0) >= 2:
            fp, fo = g["end_food"][p], g["end_food"][opp(p)]
            rows.append((fp, fo))
    if rows:
        behind = sum(1 for a, b in rows if a < b)
        out.append(f"\nIn the {len(rows)} concessions that replay and come after both players' first turn: food behind the opponent at the concession in "
                   f"{pct(behind, len(rows))}; median food {statistics.median(a for a, _ in rows)} against "
                   f"{statistics.median(b for _, b in rows)}.\n")
    other = collections.Counter(g["reason"] for g, p in conc if g["reason"] != "concede")
    out.append(f"\nOther endings without a result for the person: {dict(other)}. "
               "A person who closes the tab leaves no log line at all; those games are not here.\n")

    # ---- openings: person vs Expert, same games
    out.append("\n## Turns 1 and 2: people against the Expert in the same games\n")
    hx = [g for g in games if g["opening"] is not None and sorted(g["kind"].values()) == ["expert", "human"]]
    nfull = sum(g["replayed"] for g in hx)
    out.append(f"{len(hx)} person-vs-Expert games whose replay gets through both players' first two turns "
               f"({nfull} replay to the end, {len(hx) - nfull} break later). Counts are actions on the player's own first and second turn; "
               "\"placements\" include those an effect grants (marked free). The first player's turn 1 has one action in "
               "logs that record `first_turn_actions: 1` and two in older ones.\n")
    for first in (True, False):
        rows = []
        for t in (1, 2):
            agg = {}
            for who in ("human", "expert"):
                c = collections.Counter()
                ngames = 0
                for g in hx:
                    seat = next(p for p in SEATS if g["kind"][p] == who)
                    if (g["first"] == seat) != (first if who == "human" else not first):
                        continue
                    ngames += 1
                    for a in g["opening"]:
                        if a["seat"] != seat or a["own_turn"] != t:
                            continue
                        if a["kind"] == "draw":
                            c["draw"] += 1
                        elif a["kind"] == "roam":
                            c["roam"] += 1
                        else:
                            c["place"] += 1
                            c["free" if a["sub"] else "action"] += 1
                            c["row " + str(a["row"])] += 1
                agg[who] = (c, ngames)
            for who in ("human", "expert"):
                c, n = agg[who]
                rows.append([t, "person" if who == "human" else "Expert", n,
                             f"{c['draw'] / n:.2f} ({c['draw']})" if n else "–",
                             f"{c['place'] / n:.2f} ({c['place']}, {c['free']} free)" if n else "–",
                             *[f"{c['row ' + r] / n:.2f} ({c['row ' + r]})" if n else "–" for r in ("1", "2", "3", "4", "5", "den")]])
        seat_note = "person goes first (the Expert second)" if first else "person goes second (the Expert first)"
        out.append(f"\n{seat_note}; per game:\n")
        out.append(table(["own turn", "who", "games", "draws", "placements", "row 1", "row 2", "row 3", "row 4", "row 5",
                          "den"], rows))
    # which cards open
    out.append("\nThe cards most placed on a person's turn 1, against the Expert's turn 1 in the same games:\n")
    pc, ec = collections.Counter(), collections.Counter()
    for g in hx:
        hs_ = next(p for p in SEATS if g["kind"][p] == "human")
        for a in g["opening"]:
            if a["own_turn"] == 1 and a["kind"] == "place":
                (pc if a["seat"] == hs_ else ec)[a["card"]] += 1
    out.append(table(["person's turn 1", "times", "Expert's turn 1", "times"],
                     [[name(a), x, name(b), y] for (a, x), (b, y) in zip(pc.most_common(12), ec.most_common(12))]))

    # ---- den fell within five turns
    out.append("\n## A person's den fell within five turns, by opponent deck (replayed games)\n")
    fell = collections.defaultdict(collections.Counter)
    fell_names = collections.defaultdict(collections.Counter)
    for g in rp:
        for p in person_seats(g):
            o = opp(p)
            key = (g["kind"][o], ("a person's deck: " if g["kind"][o] == "human" else "") + label(g["lists"][o]))
            fell[key]["n"] += 1
            fell_names[key][g["deck"][o]] += 1
            # the person's sixth turn starts at counter 10 going first, 11 going second
            limit = 10 if g["first"] == p else 11
            if g["winner"] == o and g["reason"] == "hq_capture" and g["end_turn_counter"] < limit:
                fell[key]["fell"] += 1
            if g["winner"] == o and g["reason"] == "hq_capture":
                fell[key]["any"] += 1
    rows = [[k[1], k[0], ", ".join(f"{d} ({n})" for d, n in fell_names[k].most_common(3)), c["n"],
             pct(c["fell"], c["n"]), pct(c["any"], c["n"])]
            for k, c in sorted(fell.items(), key=lambda kv: (-kv[1]["fell"] / kv[1]["n"], -kv[1]["n"]))]
    tot = collections.Counter()
    for c in fell.values():
        tot.update(c)
    rows.append(["all", "", "", tot["n"], pct(tot["fell"], tot["n"]), pct(tot["any"], tot["n"])])
    out.append("Opponent deck read by its two most common tags (copies), today's cards.\n")
    out.append(table(["opponent deck", "pilot", "deck names (games)", "person-games", "den fell within 5 turns", "den fell at all"], rows))
    return "\n".join(out) + "\n"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=os.path.join(ROOT, "results", "human_games"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--json", default=None, help="also write the per-game records here")
    args = ap.parse_args(argv)
    tasks, skipped = load_tasks(args.root, args.limit)
    with mp.Pool(args.workers) as pool:
        games = list(pool.imap(game_record, tasks, chunksize=8))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            for g in games:
                fh.write(json.dumps(g) + "\n")
    print(report(games, skipped))


if __name__ == "__main__":
    main()
