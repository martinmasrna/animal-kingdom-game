# Arc: Build a trustworthy card-power ruler (the baseline deck)

_Planned 2026-07-13 in a strategy session. This is the **agreed direction for the next ~4 sessions**
and the immediate top of Balance. It builds directly on
[`benchmark-set-handoff.md`](benchmark-set-handoff.md) (the problem statement) and the
`sim/benchmark_set.py` instrument already shipped (commit `659acf9`)._

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
  not a formula. (We considered pinning it to draw-frequency ratios and rejected that in favor of
  feel.)
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
