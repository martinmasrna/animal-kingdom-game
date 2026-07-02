# Animal Kingdom — Project Status

> **This is the map.** Open it first each session. It says where every area stands and the
> next 1–3 moves in each — nothing more. Detail lives in each area's own docs (and, until the
> backlog is sorted, in `todo.md`). Keep this file short; when a "Next" item is done, replace it,
> don't append history.
>
> _Last updated: 2026-07-02._

## The project in one paragraph

A headless rules engine + bots + simulation harness for *Animal Kingdom*, a 2-player tactical
board game. The end goal is **trustworthy balance data**: run thousands of bot-vs-bot games and
learn whether the 7 premade decks are fair. Human/web UI is out of scope for now; the engine is
a pure, transport-agnostic library so a UI can drop on later. Engine built in milestones
**M0–M6** (all ✅; M6 TurnBot in the working tree, not yet git-committed).

## Areas & boundaries

Eight areas. The boundary rules that keep them from bleeding:

- **Rules ↔ Cards** — "would it survive swapping the whole card list?" Yes → Rules; no → Cards.
- **Balance ↔ Cards** — Balance owns *decisions + data*; Cards owns *current state*. A tuning
  investigation is Balance; the resulting number lives in `cards.json` (Cards).
- **Balance ↔ Bots** — Balance owns the *outcome targets* (deck-winrate spread, per-card impact)
  and the tuning to hit them; Bots owns *pilot quality*. Good bots **gate** balance conclusions
  but bot work is never a Balance task. And triage every sim finding: real card signal → Balance;
  bot blind-spot/execution bug → Bots. *Never nerf a card to fix a bot.*
- **Subsystem ↔ Code Health** — work *within one subsystem* (a feature or bug in Engine/Bots/CLI)
  stays there; *cross-cutting or whole-repo* quality work (full review, repo-wide refactor,
  conventions, architecture, tech-debt) → Code Health.

---

## 1. Rules & Mechanics
_The abstract game: turn structure, placement/covering/connection, victory conditions, card
types, keyword definitions. Source of truth: `overview.md`, `keywords.md`, `maps.md`._

**State:** Stable and documented. Keyword registry canonical (Flight, Immovable, Fragile, Apex
Predator, Battlecry, Deathrattle). Immovable/Stealth deep-dive ruled & shipped 2026-07-02.
Card-type model (Unit/Egg/Landmark) resolved *provisionally* (decision C).

**Next:**
1. **Confirm-or-revert the Landmark card-type decision** before `cards.json` hardens (Apex-eats-Landmark flavor wart included).
2. **Re-examine Immovable** (naming + effect footprint) — flagged 2026-07-02, *gated on referee-quality balance data*.
3. **Terminology sweep:** "Discard" → "Remove Pile" across all docs/data.

## 2. Cards & Flavor
_The concrete content: the 7 decks (effects, numbers, names) and their theme. Sources: `decks/`,
`card-candidates.md`, `flavor-review.md`, `data/cards.json`._
_**Flavor** (subcategory): animals, biology, folklore, naming — a recurring audit pass, not a separate area._

**State:** All 7 decks content-complete (4-4-6). Legendary names **provisional** (24/28
machine-suggested 2026-06-30; only the 4 Cats are final). `cards.json` rebuild is unblocked but
pairs with the G/H tuning below.

**Next:**
1. **(Flavor) Dedicated legendary-name review** — the stricter, do-not-skip pass before flavor-lock.
2. **(Flavor) Reskins & collisions:** Black Panther → leopard (not jaguar); rename the placeholder hornet; re-cast the generic-tag animals.
3. **Rebuild `cards.json` + effect registry** from the deck files (build #5) — do alongside Balance's Decision H.

## 3. Engine
_Core game code: state, effect stack, rules-as-code, the sim/analysis harness (`sim/`),
architecture, performance, tests. (Kept separate from CLI.)_

**State:** M0–M6 shipped; pure stdlib engine + effect interpreter + sim harness. Full suite
**252 passing, 1 xfail**. (M6 TurnBot committed in `aecfdf5`.)

**Next:**
1. **Fix `metrics.py` `impact` confound** — `win_rate_when_drawn` is biased by win-vs-loss game length (a harness bug, not card quality).
2. **State-representation speed** (struct-of-arrays) — *parked* until NN bots; measure clone cost first.

## 4. Bots
_The AI players and their quality. `bots/`, `handoff-turnbot*.md`._

**State:** Ladder is **GreedyBot** (fast baseline) → **TurnBot** (M6, new middle tier) →
**RefereeBot** (calibration oracle). TurnBot smoke: improves-or-ties all 7 decks, but blows the
10× throughput gate (12×–266×). Strength is measured only **relatively** so far (paired deltas) —
no anchored/absolute rating yet.

**Next:**
1. **Anchored strength scale (pilot rating).** Factored Bradley-Terry fit over all games —
   `strength = pilot + deck + interaction` — read the *pilot* term as an absolute-ish rating.
   Isolate pilot from deck via **mirror matches**; anchor **floor = Random**, **ceiling = oracle**,
   **calibrate to human games**. This is what tells you whether a pilot is trustworthy enough for
   Balance to rely on. *(Balance may reuse the fit's `deck` term, but that's optional.)*
2. **TurnBot → default pilot?** Pass the acceptance run (200/opp) and clear the 10× throughput gate
   (lower determinizations/beam or a turn-depth cap; A/B speed-vs-winrate), then decide whether
   `./report` switches from `greedy,greedy` to `turn,turn`.
3. **Known blind spot:** `region_control` over-values the row-2 spine, so neither bot contests
   row-1/3 as an HQ-rush lane.

## 5. CLI / App
_The human interface. `cli.py`, `render/`._

**State:** `rich`-based polish done (color by seat/rarity, in-place redraw, card-first targeting).
Plain stdin/stdout loop underneath. Lightest area right now.

**Next:**
1. **One more `rich` visual-polish pass** — a round of board/UX refinement on the current stdin/stdout loop before committing to a full TUI.
2. **Full TUI rewrite** (`textual`: mouse, panes, live updates) — *parked*; revisit after the polish pass, when `rich` feels limiting.

## 6. Code Health
_Cross-cutting code quality: whole-repo review, architecture principles, repo-wide refactors,
conventions, tech-debt, cross-cutting performance. The code analogue of Balance. (Subsystem-local
work stays in Engine/Bots/CLI.)_

**State:** No systematic review done yet. Codebase is milestone-built (M0–M6) with a green suite
(252 passing) and a deliberate architecture (data / config / effect-registry split, pure stdlib
engine) — but has never had a dedicated quality pass.

**Next:**
1. **Full code-review pass** across the whole repo (Engine + Bots + CLI + sim) — the big one to get to.
2. **Code conventions + a tech-debt register** so known seams are tracked, not rediscovered.

## 7. Balance
_The central question: are the decks fair? Winrates, matchup matrix, tuning decisions + the data
behind them. Consumes Bots + the sim harness. Roadmap: `simulation-platform-roadmap.md`._

**Two outcome targets:** (a) every **deck** winrate in **40–60%**; (b) every **card's impact**
within **±10%**.

**State:** Neither target met yet. Deck spread too wide — **colony_food_swarm ~23%** (real signal),
**food_otk overrated** by greedy. Card-impact target can't even be measured reliably yet (the
`metrics.py impact` confound — Engine #1). **Gated on Bots:** these numbers only mean something
once pilots are trustworthy — but that work is Bots, not Balance.

**Next:**
1. **Deck equality → pull every deck into 40–60%.** Active levers: Decision H food-economy re-derivation (in progress; Methuselah + food_otk floor shipped; 20-cost bodies, Landmarks, Colony/Egg numbers still open) + card-design fixes for the confirmed-weak decks (colony's early game, food_otk's kill window).
2. **Card equality → every card's impact within ±10%.** Blocked on the metrics fix (Engine #1) and trustworthy pilots (Bots).
3. **Triage the open sim findings:** colony early-game weakness (real → card-design look) vs cats-vs-aggro (bot bug → leave the card).

## 8. Meta
_Holding it together: this dashboard, milestone/roadmap tracking, conventions._

**State:** Milestones M0–M6 tracked; `simulation-platform-roadmap.md` is the long-term north star.
Docs reorg in progress (this file is step 1).

**Next:**
1. **Finish the reorg:** split `todo.md` into per-area `backlog.md` files (the "sort" step).
2. Keep `STATUS.md` as the session entry point; retire `todo.md` once sorted.
3. **Project-level `CLAUDE.md` + project skills** — a repo `CLAUDE.md` (conventions, how to run things) and reusable skills for repeatable workflows (e.g. the standard gauntlet run, a flavor pass).
