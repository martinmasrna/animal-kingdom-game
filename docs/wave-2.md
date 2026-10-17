# Wave 2: the Discord group

The plan of record for the two weeks to 31 October 2026, settled with Martin on 17 October. The goal: a link posted in a Discord of friends, many of them Magic players, that a stranger opens alone, learns from, and keeps coming back to for their own reasons, not as a favour. No alpha night. All twelve decks and every card go out. Art is good enough; placeholder legendary names ship if they must, said upfront.

## What the first launch taught

Three people played from 1 October, all close to Martin: 1,257 games, 72% of them in the first five days, then a cliff. Laras (a card gamer) beat Expert 81% and stopped after six days. Kalista (not a card gamer) lost three of four on day one, Easy included, beat Expert more often than not by day twelve, and tapered out by day sixteen. Nobody cold has ever played a game: the one stranger (5 October) clicked home, Settings, home, and left after 88 seconds. Details: `deploy/deploy.sh players` and the 17 October read in this session's history.

The reading, Martin's and Claude's together: the game holds people (hundreds of games each), the pool was small (fixed), and once the bot is beaten and nobody else is online the reason to return is gone. The bots are the 80 of retention. The phone is the unknown of the bounce: a Discord link opens in the Discord app's own browser on a phone, and both of Laras's first messages were "can't read my cards on mobile".

The cold walkthrough of 17 October (a Sonnet agent on a test server; screenshots in that session's scratchpad) found no crash and no console error, and the friction listed under step 3.

## Rules for the two weeks

- Bot difficulty comes from real strength only. No handicaps, no extra cards or food, no cheats of any kind (Martin: "a lazy solution, garbage user experience").
- The yardstick for the top bot is Martin's own win rate against it in his games, at or under 55%. Bot-vs-bot numbers rank candidates, never decide.
- Bug fixes deploy once the fast tiers pass. Anything that changes how the game feels waits for Martin.
- Out of scope until the wave is out: art, best-of-3, simulated balance tuning, async play, self-play bots. Async play (take your turn when you visit) is the likely milestone after.

## The steps, in order

### 1. Blind spots (days 1 to 3)

- The phone path as a Discord user meets it: the link opened from the Discord app on iOS and Android, including Sign in with Google and Discord inside that browser (Google refuses embedded webviews; the fix is to open sign-in in the system browser). Fix what breaks. Known from the walkthrough: collection filters truncate at phone width, the game's top buttons cover the opponent's hand.
- Verify each of the ten feedback messages from Laras and Kalista against the current client: cards unreadable on phone (hand and collection), a bot that never moved, no indicator while a card effect has you choosing a discard, Defeat harsher than Victory, no browsing while a match search runs, the practice settings forgetting the chosen bot, the leaderboard's bot rating disagreeing with the pre-game one, clicks on cards doing nothing while the rest responds. Fix what still stands.
- Event logging for the funnel: lesson started and finished, left the tab mid-game, session length, first ranked game. Without it the wave teaches nothing about where people drop.
- Feedback and notable events to a Discord webhook: feedback messages into a channel, "X is in the ranked queue" and "X beat Expert with Giants" into another. The channel is the lobby; it is where the people already are.
- Small defects from the walkthrough: the replay toolbar overlapping itself, the End turn tooltip saying "Your opponent's turn" on your own turn, Settings opening on sound-credit URLs, the defeat overlay saying nothing on a den capture.

### 2. The climb (days 3 to 7)

- Measure first: thinking time per move for each web level and deck (walkthrough: bot turns took 6 to 12 s, Easy included; split pacing, animation and search before changing any of it).
- Search budget A/B in the background: the web Expert with a node cap of 10x and 25x today's 80 and quiescence on, against today's Expert, paired seeds, both seats, 200+ games a matchup. Ship the winner as the web Expert if it is clearly stronger and stays under the 15 s move limit.
- Easy loses to a day-one player: the walkthrough's naive script lost four in a row to Easy, Kalista 16 of 34. Weaken Easy on purpose (a worse evaluator or deliberate suboptimal picks, never a cheat in the player's favour either) and check it against the recorded day-one games.
- A newcomer's first ranked games sit against Easy or Normal regardless of the Glicko start (the walkthrough's first ranked game was Expert at 1689 against a fresh 1500; Kalista's first game was Expert too). Waiting on Martin: the exact rule; Claude's default is the first five ranked games capped at Normal. Also waiting: a warning in the concede dialog when the concede costs rating (a turn-5 concede cost 215 points).
- Ladder bots play the lists the deck optimizer finds strongest for a bot, not the human-tuned starters.
- Target-aware removal in the hand eval and the features, round 4 of the value net, proved on current cards (scoped in `bots.md`). Per-deck evaluation for ladder bots is allowed: each ladder bot is one deck at one level (Martin, 17 October; the generalist invariant in CLAUDE.md stays for the search bots that play any deck).
- Re-seed the ladder's bot ratings when a new Expert ships (`sim/ladder_seed.py`).
- At the end of the week: the cold pilot. The link to two or three people from the Discord, asked only to play and say where they got stuck. One cold data point exists today; three more a week early beat any amount of guessing.

### 3. First hours (days 7 to 11)

- The tutorial teaches den defence before it hands the player to a real bot, and the lesson lines the walkthrough tripped on are fixed: "the circles show" when none are visible; "click one of your animals" meaning a hand card; the tutorial Lynx's text differing from the real Lynx; home defaulting to Normal after the tutorial's Easy match.
- A one-page How to play in the game's own words, reachable from the How to play entry beside the lessons: the turn, connection, regions and food, cover, remove (a Magic player reads destroy or exile), adjacent (road-adjacent), strength 0, +N is permanent unless it says next turn, the first player's one-action opening, and the keywords.
- Keyword lines redlined by Martin (players learn the rules from them; the Roam line is 60 words).
- Why a card is greyed in hand (Apex with nothing to eat, Hungry without the food) said on hover, and a hint that right-click reads a card large.
- News shown only to a returning player; a newcomer's red dot points nowhere.
- Placeholder names: fifteen sit beside a real card of the same name ([RAVEN] and Raven, [TUNA] and Tuna, [BOAR] and Boar) and read as duplicates. Waiting on Martin: name those fifteen first through the `naming` skill, or show a working name without brackets.

### 4. Goals and shareable things (days 9 to 13)

- Achievements designed as directed playtesting: win with each of the twelve decks, beat Expert with each, win on food, win by den, each keyword used once; later daily quests that rotate decks ("win 2 with Giants"). Coverage of the pool as test data, disguised as goals. Needs the event log from step 1.
- A replay link and a deck link anyone can open (`#/replay/<match>` for others, `#/deck/<code>` importing into the collection). Replays and deck codes exist; this is routing and a share button.
- Puzzles: "take the den this turn" positions generated from the logged human games where a win was available within two actions, played on the tutorial's fixed-state machinery, one a day. Magic players love puzzles, a puzzle teaches depth alone, and a daily one is a return hook that needs no other human online. Built if steps 1 to 3 hold.

### 5. Names and the post (days 12 to 14)

- Names in one or two sittings through the `naming` skill, the colliding fifteen first.
- The Discord post, written honestly: an alpha, what is placeholder, what to try first, where feedback goes, that every game is recorded.

## Waiting on Martin

- The first-ranked-games rule and the concede warning (step 2).
- The fifteen colliding placeholder names: name or unbracket (step 3).
- The keyword and How to play lines (step 3), as a redline.
- Who gets the pilot link, and when in the week (step 2).
