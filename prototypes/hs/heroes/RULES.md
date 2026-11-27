# Hero HS

A throwaway toy for one question: on the genre's usual card-duel rules, with one shared pool of plain cards, do three heroes make three different games? It grows out of `../vanilla/` (same rules unless stated here). Nothing here is decided; names are plain descriptions and every number is a placeholder. Where a line is Martin's it says so; the rest are an agent's placeholders of 2026-11-27 for him to change.

What the toy has to show: each hero builds a visibly different deck from the same pool, the two sides of a pairing take different roles, and no pairing is a walkover. Martin's own deck lists and games are the evidence; bot numbers are only a smoke alarm.

## Rules that differ from Vanilla HS

- **Energy, two ways to win** (Martin, 2026-11-27: "either bring enemy hero down to 0 or yourself up to 50"). Each hero starts at 25 energy. At 0 or less you lose; at 50 or more you win. Damage destroys energy, it is not stolen. Gaining has no cap below 50. Checked after every action; if both happen at once the player whose turn it is wins.
- **Deck** (Martin, 2026-11-27): your hero's card plus 20 cards from the pool, at most 2 copies of each. No other one-copy cards exist.
- **The hero's card starts in your hand** (Martin: "maybe the Hero card even starts in your hand"), on top of the opening hand of 3 (first) or 4 plus the Coin (second).
- **Hero:** a passive that is always on, and an active ability usable once on each of your turns for its mana cost.
- Fatigue as in Vanilla (1, 2, 3 ... energy lost per missing draw) unless a hero says otherwise.

## The pool (30 cards; Martin reviewed the slate on 2026-11-27 and set the numbers marked M)

Minions, mana: attack/health.

| Role | Cards |
|---|---|
| Plain bodies | 1: 2/1 · 1: 1/2 · 2: 3/2 · 2: 2/3 · 3: 3/4 · 4: 4/5 · 6: 6/7 · 7: 7/7 |
| Taunt (must be attacked first) | 3: 2/4 · 4: 3/5 · 6: 5/6 (M) |
| Rush at once | 3: 3/1, can attack the turn it is played |
| Bodies that draw | 2: 1/1, when played draw a card · 2: 2/1, when it dies draw a card · 5: 4/4, when played draw a card |
| Bodies that hit | 1: 1/1, when played deal 1 damage · 4: 2/4, when played deal 2 damage (any minion or hero) |
| Bodies that gain or grow | 3: 3/3 (M), when played gain 3 energy · 3: 2/3, at the end of your turn gain 1 energy · 2: 1/3, gains +1 attack at the start of each of your turns |
| Damage spells (any minion or hero) | 1: deal 2 · 2: deal 3 · 4: deal 6 |
| Area spells (enemy minions only, M) | 2: deal 1 to all (M) · 4: deal 2 to all (M) · 7: deal 4 to all |
| Card and value spells | 3: draw 2 cards · 5: destroy a minion |
| Buff and gain spells | 2: give a minion +2/+2 · 3: gain 5 energy |

The two gain cards that are not Martin's numbers: the 3-mana 2/3 that gains 1 a turn and "gain 5 for 3" replace the slate's "heal 6 for 2", which was priced as a delay and is too cheap once gaining is a way to win.

## The three heroes

Translated from three of Martin's leaders for the board game (their text is about cards and decks, so it carries over). "Strength" became attack and health; food became energy.

| | Pyromancer (aggro) | Angel Warrior (midrange) | Mage (control) |
|---|---|---|---|
| Passive | Your active ability upgrades after every 3 uses. | After your minion kills an enemy minion and survives, it gains +1/+1. | Fatigue gains you energy instead of losing it. |
| Active | (2) Add a Fireball to your hand. | (1) Give a friendly minion +2 attack (for good). | (3) Draw a card. |
| Hero card | 3 mana 3/3: when played, upgrade every Fireball in your hand; they keep their cost. | 6 mana 6/6: at the start of your turn, your other minions gain +1/+1. | 4 mana 4/6. When your deck is empty it becomes, wherever it is, an 8-mana 8/8 with "when played, gain 10 energy". |

Fireball ladder (a spell, any minion or hero): Baby 1 mana deal 1, Young 2 mana deal 3, Adult 4 mana deal 6, Elder 6 mana deal 10. The active adds a Baby at first, the next size after each third use. An upgraded Fireball in hand moves one step up the ladder and keeps the cost it had.

A Fireball is a card from outside the deck, but always the same known one, so the opponent can count it.

## Readings the build chose (an agent's, 2026-11-27, where the text above left a choice)

- The 3-mana 3/1 can attack anything the turn it is played, the enemy hero included (the card's text, not Hearthstone's Rush).
- The Angel Warrior's passive counts fights only, on either player's turn (attacking or attacked); a kill by a spell or a when-played hit does not count.
- The Pyromancer's power adds a Baby on uses 1 to 3, a Young on 4 to 6, an Adult on 7 to 9, an Elder from the 10th on. An Elder that is upgraded stays an Elder.
- The Mage's hero card turns into the 8-mana 8/8 the moment the last card leaves the deck. On the board it becomes a fresh 8/8 and keeps whether it can attack this turn.
- The Mage's fatigue counter still climbs 1, 2, 3 ...; each step is gained instead of lost.
- "Both at once" means both players meet a win condition after the same action (one at 50 while the other is at 0, or both at 50, or both at 0).
- A when-played hit is aimed when the minion is played and lands before the minion enters, so it cannot hit itself. Damage spells, hits and the buff may target either side; the destroy spell any minion.
- Start-of-turn effects happen before the turn's draw; a dies-draw happens after every death of that action is resolved.
- No hand limit, as in Vanilla. A match that reaches turn 100 (50 each) is a draw, as in Vanilla.
- The page's deck lists: yours shows what is left in your deck; his shows the cards he has not played yet (deck and hand together), since his hand is hidden.

## Default decks (found by bot search, a starting point)

`node search.mjs`: from a hand-picked aggro, midrange and control list, five rounds of one-copy swaps per hero, each kept only if Greedy's win rate against the other two heroes' current lists rose over 600 games and held on 600 fresh ones (about 15 minutes in all). The Mage was still climbing when it stopped, and the three lists drifted toward each other (the same burn and the 7-mana sweeper in all three), so they say more about what Greedy plays well than about each hero's identity.

- **Pyromancer**: 1: 1/1 deal 1 ×2 · 1: deal 2 ×2 · 2: 2/1 dies: draw · 2: 3/2 · 2: deal 3 ×2 · 3: 3/4 · 3: 3/1 attacks at once · 4: 2/4 deal 2 · 4: 4/5 ×2 · 4: deal 6 ×2 · 4: 3/5 Taunt · 5: destroy ×2 · 7: 4 to all ×2
- **Angel Warrior**: 1: 1/1 deal 1 ×2 · 1: deal 2 · 2: 2/1 dies: draw ×2 · 2: 1/3 grows · 2: 2/3 · 2: deal 3 · 3: 3/4 ×2 · 3: 2/4 Taunt · 4: 4/5 ×2 · 4: deal 6 ×2 · 4: 3/5 Taunt · 6: 6/7 ×2 · 6: 5/6 Taunt · 7: 4 to all
- **Mage**: 1: 1/1 deal 1 ×2 · 1: 2/1 ×2 · 1: deal 2 · 2: 1/1 draw ×2 · 2: 2/1 dies: draw · 2: deal 3 ×2 · 3: 3/3 gain 3 ×2 · 4: 2/4 deal 2 ×2 · 4: deal 6 ×2 · 4: 3/5 Taunt · 5: destroy · 7: 4 to all ×2

No default list plays the 1/2, the 7/7, the 4/4 that draws, the 2/3 that gains 1 a turn, the two cheaper sweepers, draw 2, +2/+2 or gain 5.

## The page and the scripts

`node build.mjs` writes `index.html` and `artifact.html`: pick both heroes (or a random opponent), build your 20, play against Expert. Who goes first alternates; the two numbers by Decks count your wins and Expert's for that pairing, kept in your browser (the page works without storage). `node sanity.mjs` is the set-position check every shipped bot passes; `node stats.mjs [deals] [bot]` prints the pairings; `node soak.mjs` plays thousands of random-deck games; `node tune.mjs A B` compares two bots.
