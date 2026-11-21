# Status

The map. Read it first each session and keep it current: when something here changes, rewrite the line, don't append to it.

## Where this is going

*Animal Kingdom* is a two-player card game Martin is designing, meant to become a digital game people play competitively. The path: design a game that is fun and deep (only humans can judge it), get other people playing it, stabilise the rules and cards, balance it, go public.

**Now: designing the mana game.** On 2026-11-20 Martin made the mana ruleset the whole game ("Literally nothing else than what's currently on the staging server (and localhost 8000) matters") and the old rules, their 71 animals, bots and tools were deleted. The game is set in a world of our own, not on Earth (Martin, 2026-11-19: "I thought about it and it's 1000% the right decision"), and its cards are not traditional Earth animals (Martin, 2026-11-20: "alltogether, at least the traditional Earth animals"). What the cards and the world are instead is open. Every number and rule below is a working version from his playtests, not settled.

What the game is for, why mana, and Martin's words on the rules' shape and the board: [`design.md`](design.md).

## The rules as they play

- **Board:** 19 pointy-top hex tiles in rows of 3, 4, 5, 4, 3 (`data/maps.json` `map_hex19`), your side at the bottom. Each player's row of 3 is their base, where their connection starts and where either player may place. Behind each base is its den.
- **Mana:** on your Nth turn you have min(N, 10) mana, lost at the end of the turn. A card costs its `cost`; a leader's power costs 3 (the Elf's 2) and can be used once a turn (Martin, 2026-11-21). Anything an effect puts into play is free.
- **Cards:** opening hands of 3 (first player) and 4 (second), a mulligan, one free card at the start of each turn, the first player's first turn included (Martin, 2026-11-21), no other draw.
- **Covering:** a card placed on an enemy it is stronger than covers it, and a covered card, yours or theirs, is removed.
- **Zero strength:** an animal at 0 strength is removed, by the rules (Armor doesn't hold), each time the effects finish resolving (Martin, 2026-11-21: "make it a general rule").
- **Food:** both start at 15; each region (three tiles) a player holds pays 1 food at the end of their turn; 30 food wins, 0 loses. A card placed or moved into the enemy den, connected through one of their base tiles, destroys food equal to its strength (at most what the den holds) and is spent.
- **Turns:** a turn ends when its player ends it; no turn ends or is skipped by itself.
- **Decks:** 25 cards, 2 copies of a card, 1 of a legendary, one leader.

## The cards

53 in `data/cards.json`, all collectible but the Spore token (Flight is 1 to 6 mana, strength equal to its cost), all placeholders. Most are Martin's paper cards of 2026-11-21: the Wisps (vanilla, strength twice the cost: 1 mana for 2 up to 6 for 12; Martin removed the 0-mana and the 7 to 10-mana Wisps and the 8-mana Spikes, 2026-11-21), ladders of Flight, Hungry and Spikes, draw cards (Cantrips with "Roar: draw a card.", one "Death: draw a card.", one "Roar: if this removes an enemy, draw a card.", and Scout 2 (2 mana, 1), "Roar: Scout a card.", Scout being the old game's look at the top 3, take one, shuffle the rest back), and the Spores (Martin, 2026-11-21): Duplicating Spore, "Roar: place a Spore on an adjacent tile." (any tile a card could be placed on) and Mama Spore, "Roar: put 2 Spores into your hand.", Duplicating Spore 1 mana 1 and Mama Spore 2 mana 2; the Spore itself is a 1-mana 1 token in no deck (status reserve); the Rhino (8 mana, 10), "Roar: remove all adjacent enemies with strength 5 or less.", and the Albatross (8 mana, 4, Flight), "... with strength 4 or less.", and their young, the Young Rhino (4 mana, 6), "... with strength 3 or less.", and Young Albatross (4 mana, 2, Flight), "... with strength 2 or less." (Martin, 2026-11-21: animals of another planet, despite the rule against Earth animals) two "Its raids destroy double food." (2 and 4 mana; Martin has no term for raiding yet) and one "Flight. After it raids, draw a card." (5 mana, 5). The Mana Blob (2 mana, 2), "Roar: gain 2 mana.", this turn's, past the cap too (Martin, 2026-11-21). The Djinn and Hunters are the earlier ladders: each Hunter N (1 to 6) costs N, has strength N and its Roar gives an adjacent enemy -N strength, for good (Martin, 2026-11-21; their ids are hunter_2 to hunter_7, one above their numbers); the Big Game Hunter (5 mana, strength 2) removes an adjacent enemy. Poison, Armor and Stealth are in the rules but on no card. Five leaders, each a legendary 5-mana card with an ability of its own when played (Martin, 2026-11-21: the Elf 3, "Your regions produce 1 more food." while on the board; the Assassin 5, "Roar: reduce the cost of cards in your hand by 1."; the Sage 3, "Roar: reduce the cost of your hero power by 1."; the Warlord and the Raider plain 10s), and as leader: the Warlord ("When you cover an enemy, gain 1 food."), the Raider ("Your raids destroy 1 more food."), the Sage (power: draw a card), the Elf (power, 2 mana: "Gain 1 food for each region you control.") and the Assassin ("After every third card you play in a turn, draw a card."). The four Djinn are strength 10 and 12 mana, above the mana cap, and cost 1 less for each card in your hand or ally, the Region Djinn 2 less for each region you control and the Combo Djinn 2 less for each card you played this turn (Martin, 2026-11-21, who also dropped the Shades; a strength that is a count stays in the engine, on no card). Their art is one placeholder sheet painted in a single prompt, infrared to black hole (`design/cards/wisp_sheet.png`), cut into the stand-in figures; the new cards reuse the old ladders' figures.


## What exists

- **Engine** (`engine_rs/`, Rust): the mana rules only, deterministic and serializable, validating every action, the one implementation of them. It is the Python module `ak_engine`, built by `./play`, `./test` and `./cards` whenever its source moved; the server, the tools and the tests reach it through `animal_kingdom/game.py`, which holds no rules. About 4 million clone-and-apply pairs a second on one core. How a card's effect is added: `engine_rs/README.md`.
- **Bot**: the opponent in Practice is one small greedy bot (`animal_kingdom/bot.py`, on the engine through the Python module); it plays a mirror of your deck. The search bots and their benchmark are in `engine_rs/src/bots/` (`tools/bot_bench/README.md`) and are not wired into Practice.
- **Web client** (`./play`): home is Play (against a friend by code or link), Practice (your deck against the bot) and Collection (build decks; the deck shows as a tray of pieces under the grid, `?deckview=list` switches to a side list, both are trials). The match screen tilts the board back 40 degrees with the pieces standing out of their tokens, a den behind each base row showing its food, the leader beside its den, the hands at top and bottom. Every piece is the token Martin set in the rim tool (team frame, stand-in figure, his numerals). The whole look is a plain prototype; the phone layout is not built.
- **Patch notes** (`static/patch.js`, a window over the game): numbered patches from 0.0.1 (Martin, 2026-11-21), each the rules that changed as bullets Martin redlined (`web/patches/VERSION.md`) and every card and hero power changed, added or removed since the last patch as the cards before and after (`tools/patch/build.py`, which diffs the game against the last patch's snapshot). A Patch Notes button in home's top bar opens it, and a new patch opens once by itself, on whatever screen the game loads, for a returning player.
- **Card table** (`./cards`): every card's values and how settled each is.
- **Profiles, friends, chat, match history** on the server. Sign-in with Google or Discord, the feedback e-mail and Discord posts are still in the server code but unreachable from the client.

## Open, roughly in order

1. Whether the mana game plays the way Martin wants: his playtests decide, never bot data ("we will not let bot data drive our decisions", 2026-11-20).
2. Every number above: the curve, the taxes, the food numbers, the hand sizes, the leader powers' price.
3. What the cards and the world are, once the game's shape holds.
4. The match screen and the phone layout, from the reactions of 2026-11-20 (phone first, food in the centre as the one win condition, the leader as scenery, the hand bottom centre).
