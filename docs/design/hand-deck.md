# The hand deck (Bears and Primates)

Result of the autonomous session of 2026-10-05, for Martin's review: designed, checked by me against the rules and the decks, attacked by a cold Sol review, prototyped in the engine and played by TurnBot (2,800 games). Bears hoard (hibernation: growing while held), Primates train (buffing cards in hand, Roars that pay off past a strength threshold). It fills the "special" slot of the target meta in [`families.md`](families.md): Hearthstone's Handlock, built from this game's pieces.

## How the deck plays

- Early: draw and hold (the Draw action, Black Bear, Tarsier), train the hand (Baboon, Macaque, Orangutan, Sloth), keep the den alive with bodies that are already big when they land (Grizzly grows while held).
- Middle: drop trained threats whose Roars only fire once they are big enough (Chimpanzee, Gorilla), and the small removal that grows with training (Capuchin's stone).
- The two clocks: every turn the hand gets stronger, so the opponent has to win early or out-race it on food.
- It wins on the board, mostly by the den (in the bot games 2 of 3 wins were den captures).

Buffs given in hand are stored on the card ("give +X", `keywords.md`); a bounced animal comes back fresh and loses them (Martin: two cards bounce, not a worry).

## The cards (version 3, after the review and the runs)

Version 3 is version 2 with the first draft's Gorilla sweep restored; it was not run as an exact set.

| Card | Habitat | Rarity | Str | Text |
|---|---|---|---:|---|
| Black Bear | Forest | C | 5 | Roar: in 2 turns, draw 2 cards. (moved to Food OTK, 2026-10-08) |
| Grizzly Bear | Forest | C | 6 | At the start of your turn, if this is in your hand and you hold 6 or more cards, give it +1 strength. |
| Sloth | Jungle | C | 3 | Roar: in 2 turns, give each animal in your hand +2 strength. |
| Baboon | Savanna | C | 4 | Roar: give an animal in your hand +2 strength. (locked) |
| Tarsier | Jungle | C | 2 | Roar: draw a card. Give it +2 strength. |
| Macaque | City | C | 3 | Roar: give each Primate in your hand +1 strength. |
| Capuchin | Jungle (roster addition) | R | 3 | Roar: remove an adjacent enemy of equal or lower strength. |
| Chimpanzee | Jungle | R | 5 | Roar: if this has 7 or more strength, remove an adjacent enemy. |
| Orangutan | Jungle | R | 6 | Roar: give each Primate in your hand +2 strength. |
| Gorilla | Jungle | R | 7 | Roar: if this has 10 or more strength, remove all adjacent enemies with less strength. |
| the old teacher (orangutan) | Jungle | L | 5 | At the end of your turn, give each Primate in your hand +1 strength. |
| the silverback (gorilla) | Jungle | L | 8 | Your other Primates have +2 strength. |
| the toolmaker (chimpanzee) | Jungle | L | 4 | Roar: Scout a Primate. Give it +3 strength. |
| the long sleeper (bear) | Forest | L | 3 | Has +1 strength for each Bear and Primate in your hand. |

Primate is a new family tag; with Baboon, Macaque, Capuchin and the Jungle apes it holds 10 designs, viable on its own. Capuchin needs a Jungle slot (it takes Jackal's old removal, which Martin assigned to this deck). Legendary names come later.

## What changed and why

The cold review (Sol) and the bot runs changed eight cards from the first draft:

| Card | First draft | Problem | Change |
|---|---|---|---|
| Grizzly | grew every turn in hand | a generic Lion replacement for any slow deck (Sol) | grows only while you hold 6 or more cards: hibernation needs a full larder, and the effect belongs to hand decks |
| Sloth | +1 to the hand in 2 turns | dominated by Orangutan (Sol) | +2 |
| Tarsier | strength 1 | far below the draw anchor (Sol) | 2; it stays small, as a tarsier is |
| Capuchin | strength 2 | its base removal hit almost nothing (Sol) | 3; trained, it averaged 5.6 when placed |
| Orangutan | +1 to every card in hand | exportable to any draw deck (Sol) | +2 to Primates only |
| the old teacher | +1 to every card in hand each turn | a generic engine (Sol) | Primates only |
| the long sleeper | +1 per card in hand | a free 9–10 wall in any draw deck (Sol; in our runs it averaged 9.3 when placed) | counts only Bears and Primates (8.6 in the runs) |
| Gorilla | "if this has 10 strength" | the wording switches off past 10 (Sol) | "10 or more", removing enemies with less strength. Sol also wanted it to hit only enemies of 5 or less; the runs showed that kills it (when it reached 10, an enemy of 5 or less was next to it once in 55 placements), so the full sweep stays |

Rejected from the review: Sol wanted Black Bear's draw conditioned on a full hand (Black Bear stays as Martin decided), and Tarsier at 3 (2 keeps the size rule).

## The bot runs

TurnBot, 50 games per seat against each of the seven premades (700 games a version), plus two reference decks against the same field. Bots are far below human level and don't understand a trained hand, so this only screens for the obviously broken or dead.

| | Field win rate | vs Cats | vs Egg | vs Colony | vs Ramp | vs Food | vs Aggro | vs Canine |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Hand deck, first draft | 57% | 75% | 92% | 36% | 51% | 31% | 44% | 69% |
| Hand deck, version 2 | 61% | 79% | 99% | 31% | 61% | 34% | 49% | 73% |
| Cats (reference) | 61% | — | 98% | 39% | 62% | 45% | 70% | 51% |
| Food OTK (reference) | 59% | 44% | 95% | 41% | 73% | — | 54% | 45% |

(Egg Control loses to everyone under bots, which is a known pilot flaw, not a signal.)

What it says:

- Nothing is dead: every card was played most games, the trained Roars fire (Chimpanzee met its threshold on average, Capuchin and Chimpanzee removed about one enemy every other game each, version 1's Gorilla even more), and the trainers raise placement strength by 2–3 over the printed numbers.
- Nothing looks broken alone: no card's win rate when played stands out (57–73% against a 61% deck).
- The deck is about as strong as the best existing decks under bots, with a clear matchup shape: it crushes the board decks (Cats 79%, Canine 73%) and loses to the food decks (Colony 31%, Food OTK 34%), which ignore its board and race to 100. Most of its losses are food losses.
- Against the den rush it's even (44–49%), so the early game survives without a dedicated defensive card.

## For Martin

1. The matchup shape: beats board decks, loses food races. That's a healthy rock-paper-scissors in the target meta, if you like it; if not, it needs a way to contest regions.
2. Cats at 21% against it is the number to watch: if people find the same, the trainers or the Gorilla sweep come down.
3. The long sleeper's "for each Bear and Primate in your hand" works but reads clunky; the alternative is a cap ("…up to 9").
4. Capuchin needs a Jungle slot.
5. Legendary names.

The prototype lives on the local branch `proto/hand-deck` (cards as `bench` with versioned ids, the effects, the sim and analysis scripts); it's not for main as is.
