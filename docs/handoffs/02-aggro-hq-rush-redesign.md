# Handoff 02 — Aggro HQ-rush redesign

You are a game designer continuing the **Aggro HQ Rush** redesign. Develop a coherent, testable
proposal; do not change deck files, card data, engine code, configuration, tests, or the active run.

## Read first, in order

1. `CLAUDE.md`
2. `docs/STATUS.md`
3. `docs/rules/mental-model.md`
4. `docs/cards/decks/README.md`
5. `docs/cards/decks/aggro-hq-rush.md`
6. `docs/balance/aggro-redesign.md` — read in full; it contains agreed principles, candidates, and traps
7. `docs/cards/expansion-design-todo.md`

## Objective

Aggro wins through committed forward pathing and timely HQ capture. It should punish slow, greedy
decks but lose clearly to suitable walls, stabilizers, and removal. Do not turn it into generic
flyers, removal, and draw.

This game has two actions per turn, no mana, no combat damage, and no health. Clearing a blocker
without occupying its crossroad often cannot convert the opening in one turn. Flight ignores
connection but does not capture the HQ. Treat these as hard design facts.

## Questions to resolve

1. Which failure modes matter most: reaching the HQ front, taking it, exploiting an opening, or refilling?
2. Which three mechanisms from `aggro-redesign.md` create one deck rather than a pile of strong cards?
3. Which existing cards should be kept, retired, reworked, or deferred—and why?
4. How does the proposal preserve counterplay and avoid instant-capture / unrestricted-placement traps?
5. What evidence separates a card problem from the bot blind spot around row-1/3 HQ lanes?

## Required output

Write `docs/cards/aggro-redesign-session-YYYY-MM-DD.md` with:

- A one-sentence identity plus how the deck wins and loses.
- Ranked failure-mode diagnosis with citations.
- One recommended 30-card direction: retained roles, retire/rework candidates, and up to six additions.
  Each addition must state its fence, payoff, floor, and counterplay; names/numbers remain provisional.
- A compact setup → pressure → HQ-capture dependency map.
- An RPS hypothesis: prey, predator, and expected weak matchup pattern.
- A later test plan using TurnBot and RefereeBot, ≥200 games/matchup and both seats, with bot caveats.

Do not declare cards ready to ship. Avoid Magic/Hearthstone language unless translated into this
game's action and connection model.

## Done when

The proposal makes one sharp deck more likely, rather than increasing the good-stuff card supply.

