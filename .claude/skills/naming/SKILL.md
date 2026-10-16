---
name: naming
description: >-
  Name a legendary card with Martin, or take a name he brings: the card's character in his words, the shelf first, then one wide pool from several unrelated sources shown flat on the picking page, a grab onto the card the same day as a draft, a cold look a week later. Use when Martin asks to name a legendary, to replace a bracketed placeholder ([WOLF]), to run a naming sitting, to put a name on the shelf, or brings a name of his own (in English or Slovak). Not for species names of commons and rares (that's deck-design) and not for card art (card-art).
---

# Naming a legendary

Commons and rares carry species names; a legendary is one named individual, and its name is the hardest thing in the game to get right. Read `knowledge/naming-diagnosis-2026-10-16.md` first: it is the record of eight days in which every session wrote Martin's rejections into rules, the rules ended up rejecting 11 of his 17 gold names, and the lists narrowed until nothing hit. This skill is the loop that survived that record. `docs/design/naming.md` holds what a name is and the gold set; `docs/cards/name-shelf.md` holds names waiting for a card; `tools/names/` builds the picking page.

## What never happens

- A rule is never written from a rejection. A "no" is a verdict on one name; it teaches nothing about the next. The rules doc does not grow.
- A list never carries a theory above it, a marked pick, or reasons beside the names. Martin reads the names cold ("I cannot look at this unbiased now because you just ruined it with your pick").
- A list is never one idea ten ways. Every miss in the record was that shape; every hit came from a list built from several unrelated sources.
- Names are never batched for the end of a pass. A grab goes onto the card the same day; batching lost eight names once.
- A name is never argued for. If Martin says no, it is no; if he asks what a word means, answer in one line and stop.
- The shelf is never poured onto every card. A shelf name goes only where it could belong, by judgment.

## The character first

One card at a time, and before any name: the card's image and feeling in one line each, with a film, book or real-animal analogue if one fits, put to Martin for a yes. His own description beats anything read off the art (his macaque is a crime boss, not a glutton; his honey badger is John Wick, not a brawler; his leopard is the bogeyman zebra mothers tell their foals about). Say the principle of the analogue back to him in one sentence and get "yes, exactly" before generating. Then hand that sentence to the generators and step out of it: the generators never see his reactions, so none of them can chase the last correction.

## The shelf first

`docs/cards/name-shelf.md` (Martin's sheet: https://claude.ai/artifact/4BC1u4Nh2qj7UAy3UNF5wd feeds it). Check it before generating; a shelf name that fits goes into the pool for that card and nowhere else. A Slovak entry is a feeling to match, not a word to translate: English makes the diminutive and the fondness other ways (Očko became Little Eye in the Witcher translation; Pip, Wink, Glint carry the same thing). A "great name, not this card" from any sitting goes onto the shelf, with the card it was rejected for.

## One wide pool

Per card, 50 or more names from at least three sources that do not share a brief: this session with the whole record and the character sentence; one cold agent (Opus) told to name a character in a story, given only the card line and the character sentence; one cold agent given only the stock of names real famous animals and animal characters have carried, told to use it two ways (reusable folk names and new names made the same way). Cold volume from one model with one brief produced zero hits in 90 (Test 2 in the diagnosis); breadth is unrelated briefs, not more names. The only filter is mechanical, in `tools/names/build.py`: names already in the game, a famous character of the same kind of animal, verbatim Slovak, no vowel, over 24 letters. Martin's two stated absolutes stay as judgment on his side: he can say it, and it comes from the animal's world (a razor, chalk and ivory are human things). Both have gold exceptions, so they are filters for the agent's lists, never verdicts on his names.

## The picking page

`tools/names/build.py BRIEF.json POOL.txt ... --out DIR`, then publish `DIR/placeholders.html` as an artifact (root DIR, the card art in `files`, capabilities `{"db": {}}`). One section per card: the art, the card line, the character line, every name in a list, three buttons per name: Nope hides it, Shelf, This is it. Nothing else on the page. Taps save to the page's store (`picks/placeholders`); read them with ArtifactData. Build the page with the merge-on-load pattern already in the template: the store is merged under anything tapped before it answered, never the other way round. The source of each name stays in `DIR/key.json`, never on the page.

## After the taps

- Every "this is it" goes onto the card that day: `.venv/bin/python tools/cards/hq.py set ID animal "Name/Species"`, level draft, note "Martin, date". Never fine or locked.
- Every Shelf tap goes into `docs/cards/name-shelf.md` under "Reserved during naming rounds", with the card it was rejected for.
- Nothing locks for a week. A name that survives a week on the card through art and play, and one cold look, is Martin's to lock; a name he stops liking goes back to a bracket, which is a result, not a failure (Mimi, Twiga, Cinder all died this way; Vesper, Aurum and Pestis went the other way).
- A card with nothing tapped keeps its bracket: `[SPECIES]` in caps, `Queen [ANT]` where a title is settled. Brackets are honest; testers read them as unnamed.

## When Martin brings a name

Check two things in one line each: whether it clashes with a famous character of the same kind (Sirius on a wolf) or carries an unintended echo a native ear hears (Cinder is Cinderella, Musk is Elon, Bill is an invoice), and whether a non-native player can say it. Then apply it as a draft. Do not improve it, do not offer alternatives beside it, do not explain why it works.

## The rate to expect

In the record a wide list hit about one card in three; sixteen names settled from about 1,380 candidates over three sittings, and four of them were gold a week later. Riot drafts 100 to 200 names per champion with a team. One or two settles per short sitting is the job going well. Nothing on the page expires, so a sitting happens when Martin feels like one, never on a schedule.
