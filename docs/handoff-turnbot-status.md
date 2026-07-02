# TurnBot — Status Handoff

> **Audience:** a game-simulation agent picking up TurnBot after the initial build.
> **Companion:** the original spec is `docs/handoff-turnbot.md`. This document records what
> was actually built, the smoke-benchmark results, the throughput problem, one tried-and-
> reverted optimization (with data), and the open decisions.
> **Date of work:** 2026-07-02.

---

## 1. What TurnBot is

The middle tier between GreedyBot (fast 1-ply) and RefereeBot (opponent-reply rollouts,
~100–200× greedy). TurnBot plans a **complete own turn** with the same determinized
information-set search as the referee, then **stops at the turn boundary** — no opponent-turn
rollout — and scores the finished position with the shared evaluator plus a projected
end-of-turn readiness term.

```
GreedyBot   fast one-action baseline
TurnBot     complete-own-turn planner; default large-sim candidate
RefereeBot  sampled opponent-response auditor
```

---

## 2. What was implemented (all committed to the working tree, not yet git-committed)

**Bots**
- `animal_kingdom/bots/turn_search.py` — **new** `TurnSearcher` base. Holds all shared
  machinery: determinized worlds (`bots/determinize.py`), `_observation_key` +
  information-set grouping (honesty), `_beam` pruning with reserved tactical candidates,
  `_safe_actions` (hard next-turn-HQ-loss filter incl. the two-action `draw→capture` case),
  wasted-battlecry penalty accumulation, `_complete_own_turn` recursion, and the
  projected-readiness `_planning_eval`. Behavior differences between the two bots are isolated
  as override hooks: `_score_final_line`, `_use_reply_comparison`/`_reply_candidates`,
  `_score_candidate_group`, `_resolve_opponent_subchoice`.
- `animal_kingdom/bots/turn_bot.py` — **new** `TurnBot(TurnSearcher)`. Uses the base hooks:
  scores lines by end-of-turn planning eval, never rolls out a reply, and models any
  opponent-owned sub-choice **adversarially** (worst legal public continuation). No deck
  slugs / card IDs anywhere.
- `animal_kingdom/bots/referee_bot.py` — **refactored** to subclass `TurnSearcher`, overriding
  the four hooks to restore exactly its prior behavior (reply rollout + greedy opponent
  sub-choice). RefereeBot behavior and its no-cheat tests are unchanged (verified).

**Registration** — `"turn"` added to `sim/runner.py` (`BOT_KINDS`, `make_bot`,
`TURN_DETERMINIZATIONS=3`, `TURN_BEAM_WIDTH=8`); `cli.py` controller + opponent-level menu +
`--bots` help; `README.md` examples/milestone. `report`/`gauntlet` help auto-derive from
`BOT_KINDS`.

**Paired benchmark**
- `sim/gauntlet.py` — `run_gauntlet` now takes `config` and threads it; `--config` CLI added.
- `animal_kingdom/sim/bot_comparison.py` — **new**. `run_bot_comparison(...)` runs baseline
  `greedy(D)-vs-greedy(O)` and candidate `turn(D)-vs-greedy(O)` over the **same** seed
  schedule, joins per-game by `(opponent, seed)`, and reports **paired** deltas with a
  deterministic paired bootstrap 95% CI (10k resamples, fixed seed, resamples the paired
  deltas — not the two samples independently). `BotComparisonResult` carries overall/per-
  opponent win rates + deltas + CIs, W/L/D, win-condition splits, avg length, final food,
  runtime/slowdown, seed range, and all identifiers. A seven-deck command writes
  `summary.json`, `per_deck.csv`, `per_opponent.csv`, and a gate-annotated terminal table to
  `results/bot_quality/turnbot/`. `evaluate_gates` computes the measurable §4.3 gates.

**Tests** — `animal_kingdom/tests/test_turn_bot.py` (**new**): the handoff §3 acceptance list
(two-action planning, observed-draw adaptation, no-info-leak, pending choices, adversarial
opponent sub-choice, HQ safety, determinism, serial==parallel, beam performance guard) plus a
same-turn puzzle per deck family. Full suite: **252 passed, 1 pre-existing xfail**.

### How to run

```sh
.venv/bin/python -m pytest animal_kingdom/tests/ -q                 # full suite
./run --bots turn,greedy --decks colony_food_swarm,cats_midrange --quiet   # CLI game
# smoke benchmark (20 games/opp, all 7 decks, map_b + two-action rules):
.venv/bin/python -m animal_kingdom.sim.bot_comparison --games 20 --seed 683470156 \
  --config animal_kingdom/data/two_action_config.json --out results/bot_quality/turnbot
```

Benchmark defaults: `--map map_b`, `jobs=<cpu count>`, seed `683470156`. Stages via `--games`
(20 smoke / 200 acceptance / 500 / 1000). `--deck <slug>` benchmarks one candidate deck
against the full opponent pool (incl. mirror).

---

## 3. Smoke results (20 games/opp — pipeline proof, NOT acceptance-grade)

Paired delta = candidate (turn) minus baseline (greedy), same seeds. 95% CI is the paired
bootstrap. `slow` = TurnBot wall-time ÷ greedy wall-time in that deck's gauntlet.

```
deck                greedy   turn   delta      95% CI            mirror   worst opp            slow
aggro_hq_rush        60.0%  74.3%  +14.3%  [ +5.0%,+23.6%]       60.0%    aggro_hq_rush   +0%   ~40x
canine_buff_tempo    60.7%  69.3%   +8.6%  [ -1.4%,+17.9%]       50.0%    canine         -10%   ~18x
cats_midrange        78.6%  90.0%  +11.4%  [ +4.3%,+19.3%]       70.0%    colony          +0%   ~35x
colony_food_swarm    24.3%  45.7%  +21.4%  [+12.9%,+30.0%]       85.0%    cats            +0%   ~52x
egg_control          33.6%  33.6%   +0.0%  [ -7.9%, +7.9%]       40.0%    colony         -30%   ~20x
food_otk             41.4%  62.1%  +20.7%  [+11.4%,+30.0%]       85.0%    colony          +5%  ~266x
ramp                 57.9%  68.6%  +10.7%  [ +2.1%,+19.3%]       55.0%    colony          -5%   ~16x
```

Reading (all caveated by n=20 noise):
- TurnBot **improves or ties every deck's overall paired delta**. Biggest gains are the
  combo/sequencing decks — colony_food_swarm 24%→46% (the motivating case from the spec),
  food_otk +21.
- Directional concerns to confirm at scale: egg_control shows no improvement and a −30% worst
  matchup vs colony; canine/egg mirror <50%.

### Acceptance gates (§4.3), current status at smoke scale — **not all pass**
1. Every deck delta > 0 — **fails** (egg_control +0.0).
2. Each CI entirely above zero — **fails** (canine/egg span zero; noise).
3. No opponent matchup drops > 5 pts — **fails** (egg −30% vs colony; likely noise).
4. Mirror rate > 50% — **fails** (canine 50%, egg 40%).
5. Generalist (no deck slugs) — **holds** (verify by inspection).
6. Determinism byte-equal reruns — **holds** (verified: serial==parallel, repeat runs equal).
7. Throughput ≤ 10× — **fails hard** (12×–266×; see §5).

Most of 1–4 are expected to resolve at 200/opp; **7 will not** without a speed change.

---

## 4. The throughput problem, from first principles

Cost of any search = (positions examined) × (cost per position). GreedyBot is 1-ply: try each
legal move once, score with a cheap heuristic. TurnBot grades a move by **imagining the whole
rest of the turn** and scoring the endings, in **several sampled hidden-info worlds**. Three
factors multiply:

1. **Worlds** — `TURN_DETERMINIZATIONS=3`: everything done ~3×.
2. **Branching** — `TURN_BEAM_WIDTH=8`: up to ~8 candidates kept per decision.
3. **Depth** — a two-action turn plus effect-granted extra placements plus mid-turn draws;
   each step branches again.

They nest (worlds × first-move × second-move × extra-play × …), and each imagined move also
resolves a full effect cascade, so per-position cost is heavier than greedy's too.

**Why deck slowdown varies 16×→266×:** it tracks "how big can a turn get." `ramp` plays one
big body and stops (shallow → ~16×). `food_otk` is designed to do many things in one turn and
**draws cards mid-turn**, so the turn gets deeper *and* the hand (hence branching) gets wider as
it goes → ~266×. `colony` is the same story, milder (~52×).

---

## 5. Tried and reverted: transposition (memoization) cache — NEGATIVE RESULT

**Hypothesis:** combo turns reach the same board via different move orders; memoize the
completion of a position (keyed on the full simulated state incl. deck order + carried
penalties) so each distinct board is searched once.

**Implementation:** cache wrapped around `_complete_own_turn`, TurnBot-only (gated off for
RefereeBot, whose completion consumes RNG via greedy rollouts, so caching would change its
results). Verified **exact**: benchmark win-rates came back byte-identical (per_opponent CSV
identical; per_deck identical except the timing column).

**Outcome:** **no speedup** (total 574s vs 554s, slightly slower from key-building overhead;
food_otk 266× vs 272×). Measured cache hit rate over a full food_otk game: **0.8%** (4 hits /
505 lookups).

**Why it failed:** these decks' turn depth is **draw-driven**, and drawing is *not*
commutative — it mutates the deck and hand, so every path is a genuinely distinct state and
there are no transpositions to collapse. Memoization only helps reorder-heavy
(commutative-placement) combos, which this card pool does not produce.

**Status:** fully reverted; code is clean; recorded so it isn't re-attempted.

---

## 6. Open decisions / recommended next experiments (for the sim agent)

The explosion cannot be pruned away for free here. Getting under the 10× gate needs a
speed-vs-quality lever. Ranked by suggested order:

1. **Lower `TURN_DETERMINIZATIONS` (3 → 2 or 1) and/or `TURN_BEAM_WIDTH` (8 → 4–6).** Cheapest
   to try; both live in `sim/runner.py` (and mirrored on `TurnBot`/`TurnSearcher` defaults).
   Fewer worlds weakens hidden-info robustness; narrower beam risks missing lines. **Measure
   the speed-vs-win-rate trade on the smoke set** before committing (the paired benchmark makes
   this a clean A/B: it's just a different candidate config vs the same greedy baseline).
2. **Turn-depth cap** in `_complete_own_turn` (stop expanding past N same-turn decisions and
   score the partial line). Directly targets food_otk/colony — but bites hardest exactly where
   the planning helps most, so watch those deltas.
3. **Better/cheaper leaf eval** so lines can be pruned shallower (touches `evaluate` in
   `greedy_bot.py` and the beam ordering).
4. **Learned policy/value prior (AlphaZero/ISMCTS-style).** Shrinks branching by proposing only
   the few moves worth searching, rather than deduping identical results. Larger effort;
   different architecture.

**Do not** revive the old multi-turn `lookahead` mode, and do not compensate for a failed gate
with deck-specific weights (spec §4.3).

### Acceptance run when ready
```sh
.venv/bin/python -m animal_kingdom.sim.bot_comparison --games 200 --seed 683470156 \
  --config animal_kingdom/data/two_action_config.json --out results/bot_quality/turnbot
```
Estimated ~1.5–2.5h wall on 8 workers at current speed (food_otk dominates). Uncertainty
resolution: rerun any deck whose CI spans zero at `--games 500`, then `1000`, via `--deck`.
Deliverable per spec §5: the per-deck table (greedy baseline, turn result, delta, CI, worst
matchup, mirror, slowdown) and a recommendation on whether `./report`'s default should change
from `greedy,greedy` to `turn,turn`. **Leave the report default unchanged until all seven
decks pass all gates.**

---

## 7. Key files at a glance

| Path | Role |
|------|------|
| `animal_kingdom/bots/turn_search.py` | shared `TurnSearcher` (determinize, beam, own-turn completion, honesty) |
| `animal_kingdom/bots/turn_bot.py` | `TurnBot` (no reply, adversarial sub-choice) |
| `animal_kingdom/bots/referee_bot.py` | `RefereeBot` as `TurnSearcher` + reply overrides |
| `animal_kingdom/sim/bot_comparison.py` | paired benchmark + bootstrap + artifacts + gates |
| `animal_kingdom/sim/runner.py` | bot registration, `TURN_*` constants |
| `animal_kingdom/tests/test_turn_bot.py` | acceptance tests + per-family puzzles |
| `results/bot_quality/turnbot/` | smoke artifacts (summary.json, per_deck.csv, per_opponent.csv) |
