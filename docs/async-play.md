# Daily play: take your turn when you visit

A design for asynchronous play, written 2026-11-04 overnight on the branch `play/async` (not merged). Status of the build: [`../knowledge/async/STATUS.md`](../knowledge/async/STATUS.md). wave-2.md put async play out of scope for wave 2 and named it "the likely milestone after"; this is that milestone, designed and built on a branch so Martin can decide on it without anything reaching live.

**The idea.** A match between two friends that does not need both of them online. It waits for days. Home lists the matches where it is your turn. You open one, the game screen is the game screen you know, you take your turn, and you are back home. Each turn has a clock of days, not seconds; if it runs out, you lose. When both players happen to be in the match at once, it plays like a live match: moves land at once, with the same animations.

The word players see is **Daily**, as on Chess.com: "Daily challenge", "Daily · " in the match history. It says how often you are expected to come back, which "async" does not.

## How others do it

- **Chess.com Daily.** The clock is per move, not per game: 1 to 14 days a move, 3 days by default ([What is Daily Chess](https://support.chess.com/article/361-what-is-daily-chess), [Daily settings](https://support.chess.com/article/1999-daily-chess-settings)). Running out of time loses the game. Vacation pauses all of your Daily games at once, never one; any move ends it; a new account gets 7 days and more accrues twice a month ([Vacation](https://support.chess.com/article/624-how-does-vacation-work-how-much-time-do-i-get)). Premium members get "auto-timeout protection", vacation switched on for them before a timeout. A game that ends before the fourth move, by timeout or resignation, is not rated. Daily has its own rating, apart from the live ones.
- **Words With Friends.** No visible clock at all: a game simply auto-resigns after 6 days without a move against a random opponent, 11 days against anyone else ([Zynga support](https://zyngasupport.helpshift.com/hc/en/21-words-with-friends/faq/1844-what-do-i-do-with-corrupted-games/); the support page is older and I found no newer figure). The game list (whose turn, how long since the last move) is the whole interface; the push notification "it's your turn" is what brings people back.
- **Hearthstone and Gwent** have no asynchronous mode. Hearthstone's turn is 75 seconds (90 in the alpha), with extra time added for server lag, and a player who let a turn run out gets a much shorter fuse next turn ([Hearthstone wiki, Turn](https://hearthstone.wiki.gg/wiki/Turn)). I found no statement from either team on why there is no async mode. My reading: both games interleave the players inside a turn (Hearthstone's secrets and triggers resolve on their own, but Gwent's round passing and both games' animations are built around two people watching the same moment), and both are sold on the "match night" feel. Animal Kingdom's turn is self-contained (below), so the reason does not carry over.

What the three teach for this game:

1. A per-turn clock of days is the norm and is understood without explanation. A clock per game is not used by anyone for async.
2. Timeout loses. Nobody auto-plays for an absent player across days (that is what today's live clock does for 30 seconds; across days it would play someone's whole game for them).
3. The list on home *is* the feature. Without a reminder (mail, push), people forget; Chess.com and Words With Friends both notify. This build has no notification (decision 5).

## Why this game suits it

From the logged human games (the last 400 files in `results/human_games/web/`, 258 still replayable at HEAD, a scratch script over `sim.replay`): a game lasts **9 turns on average (median 8, 90th percentile 15)**, so about 4 or 5 turns each. And in none of those 258 games did a decision pass to the other player in the middle of a turn: every handoff was a turn ending. The engine can hand a choice to the non-current player (the legendary Oxpecker's draw on covering asks the covered card's owner), but in practice the player whose turn it is makes every decision in it. So "the clock per turn" and "the clock per decision" are the same thing here, and a daily turn is one sitting: two actions, their choices, done.

At one turn a day each, a game takes about 9 days; at two turns a day, about 4 or 5. That is the right size for a game you play with a friend over a week.

## The rules (as built; the numbers are guesses for Martin to set)

- **The turn clock.** Whoever must act has `DAILY_DAYS` (2 days, `web/match.py`) from the moment the decision came to them. A choice inside your own turn does not restart it; a new turn, or the decision passing to the other player, does. There is no bank and no free window: time unused is not kept. The opening mulligans (both at once, as in a live game) share one window of the same length.
- **The forfeit.** When your clock runs out, you lose the match (reason `timeout`, "ran out of time"). The live rule (the engine passes for you, three missed turns in a row lose) does not apply: across days it would play the game for someone who left.
- **The challenge.** You send a daily challenge to a friend with your deck. It waits on their home, online or not, for `DAILY_INVITE_DAYS` (7 days), then lapses. They accept with a deck of theirs (the match starts at once) or decline. You can withdraw it while it waits.
- **Open matches.** At most `DAILY_MAX` (10) daily matches per player at once, challenges sent and received counted. Chess.com allows far more; ten keeps a home list readable.
- **Both in at once.** A daily match is an ordinary match underneath: the same socket, views and animations. When both players have it open, moves land at once and nobody is sent home. When you end your turn and the opponent is not in the match, you go back home with a line saying whose turn it is now.
- **A restart.** A daily match is saved after every change, as running matches already are, and reloaded at startup however old. Its deadline is a fixed time, so a server restart neither adds nor takes time (minutes against days).
- **The end.** A finished daily match goes into both histories ("Daily · " before the opponent's name) with its replay, as any match. It also stays on home as a result line until you have opened it once, so a player who lost on time learns why.
- **No bots.** A daily match is between two people. A bot answers at once, so a daily game against one is just a live game you leave.
- **Concede and rematch** work as in any friend match; a rematch of a daily match is daily too.

## What a player sees on home (text only, in the existing style)

Under the play bar, a short list in the menus' granite text style, only when there is something in it:

- **Your turn** rows first, the one with the least time left on top: "Your turn · Kalista · 1 day 4 h left". Clicking it opens the match.
- **Challenges to you**: "Kalista sends a daily challenge" with Play (your chosen deck) and Decline.
- **Waiting** rows: "Kalista's turn · 1 day left", and "Challenge sent to Kalista" with Withdraw.
- **Results** not yet seen: "Won against Kalista", "Lost to Kalista · out of time".

The Friend choice on home gets a second way to play beside the live challenge: **Daily**, which works whether the friend is online or not.

**Where a design belongs (for Martin and the design sandbox):** the home list is plain text on granite. It wants to be designed as part of home's piece: how it sits against the key art, how many rows before it scrolls, whether a "your turn" count belongs on the corner piece (as the Friends button counts who is online), and whether the game screen shows the daily clock differently from the live one (today it reuses the clock's place with "1 d 4 h" in text).

## Ranked daily (built in phase 4)

Asked for by Martin's supervising session after the first three phases: a player who chooses daily ranked is paired with the next person who does, or, with nobody waiting for a day, with a bot at their rating; rated like any ranked game on the one ladder; a few open daily ranked matches a person.

- **Pairing without anyone online.** Ranked, then Daily, then "Find a daily opponent" on home. You are paired with whoever has waited longest in the daily queue, whatever the ratings: with today's player numbers (no person-versus-person games among the last 400 logged) a rating window would pair nobody. One place in the queue at a time; Leave takes it back.
- **The bot after a day** (`DAILY_RANKED_WAIT_DAYS` = 1): the nearest bot at your rating (`Ladder.nearest_bot`, avoiding the decks of your last bot games, as the live queue does). It answers each turn at once; you keep the daily clock. This replaces the doc's first recommendation of no bot at all.
- **Rating.** Untouched: a daily ranked match is two ladder seats, so `rate_match` rates it as it rates any ranked match, and the history calls it ranked. Daily and live results share the one ladder.
- **At most `DAILY_RANKED_MAX` (3)** daily ranked matches a person, the wait in the queue counted, inside the 10 daily matches.
- **Not built:** Chess.com's "not rated before the fourth move". A player who joins the queue and forgets loses on time, rated. Decision 3 below.

## Decisions that are Martin's

1. **The clock.** Recommended: one fixed setting, 2 days a turn, for everyone (a choice of 1, 2 or 3 days on the challenge later, if players ask). Chess.com's default is 3, but its games run 40 moves; ours run 4 or 5 turns each, and 3 days a turn makes one slow game last a month.
2. **Timeout.** Recommended: a loss, always, as built. The alternative is a loss only after the first turn and a lapsed match before it (nobody's history), which is kinder to a challenge accepted and forgotten.
3. **Ranked daily and the rating.** Built on the one ladder (Martin, 2026-10-24: "every game counts"). Open: whether a timeout or concession before your own first turn should move no rating, as Chess.com does before the fourth move (recommended). Chess.com keeps a separate Daily rating because a day per move is a different game from blitz; a turn of this game with a day to think may be too.
4. **Vacation.** Chess.com's answer to "I'm away for a week". Recommended: none for now; the 2-day clock and 10-match cap are small enough to recover from. It is the first thing players will ask for.
5. **Telling a player it's their turn.** Nothing tells them today except home. Recommended next: a mail when a turn comes to you and you have not been on for a day (the feedback mail's Gmail sending exists, `web/feedback.py`), with an opt-out in Settings. Words With Friends lives on its notifications; without one, daily play leans on people remembering.
6. **Live clock when both are in.** Built: the daily clock always applies, even while both are in the match; only the pace is live. The alternative, switching to the live clock (30 s and the bank) while both are present, punishes whoever happens to have the tab open.

## What the current match code already does, and what it does not

Already there:

- **Matches survive a restart.** `Hub.save` writes every match to `results/web_matches/<id>.json` on every change (atomically); `Hub.load` reloads every unfinished match at startup (finished ones for a day). A daily match needs nothing more to wait a week.
- **Reconnection.** A seat is a token; the socket sends the seat's full view on connect, and the client plays only the events it has not seen. Opening a match days later is the same as reconnecting after a dropped socket.
- **Back into the match from anywhere.** `/api/current` hands any tab the match you are playing (within an hour of its last move), and boot jumps into it. For daily matches this is wrong (it would trap you in a match where it is not your turn), so daily matches are left out of it.
- **Views are per seat and complete.** Nothing in a view depends on having watched the game live.
- **Friends, presence and chat.** Who your friends are, who is online, and a socket that reaches every open tab of a player (used to tell them a daily challenge came, or a turn).
- **The history and replays** at match end, for any match with people in it.

Not there, and built for this:

- A clock in days with a forfeit (the live clock is seconds, a bank, and the engine passing for you).
- A challenge that waits for someone offline (the live challenge is held in memory, needs the friend online and lapses in 60 seconds).
- A list of your matches across days (the server knows matches only by id and token; the client keeps tokens in the tab's session storage).
- Going home when your turn ends.
