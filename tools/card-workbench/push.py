"""Write the repo's card list into the card workbench, the page Martin browses the cards on.

The repo is the source of truth: decks.json holds the card lists, convert.py builds cards.json from it, and this
script writes one file per deck for the workbench database, which Claude then sets with the ArtifactData tool
(a `batch` of `set` writes to the `decks` collection, each pinned to the version last read):

    .venv/bin/python tools/card-workbench/push.py OUT_DIR

Nothing flows back: a change made on the workbench page is read there and applied to decks.json by hand.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent


def main(out_dir: str) -> None:
    decks = json.loads((HERE / "decks.json").read_text())["decks"]
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for slug, deck in decks.items():
        (out / f"{slug}.json").write_text(json.dumps(deck, ensure_ascii=False, indent=1))
    print(f"{sum(len(d['cards']) for d in decks.values())} cards in {len(decks)} decks -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
