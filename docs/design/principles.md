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

**Card text is at most 80 characters.** That is three lines on the full card at a size as readable as Hearthstone's, and it caps how much one card may do: complexity goes into keywords and shared wording, not into sentences. `test_card_text_length.py` enforces it. Wording conventions that keep texts short are in [`../rules/keywords.md`](../rules/keywords.md) (card-text conventions).

## Power calibration

There is no mana: every card costs one card and one placement action. Low strength is a drawback, never a lower price.

- **References:** Lion (STR 7) for ground units, Eagle (STR 5) for flyers. Price every effect as strength bought off that body. A utility card should sit near vanilla strength for its role; don't lowball the body to "pay" for an ability.
- **Card ledger:** a Draw action gives 2 cards. "Draw 1" replaces the played card but doesn't refund the action.
- **Draw anchors (commons):** "Battlecry: draw 1" is a 5 on the ground and a 3 with Flight (placeholders Scout and Courier). "Battlecry: draw 2" is a 1 on the ground (placeholder Skully): it turns its own placement into a free Draw action, so it is far more than twice draw 1, and an unconditional flying draw 2 doesn't exist. Strength 0 is kept for cards that need it for a specific reason.
- **Removal anchors (commons):** removal is priced by reach. "Remove an adjacent enemy of strength 3 or less" is a 5 (placeholder Sentry), "4 or less" is a 4 (Hunter). An unconditional common "remove any adjacent enemy" doesn't exist; with a real condition it is a 2 (Soldier Ant, Muskrat). A real condition (one that can fail at home) buys +1; a condition that is nearly always met at home buys nothing, the tag is the card's edge (Lynx). Filtering to a tag ("draw a Snake") is worth nothing extra. Selection (Owl: look at 3, keep 1) is anchor −1, since it can't be weaker than the plain draw.
- **Action ledger:** free placements, tokens and deck-to-board effects are action economy, the game's only resource. The cards that break goodstuff open are exactly the ones that manufacture actions.
- **Delay ledger:** a delayed payoff gives up board presence now and hands the opponent a window to answer it.
- **Floor:** price a conditional card for its common failed state, not the screenshot where everything lines up.
- **Closest card:** reject a candidate that an existing card practically dominates, or that practically dominates one.
- **Rarity sets a card's role in its deck, like Gwent's bronze, silver and gold.** Commons (3 copies) are the consistent engine that makes the deck work. Rares (2 copies) are flexible, situational cards for specific use cases. Legendaries (1 copy) are unique, potentially deck-defining cards.
- **A higher rarity gets a better rate, never a worse one.** A rare or legendary with the same effect as a common is at least as strong.

## Guardrails

- No burst extra placements, and an instant-capture audit for every chaining effect near an enemy HQ.
- No effect that grants a connection-ignoring placement able to reach the HQ. Flight alone never captures.
- Avoid unconditional body-plus-card cards: a body that replaces itself is already premium.
- A new keyword needs at least three cards that want the exact same rules object.
- Mechanics must work on a tabletop too: no hidden bookkeeping only software could track.

## Theme and naming

- Every card is an animal. No spells, no objects, no places.
- Let the animal's real behaviour suggest the mechanic: birds fly over lines, elephants hold ground, lemmings swarm.
- Legendaries are a specific named individual of a real species; commons and rares carry species names. A legendary's name may evoke myth or folklore but never cites it (no "Bastet").
- One species per pool among commons and rares; subspecies, sex and age variants count as the same species. Legendaries are exempt, being named individuals.
- No "[adjective] animal" names that most people would see as the same animal (a Martial Eagle next to an Eagle). Species people tell apart are fine (Polar Bear, Grizzly, Black Bear).
- Tags follow what players believe, not taxonomy: Hyena is a Canine because most players would ask why it isn't (Martin, 2026-09-28).
