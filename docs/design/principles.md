# Design principles

What the game should become, and the rules every card is designed against. Read [`../rules/mental-model.md`](../rules/mental-model.md) first; most design mistakes here come from importing Magic/Hearthstone assumptions.

## The game we want

- A small set of distinct archetypes, roughly equal in power, that relate rock-paper-scissors style: each has good and bad matchups, and players choose one by playstyle.
- Pilot skill matters more than deck choice at the margin: a strong player on a slightly weaker deck beats a weaker player on a stronger one.

**Hard constraints.** No mana or per-card resource cost. No colors or classes that restrict which cards a deck may contain. It stays an open-construction deckbuilding game. Allowed: incentives that reward committing to a family (family-count thresholds) without a hard rule.

## Card design (Martin's four principles)

1. **Strength is paired with commitment.** With no colors and no mana, the strongest cards must demand commitment to a theme or plan. An unconditionally good card must be weaker than a conditional card with the same core effect (the "neutral tax").
2. **Conditional cards have a higher ceiling and a lower floor.** When the condition holds, the card beats its neutral counterpart; when it doesn't, it is worse. Compare against neutral references such as Lion (7, vanilla) or Mole (2, "play another unit").
3. **Rock-paper-scissors emerges from the cards.** A card strong against one strategy must leave its deck weak to another.
4. **Cards reward skill:** deckbuilding for the whole meta, long-term planning around both decks' win conditions, and turn-by-turn tactics.

**Cards serve play styles, not precons.** Tactical play and deep deckbuilding are the game's two equal pillars, and deckbuilding needs cards that are simple, flexible and playable in many decks, each card fitting a theme or play style rather than one pre-constructed list, never needing five other cards to be useful. The Black Bear ("in 2 turns, draw 2 cards") is the model: never in a swarm or board-buff deck, but at home in combo, control and Handlock. The Rat is another: its random discard costs a Cockroach deck nothing, and costs an aggro deck nothing either, since aggro empties its hand fast. A handful of cards may be good only with their own deck's engine; the whole collection may not (Martin, 2026-10-12 and 2026-10-26).

**Dawn and Dusk effects are automatic.** A start- or end-of-turn effect involves no choice and no optional "you may" (Martin, 2026-10-13).

**Don't build solitaire decks.** A plan that needs three or four of its own animals uncovered on the board at once (an outlet, fodder and the payoffs that count it) is solitaire: the opponent either covers one piece and breaks it, or ignores it and watches (Martin, 2026-10-13).

**Card text fits three lines on the full card.** Complexity goes into keywords and shared wording, not into sentences. About 80 characters is the budget when writing; a natural sentence may run over it as long as it fits, and a sentence is never squeezed (clipped phrases, pronoun shortcuts) to fit (Martin, 2026-10-08). The web test `cardtext.test.mjs` measures every card. Wording conventions are in [`../rules/keywords.md`](../rules/keywords.md) (card-text conventions).

## Power calibration

There is no mana: every card costs one action. Low strength is a drawback, never a lower price. Free placements, tokens and deck-to-board effects are action economy, the game's only resource. A delayed payoff gives up board presence now and hands the opponent a window. A conditional card is priced for its common failed state, not the screenshot where everything lines up. A candidate that an existing card strictly dominates, or that strictly dominates one, is rejected.

The references are the live cards, never a table: the Lion (7, vanilla) and the Eagle (5, Flight) for bodies, and for an effect, the cards that already carry it or its nearest shape, at the same rarity and strength (the sheet, `tools/cards/check.py`, prints them). How a condition is priced (Martin, 2026-10-22):

- A conditional effect is priced by what meeting its condition costs on the turn you play it. Board state already there, or a body the deck wants gone, costs nothing; a condition that takes the turn's other action, or extra plays, costs the card strength.
- Flight is worth what the flier can cover when it lands, so on a 1 or 2 it is little more than reach.

## Rarity

The rarity question is what goes wrong if the opponent faces this card three times a game, never which slot its deck has free (Martin, 2026-10-22). His calls so far: [`log_rarity.md`](log_rarity.md).

- **Rarity sets a card's role in its deck, like Gwent's bronze, silver and gold.** Commons (3 copies) are the consistent engine that makes the deck work. Rares (2 copies) are flexible, situational cards for specific use cases. Legendaries (1 copy) are unique, potentially deck-defining cards.
- **Rares** are the deck's stronger, more situational cards (conditional or unconditional removal, the reactive answers) with more complicated effects, or upgrades that would be too much at three copies: with two, drawing one is a real risk and you play it carefully (the Leopard). A rare advances the plan significantly but doesn't win on its own.
- **Legendaries** come in three kinds:
  1. The build-around (a deck's whole plan, like Black Swan; few of these).
  2. The amplifier, which takes the plan the commons and rares already have and pushes it over the edge, without changing it (King Theron, Queen Adira: Cats play the same with or without them).
  3. The generally excellent card, far stronger than a common and good in many decks (Prince Leo and Princess Lea, Aurum, Scarlett).
- **No common plays another card.** An extra play is a rare's or a legendary's effect. A common may still place a token, since it goes on a random empty crossroad ("I don't think there should be extra placement common cards"; "the extra tokens are fine cause they only go on empty crossroads and it's random as well", Martin, 2026-10-27).
- **A card that is one keyword and nothing else is a common** (Martin, 2026-10-21). A rare or legendary with a keyword earns its rarity with something more: a second keyword or an effect.
- **A higher rarity gets a better rate.** A rare must be stronger than a common, and a legendary stronger than a rare, if they were to have the same effect. Ideally they shouldn't, so this is only an anchor (Martin, 2026-10-26).

## Guardrails

- No burst extra placements, and an instant-capture audit for every chaining effect near an enemy den.
- No effect that grants a connection-ignoring placement able to reach the den.
- No infinite combos.
- A new keyword needs at least three cards.
- Unconditional generic effects (removal of any size, extra actions, extra plays, card-advantage engines) go on a tagless animal (Raccoon, Opossum, Mole, Bat, ...) (Martin, 2026-10-16).

## Before proposing a card

The sheet (`tools/cards/check.py`) prints the lookups for a card: the keyword rulings, the pool, the cards at its rarity and strength, the record, the grid, the text fit. Then, from the opponent's seat:

1. **Against the references.** The body against the Lion, the effect against every card with the same or an overlapping effect; a rare or legendary against the common with that effect, which it must beat. If one has the same effect with more strength or an extra rider, the proposal is dominated. When the size rule forces a small body, give the animal a different effect, never the same one on a smaller body.
2. **Answerable.** The opponent can still beat it by ordinary play, and they don't lose the game if they can't answer it instantly.
3. **A real design.** A known keyword with a word added is a patch, not a new mechanic; an animal isn't dropped because one wording fails.

Games imagined while designing are reasoning, not evidence: only real play settles balance.

## Theme and naming

- Every card is an animal.
- The pool celebrates what evolution made. An animal earns its card by being recognisable, one of a kind (nothing else looks like it to a normal person) and astonishing (the axolotl regrowing its legs, the chameleon changing colour). A group of lookalikes (rodents, small brown birds, most antelopes, most fish) doesn't get fifteen members; but two similar animals can both have cards when their art makes them clearly distinct (Martin, 2026-10-07).
- **Animal–effect fit** runs both ways: the effect is the best one for the animal (its most famous trait, as a normal person knows it, turned into a rule), and the animal is the best one for the effect (the first animal the effect brings to mind). Rattlesnake (the rattle is the shuffle), Owl (sees what's hidden: Scout), Raven, Cheetah and Falcon have it. Ideally, the most unique effects go on the most unique animals.
- One species per pool among commons and rares; subspecies, sex and age variants count as the same species. Two exceptions: Colony castes, and metamorphosis, life stages that look nothing alike and turn into each other (Caterpillar and Butterfly; later a tadpole and a frog). (Martin, 2026-10-08).
- Legendaries are a specific named individual of a real species that has a common or rare in the pool (Martin, 2026-10-08).
- No "[adjective] animal" names that most people would see as the same animal (a Martial Eagle next to an Eagle). Species people tell apart are fine (Polar Bear, Grizzly, Black Bear).
- Strength follows the animal's real size, at least for commons and rares (a common Lion is never a 1). The strongest utility effects (extra placements, extra actions, draw) therefore sit on small, low-strength animals (Martin, 2026-10-05).
- No pets and no farm animals. Farm animals appear as their wild forms (Martin, 2026-10-08).
