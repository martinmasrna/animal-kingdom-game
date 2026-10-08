# Card rulings

How recurring card-text patterns resolve. [`overview.md`](overview.md) holds the core rules and [`keywords.md`](keywords.md) the keywords; this file holds the rulings on everything else card text does. The engine implements all of them.

## Card identity and tags

- Every card is globally unique by name and belongs to exactly one deck. Apparent duplicates are deliberately different animals (Worker Ant and Soldier Ant, Black, Grizzly and Polar Bear).
- A card's `tags` is a flat list holding species families (Cat, Canine, Colony, Snake, Lizard, Bird, Rodent, Arachnid, Bear, Megafauna, Egg, Fish) and roles (Queen, Worker). "A Colony Queen" means the tags contain both. A card may carry several families and then counts for every matching family effect. Tagless cards are allowed.
- Eggs are units: counted by unit queries, hit by unit triggers, able to capture a den.

## Placement and actions

- **"Place" versus "play":** an effect that *places* an animal (Vesper, Sunfish's Baby Fish, Scarlett's cubs) puts it there outright: no connection, no strength check, no action. *Playing* is a full normal placement (below).
- **Extra placements** ("play another unit", "play one more Cat"): a full normal placement (connection unless Flight, covering strength, any cost) that consumes no action, so they chain. From hand only unless the card says "or deck". "May" makes it optional; it fizzles when nothing qualifies.
- **"Can't" beats "can".** When one card forbids what another allows, the prohibition wins.
- **Next to the opponent's den** means one of the enemy den's front crossroads.
- **Lemming and Sardine** place the copies from hand and deck on random empty crossroads adjacent to the triggering one; leftovers stay where they are. The copies are placed (traps beside them see them, a City Spider eats them), but their Roars don't fire.
- **Recurring timed triggers** ("at the start of your turn") fire every time their window comes while the unit is in play, including the turn it was played if the window is still ahead. "Your turn" means the owner's turn only.

## Drawing and hidden information

- **Filtered draws are random, not tutors** ("draw a Rodent", "draw 2 Birds"): pick uniformly at random among matching deck cards, with no deck inspection and no reshuffle; fizzle if none. The one exception is a designed pair fetching its named sibling from hand or deck (Prince Leo and Princess Lea).
- **Andean Condor** reveals both decks' top cards publicly, compares printed base strength (dynamic strength counts as 0), and draws its own card only if it is strictly greater. An empty opponent deck counts as strength 0; an empty own deck fizzles.
- Nothing else reveals hidden information. There are no open tutors in the pool.

## Remove Pile, returns and shuffles

- There is one shared Remove Pile, and each card in it is still its owner's: **"your Remove Pile"** (Raccoon) and **"your opponent's Remove Pile"** (the legendary Raven) are the owner's cards in it. A **remove** is any card sent there from hand, deck or board and fires remove triggers; **Deathrattle** is the narrower case of a unit leaving the board.
- **"…instead"** would replace the removal (the card never reaches the Remove Pile, fires nothing); no card in the pool does it now. **"When this is removed, do X"** (Ember, Cockroach, Earthworm, Worm) is a real removal, then the effect: a Cockroach that goes back to hand still counts as removed (Hyena, Piranha, Vulture).
- **Shuffle events** are one per card shuffled into a deck (Raven's "shuffle 2 back" is two events). Incidental reorders don't count.
- **Skunk's bounce** returns the enemy unit to its owner's hand. It is not a removal (no Deathrattle, no remove trigger). The returned copy is locked, unplayable through its owner's next turn; other copies of the same card stay playable.
- **Rat** removes an adjacent enemy of any strength, then a random card from your hand goes to the Remove Pile (a remove, not a Deathrattle), target or not; an empty hand pays nothing.
- **Plague effects** that "remove everything from a crossroad" take the whole stack, both players' units, and fire every Deathrattle.

## Specific cards

- **Oxpecker** counts the fixed 30-card starting decklist: each copy with printed base strength 8 or more.
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
- **Dawn and Dusk resolve one at a time, in play order, each in full before the next.** One that an earlier one removed or buried does nothing. Dawn effects (Hungry among them) resolve before the delayed "at the start of your next turn" payouts (the Chipmunk, King Cobra's venom, Poison).

## A unit uncovered by a removal does not react to it

When removing the top unit of a stack uncovers the unit beneath, that unit was buried at the moment of the removal, so its "when … is removed" reactions (Queen Adira, Jackal, Vulture, Egg Eater, Eon) do not fire for it. Only units already visible when the removal happens react. Found in play (2026-09-28): a Tiger ate the Grizzly covering Queen Adira and she drew a card.

## The launch decks: the engine's reading (2026-10-08)

The calls made where the card workbench's text left room when its twelve decks went into the engine. Each is a first reading, for Martin to confirm or overturn in play.

Keywords:

- **Hungry N** is a Dawn effect: it eats in play order with your other Dawn effects. Only a top animal eats; a buried one is skipped. Fed or not is all or nothing: with fewer than N food it eats nothing and gets −N strength for good. An adjacent legendary Oxpecker feeds it, and an inked animal isn't Hungry until the ink wears off.
- **Titan** takes two actions, so it's offered only while two are left (an extra action from the Chipmunk counts). No free placement can play it ("play another animal", Remora, the Prince's twin).
- **Flee** happens before every other reaction to the cover: the animal is back in hand before an Apex Predator eats, King Theron removes, or the legendary Opossum takes it. Only an enemy cover sets it off, by placement or by roaming. The returned card is playable at once. The Zebra's coverer goes back to its owner's hand unless it has Armor.
- **Octopus ink** lasts until the start of the inking player's next turn. An inked animal has no keywords (printed or given), no anthem of its own (a dynamic strength counts as its printed 0), no aura for others, and none of its triggered effects (Roar-less reactions, Dawn, Dusk, "when this is removed"). It keeps its stored counters and still gets other animals' auras; a timer it already started still runs.
- **Auras that give a keyword** (Armadillo's Stealth, Capybara's Armor, the legendary Jellyfish's Poison) reach the top animal on each adjacent crossroad you control, never the source itself.
- **Grazing**: an animal grazes while it is the top of a crossroad that is a corner of a region its owner controls.

Cards:

- **Unnamed legendaries** show their species as their name until Martin names them in the workbench; their ids are fixed (`<deck>_legend_<species>`, `food_aggro_legend_repeat` and `_refill` for the two Rodents), so naming one later changes nothing else.
- **The legendary Cuckoo** must remove an adjacent animal of strength 4 or less if there is one (yours or a choosable enemy); "play another animal" is then mandatory if anything can be played.
- **The legendary Opossum** reacts to covers by either player, your own included, and to any ally it can see covered. It draws only when the removal happened (an Armor ally stays, and no card comes).
- **The legendary Sloth** runs each of your Dusk effects twice in a row; "At the end of your turn" effects are Dusk effects.
- **Praying Mantis** is a cost the player may decline; no removal, no cards.
- **Tarantula** eats a random adjacent ally (Armor excluded) and keeps the strength it showed then, for good.
- **Sea Turtle** lays on a random adjacent empty crossroad (Dusk asks nothing); **Sunfish** lets the player choose.
- **"An ally was removed this turn"** (Piranha, Vulture) and **"your animals removed this turn"** (Hyena) count your animals leaving the board this turn, whoever removed them; discards from hand don't count.
- **City Spider** catches animals of either side, including tokens, fills and roaming animals that arrive beside it.
- **Earthworm**: the two Worms land on its crossroad only while it is empty or yours; under an enemy there is no room and none appear.
- **Clarion's** free roam is for a Canine only, one per Clarion each turn, spent before an action.
- **Jackal's** flanker must be another of your Canines, not the Jackal itself.
- **Street Dog** picks another ally with Roam anywhere, gives it +2, then it roams for free under the Roam rules (it must be connected and not have roamed this turn). That roam can't take a den.
- **African Wild Dog** draws for a cover by placement or by roaming.
- **Serval** sets the strength by storing the difference: later buffs and auras count on top of the 1.
- **Leopard** (Cats) changes placements only, not roams; an Apex Cat landing is a placement.
- **The legendary Piranha** counts the Fish you control now, itself included; it changes placements only.
- **Swordfish** removes that many different random adjacent enemies (Stealth doesn't hide from random; Armor stays). **Barracuda** counts itself among your Fish.
- **The repeat legend** (food aggro) repeats the plain Roar of each adjacent allied Rodent, in crossroad order; a Roar that depends on how it was placed (Lynx's) isn't repeated.
- **The legendary Squirrel** loses all your food at once; its 2-turn timer is the Squirrel's (covering pauses it, removing it loses the stake, a return to hand restarts nothing). It pays three times the food it took.
- **The mimic Octopus** becomes the copied card for good (removed, it goes to the Remove Pile as the copy) with its stored counter; it may copy an ally or an enemy it may choose. Nothing of a Roar happens.
- **Greywhisker's** "play another animal" is mandatory if able; the discard is the player's choice.
- **Hare** counts the animals played from your hand this turn, itself included.
- **Mole, Dormouse and Macaque** count the hand after the card that roars has left it.
- **Grizzly Bear** in hand doesn't count itself (it shows the strength it will have when played).
- **The legendary Butterfly** evolves only in hand and only on a gain: each gain moves it one stage, whatever its size; it keeps every point gained; stage 5 (Monarch) is the last. The stage shows as the card itself (Caterpillar, Chrysalis, Butterfly, Monarch), not as a badge on the art yet.
- **The Caterpillar** becomes the pool's Butterfly (strength 2) and keeps its counter.
- **The Eagles**: the legendary Eagle brings its mate whenever it enters your hand (a draw, a Scout, a steal, a return; the opening hand once the mulligans are done), one mate at a time. A buff to either while both are in hand gives the other the same. The mate never brings the Eagle back.
- **Orangutan's** copy keeps the original's counter. **Baboon** (common): the player picks two different cards; **Baboon** (legendary): two random ones. **Stork**: two different younglings.
- **Gorilla** reads its strength as it lands; **Anteater** gains the drawn card's strength as it would be played now.
- **Mocha** removes every enemy adjacent to any of your top animals, itself included; Armor stays.
- **The legendary Zebra** counts different cards among the Hoofed allies adjacent to it; enemies never count (Martin, 2026-10-08).
- **Cape Buffalo** removes an enemy sitting directly on top of one of your Hoofed animals.
- **The legendary Wildebeest and Boar** move each region's food by 5 (each copy counts; a region never produces less than nothing).
- **The legendary Giraffe** shows its controller the opponent's hand face up in the client; the bots don't use it.
- **Great White Shark** has Reach 3 after any animal, of either side, left the board this turn.
- **Cuckoo's** eggs count as the Cuckoo player's shuffles (their Rattlesnake grows, not the opponent's).
- **Opossum** (the pool's) must return an adjacent ally if one can be returned (Armor can't).
