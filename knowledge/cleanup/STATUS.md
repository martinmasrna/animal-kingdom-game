# Dead-code and duplication pass (2026-11-05)

A pass over `animal_kingdom/web`, `bots`, `sim`, `learn` and `tools/` for code nothing calls, logic written twice, dead
branches, and unread imports, variables and parameters. Behaviour is unchanged: every commit ran the fast Python tier and
the web client's `npm test` first. Engine, data, docs, results and the tests are out of scope (engine findings are listed
below, not made).

Branch: `claude/animal-kingdom-cleanup-yn3cqj` (the branch this cloud session may push to; the brief named
`code/cleanup`), from `main` at `70dc14e`.

## Baseline on main in this container

- Python fast tier: 3683 passed; 3 fail on main: `test_deck_docs.py::test_deck_doc_card_table_matches_cards_json`
  for `aristocrats`, `egg_control`, `hoofed` (the deck docs are stale against `cards.json`; docs are out of scope).
- Web `npm test`: Chrome is run through a wrapper adding `--no-sandbox` (the container runs as root, and the harness
  launches Chrome without it). 96 pass, 12 fail on main, the same 12 on two runs: collection "filters: a family, clearing
  it, and an empty result"; the News dot test; the six match-history and replay tests (a deck's list on hover, a match
  that can't be replayed, the replay's views, stepping, the opponent's hand face up, the replay's end); "the series
  opens the history, the card backs the opponent's decklist"; "hovering your deck shows your decklist"; the two hover
  label tests. Timing tests (playback's "the opponent's card shows, lands, then 'Your turn'") flake when the Python tier
  runs beside them, so the two tiers run one after the other.
- mypy (`--ignore-missing-imports --local-partial-types`) on the twelve modules the Dockerfile compiles: clean.

## What went

| Module | Lines before | Lines after | What went |
|---|---:|---:|---|
| `tools/cards/check.py` | 329 | 305 | `text_section` and the `FIT` path, `shutil`/`subprocess` imports: the text-fit section nothing calls since Martin dropped it on 2026-10-30 (`190e12b9`); `--no-fit` stays, kept on purpose so old command lines run |
| `tools/cards/fit.mjs` | 27 | 0 | the browser measurement only `text_section` ran |
| `sim/rules_ab.py` | 426 | 386 | `run_ab`: `main()` runs both arms itself (with progress and logs) since it was written; nothing else called it |
| `sim/runner.py` | 526 | 517 | `run_spec_pair`, its callers gone with the research harnesses pruned on 2026-09-25 (`bedc9c28`); the unused `import random` |
| `sim/agent_play.py` | 304 | 303 | unused `action_from_dict` import and `gm` local in `board_drawing`; an f-string with no placeholder |
| `sim/replay.py` | 202 | 201 | an `action_from_dict(adict)` whose result nobody read (`rules.apply_logged` parses the same dict) and its import |
| `sim/report.py` | 315 | 313 | `total_matchups`, assigned, never read |
| `sim/transcript.py` | 74 | 73 | unused `effective_strength` import |
| `bots/features.py` | 995 | 990 | `slot_layout`, written with the board_ability features (`89ffee67`, 2026-10-29) and never called |
| `bots/atomic_bot.py` | 565 | 563 | `last_ranking`, set on every ranked turn and never read |
| `bots/referee_bot.py` | 749 | 748 | unused `keep_hand` import (the bot calls its own `_keep_hand`) |
| `bots/raw_position.py` | 323 | 322 | `cards`, a local never read |
| `learn/artifacts.py` | 76 | 55 | `promote_checkpoint`, unused since it was written (`95a3ce08`, 2026-07-17); `build_artifact` plus `.save()` is what callers do |
| `learn/episodes.py` | 189 | 189 | unused `field` import |
| `learn/rawnet.py` | 289 | 288 | unused `sys` import |
| `learn/slotnet.py` | 296 | 295 | `np = _np()` in `split`, never read (its input is already a numpy array) |
| `tools/` (12 scripts) | 1636 | 1631 | pyflakes' unused names: `sys`/`os`/`random` imports in `den_census`, `policy/{extract,baseline,sweep,train}`, `ladder/ladder`, `engine_rs/{fuzz,oracle}`; `feature_oracle` imported `sys` twice; `action_from_dict` in `fuzz` and `puzzles/mine`, `load_bundled_json` in `fuzz`, `end_turn` in `census_replay`, `torch.nn.functional` in `policy/train`; locals `turn_facts` (`den_census`), `n0` and the `ACTION_N` constant (`policy/extract`), an unread `as e` (`blunder_scan`) |
| `web/analyse.py` | 850 | 848 | `REPLY_K` and `DEEP_K`, orphaned when the analysis board moved to the whole-turn search (2026-10-31) |
| `web/match.py` | 804 | 804 | unused `PREMADE_DECKS` import |
| `web/playtest.py` | 247 | 246 | unused `action_from_dict` import |
| `web/static/app.js` | 1836 | 1831 | `artStyle` (unused since the 2026-09-30 menus pass), `yoursChanged` (since the animation timeline, 2026-10-01), `gameNo` (computed, never shown since a match became one game, 2026-09-30), and the `denMouthAt`/`gemAt` imports (coach.js and board.js use them; app.js doesn't) |
| `web/static/chat.js` | 189 | 186 | `refreshChat`, exported since chat landed (2026-10-04) and imported by nothing |
| `web/static/app.css` | 496 | 487 | rules for classes no script or page makes: `.gradart`, `.lbl`, `.btn.primary`, `.chip`, `.dr .ban`, `.grp`, `.lead .lpin` (both rules), the Meta tab's `.mlist`/`.mlh` (gone with one list at a time, 2026-10-26) |
| `web/static/game.css` | 632 | 628 | `.boardbg`, `svg.paths` and `.stone.carved` (the old screen, removed 2026-09-29) and their `--ground`/`--path` properties |
| `web/static/menu.css` | 301 | 298 | `.dsep` and the `.pfr` friend-row rules (the profile became the Ladder, 2026-10-04); `.fr` keeps its rules |
| `web/static/collection.css` | 171 | 166 | `.mosaic` and `.fams` (both gone in the 2026-09-29 collection passes) |

## Found but left

**Parked or kept on purpose**
- `tools/cards/check.py --no-fit`: accepted and ignored, "kept so old command lines still run" (2026-10-30).
- The `lookahead` bot kind (`sim/runner.py`): kept as "a validated negative result / building block", opt-in only.
- `static/sound.js` `CALLS`/`setCalls`: the animal calls are parked (`web/parked_calls/`).
- `static/tokens.css`: eight custom properties nothing reads (`--faint`, `--field`, `--them-deep`, `--them-rgb`,
  `--token-text`, `--you-deep`, `--you-rgb`, `--surface`); it is the design system's token sheet, also read by the tools'
  own pages, so trimming it is a design call, not dead code.

**Bot kinds and spec keys no benchmark or level names** (left: the Rust port builds the same kinds and takes the same
keys, `bots/rust_bot.py` passes them through, and `tools/engine_rs/bot_oracle.py`, which would show the two still agree,
can't run here)
- The `greedy_belief` kind and its `GREEDY_BELIEF_COVERAGE_EXPOSURE` (`sim/runner.py`); the eval term it turns on,
  `coverage_exposure`, is inside the greedy evaluation.
- `RefereeBot(staged=False)`: the unstaged search, its branches through `referee_bot.py`; no spec passes `staged`.
- `RefereeBot(den_far_margin, den_far_ratio)`: no spec passes either, so the den-safety filter always runs on its
  defaults; removing them is a change inside the search.

**Compatibility code whose data I can't see** (each guards something on the live server's volume or in players'
browsers, not in this repo)
- The pre-match Ready step: `Match.ready`, the `prematch` phase, the client's `prematchScreen` and its `{t: 'ready'}`.
  Since 2026-10-01 (`225f3d6a`) a match starts at once, but `Hub.load` reloads every unfinished saved match, so one saved
  in `prematch` before that date would still open there.
- `static/app.js` `OLD_LEVELS` (a pilot level stored in a browser before 2026-10-20), the replay screen's `legacy`
  comparison for replays from before events (2026-10-01), the match history's fallbacks for matches without a mode or a
  cover, and `profiles.py`'s column migrations: all read stored data on live.
- The "log from before the mulligan rule" loop (`web/server.py position_at`, `sim/replay.py`, `tools/den_census.py`
  and other log readers): the two oldest committed games (`web_20260926T085731_CYLPBA`, `web_20260926T092118_W9VS0A`)
  were played before the mulligan landed (2026-09-26 13:09), so the loop is for logs inside the record, not older than
  it. Today neither game builds at HEAD (their deck slugs, `cats_midrange` and the like, are gone), which is a separate
  question.

**Duplication left as it is**
- Rebuilding a logged game's first position (`new_game(lists..., seed, map_id, config=Config.default().for_log(g),
  first_player)`) is written out in 18 places across `web`, `sim`, `learn` and `tools`. The copies agree (none drifted);
  merging them needs a new shared helper, which this pass doesn't add.
- The decided-game guard at the top of each evaluator's `value()` (`greedy_bot.evaluate`, `learned_eval`, `net_eval`,
  `slot_eval`, `raw_eval`: win `inf`, loss `-inf`, draw 0), the hold-out loss report in `learn/net.py` and
  `learn/slotnet.py`, the self-play loop in `learn/episodes.py` and `learn/train.py`, and the log-reading loop in
  `tools/policy/{baseline,extract,raw_extract}.py`: short copies in separate tools, each merge a new shared function.
- `server.profile_view` builds `{id: cards}` from the starters itself where `starter_cards()` does the same: a one-line
  repeat that saves building the starters twice; changing it is taste.
- The bots' method pairs (`_complete_own_turn`, `_rescore_roots` and the rest in `turn_search.py`, `turn_bot.py`,
  `referee_bot.py`) are overrides, not copies, and are inside the search.

**Engine findings (out of scope, both engines must change together)**
- `engine/effects.py:_hand_grant_one`: nothing calls it; the `hand_grant_one` op (`_op_hand_grant_one`) does its own work.
- `engine/strength.py:count_units_controlled`: nothing calls it in Python; `engine_rs/src/strength.rs` mirrors it.
- vulture also flags eleven `Config` fields (`jaguar_max`, `cap_queen_adira`...) as unread: they are read by name
  (`getattr(cfg, ...)` from card data) and checked by `test_card_text_consistency.py`, so they are live.

**Out of scope but noticed**
- `AGENTS.md` still lists "the text fit" among the card sheet's sections; the sheet dropped it on 2026-10-30.
- `greedy_bot.py` imports `enabled_roar_count as _enabled_roar_count` without using it; pyflakes flags it, but
  `turn_search.py` and the tests import it from `greedy_bot`, so it is a re-export and stays.

## Totals

25 files touched (one deleted), 11211 lines before, 11042 after: 169 lines removed, none added beyond this file. Nine
commits, each removing one theme. Tests after every commit: the same 3683 Python passes and 96 web passes as main, the
same failures, mypy clean on the twelve compiled modules; `tools/` and `animal_kingdom/{web,sim,learn}` pyflakes clean
(the `bots/` exception is the re-export noted above).

What the pass shows: the tree was already lean. The dead code was leftovers of rewrites (screens, the analysis board,
the research harnesses), not abandoned features; the duplication that exists is short repeated statements, not drifted
copies.
