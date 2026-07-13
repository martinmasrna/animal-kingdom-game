# Animal Kingdom — Project Status

> **This is the map.** Open it first each session. It says where every area stands and the
> next 1–3 moves in each — nothing more. The full open list per area lives in its
> `docs/<area>/backlog.md`; deeper detail in that area's other docs. Keep this file short; when a
> "Next" item is done, replace it, don't append history.
>
> _Last updated: 2026-07-08._

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
3. **Terminology sweep:** "Discard" → "Remove Pile" — canonical docs done (`overview.md`/`keywords.md`); legacy `cards.md`/`card-candidates.md` refs remain.

## 2. Cards & Flavor
_The concrete content: the 7 decks (effects, numbers, names) and their theme. Docs: `cards/`
(`cards.md`, `card-candidates.md`, `decks/`, `decks/flavor-review.md`), `data/cards.json`. Backlog: [`cards/backlog.md`](cards/backlog.md)._
_**Flavor** (subcategory): animals, biology, folklore, naming — a recurring audit pass, not a separate area._

**State:** All 7 decks content-complete (4-4-6) and built into `cards.json` + the effect registry.
**Locked card review applied 2026-07-04** (cats trims Prince Leo/Princess Lea 4→3 + Queen Adira 6→5;
Skunk 2→4; Hornet redesign; new Aggro legendary **Gale**; **Stoop→egg_control** as rare "Peregrine
Falcon" 6→4; **Black Swan** rare→legendary; **Goliath** legendary→rare; **Vulture** shelved) plus a
food_otk OTK-lean buff pass. Legendary names still **provisional**. Remaining card work is flavor + text cleanup.

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
1. **State-representation speed** (struct-of-arrays) — *parked* until NN bots; measure clone cost first.

_(The old `metrics.py` "impact game-length confound" item was retired 2026-07-11: any length effect is common-mode within a deck and cancels in the within-deck, same-rarity relative reads impact is actually used for.)_

## 4. Bots
_The AI players and their quality. `bots/`. Backlog: [`bots/backlog.md`](bots/backlog.md)._

**State:** Ladder is **GreedyBot** (fast baseline) → **TurnBot** (M6, new middle tier) →
**RefereeBot** (calibration oracle). TurnBot smoke: improves-or-ties all 7 decks, but blows the
10× throughput gate (12×–266×). Anchored pilot measurement is now available via the factored
Bradley–Terry runner (`sim/ratings.py`): Random is the fixed floor, Referee is the observed ceiling,
and every pilot/deck/interaction estimate includes a confidence interval. The full acceptance
cohort still needs to be run and interpreted before Balance is ungated.

**Next:**
0. **★ Learning pilot — the strategic bet (handoff written 2026-07-04).** The whole heuristic ladder
   shares a hand-written, current-state-only evaluator with a structural judgement ceiling — proven
   when a *human* piloting egg went ~even vs referee-cats where the bot scores ~18% (egg's scaling
   plan is invisible to a present-only evaluator). Direction: a pilot whose judgement is *learned
   from experience*, no strategy-class blind spots, measured against recorded human play. Conceptual
   brief for the AI/ML specialist: [`bots/learned-pilot-handoff.md`](bots/learned-pilot-handoff.md).
   **UPDATE 2026-07-05 — bet re-scoped, not obviated.** The *delayed-single-card-payoff* slice of
   this ceiling is now closed by a hand-written eval term (`pending_payoff`, commit `ad4c885`; egg/ramp
   re-rated up, egg into band) — real evidence the *smallest step* (patch the judgement, keep the
   search) can pay off cheaply. **But the canonical egg-vs-cats gap persists** (~24% bot vs ~50%
   human): out-scaling cats needs the pilot to *plan* a multi-turn grow-then-win, which a per-position
   term can't do. So the bet's target narrows to the **multi-turn planning/scaling** gap; the
   present-state delayed-payoff part is handled. This tightens the handoff's open "smallest step vs
   full learned player?" question — the smallest step already banked one class of blind spot.
1. **Pilot-trust verdict IN (2026-07-03): TurnBot is a big step up from greedy but NOT oracle-level.**
   Paired oracle validation (turn vs referee, opp greedy, 60/opp × 7, `results/bot_quality/turn_vs_referee_all/`):
   referee beats turn on all 7 decks (sig. on 5), by ~+4pt (food_otk) to +14pt (ramp). The gaps are
   non-uniform, so the turn matrix **under-rates ramp/canine/egg and over-rates food_otk/colony/cats** —
   good for **directional** deck triage, not absolute 40–60% verdicts (see `bots/backlog.md`). Remaining:
   the anchored Bradley–Terry cohort (`bots/pilot-ratings.md`) for a full pilot/deck/difficulty rating,
   and (optional) referee-piloted matrices on any deck a tuning call actually hinges on.
2. **A/B harness unified — core done (`4e5fd74`).** `bot_comparison` now accepts parametrized bot
   specs (`--baseline-kind "turn:deck_reveal_choice_width=0"`), so config/flag A/Bs run through its
   paired-vs-fixed-opponent design instead of hand-rolled low-power mirrors. Follow-up: retire
   `referee_comparison`'s `--mirror-deck` mode + add the skill caveat. See
   [`bots/backlog.md`](bots/backlog.md).
3. **TurnBot → default pilot? Strength axis GREEN on all 7 decks; only throughput left.** The original
   acceptance cohort ran at **map_b + 1-action** — the wrong ruleset (now impossible: 2-action is the code
   default). Re-ran the full 7-deck cohort at 2-action (`results/bot_quality/turnbot_2action/`, 100/opp,
   seed 683470156): **TurnBot improves every deck** (all CIs>0) — aggro +18.3%, canine +6.6%, cats +9.0%,
   colony +41.3%, egg +11.4%, **food_otk +16.4%** (the 1-action "−9.4% regression" was an artifact),
   ramp +13.0%. So the switch is no longer blocked on any deck's *strength*; the only open gate is
   **throughput** on the deep-combo decks (food_otk 47.6×, egg/colony ~33×). Decide there (accept the
   slowdown for balance sims, or scope `./report` to fast decks). Node budget (`TURN_MAX_SEARCH_NODES=80`)
   shipped; turn-*depth* cap a no-op (cost is *breadth*); uniform determinization/beam trim rejected.
4. **Known blind spots:** (a) `region_control` over-values the row-2 spine, so neither bot contests
   row-1/3 as an HQ-rush lane; (b) **the evaluator scores *current* strength.** ◐ *Partially fixed
   2026-07-05* — **delayed single-card payoffs** (Egg hatch, Bear) are now credited by
   `pending_payoff=20` (commit `ad4c885`); egg/ramp re-rated up, egg into band overall, and the
   referee-quality re-baseline is in `results/matrix_referee_pending20/`. **STILL OPEN:** the
   *multi-turn scaling plan* (growing Rattlesnake→8 / Goliath→11 to out-body cats) — egg still wins
   only **~24% vs referee-cats** vs the human's ~50%; a per-position eval term can't orchestrate a
   grow-then-win plan. Note cats deflated ~69→63 mostly because **ramp** (a delayed-payoff deck the
   fix lifted) now beats it — *not* because egg's scaling got piloted — so cats may **still** be
   mildly inflated by the residual scaling gap; confirm the cats-nerf magnitude against human play
   into cats before committing.

## 5. CLI / App
_The human interface. `cli.py`, `render/`. Backlog: [`cli/backlog.md`](cli/backlog.md)._

**State:** `rich`-based CLI polish done, plus a **recorder (`./record`) Textual UI/UX pass landed
2026-07-04** (`tui/app.py`): centered board with preserved hitboxes, contextual action prompt +
inspector rail, responsive hand shelf / deck trackers / food bars, in-app JSONL link, `?` help overlay
— all kept working at the compact 80×24 layout.

**Next:**
1. **Fix the `map_b` board overflow in `./run`** (the `rich` CLI, `render/text.py`) — the 5-column map renders ~95 cols and wraps on an 80-col terminal. (The recorder now fits 80 cols; the `./run` renderer still needs the responsive/compressed geometry.)
2. **Full general-purpose TUI** (`textual`, beyond the recorder) — *parked*; revisit when `rich` feels limiting.

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

**State:** Deck picture measured under competent both-sides piloting (turn-vs-turn 7×7 + oracle-bias
correction) — see `balance/backlog.md`. **2026-07-04 pass:** locked card review applied; **food_otk
OTK-lean buff shipped (pending sim validation)** — leans *into* the OTK (Opossum food, Tortoise/Porcupine
5→7, Pufferfish draw, Gazelle 40→30), diagnostic = flip Scrooge from worst- to best-impact without
touching Scrooge itself. **egg_control retracted as a card problem** — its ~18% is a *pilot* artifact
(human egg ~50% vs referee-cats); the fix is a Bots one (search under-values dynamic strength, §4).
**cats_midrange (~69%) still the #1 nerf target but its number may be inflated** by that same pilot gap —
hold the nerf magnitude. **colony retracted** (greedy artifact, ~48% in band). Card-impact reads as a
within-deck, same-rarity relative signal (`per_card_stats`). Pilot caveat: TurnBot is sub-oracle (~+8pt) → matrix is directional.

**Next:**
0. **★ CURRENT ARC — build a trustworthy card-power ruler (the baseline deck).** Agreed 2026-07-13: a fixed 30-card no-synergy reference opponent (extend `sim/benchmark_set.py`), anchored by impact-equivalence *within* each rarity (vanilla-7 ground / vanilla-5 flying common; feel-set rare & legendary), run at **RefereeBot** vs all 7, to price cards and rebalance the 30. Pulling the synergy decks to beat that baseline is the *sequel* arc. Full plan + locked decisions + risks: [`balance/baseline-deck-arc.md`](balance/baseline-deck-arc.md). **NB:** all pre-`8c3d473` balance data below is stale draw-1 data and must be re-baselined.
1. **Deck equality → pull every deck into 40–60%.** Active levers: Decision H food-economy re-derivation (in progress; Methuselah + food_otk floor shipped; 20-cost bodies, Landmarks, Colony/Egg numbers still open) + a card-design fix for colony's early game. **food_otk's "kill window" lever struck** — the weakness was a stale-ruleset read (see Balance backlog ✅ verdict); needs a 2-action search-vs-search read before any tuning.
2. **Card equality → every card's impact within ±10%.** Read impact within-deck / same-rarity (`per_card_stats`); still gated on trustworthy pilots (Bots).
3. **Triage the open sim findings:** colony early-game weakness (real → card-design look) vs cats-vs-aggro (bot bug → leave the card).

## 8. Meta
_Holding it together: this dashboard, milestone/roadmap tracking, conventions. Backlog: [`meta/backlog.md`](meta/backlog.md)._

**State:** Milestones M0–M6 tracked; `balance/simulation-platform-roadmap.md` is the long-term north
star. Docs reorg **done**: STATUS.md dashboard + per-area `backlog.md` files; `todo.md` retired.

**Next:**
1. **Project skills** — reusable skills for repeatable workflows (e.g. the standard gauntlet/report run, a flavor-review pass). *(Project `CLAUDE.md` at repo root: done.)*
