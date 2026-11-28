# Night run: page QA

Each of the 35 pages was played to the end by taps at 390×844 and by clicks at 1512×800 (random legal play against Expert), with New game pressed mid-game, the rules panel opened and closed, and Play again after the end. Screenshots are in each folder's `shots/` (`open-` and `mid-` at both widths). After the fixes no page throws a script error, scrolls sideways, or hides a legal action under another element, and every folder's own headless check passes. The bot plays one visible step at a time on every page, about 0.3 to 0.8 s apart. On the simultaneous pages (17, 22, 25, 40) both choices are shown at once, which is the rule. Only page code was changed: no rules, numbers or bot logic.

One bug was shared by 30 pages (all but 17, 22, 25, 40 and 42; 40 had its own variant): pressing New game while a move was animating (most of the bot's turn) let the old game's animation finish on top of the new one and overwrite its board. It froze 01 and 21 and threw a script error in 48; the other pages ran the same code. The fix stops the old move after each animation step once a new game has started. A stress test (8 New games per page at random moments, in real time) then gave no freeze and no error on any page. Tapping every non-control element (history, piles, scores, empty board) during play broke nothing, except on 32, below.

- **01 Score or Fight**: only the shared New-game bug.
- **19 Supply Grid**: only the shared New-game bug.
- **10 Engine War**: only the shared New-game bug.
- **22 Possession**: on the phone the "goal" glyph on Shoot ran into the stamina-cost dots; long glyphs now render smaller.
- **06 Breaking Sites**: on the phone "Draw 2" broke onto two lines inside its card; card names now stay on one line.
- **02 Attack and Block**: on the phone, six units on one side ran off the board and over the life and mana; phone units are a little smaller, so six fit, exhausted ones included.
- **42 Real-time Lane**: on the phone the name on the small next-card spilled past its edge; that name is now smaller.
- **17 Prize Auction**: on the phone the top bar overflowed (New game wrapped and was cut off at the top) and hand cards were 46 px with unreadable names. The round track is slimmer, the menu stays on one line, and phone hand cards are 62×82 (two rows when the hand is big).
- **25 Range Duel**: on the phone the top bar overflowed (New game wrapped and was cut off at the top); the turn track is slimmer and the menu stays on one line.
- **18 Edge Flip**: only the shared New-game bug. On the phone, card names sit tight between the edge numbers but stay legible.
- **12 Deck is Life**: on desktop, spell text ran out of the bottom of the card (Recover); the spell art box is smaller, so the text fits. The rules panel (built from RULES.md) no longer shows "All numbers are placeholders."
- **04 Lanes and Scale**: the same spell-text overflow on desktop (Shift), with the same fix. The placeholder sentence is gone from the rules panel.
- **07 Blind Fronts**: on desktop, the Mass and Lone text ran out of the card; the text is tighter now. The placeholder sentence is gone from the rules panel. Not changed: discarding down to 8 shows only as red-glowing hand cards with Pass greyed out. It plays, but a first-timer may pause there.
- **14 Response Duel**: the placeholder sentence is gone from the rules panel.
- **38 Costed Tricks**: the placeholder sentence is gone from the rules panel.
- **31 Claims**: on the phone the claim-name row (the core choice) had 40 px cards with 8 px names; they are now 56×64 with 10 px names, in two rows. The rules panel did not say what Hit 3, Blast and Draw 2 do (their cards show only a number); one sentence added.
- **41 Wave Defense**: on desktop, spell text was cut off at the card bottom (Bomb); fixed. The phone hides card text, and the rules panel did not say what Bomb, Freeze, Repair, Rebuild and the Hits do; one line added.
- **48 Junk War**: the phone hides card text, and the rules panel did not cover Draw and Thief; both added.
- **28 Curling Line**: the rules panel did not say that a card throws to the cell printed on it, or that Any picks a cell from 4 to 12; one sentence added.
- **21 Round Purse**: only the shared New-game bug.
- **03 Exert to Score**: on the phone, six units with some exerted (turned sideways) overflowed the board and overlapped; phone units are smaller, so six exerted fit.
- **33 Time Track**: the phone hides card text, and the rules panel did not say what Hit 3, Hit 6 and Haste do; one line added.
- **27 Bust Duel**: a long line of drawn cards (13 or more) ran off the right edge at both sizes. Lines now wrap, and on desktop a line of 9 or more uses smaller cards so two rows fit.
- **09 Momentum Rope**: only the shared New-game bug.
- **05 Front and Back**: only the shared New-game bug.
- **32 Hidden Contracts**: tapping the ↻ chip in the history list fired a contract swap (it shares the swap button's class). That threw "illegal swap" when no swap was allowed, and swapped a contract by accident when one was. Only the real swap button reacts now.
- **44 Bump Placement**: on desktop, the Shove text ran out of the bottom of the card; cards with text get a smaller art box.
- **46 Echo Mana**: only the shared New-game bug.
- **13 Open Discards**: on the phone, a long discard pile pushed into End turn and covered it, and the bot's pile could run under its mana. End turn now has its own row on the phone, and the bot's pile stops short of the mana.
- **16 Showdown**: on desktop, the Mirror and Solo text was cut off at the bottom of the card; cards with text get a smaller art box.
- **43 Auto Deck Battle**: on desktop, the Bomb, Rally and Opener text ran out of the shop and battle cards; text cards get a smaller art box, and the cards are a little taller on a 800 px-high screen.
- **34 Pitch to Pay**: on the phone, the pitch gem of one hand card touched the cost gem of the next; the gems moved in and the gap widened.
- **40 Simultaneous Turns**: its own reveal sequence had the same New-game bug (two unguarded waits); fixed. Nothing else.
- **15 Key Pieces**: only the shared New-game bug.
- **45 Swing Neutrals**: on the phone, "Sway 2" and "Sway 3" broke onto two lines in their cards; names now stay on one line.
