# Card design log

The measure behind `card-design-diagnosis-2026-10-25.md`: whether agent card proposals stopped failing checks a lookup would have caught. One line per sitting in which an agent proposed cards, appended by the agent at the end of the sitting, from Martin's verdicts in the chat.

A rejection's class is the cheapest thing that would have caught it: `board` (a turn on the real grid), `spec` (an earlier instruction of Martin's in the record), `pool` (a card already doing it), `rules` (a keyword's text), `fact` (what the animal is), `anchor` (the number against its anchor), `taste` (none of those; his call), `none` (no reason given). The first six are checkable: the sheet (`tools/cards/check.py`) exists to catch them.

Read on 2026-11-15. The treatment failed if, over the sittings since 2026-10-26, checkable rejections are 25% or more of all rejections, or accepted proposals are still about a third of those judged (the three-week rate before: 35% accepted, 56% of rejections checkable).

| date | sitting | proposed | accepted | rejected | board | spec | pool | rules | fact | anchor | taste | none |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-26 | Brutus (the rhino legendary's new effect) | 12 | 1 | 11 | 0 | 0 | 1 | 1 | 0 | 0 | 9 | 0 |
| 2026-10-26 | Sea Turtle (new effect; Martin wrote the card himself) | 7 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | 3 | 4 | 0 |
| 2026-10-27 | Card balance: Alley Cat, Queen Bee, Giants (Titan cheats, Oxpecker, legendary Oxpecker); agent on a stale copy of this skill | 24 | 3 | 21 | 0 | 4 | 3 | 0 | 4 | 3 | 7 | 0 |
| 2026-10-28 | Jellyfish/Toad/Tortoise; Canines and Roam redesign (board puzzle), birds; counts reconstructed from the chat, approximate | 50 | 9 | 30 | 2 | 4 | 5 | 3 | 2 | 4 | 10 | 0 |
