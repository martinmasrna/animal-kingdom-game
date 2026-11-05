# Server hardening: status

Branch `server/hardening` from `main` (70dc14e). Scope: the web server's load limits, its security and its robustness. Nothing here changes how the game plays, the bots' strength, ratings or cards. Nothing is deployed.

Checks on the branch: the Python fast tier passes but for the three `test_deck_docs.py` card tables, which fail on `main` too (the Dockerfile leaves that file out). The web client's fast suite passes but for 12 tests that fail the same way on `main` on this machine (no `sqlite3` command line tool for `news.test.mjs`; the replay, decklist-hover and hover-label tests; one collection filter test).

## Phase 1, load: measuring

`tools/loadtest.py` is in; the ramps against `main` and this branch are running. Numbers land here when they finish.

## Phase 2, security: done

Every route in `server.py` and every socket message was tried with wrong types, bad JSON, huge values, lone surrogates and bidi characters, a hostile deck list, replayed and flooded messages. The cases worth keeping are tests in `tests/test_web_guard.py`.

### Fixed (each with a test)

| What | Before | Now |
|---|---|---|
| Malformed bodies (not JSON, a list for an object, a wrong-typed field in `bot`, `gauntlet`, `tutorial`, `from`, `friend`, `text`) | 500 and a traceback in the log, on about 15 routes | 400 with a plain reason (`guard.body`, type checks) |
| A lone surrogate (`"\ud800"`) in a name, chat or feedback | 500: SQLite can't store it | dropped |
| Malformed socket message (bad JSON, `seq: Infinity`, a number for a target) | the sender's socket closed, traceback logged | an error and the view; the socket stays open |
| A socket message that changes nothing (`ready` mid-game) | each one saved the whole match to disk and pushed every seat a view: 500 a second from one socket | nothing saved or pushed. A concede now bumps the match version, so it is still pushed |
| Socket floods | unlimited; messages up to 4 MB | 64 KB a message; a seat sending more than 120 in 10 s is closed (no screen does) |
| A guest seat's name (`POST /api/match` or `join` with no profile) | any string, any length: `"Laras#4821"` showed as Laras's name#tag, 100 KB names went into every view | cleaned like a profile's name, 20 characters, no `#tag` |
| Names with bidi overrides, zero-width or control characters | kept (a name could pose as another) | removed |
| No rate limits on sign-in, profiles, matches, ranked, chat, feedback | a loop could create profiles, matches and mails without end | limits per address (Fly-Client-IP on Fly) or per profile, in `guard.LIMITS`; a server-wide cap of 60 feedback mails an hour |
| Feedback views | any size up to the 1 MB body cap, mailed | over 300 KB dropped, the message kept |
| Saved decks | card ids of any length, `true` as a count | ids over 40 characters and non-integer counts refused |
| Sign-in keys in the log | the presence socket's URL carries the permanent sign-in code (`?key=`), and aiohttp's access log printed it on every connect; seat tokens too | `key=` and `token=` values blanked in the access log |

The limits exempt the server's own machine when it is not on Fly (`FLY_APP_NAME` unset), so `./play`, the tests and the load test run as before. On Fly they key on `Fly-Client-IP`. **To check once on staging**: that Fly's proxy sets that header itself and overwrites one a client sends (Fly's documentation describes it as the address the proxy accepted the connection from). If it passed a client's value through, the per-address limits could be dodged.

### Checked and sound

- Acting as another seat or profile: every socket checks its seat token (96 random bits); every keyed route reads the profile from `X-AK-Key` only; replays, decklists, studies and takeovers check the match is in your own history; `/api/current` hands out only your own seat's token. Friend codes (50 bits) and match ids (about 31 bits, now behind a rate limit) are not credentials.
- Path traversal: `/static` (aiohttp's guard), `/api/study/{name}` (looked up by name) and `/api/replay/{match}` (a history row first) all refuse `..`.
- A replayed socket message is applied like any other: the engine validates every action against the position, so a replay is either a legal move by the seat that sent it or refused.
- The client escapes every string another player controls (names, deck names, chat; covers go through `hasArt`).
- Error texts name the problem, never a path, a query or a traceback; the 500 page is aiohttp's generic one.

### Open, by severity

| Severity | Finding | Recommendation |
|---|---|---|
| High | **Free Expert compute.** Anyone can open practice matches against the Expert (no profile needed), and each Expert move takes a core for up to 8 s. The live machine has one core. Nothing caps how many bot searches one person or address runs at once (Phase 1 has what that does to everyone else). | Cap concurrent bot searches per profile and per address (one or two), and require a profile to make a match. Longer term: bots in a worker process or machine of their own. |
| Medium | **Sign-in CSRF.** The OAuth `state` is not tied to the browser that started it. An attacker can start a Google sign-in from their own guest profile and get a victim to finish it: the victim's Google account is then linked to the attacker's guest, whose sign-in code the attacker still holds. | A short-lived cookie set at `/api/auth/{provider}` and required at the callback. Needs a real provider to test, so not done here. |
| Medium | **Disk that only grows.** `results/web_matches/` keeps every match file forever, and every unfinished one (abandoned lobbies and bot games) is reloaded and its bot kicked at each start; each new custom deck name adds a slug to `results/web_decks.json` (rewritten whole each time) and to memory. Rate limits slow this; nothing bounds it. | Move match files untouched for weeks to an archive folder instead of reloading them at each start (Martin's call: what "restarts keep matches" means for one abandoned a month ago); key custom deck slugs by the list alone. (Memory is fixed, Phase 3.) |
| Medium | **A stuck bot search holds a thread for good.** Past `BOT_THINK_MAX` the match plays a fallback move and goes on (tested), but the thread keeps searching. Python's default pool has `cores + 4` threads (5 on the live machine); five searches that never end leave every bot in every match waiting 20 s a move and playing the fallback until a restart, and the stuck threads delay shutdown. The bot's next move also runs on the bot object the stuck thread still holds. | Bot moves in a pool of their own, or in a process that can be killed; a fresh bot object after a timeout. |
| Low | `POST /api/match` works without a profile (the old guest path; the client always has one). | Require `X-AK-Key`. |
| Low | Either seat can start a rematch alone in a friend match. | A taste call. |
| Low | The `Server` header names the aiohttp and Python versions. | Drop it in `_revalidate`. |
| Low | `callback_url` trusts the Host header when `AK_BASE_URL` is unset. Providers check redirect URIs against their registered list, so the harm is a failed sign-in. | Set `AK_BASE_URL` on Fly. |
| Low | The league key is compared with `!=`. | `secrets.compare_digest`. |

### What reaches the disk from a client

The profiles database (names, decks, chat, feedback with its view, client events: 2,000 an hour a profile), `results/web_decks.json` (each custom deck's name and list), `results/web_matches/<id>.json` (seat names, decks, the whole game, rewritten on every change), the human game logs and replays (deck slugs, names). Each is bounded per request; only the deck file and the match files are unbounded in count (above).

## Phase 3, robustness: done

| Case | Result | Test (`tests/test_web_robustness.py`) |
|---|---|---|
| A bot whose search raises on every move | each move played by the fallback; the game reaches its end | `test_a_bot_that_always_fails_still_plays_the_match_to_its_end[raises]` |
| A bot that runs past `BOT_THINK_MAX` on every move | the same; the event loop never waits on the stuck searches (but see the stuck-thread finding above) | `...[overthinks]` |
| A screen that stops reading (a phone off the network without closing) | **was a defect, fixed.** Every send to it waited until the 20 s heartbeat gave up, so the match froze for everyone meanwhile (10 s and more with no view in a friend match), and the `ConnectionError` that ended the wait was not caught: it killed whichever coroutine was broadcasting, the other player's own socket handler, the bot task or the clock task. Now views go out in parallel, each within `SEND_TIMEOUT` (5 s), and a stalled or dead socket is dropped. Re-measured on a real server with a never-read socket: the other player's longest gap 4.8 s, once | `test_a_stalled_or_dead_screen_never_holds_up_the_match_or_the_other_player`, `test_a_friend_notice_to_a_stalled_tab_never_holds_up_the_sender` |
| A socket that drops mid-turn | the bot does not move in the player's turn; a new socket on the seat (the client's reconnect, or `/api/current` from another tab) gets the same position, and the turn and the game finish | `test_a_player_whose_socket_drops_mid_turn_comes_back_to_the_same_turn` |
| Memory under load | **was a defect, fixed.** `hub.matches` never let a match go: about 0.5 MB each (Python heap plus the Rust bot), 1.7 GB after the 8-minute load ramp, on a 2 GB machine. Idle matches now leave memory (finished after 10 min, unfinished after the hour's rejoin window, never one with a socket, bot or clock running) and come back from their file on demand | `test_an_idle_match_leaves_memory_and_comes_back_from_its_file` |
| The server restarting mid-match | holds: every change is saved atomically and every unfinished match reloaded with its seat tokens; same position, played to the end | `test_a_restart_in_the_middle_of_a_game_keeps_the_match`; on a real process, `tools/restartcheck.py` (SIGKILL and SIGTERM, on `main` and on this branch: back up in 0.5 s, both matches at the same position, played out, no logged error) |

What a restart loses: the ranked queue and standing challenges (players search again), the rate-limit counters, the bot's memory between moves (continuation plans, RNG streams: its next moves may differ, its strength doesn't), and the clock's time while the server was down (given to no one). A reloaded match records its `game_start` event again at each restart (`hub.noted` is not saved), a small double count in the funnel.
