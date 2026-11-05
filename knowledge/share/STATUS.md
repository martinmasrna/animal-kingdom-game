# Share links: status

Branch `share/links` from `main`. Task: wave-2 step 4, a replay link and a deck link anyone can open. Decisions and Martin's decision points: `docs/share-links.md`.

- Built: replay share tokens (`profiles.shares`, `POST /api/replay/<match>/share`, `GET /api/replay/<token>` open to anyone). `#/replay/<token>` read-only for visitors (no Play from here; Home instead of Leave). `#/deck/<code>?n=<name>` shows the list and imports it in one tap. Share is a text action on each match-history row and on an open deck in the collection.
- Tests: `animal_kingdom/tests/test_profiles.py::test_a_shared_replay_opens_for_anyone_with_its_link`; `animal_kingdom/web/test/share.test.mjs` (a fresh browser context for each link, a bad replay link, a bad deck link, both Share actions).
- The test harness passes `--no-sandbox` to Chrome when it runs as root (cloud containers).
- Not done: a link preview in chat apps; revoking a link (both are decision points in the doc).

## Test state (2026-11-05, cloud container, Chromium 1243 headless)

- New tests pass: the share test in `test_profiles.py` and all 5 of `share.test.mjs`.
- `./test` is not green, but the failures are the same on `main` in the same container, so this branch adds none:
  - Python: 3 failures in `test_deck_docs.py` (aristocrats, egg_control, hoofed): the deck docs' card tables are out of date with `cards.json`. Regenerating them (`python -m animal_kingdom.render.deck_docs`) is a card-side change, left alone here.
  - Web: 13 failures, all in hover, replay-history or news tests (`collection`, `news`, `replay`, `ui`). Run with `AK_PYTHON` on a clean `main` worktree, the same 13 fail. Probably this headless Chromium build, not the code: worth a run on Martin's Mac before merging.
