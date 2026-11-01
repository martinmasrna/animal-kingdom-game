"""Pick the positions Martin lists his candidate moves for (results/candidates/set.json): one per recent human game
that replays on today's cards, at the start of his turn in the mid-game, varied decks. Seeded, so the set is fixed."""
import glob, json, random, sys
from pathlib import Path
from animal_kingdom.engine import rules
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
SINCE = sys.argv[2] if len(sys.argv) > 2 else "web_20261028"
rng = random.Random(1)
cands = []
for f in sorted(glob.glob("results/human_games/web/*.jsonl")):
    if Path(f).stem < SINCE:
        continue
    for n, line in enumerate(open(f)):
        g = json.loads(line)
        bots = g.get("bots") or []
        if "human" not in bots or not g.get("lists") or len(g.get("actions", [])) < 20:
            continue
        me = "A" if bots[0] == "human" else "B"
        st = new_game(list(g["lists"][0]), list(g["lists"][1]), g["seed"], map_id=g.get("map_id", "map_b"),
                      config=Config.default().for_log(g), first_player=g["first_player"])
        spots, ok = [], True
        for k, a in enumerate(g["actions"]):
            if (st.player_to_act() == me and st.pending is None and st.actions_taken_this_turn == 0
                    and 6 <= st.turn_counter <= 18 and rules.is_terminal(st) is None):
                spots.append((k, st.turn_counter))
            try:
                rules.apply_logged(st, a)
            except Exception:
                ok = False
                break
        if ok and spots:
            k, turn = rng.choice(spots)
            cands.append({"src": "log", "id": Path(f).stem, "n": n, "k": k, "turn": turn, "seat": me,
                          "decks": [g.get("deck_a"), g.get("deck_b")], "match": g.get("match_id"), "game": n + 1})
rng.shuffle(cands)
out, seen = [], set()
for c in cands:                      # varied: a deck pair at most once while the set is short
    key = tuple(c["decks"])
    if key in seen and len(cands) > N:
        continue
    seen.add(key); out.append(c)
    if len(out) == N:
        break
out.sort(key=lambda c: (c["id"], c["n"]))
for i, c in enumerate(out):
    c["i"] = i
Path("results/candidates").mkdir(exist_ok=True)
Path("results/candidates/set.json").write_text(json.dumps(out, indent=1))
print(len(cands), "positions available,", len(out), "chosen")
for c in out:
    print(c["i"], c["id"], "game", c["game"], "turn", c["turn"], c["seat"], c["decks"])
