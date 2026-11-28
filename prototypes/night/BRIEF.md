# Night run, 2026-11-28: many card-game cores, each playable against a bot

## What this is for

A designer is looking for the core of a card game worth building. Designing on paper keeps producing cores that die within hours of real play, and reasoning can only show where a design breaks, never that it is fun. So this run makes many rough cores playable, removes only the ones a machine can prove broken, and leaves the judgement of fun to the designer, who will play each survivor for about five minutes in the morning.

This means: no agent in this run ranks concepts by how promising or fun they seem. Agents generate wide, attack hard, cut only on the criteria below, and build well.

## The space

Any game in which a deck matters: a personal pile drawn from repeatedly, whose composition sets the odds of what shows up, built before the match (constructed), during it (deckbuilding), or both. Playable in a browser against a bot.

- Mostly one player against one other player, turn-based. A minority may be single-player or co-op against the game, simultaneous-turn, auto-resolving, or real-time, as long as the deck is central.
- Spread the concepts far apart: different win conditions (life, points race, tug-of-war, area, majorities, objectives), different ways pieces interact (attacker picks, defender blocks, lanes or position, only exerted units are attackable, no units at all), different sources of skill (building, sequencing, reading hidden information, timing, economy).
- Mechanisms from board games, war games, abstract games and sports count as much as those from digital card games.
- Use genre mechanics freely. Never recreate a specific existing game (its name, rules set as a whole, characters or look), even renamed.

One fixed entry, to be built as described: **Score-or-fight duel.** Hearthstone-style units with attack and health, mana cost, units cannot act the turn they are played. Each turn a ready unit either attacks (an enemy unit or nothing else; there is no hero to hit) or scores, adding its current health to its owner's score and becoming spent. First to a target score wins. Attacking enemy units is therefore scoring by subtraction.

## Kill criteria on paper (concept stage)

A concept dies if any of these holds, and the reason is written in one line:

1. **No cost dimension.** Cards must differ in what they cost (mana or any resource that varies per card) so they can differ in what they are worth. A fixed number of actions per turn where every card costs one action fails this.
2. **A dominant strategy you can find by reasoning.** Cheap bodies or tokens beat everything, racing beats interacting, one card or one line is always right.
3. **Solitaire.** Each player's sources of progress must be reachable by the other, and reaching them must pay at least as well as building your own.
4. **No end.** The game must end: a track that moves one way, progress that locks in, or a resource that runs out.
5. **Too heavy for its depth.** Rules must fit on one screen; every rule must add more decisions than it costs to learn.

## Kill criteria by machine (build stage)

Every built prototype has an Expert bot (a search bot, e.g. flat Monte Carlo or determinized rollouts) and at least two trivial bots: random legal moves, and greedy (spend the most resource, take the immediate best by a fixed rule). Add a pure racer (ignores the opponent) wherever racing is possible.

A prototype is marked dead if:

- Expert wins under 70% against any trivial bot over at least 400 games, seats alternated (the game is decided by luck or by a simple rule);
- Expert fails set positions a person never gets wrong (take lethal, don't waste resources for nothing, take a free trade or its equivalent in this game);
- more than 2% of games hit a turn cap (it does not end);
- Expert's choice equals Greedy's in more than 90% of decisions (a fixed rule solves it);
- first-player win rate is outside 30–70% (the loop is broken by tempo).

These numbers are evidence about the loop, not things to tune. If a prototype fails, the builder may change one rule once, for a stated reason about the loop, and re-measure; if it still fails it is dead and kept as dead, with the numbers.

## What each prototype is

Folder `game/prototypes/night/<nn>-<slug>/`, structured like `game/prototypes/hs/vanilla/` (read that folder as the template: `src/engine.js`, `src/bot.js`, `src/ui.js`, `src/page.html`, `src/style.css`, `build.mjs` writing one self-contained `index.html` and an `artifact.html`, `sanity.mjs` for set positions). Plus:

- `RULES.md`: the complete rules, short.
- `sim.mjs`: the machine gate above; writes `report.json` with every number.
- `REPORT.md`: alive or dead; the numbers; three or four lines on what the loop is, meaning what a player decides each turn and what the best play boils down to, from watching Expert play.

The page: a human plays Expert. Abstract, clean pieces (cards as plain rectangles with their numbers), readable at a glance on a phone and on a 1512×800 desktop. The bot's turn plays out step by step so a person can see what it did. A short rules panel opens from one button; a new-game button. No hints, no tooltips, no labels for what the board already shows. Placeholder names are functional ("Wall", "Striker", "Draw 2"); no creatures, no world, no lore: the world is not ours to invent.

## Rules for every agent

- Do not read the Animal Kingdom docs, memory or the rest of the repo; only `game/prototypes/hs/vanilla/` as a structural template.
- Write only inside `game/prototypes/night/`. No git commands.
- Run anything slow in the background and keep working.
- Finish one prototype completely (built, gated, reported) before starting the next, so a run cut short still leaves finished work.
