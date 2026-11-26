# Vanilla HS

A card duel with only text-less minions and damage spells, on the usual rules of the genre, to compare against the board toys with the same 70% test (Martin, 2026-11-26: "Toy Hearthstone ... only vanilla minions and spell"; the card list reviewed: "This looks great, let's run it!").

- 30 health. Mana 1 on your first turn, one more each turn up to 10, refilled each turn. Draw 1 at the start of each turn, the first player's first turn included. Opening hands 3 (first) and 4 (second); the second also gets the Coin (0 mana: gain 1 mana this turn). Empty deck: fatigue, 1 damage, then 2, then 3.
- Up to 7 minions a side. A minion can attack from the turn after it is played, once a turn, any enemy minion or the enemy hero; minions fighting deal their attack to each other. Damage stays.
- Deck, the same for both: three copies each of minions 1 mana 2/1, 2 mana 3/2, 2 mana 2/3, 3 mana 3/4, 4 mana 4/5, 5 mana 5/5, 6 mana 6/7, and spells "Deal 2 damage" (1 mana), "Deal 3 damage" (2), "Deal 6 damage" (4), each to any minion or hero.

## The 70% test (`node ladder.mjs`, 400 games a pairing, both seats on the same deals)

Every bot here first passes `node sanity.mjs`: set positions a person never gets wrong (no face burn on turn 1, lethal, lethal through the Coin, a free trade). The first version did not: it counted a played card as costing nothing and never added up lethal, missed lethal and burned face on turn 1, and Martin beat it 8-2 (2026-11-26).

- Spend, random actions but never at its own side and never ending the turn while it can act: beats Random 98%.
- Face, plays what it can and sends every spell and attack at the enemy hero: beats Spend 76%.
- Greedy, lethal when it is there, otherwise each action the one that most improves health (worth more below 12), board and hand, a played card counted as spent (`greedyBot`): beats Face 93%.
- Expert, Greedy's turn unless twelve play-outs per candidate clearly prefer another (`rolloutBot(6, 12, 8)`): beats Greedy 68%, short of 70.

## The page

`node build.mjs` writes `index.html` and `artifact.html`: you against Expert. Who goes first alternates from game to game, and the two numbers by Restart count your wins and Expert's, kept in your browser. Hex's page keeps the same count against its own Expert.
