# News

What changed in the game, one file per release (`YYYY-MM-DD.md`, the day it went live), shown on the News screen newest first. Each release is drafted from its commits and redlined by Martin before it ships; a deploy that changes cards or rules without a new release here stops and says so.

## How a release reads

- `# 2 October 2026`, then the groups in this order, each only when it has something: `## Rules`, `## Cards`, `## New`, `## Fixed`.
- One bullet per change, one plain sentence in the cards' voice ("your opponent", never "they"). A Fixed bullet names what was wrong ("A bot could take minutes over a move").
- A rule or card change says why on the next line: `  Why: ...`, one sentence.
- A change that touches cards lists them on another line, by name: `  Cards: Tiger, Eon`. Players never see this line; it decides whose "Since you last played" shows the change (a player whose decks hold one of them).
- A card change can show the card as it was: `  Was: {"str": 1}` (the fields that differed, as cards.json has them).

## What goes in (Martin, 2026-10-02)

- Only what a player would notice or needs to know. Clarifications, internal limits and small fixes stay out: they are clutter.
- No summary line under the date: a release is a list of small changes, a summary only repeats it.
- No credit for feedback, no names.
- As concise as possible.
