"""Self-play with the live Expert (untimed) on Martin's ten precons, every pairing both ways, actions logged:
the games the candidate network learns from. Usage: selfplay.py OUT.jsonl GAMES_PER_PAIR [JOBS]"""
import json, os, sys
from pathlib import Path
os.environ.setdefault("AK_RUST_BOTS", "1")
os.environ["AK_EXTRA_DECKS"] = Path("results/policy/decks.json").read_text()   # his current decks, from his games
from animal_kingdom.sim.runner import run_pairs
from animal_kingdom.sim.replay import write_game_logs
from animal_kingdom.web.match import EXPERT

DECKS = sorted(json.loads(os.environ["AK_EXTRA_DECKS"]))
spec = EXPERT.replace("time_budget=8", "time_budget=0")
if __name__ == "__main__":
  out, per, jobs = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 7
  pairs = [(a, b) for i, a in enumerate(DECKS) for b in DECKS[i:]]
  recs = run_pairs(pairs, per, base_seed=20261101, bots=(spec, spec), jobs=jobs, log_actions=True,
                   progress=lambda a, b, i, n: print(f"{a} v {b}: {i}/{n}", flush=True))
  n = write_game_logs(recs, out, map_id="map_b", bots=(spec, spec))
  print("wrote", n, "games to", out)
