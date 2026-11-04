# Phone walkthrough, 2026-11-05: status

Done. report.md has 25 findings and the list of screens that were fine; screenshots are beside it.

- Setup: venv and npm done. The Chrome for Testing download was blocked by the proxy; the preinstalled Chromium was used instead, with --no-sandbox. Private server from main (70dc14e), game logs in a scratch folder.
- Covered on iPhone (390x844) and Android (412x915): home, both lessons, Practice vs Beginner to the end, collection (filters, search, card, deck sheet, new deck), ladder (leaderboard, history, meta), replay, Friends, Settings, News, Feedback, sideways (match, collection, home).
- Console and page errors: none recorded (the recorder was checked with a deliberate error).
- Not covered: Sign in with Google/Discord (no sign-in keys on the test server; emulated browser, not a chat app's in-app browser).
