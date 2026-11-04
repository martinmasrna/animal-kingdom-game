# Daily play (async): status

Branch `play/async` from `main`, built overnight 2026-11-04 by a cloud session. The design: [`../../docs/async-play.md`](../../docs/async-play.md). Nothing here is merged or deployed.

## Done

- **Phase 1, design** (`docs/async-play.md`): Chess.com Daily, Words With Friends, Hearthstone/Gwent read and cited; the rules (2 days a turn, timeout loses, challenges wait 7 days, at most 10 daily matches, both-in-at-once plays live, no bots); what home shows; ranked daily designed but not built; six decisions for Martin; what the match code already does.
- From the human game logs: a game is about 9 turns (median 8), and no decision passed to the other player mid-turn in 258 replayable games, so a daily turn is one sitting.

- **Phase 2, server.** `web/match.py`: `Match.daily` (None for a live match), `DAILY_DAYS` = 2, a fresh deadline when the decision comes to someone new (`_daily_update`), `yours(seat)`, `daily_time_out` (whoever had to act loses; both at the mulligan: a draw), saved in `to_dict` with its fixed deadline. `web/server.py`: `GET/POST /api/daily` (home's list; a challenge to a friend, online or not), `POST /api/daily/{id}/answer`, `DELETE /api/daily/{id}`; `DAILY_INVITE_DAYS` = 7, `DAILY_MAX` = 10; `Hub.sweep_daily` every 30 s and at startup (lapses challenges, forfeits turns); `Hub.drop`; both players' tabs told on every change of hands (`{"t": "daily"}` on the presence socket); the socket keeps `match.present` (both in at once) and marks a finished match seen; `/api/current` and a join by code leave daily matches alone; the history records them as mode `daily`. Tests: `animal_kingdom/tests/test_daily.py` (11).

## Next

- Phase 3, client and web tests.

## Blocked

- Nothing. The web tests here run on the preinstalled Chromium (`CHROME=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome`): the Chrome for Testing download is refused by this container's network (403). The venv also needs the `web` extra (`.[dev,web]`), not just `dev`, or the test servers don't start.

## For Martin to look at

Phase 2:

- Nothing to see yet: the server has no screen of its own. The forfeit is a loss, always (decision 2 in the doc); a mulligan nobody finished in time is a draw, the one case the doc didn't foresee.

Phase 1:

- The six decisions at the end of `docs/async-play.md`, above all the clock length (1) and what to do about telling a player it's their turn (5).
- Whether "Daily" is the word.
