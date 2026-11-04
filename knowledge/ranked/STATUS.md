# Ranked leagues: status

supervisor message received

Branch `ranked/leagues`, built overnight 2026-11-04 by a cloud session. The design is `docs/ranked-leagues.md`; the rules are one file, `animal_kingdom/web/tiers.py`.

## Done

- Phase 1, design: `docs/ranked-leagues.md` (the four games, what each mechanic is for, the rules table, Martin's calls, three name sets).
- Phase 2, simulation: `tools/ranked/simulate.py`. The numbers are in the doc. The plain Hearthstone rules let weak players grind to the top (rating-matched opponents keep everyone near 50%); two rating ties fixed it (a win pays double while the rating is ahead of the league, a loss costs double while it is over 100 behind).

- Phase 3, the mechanics: a `tiers` table beside `ladder` in the profiles database (`web/tiers.py` `Tiers`), moved in `server.rate_match` for every person in a rated game, read off their rating going in. Matchmaking and bot ratings untouched. `/api/me` and the profile carry `league`; the leaderboard lists a person from their first rated game, with their league and no number below the top league (before, a person still placing was left off); a ranked match's seats carry a person's league and their rating only in the top league; the match view at the end carries the one line. The migration runs once at startup (marked in `ladder_meta`). Tests: `animal_kingdom/tests/test_tiers.py` (one per rule) and `test_ladder.py` updated to the new screens. Fast tier: 3707 passed; 3 fail in `test_deck_docs.py`, which fail on `main` too (the deck docs are stale against cards.json; regenerate with `.venv/bin/python -m animal_kingdom.render.deck_docs`, left alone here as not this branch's).

- Phase 4, the client (text only, the existing styles): the ladder screen's leaderboard tab opens with your standing in one line ("League 5 · 2 of 5 stars · never below League 4 · 3 wins in a row"; the top league "League 10 · 2011"); home's Ladder piece says your league and place; the Ranked choice on home says your league instead of "your rating"; a person's leaderboard row has the league in the number's place and the stars beside the name (the top league: the rating as the number, "League 10" by the name); bots' rows as before; the end of a ranked match says the one line and shows the rating counter only in the top league (with the line on the game that brought you there). A person below the top league shows no gem at the versus moment (no number to show). Web tests: `animal_kingdom/web/test/leagues.test.mjs` (5: every screen shape, on patched answers).
- Phase 5, the migration (`Tiers.migrate`, run once at startup): two leagues under the league the rating stands for, at that league's checkpoint, never above league 8; under ten rated games, league 1. Why and examples in the doc's "Migration"; the News entry is a draft paragraph at the end of the doc, not shipped.

- Phase 6, hardening (asked by a session named "Evaluation function training methods", relaying for animal-kingdom-74):
  - Both fast suites green, 2026-11-05: Python `pytest -q -m 'not slow'` 3710 passed, 2 skipped, 18 xfailed; web `npm test` 115 of 115.
  - What was red and why: the 3 `test_deck_docs.py` failures (stale deck tables; regenerated with `render.deck_docs`, the docs only, cards.json untouched) and 12 web tests that also failed on `main` here, because of this container, not the code: its Chromium reported no mouse (`hover: none`), so the client behaved as on a phone, and the `sqlite3` tool was missing. Fixed outside the repo (Chromium started with `--blink-settings` declaring a mouse; `apt-get install sqlite3`), so nothing in the repo changed for them.
  - `animal_kingdom/web/test/ranked.test.mjs`, end to end on a real server: a ranked match against a bot, conceded, whose end says "No star lost (no stars lost in leagues 1 to 3): League 1, 0 of 3 stars" with no number; a ranked match between two people whose winner's end says "+2 stars (rating bonus): League 1, 2 of 3 stars"; the leaderboard listing the winner with "League 1" and "2 of 3 stars", the bots with their numbers. Stable over four runs.
  - The doc: the three name sets (each with its sentence on the feel), the by-day table for Martin, Laras and Kalista under the recommended rules, and a new section "What a player sees, screen by screen".

## Next

- Martin's calls (the doc's "Martin's calls"): names, pictures, bots and leagues, seasons. Then a deploy to staging for him to play, never live first.

## Blocked / caveats

- The game logs don't say who played or whether a game was ranked, so the people in the simulation are read off their decks (an inference). `deploy/deploy.sh players` on the Mac, then `.venv/bin/python tools/ranked/simulate.py --players results/players.json`, gives the exact replay.
- Web research came through search summaries only (the session's network policy blocked the wikis and blizzard.com).

## For Martin to look at

- Where pictures belong (left as text, for a design in the sandbox): beside the league's name on the ladder screen's standing line; in the person's leaderboard row in place of the league's name; at the end of a ranked match above the line (a league's badge, and a moving-up moment when you move up); and the versus moment, where a person below the top league now shows nothing in the gem's place (the gem held their rating). Today's screens: the standing line and the rows on the ladder screen, and the end line (screenshots in the session's scratchpad, not committed).
- On staging, once deployed: a few ranked games from a fresh profile (league 1 to 4 in about ten games), and his own profile, which the migration puts two leagues under his rating.

- After phase 3: nothing on screen yet. The behaviour change to judge: people still placing now show on the leaderboard (in league 1 and up) instead of being hidden until ten games.

- The rules table and "Martin's calls" in `docs/ranked-leagues.md`: names, pictures, whether bots show a league, seasons.
- The Kalista row of the simulation: the one learning player, a week at league 7 while her rating caught up. Is that the right feel?
