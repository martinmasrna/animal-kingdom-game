# Card Candidates — 100 New Designs

> A brainstorm pool to cherry-pick from. **Not** a finished set, and deliberately **not** fitted to any specific deck or archetype.
> Two design sources: **flavor-first** (animal → effect) and **mechanic-first** (effect → animal). ~half each.

## How to read an entry

```
**Name** | Tag | Str N | Rarity
Effect text (house voice).
  ↳ Balance: anchor to an existing card + the delta. · Source: flavor-first | mechanic-first · ⚙ new mechanic: … (engine cost)
```

**Baselines:** vanilla ground = **Lion 7**, vanilla flight = **Eagle 5** (Flight ≈ +2 strength). Sub-4 bodies are nearly combat-irrelevant in a covering game, so low strength buys generous effects; high strength must be gated.

**Balancing rubric:** *below baseline* → repaid by a strong effect; *above baseline* → gated by **(a)** rarity, **(b)** a playability condition, or **(c)** a drawback. The "**Costs N food to play**" lever is cheap, so it is used on only **4 of 100** cards. Novel effects with no clean anchor are tagged `(sim-tune)` for the M3 simulator.

**Voice key:** `Battlecry:` = on place · `Deathrattle:` = on leaving the board · `Has +X` = live anthem (vanishes with the source) · `Give +X` = permanent counter (persists) · keywords (`Flight`, `Immovable`, `Fragile`, `Apex Predator`) stand alone.

**New tags introduced here** (labeled on first use): `Primate`, `Insect` (non-eusocial bugs, distinct from `Colony`), `Amphibian`, `Marsupial`, `Cetacean`, `Dinosaur`. New mechanics are summarized in [Appendix A](#appendix-a--new-mechanics-introduced). Collision-check list in [Appendix C](#appendix-c--already-used-animals-collision-check).

---

## 1 · Vanilla & stat-line bodies

**Ox** | — | Str 8 | Rare
Vanilla.
  ↳ Balance: Lion +1; the single point of raw strength over baseline is paid for by Rare. · Source: mechanic-first (fills the clean "vanilla 8" slot).

**Gaur** | Megafauna | Str 9 | Rare
Vanilla. (The largest wild bovine.)
  ↳ Balance: +2 over baseline with no rider → gated by Rare + scarcity. Anchor: Matriarch Elephant (8 + Immovable, Rare); Gaur trades the keyword for a point of body. · Source: flavor-first.

**Tapir** | — | Str 5 | Common
Vanilla.
  ↳ Balance: deliberately plain colorless 5-body — a covering-game 5 is a usable wall even naked. Curve filler. · Source: mechanic-first.

**Warthog** | — | Str 6 | Common
Battlecry: gain 2 food.
  ↳ Balance: Wild Boar is the anchor (5 + gain 3); Warthog shifts a point of food into a point of body. · Source: flavor-first.

**Giraffe** | — | Str 5 | Common
May cover enemy units of equal strength (long reach).
  ↳ Balance: Honey Badger (3, cover ≤equal) is the anchor; Giraffe pays its covering-rule break with a bigger but still-Common body. · Source: flavor-first.

**Bison** | Megafauna | Str 8 | Common
Costs 10 food to play.
  ↳ Balance: a Common body above baseline, gated by a modest food cost. Anchor: Elephant (8, Immovable, costs 20) — Bison is half the cost for no keyword. · Source: mechanic-first (wanted a food-gated Common beater) · *food-cost card 1 of 3*.

---

## 2 · Removal — targeted, AoE, on-cover, retaliatory

**Secretary Bird** | Bird | Str 4 | Rare
Flight. Battlecry: remove an adjacent enemy of strength 4 or less.
  ↳ Balance: Leopard (5/≤4) anchor; Secretary Bird adds Flight and pays a point of body for it. · Source: flavor-first.

**Mongoose** | — | Str 3 | Common
Battlecry: remove an adjacent enemy Snake of any strength; otherwise remove an adjacent enemy of strength 3 or less.
  ↳ Balance: Gray Wolf (4/≤3) anchor; smaller body buys the anti-Snake tribal upside. · Source: flavor-first.

**Orca — "Granny"** | Cetacean *(new tag)* | Str 8 | Legendary
Battlecry: remove an adjacent enemy of any strength.
  ↳ Balance: uncapped single-target removal is premium → big body + Legendary (a named matriarch). Anchor: Tiger (7/≤5, Rare) pushed up for the missing cap. · Source: flavor-first.

**Goshawk** | Bird | Str 4 | Common
Flight. Battlecry: remove an adjacent enemy of strength 2 or less.
  ↳ Balance: a cheap flying answer — Secretary Bird's lower-rarity cousin (smaller cap). · Source: mechanic-first (wanted a Common flying-removal body).

**Praying Mantis** | Insect *(new tag)* | Str 3 | Rare
Battlecry: remove an adjacent enemy of strength equal to or less than this unit's strength.
  ↳ Balance: removal scales with its own (buffable) body, like Gray Wolf in the buff shell. Low base, Rare for the open-ended cap. · Source: mechanic-first (wanted removal that scales with its own strength).

**Stingray** | Fish | Str 3 | Common
Deathrattle: remove the unit that removed this.
  ↳ Balance: Pufferfish (on-cover trap) anchor; Stingray punishes its killer by *any* removal method, not just covering. · Source: mechanic-first (wanted a retaliation body; the barbed sting fit).

**Trapdoor Spider** | Arachnid | Str 2 | Common
When an enemy places a unit on an adjacent crossroad, remove it if its strength is 2 or less.
  ↳ Balance: Hippopotamus (6, removes adjacent placements ≤3) anchor; the Common ambush version with a small body and lower cap. · Source: mechanic-first (wanted a cheap ambush-removal body).

**Honey Buzzard** | Bird | Str 3 | Rare
Flight. Battlecry: remove all adjacent enemy Colony or Insect units of any strength; otherwise remove one adjacent enemy of strength 2 or less.
  ↳ Balance: Rhinoceros (AoE ≤5) anchor; conditional sweep that is huge against swarm decks, modest otherwise. · Source: mechanic-first (wanted an anti-swarm conditional sweeper).

**Stoat** | — | Str 3 | Common
Battlecry: remove an adjacent enemy of strength 2 or less.
  ↳ Balance: the most basic targeted-removal common — Gray Wolf minus a point of cap and body. · Source: mechanic-first (curve-filling cheap removal).

**Roadrunner** | Bird | Str 3 | Common
Battlecry: remove an adjacent enemy Snake or Lizard of any strength.
  ↳ Balance: narrow but uncapped tribal removal on a clean Common body. Anchor: Mongoose. · Source: flavor-first.

**Shrike** | Bird | Str 2 | Rare
Flight. Battlecry: remove an adjacent enemy of strength 3 or less; it cannot be returned to a hand or deck (impaled).
  ↳ Balance: Secretary Bird anchor; trades body for Flight + an anti-recursion rider that shines vs Egg/Opossum decks. · Source: flavor-first · ⚙ new mechanic: *exile-style removal* (skip the discard/return path — a flag on the remove op).

---

## 3 · Card draw & selection

**Meerkat** | — | Str 2 | Common
Battlecry: draw 1 card.
  ↳ Balance: mirrors Cottontail (2 + draw 1), a proven on-curve common. · Source: flavor-first.

**Magpie** | Bird | Str 2 | Common
Flight. Battlecry: draw 1 card.
  ↳ Balance: Cottontail + Flight; the flying upside keeps it at a token body. Anchor: Owl (2, flight, look-3). · Source: flavor-first.

**Bloodhound** | Canine | Str 3 | Common
Battlecry: look at the top 5 cards of your deck; draw a unit of your choice, put the rest on the bottom.
  ↳ Balance: Owl (look-3) anchor; digs deeper but trades Flight for the bigger ground body. · Source: mechanic-first (wanted deep deck selection).

**Truffle Pig** | — | Str 3 | Common
Battlecry: look at the top 4 cards of your deck; draw 1, put the rest on the bottom.
  ↳ Balance: card *selection*, not raw advantage. Owl (look-3, flight) anchor — one deeper, no Flight, bigger body. · Source: mechanic-first (wanted a deck-dig effect; the truffle pig fit).

**Blue Jay** | Bird | Str 2 | Rare
Flight. Battlecry: draw 2 cards, then put 1 card from your hand on top of your deck.
  ↳ Balance: Raven (2, flight, draw 2 then shuffle 2 back) anchor; Blue Jay is the gentler net-+1-with-setup version (cache one back on top). · Source: mechanic-first (wanted a draw-2-and-cache filterer).

**Beagle** | Canine | Str 2 | Rare
Battlecry: search your deck for a unit of strength 3 or less and put it into your hand.
  ↳ Balance: Octopus (4, tutor *any* unit, Legendary) anchor; restricting the tutor to small units drops it to a Rare 2-body. · Source: mechanic-first (wanted a consistency tutor; the scent-hound fit).

**Parrot** | Bird | Str 4 | Rare
Flight. Battlecry: reveal the top card of your deck; if it is a Bird, draw it.
  ↳ Balance: conditional filtered draw on a solid flyer; whiffs are real, so the body stays near Eagle. · Source: flavor-first.

**Hamster** | Rodent | Str 1 | Common
Battlecry: draw 2 cards, then discard 1.
  ↳ Balance: net +1 card with a filter on a 1-body (cheek-pouch hoarding). Owl-class selection at Common. · Source: mechanic-first (wanted a net-+1 dig on a 1-body).

**Crow** | Bird | Str 3 | Rare
Flight. Battlecry: draw 1; if an enemy unit was removed this turn, draw 2 instead.
  ↳ Balance: Vulture-style payoff (rewards a removal turn) folded into a flyer. · Source: flavor-first.

---

## 4 · Food economy

**Honeyguide** | Bird | Str 1 | Common
Flight. Battlecry: gain 6 food; if you control a Bear or Colony unit, gain 4 more.
  ↳ Balance: Worker Ant (1, gain 8) anchor; splits into base + a tribal kicker, with Flight justifying the slightly lower base. · Source: flavor-first.

**Dung Beetle** | Insect | Str 2 | Common
Battlecry: gain 4 food. Deathrattle: gain 4 food.
  ↳ Balance: 8 food spread across play + death on a slightly larger body than Worker Ant (1, gain 8 at once). · Source: flavor-first.

**Cow** | — | Str 4 | Common
At the end of your turn, gain 2 food.
  ↳ Balance: the entry-level recurring-ramp body. Anchor: Beaver (Immovable, +3/turn, Rare) — Cow is fragile and slower for a lower rarity. · Source: mechanic-first (wanted a cheap drip-ramp common).

**Leafcutter Ant** | Colony | Str 1 | Common
Battlecry: gain 3 food for each other Colony unit you control.
  ↳ Balance: Queen Ant (Legendary, +2/unit) anchor; smaller per-unit number at Common on a token body. · Source: mechanic-first (wanted a per-unit scaling-food body).

**Capybara** | Rodent | Str 5 | Rare
At the end of your turn, gain 1 food for each unit adjacent to this.
  ↳ Balance: board-scaling income on a sturdy, hard-to-shift hub. Caps naturally at crossroad degree. · Source: mechanic-first (wanted an adjacency-scaling food engine).

**Camel** | — | Str 6 | Rare
Battlecry: gain 12 food. You cannot gain food again until your next turn.
  ↳ Balance: Squirrel (2, +8) anchor; bigger burst + bigger body, paid for with a one-turn food lockout + Rare. · Source: flavor-first · ⚙ new mechanic: *food-gain lockout* (a per-player flag checked in `gain_food`).

**Aphid** | Insect | Str 1 | Common
Battlecry: gain 2 food. Whenever you place another Colony or Insect unit, gain 2 food.
  ↳ Balance: a recurring per-placement trickle on a token; rewards going wide. Anchor: Queen Bee's per-event rider, but capped to your own placements. · Source: mechanic-first (wanted a per-placement food trickle).

**Mosquito** | Insect | Str 1 | Common
Battlecry: steal 4 food from the opponent.
  ↳ Balance: a swing is worth ~2× a gain, so 4 stolen ≈ 8 gained (Worker Ant) on a 1-body. · Source: flavor-first · ⚙ new mechanic: *steal food* (opponent loses up to N, you gain it).

**Albatross** | Bird | Str 5 | Rare
Flight. At the end of your turn, gain 3 food.
  ↳ Balance: Worker Wasp (Colony 3, flight, +3 EoT) anchor; a bigger flyer carrying the same drip at Rare. · Source: mechanic-first (wanted a flying drip-ramp body).

---

## 5 · Strength buffs — anthems, counters & debuffs

**Gorilla** | Primate *(new tag)* | Str 7 | Rare
Adjacent enemy units have −2 strength.
  ↳ Balance: Lion-bodied (7) but Rare for the aura — silverback intimidation makes neighbors easier to cover. Anchor: Snow Leopard (Cat 6, Rare anthem). · Source: flavor-first · ⚙ new mechanic: *enemy-side anthem* ("Has −X to enemies") — mirrors existing anthem code with a sign flip.

**Chimpanzee** | Primate | Str 4 | Rare
Battlecry: give an adjacent friendly unit +3 strength.
  ↳ Balance: Dhole (3, give +2 to adjacent Canines) anchor; a single bigger grant on a slightly larger body. · Source: flavor-first.

**Mandrill** | Primate | Str 5 | Rare
Your other Primates have +2 strength.
  ↳ Balance: Wolf Matriarch (Canine 4, others +2, anthem) anchor, one point of body up for the more flexible tag. · Source: flavor-first.

**Rhinoceros Beetle** | Insect | Str 2 | Common
Has +1 strength for each other Colony or Insect unit you control.
  ↳ Balance: African Wild Dog (2, +1/Canine) anchor — same count-anthem on a bug shell. · Source: mechanic-first (wanted a count-anthem on a small body).

**Howler Monkey** | Primate | Str 3 | Common
Battlecry: give all Primates in your hand and on the battlefield +1 strength.
  ↳ Balance: Red Wolf / Howl anchor (hand + board burst buff); a smaller +1 spread on a Common. · Source: flavor-first.

**Musk Ox** | Megafauna | Str 6 | Rare
Has +1 strength for each other unit adjacent to this.
  ↳ Balance: defensive-formation anchor; caps at crossroad degree, snowballs in a clustered board. · Source: mechanic-first (wanted an adjacency-scaling body).

**Tasmanian Devil** | Marsupial *(new tag)* | Str 3 | Rare
Adjacent enemy units have −1 strength.
  ↳ Balance: the small-bodied cousin of Gorilla's debuff aura. · Source: flavor-first · ⚙ uses the enemy-anthem mechanic.

**Cardinal** | Bird | Str 2 | Common
Battlecry: give a Bird in your hand +2 strength.
  ↳ Balance: Red Wolf (hand buff) anchor, narrowed to a single hand target on a token. · Source: mechanic-first (wanted a hand-buff enabler; the songbird mentor fit).

**Bull** | — | Str 7 | Rare
Whenever this gains strength, give an adjacent friendly unit +1.
  ↳ Balance: Bush Dog (buff-cascade trigger) anchor; turns any pump into board-wide value, so it sits at baseline body + Rare. · Source: mechanic-first (wanted a cascade payoff; the charging bull fit).

---

## 6 · Tempo — extra placements, chaining, bounce, move

**Starling** | Bird | Str 2 | Common
Flight. Battlecry: if you control another flying unit, play one more flying unit from your hand.
  ↳ Balance: House Cat / Dog (conditional chain) anchor, themed to flyers (murmuration). · Source: flavor-first.

**Wildebeest** | — | Str 4 | Rare
Battlecry: move a friendly unit to an adjacent crossroad.
  ↳ Balance: pure repositioning tempo (open a lane, reconnect, dodge a cover). No body discount needed beyond Rare for the new tool. · Source: mechanic-first (wanted a repositioning/move tool) · ⚙ new mechanic: *move* a unit one crossroad (new op; respects connection/covering on arrival).

**Kangaroo** | Marsupial | Str 5 | Rare
Battlecry: move this or a friendly unit up to 2 crossroads.
  ↳ Balance: longer-range move on a solid body; great for surprise HQ reach. Anchor: Wildebeest. · Source: flavor-first · ⚙ uses *move* (range 2).

**Lemur** | Primate | Str 2 | Common
Battlecry: if you control another Primate, play one more Primate from your hand.
  ↳ Balance: House Cat anchor, retagged to Primate troops. · Source: flavor-first.

**Salmon** | Fish | Str 4 | Common
Battlecry: move this to any crossroad connected to your HQ.
  ↳ Balance: self-reposition reach (swim upstream); enables a sudden push without Flight. Anchor: Cougar (place by any Cat). · Source: flavor-first · ⚙ uses *move* (to any connected crossroad).

**Bombardier Beetle** | Insect | Str 2 | Rare
Battlecry: return an adjacent enemy unit of strength 4 or less to its owner's hand.
  ↳ Balance: Skunk (bounce) anchor; a clean tempo bounce without the lock, at a lower body. · Source: flavor-first.

**Ibex** | — | Str 5 | Common
Battlecry: may be placed adjacent to any friendly unit, ignoring connection.
  ↳ Balance: Cougar (place next to any Cat) anchor, generalized off-tribe but kept at Common with no other rider. · Source: flavor-first.

**Prairie Dog** | Rodent | Str 1 | Common
Battlecry: play one more Rodent from your hand.
  ↳ Balance: Jerboa (2, play another) anchor; an unconditional chain restricted to Rodents on a 1-body. · Source: mechanic-first (wanted a tribal chaining 1-drop).

**Gecko** | Lizard | Str 2 | Common
Battlecry: may be placed on any crossroad adjacent to an enemy unit, ignoring connection.
  ↳ Balance: an infiltration enabler for HQ-rush — reach without Flight, but only next to enemies. · Source: mechanic-first (wanted a cheap behind-the-lines reach tool; the wall-climber fit).

---

## 7 · Defensive & evasion

**Pangolin** | — | Str 3 | Common
Cannot be covered by enemy units.
  ↳ Balance: cheaper Giant Tortoise (5, uncoverable); the small body offsets the immunity. · Source: flavor-first.

**Mole** | Rodent | Str 5 | Common
Burrow.
  ↳ Balance: Eagle (5, Flight) is the evasion anchor; Burrow is flight-minus (empty crossroads only, can't cover), so an equal body at Common is on-curve. · Source: flavor-first · ⚙ new mechanic: **Burrow** keyword (= Flight restricted to empty crossroads; subset of existing connection-bypass code).

**Coconut Crab** | — | Str 5 | Rare
Cannot be covered by enemy units.
  ↳ Balance: Porcupine (5, uncoverable, Rare) anchor — a near-mirror, themed as the giant armored land crab. · Source: mechanic-first (wanted a Rare uncoverable beater).

**Stick Insect** | Insect | Str 2 | Rare
Cannot be targeted by enemy special effects until it covers an enemy unit.
  ↳ Balance: Black Panther (always untargetable) anchor; the camouflage version drops its shield once it strikes, so it is cheaper. · Source: flavor-first · ⚙ new mechanic: **Camouflage** (conditional untargetability; a predicate on the existing targeting check).

**Cuttlefish** | — | Str 3 | Rare
Adjacent friendly units cannot be targeted by enemy special effects.
  ↳ Balance: extends Black Panther's protection to neighbors (ink screen) — a small support body. `(sim-tune)` for the aura's reach. · Source: mechanic-first (wanted an untargetable support aura) · ⚙ new mechanic: *untargetable aura*.

**Bighorn Sheep** | — | Str 6 | Common
Immovable.
  ↳ Balance: a vanilla-plus Immovable wall at Common. Anchor: Giant Tortoise (5, Immovable, Rare) / Elephant — one point up, no other rider. · Source: mechanic-first (wanted a Common Immovable wall).

**Echidna** | — | Str 3 | Common
Cannot be covered by enemy units. Deathrattle: draw 1.
  ↳ Balance: Pangolin's body + a Hedgehog (DR draw 1) rider; sticky and replaces itself. · Source: mechanic-first (wanted an uncoverable body that replaces itself).

**Naked Mole Rat** | Rodent | Str 2 | Rare
Immovable. Cannot be targeted by enemy special effects.
  ↳ Balance: tiny but supremely sticky — a great carrier for delayed/anchor effects. Two defensive keywords on a 2-body justify Rare. · Source: flavor-first.

**Clownfish** | Fish | Str 2 | Common
Cannot be targeted by enemy special effects while you control another Fish.
  ↳ Balance: conditional Black Panther; the protection only switches on with a host school. · Source: mechanic-first (wanted a conditional untargetable body).

---

## 8 · Dynamic & scaling strength

**Locust** | Insect | Str X | Common
Strength equals the number of Colony or Insect units you control.
  ↳ Balance: Nile Crocodile (str = units you control) anchor, narrowed to a tribe — a swarm payoff body. · Source: flavor-first.

**Great White Shark** | Fish | Str 4 | Rare
Has +2 strength for each adjacent enemy unit.
  ↳ Balance: thrives in a contested lane (feeding frenzy); does nothing in open water. Caps at crossroad degree. · Source: mechanic-first (wanted a scales-in-combat body).

**Python** | Snake | Str 4 | Rare
When this covers a unit, give it +X strength, where X is that unit's strength (constriction).
  ↳ Balance: a snowball body — eats one big thing and keeps the muscle. `(sim-tune)` for runaway potential. · Source: flavor-first · ⚙ new mechanic: *absorb covered unit's strength as a permanent counter*.

**Saltwater Crocodile** | Lizard | Str 4 | Rare
Has +1 strength for each unit buried beneath this.
  ↳ Balance: grows as it stacks kills (death roll); resets if it is itself covered. · Source: flavor-first · ⚙ new mechanic: *read stack depth* (count units below in the stack).

**Walrus** | — | Str 8 | Rare
Has −1 strength for each empty crossroad adjacent to this.
  ↳ Balance: an above-baseline body with a positioning drawback — wants the herd around it. Anchor: Musk Ox, inverted. · Source: mechanic-first (wanted a big body with a positioning drawback) · ⚙ uses a *negative count-anthem*.

**Barnacle** | — | Str X | Common
Has the same strength as the unit directly beneath this; if none, Str 0.
  ↳ Balance: a near-free rider that only matters when it rides a host — encrusts your own big bodies for a second wall. · Source: mechanic-first (wanted a "copy the body under me" scaler; the barnacle fit).

**Remora** | Fish | Str 1 | Common
Has +X strength, where X is the highest strength among adjacent friendly units.
  ↳ Balance: leeches off your biggest neighbor; collapses when isolated. Anchor: count-anthems, keyed to a max instead. · Source: mechanic-first (wanted a "hitchhiker" body).

---

## 9 · Delayed & timed payoffs

**Cicada** | Insect | Str 1 | Rare
After 3 turns, this gains +8 strength (Str 9).
  ↳ Balance: Egg-style sleeper — nearly free now, a monster later, but a 1-body that is trivially covered in the meantime. · Source: flavor-first · ⚙ new mechanic: *timed strength transform* (existing scheduler).

**Caterpillar** | Insect | Str 1 | Common
After 2 turns, remove this and play a Butterfly (Insect, Str 4, Flight) for free.
  ↳ Balance: Egg (remove → payoff) anchor; pays out a flyer body instead of cards. · Source: flavor-first · ⚙ new mechanic: *transform into a token unit*.

**Antlion** | Insect | Str 2 | Rare
At the start of your next turn, remove an adjacent enemy of strength 3 or less.
  ↳ Balance: a telegraphed pit trap — Gray Wolf's removal on a one-turn delay, so the body is cheaper. · Source: mechanic-first (wanted a telegraphed delayed removal) · ⚙ *delayed removal* (scheduler).

**Groundhog** | Rodent | Str 3 | Common
At the start of your next turn, gain 4 food and draw 1.
  ↳ Balance: a small delayed value-bundle on a fair body; the wait is the cost. · Source: mechanic-first (wanted a delayed value-bundle).

**Dormouse** | Rodent | Str 2 | Common
Immovable. For 2 turns this does nothing; then gain 12 food.
  ↳ Balance: Hibernating Bear (store/double) anchor, simplified to a flat delayed payout on a tiny unkillable body. · Source: mechanic-first (wanted a tiny delayed-payout body) · ⚙ scheduler (exists).

**Maggot** | Insect | Str 0 | Common
Fragile. After 1 turn, remove this and play a Fly (Insect, Str 2, Flight) for free.
  ↳ Balance: the fastest, cheapest transform — a Fragile 0-body that becomes a flyer next turn. · Source: mechanic-first (wanted a 1-turn micro-transform; the larva fit).

**Tardigrade** | — | Str 1 | Rare
Immovable. Cannot be removed. After 4 turns, gain 30 food.
  ↳ Balance: an unkillable long fuse — a huge payoff gated entirely behind time and a do-nothing body. `(sim-tune)` for the threshold race. · Source: flavor-first · ⚙ scheduler + total removal immunity.

---

## 10 · Disruption — venom, lock, steal, parasite, lure

**Cobra** | Snake | Str 3 | Rare
Battlecry: poison an adjacent enemy — remove it at the start of your next turn.
  ↳ Balance: low body repaid by removal of *any* size, but delayed a full turn (the target can be covered or relocated first). Anchor: Gray Wolf (4/≤3 *now*). · Source: flavor-first · ⚙ new mechanic: **Venom** / delayed-removal counter (scheduler).

**Komodo Dragon** | Lizard | Str 5 | Rare
Battlecry: poison an adjacent enemy of any strength; gaining strength cannot save it.
  ↳ Balance: the bigger-bodied Venom carrier (septic bite) vs Cobra — pays the higher body for a sturdier delivery. · Source: flavor-first · ⚙ uses **Venom**.

**Box Jellyfish** | — | Str 2 | Rare
Battlecry: lock an adjacent enemy unit — until your next turn it cannot move, be removed, cover, or use its effects.
  ↳ Balance: Skunk's lock half on a token; freezes a key blocker for a turn. Anchor: Skunk (bounce + lock). · Source: mechanic-first (wanted a single-target lock) · ⚙ new mechanic: **Lock** (a per-unit status flag).

**Electric Eel** | Fish | Str 3 | Rare
Battlecry: set an adjacent enemy unit's strength to 0 until your next turn.
  ↳ Balance: soft-removal enabler — anything can then cover the stunned unit. Anchor: Gray Wolf, but it sets up a kill instead of making one. · Source: mechanic-first (wanted a set-strength-to-0 enabler) · ⚙ new mechanic: *temporary strength override*.

**Cuckoo** | Bird | Str 2 | Rare
Flight. Battlecry: if this covers an enemy unit, gain control of the unit beneath it instead of burying it.
  ↳ Balance: tiny body + Flight for reach; theft is strong but gated by the normal covering rule (must out-strength the target). No clean anchor → `(sim-tune)`. · Source: flavor-first · ⚙ new mechanic: *steal / flip control of a covered unit*.

**Frigatebird** | Bird | Str 3 | Rare
Flight. Battlecry: steal a random card from the opponent's hand.
  ↳ Balance: Raccoon (opponent discards random) anchor, upgraded to theft-into-your-hand + Flight → Rare. · Source: flavor-first · ⚙ new mechanic: *steal a card from the opponent's hand*.

**Anglerfish** | Fish | Str 5 | Rare
Enemy units that are able to cover this must cover this before covering your other units. Has +2 strength while an enemy is adjacent.
  ↳ Balance: a lure/taunt that protects your board and bulks up when challenged. `(sim-tune)` for the forced-targeting rule. · Source: flavor-first · ⚙ new mechanic: **Lure** (constrains the opponent's legal covers).

**Lamprey** | Fish | Str 2 | Common
Battlecry: attach to an adjacent enemy unit. At the start of each of your turns, gain 2 food and that unit has −1 strength.
  ↳ Balance: a recurring drain + debuff that rides a host; dies when the host does. · Source: mechanic-first (wanted a parasite drain engine) · ⚙ new mechanic: **Parasite / attach** (a per-unit link with an upkeep tick).

---

## 11 · Deathrattle, sacrifice & recursion

**Tarantula** | Arachnid | Str 4 | Rare
Deathrattle: play a Spiderling (Arachnid, Str 1) on each adjacent empty crossroad.
  ↳ Balance: a go-wide death burst — trades one body for several tokens, ideal sac fodder. Anchor: token generators. · Source: flavor-first · ⚙ uses *tokens*.

**Mayfly** | Insect | Str 3 | Common
Deathrattle: draw 1. This is removed at the end of your next turn no matter what.
  ↳ Balance: a built-in-expiry body that cantrips on death — pure sac-engine fuel. Anchor: Hedgehog (DR draw 1) with a guaranteed trigger. · Source: mechanic-first (wanted self-expiring sac fuel) · ⚙ new mechanic: *self-expiry timer*.

**Axolotl** | Amphibian *(new tag)* | Str 3 | Rare
The first time this would be removed, instead return it to this crossroad at Str 1.
  ↳ Balance: survives one removal in place (regrows limbs) — sticky board presence. Anchor: Opossum (return to hand), but it stays put. · Source: flavor-first · ⚙ new mechanic: *regenerate-in-place once* (per-instance flag).

**Starfish** | — | Str 2 | Common
Deathrattle: play two Arm tokens (—, Str 1) on adjacent empty crossroads.
  ↳ Balance: splits into fodder on death (regrows from a severed arm); cheap width for sac decks. · Source: mechanic-first (wanted token death-fodder) · ⚙ uses *tokens*.

**Pelican** | Bird | Str 4 | Rare
Flight. Battlecry: remove a friendly unit; draw 2.
  ↳ Balance: a flying sac outlet — converts a spent Deathrattle body into cards. Anchor: Black Widow / Devourer (sac → draw). · Source: mechanic-first (wanted a draw-sac outlet; the scooping pelican fit).

**Carrion Beetle** | Insect | Str 2 | Common
Whenever a friendly unit is removed, gain 3 food.
  ↳ Balance: the sacrifice-payoff engine for a food deck — Jackal's on-removal trigger, pointed at your own losses. · Source: mechanic-first (wanted a sac→food engine; the decomposer fit).

**Earthworm** | — | Str 1 | Common
When this is removed by being covered, return two copies of it to your hand.
  ↳ Balance: regenerating chump (cut in half → two worms) — endless fodder, but only off covering. Anchor: Opossum, doubled and conditional. · Source: flavor-first · ⚙ *recursion* (return-to-hand variant).

**Honeypot Ant** | Colony | Str 1 | Common
Deathrattle: gain 8 food.
  ↳ Balance: Gazelle (DR +20) anchor, scaled down to a Common living-larder body. · Source: flavor-first.

---

## 12 · Apex predators & reach finishers

**Wolverine** | — | Str 5 | Rare
Apex Predator. Cannot be covered by enemy units.
  ↳ Balance: Polar Bear (8, Apex) + Porcupine (5, uncoverable) on a smaller, fearless body. · Source: flavor-first.

**Bull Shark** | Fish | Str 7 | Rare
Apex Predator.
  ↳ Balance: a clean big eater — Anaconda (7, Apex, Common) bumped to Rare for the more flexible Fish tag and aggression. · Source: mechanic-first (wanted a clean vanilla-Apex beater).

**Osprey** | Bird | Str 5 | Rare
Flight. Apex Predator.
  ↳ Balance: a flying Apex (dives onto prey) — reach + guaranteed removal-on-cover, gated by Rare. Anchor: Golden Eagle + Apex. · Source: flavor-first.

**Blue Whale — "Sounder"** | Cetacean | Str 10 | Legendary
Immovable. Cannot be covered. This cannot cover units or capture an HQ. Costs 15 food to play.
  ↳ Balance: an unremovable board-locking wall (the largest animal ever), gated by Legendary + a food cost + a no-offense drawback. · Source: flavor-first · *food-cost card 2 of 3*.

**Tyrannosaurus Rex — "Sue"** | Dinosaur *(new tag)* | Str 12 | Legendary
Apex Predator. Adjacent enemy units have −2 strength. Costs 20 food to play.
  ↳ Balance: the top-end finisher — Str 12 + Apex + a fear aura, gated by Legendary + the heaviest food cost. Anchor: the Ramp titan-rhino (10, costs 20). · Source: flavor-first (extinct) · *food-cost card 3 of 3* · ⚙ uses the enemy-anthem mechanic.

---

## 13 · Landmarks & non-animal resources

**Baobab Tree** | Landmark | Str 0 | Rare
Fragile. Immovable. At the start of each of your turns, gain 5 food.
  ↳ Balance: Fig Tree (gain 20 once) anchor; Baobab is the repeatable smaller engine, killable by being covered (Fragile). · Source: mechanic-first (recurring-ramp landmark).

**Coral Reef** | Landmark | Str 0 | Rare
Fragile. Immovable. Your Fish units have +2 strength.
  ↳ Balance: a fixed anthem object (nursery) — Snow Leopard's aura on a stationary, coverable target. · Source: mechanic-first (anthem landmark).

**Salt Lick** | Landmark | Str 0 | Common
Fragile. Immovable. At the start of your next turn, give all friendly units +1 strength, then remove this.
  ↳ Balance: a one-shot team pump object; Watering Hole (delayed payoff) anchor. · Source: mechanic-first (one-shot buff landmark).

---

# Appendices

## Appendix A — New mechanics introduced

Grouped by implementation cost. "Cheap" = a flag/predicate on existing code; "New op" = a new entry in the effect `OPS`/`EFFECTS` registry; "Subsystem" = touches multiple systems.

| Mechanic | Cards | Cost | Note |
|---|---|---|---|
| Enemy-side anthem ("adjacent enemies −X") | Gorilla, Tasmanian Devil, T. Rex | Cheap | Sign-flipped, enemy-scoped anthem; reuses the live anthem layer. |
| Burrow keyword | Mole | Cheap | Connection-bypass (like Flight) restricted to empty crossroads. |
| Camouflage / conditional untargetability | Stick Insect | Cheap | Predicate on the existing `can_be_targeted` check. |
| Untargetable aura | Cuttlefish | Cheap | Anthem-style aura over the targeting check. |
| Negative count-anthem | Walrus | Cheap | Existing count-anthem with a negative coefficient. |
| Read stack depth | Saltwater Crocodile | Cheap | Count units below in the stack at strength-check time. |
| Copy host / neighbor strength | Barnacle, Remora | Cheap | Dynamic-strength readers (like Nile Croc). |
| Self-expiry timer | Mayfly | Cheap | Scheduled self-removal (reuses the scheduler). |
| Food-gain lockout | Camel | Cheap | Per-player flag checked in `gain_food`. |
| Exile-style removal (no recursion) | Shrike | Cheap | Flag on the remove op to skip hand/deck return. |
| Venom / delayed-removal counter | Cobra, Komodo Dragon, Antlion | New op | Scheduled removal targeting a marked unit (scheduler exists). |
| Timed strength transform | Cicada | New op | Scheduled stat change. |
| Transform into a token unit | Caterpillar, Maggot | New op | Scheduled remove-and-spawn. |
| Token units | Bullfrog*, Tarantula, Starfish, (Caterpillar/Maggot payoffs) | New op | Create N-strength unit instances not drawn from a deck. |
| Move a unit | Wildebeest, Kangaroo, Salmon | New op | Relocate a unit; revalidate connection/covering on arrival. |
| Steal food | Mosquito | New op | Opponent loses up to N food, you gain it. |
| Steal a card from hand | Frigatebird | New op | Random transfer from opponent hand → yours. |
| Steal / flip control of a covered unit | Cuckoo | New op | On-cover ownership change instead of burying. |
| Temporary strength override (set to 0) | Electric Eel | New op | Timed stat override (clears next turn). |
| Lock / stun | Box Jellyfish | New op | Per-unit status disabling move/cover/remove/effects for a turn. |
| Lure / taunt | Anglerfish | Subsystem | Constrains the opponent's legal cover actions. |
| Parasite / attach | Lamprey | Subsystem | Per-unit link + upkeep tick + shared fate. |
| Regenerate in place once | Axolotl | New op | Per-instance "survive removal" flag. |
| Recurring / anthem Landmarks | Baobab Tree, Coral Reef, Salt Lick | Cheap–New op | Reuse Landmark card type + scheduler/anthem. |

\* Bullfrog is in the approved plan sample; not re-listed in the 100 above. Add it under §6 or §11 if desired.

## Appendix B — Distribution summary

- **Count:** 100 entries across 13 effect families.
- **Source split:** 50 flavor-first / 50 mechanic-first (half each, as planned).
- **Rarity (as it fell out):** 49 Common · 48 Rare · 3 Legendary (Orca, Blue Whale, T. Rex — named individuals). For a candidate pool I let rarity follow each card's power rather than forcing the pool's ~15% Legendary ratio.
- **Food-cost-to-play lever:** 3 used (Bison, Blue Whale, T. Rex) — under the ≤5 budget. (Camel uses a food *lockout*, not a play cost.)
- **New tribe tags proposed:** Primate, Insect, Amphibian, Marsupial, Cetacean, Dinosaur.
- **`(sim-tune)` flags** (no clean anchor — verify in M3): Cuckoo, Cuttlefish, Python, Anglerfish, Tardigrade.

## Appendix C — Already-used animals (collision check)

Every name above was checked against the union of `animal_kingdom/data/cards.json` and all 7 files in `docs/decks/`. Already-used animals (off-limits) include:

> Anaconda, Andean Condor, Armadillo, Army Ant, Baboon, Bat, Bird Egg, Black Bear, Black Panther, Black Swan, Black Widow, Boa Constrictor, Bush Dog, Cape Buffalo, Caracal, Chameleon, Cheetah (Brother/Sister), Chipmunk, Cottontail, Cougar, Coyote, Dhole, Dingo, Dog, Domestic/House Cat, Eagle/Golden Eagle, Egg, Elephant/Matriarch Elephant, Falcon, Fig Tree, Flying Squirrel, Fox, African Wild Dog, Gazelle, Giant Tortoise, Gray Wolf, Grizzly Bear, Guard Hornet, Hedgehog, Hibernating Bear, Hippopotamus, Honey Badger, Honeybee, Hornet, Impala, Jackal, Jaguar, Jerboa, Keeper of the Stash (squirrel), Leopard, Lemming, Lion, Lioness, Lynx, Mouse, Nautilus, Nile Crocodile, Nurse Bee, Nurse Bumblebee, Octopus, Opossum, Owl, Oxpecker, Piranha, Plague Rat, Polar Bear, Porcupine, Prince Leo, Princess Lea, Pufferfish, Queen Adira, Queen Ant, Queen Bee, Rabbit, Raccoon, Rat, Rat King, Rattlesnake, Raven, Red Wolf, Rhinoceros, Serval, Sidewinder, Skunk, Snake Egg, Snow Leopard, Soldier Ant, Spotted Hyena, Squirrel, Tarantula Hawk, Termite King, Termite Queen, Tiger, Velvet Ant, Vervet Monkey, Vulture, Wasp, Watering Hole, Wild Boar, Wild Dogs, Wolf Matriarch, Worker Ant, Worker Bee, Worker Wasp, King Theron, Champion of the Hive.

> Reserved legendary *individual names* already in the deck docs (avoid reusing the name, the species is fine): Lobo, Shuck, Ember, Methuselah, Croesus/Scrooge, Carmilla/Mortessa/Vespera, Maxima/Vesper/Reaver, Raksha, Ylva, Greyback, Whiteclaw, and others in `docs/decks/flavor-review.md`.
