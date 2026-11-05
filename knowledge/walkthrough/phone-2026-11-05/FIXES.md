# Phone walkthrough: fixes

Branch `fix/phone-glitches`, from `main` at 70dc14e. Finding numbers are those of `report.md`, which is on the branch `report/phone-walkthrough`. Each fix is its own commit, with a before and an after screenshot at 390x844 (scale 3) in this folder: `fix-fNN-<screen>-before.jpg` and `-after.jpg`. The before shots come from `main`, the after shots from this branch, on the same emulated iPhone.

Tests: `npm test` in `animal_kingdom/web/test`, run through a wrapper that adds `--no-sandbox` to the preinstalled Chromium (this container runs as root, and without the flag no test browser starts). `main` gives 96 pass and 12 fail out of 108, the same 12 failures every time: collection filters (19), news (38), match history and replay (48 to 53), the in-game history and hover labels (98, 99, 106, 107). The results for this branch are at the end.

| # | Finding | State | What changed |
|---|---|---|---|
| 4 | Opponent chooser: "Intermediate" cut and covered by "Advanced" | fixed | `app.css`: on screens up to 480 px wide, the five bot buttons size to their names at 15 px (they were five equal 64 px boxes at 16 px). Measured at 360, 390 and 412 px wide: every name fits its button, and the narrowest button (Expert) is 44 px wide. Shots: `fix-f04-levels-*`. |
| 5 | Coach bubble covers the animal it asks you to tap (Polar Bear, open den) | fixed | `coach.js`, upright only. A bubble above or below a group of circles now stands 80/100 stage px from the circles' centres, not 62, clear of the animal and its strength badge. A move onto the opponent's den puts the bubble over the hand, not over the animals at the den. Measured in a full play-through: the circled Buffalo and the den's row are no longer covered. The bubble now covers part of your own Lion under the Buffalo instead (4,2 at 50%); that Lion is not what the line asks you to tap. Shots: `fix-f05-apex-*`, `fix-f05-den-*`. |
| 6 | Mamba line says "5 or less", the card says 6 | fixed | `tutorial.js`: the line takes the number from the card's own text ("strength 6 or less"), so it follows any later change to the card. Shots: `fix-f06-mambainfo-*`. |
| 7 | "The circles show..." when no circles are on the board | fixed | `tutorial.js`: the line now shows once you have picked a card, when its circles are on the board, and it stands beside them. Next, or tapping a circle, moves on. Measured: 2 ringed circles on screen when the line shows (0 before). The lesson's words are unchanged. Shots: `fix-f07-free-*`. |
| 13 | Replay: Leave off the bottom, controls 35 px | fixed | `game.css`, upright only: the controls are 74 stage px (40 px on a 390 px phone), set in two rows (the step buttons and the eye; then Play from here, the track and Leave). Measured: every control is 40x40 or larger, and Leave ends at 823 px of 844 (it ended at 854). The track is narrower: 75 px, from 103. Shots: `fix-f13-replay-*`. |
| 15 | Other coach bubbles covering pieces (opponent's food, "The number on a card...", "Press and hold any card") | left | No place for the bubble keeps its pointer and clears the animals. Upright, the bubble is 400 of the stage's 720 px wide, and a talk bubble with its Next button is about 190 px tall. Between the opponent's food gem and the top row of animals there are about 100 px, and between your front row and the hand about 160 px. Moving the bubble into the middle of the board would clear the animals, but it would stop pointing at the gem or the card its line is about. Doing this needs a smaller bubble, shorter lines, or a change to where the board sits: those are design calls for Martin. Shots `fix-f15-*-before` and `-after` show these steps unchanged. |
| 16 | Home set to Advanced after the tutorial | fixed | `app.js`: the Practice opponent for anyone without a saved choice is Beginner, not Advanced. A saved choice is kept as it was. Shots: `fix-f16-home-*`. |
| 19 | History says "Bot (Easy)" where the player picked Beginner | fixed | `server.py`: the history names a bot by the band its seat was shown under ("Beginner Bot", "Fish (Expert Bot)" give Beginner and Expert). A seat named otherwise falls back to its pilot's band. The "Bot (" prefix stays, because ranked's recent-deck check reads it. Earlier rows in the database keep their old words. Shots: `fix-f19-history-*`. |
| 20 | Defeat says nothing on a food loss | fixed | `app.js`: a game won or lost on food says who reached the food ("Your opponent reached 100 food."), as the lessons' Victory does. A den taken still shows no line: that is Martin's call of 2026-10-17, and it is unchanged. Shots: `fix-f20-defeat-food-*`, made from the lab view fed as a finished game lost on food. |
| 22 | Match end buttons 39 px | fixed | `game.css`, upright: 50 stage px, 41 px on the phone. Shots: `fix-f22-end-*`. |
| 23 | 145 wider than its gem | fixed | `game.css`: a count of three digits is drawn at 26 px, not 34 (28 px wide in a 46 px gem on the phone; it was 38). Shots: `fix-f23-gem-*` (the lab view with 145 and 112), and `fix-f23-l1-end-*` (the lesson 1 end). |
| 24 | Sound slider 8 px tall | fixed | `app.css`: the slider is 40 px tall, and its groove is still drawn 8 px. Shots: `fix-f24-settings-*`. |
| 25 | Friends close 36 px | fixed | `menu.css`: 40x40. Shots: `fix-f25-friends-*`. |

Out of scope, left for Martin as asked: 1, 2, 3, 8, 9, 10, 11, 12, 14, 17, 18, 21.

In scope: 13 findings. Fixed: 12 (4, 5, 6, 7, 13, 16, 19, 20, 22, 23, 24, 25). Left: 1 (15).

## Tests on this branch

- `npm test` after fixes 4 to 7, and again after all of them: 96 pass and 12 fail out of 108. These are the same 12 tests that fail on `main` in this container, with no new failure.
- Python fast tier (`pytest -m 'not slow'`): 3 fail, 3683 pass. The 3 failures are the same on `main`: `test_deck_docs` for aristocrats, egg_control and hoofed (the deck docs' card tables are behind `cards.json`). One test, `test_profiles.py`, pinned the old "Bot (Easy)" history label. It now expects "Bot (Beginner)" (its own commit, after fix 19).
- Each fix was checked on a 390x844 emulated iPhone by the measurements above. A full tap-through of both lessons on this branch ran without errors.
- `tutorial.slow.mjs` and the other slow web tests were not run.
