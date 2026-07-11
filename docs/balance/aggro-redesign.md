
## 1. Card design principles

This game is vastly different from most traditional card games (like Magic or Hearthstone). This is for 2 main reasons:

1. The are no colors/classes, and every single card can be theoretically used in combination with every single card.
2. There is no mana system, so all cards have equal "cost" to play -- consuming one action.

When it comes to designing cards, this leads to 4 core principles:

### 1.1 Card strength must be paired with commitment.
- Playing the strongest cards must require some form of commitment. In games like Hearthstone/Magic this is done with classes/color, but we can't do that. In our case, it must be a commitment to deck theme/archetype. For example, playing aggresively for the HQ capture, or playing the control, attrition game, etc.
- Cards without any required commitment must be generally weaker (the "neutral tax" from games like Hearthstone). And so, if card is unconditionally good, it can't be better than conditionally good card with the same core effect.

### 1.2 Conditional cards must have higher ceiling, but lower floor.
- Yes, when a conditional card works, it should be stronger than a "neutral" one. However, there must be inherit *tradeoff* associated with playing the card -- if the condition is not met, the card should be weaker than a neutral, unconditional conuter part.
- a good idea when judging a card is comparing it to unconditional, "neutral" card -- for example, a 7-strength vanilla (Lion), or a 2-strength "Battlecry: Play another unit" (Jerboa).

### 1.3 A Rock-Paper-Scissors dynamic must emerge
- this should be inheritly baked into card design, paired with the fact that strong cards cost you *commitment* -- if the card (and therefore deck archetype) is naturally strong against certain cards/strategies, it needs to be weak against other type of cards/strategies.

### 1.4 Cards should reward skill
- (a) skillful dekcbuilding -> creating deck strong against the whole "meta", across many different decks and archetypes
- (b) long- term strategic planning -> seeing the matchup, realizing what the win conditions for boths decks are, and ajusting the strategy accordingly 
- (c) in-game tactical decisions -> small, turn-by-turn play, clever manouvering, squeezing the maximum win % of of each individual game and position

## 2. Current Card Analysis

Now, we shall analyze current cards in the Aggro deck through the lens we just established. I will do it in order common -> rare -> legendary, since commons should be the most load-bearing part of the decks. For each card, we will answer 3 questions:

1. How good/bad is this card? (from actually playing with/against it)
2. At it's core, is this a "neutral" card, or an "aggro, HQ rush" card? How (un)conditional is it?
3. How well does it fit this deck? How well does it fit a "goodstuff" deck, and other archetypes?
4. Does the card need to change? If so, how and why?

### 2.1 Commons

Here are current 6 common cards:

⚪  lemming             Rodent · STR 1 · Battlecry: place all Lemmings from your hand and deck on random adjacent empty crossroads.
⚪  mouse               Rodent · STR 1 · Battlecry: draw a Rodent.
⚪  bat                 - · STR 2 · Flight. Battlecry: draw 1 card.
⚪  rat                 Rodent · STR 2 · Battlecry: remove a card in your hand to destroy an adjacent enemy unit.
⚪  falcon              Bird · STR 4 · Flight. Battlecry: if you play this next to the opponent's base, draw 1 card.
⚪  cheetah             Cat · STR 5 · Battlecry: if you play this next to the opponent's base, draw 1 card.

Let's talk about them one by one now:

#### 2.1.1 Lemming
- this is a very good card, one of the best ones in the deck. Although it might not be obvious, getting 3 bodies in 1 action is great, alongside some deck-thinning.
- it's more of a "neutral card" that happens to be good in aggro, rather than a dedicated HQ-rush card
- I can see this being a staple in many aggro or midrange decks, and also in token decks. I don't see this being played in control/ramp decks.
- The card is defnitely not weak. But also, I don't think it's too oppressive, and I don't see any soft way to make it a bit less strong. It's just a good card, I'm happy to keep it that way.


#### 2.1.2 Mouse
- unconditional, tribe-specific draw
- again, a strong card, but I don't think it's toxic or too oppresive, and we literally can't make it any weaker since it already has strength 1
- more of a "neutral card" that happens to be good in this deck, rather than a dedicated HQ rush card
- I can see this being played in heavy Rodent decks, from aggro to combo to midrange, but also in control decks that want to tutor a specific Rodent. It's possible this might become auto-include in a lot of deck, similar to many other "draw a card" unit -- changing "draw cards" action from drawing 1 card to drawing 2 cards could help with this, I think 


#### 2.1.3 Bat
- unconditional draw that's also a flyer
- again, neutral card that's played in aggro
- unlike Mouse, I can see this being played in every single deck, regardless of the tribe or archetype ... the card is simply very strong a flyer with 2 strength can cover enemy backline threats, and the fact it gives a card makes it always strictly better than "draw 1 card" action -- again, chaging the defauly action to "draw 2 cards" could help with this
- possible nerf -- make it 1 strength instead of 2. If that doesn't help, then maybe having a neutral flyer that draw a card unconditionally is not the best idea (speaking of which, Owl isstrictly better version or Bat, isn't it?)


#### 2.1.4 Rat
- from experience, one of the worst cards in the deck, you are rarely hapy to draw it
- paying 1 card to remove one unit is simply too much, you lose too much value
- I would put this card aside for now, and later on maybe develop some "discard card from hand" synnergies ... I could see some aggro self-discard deck working (or maybe also a control self+opponent discard deck, played around Black Swan maybe)


#### 2.1.5 Falcon
- good card, one of the best ones in the deck
- it is technically conditional, but in reality you can almost always get the +1 card from it ... and then it's just a stronger Bat
- this feels definitely more like a deciated HQ rush card than a neutral one -- I think the only reason it saw play even in the "goodstuff" decks is that Flying is a very streong keyword, and at 4 strength this was quite strong
- I suggest nerfing this to 3 strength, or maybe even 2 strength -- you're not really supposed to look for "value trades" with this card, just to drop it near enemy base early on, let him cover it, and then remove the unit covering this and have a connection ready for the finishing move


#### 2.1.6 Cheetah
- definitely an aggro HQ rush card rather than a neutral one
- the idea is good, but the problem is that the card it *too conditional*, and the upside insn't worth it
- too often during actual play, the card ended up being totally dead in hand, or it had to be played as a vanilla 5 strength, which is obviously horrible
- I like the effect and the flavor, but if it's supposed to stay relevant, we need to buff it
- some ideas (some of these could become other, separate cards):
    - buff strength from 5 to 6 (we can't go up to 7 strength, because then it's strictly better than Lion)
    - change effect to "has +3 strength when played next to enemy HQ"
    - change effect to "Battlecry: Draw 1 card if you have a unit next to enemy HQ"



### 2.2 Rares

4 rare cards currently being used in the deck:

🔵  jerboa              Rodent · STR 2 · Battlecry: play another unit.
🔵  hornet              - · STR 2 · Flight. Battlecry: you may remove another Hornet from your hand or deck. If you do, 
destroy an adjacent enemy unit.
🔵  skunk               - · STR 4 · Return an adjacent enemy to your opponent's hand. They can't play it next turn.
🔵  chameleon           Lizard · STR dynamic · May be placed on any unit, and any unit may be placed on top of it.

Let's go over them one by one:

#### 2.2.1 Jerboa
- one of the purest "aggro HQ rush" cards in the deck
- understandably one of the highest-winrate cards in the deck, but I don't think it's too oppresive
- I can't see this being played in "goodstuff" decks, since while the card is free tempo, it's not free value (it costs you one card to play it)

#### 2.2.2 Hornet
- one of the strongest cards in the deck
- infinitely better compared to Rat
- I have to say tho, this is a no-condition neutral card, that works in pretty much every single deck ... it's essentially a "remove a unit" card (since it has flying, you just need 1 empty crossroad next to a unit you want to remove)
- to be honest, it fits more in a control remove deck, rather than an aggro deck ... and while I definitely agree that aggro needs some removal, I think we can do better than this
- one possible idea: equivalent to "silence", which could be putting the card that's on top of the stack on the bottom, or something like that?

#### 2.2.3 Skunk
- feels more like an aggro card rather than a neutral one -- the value is low, while the tempo is high, which is exactly what you want in an aggro deck
- however, in practice this turned out to be a dead card most of the time (second lowest winrate in the deck), too clunky and conditional
- one problem is that you only want to play this when going for the finish ... and 90% of the time, you need to play this on top of one of your units ... so it's only good in EXACTLY the situation where there is a single opponent's blocker standing between you and HQ, and you remove it with 1st action, and then capture HQ with second action
- not sure how (and if) we should buff this card ... I'm fine with keeping it as it as, and trying to make the aggro HQ better in general, and seeing if it helps

#### 2.2.4 Chameleon
- not an aggro card, more like a neutral flexibiel card that could be played anywhere, but is only good in handful of decks
- one of the lowest winrate cards in the deck, but I like the effect, it's super unique, plus the card isn't toxic and I can't see it being oppressive ever ... I don't think this needs any changes

### 2.3 Legendaries

4 legendaries currently being used in the deck:

🟡  verminus            Rodent · STR 3 · Has +1 strength for each other unit you control.
🟡  sirocco             - · STR 5 · Battlecry: return all enemy units adjacent to this to their owner's hand.
🟡  gale                Bird · STR 6 · Flight. The first time an enemy unit covers this, return that enemy unit to its owner's hand.
🟡  pestis              Rodent · STR 3 · Battlecry: remove everything from an adjacent crossroad.

#### 2.3.1 Verminus
- strongest legendary in the deck (but to be honest, other 3 are quite underwhelming)
- definitely feels like a neutral card, rather than a dedicated aggro HQ rush card
- I can see this being played in any token or aggro deck (which is fine, as long as this card is not too oppressive, which from the testing it doesn't seem to be)
- nothing wrong with it, just a big body (importantly, conditional) ... there's a lot of counterplay to this, so I'm not worried about the card being too strong
- this card can stay as it is, I wouldn't change anything about it
- the only question is whether this should even be a legendary (then again, we have a legendary like this for Colony and Canine deck. so at least we're being consistent)

#### 2.3.2 Sirocco
- similar to Skunk -- pretty much everything true for Skunk is true here (both good and bad)

#### 2.3.3 Gale
- strong card for sure, even made it into one of the 3 strongest "goodstuff" decks
- effect is good for an aggro card, but at 6 strength (and Flying), it's simply too much value even in slower decks
- the effect doesn't feel legendary (compared to some other Legendaries, like Princess Lea/Prince Leo for example)
- a solution to all this might be to nerf strength (down to let's say 4), and changing the card to rare or even common

#### 2.3.4 Pestis
- in practice, this turned out to be too clunky and situational
- it suffers from the same problem as Skunk and Sirocco -> most of the time, you have to playing on top of your own unit to remove a big blocker ... but in this case, it's even worse, because you clear everything from the crossroad, including your own units. And so, in a 2-action turn, you spend 1 action clearing the blocker with Pestis, then another action putting a unit on the emtpy crossroad, and you have no action left to capture the base. In his turn, your opponent can just cover the unit you just played, and essentially negate your 2-action turn.
- as the card stands, I think it's better fit to a control/remove deck rather than an aggro one


## 3. Deck Analysis

Based on the above, here's how I see the situation with Aggro HQ Rush deck:

- too little aggro-specific cards
- all the best cards are simply strong neutral cards
- legenaries are underwhelming, and their effect are not that unique (compared to some of the best legendaries we have, like Ember, Prince Leo/Princess Lea or Scrooge)

## 4. New Card Suggestions

First of all, an important note: nothing is forcing us to stick to only 4 legenaries, only 4 rares and only 6 commons. It's okay to create more cards than decks, and then test various decks to find out what works and what doesn't work. That being said, here are some suggestions:

All strength values below are **starting proposals** marked with `?` — the real numbers get
tuned in `config.py` under sim, never hard-coded. Every card is built to two rules we agreed on:
**(1) carrot + fence ship together** (a payoff *and* a hard, aggro-only condition), and **(2) it
sharpens the weakness** — each card gets *worse* against a wall / against removal / when the race
stalls, and none of them grant resilience or a late game.

The condition each card keys on is a **legible board state a greedy/reactive deck structurally
can't fake**: *adjacent to the enemy HQ*, *adjacent to an enemy unit* ("in the fight"),
*empty hand*, *another unit placed this turn*, or *Rodent commitment*.

### 4.1 New Legendaries

Legendaries should be **splashy and identity-defining** (the current four are anthems/riders that
don't read legendary). These are engines, bursts, and finishers, not big bodies with a footnote.

🟡 **Warren General** — Rodent · STR 4? · *At the start of your turn, if you control a unit adjacent to the enemy HQ, place a Rodent from your hand for free onto a crossroad adjacent to that unit.*
- **Persistent assault engine.** Snowballs the rush turn over turn, but only while you hold the front — a durdle deck never turns it on, and it dies the moment your beachhead is swept. Skill: protecting the front unit to keep the engine online. The "reward repeated front pressure" idea made into an ongoing engine.

🟡 **Stampede** — Rodent · STR 1? · *Battlecry: place all Rodents from your hand onto empty crossroads adjacent to this or to each other (they need not be connected).*
- **One-shot forward burst.** Dumps your hand into a forward cluster in a single action — instantly builds the beachhead. High ceiling, near-zero floor (dead with no Rodents in hand). The reach ("need not be connected") builds presence but **cannot capture** (the HQ connection rule still holds), so it's a big tempo swing the opponent answers with removal — the fragility is the point. Pairs with King Ratbeard.

🟡 **Rabid Alpha** — tagless · STR 9? · *May be placed on any enemy unit regardless of its strength (covering it). At the start of each of your turns, this loses 1 strength.*
- **Melting battering ram.** Crashes through *any* wall and occupies the front in one action — then melts, so you must convert now. Fuses the conversion tool with the burnout fence: no value to a slow deck (it just rots), maximal value on the turn you punch through.

🟡 **Plague Warden** — Rodent · STR 5? · *Apex Predator. Battlecry: also remove all other enemy units adjacent to this.*
- **The Pestis fix.** Old Pestis wasted an action because clearing ≠ occupying (2-action trap). This *occupies as it clears*: eats the blocker (Apex), takes its crossroad, and wipes the rest of the HQ-front — one action, then capture next action. Enemy-only (never nukes your own chain). Only playable when there's a blocker to land on — exactly when you want it.

🟡 **King Ratbeard** — Rodent · STR 4? · *Your other Rodents have +X strength while you have no cards in hand.*
- **All-in capstone.** When you've dumped everything onto the board, the whole swarm becomes lethal — a team-wide empty-hand alpha strike. Does nothing while you hold cards or are behind. Pairs with Stampede (dump hand → whole board swells). The team-scale Cornered Rat.

### 4.2 New Rares

🔵 **Weasel** — Rodent · STR 1? · *May be placed on top of an enemy unit regardless of its strength (covering it). Can only be placed adjacent to the enemy HQ.*
- **The conversion scalpel.** Punches through the last HQ-front blocker with a weakling, in one action, so you occupy the front (connected) and capture on your second action — the direct answer to the 2-action problem. Front-only, so un-splashable. Buries rather than removes (blocker resurfaces if the Weasel is removed) — the aggro fragility we want.

🔵 **Vanguard Vole** — Rodent · STR 2? · *Whenever you place a unit adjacent to the enemy HQ, give this +X strength (wherever it is).*
- **Front-pressure escalator** (Rattlesnake pattern). Starts as chaff, *earns* its way into the finisher that out-muscles the fat wall — paid for by sustained front pressure. A deck that never reaches the front never grows it.

🔵 **Warren Rally** — Rodent · STR 2? · *Battlecry: place a Rodent from your hand onto a crossroad adjacent to this (it need not be connected).*
- **Fenced chain-extender.** One action → two forward bodies, but Rodent-locked and directional (extends *your* line), so it's tempo a goodstuff pile can't cleanly borrow — the faction-by-incentive version of Jerboa.

🔵 **Rabid Pack** — Rodent · STR 2? · *Battlecry: if you have no cards in hand, place two Rodents from your deck onto crossroads adjacent to this.*
- **Empty-hand deck-burst.** Rewards going fully all-in with a tempo explosion pulled straight from the deck. Hoarding piles can't switch it on; sharpens the deck-out clock (a real cost).

🔵 **Mongoose** — tagless · STR 4? · *Battlecry: remove all effects and keywords from an adjacent enemy unit.*
- **Silence / tech disruption** (the Hornet-rework idea). Strips Immovable / "can't be covered" / anthem off a defensive wall so you can punch through — answers the exact cards that hard-counter the rush, and does little against a board with no defensive tech.

### 4.3 New Commons

Commons are the load-bearing backbone — simple, aggressive, all hard-fenced to the plan.

⚪ **Sapper Mole** — Rodent · STR 6? · *Can only be placed adjacent to an enemy unit or the enemy HQ.*
- **The pure fence.** A big body for a common — *but* only deployable at the front, so it's a dead card in any deck that isn't already forward. The clean §1.1/§1.2 illustration: above-rate body, brutal access condition, zero splash value.

⚪ **Scurry** — Rodent · STR 2? · *Battlecry: if you placed another unit earlier this turn, remove an adjacent enemy of strength X or less.*
- **Tempo-burst removal** stapled to a body you were placing anyway — removal that *doesn't* cost the extra action to exploit. Rewards the multi-place chain; a one-place-per-turn deck whiffs the condition.

⚪ **Ratcatcher** — Rodent · STR 1? · *Battlecry: if you control a unit adjacent to the enemy HQ, draw a Rodent.*
- **The Falcon-fix.** Same "draw when you're at the front" idea, but with a *correctly hard* condition (decoupled from this card's own placement, so Flight can't make it trivial). A greedy deck can't meet it; an executing aggro deck always can.

⚪ **Cornered Rat** — Rodent · STR 1? · *Has +X strength while you have 1 or fewer cards in hand.*
- **Empty-hand berserker.** Turns "I'm out of gas" into "I'm most dangerous." Dead the moment you hold cards up. (With draw-1 kept, empty-hand states stay as reachable as today.)

⚪ **Shrike** — Bird · STR 2? · *Flight. Battlecry: if placed adjacent to the enemy HQ, give an adjacent friendly unit +X strength.*
- **Fenced reach** (the anti-Bat). A flyer whose payoff requires committing it to the front, where it pumps your brawler to cover the HQ-front blocker — reach that *enables the punch* instead of an unconditional cantrip good in every deck.

## 5. Agreed Changes

Checklist of everything we've locked in. Ordered so effects stay attributable (global rule first,
re-baseline, then cards).

### 5.1 Principle addenda — fold into §1 before designing more cards
- [ ] **Condition *difficulty* is the real lever, not condition presence.** An easy-to-meet condition (esp. one Flight satisfies for free — see Falcon) is a neutral card dodging the neutral tax. The condition must be one a greedy/reactive deck structurally can't meet.
- [ ] **Carrot and fence ship together.** A fence with no payoff is just committed-and-weak (today's disruption suite); a payoff with no fence is a goodstuff donor.
- [ ] **Sharpen the weakness, never hedge it.** Aggro cards should get *worse* vs walls/removal/durdle. **No resilience, no late game** (the Colony lesson: a steadier deck loses its RPS relationships).
- [ ] **Removal must not cost the tempo to exploit it.** In a 2-action turn, "clear then occupy then capture" doesn't fit. Removal has to *occupy as it clears* (Weasel, Plague Warden) or ride a body you were placing anyway (Scurry).

### 5.2 Draw rule — DECIDED: keep draw 1
- **Draw action stays 1 card** (the shipped default; 2 actions/turn unchanged). Draw-2 was
  considered as a game-health change (it would smooth the topdeck non-decision) but **rejected for
  cleanliness** — one card per draw is simpler and we'd rather not carry the extra tempo/exhaustion
  complexity or the re-baseline it forces. Revisit only on a *serious* reason.
- **Accepted cost:** the empty-hand "topdeck" turn stays a low-agency spot. That's a known
  tradeoff, not an oversight.
- Consequence for design: no global re-baseline needed, and the draw-family benchmark can be pinned
  directly (no rule dependency).

### 5.3 Existing-card changes
- [ ] **Gale** — nerf STR (6→4?) and demote legendary → rare/common; effect doesn't read legendary and a 6-str flyer is neutral value in slow decks.
- [ ] **Falcon** — nerf STR (4→3 or 2); condition is too easy (Flight meets it for free), so it's a neutral card in a conditional costume. Body should be weak when *not* rushing.
- [ ] **Cheetah** — buff/rework (too conditional, often dead). Test candidates: STR 5→6 (not 7 = Lion); or "+X strength when placed next to enemy HQ" (threat, not cantrip); or "draw if you control a unit next to enemy HQ" (Ratcatcher-style decoupled condition).
- [ ] **Bat** — tax the unconditional flyer+draw: STR 2→1, or add a condition. (Check the Owl overlap — is Owl a strictly-better Bat?) Do **not** fix this via a global draw change.
- [ ] **Rat** — cut from the deck; shelve for a future discard/self-mill theme.
- [ ] **Hornet** — rework off "neutral flying removal"; direction = fenced tempo disruption (see Mongoose / silence).
- [ ] **Skunk / Sirocco / Pestis** — the finish-only / 2-action-trap cards. Pestis is superseded by Plague Warden. Re-evaluate Skunk & Sirocco *after* the general aggro buffs land; cut or rework if still dead.
- [ ] **Keep as-is:** Verminus, Chameleon, Lemming, Mouse, Jerboa.

### 5.4 New cards — prototype (§4)
- [ ] Implement the 15 designs (5 leg / 5 rare / 5 common) as tunable entries; strengths start at the `?` proposals.
- [ ] Load-bearing trio to build first: **Weasel** (conversion), **Warren General** (engine), **Sapper Mole** (fence).

### 5.5 Testing / acceptance
- [ ] Build candidate 30-card list(s) from new + kept cards; measure under **TurnBot** and **RefereeBot** (Greedy under-pilots synergy), ≥200 games/matchup, both seats.
- [ ] **RPS acceptance, not just win rate:** aggro must gain *both* a prey and a predator — beat the slow/greedy decks, lose to walls/stabilizers. A higher overall win rate with no bad matchup means we sanded off the commitment (re-read the Colony crank-1 failure).
- [ ] Confirm the new payoff cards are **not** decomposable — spot-check that a goodstuff optimizer doesn't pull them into a non-aggro pile.