---
name: card-art
description: Make, repaint or review card art for Animal Kingdom - four bets per card from the proven template and the six-painting reference sheet, each naming its backdrop, Martin's voice notes folded in, Martin's review page, install. Use whenever the work is a card's painting - "card art", "paint the Savanna rares", "repaint X", "art round", "review page for art", reading art verdicts, installing a picked painting, or improving how art is made.
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

`D/cards/bar/template.txt`, word for word, with `D/cards/ref_sheet.png` attached, sent through Sol (`codex exec -m gpt-5.6-sol`), never verbatim: Sol rewrites it for the image model with its own image skill, and that rewrite is part of the recipe. Never edit the template without a test.

The only words written per card are its `line`: the animal, one specific thing it is doing, and the one simple backdrop behind it, named, then a palette. "a big gorilla wading knee-deep through a swamp, pulling up water plants to eat; behind him only soft pale morning mist over still water; palette of black fur, silver back, soft greens and pale grey-gold mist." Without a named backdrop the background fills with evenly detailed foliage and the card reads as a photo; without a specific action the model paints its one default pose for the animal.

Extra images when a card needs them: a real wildlife photograph as the pose skeleton when the model keeps getting the anatomy wrong ("copy its pose exactly"); the live card art of the deck's own animals when a legendary gathers them.

## A round

1. **The cards and Martin's notes.** List the cards with rarity, strength and effect; Martin records a voice note per card when he has a feeling about it, or says "you decide".
2. **Four bets per card.** Four lines as far apart as possible, each with its own action and named backdrop, each card in its animal's real corner of the habitat. Martin's ideas become one or two of the four.
3. **Paint.** Four at a time in the background; about 80 pictures per window before the image quota locks. Every picture the round produced goes on the review page; Martin judges anatomy himself.
4. **Martin picks** on the review page (`D/cards/notes.md` holds its link), each card next to its live art. Read his picks and notes with `ArtifactData` (collection `verdicts`). A pick is installed; "none" with a note becomes new bets on that note; a liked picture with one flaw in its sky, colour or light gets a surface edit.
5. **Install** each pick with `D/cards/bar/install.sh <card> <id>` (the picture copied to `bar/r1/<id>.png` and recorded in the manifest first), then set its `CROP`, `STRIP` and `FULL` in the game's `static/art.js` by rendering the board portrait and looking at it, run the web fast suite (`animal_kingdom/web/test`, `node --test`), and commit: design repo `cards/<card>.png cards/<card>.jpg cards/bar/manifest.jsonl` to `main`; game repo `static/art/<card>.jpg|webp` and `static/art.js` to the local `new-cards` branch, never pushed.
