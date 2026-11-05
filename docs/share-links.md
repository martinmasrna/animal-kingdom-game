# Share links

Wave 2, step 4: a replay and a deck anyone can open from a link.

## What a link looks like

- Replay: `https://animal-kingdom.fly.dev/#/replay/<token>`. The token is 16 random characters made when a player first taps Share on that match. The same match always gives the same link.
- Deck: `https://animal-kingdom.fly.dev/#/deck/<code>`. The code is the deck code's `AK1:` part without the prefix. Its first line (`### name`) goes in as `?n=<name>`. The link holds the whole list, so the server stores nothing.

A replay link carries a token, not the match key (`ABC123-0`). Match keys are six characters long and are shown to friends as room codes, so anyone could guess one. The token can't be guessed. Your own `#/replay/<match key>` keeps working for you only.

## Who sees what

- Anyone with a replay link sees it read-only: the same board and both hands, as the player's own replay shows them. They don't need a profile. "Play from here" is hidden, and Leave goes home.
- Anyone with a deck link sees the list, and one tap imports it into their collection as a new deck. A visitor with no profile gets a guest profile, as on any first visit, and the deck goes into it. Import leads to the collection, and Back leads home.
- A bad link (an unknown token, or a code that holds no card) shows a toast and goes home.

## Martin's decision points

1. **Who may share a replay.** Built: each player shares their own seat's replay, from their own match history. In a friend match both players can share, and each link shows the board from the sharer's side. Recommendation: keep it. Both players saw the whole game, and in the replay both hands are open anyway. The alternative, where the opponent must agree, adds a step for little gain.
2. **Names in a shared replay.** Built: names show, as in the player's own replay (`Name#1234` and the bot's name). Recommendation: keep them. A replay sent to a friend is about who played, and the ladder already shows names publicly. If strangers start passing links around, hiding the opponent's name (not the sharer's) is the change to make: it is one line in `replay.game_views`' `names`.
3. **Revoking.** There is no way to unshare a link. Recommendation: none for now. A link only shows a finished game. If someone asks, deleting the row from `shares` is enough.
4. **Link previews.** A link pasted in a chat app shows the site's generic preview, not the match. Recommendation: later, once links are used at all.

## Where Share sits (no new art)

- Match history: a text action "Share" at the end of each row's meta line, in the row's small grey type. It copies the link, or opens the phone's share sheet. Belongs visually: a small icon button at the row's right edge, beside the result, once there is an icon for it in `kit2`.
- Collection, an open deck: a text "Share" next to the existing deck-code actions. Belongs visually: in the deck panel's header, beside the name, with the same icon.
- Shared replay: no Share button (the viewer isn't the player); "Leave" says "Home".
