# 25 Range duel

Every number here is a placeholder.

**The question.** When two fighters on a line choose moves at the same time, and a move's speed, range and cost decide who hits, does reading distance and energy carry a duel?

## Setup

- A line of spaces 1 to 7. Fighter A on space 2, fighter B on space 6. Life 12 each.
- Each player has the same 16-card deck, shuffled, and draws 4. Energy 3 each.

## A turn

1. Both gain 2 energy (cap 6).
2. Both secretly choose one move: a card from hand or a basic (always available). A move that lets you choose a direction is chosen now. Pay its energy.
3. Reveal. Resolve in speed order, lowest first. Equal speeds resolve together: both move, then both attacks land.
4. Resolving a move: first its movement (toward the opponent or away; you cannot enter or pass the opponent's space, and the ends of the line stop you), then its attack: if the distance after moving is inside its range, it hits for its damage, less any Guard on the target this turn. A hit on a fighter whose move has not resolved yet cancels that move (its energy stays spent).
5. Played cards go to the discard; each player draws 1 (shuffle the discard when needed).

Distance is the difference between the two spaces; adjacent fighters are at distance 1.

## Basics

- **Step** (0 energy, speed 3): move 1 toward or away. No attack.
- **Rest** (0 energy, speed 5): no movement; gain 1 extra energy next turn.

## Cards (16, both players)

| Card | Cost | Speed | Movement | Range | Damage | Text | Copies |
|---|---|---|---|---|---|---|---|
| Jab | 0 | 1 | 0 | 1 | 1 | | 3 |
| Punch | 1 | 2 | 1 toward | 1 | 3 | | 3 |
| Kick | 1 | 3 | 0 | 2 | 3 | | 3 |
| Lunge | 2 | 3 | 2 toward | 1 | 4 | | 2 |
| Sweep | 2 | 4 | 0 | 1–2 | 3 | On hit, push the opponent 1 away. | 2 |
| Shot | 2 | 2 | 1 away | 3–4 | 2 | | 2 |
| Guard | 1 | 1 | 0 | | | Damage to you this turn is 3 less. | 1 |

## End

Life 0 loses; both at once is a draw. After 20 turns, the higher life wins; equal is a draw.

## Builder notes

- Simultaneous: the Expert estimates each pair of moves by rollouts, solves the matrix game for a mixed strategy and samples from it; it never sees the opponent's choice.
- Greedy: the highest-damage move that hits if the opponent stays where it is; Step toward when none does.
- There is no first player; the seat check reports fighter A's win rate (the start is mirrored).
- Set positions: lethal (the opponent on 1 life at distance 1: Jab, speed 1, hits before anything else); don't waste (never Shot at distance 1, since retreating 1 leaves the opponent at 2, outside its range); don't pay for nothing (at distance 5 no card can reach after its movement: Step or Rest, never a paid attack).
