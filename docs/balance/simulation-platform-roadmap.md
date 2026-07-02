# Simulation Platform Roadmap

## Purpose

Reliable balance simulation is a core product feature of Animal Kingdom. The long-term
goal is not merely to build a bot that wins more games. It is to produce balance conclusions
that remain useful when pilot strength, strategy, search depth, and hidden information vary.

A single bot inevitably introduces policy bias. If Colony wins 20% with one pilot and 48%
with another, its true balance has not been measured accurately enough. The correct
conclusion is that the matchup is **pilot-sensitive** and the current result is unreliable.

The durable solution is therefore a calibrated simulation platform composed of:

1. a fast production pilot for high-volume simulation;
2. a much stronger, honest reference searcher for calibration;
3. multiple competent policies to expose strategy-dependent results;
4. human-game calibration;
5. reports that quantify both balance and confidence in the pilot model.

## Target architecture

```text
Rules engine
    |
    v
Strong information-set search ("oracle")
    |
    | labels difficult positions and candidate actions
    v
Fast learned policy/value bot
    |
    v
Large paired-seed cross-play simulations
    |
    v
Policy-sensitivity, oracle, and human calibration
    |
    v
Balance reports with reliability grades
```

No production policy should contain deck slugs, archetype names, or individual card IDs.
Deck-specific knowledge should emerge from generic rules, state features, search, and
training data.

## The bot ladder

### GreedyBot: fast baseline

GreedyBot remains valuable as:

- a deterministic performance baseline;
- a regression opponent;
- a quick rules-engine smoke test;
- a deliberately limited policy that helps reveal sequencing requirements.

Its results should not be treated as authoritative balance measurements.

### TurnBot: near-term production pilot

TurnBot is the next default candidate for large simulations. It searches through the end of
its own turn, allowing it to understand draws, action ordering, pending choices, Battlecry
chains, and effect-granted actions without paying for a full opponent rollout.

TurnBot should be evaluated separately for every deck against the complete field of fixed
GreedyBot opponents, using paired seeds. It becomes the default report pilot only after it:

- improves every deck rather than merely improving aggregate win rate;
- avoids material regressions in individual matchups;
- wins mirrors against GreedyBot consistently;
- remains deterministic and acceptably fast;
- passes generic sequencing, hidden-information, and HQ-safety tests.

TurnBot is an important production component, but not the final source of truth. It still
scores the opponent's future only indirectly and will retain strategic blind spots.

### Reference SearchBot: calibration oracle

RefereeBot is the first prototype of the expensive calibration tier. Its successor should
be a genuinely strong information-set searcher that:

- never reads the real hidden hand or deck order;
- searches complete turns and credible opponent replies;
- samples hidden worlds consistently;
- keeps decisions identical across indistinguishable information sets;
- uses transposition tables and state hashing to reuse work;
- supports configurable search budgets;
- reports convergence and action confidence;
- can use a stronger opponent policy than GreedyBot;
- remains entirely generalist.

Possible later techniques include information-set MCTS, deeper determinized search, or a
hybrid search with learned policy and value priors. The exact algorithm is less important
than honest information handling, reproducibility, and demonstrated strength across every
deck.

This searcher does not need to run the full balance report. It should run smaller,
statistically useful calibration cohorts and label difficult positions.

### Fast learned policy/value bot

Once the reference searcher is trustworthy, use it to create a fast production policy:

1. collect representative positions from self-play, cross-play, regressions, and human
   games;
2. ask the reference searcher to score legal actions and resulting positions;
3. train generic policy and value models from those labels;
4. validate the student against GreedyBot, TurnBot, historical versions, and the oracle;
5. use the trained model directly for bulk simulation and as a prior inside search;
6. feed high-disagreement and high-error positions back into the training set.

This is an oracle-to-student loop: expensive search supplies quality, while the learned bot
supplies throughput. Machine learning should be introduced only after the rules engine,
state representation, reproducible datasets, and reference labels are stable.

## Do not rely on one production policy

Even a strong learned bot can settle into one strategic style. Balance reports should
eventually include a small population of competent pilots, such as:

- the current production policy;
- the reference searcher on a smaller cohort;
- the previous released production policy;
- independently trained policies or generic evaluation-weight variants.

Deck results should be measured under pilot cross-play, not only symmetric self-play. This
separates three questions:

1. **Card-pool balance:** can the deck win when piloted competently?
2. **Execution difficulty:** how much strength does the deck gain from a better pilot?
3. **Meta sensitivity:** does the result depend heavily on one policy's strategic style?

Large variation across pilots is itself an important result. It should lower the reliability
grade rather than being averaged away silently.

## Standard simulation design

Every serious comparison should be reproducible and paired wherever possible.

Record at least:

- engine, card-data, map, configuration, and bot versions;
- bot parameters and search budgets;
- deck pair, seats, first player, and seed;
- winner, win condition, turn count, and final food;
- cards observed or drawn;
- runtime and termination reason.

Use:

- identical seed schedules for before/after comparisons;
- both seat assignments where the experiment permits;
- per-deck and per-matchup results, never aggregate results alone;
- confidence intervals on changes;
- fixed regression cohorts for historical comparison;
- raw per-game records so every aggregate can be regenerated.

Large runs should support checkpointing, resumption, parallel execution, and deterministic
aggregation.

## Reliability metrics

A future balance report should present both the estimated outcome and evidence that the
estimate is trustworthy.

For every matchup, report:

- win rate and confidence interval;
- first-player and seat effects;
- win-condition distribution;
- game length and final-food distribution;
- pilot-strength sensitivity;
- policy-population spread;
- search-budget or depth convergence;
- production-versus-reference disagreement rate;
- mirror pilot advantage;
- sample size and effective paired sample size;
- human-calibration coverage;
- runtime and simulation version metadata.

A compact reliability grade can summarize these signals:

- **A — calibrated:** stable across competent pilots and search budgets, with human support;
- **B — credible:** stable across bot policies and reference spot checks;
- **C — provisional:** adequate sample size but meaningful policy or depth sensitivity;
- **D — unreliable:** weak pilot, unresolved disagreement, or inadequate evidence.

The grade must never conceal the underlying measurements.

## Human calibration

Simulation ultimately needs contact with real play. Preserve human game records and use
them to answer:

- Do bots choose the same tactical actions as strong humans?
- Do simulated matchup rankings predict human matchup rankings?
- Which decks show the largest human-versus-bot performance gap?
- Which positions create the most policy disagreement?
- Are bots producing realistic win conditions and game lengths?

Maintain a curated position suite containing:

- obvious tactical wins and defensive necessities;
- multi-action sequencing puzzles;
- delayed-payoff and resource-conversion decisions;
- hidden-information decisions;
- representative positions for every deck;
- failures discovered in human games or simulation audits.

The suite should test decisions, not encode deck-specific production behavior.

## Delivery phases

### Phase 1 — Establish the scalable baseline

- Complete and validate TurnBot.
- Add paired per-deck bot-quality benchmarks.
- Version simulation inputs and preserve raw game records.
- Make pilot identity prominent in every report.
- Keep GreedyBot results as a historical baseline.

Exit condition: TurnBot is demonstrably stronger for every deck, sufficiently fast for the
normal report, and deterministic.

### Phase 2 — Make the reference tier trustworthy

- Profile and optimize the shared search implementation.
- Add state hashing, transposition caching, and explicit search budgets.
- Strengthen opponent-reply modeling.
- Measure search-budget convergence per deck and matchup.
- Build a permanent oracle calibration cohort.

Exit condition: increasing the reference search budget rarely changes conclusions, and the
reference policy beats production pilots across the full deck field.

### Phase 3 — Add policy sensitivity to reports

- Run production, historical, alternate, and reference policies in controlled cross-play.
- Report per-matchup pilot spread and disagreement.
- Introduce reliability grades.
- Prevent balance conclusions from passing automatically when policy sensitivity is high.

Exit condition: reports distinguish card balance from pilot weakness and strategic style.

### Phase 4 — Distill search into a fast policy

- Define stable, generic state and action features.
- Create versioned oracle-labelled datasets.
- Train policy and value models.
- Add disagreement-driven data collection.
- Validate the learned pilot per deck and against historical versions.

Exit condition: the learned pilot approaches reference quality at production-simulation
speed and does not create deck-specific regressions.

### Phase 5 — Calibrate with human play

- Import and preserve human game records.
- Compare decision agreement and matchup rankings.
- Expand the curated position suite from real failures.
- Include human-calibration coverage in reliability grades.

Exit condition: simulated trends predict observed human trends well enough to guide balance
changes, with discrepancies explicitly surfaced.

## Release gates for balance conclusions

A card or deck balance recommendation should not be considered strong solely because a
large simulation has a narrow statistical confidence interval. A million games played by a
systematically weak pilot give a precise measurement of the wrong policy.

Before treating a conclusion as actionable, require:

1. sufficient paired sample size;
2. stability across seats and seeds;
3. a competent production pilot for both decks;
4. no unexplained large production-versus-reference disagreement;
5. acceptable stability across the policy population;
6. search-budget convergence on a calibration cohort;
7. human evidence when available;
8. complete version and replay provenance.

Failures should be reported as uncertainty, not smoothed into a single headline win rate.

## Immediate direction

TurnBot remains the correct next implementation step. It supplies a better high-throughput
pilot, exercises the complete-turn search machinery, and generates the difficult positions
needed for later oracle and training work.

After TurnBot, the priority should be:

1. optimize and strengthen the reference search tier;
2. add policy-sensitivity and reliability reporting;
3. begin collecting versioned position datasets;
4. only then evaluate whether learned policy/value models are justified.

The lasting core feature is not one bot. It is a **versioned, calibrated simulation
laboratory** in which every balance claim states how strongly it depends on the pilots that
produced it.
