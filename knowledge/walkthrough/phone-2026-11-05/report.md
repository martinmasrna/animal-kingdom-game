# Phone walkthrough, 5 November 2026

A first visit played as a stranger on two emulated phones, by taps only: an iPhone (390x844, device scale 3, touch, Safari user agent) and a mid-size Android (412x915, scale 2.625, touch, Chrome user agent). Each phone was its own new player with empty storage. Route: home, Learn to play (both lessons to the win), a Practice match against the Beginner bot to its end, the collection (filters, search, opening a card, the deck sheet, a new deck built), the ladder (leaderboard, match history, meta), a replay, Friends, Settings, News, Feedback, and the match, collection and home held sideways (844x390, 915x412).

Setup: a private server from `main` at 70dc14e (games logged into a scratch folder, not the repo), the preinstalled Chromium (the Chrome for Testing download was blocked by the network proxy). Screenshot files are named `<device>-<step>-<screen>.jpg`; `iphone-side-` and `android-side-` are the sideways ones. Sign in with Google and Discord could not be tried: the test server has no sign-in keys, and these are emulated browsers, not a chat app's built-in browser.

Console and page errors: **none on either phone, on any screen**. Every console error and warning, uncaught page error, failed request and HTTP 400+ response was recorded. A deliberate test error at the end showed that the recording worked.

## Findings, worst first

| # | Screenshot | Screen | Device | What is wrong |
|---|---|---|---|---|
| 1 | iphone-04-match-turn-04.jpg, android-04-match-turn-04.jpg, android-04-match-pending-place.jpg | Match: your hand | both | You cannot read your own cards. A hand card is 77 px wide, its name is set at about 7 px, and the next card covers the end of it ("Queen Melis", "Worker Wa"). With 7 or 8 cards (Android) you see only the number and 2 or 3 letters. A card's text never shows in the hand. The only way to read a card is press and hold, which the tutorial says once (lesson 1, iphone-02-l1-20-holdread.jpg). |
| 2 | iphone-04-match-pending-mulligan.jpg, android-04-match-pending-mulligan.jpg | Match: mulligan | both | The first thing a real match asks is "Don't like a card? Tap it to swap it", but the hand shows no card text and the prompt does not mention press and hold. A stranger chooses blind. |
| 3 | iphone-04-match-pending-place.jpg, android-04-match-pending-place.jpg | Match: a Roar asking for a choice (Termite Queen) | both | The choice shows only as a small box in the top-left corner ("Roar: play a non-Queen Colony animal"), on top of the opponent's hand. It does not say what to tap, nothing on the board or in the hand is marked, and there is no visible Skip. |
| 4 | iphone-03-home-opponent.jpg, android-03-home-opponent.jpg, iphone-04-practice-beginner-chosen.jpg | Home: opponent chooser | both | The bot buttons overlap: "Intermediate" is cut to "Intermedia" and "Advanced" sits on top of its end. |
| 5 | iphone-02-l2-18b-apex-picked.jpg, iphone-02-l2-19-den.jpg | Learn to play, lesson 2 (Polar Bear, den) | both | The coach's bubble covers what it asks you to tap. "Now tap the circled animal to eat it" sits on the circled Buffalo; "Your opponent's den is open! Tap the Squirrel" covers the opened way to the den. |
| 6 | iphone-02-l2-09-mambainfo.jpg | Learn to play, lesson 2 (Black Mamba) | both | The coach says the Mamba removes an enemy "with strength 5 or less"; the card shown just below it says "of strength 6 or less". |
| 7 | iphone-02-l1-23-free.jpg | Learn to play, lesson 1 (free play) | both | "The circles show where your animals can take more regions", but there are no circles on the board at that moment. They appear only after you pick a card. |
| 8 | iphone-02-l2-19-den.jpg, iphone-02-l1-01-welcome.jpg, android-02-l2-end.jpg | Match: top of the screen | both | The row of top buttons covers the opponent's hand (the red card backs), so you cannot count their cards. With about 10 cards (end of lesson 2) most of the backs are behind the buttons. |
| 9 | iphone-02-l2-11-target.jpg, android-02-l2-11-target.jpg | Match: choosing a target for a Roar (Mamba) | both | The card's box and the "Tap the Pigeon" line sit top-left, over the opponent's hand and their den, and touch the Settings button. |
| 10 | iphone-05-coll-04-dd-hab-open.jpg, iphone-05-coll-04-dd-str-open.jpg, iphone-05-coll-04-dd-rar-open.jpg, android-05-coll-04-dd-hab-open.jpg | Collection: filter row | both | The three dropdowns overlap each other (each one's arrow hides under the next), and Search is cut to "Searc". The open lists are narrower than their own words: "Any habita", "Open Ocea", "Any streng", "Strength 8" with the "+" cut off. |
| 11 | iphone-05-coll-01-open.jpg, android-05-coll-01-open.jpg | Collection: family tabs | both | 12 round animal faces. The row scrolls sideways, but nothing shows that it does: the last face is cut at the edge and 2 or 3 more are hidden. Each tab is 34x34 px, and the family it stands for ("Cat", "Canine", ...) is only a hover tip, so a finger never sees it. |
| 12 | iphone-04-match-turn-04.jpg, iphone-03-home-learned.jpg | Match top bar; home top bar | both | The buttons are icons without words, and their names (Settings, History, Remove Pile, Send feedback, Concede; on home Collection, Friends, Menu) are hover tips only. A skull for "Remove Pile" and a speech bubble for "Send feedback" are hard to guess. |
| 13 | iphone-07-replay-later.jpg, android-07-replay-later.jpg | Replay | both | The Leave button is half off the bottom of the screen. The back, pause and forward buttons and the track are 35 px (under 40). "Play from here" is in small type on three lines. At the top, the opponent's two face-up cards lie under round markers, so they cannot be read. With 8 cards in hand (Android) the hand shows only numbers. |
| 14 | iphone-06-deck-01-sheet.jpg, iphone-06-deck-02-sheet-scrolled.jpg | Collection: deck sheet | both | With the 12 decks a new player owns, the New deck button (+) is below the bottom of the sheet. You have to scroll inside the sheet to find it, and nothing says it is there. |
| 15 | iphone-02-l1-14-oppfood.jpg, iphone-02-l1-16-cover.jpg, iphone-02-l1-20-holdread.jpg, android-02-l1-20-holdread.jpg | Learn to play, lesson 1 | both | Other coach bubbles cover the pieces they talk about: "this is your opponent's food" hides an opponent animal, and "The number on a card..." and "Press and hold any card" cover your own front row. |
| 16 | iphone-03-home-learned.jpg | Home after the tutorial | both | A player who goes home from the tutorial's last screen, instead of tapping Play a match, finds Practice set to Advanced, not Beginner. |
| 17 | iphone-05-coll-08-card-tapped.jpg, android-05-coll-08-card-tapped.jpg | Collection: a card opened | both | The opened card is readable, but the related cards under it (Caterpillar, Chrysalis, Butterfly, Monarch) use type about 7 px. The view does scroll, down to the keyword explanations. |
| 18 | iphone-03-home-opponent.jpg | Home: opponent chooser | both | A "Gauntlet" tab is offered beside Practice, Ranked and Friend, with no explanation. |
| 19 | iphone-07-history.jpg | Ladder: match history | both | A match is listed as "Practice · Bot (Easy)". The player picked "Beginner"; "Easy" is the engine's word. |
| 20 | iphone-04-match-end.jpg | Practice match end (defeat on food) | iPhone | Defeat says nothing about why. The opponent had reached 100 food, but only the word Defeat shows. Victory does say "You reached 100 food" (iphone-02-l1-end.jpg). |
| 21 | iphone-07-ladder-leaderboard.jpg | Ladder: leaderboard | both | The first screen is entirely bots ("Teeth and Claws (Legendary Bot)" and so on, rows 1 to 15 or more), with no row for the player. A stranger sees nothing about themselves. |
| 22 | iphone-04-match-end.jpg, android-04-match-end.jpg | Match end | both | Menu, See the board and Rematch are 39 px tall, just under 40. |
| 23 | iphone-02-l1-end.jpg | Lesson 1 end | iPhone | The food counter shows 145, and the number is wider than its circle. |
| 24 | iphone-07-settings.jpg, android-07-settings.jpg | Settings | both | The sound slider's track is 8 px tall; only its knob is a reasonable target. |
| 25 | iphone-07-friends.jpg | Friends | both | The close × is 36x36 px. |

## Screens that were fine

- Home on a first visit (iphone-01-home-first.jpg, android-01-home-first.jpg): Learn to play and I already know how to play are large and clear.
- The two lesson end screens (iphone-02-l1-end.jpg, iphone-02-l2-end.jpg): Victory, one line, one big button.
- The match intro (iphone-04-match-start.jpg): Beginner Bot vs Player.
- Press and hold on a hand card in a real match (iphone-04-match-hold-card.jpg): the card opens large, with its keyword explained underneath.
- The board itself, in the lessons and the match: crossroads, regions, strength numbers and food counters are readable, with no overflow, on both phones.
- Collection: the card grid and its scrolling (iphone-05-coll-02-scrolled.jpg), search with no result and Clear filters (iphone-05-coll-06-search-none.jpg), search results (iphone-05-coll-07-search-lion.jpg), a card opened by a tap and by a hold (05-coll-08, 05-coll-09), building a new deck: cards added by taps, the list in the sheet, Done (iphone-06-deck-03 to 06).
- Match history row and tapping its deck to see the list (iphone-07-history-deck-tapped.jpg); the Meta tab (iphone-07-meta.jpg).
- Friends with no friends yet (iphone-07-friends.jpg), the Menu (iphone-07-menu.jpg), the Feedback box (iphone-07-feedback.jpg).
- Settings (iphone-07-settings.jpg): name, sign-in code with Show and Copy, sound, credits, Back.
- News (iphone-07-news.jpg, iphone-07-news-bottom.jpg): readable, scrolls, Back stays in reach.
- Sideways (iphone-side-08-match.jpg, iphone-side-08-collection.jpg, iphone-side-08-home.jpg and the Android ones): every screen is covered by "Turn your phone upright". Turning back upright returns to the same match, unchanged (iphone-08-match-back-upright.jpg). This is by design, so it is not listed as a finding.

## Count

25 findings. The five worst:

1. You cannot read your own hand: names about 7 px and cut by the next card, no card text (finding 1).
2. The mulligan asks you to swap cards you cannot read (2).
3. A Roar that asks for a choice says nothing about what to tap (3).
4. The Practice bot buttons overlap, so "Intermediate" is unreadable (4).
5. In lesson 2 the coach's bubble covers the animal it tells you to tap (5).
