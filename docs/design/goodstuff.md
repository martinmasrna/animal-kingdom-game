# The goodstuff problem

The central open design problem. A deck of the individually strongest cards from across all seven decks beats every themed deck, and nothing beats it. Until that changes, the game has one correct deck, not an archetype metagame.

## What was measured

- A hill-climbing optimizer over legal 4-4-6 decks converged on a pile of premium standalone value: big Apex bodies, efficient removal, draw engines. It beat the seven premades about 95% of the time under GreedyBot and 88% under RefereeBot (200 games per matchup); its worst matchup was still about 82%.
- Martin, the strongest pilot on record, piloted each premade into the bot-piloted pile and lost heavily. The edge is real, not a bot artifact.
- A double-oracle search (build the best deck against the current field, add it, repeat) produced only more value piles; the best counter it found reached 22% against goodstuff. The replicator dynamics over the resulting matrix collapse to a monoculture.
- The pool is deep: with goodstuff's 14 designs removed, the leftovers still built a 53.7% deck. Nerfing a handful of cards doesn't help; the search just finds the next handful.
- The core the piles converged on is action economy. Chinchilla (an extra action) and Polar Bear were in every pile, then Bat, Lemming, Tiger, Greywhisker, Black Bear, Alpha, Mouse, Raven and Rhinoceros. In a game whose only resource is the action, cards that manufacture actions are unconditionally strong.
- The themed decks, by contrast, carry low-floor cards that are dead draws without their partners. Goodstuff has no dead draws.

Re-run on the current ruleset (2026-09-25): a fresh optimized pile still beats all seven premades, 80% mean and 64% worst under RefereeBot. Its recipe is in [`../balance.md`](../balance.md).

## Why it happens

Picking the best cards becomes a forced dominant strategy once four things hold together: a private deck you build, from an open pool (any card with any card), with no cost to play a card, and cards that aren't all equal. Card games defuse it by removing one ingredient: colors or classes (the open pool), mana (the free cost), or drafting and fixed decks (the private deck). Flattening card power isn't feasible; small edges compound over 14 picks. This game currently has neither a deckbuilding constraint nor an in-game cost.

## What was tried or rejected

- **Nerf the core cards:** rejected, since the pool is deep enough to supply the next core.
- **Global rule dials:** drawing 2 per Draw action was tested and absorbed. It helped goodstuff as much as the synergy decks, because goodstuff also owns the best draw.
- **Colors or classes:** rejected as Magic with extra steps.
- **Food as mana:** rejected. It is too mana-like, and food comes from being ahead, so pricing cards in food makes the leader snowball. Two-action cards were rejected as a coarse, targeted nerf.
- **Best-of-3 conquest with disjoint decks** (the deck that wins a game is retired): the mechanism works on a shallow pool, but on the real, deep pool a goodstuff-plus-leftovers roster still won 69.6% under RefereeBot.

## The direction

Make synergy decks that beat the pile, while the pile remains as one midrange option. To beat a pile, a synergy deck must be at once:

1. **High-ceiling:** its payoff outclasses standalone value.
2. **Non-decomposable:** a pile can't cherry-pick a few of its pieces, which needs a steep threshold.
3. **Consistent:** it comes online reliably, since a pile has no variance.

Points 2 and 3 fight each other; that is the core difficulty. The shape that threads them is **payoffs that scale on a currency a dedicated deck accrues reliably and a pile structurally can't**, such as "5 or more of your tribe on the board".

Colony already has that shape and was the first prototype. Lowering its thresholds from 5 to 4 and raising its queens lifted it from 38% to 54% against the field, but it still won only 21% against goodstuff (30% with Martin piloting), and it lost its intended bad matchup against aggro. The likely missing lever is resilience against the pile's removal, not more food. The prototype was reverted.

## Card pricing, and why the pile gets its cards cheap

Cards have no cost, so an effect is paid for in strength. The common anchors are Lion (vanilla 7, ground) and Eagle (vanilla 5, Flight): a common with an effect sits below 7, and the gap is the effect's price. Read the pool that way and the prices are inconsistent, in one direction: **conditional effects were charged more than unconditional ones.** Bat (4, Flight, draw 1) pays 1 for an unconditional draw; Lynx (3, draw 1 if you control another Cat) pays 4 for a worse draw; Mouse (1, draw a Rodent) pays 6. A condition makes an effect worse, so it must make it cheaper; and in its home deck a tribe condition is nearly always met. The pile is largely the set of cards where the budget came out cheap, and the synergy decks are built from the cards where it came out expensive. The rule: **a condition is a discount, never a surcharge.**

Strength isn't linear either, since covering is strictly-greater: a point is worth what it lets you cover and what it stops covering you, so it depends on the strength distribution of the field. Measured on GreedyBot against the premades, value rises about 1–2 points of win rate per strength step from 5 to 9 ([`../balance.md`](../balance.md)); how that holds against the pile's field is not measured.

## The ways up

- **Each archetype gets its own answer.** The seven decks cover different playstyles on purpose, so no single mechanic (tribe-count buffs, deck-list conditions, cumulative counters) may become the rule for all of them; each is fine as one deck's signature.
- **Drawbacks buy strength above the anchor.** A common stronger than Lion needs a real drawback, and a drawback can be a deck's fuel: discard, sacrificing your own units (the parked aristocrat design), Fragile, a food cost. A strong body with a severe drawback is bad in a pile and good in the deck that turns the drawback into value, which is non-separable by construction. The current pool often charges twice instead (Rat is a 2 *and* pays a card; the Eggs are 0 *and* Fragile). A mild drawback just hands the pile a free big body.
- **Food costs stay rare,** around 10% of cards, so food never becomes mana.
- **Gated retrieval over raw draw.** Generic draw helps a pile more than a synergy deck, since almost any card helps a pile and only the missing piece helps a synergy hand; "draw a Cat" helps the committed deck only (the shared-pool study, `~/.claude/knowledge/studies/shared-pool-card-games/`).

The per-card measure of all this is **synergy = home value minus pile value**, by paired swaps: a goodstuff card scores near zero, a real synergy card high. Target: synergy cards score high *and* are worth at home at least what the pile's staples are worth.

## Held in reserve: heroes

If synergy design alone can't beat the pile, the fallback is a deckbuilding constraint that grows out of the pool instead of being imposed on it: each common and rare is attached to one or more legendaries, and a deck is built around a legendary ("hero") from the cards attached to it. That gives classes without colours. It is the Flesh and Blood shape (a hero card that defines the legal pool), and Hearthstone's classes with the hero as a card. It is a drastic change to deckbuilding and the collection, so it is the last resort, not the next experiment (Martin, 2026-09-26).

## Open questions

1. Which lever lets a synergy deck beat the pile: resilience (survive the removal) or speed (win before it)?
2. Can several such decks be built that beat the pile yet lose to something else, or does every strong deck collapse toward the pile?
3. Is part of the answer a format change (a deliberately shallow pool with conquest), or is it purely card design?
4. What is goodstuff's intended predator: go-tall, a faster race, or a combo that goes over the top?

## Instruments

- `sim/deck_optimizer.py` hill-climbs a legal deck against a field (`--evaluate-only` scores a given recipe; `SEED_RECIPE` is the hand-built goodstuff seed).
- `sim/metagame_search.py` runs the counter search and the full double-oracle expansion.
- `sim/measure_deck.py` measures one deck against a field under any pilot and config (`--with-goodstuff` adds the pile).
- `sim/benchmark_set.py` plays the fixed no-synergy baseline deck against the field; see [`../balance.md`](../balance.md).

The Colony prototype recipe lived in the untracked `results/` folder and is gone. The conquest and roster experiments are archived at tag `archive/research-2026-07`.
