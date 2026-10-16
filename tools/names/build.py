"""Build the name-picking page: every candidate for each card as a list, two taps per name (Shelf, This is it), Nope hides it.

    .venv/bin/python tools/names/build.py BRIEF.json POOL.txt [POOL.txt ...] --out DIR

BRIEF.json is a list of cards: {"id", "title", "meta", "effect", "who", "img"} (img a path under DIR, e.g. art/<id>.webp;
copy the webp from animal_kingdom/web/static/art/ into DIR/art/). Each POOL.txt has one line per card:
    <card id>: name1; name2; ...
Names already in the game, famous characters of the same kind, verbatim Slovak words, duplicates across pools and
anything unpronounceable are dropped. DIR/placeholders.html is the page (publish it as an artifact with DIR as root and
the art files in `files`, capabilities {"db": {}}); DIR/key.json records which pool each name came from, never shown
on the page. Shelf names go on a card only through the brief's "shelf" list, by judgment, never on every card.
"""
import argparse, json, random, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CLASH = {"bagheera", "akela", "shere khan", "baloo", "simba", "nala", "mufasa", "scar", "ghost", "nymeria", "white fang",
         "balto", "buck", "sirius", "hedwig", "abu", "rafiki", "zazu", "pumbaa", "timon", "kaa", "hathi", "raksha", "bigwig",
         "hazel", "fiver", "reynard", "nevermore", "moby dick", "jaws", "nemo", "dory", "marlin", "flipper", "willy", "dumbo",
         "bambi", "thumper", "tarka", "mowgli", "tigger", "hobbes", "garfield", "pikachu", "elara", "elias", "ragnaros",
         "sylvanas", "geralt", "ciri", "marcus chen"}
SLOVAK_HINT = re.compile(r"[čšžťďňľáäéíóôúýČŠŽŤĎŇĽ]")


def taken_names():
    from animal_kingdom.web.news import load_cards
    return {c.name.lower() for c in load_cards().values() if not c.name.startswith("[")}


def load_pool(path, tag):
    out = {}
    for line in Path(path).read_text().splitlines():
        if ":" not in line:
            continue
        card, names = line.split(":", 1)
        out[card.strip().strip("-").strip()] = [(n.strip(), tag) for n in names.split(";") if n.strip()]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief")
    ap.add_argument("pools", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    brief = json.loads(Path(a.brief).read_text())
    pools = [load_pool(p, chr(65 + i)) for i, p in enumerate(a.pools)]
    taken = taken_names()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    random.seed(2026); cards = []; key = {}
    for c in brief:
        seen = set(); names = []
        for pool in pools:
            for n, t in pool.get(c["id"], []):
                k = re.sub(r"\s+", " ", n).strip(); lk = k.lower()
                if not k or lk in seen or lk in taken or lk in CLASH or SLOVAK_HINT.search(k):
                    continue
                if len(k) > 24 or not re.search(r"[aeiouy]", lk):
                    continue
                seen.add(lk); names.append((k, t))
        for n in c.get("shelf", []):
            if n.lower() not in seen:
                names.append((n, "S")); seen.add(n.lower())
        random.shuffle(names)
        key[c["id"]] = [{"name": n, "pool": t} for n, t in names]
        cards.append(dict(id=c["id"], title=c["title"], meta=c["meta"], effect=c["effect"], who=c["who"], img=c["img"],
                          names=[n for n, t in names], fromShelf=[n for n, t in names if t == "S"]))
    (out / "key.json").write_text(json.dumps(key, indent=1, ensure_ascii=False))
    page = (Path(__file__).parent / "template.html").read_text().replace("__CARDS__", json.dumps(cards, ensure_ascii=False))
    (out / "placeholders.html").write_text(page)
    print({c["id"]: len(c["names"]) for c in cards}, "total", sum(len(c["names"]) for c in cards))


if __name__ == "__main__":
    main()
