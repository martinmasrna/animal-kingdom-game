# Status

The map. Read it first each session and keep it current: when something here changes, rewrite the line, don't append to it.

## Where this is going

*Animal Kingdom* is a two-player card game Martin is designing, meant to become a digital game people play competitively. The path: design a game that is fun and deep (only humans can judge it), get other people playing it, stabilise the rules and cards, balance it, go public.

**Now: designing the mana game.** On 2026-11-20 Martin made the mana ruleset the whole game ("Literally nothing else than what's currently on the staging server (and localhost 8000) matters") and the old rules, their 71 animals, bots and tools were deleted. The game is set in a world of our own, not on Earth (Martin, 2026-11-19: "I thought about it and it's 1000% the right decision"), and its cards are not traditional Earth animals (Martin, 2026-11-20: "alltogether, at least the traditional Earth animals"). What the cards and the world are instead is open. Every number and rule below is a working version from his playtests, not settled.

What the game is for, why mana, and Martin's words on the rules' shape and the board: [`design.md`](design.md).

## The rules as they play

- **Board:** 19 pointy-top hex tiles in rows of 3, 4, 5, 4, 3 (`data/maps.json` `map_hex19`), your side at the bottom. Each player's row of 3 is their base, where their connection starts and where either player may place. Behind each base is its den.
- **Mana:** on your Nth turn you have min(N, 10) mana, lost at the end of the turn. A card costs its `cost`; a leader's power costs 3. Anything an effect puts into play is free.
- **Cards:** opening hands of 3 (first player) and 4 (second), a mulligan, one free card at the start of each turn (not the first player's first turn), no other draw.
- **Covering:** a card placed on an enemy it is stronger than covers it, and a covered card, yours or theirs, is removed.
- **Zero strength:** an animal at 0 strength is removed, by the rules (Armor doesn't hold), each time the effects finish resolving (Martin, 2026-11-21: "make it a general rule").
- **Food:** both start at 15; each region (three tiles) a player holds pays 1 food at the end of their turn; 30 food wins, 0 loses. A card placed or moved into the enemy den, connected through one of their base tiles, destroys food equal to its strength (at most what the den holds) and is spent.
- **Turns:** a turn ends when its player ends it; no turn ends or is skipped by itself.
- **Decks:** 25 cards, 2 copies of a card, 1 of a legendary, one leader.

## The cards

48 in `data/cards.json`, all collectible, all placeholders. Most are Martin's paper cards of 2026-11-21: the Wisps (vanilla, strength twice the cost: 1 mana for 2 up to 6 for 12; Martin removed the 0-mana and the 7 to 10-mana Wisps and the 8-mana Spikes, 2026-11-21), ladders of Flight, Hungry and Spikes, draw cards (Cantrips with "Roar: draw a card.", one "Death: draw a card.", one "Roar: if this removes an enemy, draw a card.") two "Its raids destroy double food." (2 and 4 mana; Martin has no term for raiding yet) and one "Flight. After it raids, draw a card." (5 mana, 5). The Djinn (10 strength), Shades (3 mana) and Hunters are the earlier ladders: each Hunter's Roar gives an adjacent enemy -N strength, for good; the Giant Hunter removes an adjacent enemy. Poison, Armor and Stealth are in the rules but on no card. Three leaders: the Warlord ("When you cover an enemy, gain 1 food."), the Raider ("Your raids destroy 2 more food.") and the Sage. The Food Djinn and Food Shade count the food you gained this game (every gain, the starting 15 not included; Martin, 2026-11-21). Their art is one placeholder sheet painted in a single prompt, infrared to black hole (`design/cards/wisp_sheet.png`), cut into the stand-in figures; the new cards reuse the old ladders' figures.


## What exists

- **Engine** (`animal_kingdom/engine/`): the mana rules only, deterministic and serializable, validating every action.
- **Bot** (`animal_kingdom/bots/greedy.py`): one small greedy bot, the opponent in Practice. It plays a mirror of your deck. Martin: "for all I care it can play random moves, I just want to be able to see the game screen and polish it".
- **Web client** (`./play`): home is Play (against a friend by code or link), Practice (your deck against the bot) and Collection (build decks; the deck shows as a tray of pieces under the grid, `?deckview=list` switches to a side list, both are trials). The match screen tilts the board back 40 degrees with the pieces standing out of their tokens, a den behind each base row showing its food, the leader beside its den, the hands at top and bottom. Every piece is the token Martin set in the rim tool (team frame, stand-in figure, his numerals). The whole look is a plain prototype; the phone layout is not built.
- **Card table** (`./cards`): every card's values and how settled each is.
- **Profiles, friends, chat, match history** on the server. Sign-in with Google or Discord, the feedback e-mail and Discord posts are still in the server code but unreachable from the client.

## Open, roughly in order

1. Whether the mana game plays the way Martin wants: his playtests decide, never bot data ("we will not let bot data drive our decisions", 2026-11-20).
2. Every number above: the curve, the taxes, the food numbers, the hand sizes, the leader powers' price.
3. What the cards and the world are, once the game's shape holds.
4. The match screen and the phone layout, from the reactions of 2026-11-20 (phone first, food in the centre as the one win condition, the leader as scenery, the hand bottom centre).
