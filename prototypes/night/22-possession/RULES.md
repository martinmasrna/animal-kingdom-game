# Possession

Two players, a ball, a pitch of zones 0 to 8. Player A scores at zone 8, player B at zone 0. Most goals after 20 plays wins; equal is a draw.

- **Start.** The ball is on zone 4; a random player has it. Each player has the same 16-card deck, shuffled, and a hand of 4. Stamina 10 each.
- **A play.** Both players choose at once and in secret: the player with the ball an attacking option, the other a defending option. An option is a basic (always there) or a card of the right side from hand. Pay its stamina; an option you cannot pay for cannot be chosen. Reveal both and apply the table. Each player who played a card draws 1 (the discard pile is reshuffled when the deck is empty).
- After play 10 both players gain 4 stamina (cap 10).

Attacking: **Walk** (basic, 0), **Shoot** (basic, 1; only within 2 zones of the goal you attack: A on zone 6 or more, B on zone 2 or less), **Pass** (card, 1), **Long** (card, 2), **Dribble** (card, 1).
Defending: **Stand** (basic, 0), **Block** (basic, 1), **Tackle** (card, 1), **Intercept** (card, 1), **Press** (card, 2).

| Attacker \ Defender | Stand | Block | Tackle | Intercept | Press |
|---|---|---|---|---|---|
| Walk | no gain | +1 | turnover | +1 | turnover |
| Pass | +2 | +2 | turnover | turnover | turnover |
| Long | +3 | +3 | +3 | turnover | +3 |
| Dribble | +1 | +1 | +1 | +1 | turnover |
| Shoot | goal | turnover | goal | goal | goal |

- Gains move the ball toward the attacker's goal and stop on the last zone. Turnover: the ball changes hands where it is. Goal: the attacker scores 1, the ball returns to zone 4 and the side that conceded gets it.

Deck (both players): Pass ×3, Long ×2, Dribble ×3, Tackle ×3, Intercept ×3, Press ×2.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`): you (A, attacking to the right) against Expert; kickoff possession alternates. `node sim.mjs` runs the gate and writes `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays whole matches through the page's calls in node and by clicks in Chrome.
