# Daily play (async): status

Branch `play/async` from `main`, built overnight 2026-11-04 by a cloud session. The design: [`../../docs/async-play.md`](../../docs/async-play.md). Nothing here is merged or deployed.

## Done

- **Phase 1, design** (`docs/async-play.md`): Chess.com Daily, Words With Friends, Hearthstone/Gwent read and cited; the rules (2 days a turn, timeout loses, challenges wait 7 days, at most 10 daily matches, both-in-at-once plays live, no bots); what home shows; ranked daily designed but not built; six decisions for Martin; what the match code already does.
- From the human game logs: a game is about 9 turns (median 8), and no decision passed to the other player mid-turn in 258 replayable games, so a daily turn is one sitting.

- **Phase 2, server.** `web/match.py`: `Match.daily` (None for a live match), `DAILY_DAYS` = 2, a fresh deadline when the decision comes to someone new (`_daily_update`), `yours(seat)`, `daily_time_out` (whoever had to act loses; both at the mulligan: a draw), saved in `to_dict` with its fixed deadline. `web/server.py`: `GET/POST /api/daily` (home's list; a challenge to a friend, online or not), `POST /api/daily/{id}/answer`, `DELETE /api/daily/{id}`; `DAILY_INVITE_DAYS` = 7, `DAILY_MAX` = 10; `Hub.sweep_daily` every 30 s and at startup (lapses challenges, forfeits turns); `Hub.drop`; both players' tabs told on every change of hands (`{"t": "daily"}` on the presence socket); the socket keeps `match.present` (both in at once) and marks a finished match seen; `/api/current` and a join by code leave daily matches alone; the history records them as mode `daily`. Tests: `animal_kingdom/tests/test_daily.py` (11).

- **Phase 3, client.** `static/daily.js` (home's list, text rows on one granite piece at the top left: your turn, challenges to you with Play and Decline, unseen results, waiting, sent with Withdraw); `static/app.js`: Live or Daily under Friend on home's opponent chooser, the game's clock in days (`1d 4h`), back home with a line once your turn is done and your friend is not in the match, the timeout's words, "Daily · " in the match history; `static/app.css`: the list's look. Web tests: `web/test/daily.test.mjs` (a challenge to a friend who is away, a turn each while the other is away, both in at once playing live, a forfeit on time). The test harness passes `--no-sandbox` to Chrome when run as root.
- **Phase 4, daily ranked** (asked by the supervising session): `POST /api/daily/ranked`, paired with the longest waiting person, a bot at your rating after a day (`DAILY_RANKED_WAIT_DAYS`), at most 3 (`DAILY_RANKED_MAX`), rated by the existing `rate_match`; Ranked then Daily on home; "Looking for a daily opponent" with Leave on home's list. Tests: three more in `test_daily.py` (14 in all), one more in `daily.test.mjs` (4 in all).
- supervisor message received (2026-11-04, relayed through a session named "Evaluation function training methods" for animal-kingdom-74: phases 4 and 5).

## Next

- Phase 5: one run of `npm run test:full`, its counts here.

## Blocked

- Nothing of this work. Two things fail on `main` too, not touched here: `test_deck_docs.py` (3, the deck docs' card tables are stale against `cards.json`; regenerating them is card work) and the hover-label tests in `ui.test.mjs` (2 to 4, in this container's headless Chromium only, it seems). The web tests here run on the preinstalled Chromium (`CHROME=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome`): the Chrome for Testing download is refused by this container's network (403). The venv also needs the `web` extra (`.[dev,web]`), not just `dev`, or the test servers don't start.

## For Martin to look at

Phases 3 and 4 (on `./play` from this branch, two browser profiles, two players who are friends):

- Home with a daily match or two: the list at the top left is a stand-in. It wants a design (where it sits on the key art, how many rows before it scrolls, a "your turn" count on the corner piece?).
- Friend, then Daily, then the challenge; the friend's home; a turn, then back home with the line "Your turn is done. X has 2 days for theirs."
- The game screen's clock in a daily match reads `1d 23h` where the live clock reads `0:30`.
- Ranked, then Daily: whether a bot after a day is right, and decision 3 (no rating change before your first turn).

Phase 2:

- Nothing to see yet: the server has no screen of its own. The forfeit is a loss, always (decision 2 in the doc); a mulligan nobody finished in time is a draw, the one case the doc didn't foresee.

Phase 1:

- The six decisions at the end of `docs/async-play.md`, above all the clock length (1) and what to do about telling a player it's their turn (5).
- Whether "Daily" is the word.
