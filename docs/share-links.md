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

## Settled (Martin, 2026-11-05)

1. **Who may share a replay.** Each player shares their own seat's replay, from their own match history. In a friend match both can, and each link shows the board from the sharer's side.
2. **Names in a shared replay.** Names show, as in the player's own replay. If strangers start passing links around, the change is to hide the opponent's name (not the sharer's), in `replay.game_views`' `names`.
3. **Revoking.** No way to unshare a link: it only shows a finished game. If someone asks, delete its row from `shares`.
4. **Link previews.** A pasted link shows the site's generic preview. A match preview waits until links are used.

## Where Share sits (no new art)

- Match history: a text action "Share" at the end of each row's meta line, in the row's small grey type. It copies the link, or opens the phone's share sheet. Belongs visually: a small icon button at the row's right edge, beside the result, once there is an icon for it in `kit2`.
- Collection, an open deck: a text "Share" next to the existing deck-code actions. Belongs visually: in the deck panel's header, beside the name, with the same icon.
- Shared replay: no Share button (the viewer isn't the player); "Leave" says "Home".
