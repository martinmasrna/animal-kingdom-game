# 25 Range duel

Every number is a placeholder.

- A line of spaces 1 to 7. Fighter A on space 2, fighter B on space 6. Life 12 each.
- Both have the same 16-card deck, shuffled; draw 4. Energy 3 each.
- **A turn:** both gain 2 energy (cap 6; +1 more after a Rest). Both secretly choose one move: a card from hand or a basic, with its direction where it has a choice, and pay its energy. Reveal. Moves resolve in speed order, lowest first; equal speeds resolve together (both move, then both attacks land).
- **Resolving a move:** first its movement (toward or away from the opponent; you cannot enter or pass the opponent's space; the ends of the line stop you), then its attack: if the distance after moving is inside its range, it hits for its damage, less 3 if the target played Guard this turn. A hit on a fighter whose move has not resolved yet cancels that move (its energy stays spent). Adjacent fighters are at distance 1.
- Two fighters moving toward each other at the same speed with too little room between them share the free spaces equally; an odd middle space stays empty.
- Played cards go to the discard; then each player draws 1 (an empty deck reshuffles the discard).
- **End:** life 0 loses; both at once is a draw. After 20 turns the higher life wins; equal is a draw.

**Basics** (always available): Step (0 energy, speed 3): move 1 toward or away, no attack. Rest (0, speed 5): no movement; 1 extra energy next turn (lost if a hit cancels it).

| Card | Cost | Speed | Movement | Range | Damage | Copies |
|---|---|---|---|---|---|---|
| Jab | 0 | 1 | 0 | 1 | 1 | 3 |
| Punch | 1 | 2 | 1 toward | 1 | 3 | 3 |
| Kick | 1 | 3 | 0 | 1–2 | 3 | 3 |
| Lunge | 2 | 3 | 2 toward | 1 | 4 | 2 |
| Sweep (on hit, push the opponent 1 away) | 2 | 4 | 0 | 1–2 | 3 | 2 |
| Shot | 2 | 2 | 1 away | 3–4 | 2 | 2 |
| Guard (damage to you this turn is 3 less) | 1 | 1 | 0 | | | 1 |

The spec gives Kick range "2"; a single range number is read as "up to that distance" ("inside its range"), so Kick reaches 1–2, like Sweep. Energy, hand size, deck and discard are public; the hand is not.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless.
