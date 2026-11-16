"""Generate `map_hex` (Martin's sketch, 2026-11-16) into data/maps.json from its geometry: flat-top hexagons in a diamond of
columns 1-2-3-4-3-2-1, the two tips the dens (A left, B right), the 14 hexagons between them the crossroads, named
"column,row" (column 1..5 from your den, row from the top). Two crossroads are adjacent when their hexagons share an edge;
a den's front is the hexagons touching its tip; a region is a corner where three crossroads meet (none that touches a den),
every region worth the same food (Martin: "a good first shot would be setting all regions at 5").

    .venv/bin/python tools/maps/make_hex.py [--food 5] [--dry]
"""
import argparse, json, math
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "animal_kingdom" / "data" / "maps.json"
COLS = [1, 2, 3, 4, 3, 2, 1]


def build(food: int) -> dict:
    R3 = math.sqrt(3)
    cells = []                                     # (name, x, y); s = 1
    for k, n in enumerate(COLS):
        for i in range(n):
            x, y = 1.5 * k, R3 * ((4 - n) / 2 + i)
            name = "HQ_A" if k == 0 else "HQ_B" if k == len(COLS) - 1 else f"{k},{i + 1}"
            cells.append((name, x, y))
    near = lambda a, b: abs(math.hypot(a[1] - b[1], a[2] - b[2]) - R3) < 1e-6
    crs = [c for c in cells if not c[0].startswith("HQ")]
    edges = [[a[0], b[0]] for i, a in enumerate(crs) for b in crs[i + 1:] if near(a, b)]
    front = {p: [c[0] for c in crs if near(c, next(t for t in cells if t[0] == f"HQ_{p}"))] for p in "AB"}
    corners = {}
    for c in cells:
        for j in range(6):
            vx, vy = c[1] + math.cos(j * math.pi / 3), c[2] + math.sin(j * math.pi / 3)
            corners.setdefault((round(vx, 4), round(vy, 4)), []).append(c[0])
    regions = {}
    three = sorted((v for v in corners.items() if len(v[1]) == 3 and not any(n.startswith("HQ") for n in v[1])), key=lambda v: (v[0][0], v[0][1]))
    for i, (_, names) in enumerate(three, 1):
        regions[f"R{i}"] = {"corners": sorted(names), "food": food}
    return {"id": "map_hex", "name": "Hex Diamond", "crossroads": [c[0] for c in crs], "edges": edges,
            "hqs": {p: {"connects": front[p]} for p in "AB"}, "regions": regions, "win_food": 100}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--food", type=int, default=5); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    m = build(a.food)
    print(f"{len(m['crossroads'])} crossroads, {len(m['edges'])} edges, fronts {m['hqs']['A']['connects']} / {m['hqs']['B']['connects']}, "
          f"{len(m['regions'])} regions of {a.food}")
    if not a.dry:   # written in the file's own hand-laid format (one map block appended or replaced), so the diff is the block
        j = lambda v: json.dumps(v)
        rows = lambda items, per: [", ".join(items[i:i + per]) for i in range(0, len(items), per)]
        block = ["    {", f'      "id": "map_hex",', f'      "name": {j(m["name"])},', '      "crossroads": [']
        block += ["        " + r + ("," if k < len(rows([j(c) for c in m["crossroads"]], 5)) - 1 else "") for k, r in enumerate(rows([j(c) for c in m["crossroads"]], 5))]
        er = rows([j(e) for e in m["edges"]], 4)
        block += ["      ],", '      "edges": ['] + ["        " + r + ("," if k < len(er) - 1 else "") for k, r in enumerate(er)] + ["      ],"]
        block += ['      "hqs": {', f'        "A": {{ "connects": {j(m["hqs"]["A"]["connects"])} }},', f'        "B": {{ "connects": {j(m["hqs"]["B"]["connects"])} }}', "      },"]
        rg = list(m["regions"].items())
        block += ['      "regions": {'] + [f'        {j(k)}: {{ "corners": {j(v["corners"])}, "food": {v["food"]} }}' + ("," if i < len(rg) - 1 else "") for i, (k, v) in enumerate(rg)]
        block += ["      },", f'      "win_food": {m["win_food"]}', "    }"]
        text = DATA.read_text()
        start = text.find('    {\n      "id": "map_hex"')
        if start >= 0:                              # replace the existing block (it is the last map)
            text = text[:start].rstrip().rstrip(",") + "\n"
            text = text[:text.rfind("  ]")] if False else text
            head = text
        else:
            head = text[:text.rfind("  ]")].rstrip() + "\n"
        head = head.rstrip()
        if head.endswith("}"):
            head += ","
        text = head + "\n" + "\n".join(block) + "\n  ]\n}\n"
        json.loads(text)                            # still valid JSON
        DATA.write_text(text)
        print("written", DATA)
