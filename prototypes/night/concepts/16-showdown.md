# 16 Showdown

Every number here is a placeholder.

**The question.** When cards cost mana and the mana each player spends on a hidden hand is public, do bluffing and betting on the hand you bought carry a duel?

## Setup

- Each player has the same 24-card deck, shuffled. Chips (your life): 20 each.
- A random player is the first player of round 1; the first player alternates every round.

## A round

1. **Ante**: each player puts 1 chip in the pot (2 from round 6, 3 from round 11). A player who cannot pay the ante loses.
2. Each player draws up to 5 cards (shuffle the discard into the deck when needed).
3. **Buy**: at the same time, each player secretly chooses up to 3 cards from hand as its line, paying their costs from 6 mana (unspent mana is lost). Then the mana each spent is shown.
4. **Betting**: the first player checks or bets 2. If it checks, the second player checks (go to showdown) or bets 2. Facing a bet, a player calls (adds the same), raises (adds 2 more than the bet; each player may raise once per round) or folds.
5. **Showdown**: both lines are revealed; the higher total power takes the pot. Equal: the pot is split, an odd chip to the second player.
6. **Fold**: the other player takes the pot; the folded line is discarded unseen.
7. Line cards go to the discard pile. Cards left in hand stay there.

## End

A player with no chips, or unable to pay the ante, loses. After 20 rounds, more chips wins; equal is a draw.

## Cards (24, both players)

| Card | Cost | Power | Text | Copies |
|---|---|---|---|---|
| Low | 0 | 1 | | 4 |
| Mid | 1 | 3 | | 4 |
| High | 2 | 5 | | 4 |
| Top | 4 | 9 | | 3 |
| Bluff | 3 | 0 | | 3 |
| Mirror | 2 | | Power equal to the opponent's highest card that is not a Mirror (0 if none). | 2 |
| Spike | 1 | 2 | If your line wins at showdown, the opponent also pays you 2 chips. | 2 |
| Solo | 0 | 4 | Power 0 unless it is the only card in your line. | 2 |

## Builder notes

- Hidden information: the Expert determinizes the opponent's line from the unseen cards consistent with the mana it spent, and never reads it.
- Greedy: buys the highest-power line it can afford, bets or raises with power 9 or more, otherwise checks and always calls.
- Caller (a second trivial bot): buys like Greedy and always calls, never bets.
- The first-player check reads the first player of round 1.
- Set positions: free win (your line's power beats any line the opponent's shown spend can buy: never fold, and raise); lethal (the opponent has 2 chips left behind and your line cannot lose: bet); don't waste (never buy a Bluff into a line you will check and call down anyway, since it adds no power and the spend is the only thing it buys).
