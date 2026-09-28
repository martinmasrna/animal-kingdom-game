# Status

The map. Read it first each session and keep it current: when something here changes, rewrite the line, don't append to it.

## Where this is going

*Animal Kingdom* is a two-player tactical deckbuilding game Martin is designing, meant to become a digital game people play competitively. The path there:

1. **Design a game that is fun and deep.** Only humans can judge this.
2. **Make it playable by other people**, so humans other than Martin can play and give signal.
3. **Stabilize the rules and card pool.**
4. **Balance it seriously** with the simulation platform.
5. **Go public**, where player data takes over as the balance source.

**Current stage: 1, blocked on one design problem; 2 has a local web client, not yet hosted.**

## What exists

- **Engine** (`animal_kingdom/engine/`): complete rules for the seven-deck pool, deterministic and serializable, validating every action. Solid and well tested.
- **Bots:** random, greedy, turn and referee, plus a learned evaluator. Good enough to be an opponent and to give directional balance reads. They can't plan across turns. See [`bots.md`](bots.md).
- **Simulation:** round-robin reports, paired A/B benchmarks, a deckbuilding optimizer, metagame search, and the baseline-deck ruler. See [`balance.md`](balance.md).
- **Web client** (`./play`, `animal_kingdom/web/`): the menu flow and the horizontal game screen from the design mockups, over the real engine. Best-of-3 against Easy/Normal/Expert bots (greedy/turn/referee), or against a friend by link or code (two browser tabs work). The loser of a game goes first in the next. Every game with a human seat is saved to `results/human_games/web/` in the replay format. Runs on localhost only; nothing is hosted.
- **Terminal interfaces:** a Rich CLI (`./run`) and a Textual recorder (`./record`).

## Open problems, most important first

1. **The goodstuff problem (design).** A pile of the best cards from every deck beats all seven themed decks and nothing beats it, so there is one correct deck instead of an archetype metagame. The direction is synergy payoffs a pile structurally can't reach (tribe-count thresholds); the Colony prototype was promising but short. This is the game's central open question: [`design/goodstuff.md`](design/goodstuff.md).
2. **Nobody but Martin can play it yet.** The web client exists (see above), but it only runs on Martin's machine. What's left for friends playing remotely is hosting it: a small always-on server (a VPS or Fly.io), and HTTPS. Matches already survive a server restart (saved to `results/web_matches/`). Not in the client yet: the turn clock (numbers undecided), the collection/deckbuilder (`builder/` mockups; only the seven starter decks are playable), the Leaderboard/How to play/Settings entries, and placeholder art for Food OTK (it shows names on its portraits). The game screen is built from a painted sprite kit (`static/kit/`, made in the design sandbox's `board/r7/`) on one scaled stage; the menus are still in the wireframe look. The UI spec for content and states is the mockup set in `~/Work/fun/animal-kingdom-design/` (`game/horizontal.html` with `game/notes.md`, `menu/` with `menu/notes.md`, `builder/`).
3. **The aggro redesign** is mid-flight: Martin's card analysis is in [`cards/aggro-redesign.md`](cards/aggro-redesign.md), a candidate slate in [`cards/aggro-redesign-candidates.md`](cards/aggro-redesign-candidates.md), and nothing is chosen.
4. **Egg Control is Snake/Bird control, rebuilt 2026-09-28 by rarity role.** Eon is now the Ouroboros (10, Apex, shuffles itself back one smaller each turn); Magpie and Black Mamba are new rares; Python (was Goliath) and Rattlesnake are commons; Eagle, Anaconda and the old food-engine Eon are in the reserve. Untested beyond unit tests. Bots underplay the deck (TurnBot 11% in the last matrix); Martin's games are the real check. Details in [`cards/decks/egg-control.md`](cards/decks/egg-control.md).
5. **Card pricing pass, family by family.** Anchors are set by Martin's feel, not by bot pricing: GreedyBot overvalues extra cards by about 5 points, and both bots value strength flatter than a player does. Draw is done (anchors in [`design/principles.md`](design/principles.md)); extra placements, removal and food are done. **Lemming** is left as is, to be reworked if it stays the best common in both aggro and goodstuff. Keywords are done. **Polar Bear** (rare, 8, Apex) stays as the benchmark for synergy payoffs ([`design/goodstuff.md`](design/goodstuff.md)). Colony pass done 2026-09-28: kept as is (the swarm reaches 4+ Colony units in 95% of games; its 4+ cards are support, removal and draw, that keep it alive while queens and workers win on food). Ramp pass done 2026-09-29: Aquila and the Unnamed Giant (a strictly worse Borealis) are in the reserve; the fourth legendary is **Yuka** (woolly mammoth, 10, Immovable, costs 15 food), and **Bulwark** became 8 without Immovable (Martin's note from play). **Borealis** (giant polar bear) is a plain 10 with Apex Predator: past the top of the field (8), extra strength buys almost nothing, so it needs no drawback.
6. **Bots can't plan across turns**, which understates scaling decks in every simulation. Next experiment: a regularized learned evaluator ([`bots.md`](bots.md)).

## Waiting on Martin

Taste calls only Martin can make. Nothing here is started.

- **Card notes from play:** Queen Adira 5→4; Colony's 5-unit thresholds to 4; Prince Leo and Princess Lea play each other automatically (target chosen, not random) instead of "you may".
- **Rules:** re-examine Immovable (name, and whether blocking your own sacrifices is right; possibly split move-immunity from remove-immunity); rename Battlecry and Deathrattle to something on-theme (Instinct and Pounce were rejected); print Deathrattle uniformly ("Deathrattle: …" vs "When this is removed, …"); settle the Flight-versus-HQ wording before approving more reach cards.
- **Flavor:** the legendary-name review (only the Cats legendaries are final); Cat/Canine vs Feline/Canine as the tribe pair; Black Panther as a melanistic leopard; a new name for Hornet (Tarantula Hawk?); a Colony exception to one-species-per-pool for castes; re-casting the untagged animals. Details in [`cards/flavor-todo.md`](cards/flavor-todo.md) and [`cards/decks/flavor-review.md`](cards/decks/flavor-review.md).
- **Candidates that depended on Landmarks** (14 Landmark cards plus 6 that reference them) in [`cards/card-candidates.md`](cards/card-candidates.md): strike them, or recast the bear den as an animal.

## Bug reports to verify

Reported by Martin from play:

- **Dingo always buffs the same Canine:** confirmed. The engine gives the end-of-turn +1 to the adjacent Canine with the lowest internal id; the text says "a friendly adjacent Canine" without saying who picks. Decide between the controller's choice and random, then fix.
- Porcupine may not work properly; Chameleon can land on Porcupine and perhaps shouldn't. Not reproduced yet.

## Engine debt

- Some printed numbers are still literals in effect code (Raven's draw 3 / shuffle 2, Owl's look 3, several draw-2s); only food values and costs are guarded against the card text. Move them to `Config` or card data, and extend `test_card_text_consistency.py`.
- `benchmark_set` checkpoints don't fingerprint card data or config values.
- Before any neural-net bot: move game state to struct-of-arrays for cheap clones (measure clone cost first).

## Where things live

- [`rules/`](rules/): [`mental-model.md`](rules/mental-model.md) (read before any card or balance reasoning), [`overview.md`](rules/overview.md), [`keywords.md`](rules/keywords.md), [`rulings.md`](rules/rulings.md), [`maps.md`](rules/maps.md), and the unadopted [`expansion-mechanics-todo.md`](rules/expansion-mechanics-todo.md).
- [`design/`](design/): [`principles.md`](design/principles.md) (the game we want, card-design rules), [`art-direction.md`](design/art-direction.md) (what the art must make people feel) and [`goodstuff.md`](design/goodstuff.md).
- [`cards/`](cards/): the seven [`decks/`](cards/decks/README.md) (tables generated from `cards.json`), [`card-candidates.md`](cards/card-candidates.md), [`shelved-cards.md`](cards/shelved-cards.md), and the idea banks [`expansion-design-todo.md`](cards/expansion-design-todo.md) and [`deckbuilding-todo.md`](cards/deckbuilding-todo.md).
- [`bots.md`](bots.md), [`balance.md`](balance.md).
- [`pre-launch.md`](pre-launch.md): what must be settled before going public, and not before.
- Research tooling removed from the tree (pilot ratings, conquest and roster experiments, referee comparison, gauntlet, human scorer) and the old docs are at tag `archive/research-2026-07`.
