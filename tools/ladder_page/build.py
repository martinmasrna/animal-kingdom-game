"""The league's decks page, Martin's one permanent page of every list on the live ladder (Martin, 2026-10-26: "we can't
re-make it day after day"): https://claude.ai/artifact/DNUUrswYZgpoFhSNYALyQr. Each archetype a band (collapsible),
its lists drawn as the game draws a deck, each list's strongest bot rating, a deck code to copy, a list moved to another
archetype or a new one, a deck code pasted in.

The archetypes come from animal_kingdom/data/archetypes.json, the source of truth; a list the file doesn't name sits
with the named list it shares 24 or more cards with (an evolved child beside its parent). Moves, names and pasted decks
made on the page live in its database until the next rebuild folds them into the file: read them first (the page's
`names`, `lists` and `added` collections), change the file, then clear them.

Run from the game repo after the cards or the pool change:
  node tools/ladder_page/extract_strips.mjs          # the deck-list styles and every card's art, from the current client
  .venv/bin/python tools/ladder_page/build.py        # the page, from the live pool and ladder: results/ladder_page/page.html
then publish that file to the URL above (never as a new artifact)."""
from __future__ import annotations

import collections
import json
import re
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SERVER = "https://animal-kingdom.fly.dev"
OUT = REPO / "results" / "ladder_page"
STATIC = REPO / "animal_kingdom" / "web" / "static"
NEAR = 24   # cards shared with a named list for an unnamed one to join its archetype


def get(path: str, key: str | None = None):
    req = urllib.request.Request(SERVER + path, headers={"X-AK-League-Key": key} if key else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main() -> None:
    key = json.load(open(REPO / "results" / "oauth.json"))["AK_LEAGUE_KEY"]
    # a renamed card reads as its successor, as the client reads it (cardnums.js SUCCESSOR)
    succ = dict(re.findall(r"(\w+): '(\w+)'", re.search(r"SUCCESSOR = \{([^}]*)\}", (STATIC / "cardnums.js").read_text()).group(1)))
    lists = {d["slug"]: [succ.get(c, c) for c in d["list"]] for d in get("/api/league/pool", key)["decks"]}
    top: dict[str, int] = {}
    for r in get("/api/leaderboard")["rows"]:
        if r.get("bot") and r.get("deck"):
            top[r["deck"]] = max(top.get(r["deck"], 0), int(str(r["rating"]).rstrip("?")))
    named = json.load(open(REPO / "animal_kingdom" / "data" / "archetypes.json"))["archetypes"]
    gid = lambda name: re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "group"
    at = {s: gid(a["name"]) for a in named for s in a["lists"] if s in lists}
    names = {gid(a["name"]): a["name"] for a in named}
    shared = lambda a, b: sum((collections.Counter(a) & collections.Counter(b)).values())
    for s in lists:
        if s not in at:
            near = max((x for x in lists if x in at), key=lambda x: shared(lists[s], lists[x]), default=None)
            at[s] = at[near] if near and shared(lists[s], lists[near]) >= NEAR else "__new_" + s
            if at[s].startswith("__new_"):
                names[at[s]] = ""
    best = collections.defaultdict(int)
    for s, g in at.items():
        best[g] = max(best[g], top.get(s, 0))
    order_g = sorted(best, key=lambda g: -best[g])
    groups = [{"id": g, "n": i + 1, "name": names.get(g, "")} for i, g in enumerate(order_g)]
    order = sorted(lists, key=lambda s: (order_g.index(at[s]), -top.get(s, 0)))

    strips = json.load(open(OUT / "strips.json"))
    nums = (STATIC / "cardnums.js").read_text().replace("export const", "const")
    code = re.sub(r"^import .*$", "", (STATIC / "deckcode.js").read_text(), flags=re.M).replace("export function", "function")
    meta = {k: {**v, "id": k, "status": "collectible"} for k, v in strips["meta"].items()}
    inherit = ";".join(f"{k}:{v}" for k, v in strips["inherit"].items()) + ";" + ";".join(f"{k}:{v}" for k, v in strips["root"])
    css = strips["css"].replace("* { box-sizing: border-box; margin: 0px; padding: 0px; }", ".deck * { box-sizing: border-box; margin: 0; padding: 0; }")
    data = {"groups": groups, "order": order, "variant": {s: at[s] for s in lists}, "initial": at, "lists": lists, "rating": top}
    page = (Path(__file__).parent / "template.html").read_text()
    for k, v in {"__FONTS__": strips["fontText"], "__GAMECSS__": css, "__INHERIT__": inherit, "__DECKCODE__": nums + "\n" + code,
                 "__DATA__": json.dumps(data), "__ART__": json.dumps(strips["art"]), "__CHALK__": json.dumps(strips["chalk"]),
                 "__META__": json.dumps(meta)}.items():
        page = page.replace(k, v)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "page.html").write_text(page)
    missing = sorted({c for l in lists.values() for c in l} - set(strips["art"]))
    print(f"{len(lists)} lists in {len(groups)} archetypes, {len(page) // 1024} KB; cards without art: {missing or 'none'}")


if __name__ == "__main__":
    main()
