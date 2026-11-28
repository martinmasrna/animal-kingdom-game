# 21 Round purse

Every number here is a placeholder. Borrowed: Gwent's match structure, best of three rounds where a round ends when both players have passed and the higher total power wins it. The rest is not that game: one mana purse for the whole match pays for every card.

**The question.** When the whole match has one mana purse and rounds are won by total power, is choosing which rounds to fight, and when to pass, a real decision?

## Setup

- Each player has the same 20-card deck, shuffled, and draws 8. Each has a purse of 18 mana for the whole match.
- A random player starts round 1; the other starts round 2; round 1's starter starts round 3.

## A round

1. At the start of rounds 2 and 3, each player draws 2 (hand max 10).
2. Starting with the round's starter, players alternate turns. On your turn, play one card (paying its cost from your purse) or pass. A player who has passed takes no more turns this round; the other keeps playing until it passes too.
3. When both have passed, the higher total power on a side wins the round; equal: nobody wins it.
4. Every card on the table goes to its owner's discard pile.

## End

The first player to win 2 rounds wins. After 3 rounds without that, more rounds won wins; equal is a draw.

## Cards (20, both players)

| Card | Cost | Power | Text | Copies |
|---|---|---|---|---|
| Grunt | 0 | 1 | | 4 |
| Troop | 1 | 3 | | 4 |
| Squad | 2 | 5 | | 3 |
| Heavy | 3 | 7 | | 3 |
| Big | 5 | 11 | | 2 |
| Gift | 0 | | Put 4 power on the opponent's side this round; you draw 2 cards. | 2 |
| Cut | 2 | | Destroy the opponent's highest-power card this round. | 2 |

## Builder notes

- Greedy: while behind or level, plays its highest-power affordable card; passes when ahead; in the deciding round it never passes while behind.
- The first-player check reads the starter of round 1.
- Set positions: cheapest win (the opponent has passed and you trail by 2 with Troop and Big in hand: play Troop); don't waste (the opponent has passed and you are ahead: pass); lethal (round 3, the opponent has passed on 10, you are on 5 with Heavy in hand and 3 mana: play it).
