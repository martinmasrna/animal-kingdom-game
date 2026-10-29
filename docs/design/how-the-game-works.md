# How the game works

The generator behind every card call in *Animal Kingdom*: the few dependencies from which a card's worth follows. Read it before reasoning about any card, effect, deck or balance change, and reason *from* it, never from Magic, Hearthstone or Gwent. Martin's words carry their date; the numbers come from 2,100 human games on map_b (2026-09-26 to 2026-10-29, `results/human_games/web/`), replayed through the engine on 2026-10-29. `rules/overview.md` and `rules/keywords.md` are the rules; this is why the rules produce the game they do.

## The game in one paragraph

Everything is a placement, and you get two a turn. Drawing is not a resource you accumulate; it is a placement you give up, which is why players take the draw action about four times in a whole game and the hand sits at four cards from the first turn to the last. One placement does up to four things at once: it puts a body on a spot (a region corner, a link in your chain, a den-front crossroad), it buries an enemy if yours is bigger, it flips who owns that crossroad (which can break a region and cut a connection), and it fires an effect. The frontier it can go to is tiny: at any moment a player can legally reach about three to five empty crossroads and typically one coverable enemy, all game long. Strength has one moment of truth, the instant of placement (can I cover that?), and one standing job (can they cover me?); it grows into nothing on the board, and above the field's top it buys nothing. Nothing dies in combat, so the board changes only by covers and removal effects. Two clocks run in the open, den capture (median 10 turns) and 100 food (median 13), and every deck sits on one clock while slowing the other. The skill is reading a position with five-ish legal spots and two moves: which corner breaks their region, which crossroad cuts their chain, which body they cannot answer, which clock they are on.

## 1. The ledger is actions

There is no mana, so a card's price is its action, and every card costs the same one. What differs is what a card gives back in actions and what it does to the board.

- "Draw 2 cards" on a Roar is +1 action, not +2 cards: it skips the draw you would otherwise have spent half a turn on. Martin, 2026-10-08: "It's a tempo card. It's not a value card. Like, you spend one card to draw another while playing a body. ... if you wanted to draw cards, you might as well just press the button that draws you two cards." 2026-10-04: "units that are drawing cards are tempo units in general."
- "Play another animal" is +1 action and −1 card. Lemming, Mole, the Prince and Princess: three bodies in one action is the strongest thing the economy allows, which is why extra placements never sit on commons (Martin, 2026-10-27) and why a free placement that needs an empty crossroad is worth little after round 3.
- A card that comes back to hand costs an action to replay: "if something comes back to your hand or even to your deck, that's much worse. Then you need to spend one action to play it and another action to consume it ... you get 50% less actions than your opponent" (2026-10-12). Flee is therefore an advantage only on an animal whose Roar is worth playing again; a vanilla Flee body is "worse than a 4 strength vanilla" (2026-10-21).
- An extra action (Beaver) is the ceiling of the economy; an effect that costs the other action (Titan, "if you played another Cat this turn") is priced as half a turn.
- The hand is not value. It is the guarantee that each coming action converts into a placement. Four cards is enough; an empty hand means the next action is a draw, which is a turn half lost. The four-card median hides the archetypes: an aggro deck with extra placements empties its hand by design and lives on refuel ("you're going to have empty hand for most of the time", 2026-10-12), so "if your hand is empty" is a real aggro condition (Ocelot, the Dormouse's first version); a control deck holds cards, so a hand-size payoff (Peacock, Macaque at 5 cards) is a real condition only there.
- Fetching a specific card from the deck is a tempo rider, not value, and a weak one when the target is a common at three copies: "you have mulligan, and you can draw 2 cards per turn to draw it" (2026-10-14). A tutor earns its line when the target is a one-copy card the plan needs on time (Scout a legendary; the Eggs drawing their Snakes and Birds).

## 2. Value is cashed at the moment of placement

Because the board changes only by covers and removals, a card's worth is what its placement changes right then, per action.

- Strength is spent at cover checks: yours when you land, the opponent's every time they consider covering you. A counter that lands on a body already standing changes neither its own landing (done) nor, past 6 or 7, anyone's ability to cover it, so "strength gain once something is on board is almost useless" (2026-10-27); "once the animal is like 10 strength, then it doesn't matter anymore. There's no difference between 20 and 30" (2026-10-12). What does count is strength that changes a check still to come: a buff in hand (Handlock, Tarsier) lands bigger; an anthem over several bodies (Mahi-mahi, the Leopard's equal-strength cover) changes every future check in the fight; strength on the opponent's turn only (Giraffe, Cape Buffalo) makes a body harder to cover without making it a better coverer; a growth that counts in hand too (Python, Rattlesnake, the Boa "wherever this is") is a body that lands big later. The useless shape is the lone body ticking up where it stands.
- The same body on an empty crossroad and on an enemy are different cards: "the difference between playing lion on empty crossroad and playing lion to cover an enemy 5 or 6 strength unit is incredible" (2026-10-22). A cover is a body placed, an enemy buried, a crossroad flipped and often a region broken, in one action. 89% of covers in recorded games land on enemies.
- Delayed payoffs (Sloth, Black Bear, the Eggs) hand the opponent a window and die to a cover; they are priced for the turns they sit there.
- A removal Roar on a small body is placeability-gated: it needs an empty crossroad next to the target, and the empties near the fight go first. "In order to play a card, you need to actually be able to place it ... usually after turn 4 or 5, there are no empty crossroads anymore ... each crossroad is only adjacent to one enemy at a time, or at most two" (2026-10-22). "Remove all adjacent enemies" has a ceiling of two and a floor of zero.

## 3. The strength ladder is coarse and every step counts

Recorded covers land by +1 (29%), +2 (24%), +3 (19%); fewer than 13% of covers ever hit a 6 or more. So:

- 0–2 cannot go on a stack at all ("you cannot play one strength animal on a stack, because it cannot cover anything", 2026-10-12): a corner holder, a token, a body for an effect, nothing else. Region control ignores strength, so this is also where the food bodies live.
- 3–5 is the fighting range: covers and gets covered.
- 6–7 holds a crossroad against commons. The Lion (7, vanilla) is the anchor of the whole pool, and a 7 that also does something must pay for it (Tiger: Apex, so it cannot land on an empty crossroad).
- 8 and up is a wall only an effect answers, which is why those bodies carry a drawback (Hungry, Titan, Crocodile's −3 on the opponent's turn) and why "strength 8 or more should be animals that could take on a Lion realistically" (2026-10-17).
- A removal on a 6 body is wrong twice: the 6 already removes by covering, and "OBVIOUSLY you can't give this effect to a 6 strength unit" (2026-10-28). The strongest utility rides the smallest bodies.
- A removal is worth what it removes. Taking off a 1 or 2 that anything could have covered is worth almost nothing ("Grasshopper is beyond useless", 2026-10-12); the removals that earn a card are the ones that reach what covering can't: a 6+, a buried stack, a covered ally's coverer.

## 4. The frontier is small and the board does not fill

Connection to the den gates placement, so the spots a player can use are the empties next to their chain plus the enemies their hand can cover. Measured per action: a median of 3–5 legal empty crossroads and 1 coverable enemy, in every round. The board keeps 4–7 empty crossroads through the midgame, but they are the wrong ones: behind enemy lines or in your own back row. Consequences:

- Flight and Reach are worth what they let you cover on landing, not the keyword: "Flight is worth what the flier can cover when it lands, so on a 1 or 2 it is little more than reach" (principles). Flight never captures.
- Any effect that counts adjacent allies or enemies has a ceiling of 2 in practice ("you're not going to play swordfish next to three of your fishes and still be able to remove three enemies. No such crossroad exists", 2026-10-08).
- A condition the board makes true by default is no condition: "connected to this" is most of your animals for the first three or four turns; "stranded" is "so so easy to satisfy" (2026-10-28).
- "Place on a random adjacent empty crossroad" is a first-three-rounds effect; after that it fizzles, and a clause to rescue it "just gets clunky" (2026-10-13).

## 5. Two clocks on one board

The den is a connection problem: the defender cannot sit on it, so they hold a three-wide front with bodies the attacker cannot cover, and the attacker needs one gap plus the second action to step through. Food is region control: four corners held at once, so small bodies make it and big bodies defend it. The board decides both: "if you're at 60 and your deck can only give you food from hand 5 or 10 at a time, the 60 might as well be 0 if you're losing on board, because board transfers to food by controlling regions and translates to den capture" (2026-10-20).

- Every deck is on one clock. A den deck must stay fragile to a wall; a food deck must stay slow against a rush; that is where rock-paper-scissors comes from, and why "a card that only punishes one deck is bad design" (2026-10-08) while a deck having a bad matchup is fine (2026-10-27).
- The 2-action trap: clearing a den-front blocker with one action leaves no action to capture, and the opponent covers the gap on their turn (Martin's Pestis and Skunk analysis, `cards/aggro-redesign.md`). A closer must clear and occupy in one action (Apex), or the gap must already exist.
- "Must answer" here is an engine in the backline, not a big body: "in Hearthstone a big minion is must answer because it keeps hitting you in the face. In our game you're not doing the attacks. The must answer cards are more of engines that you play in the backline" (2026-10-23). A 7 that landed is a 7; a Whale Shark drawing every Dusk is the threat.

## 6. Pricing a card

The procedure, in Martin's order:

1. Ledger: what the card gives or costs in actions (draw rider +1, extra play +1 −1 card, bounce −1, Titan −1, a condition that eats the other action −½).
2. Placement: what the body does on landing (cover range from §3) and where it can legally land (§4). A 1–2 with an adjacency Roar has one target and needs an empty crossroad beside it.
3. Condition: how often the deck that wants it has it for free. "Payoff is always the same, which means what we need to compare is how difficult this condition is to meet" (2026-10-22). Board state already there, or a body the deck wants gone, costs nothing; a condition that takes the turn's other action costs strength. Priced for the common failed state, never the screenshot.
4. References: the Lion (7) for bodies, the Eagle (5, Flight) for fliers, and the cards that already carry the effect at the same rarity. A card an existing card strictly dominates, or that dominates one, is out. The unconditional version sits at a higher rarity than the conditional one (Honey Badger rare, Serval common).
5. Counterplay: the opponent beats it by ordinary play, covering it or ignoring it, and does not lose the game by failing to answer it at once. Orca and the legendary Leopard at 7 were "answer this immediately or you lose" (2026-10-21), and the fix was the number, not the mechanic.

When unsure between too weak and too strong, ship strong: "a broken card is obvious in play and easy to nerf, a weak one just goes unplayed" (2026-10-09).

## 7. What a deck is, and what a card is to a deck

A deck is a way to win on one clock and a way to play that feels different from every other deck: "the deck should have a really signature and unique, not just win condition, but also play style" (2026-10-13). Cards serve play styles, not precons: the Black Bear is at home in combo, control and Handlock and in no swarm deck; a family is a package that slides into real decks, not a lock ("look up what 'packages' term in deckbuilding means", 2026-10-28). "A handful of cards may be good only with their own deck's engine; the whole collection may not" (2026-10-12, 2026-10-26).

A plan that needs three or four of its own uncovered bodies at once is solitaire: "the opponent either covers one piece and breaks it, or ignores it and watches" (2026-10-13). A payoff that is good only when you are already winning is a bad card ("win more, lose more", 2026-10-22). Explicit synergy ("if you have a Megafauna in hand") is clunky; implicit synergy (the Condor compares strengths, the Oxpecker reads the strongest card in hand) is the shape to want (2026-10-04).

## 8. Rarity and legendaries

Rarity asks what goes wrong if the opponent faces the card three times a game (2026-10-22). Commons are the deck's engine; rares are the situational or tech cards and the effects that would be too consistent at three copies ("the naked mole rat, which gives you free extra placement, could not possibly be a common", 2026-10-12); a rare with a common's effect must beat the common. A keyword alone is a common; the rare with the keyword earns it with something more, never with +1 strength ("then suddenly it becomes the best card in the game", 2026-10-21).

A legendary changes a rule or bends the game's own verb for you; it does not add a number. Theron turns a Cat's cover into a removal; Krill makes a Titan cost one action; the Locusts cover the board; Eon shuffles itself back smaller. It amplifies what the deck already does ("the deck gameplay doesn't change, it just gets amplified", 2026-10-08) and is readable as the animal's own myth. "Just another card draw", a common's effect doubled with a keyword, or a reprint of a rare in gold is "lazy" (2026-10-08, four times). A board wipe from nowhere "is a card from Hearthstone or Magic, not from our game" (2026-10-22); the same function as the Locust plague, which the opponent sees and plays around, is the game's own version.

## 9. Elegant and clunky: the chess test

The game is "closer to chess, but much more fast-paced, than to solitaire" (Martin, 2026-10-29): open decklists, five legal spots, one or two coverable enemies, two moves. A good card creates decisions on the board; a bad card creates decisions in the hand.

Clunky, in his verdicts: an effect that needs a rescue clause for the common case where it fizzles; a Dawn or Dusk that asks the player anything ("don't turn this into a copy of Magic", 2026-10-13); an action on the opponent's turn; a wording with "other than", "once per turn", "this/it/there" in one sentence; a known keyword with a word added; a card whose use case exists only in one exact board state (Skunk: "only good in exactly the situation where there is a single blocker between you and the den"). Elegant: one sentence, the whole rule, the animal visible in it (Rattlesnake grows on shuffles, the Cockroach comes back, Vesper lands on whoever covers a Queen), and a decision for both players every time it is played.

## 10. References translate roles, never mechanics

Hearthstone and Gwent carry real principles, and the agent's failure is copying the surface. A reference names a role; the role is then rewritten in this game's resources.

| the reference | the role | in this game's terms |
|---|---|---|
| Big Game Hunter | the cheap answer to the one body a deck cannot otherwise pass | a small Roar body removing 6+, placed beside the wall; its cost is the empty crossroad and the body that gets covered next turn (Honey Badger) |
| Dreadsteed | a body that cannot be made to stay dead, so attrition favours its owner | the Cockroach, back on its stack at once (a return to hand would cost the action) |
| Doomsayer | a reset the opponent sees coming and plays around | the Locusts: Wild tokens with a two-turn timer, covered to be spared |
| Divine Favor, Hellbent | the aggro refuel that pays for being behind on cards | Divine Favor on the Macaque legendary; the Ocelot's empty-hand draw |
| Kazakus / Reno | a deckbuilding condition any deck can meet its own way | "your starting deck has no animal of strength 4 or more" (the Capybara) |
| Face Hunter | early bodies, a few answers, refuel, finishers | the decomposition Martin ran on Food Aggro (2026-10-08): which slot is missing here |
| Gwent bronze/silver/gold | copy limits that make rarity a role | the three-copies question (§8) |

Gwent (beta) is the closest economy: one card a turn, no mana, a unit is a number, copy limits by rarity. It is the wrong model for the board, because it is nearly solitaire; Hearthstone is the right model for interaction and counterplay and the wrong one for cost. Magic is for method only. A reference without its translation is a Hearthstone card with an animal painted on it.

## 11. Derivations

The generator should give back the calls already made. It does:

- Cougar (6, place next to any Cat ignoring connection) is the worst Cat: a 6 that cannot cover a 7 and a reach whose landing spots are the wrong empties (§3, §4).
- Lemming and the Sardines are strong at strength 1 and 0: three bodies for one action, and region control ignores strength (§1, §3).
- Serval at 3 removes any adjacent enemy for the price of the other action and a Cat deck; Macaque does it for five cards in hand; Honey Badger does it for nothing and is a rare at 3 removing 6+ (§6.3–4).
- Gale drew for every unit beside the den on a 6 flier and went into goodstuff: body plus +N actions with a condition aggro meets for free (§1, §6).
- Pestis clears a den-front stack and leaves no action to capture (§5).
- A legendary Gorilla that grows on the board for each buffed card in hand: strength after placement is nothing (§2).
- "Your opponent can't place animals next to this" and "when this leaves an enemy it covered, remove it": one freezes the frontier that is already five spots wide, the other is "apex predator with extra steps" (§4, §9).
- The Vulture that lands where a removal happened "flies from your deck and lands on top of your own 6" (2026-10-13): the board sequence, played out, is the check (§2).
- The Capybara at 2 with +7 under the small-deck condition, accepted at once: a Kazakus role translated, one line, a decision at deckbuilding (§7, §10).
- Flee on the herd's Roar animals and not on the Cape Buffalo: a fleer is worth its replayed Roar, an aura wants to stand (§1).
- Vesper from hand or deck onto whoever covers a Queen: no action spent on the answer, a cover becomes a trap, and removing Vesper puts the enemy back on top (§1, §9).

## 12. Where this stops

The generator prices and places; it does not feel. Whether a deck is fun, whether a turn has the right number of decisions, whether a card is "boring" past the point this document explains, is settled by Martin in play and nowhere else. Imagined games are reasoning, not evidence. Bot win rates are pilot artifacts until a stronger pilot says otherwise (`bots-are-players`, `balance-eval`). What this document can do is make sure that what reaches him has already passed everything above, so that his time goes to the part only he can do.
