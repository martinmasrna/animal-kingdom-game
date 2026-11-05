# Share links: status

Branch `share/links` from `main`. Task: wave-2 step 4, a replay link and a deck link anyone can open. Decisions and Martin's decision points: `docs/share-links.md`.

- Built: replay share tokens (`profiles.shares`, `POST /api/replay/<match>/share`, `GET /api/replay/<token>` open to anyone). `#/replay/<token>` read-only for visitors (no Play from here; Home instead of Leave). `#/deck/<code>?n=<name>` shows the list and imports it in one tap. Share is a text action on each match-history row and on an open deck in the collection.
- Tests: `animal_kingdom/tests/test_profiles.py::test_a_shared_replay_opens_for_anyone_with_its_link`; `animal_kingdom/web/test/share.test.mjs` (a fresh browser context for each link, a bad replay link, a bad deck link, both Share actions).
- The test harness passes `--no-sandbox` to Chrome when it runs as root (cloud containers).
- Not done: a link preview in chat apps; revoking a link (both are decision points in the doc).
