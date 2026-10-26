"""Rename card ids in the design sandbox to match the game repo's renamed ids.

    python3 tools/rename_design_ids.py [DESIGN_REPO] [--apply]

Dry run by default. With --apply it renames, by `git mv`, every file whose name is an old id in the folders that hold
per-card files (cards/, cards/bar/thumbs/, cards/research/timelines/, cards/research/links/, rarity2/masks/), and
rewrites the `card` field of cards/bar/manifest.jsonl and the ids in cards/true-names.md. Attempt files that only
start with an id (cards/bar/r1/, cards/old/) are left alone: the manifest names them by attempt id.
"""
import json
import os
import re
import subprocess
import sys

RENAME = {
    "guard_hornet": "guard_wasp", "aristocrats_legend_cuckoo": "cuckoo_legend",
    "aristocrats_legend_sloth": "sloth_legend", "canines_legend_leopard": "leopard_legend",
    "canines_legend_wolf": "wolf_legend", "gray_wolf": "jackal", "red_wolf": "dhole", "dire_wolf": "wolf",
    "raccoon_dog": "coyote", "dog": "street_dog", "house_cat": "alley_cat",
    "fish_legend_jellyfish": "jellyfish_legend", "fish_legend_tuna": "tuna_legend",
    "fish_legend_manta_ray": "manta_ray_legend", "fish_legend_piranha": "piranha_legend",
    "food_aggro_legend_repeat": "capybara_legend", "food_aggro_legend_refill": "rodent", "rat_king": "rat_legend",
    "food_otk_legend_squirrel": "squirrel_legend", "food_otk_legend_honey_badger": "honey_badger_legend",
    "food_otk_legend_octopus": "chameleon_legend", "egg_control_legend_raven": "raven_legend", "omen": "swan_legend",
    "stoop": "hawk", "king_cobra": "cottonmouth", "goliath": "python", "handlock_legend_baboon": "baboon_legend",
    "handlock_legend_butterfly": "butterfly_legend", "handlock_legend_eagle": "eagle_legend", "bulwark": "rhinoceros_legend",
    "giants_legend_oxpecker": "oxpecker_legend", "hoofed_legend_wildebeest": "wildebeest_legend",
    "hoofed_legend_boar": "boar_legend", "hoofed_legend_zebra": "zebra_legend", "hoofed_legend_giraffe": "giraffe_legend",
    "alpha": "fox_legend", "handlock_legend_butterfly_2": "butterfly_legend_caterpillar",
    "handlock_legend_butterfly_3": "butterfly_legend_chrysalis", "handlock_legend_butterfly_4": "butterfly_legend_butterfly",
    "handlock_legend_butterfly_5": "butterfly_legend_monarch", "handlock_legend_eagle_mate": "eagle_legend_2",
}
FOLDERS = ["cards", "cards/bar/thumbs", "cards/research/timelines", "cards/research/links", "rarity2/masks"]
EXTS = {".png", ".jpg", ".md", ".json"}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    root = os.path.abspath(args[0] if args else os.path.expanduser("~/Work/fun/animal-kingdom-design"))
    moves = []
    for folder in FOLDERS:
        d = os.path.join(root, folder)
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            stem, ext = os.path.splitext(f)
            if stem in RENAME and ext in EXTS and os.path.isfile(os.path.join(d, f)):
                dst = os.path.join(d, RENAME[stem] + ext)
                if os.path.exists(dst):
                    sys.exit(f"would overwrite {dst}")
                moves.append((os.path.join(d, f), dst))
    for src, dst in moves:
        print("mv", os.path.relpath(src, root), "->", os.path.relpath(dst, root))
    manifest = os.path.join(root, "cards/bar/manifest.jsonl")
    lines, n = [], 0
    for line in open(manifest):
        r = json.loads(line)
        old = r.get("card")
        if old in RENAME:
            was = f'"card": {json.dumps(old)}'
            assert was in line, line[:80]
            line = line.replace(was, f'"card": {json.dumps(RENAME[old])}', 1)
            n += 1
        lines.append(line)
    names = os.path.join(root, "cards/true-names.md")
    text = open(names).read()
    new_text = text
    for o, nw in RENAME.items():
        new_text = re.sub(r"(?<![\w-])" + o + r"(?![\w-])", nw, new_text)
    print(f"{len(moves)} files, {n} manifest records, true-names.md {'changes' if new_text != text else 'unchanged'}")
    if not apply:
        print("dry run; pass --apply to do it")
        return
    for src, dst in moves:
        try:
            subprocess.check_call(["git", "-C", root, "mv", src, dst])
        except subprocess.CalledProcessError:
            os.rename(src, dst)
    open(manifest, "w").write("".join(lines))
    open(names, "w").write(new_text)
    print("done")


main()
