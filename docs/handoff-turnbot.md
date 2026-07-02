# TurnBot — Implementation Handoff

> **Audience:** the agent implementing the scalable, turn-aware balance bot.
> **Goal:** create a generalist bot that sequences a complete current turn competently,
> while remaining cheap enough for large balance simulations.

---

## 1. Why TurnBot exists

The project currently has three relevant policies:

- **GreedyBot** is fast enough for large matrices, but scores one action at a time. Under
  the two-action rules it cannot reliably plan `draw → play`, ordered Battlecries, or
  effect-granted third placements.
- The old **lookahead** mode searches multiple own placements across turns while advancing
  the opponent with a passive filler. It was gauntlet-tested and made play worse; do not
  revive that approach.
- **RefereeBot** uses determinized opponent hands and simulates a full opposing reply. It is
  useful for calibration, but too expensive to be the default pilot for thousands of games.

TurnBot is the middle tier:

```text
GreedyBot   fast one-action baseline
TurnBot     complete-own-turn planner; default large-sim candidate
RefereeBot  sampled opponent-response auditor
```

The motivating Colony-vs-Cats investigation showed the distinction clearly. Greedy still
pilots Colony at roughly 2% in that matchup, while the turn-aware Referee reached 34% over
the same 100-seed cohort. TurnBot must capture the sequencing improvement without paying
for opponent-turn rollouts.

---

## 2. Required behavior

### 2.1 Search boundary

For every candidate action, TurnBot must search until the **current turn is completely
finished**, including:

- all configured top-level actions (`actions_per_turn`);
- Draw followed by a placement using the newly observed card;
- pending `ChoiceAction`s;
- mandatory and optional effect-granted placements;
- chains such as Nurse Bumblebee → Queen Bee → Worker;
- end-of-turn triggers and region food, which `rules.apply_action` already resolves when
  the turn advances.

Stop as soon as control passes to the opponent at a top-level decision. Do **not** simulate
the opponent's turn. Score the completed own-turn position with the shared evaluator and
the existing projected-readiness adjustment used by RefereeBot.

This is not the old multi-turn `lookahead` mode. TurnBot searches deeply only inside the
current turn.

### 2.2 Hidden-information honesty

TurnBot may not inspect the real order of either deck or the real contents of the
opponent's hand.

Use a small set of determinized worlds to model unknown draws:

- default `TURN_DETERMINIZATIONS = 3`;
- reuse `bots/determinize.py`, which samples the player's unknown deck order, the
  opponent's hidden hand/deck split, and chance RNG without leaking the real state;
- the candidate action at the current decision must be identical across all worlds;
- at later decisions, group worlds by a canonical observation key and require one action
  per indistinguishable group;
- worlds may choose different continuations only after an observable divergence, such as
  drawing different cards.

Extract the observation-key and information-set grouping code from RefereeBot into a
shared internal helper rather than maintaining two subtly different honesty models.

If an effect asks the opponent to choose during TurnBot's turn, model that choice
adversarially: select the legal continuation with the lowest mean score for TurnBot across
the corresponding information set. Do not read the true hidden hand to make that choice.

### 2.3 Candidate pruning and scoring

Default to `TURN_BEAM_WIDTH = 8`. Preserve deterministic action order and seeded tie
breaking.

Beam pruning must always retain, when available:

- Draw;
- an immediate HQ capture;
- the best connected placement per card;
- the best own-HQ-front placement per card;
- the best enemy-cover placement per card;
- a placement where the card's actual Battlecry is live.

Accumulate the existing `wasted_battlecry` penalty across every placement in the planned
turn. Reuse the hard next-turn HQ-loss filter, including the two-action
`draw → capture HQ` case.

Use only general engine-visible features. Production TurnBot/search code must contain no
deck slugs or individual card IDs.

### 2.4 Shared implementation

Create `animal_kingdom/bots/turn_bot.py` and, if useful,
`animal_kingdom/bots/turn_search.py`.

Prefer extracting these pieces from RefereeBot into `turn_search.py`:

- observation-key construction;
- grouping determinized worlds by information set;
- own-turn recursive/beam completion;
- action preservation and HQ-safety filtering;
- fizzle-penalty accumulation;
- projected readiness at the end of the player's turn.

TurnBot uses the shared own-turn planner and stops. RefereeBot uses the same planner, then
adds its sampled Greedy opponent reply before final scoring. Existing Referee behavior and
the no-cheat tests must remain intact.

Register `"turn"` everywhere bot kinds are accepted:

- `sim.runner.BOT_KINDS` and `make_bot`;
- CLI controller construction/help;
- report and gauntlet help;
- README examples.

Use module constants in `sim.runner`:

```python
TURN_DETERMINIZATIONS = 3
TURN_BEAM_WIDTH = 8
```

---

## 3. Correctness tests

Add `tests/test_turn_bot.py`. At minimum:

1. **Complete two-action turn:** TurnBot evaluates both actions together instead of choosing
   the locally best first action.
2. **Observed draw adaptation:** indistinguishable worlds share the Draw action; after
   drawing different cards they may choose different legal follow-ups.
3. **No hidden-information leak:** two states with the same player view but different true
   opponent hands/deck orders produce the same current action.
4. **Pending choices:** mandatory, optional/skip, and effect-granted placements are searched
   until the turn really ends.
5. **Opponent-owned sub-choice:** chooses the worst legal public continuation for TurnBot.
6. **HQ safety:** blocks both a held-card capture and an empty-hand
   `draw → capture` threat.
7. **Determinism:** equal seed/state inputs produce equal actions; serial and parallel
   simulations match.
8. **Performance guard:** a fixed small fixture stays inside the configured beam and does
   not expand every Flight destination recursively.

Reuse or move the existing sequencing puzzles so TurnBot must solve:

- preserve the saved game's duplicate Guard setup;
- activate Nurse Bee rather than fizzle it;
- Draw → Termite Queen → Termite King;
- Nurse Bumblebee → Queen Bee → Worker.

Add at least one same-turn puzzle from every other deck family so the implementation cannot
be tuned only to Colony:

- Cats: extra-Cat/twin sequencing;
- Canine: extra-Canine or buff-before-payoff ordering;
- Egg: draw/shuffle/removal ordering;
- Food OTK: food setup before the current-turn payoff;
- Ramp: current-turn draw/reveal or cost sequencing;
- Aggro: removal or swarm ordering.

Delayed effects beyond the current turn are not a TurnBot acceptance criterion.

---

## 4. Paired seven-deck benchmark

The claim “TurnBot is better” must be tested **for each candidate deck separately**, not
only as one blended overall rate.

### 4.1 Benchmark design

For each of the seven premade decks `D`, run two candidate gauntlets:

```text
baseline:  GreedyBot(D) vs GreedyBot(O)
candidate: TurnBot(D)   vs GreedyBot(O)
```

where `O` is every premade deck, including `D` itself. Including the mirror is deliberate:
TurnBot(D) vs GreedyBot(D) directly isolates pilot quality with identical card pools.

Hold all comparison inputs fixed:

- opponent pilot is always GreedyBot with default weights;
- candidate is always seat A; first player remains seed-randomized by the engine;
- Map B;
- `animal_kingdom/data/two_action_config.json`;
- identical ordered opponent pool;
- identical base seed and per-pair/per-game seed schedule;
- identical game count.

Use these stages:

1. **Smoke:** 20 games/opponent while developing.
2. **Acceptance:** 200 games/opponent, seven opponents, for both candidate kinds.
3. **Resolve uncertainty:** if a deck's paired 95% interval includes zero, rerun that deck
   at 500 games/opponent; if still unresolved, use 1,000.

Primary acceptance seed: `683470156`.

### 4.2 Harness changes

`sim.gauntlet.run_gauntlet` currently omits `Config`; add `config: Optional[Config]` and
thread it to `run_pairs`. Add CLI `--config` using the existing
`load_config_overrides` helper.

The current aggregate `GauntletResult` is insufficient for paired statistics. Add a
paired comparison runner that retains or joins per-game outcomes by:

```text
(candidate_deck, opponent_deck, game_seed)
```

Recommended interface:

```python
run_bot_comparison(
    deck: str,
    opponent_pool: Sequence[str],
    n_games: int,
    base_seed: int,
    baseline_kind: str = "greedy",
    candidate_kind: str = "turn",
    opponent_kind: str = "greedy",
    config: Optional[Config] = None,
    map_id: str = "map_b",
    jobs: int = 1,
) -> BotComparisonResult
```

`BotComparisonResult` must include:

- baseline and candidate overall win rates;
- paired overall delta;
- deterministic paired-bootstrap 95% interval for the delta;
- the same three values per opponent;
- wins/losses/draws and win-condition splits;
- average game length and final food;
- total runtime, games/second, and TurnBot/Greedy slowdown;
- the underlying seed range and all bot/config/map identifiers.

Use at least 10,000 paired bootstrap resamples with a fixed bootstrap seed. Resample paired
game deltas, never the two bot samples independently.

Add one command that runs all seven candidate decks and emits:

- `summary.json`;
- `per_deck.csv`;
- `per_opponent.csv`;
- a concise terminal table.

Store canonical results under:

```text
results/bot_quality/turnbot/
```

### 4.3 Acceptance gates

TurnBot is accepted as the scalable balance pilot only if all are true:

1. **Every deck improves:** TurnBot's overall paired delta is greater than zero for each of
   the seven candidate decks.
2. **Evidence, not noise:** each deck's paired 95% interval is entirely above zero after the
   uncertainty-resolution runs.
3. **No hidden collapse:** no individual opponent matchup drops by more than 5 percentage
   points. Any such cell is a blocking tactical regression to diagnose with saved games.
4. **Mirror sanity:** TurnBot's rate against same-deck Greedy is above 50% for every deck.
5. **Generalist constraint:** production bot/search files contain no deck slug or card ID.
6. **Determinism:** repeating the benchmark with the same seed produces byte-equivalent
   result data apart from runtime fields.
7. **Throughput:** TurnBot is no more than 10× slower than Greedy in the acceptance
   gauntlet and a 500-games-per-matchup seven-deck report is projected to finish within
   30 minutes on eight local workers.

If TurnBot fails a gate, do not compensate with deck-specific weights. Save representative
game logs, add general tactical puzzles, improve the shared turn planner/evaluator, and
rerun the same paired seeds.

---

## 5. Final deliverable

Hand back:

1. TurnBot and shared turn-search implementation.
2. Bot registration in CLI/sim/report tooling.
3. Config-aware paired benchmark command.
4. Full test suite results.
5. Seven-deck paired comparison artifacts and a table showing, for every deck:
   Greedy baseline, TurnBot result, paired delta, confidence interval, worst matchup
   regression, mirror rate, and slowdown.
6. A recommendation, supported by the gates above, on whether `./report` should change its
   default from `greedy,greedy` to `turn,turn`.

Do not change the report default until all seven decks pass.
