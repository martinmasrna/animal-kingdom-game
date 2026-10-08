"""Build export.json from a read of the workbench database.

Claude reads the artifact's `decks` collection with the ArtifactData tool (`list` with `out_dir`), which saves one JSON
file per deck; this script folds those files into export.json, the converter's input:

    .venv/bin/python tools/card-workbench/export.py results/<read dir>/decks
    .venv/bin/python tools/card-workbench/convert.py
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).parent


def main(read_dir: str) -> None:
    out = {"_comment": "Snapshot of the card workbench database (https://claude.ai/artifact/4LbvDkhN1qawhdc3f4dcQU), "
                       "the source of truth for the card lists. Regenerate from the workbench; never edit by hand.",
           "decks": {}}
    for f in sorted(pathlib.Path(read_dir).glob("*.json")):
        doc = json.loads(f.read_text())
        d = doc.get("data", doc)
        out["decks"][f.stem] = {"name": d["name"], "order": d.get("order"), "precon": d.get("precon", True),
                                "cards": d["cards"]}
    (HERE / "export.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{sum(len(v['cards']) for v in out['decks'].values())} cards in {len(out['decks'])} decks")


if __name__ == "__main__":
    main(sys.argv[1])
