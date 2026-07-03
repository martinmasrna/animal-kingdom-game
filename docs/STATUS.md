# Animal Kingdom — Project Status

> **This is the map.** Open it first each session. It says where every area stands and the
> next 1–3 moves in each — nothing more. The full open list per area lives in its
> `docs/<area>/backlog.md`; deeper detail in that area's other docs. Keep this file short; when a
> "Next" item is done, replace it, don't append history.
>
> _Last updated: 2026-07-02._

## The project in one paragraph

A headless rules engine + bots + simulation harness for *Animal Kingdom*, a 2-player tactical
board game. The end goal is **trustworthy balance data**: run thousands of bot-vs-bot games and
learn whether the 7 premade decks are fair. Human/web UI is out of scope for now; the engine is
a pure, transport-agnostic library so a UI can drop on later. Engine built in milestones
**M0–M6** (all ✅; M6 TurnBot committed in `aecfdf5`).

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
types, keyword definitions. Docs: `rules/` (`overview.md`, `keywords.md`, `maps.md`). Backlog: [`rules/backlog.md`](rules/backlog.md)._

**State:** Stable and documented. Keyword registry canonical (Flight, Immovable, Fragile, Apex
Predator, Battlecry, Deathrattle). Immovable/Stealth deep-dive ruled & shipped 2026-07-02.
Card-type model (Unit/Egg/Landmark) resolved *provisionally* (decision C).

**Next:**
1. **Confirm-or-revert the Landmark card-type decision** before `cards.json` hardens (Apex-eats-Landmark flavor wart included).
2. **Re-examine Immovable** (naming + effect footprint) — flagged 2026-07-02, *gated on referee-quality balance data*.
3. **Terminology sweep:** "Discard" → "Remove Pile" across all docs/data.

## 2. Cards & Flavor
_The concrete content: the 7 decks (effects, numbers, names) and their theme. Docs: `cards/`
(`cards.md`, `card-candidates.md`, `decks/`, `decks/flavor-review.md`), `data/cards.json`. Backlog: [`cards/backlog.md`](cards/backlog.md)._
_**Flavor** (subcategory): animals, biology, folklore, naming — a recurring audit pass, not a separate area._

**State:** All 7 decks content-complete (4-4-6) and **built into `cards.json` + the effect registry
(build #5 done)** — the full test suite runs on the reworked pool. Legendary names **provisional**
(24/28 machine-suggested 2026-06-30; only the 4 Cats are final). Remaining card work is flavor + text cleanup.

**Next:**
1. **(Flavor) Dedicated legendary-name review** — the stricter, do-not-skip pass before flavor-lock.
2. **(Flavor) Reskins & collisions:** Black Panther → leopard (not jaguar); rename the placeholder hornet; re-cast the generic-tag animals.
3. **Re-cast generic-tag animals + standardize Deathrattle card-text wording** — the data-level flavor/text cleanups.

## 3. Engine
_Core game code: state, effect stack, rules-as-code, the sim/analysis harness (`sim/`),
architecture, performance, tests. (Kept separate from CLI.) Backlog: [`engine/backlog.md`](engine/backlog.md)._

**State:** M0–M6 shipped; pure stdlib engine + effect interpreter + sim harness. Full suite
**260 passing, 1 xfailed**. (M6 TurnBot committed in `aecfdf5`.)

**Next:**
1. **Fix `metrics.py` `impact` confound** — `win_rate_when_drawn` is biased by win-vs-loss game length (a harness bug, not card quality).
2. **State-representation speed** (struct-of-arrays) — *parked* until NN bots; measure clone cost first.

## 4. Bots
_The AI players and their quality. `bots/`. Backlog: [`bots/backlog.md`](bots/backlog.md)._

**State:** Ladder is **GreedyBot** (fast baseline) → **TurnBot** (M6, new middle tier) →
**RefereeBot** (calibration oracle). TurnBot smoke: improves-or-ties all 7 decks, but blows the
10× throughput gate (12×–266×). Anchored pilot measurement is now available via the factored
Bradley–Terry runner (`sim/ratings.py`): Random is the fixed floor, Referee is the observed ceiling,
and every pilot/deck/interaction estimate includes a confidence interval. The full acceptance
cohort still needs to be run and interpreted before Balance is ungated.

**Next:**
1. **Run the anchored-rating acceptance cohort.** Use the paired 200-game design in
   [`bots/pilot-ratings.md`](bots/pilot-ratings.md), inspect pilot confidence intervals and
   execution-difficulty interactions, and decide whether the pilots are trustworthy enough to
   ungate Balance. Human calibration remains optional pending a curated comparable cohort.
2. **TurnBot → default pilot?** Pass its acceptance run (200/opp) and clear the 10× throughput gate
   (lower determinizations/beam or a turn-depth cap; A/B speed-vs-winrate), then decide whether
   `./report` switches from `greedy,greedy` to `turn,turn`.
3. **Referee v3 shipped (`3794071`, 2026-07-03).** `nodes 1000→150` + `reply_width 4→8`:
   ~1.31× faster than v2 and *stronger* on every deck, which also closed the colony ~7-pt
   calibration gap. Done — method/data in
   [`bots/referee-search-tuning.md`](bots/referee-search-tuning.md).
4. **Known blind spot:** `region_control` over-values the row-2 spine, so neither bot contests
   row-1/3 as an HQ-rush lane.

## 5. CLI / App
_The human interface. `cli.py`, `render/`. Backlog: [`cli/backlog.md`](cli/backlog.md)._

**State:** `rich`-based polish done (color by seat/rarity, in-place redraw, card-first targeting).
Plain stdin/stdout loop underneath. Lightest area right now.

**Next:**
1. **Fix the `map_b` board overflow** — the 5-column map renders ~95 cols and wraps on an 80-col terminal, so `./run`'s default (map_b + 2-actions) looks broken. Compress the geometry or make it responsive.
2. **Full TUI rewrite** (`textual`: mouse, panes, live updates) — *parked*; revisit when `rich` feels limiting.

_Visual-polish pass done (commit `7d1b961`): dimmed empties, held-region chips, food progress bars, tighter cards, first renderer test._

## 6. Code Health
_Cross-cutting code quality: whole-repo review, architecture principles, repo-wide refactors,
conventions, tech-debt, cross-cutting performance. The code analogue of Balance. (Subsystem-local
work stays in Engine/Bots/CLI.) Backlog: [`code-health/backlog.md`](code-health/backlog.md)._

**State:** No systematic review done yet. Codebase is milestone-built (M0–M6) with a green suite
(260 passing) and a deliberate architecture (data / config / effect-registry split, pure stdlib
engine) — but has never had a dedicated quality pass.

**Next:**
1. **Full code-review pass** across the whole repo (Engine + Bots + CLI + sim) — the big one to get to.
2. **Code conventions + a tech-debt register** so known seams are tracked, not rediscovered.

## 7. Balance
_The central question: are the decks fair? Winrates, matchup matrix, tuning decisions + the data
behind them. Consumes Bots + the sim harness. Roadmap: `balance/simulation-platform-roadmap.md`. Backlog: [`balance/backlog.md`](balance/backlog.md)._

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
_Holding it together: this dashboard, milestone/roadmap tracking, conventions. Backlog: [`meta/backlog.md`](meta/backlog.md)._

**State:** Milestones M0–M6 tracked; `balance/simulation-platform-roadmap.md` is the long-term north
star. Docs reorg **done**: STATUS.md dashboard + per-area `backlog.md` files; `todo.md` retired.

**Next:**
1. **Project skills** — reusable skills for repeatable workflows (e.g. the standard gauntlet/report run, a flavor-review pass). *(Project `CLAUDE.md` at repo root: done.)*
