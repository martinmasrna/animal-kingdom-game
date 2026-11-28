# 22 Possession

Every number here is a placeholder.

**The question.** When ball position and possession form a tug-of-war settled by simultaneous card choices priced in stamina, does reading the opponent's next play beat any fixed mix?

## Setup

- A pitch of zones 0 to 8. Player A scores at zone 8, player B at zone 0. The ball starts at zone 4; a random player has possession.
- Each player has the same 16-card deck, shuffled, and draws a hand of 4.
- Stamina: 10 each.
- The match is 20 plays. After play 10 both players gain 4 stamina (cap 10).

## A play

1. Both players secretly choose one option: the player in possession an attacking option, the other a defending option. An option is either a basic (always available, not a card) or a card from hand of the right side. Pay its stamina cost; an option you cannot pay for cannot be chosen.
2. Reveal both and apply the table.
3. Each player who played a card draws 1 (reshuffle the discard when the deck is empty).

Attacking options: **Walk** (basic, 0): +1 zone. **Shoot** (basic, 1): only when the ball is within 2 zones of the goal you attack (A: zone 6 or more; B: zone 2 or less). **Pass** (card, 1): +2. **Long** (card, 2): +3. **Dribble** (card, 1): +1.

Defending options: **Stand** (basic, 0). **Block** (basic, 1). **Tackle** (card, 1). **Intercept** (card, 1). **Press** (card, 2).

| Attacker \ Defender | Stand | Block | Tackle | Intercept | Press |
|---|---|---|---|---|---|
| Walk | no gain | +1 | turnover | +1 | turnover |
| Pass | +2 | +2 | turnover | turnover | turnover |
| Long | +3 | +3 | +3 | turnover | +3 |
| Dribble | +1 | +1 | +1 | +1 | turnover |
| Shoot | goal | turnover | goal | goal | goal |

- Gains move the ball toward the goal the attacker scores at; the ball never passes the last zone (it stops on 8 or 0).
- Turnover: possession changes, the ball stays where it is.
- Goal: the attacker scores 1, the ball returns to zone 4 and the conceding player takes possession.

## End

After 20 plays, more goals wins; equal is a draw.

## Deck (16 cards, both players)

Pass ×3, Long ×2, Dribble ×3, Tackle ×3, Intercept ×3, Press ×2. A card can only be played on its side: attacking cards while in possession, defending cards while defending.

## Builder notes

- Simultaneous: the Expert should estimate the value of each option pair by rollouts, solve the small matrix game for a mixed strategy (fictitious play or regret matching is enough) and sample from it. It must never read the opponent's choice.
- Greedy: always the most expensive affordable option of its side; Shoot whenever in range.
- The first-player check reads kickoff possession: the rate at which the player with first possession wins must lie within 30–70%.
- Set positions: free goal (in range and the defender has 0 stamina, so cannot Block: Shoot); don't waste (the attacker has 0 stamina, so can only Walk: Tackle, not Press).
