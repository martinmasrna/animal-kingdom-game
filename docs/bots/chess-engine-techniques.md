# Chess-Engine Techniques — What Transfers to Our Bots

Distilled from two Sebastian Lague "Coding Adventures" chess-engine videos, mapped onto *our*
search (`bots/turn_search.py`, `bots/turn_bot.py`, `bots/referee_bot.py`). Kept the takeaways,
dropped the raw transcripts. Sources:

- Chess AI (search fundamentals): <https://www.youtube.com/watch?v=U4ogK0MIzqk>
- Making it stronger + measuring it: <https://www.youtube.com/watch?v=_vqlIPDR2TU>

**Important framing:** these are a *chess* engine — full-information, deterministic, classic
minimax + alpha-beta over the whole game tree. Ours is different in two ways that gate what
transfers: (1) **hidden information + randomness** (we determinize sampled worlds and search
information-set trees, never the true state — the honesty invariant), and (2) we **beam-search a
single complete own turn** and score the turn boundary (TurnBot) rather than doing iterative-deepening
minimax to a fixed ply. So depth-oriented chess tricks mostly don't bite; the breadth/caching and
evaluation-horizon ideas do.

## Already have it / independently confirmed

- **The whole "match manager" methodology (video 2) is our house rule.** Lague builds a paired
  A/B harness that pits new-version vs old-version from *balanced, varied* start positions, **both
  colors**, hundreds of games, because "improving against one opponent doesn't guarantee improving
  against another." That is exactly `sim/bot_comparison.py` + the CLAUDE.md rule (≥200 games/matchup,
  paired seeds, both seats) and the sub-oracle *directional* caveat (beating greedy ≠ beating
  referee). External corroboration, no action.
- **Interrupted-search sentinel bug — we avoid it by construction.** Video 2's worst bug: a
  canceled search returned a neutral `0` that propagated up as a real evaluation and caused
  blunders. Our node-budget cutoff (`TurnBot._complete_own_turn` → `_greedy_complete_turn`,
  `turn_bot.py:68`) doesn't return a placeholder — it *plays the line out greedily to a scored turn
  boundary*, so the parent min/mean sees a genuine position. **Invariant to keep:** any future
  "bail out" path (the `_MAX_DEPTH` guard, any new cutoff) must return a genuinely-scored position,
  never a neutral sentinel.
- **Quiescence-flavored extension already partially present.** Lague's quiescence search ("don't
  evaluate a leaf mid-capture-swing; extend until quiet") has a small analogue in
  `_planning_eval`'s end-of-turn *readiness projection* (`turn_search.py:411`).

## Worth trying — ranked

### 1. Transposition cache over `_observation_key` — throughput lever (highest value)
Video 1's transposition table + Zobrist hashing memoizes positions reached by different move
orders. We already compute the hard part: `TurnSearcher._observation_key` (`turn_search.py:542`) is
a canonical, hashable, hidden-info-safe digest of a position — a Zobrist-equivalent that exists but
is currently only used for info-set grouping. Within one `choose()`, the own-turn beam tree revisits
transposed positions constantly (place A then B vs B then A reach the same board). Memoizing
`_complete_own_turn` / `_planning_eval` results on that key would cut redundant re-expansion.
- **Why it matters:** throughput on the deep-combo decks is the *only* remaining gate to making
  TurnBot the default report pilot (food_otk still 13.5× after the node budget — see
  [`backlog.md`](backlog.md)). This is a fresh lever that node-budget/beam trims haven't touched.
- **Caveats:** cache must be keyed within a single determinized-world set and scoped to one
  `choose()` (positions across worlds/turns aren't interchangeable); the readiness projection makes
  `_planning_eval` position-plus-frame dependent, so key on the projected frame too. Validate the
  usual way: byte-identical play on all 7 decks + a real speedup on food_otk/egg, or it's not worth
  the memory. Tracked in [`backlog.md`](backlog.md).

### 2. Quiescence / search extensions → the dynamic-scaling blind spot (strategic)
Two chess ideas name our known #1 eval blind spot precisely:
- **Quiescence search** = never score a "loud" position. Ours scores *current* strength, so a
  half-resolved food-this-turn chain or a pending Egg hatch is scored mid-swing.
- **Search extensions** = look deeper on the few interesting moves (checks, near-promotions). Our
  analogue: extend the projection when a win condition is *loaded* (food within one big play of the
  threshold; a Rattlesnake/Goliath mid-grow).
This is the vocabulary for the "search under-values dynamic/scaling strength" item
([`backlog.md`](backlog.md)) and the learned-pilot bet — the `pending_payoff` term was the
present-state slice; a quiescence-style extension through a decisive-swing chain is the shape of the
*multi-turn* fix. Conceptual, not a quick patch.

### 3. Move ordering — killer moves (cheap search-quality win)
Video 1's biggest single speedup was **move ordering** (search likely-best first → prune more).
Our `_beam` (`turn_search.py:443`) already orders by 1-ply eval + a smart reserved-tactical set. The
one idea we don't use is **killer moves**: an action that was best (or caused a cutoff) in a sibling
info-set group is likely good elsewhere, so reserve it in the beam. Low-effort; helps beam *quality*
(keeping the truly-best line in a narrow beam), which is orthogonal to raw speed.

## Deliberately skipped (chess-specific, low transfer)
- **Magic bitboards / bitboard move-gen / bitboard pawn-structure eval** — 64-square, piece-blind
  tricks; our board is a tiny map, move-gen isn't the bottleneck.
- **Iterative deepening** — we search a fixed horizon (one own turn), not increasing ply; the
  anytime benefit is already covered by the node budget's greedy completion.
- **Opening book** — we *want* the bot to actually play (and determinism matters for sims).
- **Piece-square tables** — the generalizable version (phase-blended positional value) is really
  the existing `region_control` row-2-spine blind spot, tracked separately; a raw square-bonus table
  would be card/position hardcoding we avoid.

## Engine safety net (not a bot change)
Video 1's **perft** test — recursively enumerate all reachable positions to a fixed depth, count
them, and compare against a trusted reference — is a cheap regression guard for move-gen/rules. We
have no second engine to diff against, but snapshotting legal-action counts over a few fixed
positions as golden fixtures would catch silent rules/move-gen regressions. Tracked in
[`../engine/backlog.md`](../engine/backlog.md).
