# Engine crash fuzz, 2026-11-05

**Tool:** `tools/engine_fuzz.py`. Random 30-card decks over every collectible card (204 cards, copy limits kept), a
random legal action each step from whichever seat is to act, one seeded stream per game (`random.Random(seed)` picks
the decks and the actions; `new_game(seed)` the engine's own chance). A 3% chance to end the turn early once an action
is taken, and a 30% chance that the seat whose mulligan waits underneath makes its choice first
(`rules.apply_early_mulligan`). Python engine only. It records every exception from `legal_actions`, `apply_action` or
`is_terminal`, every offered action that `apply_action` refused, and every game past 300 actions; groups them by the
traceback's last engine frame; keeps the shortest reproduction per group in `results/engine_fuzz.json`.

    .venv/bin/python tools/engine_fuzz.py --games 5000 --seed 0          # the run below, 16 s on 4 cores
    .venv/bin/python tools/engine_fuzz.py --replay 2800 --show          # one game, where it fails

## The run

5,000 games (seeds 0–4999), 317,650 actions. Every collectible card was placed at least 110 times; 5,230 early
mulligans; 18,460 pending choices, 3,861 pending placements, 24,515 roams, 3,826 early turn ends.

| Group | Games | Traceback line | Fixed or left | Reproduction |
|---|---|---|---|---|
| Exceptions from `legal_actions` / `apply_action` / `is_terminal` | 0 | — | — | — |
| Offered actions refused by `apply_action` | 0 | — | — | — |
| Past 300 actions | 1 | none (no exception) | left: not an engine fault | seed 2800, index 300 |

**The long game (seed 2800).** At action 300 it is turn 263: both decks and hands are empty, A's units on the board can
Roam, B has nothing to do and passes. A Roam counts as acting (`rules._end_turn`: `roams_<player>`), so the "two idle
turns in a row end the game" rule never fires, and the game runs until the 400-turn cap (`config.max_turns`) ends it at
action 369 by food (B 73, A 64). The engine does what its rules say; nothing raises and the game ends.
`test_engine_fuzz.py::test_long_game_ends_at_the_turn_cap` holds it.

A design note for Martin, not a bug: in a real game a player out of cards with a roamer can keep the game going to the
turn cap by walking a unit back and forth. With humans the cap is far off (400 turns), so it only matters if someone
stalls on purpose.

## Wider sweeps (same tool, to check the clean result)

- 95,000 more games (seeds 100000–194999): 5,981,870 actions, 0 exceptions, 0 refusals, 25 long games.
- 20,000 games with no early turn ends (`--pass-rate 0`, seeds 300000–319999): 0 exceptions, 0 refusals, 3 long games.

All 29 long games re-played to the end: each one ends by the turn cap (21) or by food (5) with both decks and hands
empty, or by the turn cap (3) with one seat holding a single card it can't place (an Orca, the legendary Anaconda) while
the other roams. Same pattern as seed 2800.

## Phase 2: effect-biased games and the human games (supervisor's request)

**Biased mode** (`--biased --games 20000 --seed 5`, seeds 500000–519999): each deck holds at least six cards with a Roar,
Dawn, Dusk, Fall, Flee, Spikes, Poison, Apex Predator or Roam; the action stream weights a placement of such a card x4,
a placement that covers an enemy x3, a skip x0.2. 20,000 games, 1,300,815 actions, 66 s: **0 exceptions, 0 refusals**,
3 long games (the same lone-roamer pattern; repro seed 500333 `--biased`, index 300).

What the bias actually changed, measured over 1,000 games of each mode: covering placements went from 9% to 17% of
placements. Effect cards went only from 79% to 86%, because 165 of the 204 collectible cards carry one of those words
(Roar alone: 114), so uniform decks are already mostly effect cards. The skip weight did nothing: in today's engine no
choice outside the mulligan is optional (0 of 2,996 non-mulligan choices offered a skip in 300 biased games).

**Human-game probe** (`--human`): every record under `results/human_games` (2,437 logs) read through `web/renamed.py`;
302 replay to their end on today's cards. At each of their 8,571 positions every legal action was applied once on a
clone (147,095 actions), then `is_terminal` and `legal_actions` asked of the result.

| Group | Hits | Traceback line | Fixed or left | Reproduction |
|---|---|---|---|---|
| crash: `KeyError: 'fish_legend_jellyfish'` | 3 | `animal_kingdom/engine/state.py:481 ensure_mates` (`card = self.cards[u.card_id]`), from `effects._op_mulligan` | **fixed** (commit 717a207) | `results/human_games/web/web_20261010T161459_LBFBOA.jsonl` line 7, action index 1, `{"kind": "choice", "choice": "__skip__"}` |

**Cause.** That log's deck A still lists four old design ids (`fish_legend_jellyfish`, `fish_legend_manta_ray`,
`fish_legend_piranha`, `fish_legend_tuna`) that `web/renamed.py` doesn't map (their map is in
`tools/rename_design_ids.py`). `new_game` took the unknown ids. The logged game happened never to look one up, so it
"replayed"; skipping the mulligan at index 1 instead ends it, and `ensure_mates` looks up every card in hand.

**Fix.** `new_game` (`animal_kingdom/engine/state.py`) raises `EngineError("unknown card ...")` for a deck id the card
registry doesn't hold. No card plays differently. Rust mirror: `engine_rs/src/py.rs` `new_game` already refuses unknown
ids ("unknown card"), so no Rust change; the two engines now agree here. Tests:
`test_unknown_card_id_is_refused_at_setup`, `test_the_logged_position_no_longer_crashes`.

**Effect of the fix on the human games.** 296 logs replay now, not 302. The six that stop are the ones whose decks hold
unknown ids and whose logged path never touched them (3 of them 1–3 actions long, conceded):
`web_20260930T212323_6FKR7W:1` (verminus), `web_20260930T235425_0J1IAA:0` (dog, raksha),
`web_20261010T161459_LBFBOA:4` and `:7` (fish_legend_*), `web_20261010T175253_ZRPDWG:9` (food_aggro_legend_*),
`web_20261010T230503_BNGM8A:11` (food_aggro_legend_*, hoofed_legend_*). The web replay viewer catches the `EngineError`
and says "its cards have changed since", as it already does for the other unreplayable logs. Rerun after the fix: 296
logs, 8,475 positions, 145,226 actions, **0 failures**.

Not done (outside the engine): 575 human logs hold ids no card has; 27 distinct ids, mostly old design placeholders
(`verminus` 231 logs, `dog` 203, `raksha` 171, `handlock_legend_*`, `fish_legend_*`, ...). Adding the old design-id map
to `web/renamed.py` would bring some of those games back as replays; that is a web/data change for Martin to decide.

## Tests

`animal_kingdom/tests/test_engine_fuzz.py`: 40 seeded games raise nothing and end; seed 2800 ends at the turn cap; the
tool reports a planted crash and a planted refusal with seed, decks and action; `play(seed, stop_at=i)` rebuilds the
position before action i. Phase 2 adds the two tests above for the one group it found. No xfail tests.

## Counts

- Games: 5,000 uniform + 20,000 biased (plus 115,000 uniform in the wider sweeps)
- Human games probed: 296 of 2,437 logs replay (302 before the fix), 8,475 positions, 145,226 actions tried
- Failure groups: 2. Long games (lone roamer to the turn cap): 1 + 3 games, left as not an engine fault. Crash
  `state.py ensure_mates KeyError` (unknown card id): 3 hits, fixed.
- Fixed: 1
- Left as xfail: 0
- Left, not an engine fault: 1
