# 40 Simultaneous turns

Every number is a placeholder.

- Both players use the same 30-card deck, shuffled, and draw 4. Life 20; bring the other to 0 (both at once is a draw). Up to 6 units a side. There is no first player.
- **Each round:** both players' mana is the round number (cap 10), refilled. Both draw 1; drawing from an empty deck loses 1 life, then 2, then 3.
- **Plan, secretly and at once:** which cards to play (total cost within your mana, units within your free board slots), a target for each Hit among what is on the board now (a unit or a player), and for each of your units an attack target (an enemy unit on the board now, or the enemy player) or no attack.
- **Reveal and resolve:**
  1. All Hits at once: damage is dealt, then destroyed units are removed.
  2. All new units enter. They cannot attack until next round.
  3. All attacks at once: each attacker deals its attack to its target, and each attacked unit deals its attack to every unit attacking it. Then destroyed units are removed. An attack whose attacker or target was destroyed in step 1 does not happen.
- Damage stays. Round cap 60 (a draw); never reached in testing.

Deck, the same for both, 3 copies of each: Striker 1 mana 2/1, Raider 2: 3/2, Guard 2: 2/3, Line 3: 3/4, Heavy 4: 4/5, Big 5: 5/5, Huge 6: 6/7, Hit 2 (1 mana), Hit 3 (2), Hit 6 (4): that much damage to any unit or player.

On the page: tap a unit card to plan it (tap again to take it back), a Hit and then its target, your unit and then what it attacks (tap it twice to keep it home); Go locks the plan. Expert plans without seeing yours.

## Files

`node build.mjs` writes `index.html` (and `artifact.html`); `node sim.mjs [games] [workers]` runs the gate into `report.json`; `node sanity.mjs` the set positions; `node check.mjs` plays the page headless.
