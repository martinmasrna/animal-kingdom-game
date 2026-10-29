# Card rulings

How recurring card-text patterns resolve. [`overview.md`](overview.md) holds the core rules and [`keywords.md`](keywords.md) the keywords; this file holds the rulings on everything else card text does. The engine implements all of them.

## Card identity and tags

- Every card is globally unique by name and belongs to exactly one deck. Apparent duplicates are deliberately different animals (Worker Ant and Soldier Ant, Black, Grizzly and Polar Bear).
- A card's `tags` is a flat list holding species families (Cat, Canine, Colony, Snake, Lizard, Bird, Rodent, Arachnid, Bear, Megafauna, Egg, Fish) and roles (Queen, Worker). "A Colony Queen" means the tags contain both. A card may carry several families and then counts for every matching family effect. Tagless cards are allowed.
- Eggs are units: counted by unit queries, hit by unit triggers, able to capture a den.

## Placement and actions

- **Eon at its end:** an Eon whose Dusk would shuffle it back at 0 strength or less is removed instead. Not printed: it's what players expect, and without it an Eon could loop forever against an empty-handed opponent (found in a random game that ran to the 400-turn cap, Martin, 2026-10-09).
- **"Place" versus "play":** an effect that *places* an animal (Vesper, Sunfish's Baby Fish, Scarlett's cubs) puts it there outright: no connection, no strength check, no action. It isn't a play: its Roar doesn't happen, and counts of animals played (Serval, Hare) don't see it. Everything else that reacts to an animal arriving does, "whenever you place" reactions among them (the Worker Wasp pays for Vesper and for a Young Ant landing; Martin, 2026-10-21): a placed animal that lands on an enemy covers it (Spikes, Poison, Flee react), and traps beside it see it. *Playing* is a full normal placement (below).
- **Extra placements** ("play another unit", "play one more Cat"): a full normal placement (connection unless Flight, covering strength, any cost) that consumes no action, so they chain. From hand only unless the card says "or deck". "May" makes it optional; it fizzles when nothing qualifies.
- **"Can't" beats "can".** When one card forbids what another allows, the prohibition wins.
- **Next to the opponent's den** means one of the enemy den's front crossroads.
- **Sardine** places the copies from hand and deck on random empty crossroads adjacent to the triggering one; leftovers stay where they are. The copies are placed (traps beside them see them), but their Roars don't fire.
- **Recurring timed triggers** ("at the start of your turn") fire every time their window comes while the unit is in play, including the turn it was played if the window is still ahead. "Your turn" means the owner's turn only.

## Drawing and hidden information

- **Filtered draws are random, not tutors** ("draw a Rodent", "draw 2 Birds"): pick uniformly at random among matching deck cards, with no deck inspection and no reshuffle; fizzle if none. The one exception is a designed pair fetching its named sibling from hand or deck (Prince Leo and Princess Lea).
- **Andean Condor** reveals both decks' top cards publicly, compares printed base strength (dynamic strength counts as 0), and draws its own card only if it is strictly greater. An empty opponent deck counts as strength 0; an empty own deck fizzles.
- Nothing else reveals hidden information. There are no open tutors in the pool.

## Remove Pile, returns and shuffles

- There is one shared Remove Pile, and each card in it is still its owner's: **"your Remove Pile"** (Raccoon) and **"your opponent's Remove Pile"** (the legendary Raven) are the owner's cards in it. A **remove** is any card sent there from hand, deck or board and fires remove triggers; **Deathrattle** is the narrower case of a unit leaving the board.
- **"…instead"** would replace the removal (the card never reaches the Remove Pile, fires nothing); no card in the pool does it now. **Fall** (Ember, Cockroach, Earthworm, Worm) is a real removal, then the effect: a Cockroach replaced by a Cockroach still counts as removed (Hyena, Piranha, Vulture). The new one stands at the same height in the stack and comes back rather than being placed: placement reactions (Golden Orb-Weaver, Hippopotamus) never see it, so nothing loops (Martin, 2026-10-10). It is a fresh Cockroach, keeping nothing the old one was given or lost; Roach King keeps its growth from fall to fall but no loss of strength, so one shrunk below 0 can't fall for ever (Martin, 2026-10-26).
- **Shuffle events** are one per card shuffled into a deck (Raven's "shuffle 2 back" is two events). Incidental reorders don't count.
- **Skunk's bounce** returns the enemy unit to its owner's hand. It is not a removal (no Deathrattle, no remove trigger). The returned copy is locked, unplayable through its owner's next turn; other copies of the same card stay playable.
- **Rat** removes an adjacent enemy of any strength, then a random card from your hand goes to the Remove Pile (a remove, not a Deathrattle), target or not; an empty hand pays nothing.
- **Plague effects** that "remove everything from a crossroad" take the whole stack, both players' units, and fire every Deathrattle.

## Specific cards

- **Oxpecker** counts the fixed 30-card starting decklist: each copy with printed base strength 8 or more.
- **Once-per-turn caps.** Value and food triggers print no cap and have none. Each one also has a `cap_*` flag in `engine/config.py` (off by default) for tuning experiments.

## Roam, Reach, Poison, Dawn and Dusk: the engine's reading

The keywords are defined in [`keywords.md`](keywords.md); these are the calls the engine makes where the definitions leave room.

- **Reach counts from the den too.** Ordinary placement lands on the den's front crossroads, so the den is a launch point: its front crossroads are one step away, and Reach lands one further. Reach never takes a den; a den is taken only along the ordinary chain.
- **Roam lands like a placement in everything but the Roar.** Arriving sets off every adjacent trap (Hippopotamus), even one the animal already stood next to before it moved. A cover by roaming is a cover: Spikes, Poison, Pufferfish, King Theron and an Apex Predator's eat all happen. What is printed as a Roar does not (Caracal's "if placed on top of an enemy"), nor do "when you play" or "whenever you place" reactions (Red Wolf, the Worker Wasp): moving isn't placing. An Apex Predator roams only onto an animal, its own included, and eats it; it never roams onto a den.
- **A roam keeps the animal's place in the play order.** Moving isn't playing; a bounced animal played again is newly played.
- **Roaming onto a den ends the game where it stands.** The animal never leaves its crossroad.
- **A roam onto the den is a capture like a placement from hand.** A roam takes the den only when the roamer's pack stands on the den front and is connected to your den (Martin, 2026-10-15); an animal Reach dropped behind the enemy's lines is cut off and can't take it (Martin, 2026-10-10).
- **A player who can roam has a move.** Only a player with no legal action passes automatically, and a roam is one.
- **A free roam is spent before an action** and keeps the turn open after its two actions until it is used or the player ends the turn. Clarion ([WHITE WOLF]) grants one each turn.
- **Poison ticks under a cover.** The poisoned coverer is removed at the start of the Poison animal's controller's next turn even if something has covered it since (it comes out from under the stack), as with venom.
- **Dawn and Dusk resolve one at a time, in play order, each in full before the next.** One that an earlier one removed or buried does nothing. The delayed payouts due this turn ("In 2 turns", "Next turn": the Sloth's food, the Chipmunk, King Cobra's venom, Poison) resolve before your Dawn effects, so a Sloth's food feeds your Hungry animals the turn it arrives (Martin, 2026-10-24).

## A unit uncovered by a removal does not react to it

When removing the top unit of a stack uncovers the unit beneath, that unit was buried at the moment of the removal, so its "when … is removed" reactions (Queen Adira, Jackal, Vulture, Egg Eater, Eon) do not fire for it. Only units already visible when the removal happens react. Found in play (2026-09-28): a Tiger ate the Grizzly covering Queen Adira and she drew a card.

## The launch decks: the engine's reading (2026-10-08)

The calls made where the card workbench's text left room when its twelve decks went into the engine. Each is a first reading, for Martin to confirm or overturn in play.

Keywords:

- **Hungry N** is a Dawn effect: it eats in play order with your other Dawn effects. Only a top animal eats; a buried one is skipped. With fewer than N food it eats all there is and gets −1 strength for good for each food short: an Elephant (Hungry 5) with 4 food eats the 4 and becomes an 8 (Martin, 2026-10-26). An inked animal isn't Hungry until the ink wears off.
- **Titan** takes two actions, so it's offered only while two are left (an extra action from the Chipmunk counts). No free placement can play it ("play another animal", Remora, the Prince's twin).
- **Flee** happens before every other reaction to the cover: the animal is back in hand before an Apex Predator eats, or King Theron removes it. Only an enemy cover sets it off, by placement or by roaming; your own cover of your fleer is a plain cover (Martin, 2026-10-29). The returned card is playable at once and keeps its stored strength, as every bounced card does. The Zebra's coverer goes back to its owner's hand unless it has Armor.
- **King Theron** happens after every other reaction to the cover: the Cat acts first (an Apex Cat eats, and the legendary Leopard grows for it), then Theron removes whatever is left. It needs only the cover: a Cat removed by Spikes still had Theron remove the animal it covered.
- **Octopus ink** lasts for good, while the animal stays on the board (Martin, 2026-10-17); the Octopus inks every adjacent enemy, so Stealth doesn't keep one out. An inked animal has no keywords (printed or given), no anthem of its own (a dynamic strength counts as its printed 0), no aura for others, and none of its triggered effects (Roar-less reactions, Dawn, Dusk, "when this is removed"). It keeps its stored counters and still gets other animals' auras; a timer it already started still runs.
- **Auras that give a keyword** (the Armadillo's Armor, the Porcupine's Spikes, the Jellyfish's Poison) reach the top animal on each adjacent crossroad you control, never the source itself, which carries its own. Poison and Spikes are judged as the animal is covered, so the cover that buries it still sets them off.
- **Grazing**: an animal grazes while it is the top of a crossroad that is a corner of a region its owner controls.

Cards:

- **Unnamed legendaries** show their species as their name until Martin names them in the workbench; their ids are fixed (`<species>_legend`, `rodent` for the placeholder-named Rodent), so naming one later changes nothing else.
- **The legendary Cuckoo** must remove an adjacent animal of strength 4 or less if there is one (yours or a choosable enemy); "play another animal" is then mandatory if anything can be played.
- **The legendary Sloth** runs each of your Dusk effects twice in a row; "At the end of your turn" effects are Dusk effects.
- **A Roar's cost is never declined** (Praying Mantis, Hornet, Pestis): when the cost can be paid, it is, and the Roar only asks which target. The Mantis with an ally adjacent eats one; the Hornet with a spare copy and an enemy adjacent spends the copy; the Pestis next to only its own animals wipes one of them. When the cost cannot be paid, nothing happens.
- **Tarantula** eats a random adjacent ally (Armor excluded) and keeps the strength it showed then, for good.
- **Queen Ant** and **Sunfish** lay on a random adjacent empty crossroad, as the old African Wild Dog placed its Pup (Martin, 2026-10-10); the Sea Turtle's Baby Turtle goes to your hand instead (Martin, 2026-10-26).
- **"An ally was removed this turn"** (Piranha, Vulture) counts your animals leaving the board this turn, whoever removed them; **"each animal removed this turn"** (Hyena) counts both players' (Martin, 2026-10-17). Discards from hand don't count.
- **City Spider** eats like the Tarantula without growing: a random adjacent ally at Dawn (Armor excluded). A Dawn death counts as removed this turn, so the Piranha, Hyena and Vulture see it. With a Cockroach as its only neighbour it's a death and a card every turn (Martin, 2026-10-11).
- **Earthworm**: the two Worms land on its crossroad only while it is empty or yours; under an enemy there is no room and none appear.
- **Clarion's** free roam is for any of your animals with Roam (the card says "an ally"), one per Clarion each turn, spent before an action.
- **Jackal's** flanker must be another of your Canines, not the Jackal itself.
- **"It roams"** (the Street Dog, the Coyote, the African Wild Dog) happens as the effect resolves, as "draw 2 cards" does: you pick where the animal lands, by the Roam rules, the den included (Martin, 2026-10-28: "if a card says 'draw 2 cards' does that mean I get to choose when it happens?"). It is not the animal's one roam of the turn ("it should NOT count towards the 'one roam per turn' limit"): an animal that roamed can still be moved, and one that was moved can still roam.
- **Street Dog** picks one of your other animals connected to it that has Roam, gives it +3 strength, and it roams.
- **Coyote** picks one of your other animals connected to it and gives it Roam, for as long as it stays on the board (covered and resurfacing included; it loses it when it leaves the board), and it roams.
- **"Connected to this"** means a chain of crossroads next to each other, all topped by your animals, starting at this animal's own crossroad. It has nothing to do with your den.
- **"Lands"** means the animal is placed (from hand or by an effect) or arrives on a crossroad by roaming. The legendary Elephant sweeps both times; a Roar happens on placement only.
- **Fox** draws 2 when it is placed if one of your animals has roamed this turn, by an action, a free roam or an effect's "It roams" (Martin, 2026-10-28: "draw on ally roam, not canine roam").
- **African Wild Dog**: a Canine you play from your hand onto a crossroad next to it roams at once ("It roams", above). Played only: a token or an animal an effect places isn't played, and a roam is never a placement, so it can't loop (Martin, 2026-10-28).
- **Bush Dog** puts a Pup on the crossroad it left, but only if the crossroad is empty: an animal that resurfaces there leaves no Pup.
- **Dhole** draws 2 when it covers an enemy that has no other enemy top animal next to it, by placement or by roaming, judged once the Dhole sits on that crossroad. The Dhole gives no equal-strength cover to anyone.
- **Wolverine** can remove only an adjacent enemy that has no other enemy top animal next to it; Stealth and Armor protect from it as from any chosen removal.
- **The legendary Black Wolf** gives +1 strength and draws a card whenever one of your Canines roams, itself included.
- **Okapi** draws at your Dawn and at your Dusk, each time it is grazing then (Martin, 2026-10-29); the legendary Sloth doubles only the Dusk draw.
- **Serval** sets the strength by storing the difference: later buffs and auras count on top of the 1.
- **Placing and roaming cover by one rule** (Martin, 2026-10-24: "the rules for Roam and place from hand should not drift"): every card that changes who may cover whom (Leopard, the legendary Piranha, Chameleon) works for a roam exactly as for a placement.
- **The legendary Piranha** counts the Fish you control now, itself included.
- **Swordfish** removes that many different random adjacent enemies (Stealth doesn't hide from random; Armor stays). **Barracuda** counts itself among your Fish.
- **The repeat legend** (food aggro) repeats the plain Roar of each adjacent allied Rodent, in crossroad order; a Roar that depends on how it was placed (Lynx's) isn't repeated.
- **The legendary Squirrel** loses all your food at once; its 2-turn timer is the Squirrel's (covering pauses it, removing it loses the stake, a return to hand restarts nothing). It pays three times the food it took.
- **The Chameleons** become the copied card for good (removed, it goes to the Remove Pile as the copy) with its stored counter: everything it does from then on, Dawn, Dusk, Poison, Spikes and the rest, but not the Roar it never made. The Chameleon copies a card in your hand, which stays there; Iris copies an adjacent ally or an enemy it may choose, and the copy it adds to your hand is a plain card, its Roar to come when it is played (Martin, 2026-10-26).
- **The Macaw** repeats the last Roar the opponent played, at any point in the game, as its own: next to the Macaw, for its owner. A Macaw's copy counts as the copied Roar, so a Macaw repeating a Macaw repeats what that one repeated. It is not optional (Martin, 2026-10-17). Before the opponent has roared, it does nothing.
- **Greywhisker's** "play another animal" is mandatory if able; the discard is the player's choice.
- **Hare** counts the animals played from your hand this turn, itself included.
- **Mole, Dormouse and Macaque** count the hand after the card that roars has left it.
- **Peacock** counts every card in your hand, itself included while it is there: it covers with the strength it shows, then has one less once it lands (the text taken literally, Martin 2026-10-21).
- **The legendary Butterfly** evolves in hand and on the board alike: each of your Dawns and each gain moves it one stage, whatever the gain's size (its Dawn works from the hand too, the one Dawn that does); a buried stage doesn't evolve at Dawn, and an evolution on the board never fires a Roar again; it keeps every point gained; stage 5 (Monarch) is the last. The stage shows as the card itself (Caterpillar, Chrysalis, Butterfly, Monarch), not as a badge on the art yet.
- **The Caterpillar** becomes the pool's Butterfly (strength 2) and keeps its counter.
- **The Eagles**: the legendary Eagle brings its mate whenever it enters your hand (a draw, a Scout, a steal, a return; the opening hand once the mulligans are done), one mate at a time. A buff to either while both are in hand gives the other the same. The mate never brings the Eagle back.
- **Orangutan's** copy keeps the original's counter. **Baboon** (common): the player picks two different cards; **Baboon** (legendary): two random ones. **Stork**: two different younglings.
- **Gorilla** reads its strength as it lands; **Anteater** gains the drawn card's strength as it would be played now.
- **Mocha** removes every enemy adjacent to any of your top animals, itself included; Armor stays.
- **The legendary Zebra** counts the different Hoofed cards among your top animals anywhere on the board, itself included: two copies of one card count once, enemies and buried animals never count. Different cards, not species: the legendary Zebra and the rare Zebra count as two.
- **Cape Buffalo** removes an enemy sitting directly on top of one of your Hoofed animals.
- **Impala** (Martin, 2026-10-29) makes a Baby Impala and plays it at once: a full placement of the owner's choice, connection and strength checked, its Roar happening, no action spent; a calf with no legal place is gone. The calf has Flee, so a covered calf comes back to your hand as a card and can be played again; its Roar draws only if it lands grazing (as the fourth corner of a region you then hold).
- **The legendary Deer** grows every animal of yours that flees, itself included (Martin, 2026-10-29): the fled card gains 2 strength in hand, keeps it when played again and through every later flight, so a fleer chased twice comes back 4 stronger. It must be on top of its crossroad to grow the others; its own flight grows itself.
- **The legendary Wildebeest and Boar** move each region's food by 5 (each copy counts; a region never produces less than nothing).
- **The legendary Giraffe** shows its controller the opponent's hand face up in the client; the bots don't use it.
- **Great White Shark** has Reach after any animal, of either side, left the board this turn.
- **Cuckoo's** eggs count as the Cuckoo player's shuffles (their Rattlesnake grows, not the opponent's).
- **Opossum** (the pool's) must return an adjacent ally if one can be returned (Armor can't).

## The fit and rarity passes: the engine's reading (2026-10-09)

- **Vesper** works only from its owner's hand or deck: on the board or in the Remove Pile it does nothing. It answers an enemy covering one of your top animals tagged Colony, by placement or by roaming (any Colony animal, Martin, 2026-10-24); your own cover of your animal doesn't count. It resolves with the other reactions to the cover, after the coverer's Roar (as Spikes does), and only if that enemy is still on the crossroad by then. Vesper comes from your hand if it's there, else from the deck, and is placed on top of the enemy: no action, no connection or strength check (a 5 lands on a 10), no Roar, not a play. Landing there is a cover like any other: a Hedgehog's Spikes remove Vesper, a Flee animal runs. An Apex Predator that covered the Colony animal still eats it under Vesper (it is still right on top of its prey). Vesper's trigger reads only where it is, which is public: the decklist is open and hand plus deck is everything not yet seen, so the bots anticipate it without reading hidden information. The client shows Vesper large as it lands, whoever's it is.
- **Methuselah's cap** counts every food a player gains in the current turn, whoever's turn it is and from any source: Roars, Dawn and Dusk, region income, Falstaff's rider. Methuselah's own Dusk 5 counts, and Dusk comes before region income, so its controller's turn ends with at most 20 food gained in all. Food over the cap is lost, not saved for later; food paid or eaten doesn't make room. Like every static, the cap holds only while a Methuselah tops its crossroad and isn't inked: buried, it caps nothing. "The food you gained this turn" (Scrooge, the fed threshold) counts what was actually gained.

## After the launch (2026-10-17, Martin)

- **Gale** counts itself: landing next to the opponent's den, it draws for itself too.
- **[WOLF]** and **Bush Dog** count only your own adjacent Canines, never the opponent's; their text says "your".
- **Python** grows only when an animal leaves the board; a discard from hand isn't a remove (keywords.md, Discard).
- **Spikes** are spent by the first enemy cover even when Armor keeps the coverer on the board.
