# Aggro HQ Rush redesign session — 2026-07-15

## Identity

**Aggro HQ Rush is a Rodent-led forward-pathing deck that converts one defended HQ-front crossroad into an immediate capture; it wins by holding a fragile beachhead long enough to do that and loses when walls, removal, or stabilization deny that beachhead.**

This is a design proposal only. Names, strength values, and exact wording are provisional; nothing below is ready to ship. It does not authorize a deck, data, engine, configuration, or bot change.

## Governing facts and scope

The current game is two actions per turn, with a Draw action drawing two cards. A unit captures the HQ immediately when placed there; normal placement needs a connected chain, while Flight only ignores that connection for the flying unit. Strength is relevant to covering and holding a crossroad, not to dealing damage. These are the constraints for this proposal, not the historical draw-1 assumptions in the earlier Aggro redesign document. See the [mental model](../rules/mental-model.md#the-whole-system-in-one-breath) and its [connection and strength rules](../rules/mental-model.md#the-board-is-a-graph-placement-is-gated-by-connection).

The current 4-4-6 list is a source of roles and candidates, not a claim that every current card belongs in the redesign ([current deck](decks/aggro-hq-rush.md)). The recommendation below still uses a 30-card, 4-4-6 test deck so it is comparable to the existing decks. A larger candidate pool is useful for deckbuilding, but should not be mistaken for an instruction to add all of its cards.

## Ranked diagnosis

| Rank | Failure mode | Diagnosis | Design consequence |
|---:|---|---|---|
| 1 | **Convert the HQ-front blocker** | This is the decisive failure. With two actions, a card that clears a blocker but does not occupy its crossroad often requires clear, occupy, then capture, which cannot happen in one turn. Existing Pestis is the clearest example. | The deck needs one narrow cover-any-wall conversion tool, plus only removal that rides on a placement it already wanted to make. |
| 2 | **Reach and hold the HQ front** | A normal chain has to survive until it reaches the front. Flight can make a beachhead but does not connect a later HQ capture by itself. A single removal or larger wall should be able to end the attempt. | Reward a real occupied HQ-front crossroad, not merely playing a flyer near it; use forward-only Rodent bodies and chaining. |
| 3 | **Exploit a real opening** | Once a front is held, the deck must turn that state into pressure before the defender re-establishes a wall. Current bounce and whole-stack effects can be too situational because they do not reliably convert their opening into connection. | Extra placement and removal must be front- or sequence-fenced; no unrestricted placement and no Flight-plus-capture shortcut. |
| 4 | **Refill** | Draw 2 makes refill materially less urgent than the historical draw-1 analysis suggests. The deck still needs enough cards to continue a committed push, but its primary answer should be efficient, conditional pressure, not a generic draw suite or a late-game engine. | One front-gated Rodent draw rider may be tested, but it must at least beat the Scout comparison rather than asking the fence to pay for a weak body. Empty-hand payoff remains optional and risky rather than a core repair. |

This order follows the earlier diagnosis that clearing without occupying fails the two-action test and that strong conditions must be difficult for a reactive pile to fake ([Aggro redesign, sections 4–5](../balance/aggro-redesign.md#4-new-card-suggestions)). It also applies the rule that only top-of-stack occupants provide connection ([mental model](../rules/mental-model.md#the-board-is-a-graph-placement-is-gated-by-connection)).

### Evidence versus bot blind spot

The first three failures are rule-structure claims; they can be demonstrated from a board position without any bot. The claim that Aggro cannot reach row-1/3 HQ lanes is not yet a card diagnosis: both production bot families are documented as over-valuing the row-2 spine and under-contesting those lanes ([project status, Bots — known blind spots](../STATUS.md)). Therefore:

- Treat a low use rate of a row-1/3 route as a pilot hypothesis until RefereeBot replays and deliberately constructed lane positions agree with it.
- Treat a card as a card problem when the same legal front/capture sequence is unattractive or fails under RefereeBot and inspected replays, not merely when TurnBot misses it.
- Do not weaken a wall or a rush card to compensate for a bot that never recognizes the lane.

## One deck, three mechanisms

The deck is not “Rodents plus good cards.” Its mechanisms depend on one another:

1. **Forward Rodent pressure.** Lemming, Jerboa, Sapper Mole, and a small number of neutral bodies establish a connected line and make a front worth defending.
2. **Front-state payoff.** Ratcatcher, Cheetah’s rework, Warren General, and conditional Skunk only pay when an HQ-front unit already exists. They make holding the front urgent, but do not create it from safety.
3. **Conversion.** Weasel covers the last front wall regardless of strength and remains exposed; Scurry turns a two-placement turn into bounded removal plus a body. They make an earned opening actionable, rather than providing generic removal.

Dependency map:

    connected Rodent line / width
                |
                v
    occupied HQ-front crossroad -- removed or covered --> attempt ends
                |
         front-gated draw, free Rodent, bounce
                |
                v
    last wall at the HQ front
                |
         Weasel covers it while occupying the crossroad
                |
                v
    normal connected placement on enemy HQ -> immediate win

There is deliberately no arrow from Flight, empty-crossroad placement, or removal directly to capture. Flight can establish a unit but cannot establish the ordinary connected HQ path; a cleared wall that remains unoccupied does not complete the map. This preserves the hard guards already identified for this archetype ([Aggro deck — rejected designs](decks/aggro-hq-rush.md#open-items--resolved-2026-06-28)).

## Recommended first 30-card direction

The test deck uses approximately **21 committed slots / 9 neutral-support slots**. “Neutral” here does not mean automatically good: each is included because it improves an action-efficiency or board-state problem in this particular rush plan. The present 4-4-6 shape yields this exact slot sketch:

| Rarity | 30-card direction | Slots | Role and disposition |
|---|---|---:|---|
| Legendary | Warren General — addition; King Ratbeard — addition; Sirocco — retain only as a conditional front-opening test; Verminus — retain | 4 committed 3 / neutral 1 | General sustains an earned front. Ratbeard is the all-in payoff. Verminus is the one neutral swarm finisher. Sirocco must prove it converts a front rather than merely bounces value; otherwise retire it. |
| Rare | Weasel — addition; Jerboa — retain; Skunk — front-gated rework; Chameleon — retain | 8 committed 6 / neutral 2 | Weasel is the actual conversion card; Jerboa supplies a placement chain. Rework Skunk to require an existing HQ-front unit before its bounce/lock. Chameleon stays as limited flexible stack play, not an identity card. |
| Common | Sapper Mole — addition; Ratcatcher — addition; Scurry — addition; Cheetah — rework; Lemming — retain; Mouse — retain | 18 committed 12 / neutral 6 | The first four are the pressure/conversion backbone. Lemming supplies width; Mouse is limited Rodent consistency. |

This is a direction to construct and test, not a declaration that every retained card survives. The current **Rat** is retired to a future discard theme; **Hornet** is retired from this list rather than preserving generic flying removal; **Pestis** is retired because it embodies the clear-without-occupy trap; and **Gale** is deferred pending a separate rework, because a large unconditional flyer is poor identity fit. Every candidate below must identify its closest existing comparator or comparators, then clear a body, card, action, and condition ledger against them. Lion (STR 7), Scout (STR 5, draw 1), and Chameleon are the relevant comparisons for several first-wave cards, not a fixed universal checklist. This is the project-required closest-card test, not optional polish ([expansion design to-do, guardrails and rate check](expansion-design-todo.md#design-guardrails)).

### Six first-wave additions

These six are the only new designs recommended for the first test. Values marked with a question mark are tuning placeholders, not balance numbers.

| Card | Fence | Payoff | Floor | Counterplay |
|---|---|---|---|---|
| **Warren General** — Rodent, STR 4?, Legendary | At the start of your turn, it requires a unit you control adjacent to the enemy HQ. | Place one Rodent from hand for free on an **empty non-HQ** crossroad adjacent to that unit. | A vanilla-ish STR 4 when the front is absent; it cannot auto-place on the HQ. | Remove/cover the front unit, wall the adjacent empty crossroads, or remove General before the next turn. |
| **King Ratbeard** — Rodent, STR 4?, Legendary | Other Rodents gain +X strength only while you have no cards in hand. | Turns a fully committed swarm into a temporary wall-breaking threat. | STR 4 and no team benefit while holding cards; draw 2 makes empty hand a real commitment rather than a default state. | Force a draw/hold decision, remove the King, or answer the board before it is empty. It neither reaches nor captures the HQ. |
| **Weasel** — Rodent, STR 5?, Rare | May cover an enemy regardless of strength **only if that enemy is adjacent to the enemy HQ**. | Occupies the decisive crossroad with the first action, leaving a normal connected HQ placement as the second. | A real STR 5 body outside the conversion, rather than a weaker Chameleon. The front-only fence gives up Chameleon’s all-board flexibility. | Remove or cover Weasel; the buried wall resurfaces. It cannot be used as generic removal or placed directly on HQ. |
| **Sapper Mole** — Rodent, STR 9?, Common | Can be placed only adjacent to an enemy unit or the enemy HQ. | A true front-only battering ram: it can cover ordinary Lion-sized and STR 8 walls, so the placement fence buys a real gain over a vanilla STR 7. | Dead in hand while the player has not advanced; it is not a general STR 9. | Present a STR 9+ wall, remove it, or deny legal forward placement. The starting STR 9 is a hypothesis to test, not a claim that STR 6 was acceptable. |
| **Ratcatcher** — Rodent, STR 5?, Common | Battlecry requires a friendly unit adjacent to the enemy HQ. | Draw two random Rodents, repaying the card and improving the next pressure turn only after the front is earned. | A Scout-sized STR 5 with no draw when the condition is absent. | Clear the front or force the rush to spend its actions rebuilding instead of taking the conditional refill. It must prove that the front condition and Rodent restriction are worth its extra card relative to Scout. |
| **Scurry** — Rodent, STR 2?, Common | Battlecry works only if **two or more other units** were placed this turn; remove an adjacent enemy of strength X or less. | Bounded removal rides on the third-or-later body of a genuine chain, rather than being trivial in an ordinary two-placement turn. | A STR 2 if the chain or target is unavailable. | Present a wall above X, stop the Jerboa/Lemming-style chain, or remove its forward setup. Scurry does not ignore connection or occupy the removed enemy’s crossroad. |

### Rework tests, not additions

- **Cheetah:** retain the HQ intent but change its cantrip condition from “this was placed next to HQ” to “you control another unit next to HQ”; test STR 5–6 and a one-card draw. Its fence is an existing beachhead, so Flight cannot counterfeit it.
- **Skunk:** retain bounce only if its effect requires an existing friendly HQ-front unit. Its job is to make an already connected front harder to stabilize against, not to be a universally useful bounce card. It remains a test because bounce does not itself occupy the newly open crossroad.
- **Sirocco:** retain as a one-of only for the first list, with the same success criterion: replay evidence must show that its bounce creates captures rather than merely delaying the opponent.

## Larger pool, with a gate

The long-term pool may expand to at most **6 legendaries, 12 rares, and 18 commons**. That is a deckbuilding reservoir, not a 36-card recommendation and not a request to implement 36 cards. After the six first-wave additions, stage candidates by mechanism:

| Mechanism | Later candidates | Gate before promotion |
|---|---|---|
| Forward pressure | Prairie Dog, Warren Rally, Mole/Burrow, Springhare | Must create legal pressure without granting an unconnected HQ capture; Burrow remains empty-crossroad only. |
| Front payoff | Vanguard Vole, Shrike, a narrowed Cheetah variant | Must require a pre-existing HQ-front state rather than be satisfied by Flight alone. |
| Conversion / disruption | Plague Warden, Mongoose, Bombardier Beetle, a Hornet replacement | Must occupy as it clears or be bounded to a placement sequence; no unrestricted removal donor. |
| Neutral support | alternate Rodent consistency, stack-flex cards, limited flyers | Must improve a real action/pathing role in Aggro without being an automatic inclusion in slow decks. |

Starling and any other multi-flyer extra-placement burst are explicitly held behind a two-card and three-card HQ-capture search. The expansion queue already identifies that risk, as well as the empty-only requirement for Burrow ([expansion to-do, Aggro alternatives](expansion-design-todo.md#16-aggro--alternative-rush-packages)).

## RPS hypothesis

| Role | Hypothesis | Expected game pattern |
|---|---|---|
| **Prey** | Slow, greedy, food-scaling, or value-first decks that spend early actions drawing, building delayed value, or deploying a single insufficient front defense. | Aggro takes a lane, establishes an HQ-front unit, and forces the opponent to answer immediately; Weasel converts one late wall. |
| **Predator** | Decks with repeated cheap removal, durable/high-strength HQ-front walls, or stabilizers that can erase the beachhead while continuing their own plan. | Aggro spends actions rebuilding the chain; its front-gated cards become weak floors and it exhausts before a conversion window. |
| **Weak-matchup signature** | The rush loses clearly, not narrowly, when its initial front is removed or covered twice. | It has no broad late-game draw engine, no unrestricted placement, and no generic answer to every wall. A high overall rate with no such losing pattern is evidence that a fence failed. |

The aim is therefore an RPS relationship, not simply a higher aggregate win rate—the acceptance rule stated in the earlier redesign ([Aggro redesign, section 5.5](../balance/aggro-redesign.md#55-testing--acceptance)).

## Later validation plan

No simulation is requested in this design session. Once an implemented candidate list exists:

1. **Rule and burst safety first.** Exhaustively inspect the legal two-card and three-card sequences involving Flight, free placement, Weasel, and any later Burrow/Starling candidate. Confirm no sequence gains an unconnected or automatic HQ capture, and confirm General cannot place on HQ.
2. **Pilot-aware matchup cohort.** Run TurnBot and RefereeBot separately, at **at least 200 games per matchup**, paired seeds, and both seats. Compare the 30-card list with every premade deck and with variants that replace each first-wave card by its closest retained role.
3. **Inspect pathing, not only win rates.** Log/replay the games. Record HQ-front reaches, front turns held, conversion attempts, successful capture after a conversion, and whether the decisive route used row 1, 2, or 3.
4. **Bot-blind-spot control.** Give both pilots a small, fixed set of row-1/3 HQ-lane positions. If RefereeBot routinely finds a line TurnBot misses, classify the delta as a bot issue. If both decline the line or the line fails after replay, revise the card/pathing hypothesis.
5. **RPS and decomposability check.** Require both a plausible prey and a credible predator. Test whether the six additions appear in a no-synergy/goodstuff optimizer; a card that remains dominant without the Rodent-front package has failed its fence and should be narrowed rather than merely numerically nerfed.

TurnBot is useful for directional triage but is not an oracle, so no balance conclusion should be drawn from its results alone ([project status, Bots](../STATUS.md)). This plan also follows the project-wide requirement for paired, both-seat cohorts of 200 or more games per matchup.
