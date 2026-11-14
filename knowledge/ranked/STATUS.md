# Ranked leagues: status

On `main`. The design is `docs/ranked-leagues.md`; the rules are one file, `animal_kingdom/web/tiers.py`.

## Where it stands

- The rules: ten leagues named by material (Wood to Diamond) and a top league (placeholder name Legend); three stages a league, five wins a stage; a win gains one, two from the third win in a row; a loss loses one and with none left drops a stage, then a league (never out of Wood 1); opponents come from your league (a bot from the league's band of ratings, `ladder.bot_in`, or a person waiting in the same league); the top league keeps the rating as its number and matches by it. `STAGES`, `WINS` and the `LEAGUES` table in `tiers.py` are the whole shape.
- Server: a `tiers` table beside `ladder` in the profiles database (league, and the wins inside it as `stars`, 0 to 14), moved in `server.rate_match` for every person in a rated game; `join_ranked` pairs by league (`_meets`) and picks the bot from the league's band, falling back to the nearest bot when a band is empty. `/api/me`, the profile, the leaderboard and a ranked match's seats carry a person's league; the number shows only in the top league.
- Client, a placeholder look Martin accepted as one (2026-11-13): thirty painted shields, a league's material with its division carved in (`static/kit2/league/<league>_<division>.webp`, `lgDisc` in `app.js`), and five pips for the wins (`lgPips`). The emblem stands without words on home's Ladder piece, the leaderboard rows (no pips there) and the end of a match; the league's name is written only on the standing line. A league's stages show as divisions 3, 2, 1, the last the best (`tiers.division`).
- Migration: standings from the first build (numbered leagues with 3 or 5 stars) are converted once at startup (`Tiers._to_stages`).
- Tests: `animal_kingdom/tests/test_tiers.py` (one per rule, the bands, the bot pick, the conversion), `test_ladder.py` (the queue), `web/test/leagues.test.mjs` and `web/test/ranked.test.mjs` (every screen shape, and ranked matches end to end on a real server).
- Simulation: `tools/ranked/simulate.py`; the table is in the doc.
- Not deployed: live still runs the first build.

## Open, Martin's

- Pictures: parked on 2026-11-13 with the placeholder in place; the design work and how to run it are in `~/Work/fun/league-fresh/README.md`.
- The top league's name; seasons (none while few play). The doc's "Open calls".
- Deploying it: the conversion of live standings runs once on the first start.
