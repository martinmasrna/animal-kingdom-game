# Daily play (async): status

Branch `play/async` from `main`, built overnight 2026-11-04 by a cloud session. The design: [`../../docs/async-play.md`](../../docs/async-play.md). Nothing here is merged or deployed.

## Done

- **Phase 1, design** (`docs/async-play.md`): Chess.com Daily, Words With Friends, Hearthstone/Gwent read and cited; the rules (2 days a turn, timeout loses, challenges wait 7 days, at most 10 daily matches, both-in-at-once plays live, no bots); what home shows; ranked daily designed but not built; six decisions for Martin; what the match code already does.
- From the human game logs: a game is about 9 turns (median 8), and no decision passed to the other player mid-turn in 258 replayable games, so a daily turn is one sitting.

## Next

- Phase 2, server: the daily match, its clock and forfeit, the home list, the daily friend challenge; tests in `animal_kingdom/tests/`.
- Phase 3, client and web tests.

## Blocked

- Nothing. The web tests here run on the preinstalled Chromium (`CHROME=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome`): the Chrome for Testing download is refused by this container's network (403). The venv also needs the `web` extra (`.[dev,web]`), not just `dev`, or the test servers don't start.

## For Martin to look at (phase 1)

- The six decisions at the end of `docs/async-play.md`, above all the clock length (1) and what to do about telling a player it's their turn (5).
- Whether "Daily" is the word.
