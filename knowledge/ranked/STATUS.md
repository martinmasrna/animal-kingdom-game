# Ranked leagues: status

Branch `ranked/leagues`. The design is `docs/ranked-leagues.md`; the rules are one file, `animal_kingdom/web/tiers.py`.

## Where it stands

- The rules Martin settled on 2026-11-05 are built: a win gains a star, two from the third win in a row; a loss loses a star and at 0 stars drops a league (never out of league 1); opponents come from your league (a bot from the league's band of ratings, `ladder.bot_in`, or a person waiting in the same league); the top league keeps the rating as its number and matches by it.
- Server: a `tiers` table beside `ladder` in the profiles database, moved in `server.rate_match` for every person in a rated game; `join_ranked` pairs by league (`_meets`) and picks the bot from the league's band, falling back to the nearest bot when a band is empty. `/api/me`, the profile, the leaderboard and a ranked match's seats carry a person's league; the number shows only in the top league.
- Client (text only, the existing styles): home's Ladder piece and Ranked choice, the standing line on the leaderboard tab, the leaderboard rows, the end-of-match line.
- Migration: once at startup, each rated profile into the league its rating stands for (at most 9), 0 stars; under ten rated games, league 1.
- Tests: `animal_kingdom/tests/test_tiers.py` (one per rule, the bands, the bot pick), `test_ladder.py` (the queue: a league-1 bot alone, two people paired, the leagues moved), `web/test/leagues.test.mjs` and `web/test/ranked.test.mjs` (every screen shape, and ranked matches end to end on a real server).
- Simulation: `tools/ranked/simulate.py`, players of fixed strength against the real seeded bots of their league; the table is in the doc.

## Open, Martin's

- Names: open for a session of their own (Martin, 2026-11-05); League 1 to 10 meanwhile. Pictures (a sandbox design job), seasons (none while few play). The doc's "Open calls".
- Play it on staging: a fresh profile's first ranked games in league 1, and his own profile placed by its rating.
