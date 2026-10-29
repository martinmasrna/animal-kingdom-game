"""The sheet: the facts about one card an agent looks up before the card reaches Martin.

Agents designing cards reasoned in prose from memory and missed what a lookup would have shown: a keyword's actual
timing, a card already in the pool doing the same thing, the anchor the number should sit against, how many neighbours
a crossroad has, an earlier call of Martin's on the same animal, text that doesn't fit the card. Half the cards he
rejected in three weeks failed one of those (knowledge/card-design-diagnosis-2026-10-25.md). This prints them, and
nothing else: no verdict, no score. The agent reads the sheet; Martin sees the card.

    .venv/bin/python tools/cards/check.py ID [--text "..."]        an existing card, or another wording of it
    .venv/bin/python tools/cards/check.py --new "Rat" --rarity C --str 3 --tag Rodent --text "Roar: ..." [--species S]
    options: --no-fit (skip the browser measurement of the text), --play (place an existing card in a scratch game)

Sections: card, keywords (the registry's ruling for every keyword and term in the text), pool (the animal, the tag, the
nearest effects), anchors (the cards at this rarity and strength, what can cover the body), record (every line of the design record that names the animal), grid (map_b's neighbours
and regions at the places the card will stand), text (lines on the real card at every width the client draws it),
play (a placement in a scratch game, for a card the engine knows; otherwise the one fact that it isn't in the engine).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from animal_kingdom.engine.cards import load_cards  # noqa: E402
from animal_kingdom.engine.maps import load_map  # noqa: E402
from animal_kingdom.engine.resources import load_bundled_json  # noqa: E402

DESIGN = ROOT / "docs" / "design"
KEYWORDS_MD = ROOT / "docs" / "rules" / "keywords.md"
LEVELS = Path(__file__).parent / "levels.json"
FIT = Path(__file__).parent / "fit.mjs"
RARITY = {"C": "common", "R": "rare", "L": "legendary", "common": "common", "rare": "rare", "legendary": "legendary"}

# The registry's sections, found by the term in the text. Terms that are not keywords (Discard, Scout, "has +"/"give +")
# have sections too; their heading starts with the key.
TERM_PATTERNS = [
    (r"\bFlight\b", "Flight"), (r"\bReach\b", "Reach"), (r"\b[Rr]oams?\b", "Roam"), (r"\bArmor\b", "Armor"),
    (r"\bStealth\b", "Stealth"), (r"\bSpikes\b", "Spikes"), (r"\bPoison\b", "Poison"), (r"\bTitan\b", "Titan"),
    (r"\bHungry\b", "Hungry"), (r"\bFlee\b", "Flee"), (r"\bWild\b", "Wild"), (r"\bApex Predator\b", "Apex Predator"),
    (r"\bRoar\b", "Roar"), (r"\bDawn\b|\bDusk\b", "Dawn and Dusk"), (r"\bremoved?\b|\bleaves the board\b", "Leaving the board"),
    (r"\bCosts \d+ food\b", "Costs X food"), (r"\+\d+ strength|[Ss]trength \d|become strength", "Strength modifiers"),
    (r"\b[Dd]iscards?\b", "Discard"), (r"\bScout\b", "Scout"),
]
# The species (the animal of a legendary) is display data the engine's Card drops; read it off the raw records.
SPECIES = {r["id"]: r.get("species", "") for r in load_bundled_json("cards" + ".json")["cards"]}


def sp(card) -> str:
    return SPECIES.get(card.id, "")


STOP = set("a an the of to your you it its this that and or in on for each with when whenever at end start turn next "
           "is are be by from as if into up one all any other another another's animals animal card cards strength "
           "roar dusk dawn food more less than".split())


def out(label: str, lines) -> None:
    lines = [lines] if isinstance(lines, str) else list(lines)
    if not lines:
        lines = ["none"]
    print(f"{label:<10}{lines[0]}")
    for ln in lines[1:]:
        print(f"{'':<10}{ln}")


def card_line(c: dict) -> str:
    tags = " ".join(c["tags"]) or "no tag"
    return f"{c['name']} · {c['rarity']} · {c['str']} · {tags}" + (f" · {c['species']}" if c.get("species") and c["species"] != c["name"] else "")


def one_line(card) -> str:
    s = "*" if card.is_dynamic else card.base_strength
    return f"{card.name or sp(card)} {card.rarity[0].upper()}{s}: {card.text or '(vanilla)'}"


# ----------------------------------------------------------------------------------------------------------- sections

def keywords_section(text: str) -> list[str]:
    md = KEYWORDS_MD.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    for m in re.finditer(r"^### (.+?)\s*(?:\(.*?\))?\s*(?:\*\(.*?\)\*)?\s*$\n(.*?)(?=^### |^## |\Z)", md, re.M | re.S):
        sections[m.group(1).strip()] = m.group(2).strip()
    lines = []
    for pat, key in TERM_PATTERNS:
        if re.search(pat, text):
            body = sections.get(key) or next((v for k, v in sections.items() if k.startswith(key)), "")
            body = re.sub(r"\s+", " ", body.split("\n\n")[0]) if key not in ("Strength modifiers",) else re.sub(r"\s+", " ", body)
            lines.append(f"{key}: {body}")
    return lines


def pool_section(cards: dict, c: dict) -> list[str]:
    lines = []
    name = c["name"].lower()
    species = (c.get("species") or c["name"]).lower()
    same_animal = [k for k in cards.values() if k.id != c.get("id") and species and
                   sp(k).lower() == species or (k.name or "").lower() == name]
    lines.append("animal already in the pool: " + ("" if same_animal else "no"))
    lines += [f"  {k.id} ({k.status}) {one_line(k)}" for k in same_animal]
    if not same_animal:
        from collections import Counter
        habs = Counter(k.habitat for k in cards.values() if k.collectible and k.habitat)
        lines.append("habitats the collectible pool uses: " + ", ".join(f"{h} {n}" for h, n in habs.most_common())
                     + "; the card's is the animal's real, well-known home")
    for tag in c["tags"]:
        family = sorted((k for k in cards.values() if tag in k.tags and k.status in ("collectible", "reserve") and k.id != c.get("id")),
                        key=lambda k: (99 if k.is_dynamic else k.base_strength, k.name))
        lines.append(f"{tag} ({len(family)}):")
        lines += [f"  {one_line(k)}" + (" [reserve]" if k.status == "reserve" else "") for k in family]
    words = {w for w in re.findall(r"[a-z]+", c["text"].lower()) if w not in STOP and len(w) > 2}
    scored = []
    for k in cards.values():
        if k.id == c.get("id") or k.status not in ("collectible", "reserve") or not k.text:
            continue
        kw = {w for w in re.findall(r"[a-z]+", k.text.lower()) if w not in STOP and len(w) > 2}
        shared = words & kw
        if len(shared) >= 2:
            scored.append((len(shared) / max(1, len(words | kw)), k))
    scored.sort(key=lambda t: -t[0])
    lines.append("nearest effects (shared words):")
    lines += [f"  {one_line(k)}" + (" [reserve]" if k.status == "reserve" else "") for _, k in scored[:8]] or ["  none share two words"]
    return lines


def anchors_section(cards: dict, c: dict) -> list[str]:
    lines = []
    text = c["text"]
    lines.append("Lion 7 (vanilla, ground), Eagle 5 (vanilla, Flight); the pool below is the reference, by rarity and strength")
    if re.search(r"\bdraw (a|\d)", text, re.I):
        lines.append("ledger: the Draw action is 2 cards for one action; this card's draw replaces the card played, the action is still spent")
    s = c["str"]
    if isinstance(s, int):
        rar = c["rarity"]
        same = sorted((k for k in cards.values() if k.collectible and k.rarity == rar and not k.is_dynamic
                       and k.base_strength == s and k.id != c.get("id")), key=lambda k: k.name)
        lines.append(f"{rar}s at {s} ({len(same)}):")
        lines += [f"  {one_line(k)}" for k in same]
        for d in (-1, 1):
            near = sorted(k.name for k in cards.values() if k.collectible and k.rarity == rar and not k.is_dynamic and k.base_strength == s + d)
            lines.append(f"{rar}s at {s + d}: " + (", ".join(near) or "none"))
        pool = [k for k in cards.values() if k.collectible and not k.is_dynamic]
        over = [k for k in pool if k.base_strength > s]
        lines.append(f"covered by {len(over)} of {len(pool)} collectible cards on printed strength"
                     + (" (strength 10: nothing covers it)" if s >= 10 else ""))
    return lines


def record_section(c: dict) -> list[str]:
    names = {c["name"], c.get("species") or ""} - {""}
    pat = re.compile(r"(?<![\w-])(" + "|".join(re.escape(n) for n in names) + r")s?(?![\w-])", re.I)
    lines = []
    files = sorted(DESIGN.glob("*.md")) + sorted((DESIGN / "societies").glob("*.md"))
    for f in files:
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(ln):
                m = pat.search(ln)
                start = max(0, m.start() - 110)
                snippet = ln[start:m.end() + 130].strip()
                lines.append(f"{f.relative_to(ROOT)}:{i}: {'…' if start else ''}{snippet}{'…' if m.end() + 130 < len(ln) else ''}")
    if c.get("id") and LEVELS.exists():
        for col, v in json.loads(LEVELS.read_text(encoding="utf-8")).get(c["id"], {}).items():
            if isinstance(v, dict) and (v.get("note") or v.get("lv") in ("locked", "fine", "problem")):
                lines.append(f"levels.json {col}: {v.get('lv', 'draft')}" + (f" · {v['note']}" if v.get("note") else ""))
    return lines[:40] + ([f"… {len(lines) - 40} more lines"] if len(lines) > 40 else [])


def grid_section(c: dict) -> list[str]:
    gm = load_map("map_b")
    spots = [("home back corner", "1,1"), ("home den front, middle", "1,2"), ("board centre", "3,2"),
             ("edge, middle column", "3,1"), ("enemy den front, middle", "5,2"), ("enemy corner", "5,3")]
    lines = ["5×3 grid; dens behind column 1 (yours) and column 5; regions are the 2×2 squares (flanks 10 food, centre 15)"]
    per = re.search(r"\+(\d+) strength for each adjacent", c["text"], re.I)
    for label, cr in spots:
        ns = gm.neighbors(cr)
        regs = [r.id for r in gm.regions.values() if cr in r.corners]
        den = "on your den front" if cr in gm.hq_front("A") else "on the enemy den front" if cr in gm.hq_front("B") else ""
        extra = ""
        if per and isinstance(c["str"], int):
            extra = f" · +{int(per.group(1))} each: at most {c['str'] + int(per.group(1)) * len(ns)}"
        lines.append(f"{label} ({cr}): {len(ns)} neighbours {', '.join(ns)} · regions {', '.join(regs)}" + (f" · {den}" if den else "") + extra)
    if re.search(r"\badjacent\b|\bnext to\b|for each", c["text"], re.I):
        lines.append("an 'adjacent' payoff has 2 slots in a corner, 3 on an edge, 4 in the centre; the den is not a neighbour")
    return lines


def text_section(c: dict, fit: bool) -> list[str]:
    n = len(c["text"])
    lines = [f"{n} characters"]
    if not fit:
        return lines + ["not measured (--no-fit)"]
    node = shutil.which("node")
    if not node or not FIT.exists():
        return lines + ["not measured: node or fit.mjs missing"]
    try:
        r = subprocess.run([node, str(FIT), json.dumps({"id": c.get("id") or "new", "name": c["name"], "rarity": c["rarity"],
                                                        "str": c["str"], "text": c["text"], "tags": c["tags"]})],
                           capture_output=True, text=True, timeout=120, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return lines + ["not measured: the browser took over two minutes"]
    if r.returncode:
        return lines + [f"not measured: {(r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else 'fit.mjs failed'}"]
    res = json.loads(r.stdout.strip().splitlines()[-1])
    worst = max(res.values())
    return lines + [f"{'fits' if worst <= 3 else 'does not fit'}: " + ", ".join(f"{k}px {v} lines" for k, v in res.items()) + " (limit 3)"]


def play_section(cards: dict, c: dict) -> list[str]:
    cid = c.get("id")
    if not cid or cid not in cards or cards[cid].status not in ("collectible", "reserve"):
        return ["not in the engine: wire it (effects.py, engine_rs) into a scratch build before any claim about how it plays; until then that claim is prose",
                "then: .venv/bin/python tools/cards/check.py ID --play, and ./report 200 --deck <its deck> for a bot read (not a verdict)"]
    from animal_kingdom.engine import rules
    from animal_kingdom.engine.actions import SKIP, ChoiceAction, PlaceAction
    from animal_kingdom.engine.config import Config
    from animal_kingdom.engine.state import GameState, UnitInstance
    from animal_kingdom.engine.strength import effective_strength

    def put(state, cr, card_id, owner):
        u = UnitInstance(card_id, owner, state.new_iid(), placed_on_turn=state.turn_counter)
        state.stamp_played(u)
        state.board.setdefault(cr, []).append(u)
        return u

    def snapshot(state):
        tops = {cr: f"{state.cards[u.card_id].name}({u.owner}){effective_strength(state, u)}" for cr, u in
                ((cr, state.top_unit(cr)) for cr in sorted(state.board)) if u}
        return tops, dict(state.food), {p: [u.card_id for u in state.hands[p]] for p in "AB"}

    from animal_kingdom.decks import load_premade_deck
    from animal_kingdom.engine.resources import load_bundled_json
    starters = [d["slug"] for d in load_bundled_json("decklists.json")["decks"] if d.get("starter") and cid in d["cards"]]
    deck_a = [k for k in load_premade_deck(starters[0] if starters else "den_rush") if k != cid]
    lines = []
    # One scratch position: you hold the card over your own starter deck (or Den Rush's); your Lion stands on the den
    # front with a Mouse of yours beside it, so family and adjacency effects have something to see; an enemy Lemming (1)
    # stands ahead to be covered and an enemy Lion (7) behind it.
    board = [("1,2", "lion", "A"), ("1,1", "mouse", "A"), ("2,2", "lemming", "B"), ("3,2", "lion", "B")]
    scenario = ", ".join(f"{'your' if o == 'A' else 'enemy'} {cards[k].name} ({cards[k].base_strength}) at {cr}" for cr, k, o in board)
    for _ in (1,):
        state = GameState(load_map("map_b"), cards, Config.default(), board={}, hands={"A": [], "B": []},
                          decks={"A": deck_a, "B": ["lion"] * 10}, remove_pile=[], food={"A": 20, "B": 20},
                          current="A", first_player="A", turn_counter=4)
        for cr, k, owner in board:
            if k in cards:
                put(state, cr, k, owner)
        state.add_to_hand("A", cid)
        legal = [a for a in rules.legal_actions(state) if isinstance(a, PlaceAction) and a.card_id == cid]
        lines.append(f"scenario: {scenario}; you hold {cards[cid].name} with 20 food and two actions, over "
                     f"{'the ' + starters[0] + ' deck' if starters else 'the Den Rush deck'}")
        lines.append("legal places for it: " + (", ".join(a.target[1] if a.target[0] == 'cr' else 'enemy den' for a in legal) or "none"))
        pick = next((a for a in legal if a.target == ("cr", "2,2")), None) or next((a for a in legal if a.target == ("cr", "2,1")), None) or (legal[0] if legal else None)
        if not pick:
            continue
        before = snapshot(state)
        rules.apply_action(state, pick)
        asked = []
        while state.pending and state.pending.get("options"):
            opts = [o for o in state.pending["options"] if o != SKIP]
            asked.append(f"asked to choose among {len(opts)}: {opts[:6]}")
            rules.apply_action(state, ChoiceAction(opts[0] if opts else SKIP))
        after = snapshot(state)
        lines.append(f"placed on {pick.target[1]}" + (": " + "; ".join(asked) if asked else ""))
        changed = {cr: (before[0].get(cr), after[0].get(cr)) for cr in set(before[0]) | set(after[0]) if before[0].get(cr) != after[0].get(cr)}
        lines.append("board: " + ("; ".join(f"{cr} {a or 'empty'} → {b or 'empty'}" for cr, (a, b) in sorted(changed.items())) or "no other change"))
        if before[1] != after[1]:
            lines.append(f"food: {before[1]} → {after[1]}")
        if before[2] != after[2]:
            lines.append(f"hands: {before[2]} → {after[2]}")
        # The turn ends on its own after the second action; a Dusk effect shows up here.
        if not rules.is_terminal(state) and state.player_to_act() == "A":
            from animal_kingdom.engine.actions import DrawAction
            rules.apply_action(state, DrawAction())
            end = snapshot(state)
            if end != after:
                lines.append(f"after your turn ends (Dusk): board {', '.join(f'{cr} {v}' for cr, v in end[0].items())} · food {end[1]} · hands {end[2]}")
    return lines


# --------------------------------------------------------------------------------------------------------------- main

def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("id", nargs="?", help="an existing card's id")
    ap.add_argument("--new", metavar="NAME", help="a proposed card's animal (display name)")
    ap.add_argument("--species", help="the animal of a legendary (defaults to NAME)")
    ap.add_argument("--rarity", help="C, R or L")
    ap.add_argument("--str", dest="strength", type=int)
    ap.add_argument("--tag", action="append", default=[], help="a tag (repeatable)")
    ap.add_argument("--text", default="")
    ap.add_argument("--no-fit", action="store_true", help="skip the browser measurement of the text")
    ap.add_argument("--play", action="store_true", help="place an existing card in a scratch game and print what changed")
    a = ap.parse_args(argv)

    cards = load_cards()
    if a.id:
        if a.id not in cards:
            raise SystemExit(f"no card {a.id!r}")
        k = cards[a.id]
        c = {"id": k.id, "name": k.name or sp(k), "species": sp(k), "rarity": k.rarity, "str": "*" if k.is_dynamic else k.base_strength,
             "tags": sorted(k.tags), "text": k.text, "kws": sorted(k.keywords), "status": k.status}
        if a.text is not None:  # another wording on the same card
            c["text"] = a.text
    elif a.new:
        if not a.rarity or a.strength is None:
            raise SystemExit("--new needs --rarity and --str")
        from tools.cards.hq import KEYWORD  # the same reading of printed keywords as the card table
        c = {"id": None, "name": a.new, "species": a.species or a.new, "rarity": RARITY[a.rarity], "str": a.strength,
             "tags": a.tag, "text": a.text, "kws": [m.group(1) for m in KEYWORD.finditer(a.text)], "status": "proposed"}
    else:
        ap.error("give a card id or --new")

    out("card", card_line(c) + (f" · {c['status']}" if c["status"] != "collectible" else ""))
    out("", f'"{c["text"]}"' if c["text"] else "(vanilla)")
    out("keywords", keywords_section(c["text"]))
    out("pool", pool_section(cards, c))
    out("anchors", anchors_section(cards, c))
    out("record", record_section(c))
    out("grid", grid_section(c))
    out("text", text_section(c, fit=not a.no_fit))
    out("play", play_section(cards, c) if (a.play or not c.get("id")) else ["--play places it in a scratch game"])


if __name__ == "__main__":
    main()
