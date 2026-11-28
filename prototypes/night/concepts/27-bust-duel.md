# 27 Bust duel

Every number here is a placeholder.

**The question.** When both players push their luck from their own decks side by side, can stopping, pushing and buying make a duel rather than two solitaires?

## Setup

- Each player's starting deck (10 cards): Step 1 (power 1) ×4, Step 2 (power 2) ×3, Risk 3 (power 3, strain 1) ×2, Crack (power 0, strain 2) ×1. Shuffle.
- The market deck (22 cards, list below) is shuffled; 5 cards lie face-up, refilled at once when one is bought.
- Life 15 each. A random player is the first player of round 1; the first player alternates every round.

## A round

1. **Lines.** Starting with the round's first player, players alternate one action at a time: **Draw** (reveal the top card of your own deck into your line; when your deck is empty, shuffle your discard into it) or **Stop**. A player who stops or busts takes no more actions this round; the other continues alone. Both lines are face-up.
2. **Bust.** If the total strain in your line reaches 4 or more, you bust: your line's power counts as 0.
3. **Clash.** The higher line power wins the round. The loser loses life equal to the difference, at least 1 and at most 5. Equal: nobody loses life.
4. **Buy.** Each player gets coin equal to its own line's power (2 if busted) and may buy one face-up market card costing no more than that; it goes to the buyer's discard. The round's loser buys first; on a tie, the round's first player buys first.
5. Both lines go to their owners' discard piles.

Effects marked "on draw" happen when the card is revealed into a line.

## End

Life 0 loses. After 15 rounds, the higher life wins; equal is a draw.

## Market (22 cards)

| Card | Cost | Power | Strain | Text | Copies |
|---|---|---|---|---|---|
| Step 3 | 3 | 3 | 0 | | 4 |
| Step 4 | 5 | 4 | 0 | | 3 |
| Big 6 | 6 | 6 | 1 | | 3 |
| Calm | 3 | 1 | −1 | | 3 |
| Spoil | 4 | 1 | 0 | On draw: the opponent's line gains 1 strain, even if they have stopped. | 3 |
| Peek | 2 | 1 | 0 | On draw: look at the top card of your deck. | 2 |
| Trim | 3 | 0 | 0 | When bought: remove one card in your discard pile from the game. | 2 |
| Surge | 7 | 8 | 2 | | 2 |

## Builder notes

- Greedy: draws while its strain is 1 or less, or while its power is below the opponent's line; buys the most expensive affordable card.
- Pusher (the racer here): draws until its strain reaches 3, ignoring the opponent's line.
- The first-player check reads the first player of round 1.
- Set positions: don't push for nothing (the opponent busted and you are ahead: Stop); free draw (no strain card is left in your draw pile: Draw); lethal (the opponent has stopped, is on 2 life and you lead by 2: Stop).
