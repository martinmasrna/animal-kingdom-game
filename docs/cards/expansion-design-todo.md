# Expansion Card Design — To-Do

Working backlog for growing the card pool beyond the initial 14 designs per archetype. Nothing
in this document is locked or canonical until reviewed. Existing deck files remain the source of
truth for the launch packages.

The single candidate inventory is [`card-candidates.md`](card-candidates.md), organized only by
rarity. This document retains the design reasoning and module context that produced those rows;
it is not a separate candidate list. If wording or numbers differ, preserve both as unresolved
variants in the consolidated inventory.

The larger pool should force real deckbuilding decisions. New cards should create sidegrades,
subpackages, and cross-archetype possibilities—not simply replace the weakest card in every
premade list.

## Design guardrails

- [ ] **Non-negotiable no-mana calibration:** every card costs one card and the same placement
  action. Low strength is a drawback, never a lower price. Start every ground-unit design from
  Lion (STR 7) and every Flight design from Eagle (STR 5), then exchange body strength only for
  effect value that matters immediately or reliably.
- [ ] Rarity does not pay for a weak rate. It changes copy count, consistency, and how singular a
  gameplay pattern may be; a rare STR 3 with a modest effect is still a bad card.
- [ ] Price conditions by reliability. “If adjacent to a Landmark” or “if an Egg hatched” cannot
  repay several missing strength unless the successful effect is correspondingly large.
- [ ] Price delay twice: the player gives up immediate board presence and the opponent receives a
  window to disrupt the payoff. A STR 0 Egg/Landmark that later produces one ordinary body is
  generally worse than playing that body immediately.
- [ ] Count free placements and tokens as action economy. One card creating two bodies, or moving
  a card directly from deck to battlefield, is powerful even when the individual bodies are small.
- [ ] Build toward at least **20–24 plausible cards per established archetype** before considering
  the first constructed-card-pool milestone.
- [ ] Preserve the 30-card deck limits: at most 4 legendary and 8 rare cards. Extra designs are
  choices, not permission to increase those limits.
- [ ] Avoid printing several unconditional body-plus-card-advantage cards. In a place-or-draw
  economy, a body that replaces itself is already premium.
- [ ] Avoid unrestricted extra placements near an enemy HQ. Every chaining effect needs an
  instant-capture audit.
- [ ] Prefer cards that are useful in two homes. Tags should suggest archetypes rather than act
  as hard classes.
- [ ] Keep Cats expansion cards conditional or narrow until the post-nerf shell is proven fair.
- [ ] Treat food values as placeholders until the shared food scale is re-tested.
- [ ] Promote a new keyword only after at least three cards want the exact same rules object.
- [ ] Run a species-collision check before flavor-lock. Candidate names below are mechanical
  handles, not promises.

### Required rate check for every candidate

- [ ] **Body ledger:** compare ground cards to Lion 7 and Flight cards to Eagle 5. Record exactly
  how much strength the effect is buying or adding.
- [ ] **Card ledger:** playing a card subtracts one card; the alternative Draw action adds two.
  “Draw 1” replaces the played card but does not refund the placement action. A STR 0 card that
  draws only one card later has lost both tempo and card velocity.
- [ ] **Action ledger:** count every free placement, token, move, and deck-to-board effect.
  Playing a card from deck is both selection and a saved future placement action.
- [ ] **Delay ledger:** compare the payoff to what an immediate Lion/Eagle would have accomplished
  during every opponent turn in the waiting window.
- [ ] **Floor/ceiling:** price the card for its common unsuccessful state, not only the screenshot
  where all tribal conditions are active.
- [ ] **Closest-card test:** reject a candidate that is strictly or practically dominated by an
  existing card—or that makes an existing card obsolete without creating a meaningful deckbuilding
  tradeoff.

---

## 1. Expansion modules for the seven established archetypes

### 1.1 Cats — conditional sidegrades

Cats already possess the strongest collection of unconditional bodies. Their expansion should
open positional and Landmark builds without adding more generic removal.

- [ ] **Fishing Cat** — Cat · STR 4 · Common
  `Battlecry: if this is adjacent to a Landmark, draw 1 card.`
  A build-around cantrip that is below rate without a contested Landmark.

- [ ] **Sand Cat** — Cat · STR 5 · Common
  `Has +3 strength while no other friendly unit is adjacent to this.`
  Rewards spreading across regions rather than forming the usual Cat death-ball.

- [ ] **Margay** — Cat · STR 7 · Common
  `May be placed on an empty crossroad adjacent to any Cat you control, ignoring connection.`
  Trades Cougar's ability to contest occupied crossroads for a full Lion-sized body.

- [ ] **Clouded Leopard** — Cat · STR 7 · Rare
  `Camouflage.`
  Proposed Camouflage definition: Stealth until this covers an enemy unit. It trades Black
  Panther's permanent protection for a larger pre-attack body.

- [ ] **Ocelot** — Cat · STR 6 · Rare
  `Battlecry: if this covers an enemy, return one friendly Cat buried beneath it to your hand.`
  Opens a stack-recovery build and rewards deliberate friendly stacking. Needs a ruling that
  effects may name a buried card without making buried cards generally targetable.

- [ ] **Sable, the Solitary** — Cat · STR 5 · Legendary candidate
  `At the end of your turn, if no other friendly unit is adjacent to this, draw 1 card.`
  A slow isolated-value engine. Test carefully: recurring draw plus Cat mobility could still
  make this an automatic inclusion.

### 1.2 Egg Control — hatching and incubation

Build two alternatives to the current draw/shuffle engine: delayed board hatching and Egg
protection. These cards should remain vulnerable to covering.

- [ ] **Turtle Egg** — Egg · STR 0 · Common
  `Fragile. Hatch 1 — play two Turtle Hatchling tokens (STR 4) on this crossroad and an
  adjacent empty crossroad.`
  The delayed payoff must create both total strength and board width; one ordinary STR 5 body
  would be dramatically worse than playing Lion immediately.

- [ ] **Crocodile Egg** — Egg · STR 0 · Rare
  `Fragile. Hatch 2 — play a Crocodile token (Lizard, STR 8) on this crossroad. Its
  Battlecry removes an adjacent enemy of strength 4 or less.`
  A delayed premium body plus interaction. Verify that a covered Egg cannot hatch.

- [ ] **Cuckoo** — Bird · STR 3 · Rare
  `Flight. Battlecry: you may play an Egg from your hand on an empty crossroad adjacent to an
  enemy unit.`
  Seeds an Egg behind enemy lines but cannot cover or capture with the bonus placement.

- [ ] **Malleefowl** — Bird · STR 5 · Rare
  `At the end of your turn, incubate one adjacent Egg.`
  “Incubate” would advance one Hatch timer by one owner-turn. This is the cleanest reason to
  formalize an incubation operation.

- [ ] **Emperor Penguin** — Bird · STR 7 · Common
  `Adjacent friendly Eggs cannot be chosen by enemy abilities.`
  Covering remains valid, so the protection does not erase the Egg archetype's main weakness.

- [ ] **King Cobra** — Snake · STR 4 · Rare
  `Battlecry: envenom an adjacent enemy unit.`
  Gives the control half active interaction without another immediate removal effect.

- [ ] **Vulture / Crow / other Bird (identity TBD)** — Bird · STR 3 · Rare
  `Flight. Battlecry: draw 1 card; if an enemy unit was removed this turn, draw 2 cards
  instead.`
- [ ] Decide whether this remains Vulture, becomes Crow/Rook/another Bird, or whether Vulture is
  reserved for a separate “eat” or scavenging design.

- [ ] **Nesting Ground** — Landmark · STR 0 · Rare
  `Fragile. Immovable. At the end of your turn, incubate every adjacent Egg.`
  It can accelerate multiple Eggs immediately; incubating one Egg starting next turn would not
  repay a card, a placement action, and a STR 0 board slot.

### 1.3 Colony — earlier texture and mixed-insect builds

The current package asks Colony to reach a large board before many cards become live. Expansion
cards should create playable early turns and alternative engines, not simply add more “control
five units” payoffs.

- [ ] **Leafcutter Ant** — Colony · STR 3 · Common
  `Battlecry: gain 3 food for each other friendly Colony unit.`
  Scales earlier than the legendary Queen but remains a poor opening play.

- [ ] **Honeypot Ant** — Colony · STR 2 · Common
  `Deathrattle: gain 16 food.`
  Connects Colony to sacrifice decks and gives opponents a reason not to remove every token
  automatically.

- [ ] **Weaver Ant** — Colony · STR 5 · Rare
  `Battlecry: move an adjacent Colony unit to an adjacent empty crossroad.`
  Repairs swarm geometry without creating an additional unit.

- [ ] **Rhinoceros Beetle** — Insect · STR 2 · Common
  `Has +1 strength for each other friendly Colony or Insect unit.`
  Seeds a broader bug deck without making every insect a Colony caste.

- [ ] **Aphid** — Insect · STR 3 · Common
  `Battlecry: gain 4 food. Whenever you play another Colony or Insect unit adjacent to this,
  gain 2 food.`
  A fragile mixed-tag engine; once-per-turn may be necessary if placement chains become
  excessive.

- [ ] **Termite Mound** — Landmark · STR 0 · Common
  `Fragile. Immovable. Battlecry: draw a random Colony unit from your deck. Adjacent Colony
  units have +2 strength.`
  A local formation payoff that does not count toward Colony unit thresholds.

- [ ] **Royal Jelly** — Landmark · STR 0 · Rare
  `Fragile. At the start of your next turn, remove this and play a random Queen from your deck
  on this crossroad.`
  The delay exchanges Royal Jelly for a filtered free placement, not merely one replacement
  card. It forces a deckbuilder to decide how many Queens are worth including.

### 1.4 Ramp — more routes upward, not more finishers

Ramp already has enough giant payoff bodies. Add competing engines, medium-cost bodies, and
Landmarks that make the opponent interact with its setup.

- [ ] **Beaver** — STR 5 · Rare
  `At the end of your turn, if this is adjacent to a Landmark, gain 5 food.`
  Recurring ramp that asks for a two-card board rather than carrying Immovable itself.

- [ ] **Bison** — Megafauna · STR 9 · Common
  `Costs 5 food to play.`
  STR 8 for 10 food would be worse than Lion in the turns that matter; the medium rung must buy
  a meaningful body increase.

- [ ] **Gaur** — Megafauna · STR 9 · Rare
  No effect.
  A clean large body that tests whether raw strength can be a legitimate rare choice.

- [ ] **Honeyguide** — Bird · STR 3 · Common
  `Flight. Battlecry: gain 6 food; if you control a Bear or Colony unit, gain 4 more.`
  A bridge card between Ramp, Colony, and future mixed-food decks.

- [ ] **Moose** — Megafauna · STR 6 · Common
  `Has +2 strength while adjacent to a Landmark.`
  Turns vulnerable infrastructure into a positional reason to contest the board.

- [ ] **Baobab Tree** — Landmark · STR 0 · Rare
  `Fragile. Immovable. At the end of each of your turns, gain 8 food.`
  It pays once on the placement turn and remains interactable by covering. Test against Fig
  Tree's one-shot 20-food benchmark.

- [ ] **Cave** — Landmark · STR 0 · Rare
  `Fragile. Immovable. Battlecry: draw a random Bear from your deck. Your Bears cost 5 less
  food to play.`
  Specify that multiple Caves do not stack. The filtered draw replaces the spent Cave card;
  the ongoing discount must justify spending a placement action on no body.

- [ ] **Salt Lick** — Landmark · STR 0 · Common
  `Fragile. At the start of your next turn, give all friendly units +2 strength, then remove
  this.`
  A temporary setup cost for a permanent wide-board payoff; also attractive to Colony.

### 1.5 Food sacrifice — value, fodder, and alternate outlets

Expand toward a fair sacrifice-value deck as well as the all-in OTK. Do not add more 40-food
effects until Gazelle is understood.

- [ ] **Dung Beetle** — Insect · STR 3 · Common
  `Battlecry: gain 4 food. Deathrattle: gain 8 food.`
  Splits its value across entry and sacrifice.

- [ ] **Mayfly** — Insect · STR 3 · Common
  `Battlecry: draw 1 card. Deathrattle: draw 1 card. At the end of your next turn, remove this.`
  Self-expiring fodder that guarantees eventual value without requiring an outlet.

- [ ] **Pelican** — Bird · STR 4 · Rare
  `Flight. Battlecry: remove another friendly unit; draw 2 cards.`
  A mobile sacrifice outlet. “Another” prevents it from paying with itself.

- [ ] **Carrion Beetle** — Insect · STR 4 · Common
  `Battlecry: gain 4 food. The first time each turn another friendly unit is removed, gain 4
  food.`
  A fair, capped engine that can appear in Colony token lists.

- [ ] **Tarantula** — Arachnid · STR 4 · Rare
  `Deathrattle: play up to two Spiderling tokens (Arachnid, STR 2) on adjacent empty
  crossroads.`
  Converts one sacrifice into width rather than direct food.

- [ ] **Carcass** — Landmark · STR 0 · Common
  `Fragile. Battlecry: gain 8 food. The first time each turn a unit adjacent to this is
  removed, gain 4 food.`
  A contested scavenging site usable by either sacrifice or control shells.

- [ ] **Vulture** — Bird · STR 4 · Rare, currently shelved
  `Flight. Whenever a card is removed, gain 5 food.`
  Keep available for the larger pool, but test a once-per-turn cap before release.

### 1.6 Aggro — alternative rush packages

Aggro's extra cards should split into Rodent chaining, aerial pressure, and empty-crossroad
infiltration. Avoid adding more unconditional removal.

- [ ] **Prairie Dog** — Rodent · STR 3 · Common
  `Battlecry: play one more Rodent from your hand.`
  A narrower Jerboa that enables a dedicated Rodent build.

- [ ] **Gecko** — Lizard · STR 7 · Common
  `May be placed on an empty crossroad adjacent to an enemy unit, ignoring connection.`
  Reach without covering, removal, or direct HQ capture.

- [ ] **Mole** — Rodent · STR 6 · Common
  `Burrow.`
  Proposed Burrow definition: ignore connection only when placing onto an empty crossroad.

- [ ] **Starling** — Bird · STR 2 · Common
  `Flight. Battlecry: if you control another unit with Flight, play one more unit with Flight
  from your hand.`
  High burst-risk. Run an explicit two-card/three-card HQ-capture search before approving.

- [ ] **Bombardier Beetle** — Insect · STR 5 · Rare
  `Battlecry: return an adjacent enemy of strength 4 or less to its owner's hand.`
  A smaller, capped alternative to Skunk without the one-turn lock.

- [ ] **Springhare** — Rodent · STR 5 · Rare
  `Burrow. Battlecry: if played adjacent to the opponent's headquarters, draw 1 card.`
  Combines Cheetah's reward with empty-only infiltration and a much smaller body.

- [ ] **New cover-retaliation legendary** — STR 4 · Legendary
  `Flight. The first time an enemy unit covers this, return that enemy unit to its owner's
  hand.`
  Already locked in the balance to-do; species and name remain open.

### 1.7 Canines — hand-buff, movement, and pack protection choices

Use distinct wild canid species. Domestic dog breeds are one species and should not silently
evade the one-species rule.

- [ ] **Bat-eared Fox** — Canine · STR 4 · Common
  `Battlecry: look at the top 3 cards of your deck; draw a Canine and put the rest on the
  bottom.`
  “Draw a Canine” means choose among the revealed cards, not search the full deck.

- [ ] **Maned Wolf** — Canine · STR 6 · Common
  `May be placed on an empty crossroad adjacent to any Canine you control, ignoring connection.`
  A pack-positioning tool rather than another buff.

- [ ] **Raccoon Dog** — Canine · STR 3 · Common
  `Battlecry: draw 1 card. Deathrattle: shuffle this into your deck.`
  The immediate draw repays the weak body; playing dead becomes slow recursion and also crosses
  into Egg Control's shuffle package.

- [ ] **Fennec Fox** — Canine · STR 5 · Rare
  `The first time each turn this gains strength, you may move it to an adjacent empty
  crossroad.`
  Turns buffs into board reach without granting an extra placement.

- [ ] **Ethiopian Wolf** — Canine · STR 5 · Rare
  `Battlecry: if this has a strength counter while in your hand, draw 1 card.`
  Makes hand buffs a deckbuilding commitment rather than incidental upside.

- [ ] **Culpeo** — Canine · STR 5 · Rare
  `Battlecry: give one Canine in your hand +2 strength.`
  A focused alternative to Red Wolf's wide +1.

- [ ] **Hachiko, the Faithful** — Canine · STR 5 · Legendary candidate
  `The first time each turn another friendly Canine would be removed, return it to your hand
  instead.`
  A defensive pack build. Check whether using a real famous individual is desirable before
  flavor-lock, and audit replacement effects against Deathrattles.

#### Dog/Canine copy-scaling candidate

- [ ] **Dog/Canine identity TBD** — Canine · STR 3 · Common
  `Battlecry: give +3 strength to every other copy, wherever they are.`
- [ ] Decide whether this reworks the existing Dog or belongs to another Canine.
- [ ] Define “wherever,” including whether it covers deck, hand, battlefield, and/or Remove Pile.
- [ ] Account for its dependence on multiple copies when designing the test deck, as with
  Lemming.

### 1.8 Movement and mimicry candidates

- [ ] **Kangaroo** — Marsupial · STR and rarity TBD
  `Battlecry: Move 1.`
  Proposed scope: move itself or an ally. Exact targeting and destination rules remain open.

- [ ] **Parrot** — Bird · STR TBD · rarity TBD
  Original concept: `Become a copy of the last Common unit your opponent played.`
- [ ] **Legendary Parrot** — named Bird · STR TBD · Legendary
  Original concept: `Become a copy of the last unit your opponent played.`
- [ ] Also compare the full-copy proposal with a narrower mimic alternative:
  `Flight. Battlecry: repeat the Battlecry of the last Common unit your opponent played.`
  Possible animal fits include Parrot/Lyrebird for repetition and Mimic Octopus/cuttlefish for
  physical copying; no identity is selected.
- [ ] Do not assign power numbers until copy timing is settled: copying before placement may fire
  the copied Battlecry, while becoming a copy after its own Battlecry normally would not.

---

## 2. Candidate archetype incubators

These are broader card-pool directions, not eighth-through-eleventh premade decks. Prototype
small cross-compatible modules first; promote one to a full archetype only after its board play
is distinct from the current seven.

### 2.1 Dinosaur Hatch — delayed bodies without food ramp

**Identity:** protect vulnerable Eggs, accelerate Hatch timers, then win through large bodies.
Unlike Ramp, it spends time and board space rather than food. Unlike Egg Control, it converts
Eggs into units rather than cards and event-food.

Anchor candidates:

- [ ] **Dinosaur Egg** — Egg · STR 0 · Common
  `Fragile. Hatch 2 — play a random non-Legendary Dinosaur from your deck on this
  crossroad.`
- [ ] **Oviraptor** — Dinosaur · STR 3 · Common
  `Battlecry: draw a random Egg from your deck.`
- [ ] **Velociraptor** — Dinosaur · STR 5 · Common
  `Battlecry: if an Egg hatched this turn, draw 1 card.`
- [ ] **Protoceratops** — Dinosaur · STR 7 · Common
  No effect.
- [ ] **Triceratops** — Dinosaur · STR 7 · Rare
  `When an enemy covers an adjacent Egg, remove that enemy if its strength is 4 or less.`
- [ ] **Ankylosaurus** — Dinosaur · STR 8 · Rare
  `Cannot be returned to a hand.`
- [ ] **Archaeopteryx** — Bird/Dinosaur · STR 4 · Rare
  `Flight. Battlecry: incubate an adjacent Egg.`
- [ ] **Sue** — Dinosaur · STR 10 · Legendary candidate
  `Apex Predator. You may play this only if one of your Eggs has hatched this game.`
  A real named individual, but verify whether museum-specimen names fit the game's legendary
  tone.
- [ ] **Nesting Ground** — Landmark support from Egg Control.

Primary risks: snowballing free bodies, timers becoming bookkeeping-heavy, and a protected Egg
package that opponents cannot meaningfully disrupt.

### 2.2 Wetlands School — Fish, Amphibians, and formation movement

**Identity:** build formations around fragile aquatic Landmarks, relocate along empty crossroads,
and gain strength from nearby allies/enemies. This should play as positional midrange, not as a
second tribal anthem deck.

Anchor candidates:

- [ ] **Coral Reef** — Landmark · STR 0 · Rare
  `Fragile. Immovable. Battlecry: draw a random Fish from your deck. Your Fish have +2
  strength.`
- [ ] **Kelp Forest** — Landmark · STR 0 · Common
  `Fragile. Battlecry: draw a random Fish from your deck, then you may move a friendly Fish
  to an empty crossroad adjacent to this. Adjacent Fish have Stealth.`
- [ ] **Salmon** — Fish · STR 5 · Common
  `Battlecry: move another friendly Fish to an empty crossroad connected to your
  headquarters.`
- [ ] **Clownfish** — Fish · STR 6 · Common
  `Has Stealth while adjacent to a friendly Landmark.`
- [ ] **Remora** — Fish · STR 2 · Common
  `Has +6 strength while adjacent to a friendly unit with strength 6 or more.`
- [ ] **Great White Shark** — Fish · STR 5 · Rare
  `Has +2 strength for each adjacent enemy unit.`
- [ ] **Electric Eel** — Fish · STR 5 · Rare
  `Battlecry: an adjacent enemy has 0 strength until the end of your next turn.`
- [ ] **Axolotl** — Amphibian · STR 5 · Rare
  `The first time this would be removed, return it to this crossroad with base strength 1
  instead.`
- [ ] **Frogspawn** — Egg/Amphibian · STR 0 · Common
  `Fragile. Hatch 1 — play two Tadpole tokens (Amphibian, STR 4) on adjacent empty
  crossroads.`

Primary risks: map-independent “aquatic” flavor, too many live strength calculations, and token
width overlapping Colony.

### 2.3 Primate Toolmakers — Landmark value and tactical movement

**Identity:** Primates build around Landmarks, improve neighboring units, and rearrange the board.
Their strength comes from flexible sequencing rather than raw bodies.

Anchor candidates:

- [ ] **Capuchin** — Primate · STR 5 · Common
  `Battlecry: if adjacent to a Landmark, draw 1 card.`
- [ ] **Lemur** — Primate · STR 2 · Common
  `Battlecry: if you control another Primate, play another Primate from your hand.`
- [ ] **Howler Monkey** — Primate · STR 3 · Common
  `Battlecry: give all other Primates in your hand and battlefield +1 strength.`
- [ ] **Bonobo** — Primate · STR 5 · Common
  `Battlecry: move an adjacent friendly unit to an adjacent empty crossroad.`
- [ ] **Chimpanzee** — Primate · STR 4 · Rare
  `Battlecry: give an adjacent friendly unit +3 strength.`
- [ ] **Mandrill** — Primate · STR 5 · Rare
  `Your other Primates have +2 strength.`
- [ ] **Gorilla** — Primate · STR 6 · Rare
  `Adjacent enemy units have −2 strength.`
- [ ] **Orangutan** — Primate · STR 6 · Rare
  `Battlecry: return a Landmark from the Remove Pile to your hand.`
- [ ] **Kanzi** — Primate · STR 4 · Legendary candidate
  `Battlecry: repeat the Battlecry of another adjacent Primate.`
  Copying effects is dangerous even when tribe-restricted; enumerate every Primate Battlecry
  before approval.
- [ ] **Tool Cache** — Landmark · STR 0 · Common
  `Fragile. When you play a Primate adjacent to this, remove this and draw 3 cards.`

Primary risks: copied Battlecries, permanent-buff overlap with Canines, and Landmarks becoming
solitaire engines rather than contested positions.

### 2.4 Venom Control — delayed answers with visible counterplay

**Identity:** mark a visible unit for delayed removal. The opponent gets one turn to cover it,
move it, return it, or otherwise break the condition. This creates control decisions without
another family of immediate removal Battlecries.

Anchor candidates:

- [ ] **Cobra** — Snake · STR 3 · Rare
  `Battlecry: envenom an adjacent enemy.`
- [ ] **Komodo Dragon** — Lizard · STR 5 · Rare
  `Battlecry: envenom an adjacent enemy of strength 5 or less.`
- [ ] **Scorpion** — Arachnid · STR 3 · Common
  `The first enemy unit that covers this becomes envenomed.`
- [ ] **Poison Dart Frog** — Amphibian · STR 4 · Common
  `Deathrattle: envenom an adjacent enemy.`
- [ ] **Blue-ringed Octopus** — Cephalopod · STR 3 · Rare
  `Stealth. Battlecry: envenom an adjacent enemy of strength 5 or less.`
- [ ] **Mongoose** — STR 5 · Common
  `Battlecry: clear Venom from an adjacent friendly unit; otherwise remove an adjacent enemy
  Snake of any strength.`
- [ ] **Antivenom Grove** — Landmark · STR 0 · Common
  `Fragile. Battlecry: clear Venom from all friendly units and draw 2 cards. Adjacent
  friendly units cannot become envenomed.`

Primary risks: delayed-effect memory, unclear behavior when the marked card becomes buried, and
Venom becoming functionally identical to immediate removal against bots.

### 2.5 Warren/Burrow — breeding and empty-crossroad infiltration

**Identity:** multiply small Rabbits/Rodents over time and use Burrow to occupy open ground behind
the front. The package races for regions and connection but struggles to cover defenders.

Anchor candidates:

- [ ] **Rabbit** — Rabbit · STR 3 · Common
  `At the start of each of your turns, draw a random Rabbit from your deck.`
- [ ] **Hare** — Rabbit · STR 6 · Common
  `Burrow.`
- [ ] **Prairie Dog** and **Mole** — cross over from the Aggro module.
- [ ] **Wombat** — Marsupial · STR 8 · Rare
  `Burrow. Cannot cover enemy units.`
- [ ] **Pika** — Rabbit · STR 5 · Common
  `Battlecry: if played by Burrow, gain 8 food.`
- [ ] **Warren** — Landmark · STR 0 · Rare
  `Fragile. At the end of your turn, play a Rabbit token (Rabbit, STR 3) on an adjacent
  empty crossroad.`
  This must be optional when no empty destination exists and needs a runaway-width test.
- [ ] **Burrow Owl** — Bird · STR 4 · Rare
  `Flight. Your adjacent units with Burrow have +2 strength.`

Primary risks: automated token growth, unconnected units creating confusing pseudo-fronts, and
overlap with Aggro/Colony width.

---

## 3. Landmark queue

Landmarks should remain a minority of the total pool, but two cards are not enough to establish
meaningful deckbuilding. Prioritize Landmarks that create contested board positions rather than
safe delayed spells.

- [ ] Prototype first: **Nesting Ground, Termite Mound, Baobab Tree, Coral Reef, Carcass,
  Cave, Salt Lick**.
- [ ] **Kelp Forest** — local Stealth for Fish.
- [ ] **Fallen Log** — `Fragile. When this leaves the battlefield, play two Insect tokens
  (STR 3) on adjacent empty crossroads.`
  Determine whether a Landmark leaving play should use a separate trigger name from Deathrattle.
- [ ] **Fossil Bed** — `Fragile. At the start of your next turn, remove this and play a random
  non-Legendary Dinosaur from your deck on this crossroad.`
- [ ] **Cut Mud Wall.** Bounce immunity on a STR 0 card does not repay its card and placement
  action; revisit only as a rider on a broader Landmark.
- [ ] Do not make Immovable a default Landmark keyword. Bounceable Landmarks create useful
  interaction and allow some designs to be replayed; each card should justify immunity.
- [ ] Decide whether an Apex Predator “destroys” or “razes” a Landmark rather than “eats” it.
  Keep the mechanics identical unless balance testing demands otherwise.

## 4. Egg queue

Eggs can support multiple archetypes if their outcomes differ: cards, units, tokens, disruption,
or delayed food. Avoid making every Egg “wait two turns, draw two.”

- [ ] Prototype first: **Turtle Egg, Crocodile Egg, Dinosaur Egg, Frogspawn**.
- [ ] **Spider Egg Sac** — Egg/Arachnid · STR 0 · Common
  `Fragile. Deathrattle: play two Spiderling tokens (Arachnid, STR 3) on adjacent empty
  crossroads.`
- [ ] **Mantis Ootheca** — Egg/Insect · STR 0 · Common
  `Fragile. Hatch 1 — play up to three Mantis Nymph tokens (Insect, STR 2) on adjacent empty
  crossroads.`
- [ ] **Cut Shark Egg Case for now.** A single delayed body needs a premium effect or action
  advantage; “wait two turns for a large vanilla Fish” is not a sufficient design.
- [ ] **Decoy Egg** — Egg · STR 0 · Common
  `Fragile. Deathrattle: draw 3 cards.`
  Deliberately simple glue for sacrifice and Egg lists.
- [ ] Test whether Egg cards should carry both `Egg` and their future-animal tag. Multi-tagging
  improves discoverability but may let Bird/Snake filtered draws find unhatched Eggs.

## 5. Selection order

- [ ] First prototype wave: Burrow, Secretarybird replacement, one new Egg that hatches a body,
  one incubation card, Baobab Tree, Termite Mound, Dung Beetle, and one movement card.
- [ ] Second prototype wave: Camouflage, Venom package, Fish/Landmark formation package.
- [ ] Third prototype wave: tokens, Dinosaur Hatch, Primate Battlecry copying.
- [ ] Before any wave becomes canonical, build at least two competing 30-card lists using the
  enlarged pool. A new card has succeeded only if plausible lists sometimes omit it.
