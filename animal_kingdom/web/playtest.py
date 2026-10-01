"""Human games read back as playtests: every game a person played on the web client, rebuilt move by move through
the real engine, tied to who played it, with the moments a player was likely surprised flagged.

    .venv/bin/python -m animal_kingdom.web.playtest        (after deploy/deploy.sh pull and deploy/deploy.sh players)

Writes the untracked results/playtest/: games.jsonl (one rebuilt game a line: players, decks, every action with its
time, the engine's events under it and the flags), and text/<player>/<nn>_<match>.txt, each game as plain lines a
reader (a person or a model) can follow. A flag is a fact about the game, never a guess about the player's mind:
what the player then did is for the reader to judge.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from ..engine.actions import action_from_dict
from ..engine.cards import load_cards
from ..engine.state import EngineError, new_game
from ..engine import rules
from ..decks import load_premade_deck
from .match import Match, Seat

ROOT = Path(__file__).resolve().parents[2] / "results"
CARDS = load_cards()
LONG_THINK = 25.0          # seconds before a human's action that count as a long think


def apex(card: str) -> bool:
    return card in CARDS and "Apex Predator" in CARDS[card].keywords


DELAYED = re.compile(r"\b(in \d turns|next turn|at the start|play |place )", re.I)


def roar(card: str) -> bool:
    """A Roar that acts at once (remove, draw, give, gain now): one whose effect lands later, or that lets you play
    another card, does nothing visible under the placement by design."""
    text = CARDS[card].text or "" if card in CARDS else ""
    return "Roar:" in text and not DELAYED.search(text.split("Roar:", 1)[1])


def name(card) -> str:
    return CARDS[card].name if card in CARDS else str(card)


def players_by_match(path: Path) -> dict:
    """(match key, seat) -> 'name#tag', from deploy/deploy.sh players."""
    if not path.is_file():
        return {}
    d = json.loads(path.read_text())
    names = {p["id"]: f"{p['name']}#{p['tag']}" for p in d["profiles"]}
    out = {}
    for h in d["history"]:
        out[(h["match"], h.get("seat") or "")] = {"player": names.get(h["profile"], "?"), "mode": h.get("mode", ""), "ended": h["ended"]}
    return out


def rebuild(g: dict) -> dict:
    """One logged game, replayed: each action with who took it, when, the state it was taken in, and its events."""
    lists = g.get("lists") or [load_premade_deck(g["deck_a"]), load_premade_deck(g["deck_b"])]
    m = Match(g.get("match_id", "pt"), Seat("", "A", deck=g["deck_a"]))
    m.seats["B"] = Seat("", "B", deck=g["deck_b"])
    m.phase, m.seed = "playing", g["seed"]
    m.state = new_game(lists[0], lists[1], g["seed"], map_id=g["map_id"], first_player=g["first_player"])
    st, human = m.state, {p: b == "human" for p, b in zip("AB", g["bots"])}
    times = g.get("action_times") or []
    steps = []
    for i, a in enumerate(g["actions"]):
        seat = a.get("by") or m.to_act()
        bonus = st.turn_flags.get(f"bonus_actions_{st.current}", 0)
        before = {
            "turn": st.turn_counter, "round": st.turn_counter // 2 + 1, "current": st.current,
            "left": st.config.actions_per_turn + bonus - st.actions_taken_this_turn,
            "food": dict(st.food), "hand": [u.card_id for u in st.hands[seat]],
            "pending": bool(st.pending), "top": {cr: (s[-1].card_id, s[-1].owner) for cr, s in st.board.items() if s},
        }
        if not st.pending and human[seat]:
            legal = rules.legal_actions(st)
            before["could_place"] = sorted({x.card_id for x in legal if x.to_dict()["kind"] == "place"})
            before["could_draw"] = any(x.to_dict()["kind"] == "draw" for x in legal)
        ids = {u.iid: u.card_id for p in "AB" for u in st.hands[p]}
        ids.update({u.iid: u.card_id for stack in st.board.values() for u in stack})
        if a.get("kind") == "choice" and isinstance(a.get("choice"), int):
            before["chosen"] = ids.get(a["choice"])
        seq0 = m.seq
        m.act(seat, a)
        events = [e for e in m.events if e.get("seq", 0) > seq0]
        t = times[i] if i < len(times) else None
        dt = round(t - times[i - 1], 1) if t is not None and i > 0 and i - 1 < len(times) else None
        steps.append({"i": i, "seat": seat, "human": human[seat], "a": a, "t": t, "dt": dt, "before": before, "events": events})
    r = st.result
    return {"steps": steps, "result": {"winner": r.winner, "reason": r.reason} if r else None, "lists": lists}


def flags(game: dict) -> list:
    """Facts that mark a likely surprise or a stuck moment, for a human's own actions (or what happened to them)."""
    out, steps = [], game["steps"]
    for k, s in enumerate(steps):
        a, b, ev = s["a"], s["before"], s["events"]
        if s["human"] and s["dt"] is not None and s["dt"] >= LONG_THINK:
            out.append({"i": k, "f": "long_think", "seconds": s["dt"], "seat": s["seat"]})
        if a.get("kind") != "place":
            if s["human"] and a.get("kind") == "pass" and b["left"] > 0 and (b.get("could_place") or b.get("could_draw")):
                out.append({"i": k, "f": "ended_turn_with_moves_left", "left": b["left"], "seat": s["seat"]})
            continue
        card, cr = a["card_id"], a["target"][1] if a["target"][0] == "cr" else None
        # what happened under this placement, its choices included (up to the next top-level action)
        under = list(ev)
        for nxt in steps[k + 1:]:
            if not nxt["before"]["pending"]:
                break
            under += nxt["events"]
        below = b["top"].get(cr) if cr else None
        if apex(card) and below and below[1] != s["seat"]:
            eaten = any(e["e"] == "remove" and e.get("card") == below[0] and e.get("cr") == cr for e in under)
            if not eaten:
                out.append({"i": k, "f": "apex_did_not_eat", "card": card, "prey": below[0], "seat": s["seat"]})
        if roar(card) and not any(e.get("cause") == card and e["e"] not in ("place", "cover") for e in under):
            out.append({"i": k, "f": "roar_did_nothing", "card": card, "seat": s["seat"]})
        placed = next((e.get("iid") for e in ev if e["e"] == "place" and e.get("card") == card and not e.get("cause")), None)
        mine_gone = [e for e in under if e["e"] in ("remove", "bounce", "to_deck") and placed is not None and e.get("iid") == placed]
        if mine_gone:
            out.append({"i": k, "f": "placed_card_left_at_once", "card": card, "how": mine_gone[0]["e"], "seat": s["seat"]})
    return out


def describe(step: dict, me: str) -> str:
    """One action, read from the player's side (`me`): yours or the opponent's, whoever moved."""
    a, b = step["a"], step["before"]
    who = "YOU" if step["seat"] == me else "OPP" if step["human"] else "BOT"
    whose = lambda owner: "your" if owner == me else "their"
    t = f"{step['t']:>6.1f}s" if step["t"] is not None else "      "
    if a["kind"] == "place":
        what = f"places {name(a['card_id'])} on {a['target'][1] if a['target'][0] == 'cr' else 'a den'}"
        top = b["top"].get(a["target"][1]) if a["target"][0] == "cr" else None
        if top:
            what += f" (covering {whose(top[1])} {name(top[0])})"
    elif a["kind"] == "draw":
        what = "draws 2"
    elif a["kind"] == "pass":
        what = f"ends the turn ({b['left']} move{'s' if b['left'] != 1 else ''} unused)" if b["left"] else "ends the turn"
    else:
        c = a.get("choice")
        what = ("skips / keeps" if c == "__skip__" else f"chooses {name(b['chosen'])}" if b.get("chosen")
                else f"chooses {name(c)}" if isinstance(c, str) and c in CARDS else f"chooses {c}")
    fx = []
    for e in step["events"]:
        if e["e"] == "remove" and e.get("cr"):
            fx.append(f"{whose(e['owner'])} {name(e['card'])} removed")
        elif e["e"] == "bounce":
            fx.append(f"{whose(e['owner'])} {name(e['card'])} back to hand")
        elif e["e"] == "to_deck":
            fx.append(f"{whose(e['owner'])} {name(e['card'])} shuffled into its deck")
        elif e["e"] == "capture":
            fx.append(f"{whose(e.get('player', step['seat']))} side CAPTURES THE DEN")
        elif e["e"] == "steal":
            fx.append(f"{'you stole' if e.get('player') == me else 'they stole'} {name(e['card'])}")
        elif e["e"] == "food" and not e.get("income"):
            fx.append(f"{whose(e['player'])} +{e['n']} food")
    think = f"  [thought {step['dt']:.0f}s]" if step["seat"] == me and step["dt"] and step["dt"] >= LONG_THINK else ""
    return f"{t} R{b['round']:<2} {who} {what}" + (f"  -> {'; '.join(fx)}" if fx else "") + think


def render(game: dict) -> str:
    h = game["head"]
    lines = [f"Game {h['match']} ({h['mode'] or 'unknown mode'}): {h['you']} with {h['your_deck']} vs {h['opp']} with {h['opp_deck']}",
             f"Result: {'WON' if h['won'] else 'LOST'} by {h['reason']} after {h['turns']} turns" + (f" ({h['flags']} flags)" if h["flags"] else ""), ""]
    seat = h["seat"]
    for s in game["steps"]:
        lines.append(describe(s, seat))
        for f in game["flags"]:
            if f["i"] == s["i"] and f.get("seat") == seat:
                lines.append(f"         ^ FLAG {f['f']}: " + ", ".join(f"{k}={v}" for k, v in f.items() if k not in ("i", "f", "seat")))
    return "\n".join(lines) + "\n"


def main() -> None:
    who = players_by_match(ROOT / "players.json")
    out_dir = ROOT / "playtest"
    (out_dir / "text").mkdir(parents=True, exist_ok=True)
    games, broken = [], Counter()
    for path in sorted((ROOT / "human_games" / "web").glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            g = json.loads(line)
            if "match_id" not in g:
                broken["no match id"] += 1
                continue
            try:
                game = rebuild(g)
            except (EngineError, KeyError, ValueError) as e:
                broken[type(e).__name__] += 1
                continue
            if game["result"] is None and g["reason"] == "concede":   # a concede ends the match outside the engine
                game["result"] = {"winner": g["winner"], "reason": "concede"}
            if not game["result"] or game["result"]["winner"] != g["winner"] or game["result"]["reason"] != g["reason"]:
                broken["replays differently (cards changed since)"] += 1
                continue
            game["flags"] = flags(game)
            key = f"{g['match_id']}-{g.get('series', 0)}"
            for seat, bot in zip("AB", g["bots"]):
                if bot != "human":
                    continue
                p = who.get((key, seat), {})
                opp = "B" if seat == "A" else "A"
                oinfo = who.get((key, opp), {})
                games.append({**game, "head": {
                    "match": key, "game_no": g.get("game_no"), "seat": seat, "you": p.get("player", "unknown"),
                    "mode": p.get("mode", ""), "ended": p.get("ended"),
                    "opp": oinfo.get("player") if g["bots"][ord(opp) - 65] == "human" else f"Bot ({g['bots'][ord(opp) - 65]})",
                    "your_deck": g["deck_a" if seat == "A" else "deck_b"], "opp_deck": g["deck_b" if seat == "A" else "deck_a"],
                    "won": g["winner"] == seat, "reason": g["reason"], "turns": g["turns"],
                    "first": g["first_player"] == seat,
                    "flags": sum(1 for f in game["flags"] if f.get("seat") == seat)}})
    games.sort(key=lambda x: (x["head"]["you"], x["head"]["ended"] or 0))
    n = defaultdict(int)
    with open(out_dir / "games.jsonl", "w") as f:
        for game in games:
            f.write(json.dumps(game) + "\n")
            you = re.sub(r"[^A-Za-z0-9#_-]", "_", game["head"]["you"])
            n[you] += 1
            d = out_dir / "text" / you
            d.mkdir(exist_ok=True)
            (d / f"{n[you]:03d}_{game['head']['match']}.txt").write_text(render(game))
    print(f"{len(games)} human seats in {len({g['head']['match'] for g in games})} games; skipped: {dict(broken)}")
    print("by player:", dict(Counter(g["head"]["you"] for g in games)))
    print("flags:", dict(Counter(f["f"] for g in games for f in g["flags"] if f.get("seat") == g["head"]["seat"])))


if __name__ == "__main__":
    main()
