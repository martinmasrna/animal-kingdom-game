# Bots

The bots have two jobs: the AI opponent people play against, and the pilots whose games produce balance data. Both jobs hit the same limit, which is judgement about the future.

## The ladder

| Kind | What it does | Cost vs greedy | In the game UI |
|---|---|---|---|
| `random` | uniform legal moves; the floor | — | Easy |
| `greedy` | one-ply search over a hand-written board evaluation | 1× | Normal |
| `turn` | plans its complete current turn across sampled hidden worlds (determinization), no opponent reply | ~8–14× | Hard |
| `referee` | `turn` plus the opponent's reply turn, played by greedy in each sampled world | ~50–100× | Expert |
| `*_learned` | the same search driven by a learned linear evaluation (`data/learned/rung0.json`) | same as base | — |

All share one evaluation: `bots/greedy_bot.py` holds the terms and `bots/features.py` the feature code. Search knobs live at the top of `sim/runner.py`.

## Invariants

- **Generalist:** no deck slugs, archetype names or card ids in bot policy; deck knowledge comes from generic features (tags, keywords, geometry).
- **Honest:** bots never read the opponent's hand or deck order. Determinization samples hidden cards from public information only; regression tests enforce it.
- **Never nerf a card to fix a bot.** Every sim finding is either a card signal or a pilot flaw, and the two get different fixes.

## How far to trust them

- TurnBot beats greedy on every deck, and RefereeBot beats TurnBot on every deck by roughly 4 to 14 points. The gaps differ per deck, so a TurnBot matrix is directional: it underrates the decks it underplays (ramp, canine, egg) and overrates the ones it plays near-optimally.
- **The structural ceiling: no bot plans across turns.** The evaluation scores the current position. The `pending_payoff` term credits single delayed payoffs (hatching Eggs, bear timers), but no bot can play a multi-turn grow-then-win plan: a human piloting egg into cats won about 50% of games where the bots win about 24%. Treat any "loses" verdict for a scaling deck (egg, ramp) as unproven until a human has played it.
- **Known blind spots:** the region-control term overvalues the middle row, so bots never contest the flank rows as an HQ-rush lane. Cats beat aggro about 87% in sims, while Martin's play went 2 of 3 to aggro: the bots dump their hand where they should hold disruption. That matchup is a pilot flaw, not a card problem.

## The learned evaluator

Self-play TD(λ) (`learn/`) fits the weights of a linear evaluation.

- **rung-0** learns weights for the 11 hand-written terms. It beats the hand weights on 6 of 7 decks and is the shipped learned eval (`rung0.json`); `rung0_identity.json` reproduces the hand weights.
- **rung-1** added 13 dynamics features and regressed on 5 of 7 decks (food_otk −20 points). Cause: several new features duplicate rung-0 terms, and an unregularized fit on raw features moved weight toward self-play's majority rush dynamic. Training converged, so it wasn't undertrained.
- **Next experiment:** standardize the features, add L2, and merge the duplicates (the scheduled-payoff pair and `pending_payoff`, HQ distance and HQ threat, income and region control). Then add conditional features such as "food × holding food payoffs". If a well-built linear eval still plateaus, that is the evidence to try a small neural net; time a forward pass at the search's leaf-eval rate first.
- A better evaluation alone won't close the planning gap. The egg-vs-cats gap needs search depth plus a good leaf evaluation: this is the horizon problem that quiescence search and extensions solve in chess.

Train with `.venv/bin/python -m animal_kingdom.learn.train --out results/learn/<run>` and promote with `animal_kingdom.learn.promote`.

## Throughput

The complete-turn search is bushy, not deep: turn trees are only 2 to 6 plies but explode in breadth on combo decks. The shipped levers are a node budget (`TURN_MAX_SEARCH_NODES=80`, byte-identical play on all decks) and collapsing Owl/Raven's keep-or-shuffle choices to the top 2 in lookahead. food_otk remains the slowest deck, about 13× greedy.

Untried: a transposition cache keyed on the existing hidden-info-safe position digest (`TurnSearcher._observation_key`), since placing A then B reaches the same board as B then A. Also killer-move ordering in the turn beam.

## Measuring a bot change

Use the paired benchmark: `.venv/bin/python -m animal_kingdom.sim.bot_comparison --games 200 --out results/bot_quality/<name>`, with `--baseline-kind` / `--candidate-kind` (for example `turn:deck_reveal_choice_width=0`). A change must improve or tie every deck, not just the average. Freeze the misplayed position as a puzzle in `tests/test_bot_puzzles.py` before fixing it. Mirror self-play is too noisy for small pilot changes; always compare against a fixed opponent.
