# Constructed Deckbuilding — To-Do

The initial 14-design packages are premade-deck foundations, not intended final archetype pools.
All cards remain globally legal; “archetype” describes synergy and expected use, not a class or
faction restriction.

## 1. First constructed-pool target

- [ ] Test deck shapes beyond the premade **4–4–6** maximum-copy pattern. One proposed
  high-diversity shape is **4–8–18** distinct designs while preserving the usual totals of 4
  legendary, 8 rare, and 18 common cards.
- [ ] Determine copy counts card by card. Some designs, such as Lemming and other copy-scaling
  cards, may only provide useful data when played at their full copy count.
- [ ] Consider comparing two test-list families:
  - **Breadth lists:** many one-copy candidates for broad rules/power exposure.
  - **Focused lists:** maximum-copy synergy packages for consistency, ceiling, and degeneracy
    testing.
- [ ] Do not compare raw drawn win rate across different copy counts without recording the exact
  decklist and number of copies. Singleton breadth tests expose more designs but require more
  games for useful per-card samples.
- [ ] Grow each established archetype's plausible pool from 14 to roughly **20–24 designs**.
- [ ] Use a rough per-archetype target of **6 legendary, 7 rare, and 11 common designs** before
  claiming that archetype has mature deckbuilding:
  - at most 4 of 6 legendary designs can be included;
  - at most four full two-copy rare packages fit under the 8-rare-card cap;
  - commons must compete for the remaining 18+ card slots.
- [ ] Do not require every archetype to reach the same number simultaneously. Bridge cards that
  genuinely belong in two or three shells count toward each shell's practical options.
- [ ] Maintain a smaller neutral/bridge pool rather than designing seven sealed factions.
- [ ] Keep the seven premade 30-card lists as onboarding products even after constructed play is
  available.

## 2. What counts as a deckbuilding choice

- [ ] A new card succeeds when at least one plausible list includes it and another plausible list
  intentionally omits it.
- [ ] Every archetype should eventually support at least **three recognizable builds**, for
  example:
  - Cats: removal goodstuff / isolated hunters / Landmark Cats.
  - Egg: shuffle-food / hatch-board / Venom control.
  - Colony: pure caste swarm / mixed Insect food / token-sacrifice.
  - Ramp: Bear-cost / Landmark engines / medium-curve Megafauna.
  - Food: OTK / sacrifice value / scavenger attrition.
  - Aggro: Rodent chain / aerial rush / Burrow-region pressure.
  - Canines: hand-buff / movement tempo / resilient pack.
- [ ] Competing builds should differ by at least **8–10 cards**, not merely swap one legendary
  and two commons.
- [ ] Include cards that are matchup or map calls, but avoid narrow hate cards that are dead
  outside one pairing.
- [ ] Preserve weaknesses. Expansion should not give every archetype efficient removal, draw,
  ramp, recursion, reach, and protection.

## 3. Module construction

- [ ] Treat rarity primarily as a **copy-count and gameplay-pattern lever**, not a reward for
  wordiness:
  - Common designs must be safe at three copies.
  - Rare designs must remain healthy when both copies are drawn or active.
  - Legendary designs should create a distinctive story or engine at one copy; they may be
    mechanically simple.
- [ ] Design synergy modules in packages of roughly **4–8 designs**:
  - 1 payoff;
  - 1–2 enablers;
  - 1 bridge card usable elsewhere;
  - 1 interaction or resilience card;
  - optional legendary build-around.
- [ ] Avoid packages that require including every card with a tag. A tag should have more legal
  members than a 30-card deck can comfortably run.
- [ ] Keep build-around legendaries functional at one copy without making the deck nonfunctional
  when they are not drawn.
- [ ] Use common cards to establish an archetype's ordinary turns. Rare/legendary cards should
  alter direction or ceiling, not supply all basic functionality.
- [ ] Make some cards compete for the same role at different rates:
  - immediate but small versus delayed but large;
  - strong body versus weak engine;
  - generic consistency versus narrow synergy;
  - board victory versus food victory.

## 4. Bridge-card goals

- [ ] Create at least one honest bridge for each pair below:
  - Colony ↔ Food sacrifice: Insect Deathrattles and token fodder.
  - Egg ↔ Dinosaur Hatch: Eggs, incubation, delayed bodies.
  - Egg ↔ Venom: Snakes and delayed control.
  - Ramp ↔ Primate/other Landmark decks: contested ecological structures.
  - Aggro ↔ Warren/Burrow: empty-crossroad reach.
  - Canines ↔ general movement: buffs that enable repositioning.
  - Fish ↔ Food sacrifice: fragile prey and on-covered effects.
- [ ] A bridge card should be slightly less efficient than a tribe's pure payoff when used
  outside its best home; otherwise it becomes generic goodstuff.
- [ ] Avoid bridge cards that accidentally combine two complete win engines on one body.

## 5. Required list-building exercises

- [ ] Build two different legal 30-card lists for each existing archetype using the expansion
  slate. Explain every omitted native card.
- [ ] Build at least three cross-archetype lists:
  1. Colony sacrifice;
  2. Egg/Dinosaur hatch;
  3. Landmark midrange using cards from at least three tags.
- [ ] Build the strongest apparent legendary-goodstuff list. Verify that tribal/common synergy
  beats simply selecting the best four one-copy cards.
- [ ] Build the lowest-curve legal list and search manually for two- and three-card HQ captures.
- [ ] Build the most deterministic food combo possible and count filtered draws, tutors,
  recursion, and redundant win pieces.
- [ ] Build against all three revealed maps with no sideboard. Confirm that map specialization
  creates tension without making one map an automatic loss.

## 6. Diversity measurements for later simulation/human testing

- [ ] Track card inclusion rate across submitted/test lists, not only drawn win rate.
- [ ] Flag cards appearing in more than roughly 80% of lists that can legally exploit them.
  High inclusion may be correct for archetype glue, but should be intentional.
- [ ] Track opening-hand keep rate and first-play rate; these reveal glue cards that drawn win
  rate can hide.
- [ ] Track how many distinct cards are seen in winning lists for each tag.
- [ ] Track pairwise co-inclusion to find inseparable packages and hidden “deck taxes.”
- [ ] Track list overlap among top-performing builds. A healthy constructed pool should not
  converge to the original 14-card premade list plus one obvious swap.

## 7. Format decisions to defer

- [ ] Do not add sideboards until the one-list/three-map match premise has been tested with a
  larger pool. Sideboards would weaken the intended generalist constraint.
- [ ] Do not introduce card rotation, set legality, or collection rarity into balance discussion
  yet.
- [ ] Do not impose faction locks unless unrestricted construction repeatedly collapses into
  homogenized goodstuff. Soft tag synergy is the preferred solution.
- [ ] Revisit whether exactly four legendary designs per premade deck remains the best onboarding
  presentation once players can choose from six or more.
