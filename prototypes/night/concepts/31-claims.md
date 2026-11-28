# 31 Claims

Every number here is a placeholder. Borrowed: Coup's claim and challenge, where any claim may be a bluff, a challenged honest claim costs the challenger and a caught bluff costs the bluffer. The rest is not that game: a unit duel with mana, where the claim is which card you are playing.

**The question.** When any card can be played as a claimed better card and the opponent may challenge, do bluffing and counting copies carry a duel?

## Setup

- Both players use the same known list: 8 cards, 3 copies each (24 cards, list below). Each shuffles its own deck. Life 20. Board max 5 units.
- Random first player; the first player draws 3, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn; never claimed or challenged).
- Discard piles are face-up.

## Turn

1. Your maximum mana goes up by 1 (cap 10) and refills. Your units become ready. Draw 1. Drawing from an empty deck loses 1 life, then 2, then 3.
2. **Play by claim**: put a card from hand face-down, name any card on the list, and pay the named card's cost.
3. The opponent may **challenge** at once.
   - Not challenged: the card works as the named card. A unit enters face-down with the named stats and is that card for the rest of the game; a spell resolves as named.
   - Challenged, and the card is the named card: it is turned face-up, the challenger loses 3 life, and the card resolves.
   - Challenged, and the card is not the named card: it is turned face-up and discarded with no effect, the mana stays spent, and the player who claimed loses 3 life.
4. Units attack HS-style: each ready unit that was not played this turn may attack an enemy unit (both deal their attack to each other; damage stays) or the enemy player.
5. End the turn.

A face-down card turns face-up when it leaves play (destroyed unit, resolved spell), so the true card always ends up visible in the discard pile.

## End

Life 0 or less loses; both at once is a draw.

## Cards (the list; 3 copies each)

| Card | Cost | Attack/Health | Text |
|---|---|---|---|
| Striker | 1 | 2/1 | |
| Guard | 2 | 1/4 | |
| Raider | 2 | 3/2 | |
| Line | 3 | 3/4 | |
| Heavy | 5 | 5/6 | |
| Hit 3 | 2 | | 3 damage to a unit or player |
| Blast | 4 | | 5 damage to a unit or player |
| Draw 2 | 2 | | Draw 2 cards |

## Builder notes

- Hidden information: the Expert determinizes the opponent's hand and face-down units from the copies not yet seen, and never reads them.
- Greedy: always plays honestly, the most expensive affordable card; challenges only when all three copies of the named card are already visible.
- Random: random claims (half honest), challenges a third of the time.
- Set positions: free challenge (all three Blasts are face-up in the discards and the opponent names Blast: challenge); lethal (the opponent on 5 life, Blast in hand and 4 mana: play it honestly); don't die for nothing (on 3 life, never challenge unless every copy of the named card is in sight, since a failed challenge ends the game).
