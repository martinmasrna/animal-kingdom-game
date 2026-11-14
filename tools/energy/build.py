"""Build animal_kingdom/data/energy.json from table.py (and decks.py when it exists), and print the checks:
coverage, Martin's hand-set strengths, the shifted thresholds, the cost and strength spread, and where the costs differ
from his price piles.

    .venv/bin/python tools/energy/build.py
"""
import json, re, sys, collections
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import table

raw = json.loads((ROOT / "animal_kingdom/data/cards.json").read_text())["cards"]
by_id = {r["id"]: r for r in raw}
coll = [r for r in raw if r.get("status") == "collectible"]

# ---- coverage
missing = [r["id"] for r in coll if r["id"] not in table.T and r["id"] not in table.BENCH]
extra = [i for i in table.T if i not in by_id or by_id[i].get("status") != "collectible"]
assert not missing and not extra, (missing, extra)

def new_strength(r):
    e = table.T.get(r["id"])
    if e is None or e[0] is None:
        return r["base_strength"]
    return e[0]

# ---- Martin's hand-set strengths
P = json.loads((HERE.parent / "board/boards/prices.json").read_text())
S = json.loads((HERE.parent / "board/boards/strengths.json").read_text())
his = dict(S.get("strs", {})); his.update(P.get("strs", {}))
pile = {i: int(p["name"].split()[-1]) for p in P["piles"] for i in p["cards"]}
for i in pile:
    his.setdefault(i, by_id[i]["base_strength"])   # a card he priced, he looked at: its shown strength is his
bad = [(i, his[i], table.T[i][0]) for i in his if i in table.T and table.T[i][0] is not None and table.T[i][0] != his[i]]
print("strengths that differ from Martin's boards:", bad or "none")

# ---- thresholds: the same share of the pool as before
rules = dict(table.RULES)
from animal_kingdom.engine.config import Config
base_cfg = Config()
old = [r["base_strength"] for r in coll if isinstance(r["base_strength"], int)]
new = [new_strength(r) for r in coll if r["id"] in table.T and isinstance(new_strength(r), int)]
def share(vals, kind, t):
    return sum(1 for v in vals if (v <= t if kind == "max" else v >= t)) / len(vals)
shifted = {}
for field, (kind, cid) in table.THRESHOLDS.items():
    t_old = getattr(base_cfg, field)
    target = share(old, kind, t_old)
    t_new = min(range(0, 11), key=lambda t: (abs(share(new, kind, t) - target), abs(t - t_old)))
    shifted[field] = (t_old, t_new, round(target, 2), round(share(new, kind, t_new), 2))
    if t_new != t_old:
        rules[field] = t_new
rules["gorilla_min"] = 9    # the Gorilla is a 7 now: still two buffs away from its draw, as it was at 6
print("thresholds (old, new, share before, share now):", shifted)

# ---- the card overlay
cards = {}
changed_text = {}
for cid, entry in table.T.items():
    s, c = entry[0], (table.COST_LION2[cid] if table.SCALE == "lion2" else entry[1])
    opt = entry[2] if len(entry) > 2 else {}
    o = {"cost": c}
    if s is not None:
        o["strength"] = s
    text = opt.get("text")
    if text is not None:
        text = text.format(**{k: rules.get(k, getattr(base_cfg, k)) for k in ("cuckoo_legend_max",)})
    if "kw" in opt:
        o["keywords"] = opt["kw"]
    if "hungry" in opt:
        o["hungry"] = opt["hungry"]
    if text is not None:
        o["text"] = text
    cards[cid] = o
# printed thresholds follow the shifted numbers
for field, (kind, cid) in table.THRESHOLDS.items():
    t_old, t_new = shifted[field][0], shifted[field][1]
    if t_new == t_old or cid not in cards:
        continue
    text = cards[cid].get("text", by_id[cid].get("text", ""))
    if field == "capybara_small_max":
        text2 = text.replace(f"strength {t_old + 1} or more", f"strength {t_new + 1} or more")
    else:
        text2 = re.sub(rf"strength {t_old}\b", f"strength {t_new}", text, count=1)
    assert text2 != text, (cid, text)
    cards[cid]["text"] = text2
g = by_id["gorilla"].get("text", "")
cards["gorilla"]["text"] = g.replace("8 or more", "9 or more"); assert cards["gorilla"]["text"] != g
for cid, o in cards.items():
    if "text" in o and o["text"] != by_id[cid].get("text", ""):
        changed_text[cid] = (by_id[cid].get("text", ""), o["text"])
for tid, c in table.TOKEN_COST.items():
    c = c - 1 if table.SCALE == "lion2" else c
    assert by_id[tid]["status"] == "token", tid
    cards[tid] = {"cost": c}

decks = []
if (HERE / "decks.py").exists():
    import decks as D
    for k, (name, cover, lst) in enumerate(D.DECKS + [D.SWARM[table.SCALE]]):
        n = sum(lst.values())
        assert n == 30, (name, n)
        for cid, q in lst.items():
            assert cid in cards and cid not in table.TOKEN_COST, (name, cid)
            assert q <= (1 if by_id[cid]["rarity"] == "legendary" else 2), (name, cid, q)
        decks.append({"slug": f"energy_{k + 1}", "name": name, "cover": cover, "order": k + 1, "starter": True, "bot": True, "cards": lst})

out = {"_comment": "The energy prototype (ENERGY_PLAN.md). Built by tools/energy/build.py from tools/energy/table.py; the Costs board edits table values through tools/energy/edits.json.",
       "rules": rules, "cards": cards, "decks": decks, "benched": table.BENCH}
edits = HERE / "edits.json"       # Martin's changes on the Costs board, laid over the table
if edits.exists():
    e = json.loads(edits.read_text())
    out["rules"].update(e.get("rules", {}))
    for cid, o in e.get("cards", {}).items():
        out["cards"].setdefault(cid, {}).update(o)
(ROOT / "animal_kingdom/data/energy.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")

# ---- report
print(len(cards), "cards costed;", len(table.BENCH), "benched;", len(decks), "decks")
print("cost spread:", dict(sorted(collections.Counter(o["cost"] for i, o in cards.items() if i in table.T).items())))
print("strength spread:", dict(sorted(collections.Counter(new).items())))
diff = sorted((i, pile[i], cards[i]["cost"]) for i in pile if i in cards and cards[i]["cost"] != pile[i])
print(f"costs that differ from Martin's price piles ({len(diff)} of {len(pile)}):", diff)
print("texts changed:", len(changed_text))
for cid, (a, b) in sorted(changed_text.items()):
    print(f"  {cid}: {a!r} -> {b!r}")
