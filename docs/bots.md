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
- **The human gap:** in Martin's reverse gauntlet (2026-09-29, 10 games a deck with each premade against the goodstuff pile piloted by RefereeBot) he won 50%, where RefereeBot piloting the same decks gets 26%; Egg 5 of 10 against the bots' 8%, Ramp 8 of 10 against 38%. The gap is the pilot, not the pile: the same bot pilots the pile in both.
- **Hoarding (the biggest measured flaw):** RefereeBot spends 30-34% of its actions drawing where Martin spends 17-27%, and leaves its Roar cards in hand (Viper played 0.44 times a game it is drawn against his 1.30, Owl 1.02 against 2.10, Termite Queen 0.83 against 1.50). Cause: `effect_readiness` pays 16 points per live Roar held in hand, and `card_economy` counts hand size against the opponent's, while a 7-strength unit on the board is worth 3.5 points of `board_presence`. In Martin's Canine position (tests/puzzles/canine_develop) the bot scores Draw 36 against a Wolf's 22 and draws to eight cards.
- **Readiness is also a den-race proxy:** removing it (or the learned linear eval, which drops it) fixes the hoarding puzzles but costs Aggro and Canine about 12 points against the pile, almost all in den captures won and lost. Counting at most one live Roar (`readiness_cap=1`) recovers Canine but not Aggro, whose early draws are right (Martin draws there too). One weight can't be right for both decks; the value of holding a card depends on the hand and the board, which is what the value network is for.
- **Known blind spots:** the region-control term overvalues the middle row, so bots never contest the flank rows as a den-rush lane. Cats beat aggro about 87% in sims, while Martin's play went 2 of 3 to aggro: the bots dump their hand where they should hold disruption. That matchup is a pilot flaw, not a card problem.

## The learned evaluator

Self-play TD(λ) (`learn/td.py`, `learn/train.py`) fits the weights of a linear evaluation.

- **rung-0** learns weights for the 11 hand-written terms. It beats the hand weights on 6 of 7 decks and is the shipped learned eval (`rung0.json`); `rung0_identity.json` reproduces the hand weights.
- **rung-1** added 13 dynamics features and regressed on 5 of 7 decks (food_otk −20 points). Cause: several new features duplicate rung-0 terms, and an unregularized fit on raw features moved weight toward self-play's majority rush dynamic. Training converged, so it wasn't undertrained.
- A better evaluation alone may not close the planning gap: the egg-vs-cats gap may need search depth plus a good leaf evaluation (the horizon problem quiescence search and extensions solve in chess). The search's pruning has its own horizon bug: it ranks a candidate by its half-resolved position, before its own sub-choice (a target, a kept card, an extra placement) resolves, so Owl never reached RefereeBot's search in any of the 18 turns Martin played it. `quiesce=1` resolves those sub-choices greedily before ranking; it is off by default and not yet benchmarked.

Train with `.venv/bin/python -m animal_kingdom.learn.train --out results/learn/<run>` and promote with `animal_kingdom.learn.promote`.

- **Outcome-fitted linear (2026-09-30):** a logistic fit of the rung-1 features on the outcomes of 5,600 RefereeBot games predicts winners better than the hand eval (held-out log-loss 0.570 against 0.591) but loses Aggro and Canine by 12-13 points as a pilot. Unconstrained, it credits what merely correlates with winning (fewer cards left in deck, live Roars in hand), which a search then exploits; sign constraints and dropping those terms remove the exploit but also the readiness term's den-race value.

## The value network

A small network over the rung-2 features (rung 1 plus hand and board context: Roars in hand against live ones, hand strength, fliers, affordable food cards, hand cards sharing a tag with the board, engines on the board, extra actions coming, den-front defence), trained on who won self-play games and iterated: train, let TurnBot play the next round with it, retrain.

- `learn/selfplay.py` plays TurnBot games (hand eval or a network) across all 36 pairings of the premades and the pile, 5% random moves, and records the positions the search scores; about 4,000 games (150k positions) in 40 minutes on 8 cores.
- `learn/net.py` fits one hidden ReLU layer on outcomes (split by game, a linear fit alongside as the yardstick) and writes a `NetEval` artifact (`bots/net_eval.py`, stdlib inference, scaled into hand-eval points). Load it as any learned eval: `referee_learned:eval=<path>`.
- Round 0 (hand-eval pilots) and round 1 (TurnBot on the round-0 net, trained on both rounds, 317k positions): the network predicts winners better than a linear fit on the same inputs, held-out log-loss 0.562 against 0.585.
- As RefereeBot's evaluation, round 1 against RefereeBot on the pile (`results/bot_quality/net-r1-vs-gs`, 200 paired games a deck): Colony +20.5 [+13.5, +28], Food +8.5 [+1.5, +15.5], Canine +6.5, Cats +4.5, Ramp −2.5, Egg −2, Aggro −8.5 [−17.5, +0.5]. Aggro loses its den race as with every other replacement for the readiness term: den wins 41 → 25, den losses 36 → 45, Rat spent more eagerly. About 1.5x slower than the hand eval.

## Throughput

The complete-turn search is bushy, not deep: turn trees are only 2 to 6 plies but explode in breadth on combo decks. The shipped levers are a node budget (`TURN_MAX_SEARCH_NODES=80`, byte-identical play on all decks) and collapsing Owl/Raven's keep-or-shuffle choices to the top 2 in lookahead. food_otk remains the slowest deck, about 13× greedy.

Untried: a transposition cache keyed on the existing hidden-info-safe position digest (`TurnSearcher._observation_key`), since placing A then B reaches the same board as B then A. Also killer-move ordering in the turn beam.

## Measuring a bot change

Use the paired benchmark: `.venv/bin/python -m animal_kingdom.sim.bot_comparison --games 200 --out results/bot_quality/<name>`, with `--baseline-kind` / `--candidate-kind` (for example `turn:deck_reveal_choice_width=0`). A change must improve or tie every deck, not just the average. `--opponents goodstuff` measures every deck against the pile, which is the matchup Martin's gauntlet measured, and the run keeps its game logs under `<out>/logs/`. A weight override goes in the bot spec: `referee:w.effect_readiness=0`. Mirror self-play is too noisy for small pilot changes; always compare against a fixed opponent.

Freeze the misplayed position as a puzzle in `tests/test_bot_puzzles.py` before fixing it. The strongest puzzles are real positions from bot games that Martin has judged: saved as `GameState` snapshots in `tests/puzzles/`, shown to him in the client's lab view (`#/lab/<name>`, card text on hover), asserting the set of moves he accepts (a guard puzzle asserts a move the bot already gets right). Puzzles catch specific misplays but don't prove strength: readiness at 0 passes all of them and still loses games.
