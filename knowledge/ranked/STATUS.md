# Ranked leagues: status

Branch `ranked/leagues`, built overnight 2026-11-04 by a cloud session. The design is `docs/ranked-leagues.md`; the rules are one file, `animal_kingdom/web/tiers.py`.

## Done

- Phase 1, design: `docs/ranked-leagues.md` (the four games, what each mechanic is for, the rules table, Martin's calls, three name sets).
- Phase 2, simulation: `tools/ranked/simulate.py`. The numbers are in the doc. The plain Hearthstone rules let weak players grind to the top (rating-matched opponents keep everyone near 50%); two rating ties fixed it (a win pays double while the rating is ahead of the league, a loss costs double while it is over 100 behind).

## Next

- Phase 3, the mechanics: league state per profile, updated on every rated game with a person in it; tests.
- Phase 4, the client text; phase 5, the migration (designed in the doc).

## Blocked / caveats

- The game logs don't say who played or whether a game was ranked, so the people in the simulation are read off their decks (an inference). `deploy/deploy.sh players` on the Mac, then `.venv/bin/python tools/ranked/simulate.py --players results/players.json`, gives the exact replay.
- Web research came through search summaries only (the session's network policy blocked the wikis and blizzard.com).

## For Martin to look at

- The rules table and "Martin's calls" in `docs/ranked-leagues.md`: names, pictures, whether bots show a league, seasons.
- The Kalista row of the simulation: the one learning player, a week at league 7 while her rating caught up. Is that the right feel?
