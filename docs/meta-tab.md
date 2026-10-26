# The Meta tab: the competitive player's tool

The Ladder screen's Meta tab is where a competitive player prepares for ladder. It is meant to become the game's first-party equivalent of HSReplay or HSGuru, with complete data instead of a tracker sample, and later the paid "pro" tool Martin described on 2026-10-24 as the game's honest way to make money (useful tools for players who compete, instead of gambling mechanics). The free and paid split is not designed yet; until it is, the tool is built as good as it can be, whole (Martin, 2026-10-24: "let's not worry about Free/Pro split at all now").

## Who it is for

Players for whom fun is winning and climbing: the competitive hobbyist and the pro, not the casual. Martin, 2026-10-24: the tool must not treat them as people who need things explained; "I want the data presented in the best possible way, but I don't want them synthesized". No guides, no written advice, no generated text: raw numbers, presented well, and the player draws the conclusions.

## The two questions

1. Which deck should I play?
   - The meta by rating: what each archetype's share of games is. Rating (one two-handled slider), the last so many days (a week by default, counted back from now) and a minimum of games filter the whole tab.
   - The tier list and the matchup matrix, sortable. Clicking several columns (decks you keep meeting) gives every deck's average against just those.
   - Each archetype's lists, one row each: its win rate and games beside the portraits of the cards it runs beyond the ones every list shares (Martin, 2026-10-26). A player plays an exact list, so the card figures below are one list's, the most played first.
2. How should I play it?
   - Per card: Mulligan (in the opening hand after the mulligan, replacements included), Drawn (at any point) and Played, as HSReplay counts them (Martin, 2026-10-24 and 2026-10-26), each shown as the card's win rate minus its list's, in points ("+/- is better than raw percentages", 2026-10-26), so a strong deck's cards don't look strong for the deck's sake. Drawn and Played run above zero for most cards (longer games see more cards, the side ahead plays more): cards are compared with each other. Per list on the archetype page, per matchup when an opponent is chosen, and for every card under the matchup matrix, pooled over the lists running it.
   - A figure on fewer games than the filter shows a "?" and sorts after the sure ones; nothing is hidden (Martin, 2026-10-26). A card reads as in the collection: hovered, beside it; right-clicked, held or tapped on a phone, large.
   - The opponent's cards that beat you, per matchup.

Out, by Martin's verdict on 2026-10-24: skill sensitivity across ratings, climb rate per hour, win rate by game length, going first or second, bot-simulated counterfactual mulligans, and any confidence decoration ("NO, unless it's done in non-AI slop way"): a number carries its game count where it needs one, and a minimum-games filter does the rest.

## The data

For now the league's bot games stand for human play (Martin, 2026-10-24: "for all intents and purposes bot league = human play"); people's games join the same counts when there are enough. Each league game since 2026-10-24 22:57 keeps its card facts (`league/facts.py`, written by the runner to `results/league/facts/<day>.jsonl`): every card the mulligan showed and every card sent back, each card's draw and play turn, who went first, and both players' ratings as the game began.

Only games on the current cards count (Martin, 2026-10-25: "the Meta tab should only show games played on current cards"). The server keeps each card's print, everything on it that plays, and when a card changes it forgets every game of each list holding that card, both sides, so that list counts again from its new cards while the rest keep theirs. A change the print does not show (an engine fix, an effect's number in the config) goes through `/api/league/meta/forget` with the lists it touches. The league runner plays from a frozen copy of the code, so it is refrozen whenever cards change on live, or it keeps posting games on the old cards as current.

Archetypes are Martin's: he grouped, named and pruned the lists on 2026-10-25, recorded in `animal_kingdom/data/archetypes.json`. A list born later joins its parent's archetype. Decks are named by him, never by habitat and tag ("there are no classes or colors in this game").
