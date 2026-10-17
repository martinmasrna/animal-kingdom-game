---
name: card-art
description: Make, repaint or review card art for Animal Kingdom - the agent turns Martin's feeling for a card into clearly different picture ideas and runs the logistics (lines, painting, review page, install, crops); Martin makes every judgment, one tap per picture. Use whenever the work is a card's painting - "card art", "paint the Savanna rares", "repaint X", "art round", "review page for art", reading art verdicts, installing a picked painting, or improving how art is made.
---

# Card art

Why it works this way: `knowledge/card-art-diagnosis-2026-10-17.md` (game repo). Three weeks of record say that words move what is in a picture, not how it feels; that an agent's judgment of these pictures is at chance (11 of 31 against Martin's picks, chance 8, with or without the rules); and that no rule written from a verdict ever changed what came out. So the agent does ideas and logistics, Martin does every judgment, and no verdict becomes a rule. `D` below is `~/Work/fun/animal-kingdom-design/`.

## The split

**The agent:** reads the card, turns Martin's feeling into clearly different picture ideas, writes the lines, paints, builds the page, installs, sets crops, commits.

**The agent never:** picks, ranks, recommends, praises or grades a picture, or says which is "strongest"; writes a rule, a memory or a principle from a verdict; starts a repaint round without a reason Martin stated; drops a picture from the page (every picture a round produced goes on it; he judges anatomy himself, at full size).

**Martin:** a voice note or a character for a card when he has a feeling ("you decide" otherwise), then one tap per picture.

## A round

1. **Cards.** `.venv/bin/python tools/cards/hq.py show` (game repo): the Art column marks each painting empty, draft, problem (with his note), fine or locked. Read the card's effect and name before writing anything: the picture shows the effect through what the real animal does. Look at the live cards of the same animal and family first; the new picture must not read as one of them.
2. **Ideas.** Four to six per card, as far apart as possible: different moments, different ways the effect shows, different distance and backdrop. His note becomes one or two of them, translated, never executed word for word. One picture per idea in round one. A roll is dice; an idea is not.
3. **Briefs.** One brief per idea, two or three plain sentences (see below). Jobs in `D/cards/bar/<batch>.jsonl`: `{"id","card","batch","idea","line"}`, plus a `{"card","batch","brief"}` line holding what Martin said. `python3 art.py gen <batch>.jsonl -p 4` in the background (about 10 minutes per 16; about 80 pictures per window before the image quota locks). The template, the reference sheet and Sol's rewrite stay as they are: tested 2026-10-17, they neither help nor hurt, and changing them is not a lever.
4. **Page.** `python3 art.py page <review> <ids...>` builds it; publish to the review artifact (`D/cards/notes.md` holds its link) with its image files. Every picture of the round, next to the live art, numbered, with no label of ours. Tell Martin what each idea is, one line each, and the link. Nothing about which is better.
5. **Verdicts.** Three buttons per picture: This is it, Almost, Nope. Read them with `ArtifactData` (collection `verdicts`) and merge them with `python3 art.py verdicts <review> <export.json>`. His note is a `note` record in the manifest, never a rule. Then:
   - This is it: install.
   - Almost and nothing better: two or three more rolls of that idea from the same line, or a surface edit (`edit.sh`) when the flaw is a sky, a colour, the eyes. Never a new scene for a liked picture.
   - All Nope: the ideas are dead; new ideas, not re-rolls. Ask for his feeling only if he hasn't given one.
   - A card is parked (`problem` on the card table, with his note) when its ideas are dead and nobody has a new one, or when Martin says so; never by a round count. "More legendary" and "too photographic" are reasons to park, never to roll.
6. **Install** with `D/cards/bar/install.sh <card> <id>` (master to `cards/<card>.png`, JPEG and WebP into the game, the settle recorded, the card's art and crop back to draft on the card table). Set `CROP`, `STRIP` and `FULL` by rendering the board portrait and looking: `.venv/bin/python tools/cards/hq.py crop <card> --crop x,y,d --strip x,y,z --full y` (a hook refuses hand edits). An install runs no tests. Commit by path: design repo `cards/<card>.png cards/<card>.jpg cards/bar/manifest.jsonl cards/bar/<batch>.jsonl`; game repo `static/art/<card>.jpg|webp`, `static/art.js` and `tools/cards/levels.json` (only your own hunks; other sessions edit them too).

A pick is a draft. It stays on the board; a later repaint needs a reason Martin writes on the card table.

## The brief

Sol is an illustrator, not a tool: it gets the card and the idea, and it decides how to paint it (Martin, 2026-10-18: "trust it, treat it as your partner"). `art.py` puts the card's facts in front of every brief (name, habitat, rarity, strength, text), so a brief is two or three plain sentences: the one idea, and what the picture should say in half a second and on a second look. Sol picks the pose, the backdrop, the light and the palette.

A brief never lists parts. No palette, no anatomy, no clause about where a limb goes, no negatives ("no X", "nothing like Y"), no stack of constraints: Sol turns every clause into a rule and the model paints the rules instead of the animal. The template already carries the fixed principles (one animal the hero, a calm area behind it, painted not photographed, the top band and bottom third kept clear). The record's lines ran at a median of 56 words and the ones that settled were no longer.

"The idea: the albatross arriving, and the moment it arrives the small creatures around it are gone. One albatross, the hero; the small ones are whatever you think reads best and paints well. It is a portrait card, so solve the wingspan with the composition rather than cutting it."

What stays in the agent's hands: real animals in a real place, one animal as the hero, no human roles or feelings as the idea (king, wise, proud paint a character), the animal's own habitat, nothing that implies an effect the card lacks. A real photo as pose skeleton (`"sheet"` in the job) only when the model keeps getting the anatomy wrong; the deck's live card art attached when a legendary gathers them; a liked picture attached as `"world"` when Martin wants it kept and one thing changed.

`D/cards/art-principles.md` is Martin's taste as it was written down, frozen 2026-10-17: read it for what the art must achieve; never add to it.

## The measure

`python3 art.py cost`: pictures per installed card and rounds per card, by week. The floor is one round of four to six. The treatment has failed if, after four weeks of rounds, pictures per installed card are still about 8 and rounds about 3. Then the lever is what paints (`docs/later.md`), not the words.
