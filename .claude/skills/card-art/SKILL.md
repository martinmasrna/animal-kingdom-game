---
name: card-art
description: Make, repaint or review card art for Animal Kingdom - the agent turns Martin's feeling for a card into clearly different picture ideas and runs the logistics (lines, painting, review page, install, crops); Martin makes every judgment, one tap per picture. Use whenever the work is a card's painting - "card art", "paint the Savanna rares", "repaint X", "art round", "review page for art", reading art verdicts, installing a picked painting, or improving how art is made.
---

# Card art

Why it works this way: `knowledge/card-art-diagnosis-2026-10-17.md` (game repo). Three weeks of record say that words move what is in a picture, not how it feels; that an agent's judgment of these pictures is at chance (11 of 31 against Martin's picks, chance 8, with or without the rules); and that no rule written from a verdict ever changed what came out. So the agent does ideas and logistics, Martin does every judgment, and no verdict becomes a rule. `D` below is the design sandbox, the game repo's sibling folder `../design/`.

## The split

**The agent:** reads the card, turns Martin's feeling into clearly different picture ideas, writes the lines, paints, builds the page, installs, sets crops, commits.

**The agent never:** picks, ranks, recommends, praises or grades a picture, or says which is "strongest"; writes a rule, a memory or a principle from a verdict; starts a repaint round without a reason Martin stated; drops a picture from the page (every picture a round produced goes on it; he judges anatomy himself, at full size).

**Martin:** a voice note or a character for a card when he has a feeling ("you decide" otherwise), then one tap per picture.

**The agent checks facts, never taste.** Before a prompt goes out, it is read once as Sol will read it, with only the attached images and the words: "in their place" next to a picture is a location, not "instead of" (the Albatross's fish landed on the horizon, 2026-10-18). When the pictures come back, each is looked at against its concept: is what was asked in it, where it was asked? A miss is rolled again before the page, or said in one line next to the picture. Whether a picture is good stays Martin's.

## A round

1. **Cards.** `.venv/bin/python tools/cards/hq.py show` (game repo): the Art column marks each painting empty, draft, problem (with his note), fine or locked. Read the card's effect and name before writing anything: the picture shows the effect through what the real animal does. Look at the live cards of the same animal and family first; the new picture must not read as one of them.
2. **Concepts.** Eight to twelve per card, as far apart as possible in moment and feeling (see below). His note becomes concepts of its own, fleshed out. One picture per concept in round one. A roll is dice; a concept is not.
3. **Jobs.** Jobs in `D/cards/bar/<batch>.jsonl`: `{"id","card","batch","idea","line"}`, plus a `{"card","batch","brief"}` line holding what Martin said. `python3 art.py gen <batch>.jsonl -p 4` in the background (about 10 minutes per 16; about 80 pictures per window before the image quota locks). The template, the reference sheet and Sol's rewrite stay as they are: tested 2026-10-17, they neither help nor hurt, and changing them is not a lever.
4. **Page.** `python3 art.py page <review> <ids...>` builds it; publish to the review artifact (`D/cards/notes.md` holds its link) with its image files. Every picture of the round, next to the live art, numbered, with no label of ours. Tell Martin what each idea is, one line each, and the link. Nothing about which is better.
5. **Verdicts.** Three buttons per picture: This is it, Almost, Nope. Read them with `ArtifactData` (collection `verdicts`) and merge them with `python3 art.py verdicts <review> <export.json>`. His note is a `note` record in the manifest, never a rule. Then:
   - This is it: install.
   - Almost and nothing better: two or three more rolls of that idea from the same line, or a surface edit (`edit.sh`) when the flaw is a sky, a colour, the eyes. Never a new scene for a liked picture.
   - All Nope: the ideas are dead; new ideas, not re-rolls. Ask for his feeling only if he hasn't given one.
   - A card is parked (`problem` on the card table, with his note) when its ideas are dead and nobody has a new one, or when Martin says so; never by a round count. "More legendary" and "too photographic" are reasons to park, never to roll.
6. **Install** with `python art.py install <card> <id>` (the game's venv python, in `D/cards/bar`; master to `cards/<card>.png`, JPEG and WebP into the game, the settle recorded, the card's art and crop back to draft on the card table). Set `CROP`, `STRIP` and `FULL` by rendering the board portrait and looking: `.venv/bin/python tools/cards/hq.py crop <card> --crop x,y,d --strip x,y,z --full y` (a hook refuses hand edits). An install runs no tests. Commit by path: design repo `cards/<card>.png cards/<card>.jpg cards/bar/manifest.jsonl cards/bar/<batch>.jsonl`; game repo `static/art/<card>.jpg|webp`, `static/art.js` and `tools/cards/levels.json` (only your own hunks; other sessions edit them too).

A pick is a draft. It stays on the board; a later repaint needs a reason Martin writes on the card table.

**Martin painting with Sol himself.** The same round without the agent in the middle: he opens `D` in the Codex app (its `AGENTS.md` is the sandbox's map and Sol's standing brief: the card, the hand sheet, the absolutes, where the data is, where to save), talks to Sol, and judges the pictures there. The agent's part starts afterwards: `python art.py adopt <card> <batch>` moves the pictures Sol saved to `D/cards/new/` into `bar/r1/` and the manifest, then install and crops as above. Steps 2 to 5 are his in that mode; nothing from them is written down by the agent.

## Concepts

The ideas are the agent's job, and Martin's when he has them; Sol is the translator into the image model's language and gets the room to do that (Martin, 2026-10-18). For each card the agent writes many concepts, eight to twelve, fast and wide, each the way a novelist puts a scene on the page with words alone: what is happening, the feeling it leaves, the psychology of the moment. A concept points at something that already exists in the model; a feeling points better than a list of parts.

Two ways to get it wrong. A parts list (palette, anatomy, where a wing goes, negatives, stacked constraints): Sol turns every clause into a rule and the model paints the rules. A delegation ("paint it the way you think best"): that skips the creative step. The card's text and keywords are the agent's input for the concept, never Sol's: the effect lives in the concept as a feeling (the moment the big thing arrives and the small things know), so Sol never needs the rules and never gets them. `art.py` puts only the card's name, habitat and rarity in front of the concept; the template carries the fixed principles.

"The sea has been empty for a thousand miles, and then it isn't: a shape comes down out of the grey with wings that do not seem to end, and every small bird on the water knows, in the same instant, that it is small. The albatross has arrived, and the water around it clears."

Martin's ideas go in as they are when fleshed out, fleshed out by the agent when not, or as seeds for more. One picture per concept in the first round; a concept he marks Almost gets a few rolls.

What stays in the agent's hands: real animals in a real place, one animal as the hero, the animal's own habitat, no human roles as the idea (a king, a sage: the model paints a character), nothing that implies an effect the card lacks. A real photo as pose skeleton (`"sheet"` in the job) only when the model keeps getting the anatomy wrong; the deck's live card art attached when a legendary gathers them; a liked picture attached as `"world"` when Martin wants it kept and one thing changed.

`D/cards/art-principles.md` is Martin's taste as it was written down, frozen 2026-10-17: read it for what the art must achieve; never add to it.

## The measure

`python3 art.py cost`: pictures per installed card and rounds per card, by week. The floor is one round of four to six. The treatment has failed if, after four weeks of rounds, pictures per installed card are still about 8 and rounds about 3. Then the lever is what paints (`docs/later.md`), not the words.
