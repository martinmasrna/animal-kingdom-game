# Design principles

What the game should become, and the rules every card is designed against. Read [`../rules/mental-model.md`](../rules/mental-model.md) first; most design mistakes here come from importing Magic/Hearthstone assumptions.

## The game we want

- A small set of distinct archetypes, roughly equal in power, that relate rock-paper-scissors style: each has good and bad matchups, and players choose one by playstyle.
- Pilot skill matters more than deck choice at the margin: a strong player on a slightly weaker deck beats a weaker player on a stronger one.
- The generalist "goodstuff" pile may exist as one archetype (midrange), provided it has predators and isn't the forced best deck. Today it is the forced best deck: see [`goodstuff.md`](goodstuff.md).

**Hard constraints.** No mana or per-card resource cost. No colors or classes that restrict which cards a deck may contain. It stays an open-construction deckbuilding game. Allowed: incentives that reward committing to a family (family-count thresholds) without a hard rule.

## Card design (Martin's four principles)

1. **Strength is paired with commitment.** With no colors and no mana, the strongest cards must demand commitment to a theme or plan. An unconditionally good card must be weaker than a conditional card with the same core effect (the "neutral tax").
2. **Conditional cards have a higher ceiling and a lower floor.** When the condition holds, the card beats its neutral counterpart; when it doesn't, it is worse. Compare against neutral references such as Lion (7, vanilla) or Jerboa (2, "play another unit").
3. **Rock-paper-scissors emerges from the cards.** A card strong against one strategy must leave its deck weak to another.
4. **Cards reward skill:** deckbuilding for the whole meta, long-term planning around both decks' win conditions, and turn-by-turn tactics.

Martin's worked application of these to the aggro deck is in [`../cards/aggro-redesign.md`](../cards/aggro-redesign.md).

**Card text fits three lines on the full card.** Three lines at a size as readable as Hearthstone's caps how much one card may do: complexity goes into keywords and shared wording, not into sentences. About 80 characters is the budget when writing; a natural sentence may run over it as long as it fits, and a sentence is never squeezed (clipped phrases, pronoun shortcuts) to fit. Parentheses are fine where they read naturally ("gain 1 strength (wherever this is)"): players understand them (Martin, 2026-10-08). The web test `cardtext.test.mjs` measures every card. Wording conventions are in [`../rules/keywords.md`](../rules/keywords.md) (card-text conventions).

## Power calibration

There is no mana: every card costs one card and one placement action. Low strength is a drawback, never a lower price.

- **References:** Lion (STR 7) for ground units, Eagle (STR 5) for flyers. Price every effect as strength bought off that body. A utility card should sit near vanilla strength for its role; don't lowball the body to "pay" for an ability.
- **Card ledger:** a Draw action gives 2 cards. "Draw 1" replaces the played card but doesn't refund the action.
- **Draw anchors (commons):** "Roar: draw 1" is a 5 on the ground and a 3 with Flight (placeholders Scout and Courier). "Roar: draw 2" is a 1 on the ground (placeholder Skully): it turns its own placement into a free Draw action, so it is far more than twice draw 1, and an unconditional flying draw 2 doesn't exist. Strength 0 is kept for cards that need it for a specific reason.
- **Removal anchors (commons):** removal is priced by reach. "Remove an adjacent enemy of strength 3 or less" is a 5 (placeholder Sentry), "4 or less" is a 4 (Hunter). An unconditional common "remove any adjacent enemy" doesn't exist; with a real condition it is a 2 (Soldier Ant, Muskrat). A real condition (one that can fail at home) buys +1; a condition that is nearly always met at home buys nothing, the tag is the card's edge (Lynx). Filtering to a tag ("draw a Snake") is worth nothing extra. Selection (Owl: look at 3, keep 1) is anchor −1, since it can't be weaker than the plain draw.
- **Action ledger:** free placements, tokens and deck-to-board effects are action economy, the game's only resource. The cards that break goodstuff open are exactly the ones that manufacture actions.
- **Delay ledger:** a delayed payoff gives up board presence now and hands the opponent a window to answer it.
- **Floor:** price a conditional card for its common failed state, not the screenshot where everything lines up.
- **Closest card:** reject a candidate that an existing card practically dominates, or that practically dominates one.
- **Rarity sets a card's role in its deck, like Gwent's bronze, silver and gold.** Commons (3 copies) are the consistent engine that makes the deck work. Rares (2 copies) are flexible, situational cards for specific use cases. Legendaries (1 copy) are unique, potentially deck-defining cards.
- **Copies change reliability.** Going from one copy to two doubles how often you see a card; going from two to three adds half again. A legendary can't be counted on in a given game, so a game plan is never built on drawing one (unless the deck tutors for it).
- **Rares** are the deck's stronger, more situational cards (conditional or unconditional removal, the reactive answers), or upgrades that would be too much at three copies: with two, drawing one is a real risk and you play it carefully (the Leopard). A rare advances the plan significantly but doesn't win on its own. Heuristic: if you could play three, would you? If not, that often marks a true rare.
- **Legendaries** come in three kinds. The build-around (a deck's whole plan, like Black Swan; few of these). The amplifier, which takes the plan the commons and rares already have and pushes it over the edge, without changing it (King Theron, Queen Adira: Cats play the same with or without them). The generally excellent card, far stronger than a common and good in many decks (Prince Leo and Princess Lea, Aurum, Scarlett). Test: if two copies in a deck would be balanced, it isn't a legendary.
- **A higher rarity gets a better rate, never a worse one.** A rare or legendary with the same effect as a common is at least as strong.

## Guardrails

- No burst extra placements, and an instant-capture audit for every chaining effect near an enemy den.
- No effect that grants a connection-ignoring placement able to reach the den. Flight alone never captures.
- Avoid unconditional body-plus-card cards: a body that replaces itself is already premium.
- A new keyword needs at least three cards that want the exact same rules object.

## Before proposing a card

Run every card in a batch through these, from the opponent's seat, before showing it:

1. **Against the references.** Compare it with Lion (7, vanilla) and with every card that has the same or an overlapping effect. If one has the same effect with more strength or an extra rider, the proposal is dominated. When the size rule forces a small body, give the animal a different effect, never the same one on a smaller body.
2. **Answerable.** The opponent can still beat it by ordinary play, a cover with more strength or a removal ability, without being forced to lose a card every time. An animal that can never be covered is an unbreakable wall.
3. **The trigger fires.** Ask what the opponent will actually do to it. Covering is the everyday answer to small animals and fires no removal trigger, so "when this is removed" on a 1 or 2 is dead text.
4. **It does what it claims.** A 0-strength token blocks nothing (anything covers it); strength on the board defends and dodges removal but never covers anything, since covering is placement from hand.
5. **Balance with numbers.** Fix a card that's too strong through its strength, magnitude or count, never by bolting on a cap or condition.
6. **A real design.** A known keyword with a word added is a patch, not a new mechanic; an animal isn't dropped because one wording fails.

Games imagined while designing are reasoning, not evidence: only real play settles balance.

**Effects speak only of the board's graph:** adjacent, connected, a number of crossroads away, regions. Never rows, columns, lines or directions: maps won't all be grids (Martin, 2026-10-08).

## Theme and naming

- Every card is an animal. No spells, no objects, no places.
- The pool celebrates what evolution made. An animal earns its card by being recognisable, one of a kind (nothing else looks like it to a normal person) and astonishing (the axolotl regrowing its legs, the chameleon changing colour). A group of lookalikes (rodents, small brown birds, most antelopes, most fish) doesn't get fifteen members; but two similar animals can both have cards when their art makes them clearly distinct (Bobcat next to Lynx, Martin, 2026-10-07). The most unique effects go on the most unique animals (Martin, 2026-10-05).
- Let the animal's real behaviour suggest the mechanic: birds fly over lines, elephants hold ground, lemmings swarm.
- **Animal–effect fit** runs both ways: the effect is the best one for the animal (its most famous trait, as a normal person knows it, turned into a rule), and the animal is the best one for the effect (the first animal the effect brings to mind). Rattlesnake (the rattle is the shuffle), Owl (sees what's hidden: Scout), Raven, Cheetah and Falcon have it. A card that passes only one direction is a weak fit.
- Legendaries are a specific named individual of a real species that has a common or rare in the pool (Martin, 2026-10-08: a named animal whose species no card names reads wrong); commons and rares carry species names. Methuselah and Ember are the exceptions still to fix. A legendary's name may evoke myth or folklore but never cites it (no "Bastet").
- One species per pool among commons and rares; subspecies, sex and age variants count as the same species. Legendaries are exempt, being named individuals. Two exceptions: Colony castes (castes of one eusocial species may repeat in Colony when the name gives the caste: Worker Ant, Soldier Ant), and metamorphosis, life stages that look nothing alike and turn into each other (Caterpillar and Butterfly; later a tadpole and a frog) (Martin, 2026-10-08). Never breeds, sexes or other ages.
- No "[adjective] animal" names that most people would see as the same animal (a Martial Eagle next to an Eagle). Species people tell apart are fine (Polar Bear, Grizzly, Black Bear).
- Strength follows the animal's real size, at least for commons and rares (a common Lion is never a 1). The strongest utility effects (extra placements, extra actions, draw) therefore sit on small, low-strength animals, the way Bloodmage Thalnos is a 1/1: rodents are the natural default. A strength-realism pass over the pool is pending (Mouse at 5 is too big) (Martin, 2026-10-05).
- Birds blend together for most people, so a bird gets a card only when a normal person has a clear picture of it no other bird shares (Falcon, the fastest bird; Eagle, the bald eagle; one parrot, never three), and the picture must differ, not only the name (the bald eagle passes next to the Hawk). Across the pool, birds stay around 10% of cards and flyers of every kind (birds, insects, bats) at most 20%, and no habitat's set feels like a bird set (Martin, 2026-10-05).
- No pets and no farm animals. Farm animals appear as their wild forms (aurochs, wild boar); a domestic animal appears only where it lives wild, as a City stray with its City name (Alley Cat, Street Dog). A pet that never lives on its own, like a Goldfish, has no card (Martin, 2026-10-08).
- Tags follow what players believe, not taxonomy, and a tag nobody would miss is left off: the Hyena, a scavenger in the aristocrats deck, carries no Canine tag (Martin, 2026-10-07).
