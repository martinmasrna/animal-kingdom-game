# Arc: Build a trustworthy card-power ruler (the baseline deck)

_Planned 2026-07-13 in a strategy session. This is the **agreed direction for the next ~4 sessions**
and the immediate top of Balance. It builds directly on
[`benchmark-set-handoff.md`](benchmark-set-handoff.md) (the problem statement) and the
`sim/benchmark_set.py` instrument already shipped (commit `659acf9`)._

> **Status — Steps 1–2 DONE, first tune applied; re-running fresh (2026-07-15).**
>
> **Step 1 (2026-07-13).** The baseline roster is built and locked in `sim/benchmark_set.py`
> (source of truth). "Basic" was settled as **self-sufficient** (no synergy/tribal/food-state/cost
> condition to function) — *not* "effectless." Cut the cost-gated apex bombs (borealis/aquila),
> delayed bears' co-tenants stayed, and the reactive/keyword outliers; `mock_draw2` dropped
> legendary→rare. Minted 4 controlled mocks: `mock_vanilla_10` (bare body), `mock_flyer_7` (vanilla
> flyer), `mock_immovable_6` (vanilla wall), `mock_removal` (unconditional "remove an adjacent
> enemy" — the basic-removal legendary anchor). Legendary tier is now the basic primitives at top
> dosage: engine (greywhisker) / body (vanilla-10) / reach-body (flyer-7) / removal (mock_removal).
>
> **Step 2 + a first step-4 tune (2026-07-13/14).** Referee run vs the 7-deck field, then a tuning
> pass on the 30 (`e3020e4`, draw-1 buffs + 2 nerfs) re-confirmed in `referee_tuned1.csv`.
> **Headline: the tuned ruler beats 6 of 7 decks** — aggro 70%, food_otk 61%, canine 60%, colony
> 59%, ramp 54%, egg_control 96%; only cats holds it under 50 (43%). That is either the anchors
> sitting far above the game's power level (caveat 2) or pilot bias landing exactly where caveat 1
> predicted — **unresolved, and the arc's live question.**
>
> **Rig fix (2026-07-15).** The rig scored only one seat per run, so reading the field decks' cards
> meant re-simulating the *identical* games to fold the seat thrown away (`referee_tuned1` and
> `referee_opp` differed only in `measure`). It now folds **both seats always** — one pass yields the
> rig's ranking *and* every field deck's; `--report` only picks what prints. Seed re-rolled
> 902000→715000, so **all pre-2026-07-15 benchmark data is superseded** by the fresh both-seats run.
>
> **⚠ ALL BENCHMARK DATA VOID — the ruler itself was buggy (2026-07-15).** The fresh both-seats run
> was launched and then **killed one matchup in**, because the timed-effect survey found that
> **`black_bear` and `grizzly_bear` — both in the rig's own `DECKLIST`** — were cheating: Black Bear
> drew 2 cards even after being destroyed, Grizzly struck from under a stack. Every matchup runs the
> ruler, so *every* number was affected, not just ramp's. Ruled and fixed the same day
> ([`../rules/timed-effect-ruling.md`](../rules/timed-effect-ruling.md)): timers now tick only while
> their unit is top-of-stack. Ramp also changed underneath it (Landmarks cut; Sloth + Cape Buffalo
> in, which moves Oxpecker 15→18).
>
> **Next: re-run the ruler from scratch** (`--pilot referee --games 500`, both seats, all 7,
> seed 715000), then Step 3 — analyze. Nothing may be locked from pre-2026-07-15 data.

## The idea in one paragraph

Introduce a **fixed, neutral reference opponent**: a 30-card deck of solid basic cards with **zero
synergies** (the existing `benchmark_set` singleton rig, 18C/8R/4L, extended into a real fixed
opponent). Because it never changes, it's a **stable ruler** — it prices card power in absolute
terms, detects drift as we tune elsewhere, and gives each synergy deck an independent, *meaningful*
design target ("a synergy deck should beat a pile of merely-good cards, because that's the point of
synergy") instead of the arbitrary "everyone ~50% vs everyone." It also decouples balance from the
noisy 7×7 coupled system, where tuning one deck shifts every cell.

## Why the fixed anchor is the key move (not just a nicety)

It **collapses the opponent axis from 7 decks to 1**. That's what makes the expensive-but-trustworthy
pilot affordable: piloting all 7 synergy decks at **RefereeBot (oracle) level vs one fixed opponent**
is O(decks), not O(decks²) — a walk-away overnight run instead of a brutal full referee 7×7.

## Decisions locked this session

- **Pilot: RefereeBot all the way** for anything recorded; GreedyBot only for quick directional
  probes. (This also re-baselines everything at the current **draw-2** default for free — all
  pre-`8c3d473` balance data, incl. the earlier benchmark_set run, is stale draw-1 data.)
- **Anchor method: impact-equivalence *within* each rarity.** A card is "a fair common" if its
  measured impact (WR-when-drawn / impact %) ≈ the common anchor; likewise rare, legendary.
- **Common anchor = vanilla str-7 non-flying body AND vanilla str-5 flying body.** These are asserted
  equal, which **prices Flight at ~+2 strength as a byproduct** — and the rig *self-checks* it: if the
  two don't land at equal impact, Flight isn't worth 2 and we re-anchor.
- **Rare / legendary anchors set by feel, not computed.** The rarity ladder (how much more impact a
  fair legendary is allowed than a fair common — the "rarity premium") is a deliberate *design* call,
  not a formula. The premium exists because of the **deckbuilding slot budget** — a constructed deck
  is 18 common / 8 rare / 4 legendary *cards* (the 6×3 / 4×2 / 4×1 "4-4-6" max-copy shape), so a
  legendary is capped at 4 slots and must earn its scarce seat by being individually more impactful.
  (NOT because it's drawn less — that's a weaker, secondary effect.) Mechanically the rig flattens
  rarity (all ×1, equal draw → one unified impact ladder, Lion/Eagle ≈ 0); the per-rarity anchors are
  the **feel-set target heights on that single ladder**, not separate measurement contexts. The rig's
  18C/8R/4L singleton composition is itself a legal-shape deck, honoring the 4-legendary cap.
- **Legendary anchor character is ours to choose** — engine, big body, or reach. Greywhiskers (an
  effect-engine) is a candidate; a "vanilla legendary" (bare str-9/10 body) is an alternative worth
  *testing* rather than assuming (see caveats). Pick the character by feel; let the rig confirm it
  holds up.
- **Starting point = the existing 30-card rig**, which already contains cards deliberately set
  stronger/weaker than baseline as calibration/test points.

## Risks & caveats that survived the discussion (do not lose these)

1. **Pilot bias cuts against synergy decks — the biggest threat to validity.** A synergy-free deck is
   the *easiest* thing to pilot well (no multi-turn plan to miss), while the synergy decks are exactly
   the ones bots under-pilot (egg 24% bot vs 50% human). So baseline-vs-synergy is structurally a
   well-piloted deck vs badly-piloted decks; a *fine* synergy deck can look like it "loses to
   goodstuff" purely as a piloting artifact. **Referee-level piloting mitigates this** (the anchor
   makes it affordable), **but even RefereeBot can't plan multi-turn scaling** — egg-vs-cats is ~24%
   even at referee. So for the 2–3 scaling decks (egg, ramp, and any deck whose win-con is a growth
   plan), a "loses to baseline" verdict needs a **human-play asterisk** before it drives any redesign.
   Never buff a synergy deck to clear the bar if the shortfall is a piloting artifact — that
   homogenizes the very decks whose identity is synergy. (Same boundary as `STATUS.md`: never nerf/buff
   a card to fix a bot.)
2. **The anchors pin the game's *aggregate* power level.** Internal balance of the 30 (every card ≈ its
   rarity anchor) does *not* by itself fix how strong the deck is as a whole — the anchor *values* are
   that decision. Choosing vanilla-7 / vanilla-5 / feel-set legendary **is** setting the power baseline
   for the entire game. Own that explicitly.
3. **Impact is a coarse ruler — measure its resolution floor.** The vanilla strength ladder is ~flat
   across str 5–8 under competent play (strength is threshold-y, not linear), and 200-game runs have a
   noise floor. The deliberately-off-baseline test cards therefore do double duty: they measure **the
   smallest impact delta the rig can reliably resolve.** Read that number off early — you cannot tune a
   card below your own measurement floor without chasing noise.
4. **"Beats baseline" ≠ "mutually balanced."** Two decks can both clear the baseline bar and still be
   lopsided against each other. The baseline is an *added anchor*, not a replacement for the 7×7 mutual
   check. This arc produces a trustworthy *ruler*, not a complete balance verdict.
5. **Verify Greywhiskers is mid-pack among legendaries before locking it as the anchor.** The only
   data point so far (the `659acf9` commit note) has it *topping the overall ranking*. If that's just
   "legendaries outrank commons," fine; if it's also high *among legendaries*, anchoring on it sets the
   legendary tier too tall and would tempt over-buffing the tier in step 4. One number in the same
   referee output settles it.
6. **Is a "vanilla legendary" even a coherent anchor? — an empirical question.** The flat-ladder finding
   (5–8) suggests a bare big body under-performs its rarity slot → a *low* anchor, implying legendaries
   must earn their slot via *effects*. **But** str 9–10 is unmeasured territory where the coverage
   ceiling bites (a 10 is uncoverable, immune to all strength-gated removal ≤9) and strength may stop
   being flat. Resolve by dropping a vanilla-10 *and* Greywhiskers into the deck and comparing impacts.

## The session sequence

1. **Build the baseline deck.** Fix the anchors (vanilla-7 ground / vanilla-5 flying common; feel-set
   rare; chosen-character legendary + a vanilla-10 for the anchor test), keep the salted off-baseline
   test cards, extend `benchmark_set` into a real fixed opponent.
2. **Referee run vs all 7**, both seats, ≥200 games/matchup. Collect matchup WR + per-card
   WR_drawn/impact. Read off the **resolution floor** from the test cards.
3. **Analyze:** (a) goodstuff-vs-synergy standings (which synergy decks fail to beat a no-synergy pile —
   with the pilot-bias asterisk on scaling decks) and (b) internal balance of the 30 against the anchors.
4. **Rebalance the 30** to their rarity anchors; re-run to confirm. Baseline is now a locked ruler.

**→ Sequel arc (NOT this one):** pull every synergy deck to a positive margin vs the locked baseline
while keeping them mutually sane. That's 7 decks of redesign — its own multi-session program, unblocked
by the ruler above.

## Scope

Build and calibrate **the ruler** only. Do **not** redesign any synergy deck this arc (that's the
sequel). Keep every number a placeholder in `engine/config.py`.
