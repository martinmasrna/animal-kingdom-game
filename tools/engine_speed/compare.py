"""Compare two recordings move for move: .venv/bin/python tools/engine_speed/compare.py results/engine_speed/baseline.json results/engine_speed/after.json"""
import json, sys
a, b = (json.load(open(f)) for f in sys.argv[1:3])
same = 0
for x, y in zip(a, b):
    k = f"{x['kind'].split(':')[0]:8} {x['a']:>14} v {x['b']:<14} seed {x['seed']}"
    if x["actions"] == y["actions"]:
        same += 1; print(f"same   {k}  {x['seconds']:6.1f}s -> {y['seconds']:6.1f}s")
    else:
        i = next(i for i, (p, q) in enumerate(zip(x["actions"], y["actions"])) if p != q) if len(x["actions"]) == len(y["actions"]) or any(p != q for p, q in zip(x["actions"], y["actions"])) else min(len(x["actions"]), len(y["actions"]))
        print(f"DIFFER {k}  at action {i}: {x['actions'][i] if i < len(x['actions']) else 'END'} vs {y['actions'][i] if i < len(y['actions']) else 'END'}")
print(f"{same}/{len(a)} identical; time {sum(g['seconds'] for g in a):.0f}s -> {sum(g['seconds'] for g in b):.0f}s")
