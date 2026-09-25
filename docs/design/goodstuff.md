# The goodstuff problem

The central open design problem. A deck of the individually strongest cards from across all seven decks beats every themed deck, and nothing beats it. Until that changes, the game has one correct deck, not an archetype metagame.

## What was measured

- A hill-climbing optimizer over legal 4-4-6 decks converged on a pile of premium standalone value: big Apex bodies, efficient removal, draw engines. It beat the seven premades about 95% of the time under GreedyBot and 88% under RefereeBot (200 games per matchup); its worst matchup was still about 82%.
- Martin, the strongest pilot on record, piloted each premade into the bot-piloted pile and lost heavily. The edge is real, not a bot artifact.
- A double-oracle search (build the best deck against the current field, add it, repeat) produced only more value piles; the best counter it found reached 22% against goodstuff. The replicator dynamics over the resulting matrix collapse to a monoculture.
- The pool is deep: with goodstuff's 14 designs removed, the leftovers still built a 53.7% deck. Nerfing a handful of cards doesn't help; the search just finds the next handful.
- The core the piles converged on is action economy. Chinchilla (an extra action) and Polar Bear were in every pile, then Bat, Lemming, Tiger, Greywhisker, Black Bear, Alpha, Mouse, Raven and Rhinoceros. In a game whose only resource is the action, cards that manufacture actions are unconditionally strong.
- The themed decks, by contrast, carry low-floor cards that are dead draws without their partners. Goodstuff has no dead draws.

These numbers predate the draw-2 rule and the timed-effect fix, so they need a re-run, but the structural argument below doesn't depend on them.

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

The optimized piles and the Colony prototype recipe lived in the untracked `results/` folder and are gone. The conquest and roster experiments are archived at tag `archive/research-2026-07`.
