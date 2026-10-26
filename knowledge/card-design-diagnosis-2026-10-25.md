# Why agent card design stopped improving: diagnosis, 2026-10-25

Read this before asking an agent to design, rework or judge a card. It is a diagnosis of the feedback loop, written by /last-hope after reading every card-design session on this Mac from 2026-10-04 to 2026-10-25 (eleven distinct sessions, about 3.3 MB of dialogue after tool output was stripped, read in full by ten readers with one fixed report shape), the git history of `docs/design/principles.md`, `effects-pass.md`, `rarity.md`, `animal-fit.md` and the deck-design skill, the churn of `cards.json`, the card table's lock levels, and two tests run today. It is not a new rule for cards. Do not add it to `principles.md`. The sessions designed on Martin's work PC (10-05 to 10-07, 10-12, 10-13, 10-16) are not on this Mac; their outcomes appear here only through git and the memories they left.

## The one sentence

The agent designs by prose and checks by prose: 56% of its rejected cards failed a check it could have run before Martin saw them (a turn played on the real grid, a search of the pool, a keyword's text, his last instruction, an animal fact), the other 44% failed a taste its written rules predict no better than a coin, and every verdict was written back into those rules as his, so the rules file became a rejector that throws out two thirds of what he accepts and the next round could not get better.

## What every treatment had in common

The counted timeline is at the end. In three weeks: a principles file (09-25); habitat, family and signature docs, cold-agent rosters and three pre-proposal checks (10-05); "the usual" framing round, imagined games, the deck-design skill, a four-stage lock pipeline, a fit pass and a rarity pass (10-08, 10-09); the gauntlet as the balance read, the 30 Lions floor, four new principles and three extensions of a stress-test memory (10-10 to 10-15); the tag principle and an anchor audit (10-16); real anchor cards (10-17); the keyword ruler, three pre-proposal checks again, two first-principles essays (10-21); the rarity test and conditional pricing tables (10-22); a silence memory and a Fable animal search (10-23); a world-first study, society pages and a four-ideas memory (10-24). `principles.md` grew from 671 words and 24 bullets to 2,687 words and 51 bullets; `effects-pass.md` from 413 to 9,038 words before its restructure; the deck-design skill carries nine "failures this procedure exists to stop"; the stress-test memory is 708 words and seven numbered checks.

All of them did the same thing: the agent reasoned in prose from the written rules to a card, showed it, read Martin's verdict, and wrote what the verdict seemed to mean back into the rules. The shared assumption, never tested: **an agent can tell, by reasoning in prose against the written rules, whether a card is right, and Martin's verdict reasons written into those rules make the next card better.**

## Where the loop breaks

### 1. The verifier is absent where it could work and blind where it can't (tested)

Every agent proposal was checked by the agent's own reasoning before Martin saw it. Test 2 took all 390 agent proposals Martin rejected (one duplicated session removed) and asked, from his stated reason, which check would have caught it:

| what settles it | share | examples of his reason |
|---|---|---|
| only Martin (taste, fit, direction) | 39% | "boring as fuck", "doesn't fit the deck", "it's just a bad design" |
| one turn played on the grid or one bot game | 17% | "there's only so many empty crossroads", "strength gain once on board is almost useless", "half the deck instantly loses the moment this is played" |
| re-reading his last instruction | 14% | "keep the wording exactly as it was", "this card is already locked", "I never approved this card" |
| a search of cards.json by effect or animal | 10% | "did you just reprint Chameleon", "strictly worse than Rue", "mouse is already a card" |
| the keyword's own text | 6% | "READ WHAT THE KEYWORD DOES", "did you just give it Flight?", "read what Titan does" |
| checking the animal fact | 5% | "peacocks can fly, no?", "beaver not a rodent" |
| the anchor table | 4% | "strictly worse than vanilla Lion", "by definition rares are stronger" |
| no reason given | 5% | "the other 2 don't", "THEY ARE COMPLETELY RETARDED" |

So 56% of rejections were catchable by a procedure the agent owns (it wrote the engine, the keyword doc and the card file) and never ran on its own proposals, and the Rule Synergy study of LLMs on Slay the Spire names the same three failure types: timing errors, game-state errors ("builds an artificially optimal state") and rule errors.

For the other 44%, Test 1 asked whether the written rules carry his taste. Seventy agent-invented proposals (35 accepted, 35 rejected), shuffled, card text only, judged cold by Sonnet twice:

| judge | agrees with Martin | his accepted recognised | his rejected recognised |
|---|---|---|---|
| the card alone | 39 of 70 (56%) | 19 of 35 | 20 of 35 |
| after reading mental-model, keywords, principles, rarity, animal-fit, the deck-design skill and cards.json | 46 of 70 (66%) | 14 of 35 | 32 of 35 |
| the same, on the 45 items where it could not cite a recorded call or an existing card | 28 of 45 (62%) | 7 of 22 | 21 of 23 |

Chance and "reject everything" both score 35 of 70; disproof was 75%. The rules turn the judge into a rejector (53 of 70 rejected) that reproduces his "no" and misses two thirds of his "yes"; most of the gain over the blind judge came from `rarity.md`'s and `animal-fit.md`'s "calls so far" and from accepted proposals now being cards, which is the record leaking, not the rules carrying taste. The naming diagnosis found the same shape nine days ago (the rules passed 6 of 17 gold names).

### 2. The controls did not move the output, so the rules were learned from dice

Acceptance of agent proposals, share of those judged, by session: 10-04/05 35% · 10-08 34% (65% in the evening fit pass) · 10-10 to 10-15 29% · 10-15 to 10-17 29% · 10-14 2 of 7 · 10-17 24% · 10-21 21% · 10-22 42% · 10-23 23% · 10-24 32%. No trend while the rules tripled. Split by kind: proposals that only re-level a number, rarity, tag or wording against an anchor were accepted 47% of the time (39 of 83); proposals that invent an effect, a card or an animal for an effect 29% (100 of 342). The two best days were pricing passes; the worst were invention under a loose brief.

What did move it was never a rule: Martin narrowing the slot himself ("what we need is an 8 strength common with a drawback" gave the Crocodile and the Grizzly in one round; "a rare that refuels an empty hand" gave the Ocelot; "price these against the anchors" gave a morning where 9 of 9 rarity calls and every strength change were accepted), and a known card-game shape translated into this game's economy (Divine Favor, Hellbent, the one-action first turn). After every written rule the next invention round scored the same: the 10-08 checklist was followed by 29%, the 10-13 one-partner rule by 2 of 7, the 10-21 three checks by 23%, the 10-24 four-ideas memory by a batch rejected in block.

### 3. The target is mostly stable; the verdict-to-rule hop is where it was lost

Martin's own designs: 110 proposals, 4 rejected, all by himself on second thought. Joint designs (he framed, the agent wrote): 83, 7 rejected. His reasons repeat verbatim across weeks (the action is the cost, draw-1 is tempo, strength on the board does nothing, compare with the Lion, rares are stronger), and his reversals are few and come after play (Vesper from Queens to any Colony after a gauntlet; the Black Panther food engine to Apex the same evening; the Infestation deck liked then dropped; "remove all animals doesn't fit" then "fine as a board wipe if themed"). The target is expressible for mechanics and taste for fit; it is not noise.

The hop that lost it is verdict into rule. Of 186 rules the sessions wrote into docs, skills and memories, 104 are his words, 35 were generalised by the agent from a verdict, 38 were the agent's own idea, 9 unclear: 39% not his. The three lines he did not recognise on 10-24 are all of that kind: "a deck works with a card and its one partner" was written from "you still need 3-4 uncovered bodies… solitaire" and dated as his; "a group of lookalikes doesn't get fifteen members" from "celebrate the natural beauty and diversity of nature"; "Mouse at 5 is too big" from "high utility animals should have low strength". Each was then used against him: today the Rat was defended and condemned with the one-partner rule. A second lossy hop runs the other way: supporting facts the agent asserted and later admitted inventing ("I made that up", twice on 10-16; the beaver, the honeyguide, the wasp painting, the brother's deck) cost trust on every claim around them ("gaslighting", four times in the record).

### 4. The base rate

Hearthstone's designers "brainstorm a ton of cards, the number of cards we iterate on then cut is hundreds and hundreds for each expansion" of about 135 (Chadd Nervig); Eric Dodds: "tons and tons of bad ideas that we needed to try, and then not do", prototyped on paper and judged by how it felt to play; a designer builds a card in HearthEdit and plays it without an engineer. Magic playtests a set for about two years. A 29% first-sight hit rate on raw invention is not far from what professionals' idea piles would score if a senior read every one. What is abnormal here is that every one of the 734 agent proposals crossed Martin's desk unplayed, while his own ideas get a gauntlet before he judges them. He said it himself: "one round of actually playing it tells you more than all the theory" (10-21), "infinitely better feedback than just designing in vacuum" (10-15), "it's your word against the expert bots" (10-24).

## Why each previous treatment had to fail

A rule written by a judge that cannot see the target (section 1) from a single verdict (section 3) changes the prose the agent reasons from, and prose reasoning never ran the checks that would have caught half the misses (section 1), so the next round's hit or miss was a coin either way and either way became a rule (section 2). The checklists (10-05, 10-08, 10-21) were the right checks written as reading instructions instead of run as procedures; the essays and "think from first principles" asked the same prose reasoner to reason harder; the fit and rarity passes worked because they were pricing against anchors, which is the one kind of judgment the rules do carry; the world-first study moved the generator's inputs and could not touch the verifier.

## Alternatives that survived, ranked

1. **The model cannot design cards** (Martin, 10-24: "beyond useless when it comes to card design"). Half true: inventing under a loose brief it is a coin on taste and never checked the checkable; pricing against anchors it is useful (47%), and under a tight brief it produced several of the cards he likes best (Divine Favor, the Ocelot, the Capybara, the man-eater Tiger, the Vulture that lands from the deck). The distinction the record supports is not "can't" but "cannot judge its own invention, and did not check what it could".
2. **Long sessions pollute the context** ("this one has too much dumb context inside it now", 10-24). The worst batches did come late in long days (10-04 after 23:00, 10-21 after 20:00, 10-24 at 15:19), but 10-23's misses came before noon. A contributor, not the break.
3. **Martin's target drifts.** Weak: his own designs hold at 96%, his reasons repeat, and his reversals follow play.
4. **Nothing is broken; this is the base rate.** Half true for the generation step; the cost that is not base rate is 734 unplayed proposals read by him and 73 rules written in his name that he did not state.

## The tests

**Test 1, run 2026-10-25: do the rules carry his verdicts?** Above. Disproof would have been 75% or more agreement; the rules judge reached 66% overall and 62% where it could not look the answer up.

**Test 2, run 2026-10-25: how many rejections were catchable?** Above. Prediction was 40% or more; disproof under 25%; result 56%.

**Test 3, for Martin, five minutes, on or after 2026-11-01: is his first-sight verdict stable?** The 70 items of Test 1 shown cold and shuffled, card text only, one keystroke each: keep or nope. Prediction: 80% or more of his verdicts hold, which confirms section 3 and keeps the treatment below. Disproof: under 65% hold, which means taste dominates and the treatment becomes the naming one (breadth, cooling period, no verdict reasons).

**Test 4, the treatment's own measure, read on 2026-11-15:** in the design sessions after the treatment, agent proposals judged, accepted and rejected, and rejections by the Test 2 classes, logged in `knowledge/card-design-log.md`. The treatment worked if rejections of the checkable kinds fall under 10% of rejections and acceptance of agent proposals rises above 50%. Disproof: checkable rejections still 25% or more, or acceptance still at 35%.

## The treatment

Remove the broken parts from the loop instead of adding effort on them. Martin's shape, 2026-10-26: the sheet is the agent's, not his ("I mostly have this in my head, this is just for agent to not make retarded suggestions"); his own cards skip it; agent ideas on request.

- **The sheet.** `tools/cards/check.py` prints, for one card, the facts an agent kept getting wrong from memory: the registry's ruling for every keyword and term in the text, the animal's existing cards and its family in the pool and the nearest effects, the cards at its rarity and strength and how much of the pool covers the body, every line of the design record that names the animal, map_b's neighbours and regions at six places (an adjacent payoff's ceiling at each), the lines the text takes on the real card at every width, and for a card the engine knows a placement in a scratch game with what changed. No verdict. An agent runs it on every card of its own before Martin sees the card, and Martin sees the card, never the sheet, unless he asks why something wasn't caught.
- **Agent ideas only when he asks.** Four distinct, one line of card text each, each already through the sheet, flat: no reasons, no ranking. Silence is unjudged. A claim about an animal is checked before it is written, or not written.
- **No more rules from verdicts.** The deck-design skill's nine failure bullets and the stress-test memory's seven checks are gone; both say "run the sheet". A rejected idea and his reason stay in the deck's rejected list in `effects-pass.md`, a log, never a rule. `principles.md` keeps what survives his redline (open with him since 2026-10-24) and nothing is added to it from a verdict.
- **One number, read on 2026-11-15.** `card-design-log.md`: per sitting, proposals judged, accepted, rejections by class. Test 4's disproof is written at its head.

Built 2026-10-26: `tools/cards/check.py` and `tools/cards/fit.mjs` (tested by `animal_kingdom/tests/test_card_sheet.py`), the deck-design skill rewritten around it, the stress-test memory cut to a pointer, `knowledge/card-design-log.md`. Waiting on Martin: the `principles.md` redline; Test 3 after 2026-11-01.

## Timeline of treatments

| date | treatment | assumption | what followed |
|---|---|---|---|
| 09-25 | `principles.md`: references, floor, closest card | anchors in prose guide design | 671 words |
| 10-05 | habitats, families, signatures docs; cold Sonnet rosters; signature registry (Opus, 274 animals); three checks before any card; Sol critic plus bot screen | more written context, more checks to read | 90 of 158 agent proposals rejected that day (35% accepted); Martin: "I opened a single sheet in Excel and I just designed the decks" |
| 10-08 | "the usual" framing; imagined games; Face Hunter decomposition; deck-design skill; trivia rule; four-stage lock pipeline; workbench; fit pass (`animal-fit.md`) | a procedure plus a record of past misses | six decks finished, 34% accepted; the evening fit pass 65% |
| 10-09 | `rarity.md`, rarity calls | criteria sharpen from his calls | names pass: "100 times worse than before" |
| 10-10 to 10-13 | gauntlet as the balance read; 30 Lions floor; principles: action is the cost, play styles not precons, Dawn/Dusk automatic, one partner; stress-test memory extended three times; check-against-rejected-designs memory | his verdict reasons, written as rules, stop the repeats | 29% accepted; the Cockroach deck took "more time than all the other decks combined" |
| 10-14 | real-play lists with written reasoning per move | play before showing | 2 of 7 accepted; the deck "clunky all around" |
| 10-16 | tag principle; removal audit against anchors | search keys and anchors | "when did I ever ask you to give me suggestions?" |
| 10-17 | Lion rule for 8+; anchors as real cards | fixed points to price from | 24% accepted; Crocodile and Grizzly landed from a tight brief |
| 10-21 | keyword ruler; three pre-proposal checks again; two first-principles essays | reason harder | 21% accepted; "clearly I'm not going to get quality from you, so let's try quantity" |
| 10-22 | rarity test (three copies); conditional pricing tables; effects-pass restructure | pricing by what a condition costs | 42% accepted, nearly all of it pricing |
| 10-23 | silence-is-not-approval memory; Fable animal search; HS Hunter list | another memory | 23% accepted; Martin wrote the Tiger, the Panther and the Whale himself |
| 10-24 | world-first study (660k tokens); society pages; four-ideas memory; deck-design skill from scratch for Colony | a world under the cards | a batch rejected in block; Martin designed Colony in Excel; the Rat; /last-hope |

Session files read: `-game/47850256` (10-04), `d1e24d24` and its duplicate `9f841078` (10-08), `328aae99` (10-10 to 10-17), `aed153ec` (10-14), `5310e55b` and `76ff0810` and `697bf5fc` (10-17); workspace `c3247b24` (10-21), `a42fa3f4` (10-22), `c1d51b98` (10-23), `dd78d375` (10-24). Reader reports, the classification and both judges' outputs are in the session's scratchpad (`lh/`); the counts in this file are from them.
