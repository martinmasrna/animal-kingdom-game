# The Meta tab: the competitive player's tool

The Ladder screen's Meta tab is where a competitive player prepares for ladder. It is meant to become the game's first-party equivalent of HSReplay or HSGuru, with complete data instead of a tracker sample, and later the paid "pro" tool Martin described on 2026-10-24 as the game's honest way to make money (useful tools for players who compete, instead of gambling mechanics). The free and paid split is not designed yet; until it is, the tool is built as good as it can be, whole (Martin, 2026-10-24: "let's not worry about Free/Pro split at all now").

## Who it is for

Players for whom fun is winning and climbing: the competitive hobbyist and the pro, not the casual. Martin, 2026-10-24: the tool must not treat them as people who need things explained; "I want the data presented in the best possible way, but I don't want them synthesized". No guides, no written advice, no generated text: raw numbers, presented well, and the player draws the conclusions.

## The two questions

1. Which deck should I play?
   - The meta by rating: what each archetype's share of games is. Rating is a filter on the whole tab, starting near the viewer's own rating and settable to any range.
   - The tier list and the matchup matrix, sortable. Clicking several columns (decks you keep meeting) gives every deck's average against just those.
   - Each archetype's variants: which cards are staples and which are flex slots, and the win rate with a card in the list against without it, within the archetype.
2. How should I play it?
   - Per card: mulligan win rate, drawn win rate, played win rate (three distinct figures, Martin, 2026-10-24), in general and per matchup when the games are there.
   - The opponent's cards that beat you, per matchup.

Out, by Martin's verdict on 2026-10-24: skill sensitivity across ratings, climb rate per hour, win rate by game length, going first or second, bot-simulated counterfactual mulligans, and any confidence decoration ("NO, unless it's done in non-AI slop way"): a number carries its game count where it needs one, and a minimum-games filter does the rest.

## The data

For now the league's bot games stand for human play (Martin, 2026-10-24: "for all intents and purposes bot league = human play"); people's games join the same counts when there are enough. Each league game since 2026-10-24 22:57 keeps its card facts (`league/facts.py`, written by the runner to `results/league/facts/<day>.jsonl`): every card the mulligan showed and every card sent back, each card's draw and play turn, who went first, and both players' ratings as the game began.

Archetypes are Martin's: he grouped, named and pruned the lists on 2026-10-25, recorded in `animal_kingdom/data/archetypes.json`. A list born later joins its parent's archetype. Decks are named by him, never by habitat and tag ("there are no classes or colors in this game").
