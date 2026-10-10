---
name: card-art
description: Make, repaint or review card art for Animal Kingdom - the idea per card agreed with Martin, one picture from the proven template with the six-painting reference sheet, a full-size check, Martin's review page, install. Use whenever the work is a card's painting - "card art", "paint the Savanna rares", "repaint X", "art round", "review page for art", reading art verdicts, installing a picked painting, or improving how art is made.
---

# Card art

Everything here has evidence behind it in `D/cards/research/findings.md` (`D` is `~/Work/fun/animal-kingdom-design/`): every image ever generated, the prompt it got, and Martin's reaction to it. A rule without evidence doesn't go in; a change to how art is made is tested on a few cards and goes in only when Martin's verdicts back it. What the art must achieve is `D/cards/art-principles.md`.

## What works

- **The animal is the hero.** Big, filling most of the card, a calm simple area behind it so its silhouette reads instantly. Never a landscape with a small animal in it.
- **The picture people carry of that animal, plus one hook no other card has.** What a player pictures when hearing the name, not an obscure behaviour: the big-eyed eagle-owl at dusk, the green viper with open fangs, the strawberry chipmunk.
- **One idea.** One animal, one moment. A second animal only when the card can't be read without it, and then small or partial; the effect shown by one simple device, if at all (the Jerboa's second hop, the Hornet pair).
- **A legendary's myth lives in the animal itself**, never only in the sky or in size.
- **An approved composition is kept.** To fix a liked picture, repaint only what is wrong (`edit.sh`: the sky, the eyes, the colour); never invent a new scene for it. To fix a wrong one, start fresh; never stack edits.

## The prompt

`D/cards/bar/template.txt`, word for word, sent through Sol with `D/cards/ref_sheet.png` attached; `art.py gen` does both. It made 8 of the 10 graded wows, a quarter of its pictures went live against 4% for everything since, and it was confirmed on the open Savanna rares on 2026-10-10 ("much better", the Zebra "a magnitude of order better"). Never edit the template without a test.

The only words written per card are its `line`: the animal, the one moment that shows it (the picture people carry, its hook), its habitat and light, then a palette, in one sentence. "a golden eagle, the king of the sky, landing on the top of a high mountain crag, the whole bird in the picture with its great wings raised high above its back and talons reaching for the rock; behind it only a bright open sky and snowy peaks far below; palette of bright sky blue, snow white, warm grey rock and the eagle's golden-brown." No camera directions, no facial expressions, no corrections.

## A round

1. **The idea, with Martin.** For each card, the one picture people carry of the animal and its hook, agreed in chat in a line.
2. **Paint.** A jobs file in `D/cards/bar/jobs/` with one `{"id", "card", "batch", "line"}` per picture (one or two per card, different moments if two), then `python3 D/cards/bar/art.py gen <file> -p 6` in the background (`--dry` prints the prompts). A FAIL within seconds is the image quota (its own cap, about 80 pictures then hours locked); it prints when it resets.
3. **Look before showing.** Full-size crops (`art.py crop <id> x0 y0 x1 y1`) of every face, every set of legs, every place two animals touch. A picture with a visible fault isn't shown.
4. **Martin picks** on the review page: `art.py page <review> <ids...>`, then publish its `index.html` and `files.json` with the Artifact tool to the review artifact in `D/cards/notes.md`. Read his marks with `ArtifactData` (collection `verdicts`), merge them with `art.py verdicts <review> <file>`. A pick with one named flaw gets one surface edit, then the card is done. A card picked "none" gets a new idea, not a reworded one.
5. **Install** each pick with `D/cards/bar/install.sh <card> <id>`, then set its `CROP`, `STRIP` and `FULL` in the game's `static/art.js` by rendering the board portrait and looking at it, run the web fast suite (`animal_kingdom/web/test`, `node --test`) in the background, and commit: design repo `cards/<card>.png cards/<card>.jpg cards/bar/manifest.jsonl` to `main`; game repo `static/art/<card>.jpg|webp` and `static/art.js` to the local `new-cards` branch, never pushed.
