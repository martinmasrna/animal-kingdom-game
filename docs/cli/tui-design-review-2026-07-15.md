# TUI design review — 2026-07-15

## UX objective

Make the terminal UI a calm, legible tabletop for learning and replaying *Animal Kingdom*: a player should always know whose turn it is, how many actions remain, what they can do now, and why a board location matters, without leaking hidden information or making the 80×24 layout unusable. The general game UI should retain automatic JSONL recording as a useful assurance and replay artifact, rather than presenting recording as the product’s primary purpose.

## Evidence, hypotheses, and task priorities

**Evidence** below is from the cited source or read-only test interaction. **Hypothesis** is an interaction conclusion to validate with first-time players; it is deliberately not presented as observed user research. Risks are relative implementation/design risk, not estimates of effort.

### 1. Explain a selected card’s legal placements in board language

**Player problem.** A new player can select a card and see highlighted targets, but does not learn *why* other crossroads are unavailable: disconnected path, an equal-or-stronger enemy top card, an occupied location, or a card-specific restriction. The game’s core spatial rule is connection, and covering requires strictly greater strength; both are unusually easy to misread as combat or movement rules.

**Proposed behavior/layout.** When a card is selected, retain the clean highlight of legal targets, then offer one short placement explanation in the persistent prompt and a focused detail on the current/hovered crossroad: `Legal: connected empty crossroad`, `Cover: opponent STR 4; your STR 5`, or `Not reachable: no connected path`. Do not paint every illegal crossroad with prose. On wide layouts, the inspector can provide the fuller explanation; on compact layouts, the prompt cycles with the keyboard focus and a help/inspect view supplies detail.

**Why it matters.** It teaches the game’s differentiator at the moment of action, reduces trial-and-error, and prevents the false expectation that strength is health or damage.

**Terminal-size impact.** Wide: selected-card + location explanation in the inspector. Compact: one-line reason replacing secondary metadata; details remain reachable through inspection.

**Risk.** Medium — legality reasons must be accurate, mutually understandable, and compatible with unusual card effects.

**Evidence.** The UI currently derives only legal `PlaceAction` targets and highlights them (`animal_kingdom/tui/app.py:916-949`), while the prompt says only “Choose a highlighted location” (`animal_kingdom/tui/app.py:883-908`). The rules define connection and strict-greater covering as core concepts (`docs/rules/mental-model.md`, “The board is a graph” and “A unit is a single number”). **Hypothesis:** a legal-only highlight is insufficient teaching feedback for a first game.

### 2. Make stacks and covering readable without hover

**Player problem.** A covered unit is buried, not removed, and only the top card occupies/connects. This is fundamental but visually compact stacks can be misread as a unit having been destroyed. Stack detail exists on mouse hover and in the inspector, but the inspector is absent in narrow layouts and hover is not a keyboard-first interaction.

**Proposed behavior/layout.** Give every non-empty crossroad a compact, consistent stack cue (top owner/strength plus `+N below` when applicable). When focus lands on a crossroad, use the contextual line to state `top controls/connects`; inspection expands bottom-to-top history, including that a covered card can resurface. In a selected-cover action, explicitly name the incoming and covered top cards before confirmation.

**Why it matters.** It makes covering a tactical state change rather than an unexplained disappearance, and protects the connection mental model.

**Terminal-size impact.** The board cue must fit at 80×24; the full card list is progressive disclosure. No extra permanent rail is required.

**Risk.** Low–medium — mostly presentation, with care needed for dense stacks and existing board-render fit guarantees.

**Evidence.** Board hover tooltips enumerate a stack bottom→top (`animal_kingdom/tui/app.py:213-250`); the inspector lists it top first (`animal_kingdom/tui/app.py:1023-1074`); the compact CSS hides that inspector (`animal_kingdom/tui/app.py:504-579`). The read-only TUI test confirms the stack data is available but accessed via hover/rail (`animal_kingdom/tests/test_tui.py:517-555`). **Hypothesis:** keyboard and compact players will otherwise treat covered units as removed.

### 3. Promote the turn/action and win-race state to a compact, persistent scoreboard

**Player problem.** Food, hand, deck, and remaining actions are useful, but they are split across status, opponent line, and contextual notice; at compact height the status and opponent lines disappear. A first-time player needs food’s threshold and the two-action cadence; repeat players need a fast scan of both food races and the active turn.

**Proposed behavior/layout.** Reserve a stable one- or two-line scoreboard, with turn owner, actions left for the active player, and both food values/progress toward the target. Keep personal hand/deck counts secondary. Make “food is a win race, not a spendable mana bar” discoverable in the first-game help and inspector.

**Why it matters.** These are the only persistent resources and victory race; preserving them prevents a compact layout from becoming board-plus-hand with no strategic frame.

**Terminal-size impact.** Wide may retain the existing richer player lines. At 80×24, preserve the scoreboard and reclaim space from the less time-critical footer, deck trackers, and verbose recent history.

**Risk.** Low — information prioritization/layout work, subject to fitting the existing board and hand shelf.

**Evidence.** The current summary has food, cards, deck, and actions (`animal_kingdom/tui/app.py:721-753`), but compact-height rules hide status, opponent, and footer (`animal_kingdom/tui/app.py:570-579`). Food is a victory condition and actions are the game’s resource (`docs/rules/mental-model.md`, “The whole system in one breath”). The 80×24 test verifies board and shelf fit, not persistent player-state visibility (`animal_kingdom/tests/test_tui.py:56-130`). **Hypothesis:** the win-race scan should outrank deck inventory in compact play.

### 4. Give the first game a staged “learn while playing” help path

**Player problem.** The `?` overlay is a control reference with recorder commands, but not a succinct explanation of the game loop, connection, covering, stacks, or the two win conditions. It assumes the player already understands what the highlighted board is showing.

**Proposed behavior/layout.** Reframe help into two layers: a short, plain-language “How a turn works” and “What this board means” layer for play, plus a separate recording/review section. Link inspection to the relevant rule concept (e.g., a stack view offers “top card controls this crossroad”). Keep controls available, but never make them the opening content.

**Why it matters.** The game deliberately rejects familiar card-game assumptions—no mana, health, combat damage, or spells—so a concise in-context correction prevents incorrect learning.

**Terminal-size impact.** Modal/progressive disclosure only; compact help should paginate or section rather than shrink text below readability.

**Risk.** Low — content and hierarchy; validate wording against the canonical rules.

**Evidence.** Current help foregrounds keys and recorder functions (`animal_kingdom/tui/app.py:443-483`); the test asserts those recorder controls are present (`animal_kingdom/tests/test_tui.py:458-477`). The canonical misconception list and rules are in `docs/rules/mental-model.md`. **Hypothesis:** players’ first need is a rules orientation, before audit/recording controls.

### 5. Turn the inspector into a consistent inspect/focus mode

**Player problem.** Wide layouts can inspect a selected card, highlighted legal target, or hovered stack, but the information vanishes when the pointer leaves and there is no explicit keyboard affordance to pin an item. Repeat players and replay reviewers need to compare effects, effective strength, food cost, and board stacks deliberately.

**Proposed behavior/layout.** Add a single conceptual inspect/focus mode: mouse hover previews; keyboard focus is persistent; an inspect command pins the chosen card/crossroad until dismissed. The wide inspector is its expanded home; compact view opens the same content as a temporary panel/modal. Use it for card text, effective (not printed) strength, stack order, ownership, and legal reason.

**Why it matters.** It makes the information architecture work for mouse and keyboard, supports accessibility, and gives replay review a reliable detail surface without cluttering the board.

**Terminal-size impact.** Wide: existing rail gains persistence. Compact: temporary overlay, returning exactly to prior selection and board focus.

**Risk.** Medium — needs clear focus semantics so it cannot conflict with target navigation or action selection.

**Evidence.** Board hover sets tooltip and sidebar context (`animal_kingdom/tui/app.py:213-257`, `1023-1074`); arrow keys navigate legal targets (`animal_kingdom/tui/app.py:581-594`, `1142-1150`); no pinned inspect behavior is present. The existing side rail is shown only at the inspector breakpoint (`animal_kingdom/tui/app.py:486-579`). **Hypothesis:** a deliberate inspection mode will be more dependable than pointer-only discovery.

### 6. Replace cryptic recent-action icons with a reviewable public timeline

**Player problem.** The current six-event history is rendered as icons whose narration is only available through tooltips. That conserves space but makes the sequence difficult to reconstruct, especially on keyboard-only play and in post-game review where “what changed?” is the key task.

**Proposed behavior/layout.** Keep a compact visual activity strip during live play, but make activating/focusing it reveal a chronological public timeline with full narration and turn grouping. After a game, make this the default review surface alongside the saved JSONL link; offer stepping through recorded decisions as a future capability, but do not require a separate replay UI for the initial improvement.

**Why it matters.** Replay review needs decision context, not merely proof that an action happened; a readable public timeline also helps players understand bot turns they did not watch.

**Terminal-size impact.** Wide may retain a narrow strip and use the inspector for expansion. Compact hides the strip or folds it into inspect/help; the timeline is on demand.

**Risk.** Medium — requires a clear distinction between public narration and any hidden information, plus a sensible post-game entry point.

**Evidence.** `RecentLog` deliberately renders glyphs with tooltip narration (`animal_kingdom/tui/app.py:96-133`), and the test confirms only icon text is visible while full narration is tooltip-only (`animal_kingdom/tests/test_tui.py:227-265`). Completed games currently surface only an “Open JSONL log” link (`animal_kingdom/tui/app.py:883-915`). **Hypothesis:** the timeline is the highest-value bridge from a finished game to later replay tooling.

### 7. Reposition setup, naming, and launch around “Play,” with recording as an always-on benefit

**Player problem.** The current title, setup heading, and launcher call the experience a “Human Benchmark Recorder” / “New recorded game.” That makes ad-hoc play feel like data-entry and obscures the planned general game UI. Meanwhile, scheduled cohorts are genuinely useful and should remain discoverable for research play.

**Proposed behavior/layout.** Name the app and default setup **Animal Kingdom** / **New game**. The launcher should offer a simple Play path (last settings/new game) and a distinct Scheduled games path, while retaining saved JSONL as an unobtrusive game detail and an end-of-game review option. Have `./run` open this UI for a human game with an explicit headless/simulation route preserved; keep `./record` as a compatibility alias until documentation and workflows move.

**Why it matters.** It aligns the product’s language with player intent while preserving the project’s valuable recording and cohort workflow.

**Terminal-size impact.** Setup remains compact and modal; it should remember last choices and use short human-readable deck names/descriptions where they fit.

**Risk.** Medium — affects launch contracts, docs, and users of the existing recorder command; compatibility needs an intentional transition.

**Evidence.** The backlog has already decided to promote the recorder, rename it, make `./run` launch the TUI, preserve headless play, and later alias/retire `./record` (`docs/cli/backlog.md`). Current app title/setup copy remains recorder-first (`animal_kingdom/tui/app.py:381-443`, `486-487`), while `record` and `run` still invoke different products (`record`, `run`). **Hypothesis:** “Play” will improve first-use comprehension without reducing research value.

### 8. Preserve settings and make repeat play one decision, not five fields

**Player problem.** Repeat players commonly want “same deck, opponent, difficulty, and seat; new seed.” The current ad-hoc setup resets a five-field form with a fresh random seed every time.

**Proposed behavior/layout.** On completion, offer **Play again** (same matchup, fresh seed), **Rematch** (same seed), and **Change setup**. The launcher/setup should prefill last-used deck, opponent, bot, seat, and map, visibly marking the seed behavior. Scheduled cohort parameters remain authoritative and should not be silently overwritten.

**Why it matters.** It shortens the repeat-game loop, makes intentional replay possible, and supports comparing a learned matchup without erasing the distinction between a rematch and a new trial.

**Terminal-size impact.** Post-game choices fit in the contextual line; full settings stay modal. No additional persistent UI.

**Risk.** Low–medium — persistence scope and cohort-vs-ad-hoc boundaries need a clear policy.

**Evidence.** The CLI backlog explicitly calls for settings persistence (`docs/cli/backlog.md`). On game end, the current UI offers only Enter for a new game or next scheduled game (`animal_kingdom/tui/app.py:883-908`, `1152-1172`), and setup always creates a fresh random seed (`animal_kingdom/tui/app.py:399-443`). **Hypothesis:** repeat play is a frequent enough task to deserve a direct path.

## Task model

| Moment | Highest-value player task | UI support to prioritize |
| --- | --- | --- |
| First game | Learn the two-action loop; choose a card; understand legal placement, connection, covering, stacks, and food/HQ wins. | Priorities 1–4; no hidden-state leakage; rule language at decision time. |
| Repeat game | Scan the race, execute a known plan quickly, inspect an unfamiliar interaction, restart with familiar settings. | Priorities 3, 5, and 8; keyboard parity and minimal setup friction. |
| Replay review | Reconstruct pivotal decisions and board changes; inspect card/stack context; reach the durable JSONL record. | Priorities 5–7; public chronological timeline and a clear review entry. |

## Information hierarchy

**Always visible:** current turn/actor, actions remaining when relevant, both food totals and target, board ownership/top-of-stack cue, available hand/action choices, selected-card state, and a clear next action.

**Contextual:** selected card text and effective strength; legal-target and legality explanation; focused crossroad/HQ ownership and stack summary; bot-thinking state; the immediately relevant effect choice.

**Progressive disclosure:** full stack/card details, deck composition and opponent-known-card accounting, full action timeline, rules/tutorial, recording controls and path, cohort progress, setup/configuration, and post-game diagnostics.

## Responsive layout intent

### Wide terminal (about 130×32 and above)

```text
┌────────────────────────── GAME STATE / TURN / FOOD RACE ──────────────────────────┐
├──── YOUR DECK ────┬────────────── BOARD: HQs, CROSSROADS, TOPS ─────────┬ INSPECT ┤
│ known copies      │                                                       │ card /   │
│ remaining         │      [focused legal target / stack cue]              │ stack /  │
│                   │                                                       │ reason   │
├───────────────────┴────────────── PUBLIC ACTIVITY STRIP ─────────────────┴─────────┤
│ CONTEXT: next action + actions left + selected-card/target explanation             │
├────────────────────────────── HAND / DRAW / EFFECT CHOICES ────────────────────────┤
└──────────────────────────── HELP · INSPECT · REVIEW · QUIT ────────────────────────┘
```

### Compact terminal (80×24)

```text
┌──────── TURN · ACTIONS · YOU/OPPONENT FOOD / TARGET ────────┐
│                    BOARD: HQs / CROSSROADS                  │
│              top cards + compact stack/target cues           │
│                                                              │
├──────────── CONTEXT: what to do / why focused location ──────┤
│  HAND / DRAW / EFFECT CHOICES  ← horizontal browse if needed │
└──────────────────── ? Help · Inspect · Quit ─────────────────┘

On demand: inspect panel (card, stack, legality); help/tutorial; timeline/review.
```

At 110–129 columns, retain the inspector **or** deck tracker only when it does not compromise the board, prompt, or hand. Deck trackers are secondary to inspectability. At compact height, preserve the scoreboard and contextual line before any deck inventory, footer wording, or activity strip.

## Brief interaction flows

### Empty placement

1. Player selects a playable card by number/click; the card is visibly selected.
2. Board highlights legal empty crossroads; focus starts on one and the context states why it is legal (for example, “connected to your HQ chain”).
3. Player moves focus or clicks a target; inspect can reveal the connection explanation if desired.
4. Confirming places the card, updates actions/food/board state, and adds a public timeline entry.

### Covering an enemy

1. Player selects a card; eligible enemy tops are highlighted distinctly from empty legal placements.
2. Focusing an enemy stack states the comparison: incoming effective strength versus opponent top strength, and that the opponent card is covered (buried) rather than removed.
3. Player confirms; the board’s stack cue changes and the inspector/timeline exposes the new top and buried card.
4. The next state makes clear that the top card now controls connection.

### Help and inspection

1. `?` opens play help first: turn/actions, placement/connection, covering/stacks, food/HQ wins; controls and recording are a secondary section.
2. From board or hand, Inspect opens/pins details without submitting an action; Escape returns to exactly the prior selection/focus.
3. In a finished game, Review opens the public timeline and exposes the JSONL record as the durable external artifact.

## Non-goals

- Do not change rules, bot behavior, card data, recording fidelity, or hidden-information boundaries.
- Do not replace the Textual recorder with a graphical/web client.
- Do not overload the first pass with an animated combat metaphor; this game has no combat-damage step.
- Do not expose the opponent’s hand, deck order, or unobserved deck contents in inspection or review.
- Do not require a mouse; every essential action and inspection must remain keyboard-capable.

## Unanswered questions

- What terminal sizes and input modes (mouse, keyboard only, screen reader) do actual players use most?
- Which legal-placement explanation taxonomy is both complete and concise once all card-specific placement effects are included?
- Should post-game review be an in-app timeline first, a deterministic replay player first, or a small bridge to both?
- Which settings belong to local persistence, and how should a user see/reset them?
- Should the general launcher expose scheduled cohorts to ordinary players, or keep them behind an explicit “research/benchmark” entry?
