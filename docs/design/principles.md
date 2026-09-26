# Design principles

What the game should become, and the rules every card is designed against. Read [`../rules/mental-model.md`](../rules/mental-model.md) first; most design mistakes here come from importing Magic/Hearthstone assumptions.

## The game we want

- A small set of distinct archetypes, roughly equal in power, that relate rock-paper-scissors style: each has good and bad matchups, and players choose one by playstyle.
- Pilot skill matters more than deck choice at the margin: a strong player on a slightly weaker deck beats a weaker player on a stronger one.
- The generalist "goodstuff" pile may exist as one archetype (midrange), provided it has predators and isn't the forced best deck. Today it is the forced best deck: see [`goodstuff.md`](goodstuff.md).

**Hard constraints.** No mana or per-card resource cost. No colors or classes that restrict which cards a deck may contain. It stays an open-construction deckbuilding game. Allowed: incentives that reward committing to a tribe (tribe-count thresholds) without a hard rule.

## Card design (Martin's four principles)

1. **Strength is paired with commitment.** With no colors and no mana, the strongest cards must demand commitment to a theme or plan. An unconditionally good card must be weaker than a conditional card with the same core effect (the "neutral tax").
2. **Conditional cards have a higher ceiling and a lower floor.** When the condition holds, the card beats its neutral counterpart; when it doesn't, it is worse. Compare against neutral references such as Lion (7, vanilla) or Jerboa (2, "play another unit").
3. **Rock-paper-scissors emerges from the cards.** A card strong against one strategy must leave its deck weak to another.
4. **Cards reward skill:** deckbuilding for the whole meta, long-term planning around both decks' win conditions, and turn-by-turn tactics.

Martin's worked application of these to the aggro deck is in [`../cards/aggro-redesign.md`](../cards/aggro-redesign.md).

## Power calibration

There is no mana: every card costs one card and one placement action. Low strength is a drawback, never a lower price.

- **References:** Lion (STR 7) for ground units, Eagle (STR 5) for flyers. Price every effect as strength bought off that body. A utility card should sit near vanilla strength for its role; don't lowball the body to "pay" for an ability.
- **Card ledger:** a Draw action gives 2 cards. "Draw 1" replaces the played card but doesn't refund the action.
- **Action ledger:** free placements, tokens and deck-to-board effects are action economy, the game's only resource. The cards that break goodstuff open are exactly the ones that manufacture actions.
- **Delay ledger:** a delayed payoff gives up board presence now and hands the opponent a window to answer it.
- **Floor:** price a conditional card for its common failed state, not the screenshot where everything lines up.
- **Closest card:** reject a candidate that an existing card practically dominates, or that practically dominates one.
- Rarity doesn't pay for a weak rate. It changes copy count and how singular a pattern may be.

## Guardrails

- No burst extra placements, and an instant-capture audit for every chaining effect near an enemy HQ.
- No effect that grants a connection-ignoring placement able to reach the HQ. Flight alone never captures.
- Avoid unconditional body-plus-card cards: a body that replaces itself is already premium.
- A new keyword needs at least three cards that want the exact same rules object.
- Mechanics must work on a tabletop too: no hidden bookkeeping only software could track.

## Theme and naming

- Every card is an animal. No spells, no objects, no places.
- Let the animal's real behaviour suggest the mechanic: birds fly over lines, elephants hold ground, lemmings swarm.
- Rarity follows how exotic the animal is. Commons are everyday animals, rares exotic ones, legendaries a specific named individual of a real species. A legendary's name may evoke myth or folklore but never cites it (no "Bastet").
- One species per pool among commons and rares; subspecies, sex and age variants count as the same species. Legendaries are exempt, being named individuals.
