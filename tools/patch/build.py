"""Build a patch's notes for the game's Patch notes screen.

    .venv/bin/python tools/patch/build.py 0.0.2 [--date "22 November 2026"]
    .venv/bin/python tools/patch/build.py --check        what changed since the last patch, nothing written

A patch is what changed in the game for a player since the last patch: the rules, as words Martin redlined, and every
card and hero power, as the cards before and after. Its words live in animal_kingdom/web/patches/VERSION.md (a "## Rules"
list); the cards come from diffing the game now against the snapshot the last patch left in tools/patch/snapshots/.
Writes static/patches/VERSION.json (what the screen shows), adds VERSION to static/patches/index.json (newest first),
and snapshots the game as VERSION.json for the next patch. A removed card's figure is kept in static/hex/fig so the
patch can show it.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from animal_kingdom.game import LEADERS, Config, load_cards, power_price  # noqa: E402

WEB = ROOT / "animal_kingdom" / "web"
OUT = WEB / "static" / "patches"
SNAPS = Path(__file__).resolve().parent / "snapshots"
FIGS = WEB / "static" / "hex" / "figs.js"


def snapshot() -> dict:
    """The game as a player sees it: every collectible card and every leader's ability."""
    figs = json.loads(re.search(r"FIGS = (\{.*\})", FIGS.read_text()).group(1))
    cards = {c.id: {"id": c.id, "name": c.name, "rarity": c.rarity, "str": None if c.is_dynamic else c.base_strength,
                    "text": c.text, "kw": sorted(c.keywords), "mana": c.cost, "fig": figs.get(c.id)}
             for c in load_cards().values() if c.status == "collectible"}
    leaders = {lid: {"id": lid, "passive": passive, "power": power, "mana": power_price(lid, Config()) if power else None}
               for lid, (passive, power) in LEADERS.items()}
    return {"cards": cards, "leaders": leaders}


def last_snapshot(version: str | None = None) -> tuple[str, dict]:
    """The snapshot the patch `version` is measured against: the newest patch before it (rebuilding one skips itself)."""
    index = json.loads((OUT / "index.json").read_text()) if (OUT / "index.json").exists() else []
    index = [v for v in index if v != version]
    name = index[0] if index else "base"
    return name, json.loads((SNAPS / f"{name}.json").read_text())


def rules_of(version: str) -> list[str]:
    """The bullets under "## Rules" in the patch's words, CriticMarkup refused (an unresolved redline)."""
    text = (WEB / "patches" / f"{version}.md").read_text()
    if re.search(r"\{(\+\+|--|~~|==|>>)", text):
        sys.exit(f"patches/{version}.md still holds redline markup: resolve it first")
    m = re.search(r"^## Rules\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return [ln[2:].strip() for ln in (m.group(1) if m else "").splitlines() if ln.startswith("- ")]


def abilities(L: dict) -> dict:
    """A leader's passive, power and the power's mana; a snapshot before 0.0.5 held one ability ({kind, text})."""
    if "kind" in L:
        return {"passive": L["text"] if L["kind"] == "passive" else None, "power": L["text"] if L["kind"] == "power" else None, "mana": L["mana"]}
    return {"passive": L["passive"], "power": L["power"], "mana": L["mana"]}


def abilities(L: dict) -> dict:
    """A leader's passive, power and the power's mana; a snapshot before 0.0.5 held one ability ({kind, text})."""
    if "kind" in L:
        return {"passive": L["text"] if L["kind"] == "passive" else None, "power": L["text"] if L["kind"] == "power" else None, "mana": L["mana"]}
    return {"passive": L["passive"], "power": L["power"], "mana": L["mana"]}


def abilities(L: dict) -> dict:
    """A leader's passive, power and the power's mana; a snapshot before 0.0.5 held one ability ({kind, text})."""
    if "kind" in L:
        return {"passive": L["text"] if L["kind"] == "passive" else None, "power": L["text"] if L["kind"] == "power" else None, "mana": L["mana"]}
    return {"passive": L["passive"], "power": L["power"], "mana": L["mana"]}


def diff(was: dict, now: dict) -> dict:
    keys = ("name", "str", "text", "mana")
    changed = [{"was": was["cards"][i], "now": c} for i, c in now["cards"].items()
               if i in was["cards"] and any(was["cards"][i][k] != c[k] for k in keys)]
    added = [c for i, c in now["cards"].items() if i not in was["cards"]]
    removed = [c for i, c in was["cards"].items() if i not in now["cards"]]
    powers = [{"was": was["leaders"][i], "now": L} for i, L in now["leaders"].items()
              if i in was["leaders"] and abilities(was["leaders"][i]) != abilities(L)]
    key = lambda c: (c["mana"], c["name"])
    changed.sort(key=lambda p: key(p["now"])); added.sort(key=key); removed.sort(key=key)
    return {"powers": powers, "changed": changed, "added": added, "removed": removed}


def keep_figures(removed: list[dict], since: str) -> None:
    """A removed card's figure stays where the piece looks for it, taken back from git if it was deleted."""
    import subprocess
    for c in removed:
        f = WEB / "static" / "hex" / "fig" / f"{c['id']}.webp"
        if f.exists() or not c.get("fig"):
            continue
        rev = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%H", "--", str(f.relative_to(ROOT))],
                             capture_output=True, text=True).stdout.strip()
        if rev:
            blob = subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}^:{f.relative_to(ROOT)}"], capture_output=True).stdout
            if blob:
                f.write_bytes(blob)
                print(f"kept the figure of the removed {c['name']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("version", nargs="?")
    ap.add_argument("--date", default=datetime.date.today().strftime("%-d %B %Y"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    since, was = last_snapshot(a.version)
    now = snapshot()
    d = diff(was, now)
    if a.check or not a.version:
        print(f"since {since}: {len(d['powers'])} hero powers, {len(d['changed'])} changed, {len(d['added'])} new, {len(d['removed'])} removed")
        for p in d["powers"]: print("  power", p["now"]["id"])
        for p in d["changed"]: print("  changed", p["now"]["name"], {k: (p["was"][k], p["now"][k]) for k in ("name", "str", "text", "mana") if p["was"][k] != p["now"][k]})
        for c in d["added"]: print("  new", c["name"])
        for c in d["removed"]: print("  removed", c["name"])
        return
    patch = {"version": a.version, "name": f"Patch {a.version}", "date": a.date, "rules": rules_of(a.version), **d}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{a.version}.json").write_text(json.dumps(patch, indent=1) + "\n")
    index = json.loads((OUT / "index.json").read_text()) if (OUT / "index.json").exists() else []
    (OUT / "index.json").write_text(json.dumps([a.version] + [v for v in index if v != a.version]) + "\n")
    SNAPS.mkdir(exist_ok=True)
    (SNAPS / f"{a.version}.json").write_text(json.dumps(now, indent=1) + "\n")
    keep_figures(d["removed"], since)
    print(f"Patch {a.version}: {len(patch['rules'])} rules, {len(d['powers'])} hero powers, {len(d['changed'])} changed, "
          f"{len(d['added'])} new, {len(d['removed'])} removed")


if __name__ == "__main__":
    main()
