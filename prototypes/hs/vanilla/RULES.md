# Vanilla HS

A card duel with only text-less minions and damage spells, on the usual rules of the genre, to compare against the board toys with the same 70% test (Martin, 2026-11-26: "Toy Hearthstone ... only vanilla minions and spell"; the card list reviewed: "This looks great, let's run it!").

- 30 health. Mana 1 on your first turn, one more each turn up to 10, refilled each turn. Draw 1 at the start of each turn, the first player's first turn included. Opening hands 3 (first) and 4 (second); the second also gets the Coin (0 mana: gain 1 mana this turn). Empty deck: fatigue, 1 damage, then 2, then 3.
- Up to 7 minions a side. A minion can attack from the turn after it is played, once a turn, any enemy minion or the enemy hero; minions fighting deal their attack to each other. Damage stays.
- Deck, the same for both: three copies each of minions 1 mana 2/1, 2 mana 3/2, 2 mana 2/3, 3 mana 3/4, 4 mana 4/5, 5 mana 5/5, 6 mana 6/7, and spells "Deal 2 damage" (1 mana), "Deal 3 damage" (2), "Deal 6 damage" (4), each to any minion or hero.

## The 70% test (`node ladder.mjs`, 400 games a pairing, both seats on the same deals)

- Spend, random actions but never at its own side and never ending the turn while it can act: beats Random 98%.
- Face, plays what it can and sends every spell and attack at the enemy hero: beats Spend 76%.
- Greedy, each action the one that most improves health, board and hand (`greedyBot`): beats Face 74%.
- Expert, play-outs with Greedy on both sides (`rolloutBot(6, 4, 8)`, the same search as Hex's Expert): beats Greedy 71%.
- An eight-times larger search beats Expert 58.5%: the chain stops there. Games last about 7 to 9 turns each.

## The page

`node build.mjs` writes `index.html` and `artifact.html`: you against Expert. Who goes first alternates from game to game, and the two numbers by Restart count your wins and Expert's, kept in your browser. Hex's page keeps the same count against its own Expert.
