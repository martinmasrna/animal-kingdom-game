# Card rulings

How recurring card-text patterns resolve. [`overview.md`](overview.md) holds the core rules and [`keywords.md`](keywords.md) the keywords; this file holds the rulings on everything else card text does. The engine implements all of them.

## Card identity and tags

- Every card is globally unique by name and belongs to exactly one deck. Apparent duplicates are deliberately different animals (Worker Ant and Soldier Ant, Black, Grizzly and Polar Bear).
- A card's `tags` is a flat list holding species families (Cat, Canine, Colony, Snake, Lizard, Bird, Rodent, Arachnid, Bear, Megafauna, Egg, Fish) and roles (Queen, Worker). "A Colony Queen" means the tags contain both. A card may carry several families and then counts for every matching family effect. Tagless cards are allowed.
- Eggs are units: counted by unit queries, hit by unit triggers, able to capture a den.

## Placement and actions

- **Extra placements** ("play another unit", "play one more Cat"): a full normal placement (connection unless Flight, covering strength, any cost) that consumes no action, so they chain. From hand only unless the card says "or deck". "May" makes it optional; it fizzles when nothing qualifies.
- **"Can't" beats "can".** When one card forbids what another allows, the prohibition wins.
- **Next to the opponent's den** means one of the enemy den's front crossroads.
- **Lemming** places the Lemmings from hand on random empty crossroads adjacent to the triggering Lemming; leftovers stay in hand, and the auto-placed copies' Battlecries don't fire.
- **Recurring timed triggers** ("at the start of your turn") fire every time their window comes while the unit is in play, including the turn it was played if the window is still ahead. "Your turn" means the owner's turn only.

## Drawing and hidden information

- **Filtered draws are random, not tutors** ("draw a Rodent", "draw 2 Birds"): pick uniformly at random among matching deck cards, with no deck inspection and no reshuffle; fizzle if none. The one exception is a designed pair fetching its named sibling from hand or deck (Prince Leo and Princess Lea).
- **Andean Condor** reveals both decks' top cards publicly, compares printed base strength (dynamic strength counts as 0), and draws its own card only if it is strictly greater. An empty opponent deck counts as strength 0; an empty own deck fizzles.
- Nothing else reveals hidden information. There are no open tutors in the pool.

## Remove Pile, returns and shuffles

- There is one shared Remove Pile. A **remove** is any card sent there from hand, deck or board and fires remove triggers; **Deathrattle** is the narrower case of a unit leaving the board.
- **"…instead"** (Opossum) replaces the removal: the card never reaches the Remove Pile, fires nothing, and doesn't count as removed. **"When this is removed, do X"** (Phoenix) is a real removal, then a relocation.
- **Shuffle events** are one per card shuffled into a deck (Raven's "shuffle 2 back" is two events). Incidental reorders don't count.
- **Skunk's bounce** returns the enemy unit to its owner's hand. It is not a removal (no Deathrattle, no remove trigger). The returned copy is locked, unplayable through its owner's next turn; other copies of the same card stay playable.
- **Rat** optionally pays one card from hand (a remove, not a Deathrattle) to destroy an adjacent enemy of any strength.
- **Plague effects** that "remove everything from a crossroad" take the whole stack, both players' units, and fire every Deathrattle.

## Specific cards

- **Oxpecker** counts the fixed 30-card starting decklist: each copy with printed base strength 6 or more.
- **Once-per-turn caps.** Value and food triggers print no cap and have none. Each one also has a `cap_*` flag in `engine/config.py` (off by default) for tuning experiments.

## Roam, Reach, Poison, Dawn and Dusk: the engine's reading

The keywords are defined in [`keywords.md`](keywords.md); these are the calls the engine makes where the definitions leave room.

- **Reach N counts from the den too.** Ordinary placement is Reach 1 and lands on the den's front crossroads, so the den is a launch point: its front crossroads are one step away. Reach never takes a den; a den is taken only along the ordinary chain.
- **Roam lands like a placement in everything but the Roar.** Arriving sets off every adjacent trap (Hippopotamus), even one the animal already stood next to before it moved. A cover by roaming is a cover: Spikes, Poison, Pufferfish, King Theron and an Apex Predator's eat all happen. What is printed as a Roar does not (Caracal's "if placed on top of an enemy"), nor do "when you play" reactions (Queen Honoria, Red Wolf). An Apex Predator roams only onto an animal, its own included, and eats it; it never roams onto a den.
- **A roam keeps the animal's place in the play order.** Moving isn't playing; a bounced animal played again is newly played.
- **Roaming onto a den ends the game where it stands.** The animal never leaves its crossroad.
- **A player who can roam has a move.** Only a player with no legal action passes automatically, and a roam is one.
- **A free roam is spent before an action** and keeps the turn open after its two actions until it is used or the player ends the turn. No card grants one yet.
- **Poison ticks under a cover.** The poisoned coverer is removed at the start of the Poison animal's controller's next turn even if something has covered it since (it comes out from under the stack), as with venom.
- **Dawn and Dusk resolve one at a time, in play order, each in full before the next.** One that an earlier one removed or buried does nothing. Dawn effects resolve before the delayed "at the start of your next turn" payouts (Chipmunk, Taipan's venom, Poison).

## A unit uncovered by a removal does not react to it

When removing the top unit of a stack uncovers the unit beneath, that unit was buried at the moment of the removal, so its "when … is removed" reactions (Queen Adira, Jackal, Vulture, Egg Eater, Eon) do not fire for it. Only units already visible when the removal happens react. Found in play (2026-09-28): a Tiger ate the Grizzly covering Queen Adira and she drew a card.
