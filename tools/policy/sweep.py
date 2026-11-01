"""Time and top pick of the whole-turn search under several settings on several positions, each run capped.
Usage: sweep.py OUT_DIR CAP_SECONDS "setting1" "setting2" ... -- pos1.json pos2.json ...
Writes OUT_DIR/<pos>.<tag>.txt per run (rank_pos.py's output, or TIMEOUT) and prints a summary table."""
import os, re, subprocess, sys, time
from pathlib import Path

args = sys.argv[1:]
out, cap = Path(args[0]), float(args[1])
sep = args.index("--")
settings, positions = args[2:sep], args[sep + 1:]
out.mkdir(parents=True, exist_ok=True)
py = ".venv/bin/python"
rows = []
for pos in positions:
    name = Path(pos).stem
    for st in settings:
        tag = re.sub(r"[^A-Za-z0-9]+", "_", st.replace("animal_kingdom/data/learned/", "")).strip("_")[:60]
        f = out / f"{name}.{tag}.txt"
        t = time.time()
        try:
            r = subprocess.run([py, "-W", "ignore", "tools/policy/rank_pos.py", pos, st], capture_output=True, text=True, timeout=cap)
            text = "\n".join(l for l in r.stdout.splitlines() if "_check" not in l)
        except subprocess.TimeoutExpired:
            text = "TIMEOUT"
        f.write_text(text)
        secs = time.time() - t
        pick = next((l.strip() for l in text.splitlines()[1:2]), "")
        m = re.search(r"\] ([0-9.]+) s", text)
        rows.append((name, st, m.group(1) if m else f">{cap:.0f}", pick[-100:]))
        print(f"{name:16} {st[:60]:60} {rows[-1][2]:>6}  {pick[-90:]}", flush=True)
print("\nsummary")
for name, st, secs, pick in rows:
    print(f"{name:16} {secs:>6}  {st[:50]:50}  {pick[-80:]}")
