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

## Found but left

## Totals
