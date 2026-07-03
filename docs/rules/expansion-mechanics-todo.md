# Expansion Mechanics — To-Do

Rules questions created by the larger-card-pool brainstorm. Nothing here changes the canonical
keyword registry until explicitly adopted.

All card candidates that use these mechanics are inventoried in
[`../cards/card-candidates.md`](../cards/card-candidates.md). This document defines only the open
rules questions.

## Design standard

- [ ] A keyword must save meaningful repeated text on at least three cards.
- [ ] Prefer an existing operation plus a targeting restriction over a new subsystem.
- [ ] Every mechanic must specify interaction with covering, stacks, Stealth, Immovable,
  Landmarks, Eggs, the Remove Pile, and headquarters where relevant.
- [ ] New mechanics must work for a human tabletop implementation without hidden bookkeeping
  that only software can manage.
- [ ] “Once each time this enters play” counters reset only after the physical card leaves the
  battlefield and is later played again. Covering does not count as leaving play.
- [ ] Every event trigger must name its controller scope explicitly: `when you draw`, `when your
  opponent removes`, `when either player shuffles`, or `when a unit is removed`. Do not rely on a
  global implied default.
- [ ] Audit existing ambiguous triggers before adding more event cards:
  - Eon: whose draws, shuffles, and removals?
  - Vulture: any card removed by either player, or only the controller's cards/effects?
  - Goliath: all cards in the shared Remove Pile remains clear, but token removals need exclusion.
  - Jackal: “an adjacent unit” currently reads as either player's unit; confirm.

---

## 1. First-priority mechanics

### 1.0 Resolve Flight versus headquarters

The current documents say both that Flight ignores connection when placed and that Flight alone
cannot capture an HQ. Reach and extra-placement cards cannot be audited until this is stated in
one canonical sentence.

- [ ] Recommended rule: **no connection-bypass ability applies when placing onto an enemy
  headquarters**. The capturing placement must have an ordinary friendly connection.
- [ ] Add the HQ exception directly to Flight if adopted, rather than relying on deck notes.
- [ ] Apply the same HQ exception to Burrow, “place adjacent ignoring connection,” and all future
  reach mechanics.
- [ ] Re-check Falcon, Bat, Cuckoo, Starling, Gecko, Springhare, and the new Aggro legendary after
  the wording is settled.

### 1.1 Burrow

Proposed keyword:

> **Burrow** — This may be placed on an empty crossroad without connection to your
> headquarters.

- [ ] Confirm that Burrow cannot cover any occupant, be placed on either headquarters, or bypass
  any non-connection restriction.
- [ ] Burrowed units do not create connection unless a normal continuous friendly path later
  reaches them.
- [ ] Confirm that Burrow is a placement permission, not movement and not Flight. Effects that
  reference Flight do not see Burrow.
- [ ] Run an HQ-rush audit with Mole, Hare, Springhare, Pika, and Warren before adoption.

This is the cleanest proposed keyword: it uses the existing connection bypass but removes
Flight's ability to land on occupied crossroads.

### 1.2 Camouflage

Proposed keyword:

> **Camouflage** — This has Stealth until it covers an enemy unit.

- [ ] Covering a friendly occupant does not break Camouflage.
- [ ] An Apex Predator eating an enemy counts as covering it for this condition, even though the
  prey is removed instead of stacked.
- [ ] Once broken, Camouflage stays broken for that battlefield instance. Returning and replaying
  the card resets it.
- [ ] Do not promote this keyword until at least three cards use it. Until then, print the full
  conditional-Stealth text.

### 1.3 One-use cover retaliation

Required by the locked Aggro legendary:

> The first time an enemy unit covers this, return that enemy unit to its owner's hand.

- [ ] Resolve the placement first, then the retaliation. The coverer is returned and this unit
  becomes visible again.
- [ ] The retaliation is automatic, not chosen, so Stealth does not protect the coverer.
- [ ] An Immovable coverer cannot be returned; it remains on top and the one-use retaliation is
  considered spent.
- [ ] The returned card is not removed, triggers no Deathrattle/remove event, and receives no
  Skunk-style play lock.
- [ ] Track the spent shield on the card instance. Burying and later revealing it does not reset
  the shield; leaving and re-entering play does.
- [ ] Confirm ordering against King Theron, Pufferfish, Fragile, and future “when covered”
  triggers before canonizing the card.

### 1.4 Hatch and Incubate

Proposed parameterized ability word:

> **Hatch N — [effect].** At the start of your Nth turn after this entered play, remove this
> Egg and resolve its Hatch effect.

Proposed operation:

> **Incubate an Egg** — reduce its remaining Hatch time by one owner-turn. If that reaches
> zero, hatch it immediately.

- [ ] Hatch is not a cost discount. An Egg still consumes one card and the same placement action
  as Lion while contributing STR 0 during the delay. A body-only Hatch payoff must be premium;
  “wait N turns for one ordinary body” is an invalid rate.
- [ ] Count deck-to-board hatches and multiple tokens as explicit action advantage when balancing
  the Egg.
- [ ] Timers count owner turns only.
- [ ] An Egg played during its owner's turn does not consume a timer step that same turn; its
  first natural step is the start of the owner's next turn.
- [ ] A covered Egg remains on the battlefield but is not visible. It cannot hatch and cannot be
  incubated; decide whether its timer pauses or the Hatch effect permanently expires. Recommended:
  **pause while buried**, resume if revealed.
- [ ] If a Fragile Egg is covered, it is removed and its Hatch effect does not resolve.
- [ ] Incubation may cause an immediate hatch during the end step or a Battlecry. Check victory
  and region control after the token/unit enters.
- [ ] After the Egg is removed, play the Hatch result using normal placement rules on the Egg's
  former crossroad. A friendly occupant revealed beneath it may be covered normally; an enemy
  occupant requires sufficient strength. If the placement is illegal, the Hatch result fizzles.
- [ ] A card hatched from the deck resolves its Battlecry and must satisfy printed play conditions
  and food costs. Hatching supplies the placement action, not permission to ignore the card's
  other requirements.
- [ ] Existing Bird Egg and Snake Egg may remain written delayed effects; only convert them to
  Hatch if the shared wording genuinely improves clarity.

### 1.5 Move

Initial wording proposal:

> **Move N** — choose the unit specified by the card and relocate it along a path of up to N
> graph edges without treating it as played.

- [ ] Decide whether movement triggers Battlecry, “when played,” covering, Fragile, and
  on-covered effects.
- [ ] Decide whether the moved unit and/or destination must be connected to its controller's HQ.
  Concern noted: requiring connection may remove much of the mechanic's positional purpose.
- [ ] Define when connection, regions, and victory are recalculated after movement.
- [ ] Decide whether movement may enter or capture either HQ.
- [ ] Decide whether buried units can move or be selected for movement.
- [ ] Define how moving a visible unit off a stack affects the newly revealed occupant and
  control.
- [ ] Define interactions with Immovable and Stealth.
- [ ] Define eligible movers. The Kangaroo proposal allows moving itself or an ally; adjacency
  and visibility requirements remain open.
- [ ] Test two destination models separately:
  1. **Empty-only Move:** pure repositioning.
  2. **Covering Move:** occupied destinations are legal if every normal covering rule is
     satisfied, including strength, Snow Leopard, Chameleon, Porcupine, Fragile, and
     on-covered triggers.
- [ ] If covering is allowed, decide whether all ordinary covering rules apply or whether Move
  needs exceptions.
- [ ] Specify range measurement and whether intermediate crossroads matter.

### 1.6 Copy / mimic

Two distinct mechanics are under consideration:

1. **Full copy:** become a copy of the last eligible unit the opponent played.
2. **Mimic:** repeat only that unit's Battlecry.

- [ ] Decide how “last unit played” and “last Common unit played” are tracked, including whether
  the information is public and whether a later non-Common clears the Common reference.
- [ ] Decide copy timing before setting card stats:
  - `As you play this, copy...` copies before placement and may resolve the copied Battlecry.
  - `Battlecry: become a copy...` transforms after placement; the newly copied Battlecry does
    not retroactively resolve.
- [ ] Decide which properties a full copy inherits: strength, types/tags, keywords, rules text,
  counters, modifiers, status markers, name, rarity, and once-per-turn usage.
- [ ] Define how copied dynamic-strength formulas read controller and game state.
- [ ] Define the fallback when no eligible opponent unit has been played.
- [ ] Define copy-of-copy behavior and prevent unintended recursion.
- [ ] Define whether repeating a Battlecry counts as playing or copying any part of the original
  unit.
- [ ] Enumerate dangerous Battlecries before approving an unrestricted legendary mimic: extra
  placements, sibling fetches, Pestis, Sirocco, Carmilla, Bulwark, and future action modifiers.
- [ ] Compare Parrot/Lyrebird, Mimic Octopus/cuttlefish, and other animals before assigning the
  mechanic's final identity.

### 1.7 Tokens

- [ ] Treat every token placed without spending a card/action as real action economy. Low token
  strength does not make mass token generation free.
- [ ] Tokens exist only on the battlefield. They are not cards in a deck or hand.
- [ ] A token that would leave the battlefield ceases to exist after all relevant leave-play and
  remove triggers resolve.
- [ ] Tokens do not enter the shared Remove Pile and cannot be returned to a hand or shuffled into
  a deck. An effect attempting either makes the token cease to exist.
- [ ] Decide whether a disappearing token counts as “removed.” Recommended: **yes for battlefield
  remove/Deathrattle triggers, no for Remove-Pile-counting effects such as Goliath**.
- [ ] Tokens carry printed type/tags/strength and may control crossroads, regions, and capture an
  HQ unless their token definition says otherwise.
- [ ] Token-spawning unit proposals place tokens only on adjacent empty crossroads.
- [ ] Define placement order and what happens when too few adjacent empty crossroads exist.
- [ ] Add physical-component guidance before accepting a token-heavy archetype.

### 1.8 Venom

Proposed keyword action:

> **Envenom a visible unit** — mark it. At the start of the envenoming player's next turn,
> remove it if it is still visible on the battlefield, then clear the mark.

- [ ] Venom ignores later strength changes.
- [ ] Covering the marked unit before the timer resolves hides it and causes the Venom to expire.
  This is intended counterplay.
- [ ] Moving the marked unit does not clear Venom; returning it to hand/deck or removing it does.
- [ ] Immovable units may be marked but resist the eventual removal. The mark then clears.
- [ ] Stealth prevents an enemy from choosing a unit to envenom.
- [ ] Multiple Venom marks do not stack or extend the timer.
- [ ] Clearly mark Venom with a physical token and identify which player's next turn clears it.
- [ ] Decide whether “Venom” is the noun printed on cards or whether cards use “Poisoned.” Avoid
  the verb/noun ambiguity before flavor-lock.

### 1.9 Stack-order interaction — later module

- [ ] Keep this parked until movement/copy rules are stable; stack manipulation touches control,
  visibility, targeting, and connection simultaneously.
- [ ] Candidate operations to examine separately:
  - return one of your own buried units to hand;
  - swap the top two occupants;
  - move the visible occupant to the bottom;
  - inspect a stack without changing public control;
  - remove a specific buried card.
- [ ] Buried occupants remain generally untargetable. Every stack card must state an explicit
  exception rather than making “buried” a normal target class.
- [ ] Mixed-owner stacks need deterministic control updates after every intermediate reorder.
- [ ] Reordering is not placement: it does not trigger Battlecry, covering, Fragile, or
  on-covered effects unless a future card explicitly says to replay an occupant.
- [ ] Ocelot's proposed recovery of a friendly Cat buried under the enemy it just covered is the
  narrow first test case.

---

## 2. Actions concept

Initial note: players receive **2 actions per turn by default**. It remains open whether “Actions”
is a keyword, a core turn resource, or a larger alternate rules model.

### Possible interpretation A — map actions onto the current turn

- [ ] Each player begins a turn with **2 Action Points (AP)**.
- [ ] `Draw 1 card` costs **1 AP**.
- [ ] `Place 1 unit` costs **2 AP**.
- [ ] At two AP, the legal baseline choices remain exactly the current rules: draw two cards or
  place one unit.
- [ ] Card-effect draws, extra placements, movement, and triggered effects cost no AP unless the
  card explicitly says otherwise.
- [ ] `Gain +1 AP next turn` produces a three-AP turn: draw three, or place one then draw one.
- [ ] `Opponent gets −1 AP next turn` produces a one-AP turn: they may draw one but cannot place.
  This is extremely strong tempo denial even though it does not skip the whole turn.

### Possible interpretation B — draw and placement both cost one action

- [ ] Each player gets 2 AP; both `Draw 1` and `Place 1` cost 1 AP.
- [ ] This permits two placements or draw-plus-placement every turn, fundamentally changing game
  speed, hand pressure, HQ races, first-player advantage, and the value of every existing extra
  placement/draw card.
- [ ] Evaluate how this interpretation changes game speed, hand pressure, HQ races,
  first-player advantage, and existing extra-placement/draw cards.

### Shared action questions

- [ ] Decide whether action modifiers stack and whether actions have minimum/maximum bounds.
- [ ] Decide whether unspent actions expire or can be banked.
- [ ] Decide when victory and region control are checked within a multi-action turn.
- [ ] Define how temporary action loss interacts with exhaustion.
- [ ] Define order for multiple “next turn” modifiers before designing cards.
- [ ] Candidate positive unit: `Battlecry: you have +1 AP next turn.`
- [ ] Candidate denial unit: `Battlecry: your opponent has −1 AP next turn.`
- [ ] Balance both only after choosing Model A or B; their values differ radically.

---

## 3. Ability words before keywords

These patterns may deserve italicized ability words for flavor, but they should not have rules
meaning until repetition proves useful.

- [ ] **Schooling** — bonus while adjacent to another Fish.
- [ ] **Forage** — payoff for being placed adjacent to a Landmark or food region.
- [ ] **Territorial** — reaction when an enemy is placed adjacent.
- [ ] **Scavenge** — reaction when a card/unit is removed.
- [ ] **Brood** — payoff when an Egg is played, removed, incubated, or hatched.

Cards must remain fully understandable without the ability word.

---

## 4. Higher-risk mechanics to hold

- [ ] **Lure/taunt:** forcing legal cover choices changes the action-selection rules globally.
  Do not introduce it for one Anglerfish.
- [ ] **Parasite/attach:** linked cards, shared fate, hidden stack position, and recurring upkeep
  create a subsystem. Revisit only if a full parasite module is selected.
- [ ] **Control theft:** taking ownership of a covered card complicates open decklists, Remove
  Pile ownership, and return-to-hand effects.
- [ ] **Copy a Battlecry:** enumerate every legal source and loop before approving Kanzi or any
  similar design. Copied effects should not count as playing the source card.
- [ ] **Open deck tutors:** continue using random filtered draws or top-card selection. Full-deck
  choice compresses variance and makes future combo cards dangerous.
- [ ] **Permanent action denial:** effects that stop drawing, placing, or all covering for a turn
  can create non-games in a one-action system. Prefer one-unit restrictions with clear answers.
- [ ] **Connection-granting auras:** these can turn an innocent extra placement into an immediate
  HQ capture. Burrow's empty-only self-placement is the safer reach tool.

---

## 5. Landmark rules to settle before expansion

- [ ] A Landmark pays the full card and placement-action cost despite having STR 0 and being
  unable to capture an HQ. Its immediate, recurring, or delayed effect must compensate for all
  three disadvantages; rarity does not do so.
- [ ] Keep Landmarks as non-units that occupy crossroads, participate in connection, cannot
  capture an HQ, and are ignored by text that says “unit.”
- [ ] Confirm that a player may cover their own Landmark normally. Fragile then removes it.
- [ ] Create a type-neutral phrase for a Landmark leaving play. Deathrattle currently applies
  only to units. Candidate wording: `When this leaves the battlefield, ...`
- [ ] Do not make Landmarks Immovable by default; print it only when the delayed engine requires
  protection from abilities.
- [ ] Decide whether filtered “draw a Landmark” effects are allowed. Recommended: yes, using the
  same random filtered-draw rule as tags/rarity.
- [ ] Preserve the current mechanical Apex interaction but change flavor language: an Apex
  Predator **destroys** or **razes** a Landmark rather than eating it.
- [ ] If a Landmark returns to hand, all timers/counters on its battlefield instance are cleared
  unless the effect explicitly preserves them.

## 6. Multi-tag and Egg-tag questions

- [ ] Reconsider whether Eggs may capture an enemy headquarters. The current model treats Eggs as
  units and therefore allows it, but a larger Egg pool turns that flavor wart into a real
  deckbuilding exploit. Recommended: Eggs may occupy crossroads, provide connection, and control
  regions, but **cannot be placed onto an enemy HQ**.
- [ ] A multi-tag card counts for every matching effect. This makes `Bird/Dinosaur`,
  `Egg/Amphibian`, and `Egg/Arachnid` mechanically significant.
- [ ] Decide whether an unhatched Egg should carry the future creature's tag. Recommended first
  test: **yes for constructed synergy, but exclude Eggs from “draw a Bird/Snake/etc.” unless the
  effect explicitly says it can draw Eggs**. Otherwise Bird Egg may recursively find Egg cards.
- [ ] Keep type and tags distinct: Egg is a unit type/subtype even if it also appears in the flat
  tag list.
- [ ] Formalize the narrow Colony caste exception to the one-species rule before adding more ants
  and bees.

### 6.1 Proposed taxonomy expansion

Candidate tags introduced by the expansion slate:

`Insect · Amphibian · Dinosaur · Primate · Rabbit · Marsupial · Cephalopod`

- [ ] Activate a tag only when at least one effect references it or when it is part of a clearly
  approved near-term module. Avoid decorative taxonomy that creates no deckbuilding hook.
- [ ] Keep **Insect** distinct from **Colony**: Colony represents eusocial caste cards; Insect
  covers solitary/non-colony bugs. Individual cards may carry both only when biologically and
  mechanically justified.
- [ ] **Primate, Rabbit, Amphibian, and Dinosaur** have coherent proposed modules and are the
  strongest activation candidates.
- [ ] **Marsupial** and **Cephalopod** are currently thin. Leave those animals tagless unless more
  synergy cards are selected.
- [ ] Do not restore broad `Reptile`; the existing Snake/Lizard split is mechanically useful.

## 7. Trigger-name review

Battlecry and Deathrattle remain placeholder terms. Candidate pair for a later language test:

- [ ] **Arrival:** an effect when the card is placed.
- [ ] **Last Act:** an effect when a unit leaves the battlefield through removal.

Other candidates to test in real card layouts:

- [ ] `On Arrival` / `When Removed` — maximally plain, no keyword flavor burden.
- [ ] `Entrance` / `Legacy`.
- [ ] `Emerge` / `Last Breath` — flavorful, but “Last Breath” reads poorly on Eggs.

Do not rename either keyword until sample cards are laid out side by side; clarity matters more
than novelty.
