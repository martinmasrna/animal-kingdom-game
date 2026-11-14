"""Write tools/board/boards/costs.json: every prototype card in the pile of its cost, the benched ones in their own pile.
Run once (or again to reset the board to the table)."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
ov = json.loads((HERE.parent.parent / "animal_kingdom/data/energy.json").read_text())
import sys; sys.path.insert(0, str(HERE)); import table
raw = {r["id"]: r for r in json.loads((HERE.parent.parent / "animal_kingdom/data/cards.json").read_text())["cards"]}
ids = [i for i in table.T]
H, y, piles = 264, 0, []
def pile(pid, name, cards, tint="none"):
    global y
    rows = max(1, -(-len(cards) // 18))
    piles.append({"id": pid, "name": name, "x": 0, "y": y, "cols": 18, "stacked": False, "cards": cards, "tint": tint})
    y += 92 + rows * (H + 14) + 16 + 90
key = lambda i: (ov["cards"][i].get("strength", 0) if isinstance(ov["cards"][i].get("strength", 0), int) else 0, raw[i]["name"])
for c in range(1, 6):
    pile(f"cost{c}", f"Cost {c}", sorted((i for i in ids if ov["cards"][i]["cost"] == c), key=key))
pile("bench", "Benched (out of the prototype)", sorted(table.BENCH), "grey")
board = {"rev": 0, "name": "Costs", "energy": True, "only": ids + sorted(table.BENCH), "cards": {}, "piles": piles, "strs": {},
         "rules": {k: ov["rules"][k] for k in ("actions_per_turn", "first_turn_actions", "draw_cost", "max_places_per_turn")}}
(HERE.parent / "board/boards/costs.json").write_text(json.dumps(board, indent=1) + "\n")
print({p["name"]: len(p["cards"]) for p in piles})
