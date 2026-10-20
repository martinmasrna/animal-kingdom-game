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
- The ten feedback messages from Laras and Kalista, verified 17 October against the current client: browsing during a ranked search, the practice settings, the leaderboard's bot rating and the discard prompt were fixed on 1 to 4 October. Still standing and fixed now: a bot whose move the match refused died silently (only conceding got the player out; it now plays a fallback and a dying task is logged), a move dropped while the socket is down said nothing (a toast now), the portrait discard prompt ran under the icon row. Still standing, waiting on Martin: hold-to-read on a phone is told only by the tutorial (a player who skipped it never learns it, in the hand or the collection); with a deck open in the collection a tap adds or removes a card, which is how Laras's accidental edits happened; a hand card pressed while a new view lands loses the click (the hand is rebuilt on every view). Defeat versus Victory: the sounds are equally loud (a lion's roar, a wolf's howl, both 2.3 to 2.5 s at -19 LUFS); the difference is the overlay, Defeat greys and darkens the board to 60% over 1.4 s, Victory leaves it lit; a taste call.
- The funnel read. The events exist already (`web/events.py`: Learn to play clicked or skipped, each coach step reached, each lesson's start and end, left the tab mid-game, screens, hidden and shown); `tools/funnel.py` turns `deploy/deploy.sh players` into one row per newcomer and the stage counts (came, Learn to play, lesson 1, lesson 2, first match, first win, ranked, came back, a week later). Run it daily during the wave.
- Discord webhooks (`web/discord.py`, built 17 October, dormant): with friends in one server, people talk in the channel directly and the in-game feedback box already mails the match and the board; a feedback or events channel adds little. Not part of the wave (Martin, 2026-10-17). The code stays for a larger audience; it posts nothing without its secrets.
- Small defects from the walkthrough: the replay toolbar overlapping itself (fixed), the End turn tooltip saying "Your opponent's turn" on your own turn (fixed), the News dot for a newcomer (fixed). The defeat overlay says nothing on a den capture on purpose: the animal flies in and the den crashes down (Martin, 2026-10-17, reaffirmed). Bot turns measured: about 7 s for an Easy turn of two actions, of which thinking is nothing, server pacing about 1 s, and the client's animations the rest (the second action's income flights and the 1.5 s Your turn plate); a taste call whether to shorten any of it.

### 2. The climb (days 3 to 7)

The bots are opponents, not balance instruments (Martin, 2026-10-17; `bots.md` opens with it). The measure is the ladder rating against people per bot and deck; baseline 17 October: Expert Cats 1921, Martin and Kalista 1870 (beating the Expert three in four), Laras 2367; goal: the best pairing near 2100.

- Depth first. The search never imagines its own next turn; at the leaf, after the opponent's reply, it now plays its own next turn and their reply with the fast policy and scores after, a second turn of sight at about twice the cost. Acceptance: a Zebra puzzle (the legendary played on turn one for one card), the Taipan puzzle, an A/B against today's Expert at ten games, the time per move under the 15 s limit, then it ships as the web Expert and the ladder is re-seeded.
- Then decks that suit a bot (the ladder bots play the lists a bot wins most with, not the human-tuned starters) and per-deck evaluation for ladder bots, each measured against the baseline.
- The target-aware evaluator candidate (the Taipan fix) ships when its paired run passes; it is cheap and orthogonal.
- Easy for a day-one player: done (Practice Easy on Random and the tutorial's first match draw from Colony, Hoofed or Giants; the queue picks by per-deck rating).
- Re-seed the ladder's bot ratings whenever a new Expert ships (`sim/ladder_seed.py`).
- At the end of the week: the cold pilot. The link to two or three people from the Discord, asked only to play and say where they got stuck.

### 3. First hours (days 7 to 11)

- The tutorial teaches den defence before it hands the player to a real bot, and the lesson lines the walkthrough tripped on are fixed: "the circles show" when none are visible; "click one of your animals" meaning a hand card; the tutorial Lynx's text differing from the real Lynx; home defaulting to Normal after the tutorial's Easy match.
- No How to play page: nobody learns a game from text, the tutorial teaches (Martin, 2026-10-17). The words the walkthrough called unexplained (remove, adjacent, connected) are taught by the lessons (the Mamba frees the Squirrel; the chain from the den), and sit on 60 to 71 cards each, so no term line for them: it would caption a quarter of the pool.
- Keyword lines redlined by Martin (players learn the rules from them; the Roam line is 60 words).
- Why a card is greyed in hand (Apex with nothing to eat, Hungry without the food) said on hover, and a hint that right-click reads a card large.
- News shown only to a returning player; a newcomer's red dot points nowhere.
- Placeholder names ship in brackets as they are, the fifteen beside a same-named card included (Martin, 2026-10-17: dropped); names come through the `naming` skill at its own pace.

### 4. Goals and shareable things (days 9 to 13)

- The five bots (Martin, 2026-10-20; shipped the same evening, `web/ladder.py` `RUNGS`, `server.pilot_for`): one vocabulary everywhere. Beginner, Intermediate from 1300, Advanced from 1500, Expert from 1700, Legendary from 1900 are bands over the rating scale. A ranked bot is named by the band its own rating sits in ("Fish (Expert Bot)"), the leaderboard lists the bots one row per band, and Practice offers the same five: the player picks a bot and a deck, the server hands out the pilot whose rating with that deck sits nearest the band. Easy, Normal and Expert are the engine's three pilots and no longer words a player sees. A person's row shows the rating alone (a band word beside a rating is noise, Martin). Matchmaking is untouched: every bot's deck keeps its own rating and the nearest plays.
- Achievements designed as directed playtesting: win with each of the twelve decks, beat Expert with each, win on food, win by den, each keyword used once; later daily quests that rotate decks ("win 2 with Giants"). Coverage of the pool as test data, disguised as goals. Needs the event log from step 1.
- A replay link and a deck link anyone can open (`#/replay/<match>` for others, `#/deck/<code>` importing into the collection). Replays and deck codes exist; this is routing and a share button.
- Puzzles: "take the den this turn" positions generated from the logged human games where a win was available within two actions, played on the tutorial's fixed-state machinery, one a day. Magic players love puzzles, a puzzle teaches depth alone, and a daily one is a return hook that needs no other human online. Built if steps 1 to 3 hold.

### 5. Names and the post (days 12 to 14)

- Names in one or two sittings through the `naming` skill, the colliding fifteen first.
- The Discord post, written honestly: an alpha, what is placeholder, what to try first, where feedback goes, that every game is recorded.

## Waiting on Martin

- The keyword lines (step 3), as a redline, when he wants to.
- Who gets the pilot link, and when in the week (step 2).
- The phone path from the Discord app (step 1), a two-minute check on his phone.
