# Expansion Card Design — To-Do

Working backlog for growing the card pool beyond the initial 14 designs per archetype. Nothing in this document is locked or canonical until reviewed. Existing deck files remain the source of truth for the launch packages.

The single candidate inventory is [`card-candidates.md`](card-candidates.md), organized only by rarity. This document retains the design reasoning and module context that produced those rows; it is not a separate candidate list. If wording or numbers differ, preserve both as unresolved variants in the consolidated inventory.

The larger pool should force real deckbuilding decisions. New cards should create sidegrades, subpackages, and cross-archetype possibilities—not simply replace the weakest card in every premade list.

## Design guardrails

- [ ] **Non-negotiable no-mana calibration:** every card costs one card and the same placement action. Low strength is a drawback, never a lower price. Start every ground-unit design from Lion (STR 7) and every Flight design from Eagle (STR 5), then exchange body strength only for effect value that matters immediately or reliably.
- [ ] Rarity does not pay for a weak rate. It changes copy count, consistency, and how singular a gameplay pattern may be; a rare STR 3 with a modest effect is still a bad card.
- [ ] Price conditions by reliability. A condition like “if an Egg hatched” cannot repay several missing strength unless the successful effect is correspondingly large.
- [ ] Price delay twice: the player gives up immediate board presence and the opponent receives a window to disrupt the payoff. A STR 0 Egg that later produces one ordinary body is generally worse than playing that body immediately.
- [ ] Count free placements and tokens as action economy. One card creating two bodies, or moving a card directly from deck to battlefield, is powerful even when the individual bodies are small.
- [ ] Build toward at least **20–24 plausible cards per established archetype** before considering the first constructed-card-pool milestone.
- [ ] Preserve the 30-card deck limits: at most 4 legendary and 8 rare cards. Extra designs are choices, not permission to increase those limits.
- [ ] Avoid printing several unconditional body-plus-card-advantage cards. In a place-or-draw economy, a body that replaces itself is already premium.
- [ ] Avoid unrestricted extra placements near an enemy den. Every chaining effect needs an instant-capture audit.
- [ ] Prefer cards that are useful in two homes. Tags should suggest archetypes rather than act as hard classes.
- [ ] Keep Cats expansion cards conditional or narrow until the post-nerf shell is proven fair.
- [ ] Treat food values as placeholders until the shared food scale is re-tested.
- [ ] Promote a new keyword only after at least three cards want the exact same rules object.
- [ ] Run a species-collision check before flavor-lock. Candidate names below are mechanical handles, not promises.

### Required rate check for every candidate

- [ ] **Body ledger:** compare ground cards to Lion 7 and Flight cards to Eagle 5. Record exactly how much strength the effect is buying or adding.
- [ ] **Card ledger:** playing a card subtracts one card; the alternative Draw action adds two. “Draw 1” replaces the played card but does not refund the placement action. A STR 0 card that draws only one card later has lost both tempo and card velocity.
- [ ] **Action ledger:** count every free placement, token, move, and deck-to-board effect. Playing a card from deck is both selection and a saved future placement action.
- [ ] **Delay ledger:** compare the payoff to what an immediate Lion/Eagle would have accomplished during every opponent turn in the waiting window.
- [ ] **Floor/ceiling:** price the card for its common unsuccessful state, not only the screenshot where all family conditions are active.
- [ ] **Closest-card test:** reject a candidate that is strictly or practically dominated by an existing card—or that makes an existing card obsolete without creating a meaningful deckbuilding tradeoff.

---

## 1. Expansion modules for the seven established archetypes

### 1.2 Egg Control — hatching and incubation

Build two alternatives to the current draw/shuffle engine: delayed board hatching and Egg protection. These cards should remain vulnerable to covering.

- [ ] **Turtle Egg** — Egg · STR 0 · Common `Fragile. Hatch 1 — play two Turtle Hatchling tokens (STR 4) on this crossroad and an adjacent empty crossroad.` The delayed payoff must create both total strength and board width; one ordinary STR 5 body would be dramatically worse than playing Lion immediately.

- [ ] **Crocodile Egg** — Egg · STR 0 · Rare `Fragile. Hatch 2 — play a Crocodile token (Lizard, STR 8) on this crossroad. Its Roar removes an adjacent enemy of strength 4 or less.` A delayed premium body plus interaction. Verify that a covered Egg cannot hatch.

- [ ] **Vulture / Crow / other Bird (identity TBD)** — Bird · STR 3 · Rare `Flight. Roar: draw 1 card; if an enemy unit was removed this turn, draw 2 cards instead.`

### 1.4 Ramp — more routes upward, not more finishers

- [ ] **Honeyguide** — Bird · STR 3 · Common `Flight. Roar: gain 6 food; if you control a Bear or Colony unit, gain 4 more.` A bridge card between Ramp, Colony, and future mixed-food decks.

### 1.7 Canines — hand-buff, movement, and pack protection choices

Use distinct wild canid species. Domestic dog breeds are one species and should not silently evade the one-species rule.

- [ ] **Fennec Fox** — Canine · STR 5 · Rare `The first time each turn this gains strength, you may move it to an adjacent empty crossroad.` Turns buffs into board reach without granting an extra placement.

#### Dog/Canine copy-scaling candidate

- [ ] **Dog/Canine identity TBD** — Canine · STR 3 · Common `Roar: give +3 strength to every other copy, wherever they are.`

### 1.8 Movement and mimicry candidates

- [ ] **Parrot** — Bird · STR TBD · rarity TBD Original concept: `Become a copy of the last Common unit your opponent played.`
- [ ] **Legendary Parrot** — named Bird · STR TBD · Legendary Original concept: `Become a copy of the last unit your opponent played.`

---

## 2. Candidate archetype incubators

These are broader card-pool directions, not eighth-through-eleventh premade decks. Prototype small cross-compatible modules first; promote one to a full archetype only after its board play is distinct from the current seven.

### 2.1 Dinosaur Hatch — delayed bodies without food ramp

**Identity:** protect vulnerable Eggs, accelerate Hatch timers, then win through large bodies. Unlike Ramp, it spends time and board space rather than food. Unlike Egg Control, it converts Eggs into units rather than cards and event-food.

Anchor candidates:

- [ ] **Dinosaur Egg** — Egg · STR 0 · Common `Fragile. Hatch 2 — play a random non-Legendary Dinosaur from your deck on this crossroad.`
- [ ] **Oviraptor** — Dinosaur · STR 3 · Common `Roar: draw a random Egg from your deck.`
- [ ] **Velociraptor** — Dinosaur · STR 5 · Common `Roar: if an Egg hatched this turn, draw 1 card.`
- [ ] **Archaeopteryx** — Bird/Dinosaur · STR 4 · Rare `Flight. Roar: incubate an adjacent Egg.`

### 2.4 Venom Control — delayed answers with visible counterplay

**Identity:** mark a visible unit for delayed removal. The opponent gets one turn to cover it, move it, return it, or otherwise break the condition. This creates control decisions without another family of immediate removal Roars.

Anchor candidates:

- [ ] **Cobra** — Snake · STR 3 · Rare `Roar: envenom an adjacent enemy.`
- [ ] **Komodo Dragon** — Lizard · STR 5 · Rare `Roar: envenom an adjacent enemy of strength 5 or less.`
- [ ] **Scorpion** — Arachnid · STR 3 · Common `The first enemy unit that covers this becomes envenomed.`
- [ ] **Poison Dart Frog** — Amphibian · STR 4 · Common `Deathrattle: envenom an adjacent enemy.`
- [ ] **Blue-ringed Octopus** — Cephalopod · STR 3 · Rare `Stealth. Roar: envenom an adjacent enemy of strength 5 or less.`
- [ ] **Mongoose** — STR 5 · Common `Roar: clear Venom from an adjacent friendly unit; otherwise remove an adjacent enemy Snake of any strength.`

---

## 6. Deckbuilding conditions and choose-one (Martin, 2026-10-21/22)

**The small-deck archetype ("your starting deck has no animal of strength 4 or more").** A condition any deck can meet in its own way, so it pulls several lists toward one theme instead of dictating a family's fourteen cards (the Kazakus effect: two or three decks end up good, and nobody is forced into one list). Target at launch: two commons, two rares, one legendary. The Capybara is the first common ("If your starting deck has no other animal of strength 4 or more, this has strength 9"; printed 2). The condition is cheap for decks already small (Colony 25 of 30, Aristocrats 24, Egg Control 25), so its payoffs stay modest. The legendary is the royal-jelly Bee (`bee_legend_2`, Colony, Meadow, 1; name to come): "Roar: your animals on the board, in your hand and in your deck become strength 5." It needs no condition because setting strength chooses its own deck: a nerf in Giants, a feast in Colony; 5 keeps the small deck answerable (a 6 covers it, the Black Mamba removes it). Built on 2026-10-22; the second common and the second rare wait for play to show what the deck lacks. A payoff must be flat: an effect that reads strength either rewards big decks (useless under the condition) or needs no condition at all. Rejected on the way: a cover-protection aura (a prohibition, fun for nobody), "+2 to your small animals" (defensive, and buried animals don't cover back), deck-to-board placement and "gains its neighbours' strength" (both best with big animals), "return adjacent 7s" (strictly worse than Rue), an extra turn (breaks the den race).

- **Seagull** (Coast, later set; čajka), rare, Flight: "Roar: if your starting deck has no animal of strength 4 or more, Scout your opponent's hand." It snatches the sandwich out of your hand: it takes one of three, not the whole hand, which cuts most of the information and keeps the choosing. Waits for Coast, as the Rattlesnake waits for Desert; it is no city bird.
- **"Dawn: your next Roar this turn happens twice."** A parrot legendary (mimicry, the dawn racket; the Macaw is the rare), left unconditional: Roars live on small cards anyway, so the condition would cost nothing. The Woodpecker's "your next Roar this turn happens twice" then needs a new effect.

**Choose-one cards, their own design session.** Skill-rewarding and healthy in every card game that has them, as long as the options are balanced. Not to be spent on a deck condition: a group of animals (a family or a subgroup) gets it as its signature, the way Primates own the hand buffs and parrots own repetition. Commons choose between 2, rares 2–3, legendaries 3–4; a handful at each rarity, not the whole pool.

**Costlier conditions, a later set.** Singleton (Reno, Kazakus), ten different strengths in the starting deck, ten different families. Gwent's Shupe and Syanna show how much fun they are when the payoff is unique and big; Kazakus is the model, Reno was toxic (Martin).
