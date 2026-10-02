# Keyword Registry

Canonical definitions for every printed keyword. **This is the single source of truth** — card files, deck files, and the engine reference keywords by name and do not re-explain them. Companion to `overview.md` (rules) and `rulings.md` (how other card text resolves).

Everything on a crossroad is a unit; Eggs are units too.

---

## Official keywords

### Flight
Can be placed ignoring connection, except onto a den: capturing the enemy den still needs a connected path, so Flight alone never captures. All other placement rules still apply.

### Armor
A shell, plates or spines: cannot be removed, returned to hand, or eaten by **any** ability — the enemy's **or its own controller's**. It can still be **covered** under the normal placement rules — covering is placement, not an ability. Pestis can't target an enemy with Armor; when it removes a stack, a buried unit with Armor is skipped **in place** and everything else is still removed. Armor is not a shield for the cards beneath it. Scope is **board-only**: a card with Armor in hand can be paid or removed normally.

Carried by: Methuselah the tortoise and Cairn the glyptodont (Ramp); Armadillo (Food). Only animals a player sees as armored carry it; the spiny ones (Porcupine, Hedgehog) remove the first enemy that covers them instead.

### Stealth
Cannot be **chosen** by an enemy ability: excluded from any option list an enemy picks a target from (Jaguar/Serval/Hawk/Jackal/Soldier Ant/Rat/Hornet/Skunk/Pestis). **Mass, random, and automatic effects hit it normally**, and so does an Apex Predator's eat (a predator eats what it lands on; nobody chooses): Rhinoceros/Brutus AoE, the units buried under a Pestis target, Sirocco's mass bounce, Grizzly Bear's random strike, Hippopotamus/King Theron triggers. Its own controller may still choose it freely. Scope is board-only.

Carried by: Black Panther. Armadillo gives it to every friendly unit on an adjacent crossroad while Armadillo tops its own.

### Spikes
The first time an enemy covers it, that enemy is removed (a remove, so Armor resists it). Once per animal: a Spikes animal that has removed a coverer is an ordinary animal from then on, and its badge on the board goes. Covering is placement, so the coverer's own Roar resolves first, then the spikes (and an Apex Predator landing on it is removed before it can eat). A friendly cover doesn't set it off.

Carried by: Porcupine and Hedgehog (Food).

### Apex Predator
A predator that must land on prey and eats it.

- **Must** be placed on top of another **occupant** — it **cannot** be placed on an empty crossroad. If there is no legal occupant to land on, it cannot be played.
- **Normal covering rules apply in full**: landing on an **enemy** occupant uses the same legality as a normal cover — strictly-greater strength by default, **including every covering static**: Snow Leopard lets an apex Cat land at equal strength. Landing on **your own** occupant has **no** strength requirement.
- **May target your own occupants** as well as enemy ones — and removes (eats) them too.
- **It covers, then eats.** Landing is an ordinary cover, and everything that reacts to being covered happens first (Porcupine's and Hedgehog's spines remove it, Gale sends it back to hand). Then, if the predator is still on top of its prey, it eats it: the prey is removed, its leave-the-board and remove effects fire normally, and the predator sits on whatever remained beneath.
- **If the occupant can't be eaten** (Armor), the predator is **not** blocked from landing there: it simply **covers** it under the normal placement rules and buries it instead of eating it. Apex Predator is not restricted to prey it can eat — eating is what it does *when it can*, not a placement precondition.
- **Cannot be placed onto a den** — deliberate design choice, so Apex Predators can't capture an enemy den directly.

Carried by: **Tiger** (Cats), **Eon** (Egg), **Polar Bear** and **Borealis** (Ramp).

### Roar
An effect that resolves when the unit is placed. Most "when placed…" effects are Roars.

### Leaving the board  *(not a keyword)*
An effect that resolves when **a unit leaves the board** is written out in plain words: "When this is removed, …" (Ember). It becomes a keyword only once at least three cards want it.

**Leaving the board vs. "remove":** a unit leaving the board is one kind of *remove*, but not the only one — a card sent to the **Remove Pile** from hand or deck (e.g. Rat's paid card, Black Swan's hand-remove) is a **remove** but doesn't leave the board. So there are two trigger tiers: a **remove trigger** (any card → Remove Pile, from anywhere) and the narrower **leaving the board**. See `overview.md` for the Remove Pile zone. A return to hand or deck (Skunk, Sirocco, Eon) is *not* a remove at all — the card never reaches the Remove Pile.

---

## Not a keyword

### Costs X food  *(placement cost)*
A printed cost, handled by the engine, not a keyword. The placement is offered only if the controller has ≥ X food; X food is paid on placement. (e.g. Ramp's `Costs 15 food` bodies, some legendaries.) X is card-intrinsic — `food_cost` in `cards.json`, next to `base_strength` — not a `config.py` constant; tune it there.

### Strength modifiers  *(card-text convention, not a keyword)*
Card text grants strength two ways, **distinguished by the verb** — this reading is binding:

- **"has +X strength" → an anthem** (live, conditional aura). Recomputed live; **vanishes** when its source leaves play or its condition stops holding. Examples: wolf matriarch ("your other Canines *have* +2"), African Wild Dog ("*has* +1 for each friendly Canine"), Champion of the Hive, Guard Hornet ("*has* +5 while ≥4 Colony"). The same live layer also computes **dynamic strength** (e.g. the giant-anaconda legendary = number of removed units).
- **"give +X strength" → a permanent counter** (one-time grant, **stored on the unit instance**, persists after the granter dies). Also applies to **cards in hand** (which carry the counter onto the board when played); hand buffs are **one-time** — a unit drawn *after* the buff is not retroactively buffed. Examples: Dhole ("*give* all adjacent Canines +2"), howl ("*give* +1 to all other Canines in hand and battlefield"), hellhound's returned Canine (+2), the end-of-turn buffer.

**`effective_strength`** = `base_or_dynamic + stored_counters + active_anthems`, clamped ≥ 0, **evaluated live** wherever strength matters (covering, removal thresholds, region-holding, conditions like Coyote's "if this has 5+"). Counters are signed ints (Viper's "−3" is one). The event **`ON_GAIN_STRENGTH`** fires only when a counter is granted (not on live anthem drift).

### Discard  *(card-text term, not a keyword)*
**Discard a card** means remove a card from a hand (or from a deck, when the text says so, as on Hornet). "Your opponent discards a random card" (Black Swan) and "discard a random card" (Rat) are the same removal the engine has always done for "removes a random card from their hand".

### Scout  *(card-text term, not a keyword)*
**Scout a card** means look at the top three cards of your deck, draw one and shuffle the other two back. **Scout a Bird** (or a legendary unit, or any other kind) looks at three random cards of that kind in your deck instead, all of them if there are fewer. It draws from the deck and never creates a card; the shuffle counts as shuffling (Rattlesnake grows). The count is `scout_count`. Cards: Owl, Fathom, Bird Egg.

### Card-text conventions
Card text fits three lines on the full card (`docs/design/principles.md`). These phrasings are binding:

- **"enemy"** means an enemy unit; **"your Canines"** means friendly Canines.
- A unit is an **"animal"** on the cards and in the client ("play another animal", "Colony animal"); Eggs and tokens are animals too. "Unit" stays the word in the rules docs and code.
- Your own units are **"your Canines"** or **"Canines you control"**, never "friendly". **"Play"** means from your hand; only another place is named ("from your hand or deck").
- One card is **"draw a card"**; more are **"draw 2 cards"**.
- The other player is always **"your opponent"**, never "they", "their" or "them". Stealing from the opponent's hand is random by nature (the hand is hidden), so the text doesn't say "random".
- Thresholds read **"of strength 4 or less"**, **"6 or more"**, **"10 or more food"**.
- Timed triggers read **"At the end of your turn, …"** and **"At the start of your next turn, …"**; a delayed effect reads **"In 2 turns, …"**, or **"Next turn, …"** where the long form doesn't fit (Bird Egg).

