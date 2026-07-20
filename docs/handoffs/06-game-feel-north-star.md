# Handoff 06 — Game-feel north star

You are a game-design strategist. Write a concise decision charter for the intended *Animal Kingdom*
player experience. It should guide future card, deck, balance, bot, and UI choices without changing
rules. This session is conceptual and documentation-only.

## Read first

1. `CLAUDE.md`
2. `docs/STATUS.md`
3. `docs/rules/mental-model.md`
4. `docs/rules/overview.md` and `docs/rules/keywords.md`
5. `docs/balance/design-handoff.md`
6. `docs/balance/goodstuff-investigation.md`
7. `docs/balance/aggro-redesign.md`
8. `docs/cards/decks/README.md` and the seven deck files

## Design context

The game is open-construction and has no mana, colors/classes, combat damage, or attack/health
model. The desired result is several distinct, roughly equal decks with meaningful good and bad
matchups; the good-stuff generalist may remain, but needs predators. Skill should matter at the
margin. Some apparent deck weaknesses are bot-planning failures, so frustration is not automatically
a power-level mandate.

## Required output

Write `docs/meta/game-feel-north-star-YYYY-MM-DD.md` with:

- A one-paragraph north-star statement.
- Five to seven design pillars, each with a positive rule and anti-goal.
- A player journey: opening, contested midgame, conversion/endgame, and post-game learning.
- Desired tensions: action economy, connection/pathing, strength thresholds, region food, deck commitment.
- Accepted frustrations/tradeoffs and why they are acceptable.
- A checklist for future card, deck, TUI, bot, and balance work.
- A final "Not decided here" section for data- or taste-dependent questions.

Do not invent foundational constraints or contradict locked rules. When docs disagree, surface the
conflict and defer to canonical rules rather than silently resolving it.

## Done when

A future agent can judge whether an idea makes the game more like the game the project intends.

