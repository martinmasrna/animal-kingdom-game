# 43 Auto deck battle

Every number here is a placeholder. Borrowed: the front-unit autobattle of Super Auto Pets, where each team's front unit strikes the other's at the same time, a fallen unit is replaced by the next in line, and gold each round buys units from a shop. The rest is not that game: the team is a shuffled deck, drawn in random order.

**The question.** When the fight resolves itself and the only skill is what you buy into your deck, is building enough of a game?

## Setup

- Each player's deck starts as 3 Pips. Deck max 10 cards. Life 10 each.
- Both decks' contents are public at all times; shops are private.

## A round

1. **Shop**, both players at the same time and in secret: 6 gold each (unspent gold is lost). Your shop shows 4 cards drawn at random from the pool of the 8 cards below (unlimited copies, equal odds, independent for each player).
   - Buy a shop card: pay its cost; it joins your deck.
   - Reroll: 1 gold, 4 new shop cards.
   - Remove: 1 gold, take a card out of your deck (once per round).
2. **Battle**: both decks are shuffled. The top card of each is its side's front card. Each step, the two front cards deal their attack to each other at the same time; a card at 0 health or less falls (it stays in your deck for later rounds), and the next card of that deck becomes the front card, its "enters" text happening then. Damage lasts for this battle only.
3. The battle ends when a side has no front card and no cards left to draw. The other side wins and deals 1 damage plus 1 per card it still has (front and undrawn), at most 4. Both sides out at the same step: no damage.

## End

Life 0 loses; both at once is a draw. After 12 rounds, the higher life wins; equal is a draw.

## Pool (8 cards)

| Card | Cost | Attack/Health | Text |
|---|---|---|---|
| Pip | 1 | 1/2 | |
| Brawler | 2 | 3/2 | |
| Wall | 2 | 1/5 | |
| Bomb | 3 | 2/1 | When it falls, 3 damage to the enemy front card. |
| Opener | 3 | 2/3 | Enters: 2 damage to the enemy front card. |
| Rally | 3 | 1/3 | When it falls, your next front card gets +2/+2. |
| Guardian | 3 | 2/4 | Takes 1 less damage from each hit. |
| Heavy | 4 | 4/6 | |

## Builder notes

- Simultaneous: shops are hidden from each other; the Expert evaluates buys by simulating battles against samples of what the opponent's public deck may become.
- Greedy: buys the most expensive affordable cards until gold runs out; never rerolls or removes.
- There is no first player; the seat check reports seat A's win rate.
- Set positions: don't waste (6 gold, a deck of 5 and four affordable cards in the shop: don't end the shop with all 6 unspent); free removal (a deck at 10 holding Pips, a Heavy in the shop and 5 gold: remove a Pip and buy the Heavy); lethal (the opponent on 1 life: any battle win ends it, so maximise the chance to win the battle rather than the damage).
