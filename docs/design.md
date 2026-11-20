# Design

What the game is for and what Martin has said about its shape, with his words and dates. Decided means he decided it; everything else here is his reaction and stays open. The rules as they play now are in [`STATUS.md`](STATUS.md).

## What a card game is for

Martin's model, restated by an agent and confirmed by him (2026-11-20: "You understand the model way, exactly how I'd put it"):

- **Before the match** I pick how I want to play: the deck is a plan that is mine, known before I sit down, reliable enough to carry out in most games. Winning with it counts double; losing is cushioned because the deck can be fixed. Picking an existing deck and building one are the same act.
- **In the match** I carry the plan out against a hand I can't see, and each turn is a judgement, not a calculation: what is he holding and how much do I respect it, do I spend this card now or keep it for when it's worth more, am I ahead enough to play safe or behind enough to gamble, does the plan still hold here.
- **Across matches** each card is something I learn (how to play it, hold it, play around it), and that carries from deck to deck.
- **What kills it:** luck that can't be prepared for, cards from outside the decks, two players playing solitaire, one heuristic that is right 90% of the time.

The agent's reading, which he agreed with: every in-match decision is about *when*, and reading, bluffing, risk and tempo all rest on a card in hand that is sometimes right to keep. So a rule or a card is judged by whether it makes *when* matter and gives a held card worth. His essay `essay-core.md` (workspace root, 2026-11-14) is the same argument from complexity and depth: as little to learn as possible, as much to master.

Why mana: the old rules' two actions a turn ate two cards a turn, so cards could never be scarce and a held card had no worth. Mana with the two-action limit kept was "worst of both worlds" (2026-11-20).

## The shape of the rules

- **Effects are local.** Every effect acts through the board: "remove an adjacent enemy", never "remove an enemy". No cards that act anywhere from hand (2026-11-20: "If we allows spells from hand, we're losing big part of what makes the indetity of our game -- the hexagonal board, the connectivty and adjacency mechanics"). A role other games give a spell becomes a card on the board acting on what is next to it or connected to it.
- **Strength is four things at once** (2026-11-20): removal (it covers one more size), flexibility (more tiles it may land on), defence (one more size can't cover it) and burn (one more food on a raid). Cards never attack, so two 5s hold two tiles where one 10 holds one. Cost is a liability of its own (dead in hand until affordable, the whole turn spent), so strength per mana rises with cost and decks live mostly at low cost: "there is a reason why in hearthstone vanilla minions end at 7 mana, and why no mana curve is linear".
- **Fast.** "our game is much more fast-paced than hs, and I want to keep it that way" (2026-11-20, on the mana cap; the cap went to 10 later that day).
- **His numbers and readings of 2026-11-20** (open, his starting points): the den raid as the win, starting at 15, 30 wins, 0 loses ("instead of stealing it destroys"); a covered card removed ("covered units don't get shuffled back into the deck, they just get removed"); opening hands "3 for first and 4 for second"; a leader's power at 3 mana; base tiles open to both players (the rule that only the owner could place there was "just dumb"). The card food numbers are his to rescale.
- **Evidence comes from people.** "we will not let bot data drive our decisions" (2026-11-20): a bot plays well enough to show the screen; whether the game is good, his and other people's games decide.

## The board and the screen

- **Decided:** the board is hexagonal tokens touching, the card in hand and the piece on the board one shape (2026-11-16: "I played 2 games and I'm convinced, this is 100% the way to go"); the tiling is locked and the visuals around it designed from scratch (2026-11-17); the board runs bottom to top on every device, your side at the bottom (2026-11-17); blue you, red opponent, one measured hue each (2026-11-18). One picture per card everywhere (2026-11-17: "The hexagon IS the card ... Imagine it's a physical board game and we're just trying to translate it into digital one").
- **Reactions on the mana screen (2026-11-20):** phone first ("desktop will just have to deal with it somehow, same way marvel snap did"); "food to be center, same way hero you're attacking is in HS. It the one and only windondition. The hero is basically nothing more than decoration"; the leader as scenery; the hand bottom centre (anywhere else is "a design crime"). He rejected a den floating under the board, anything breaking the board's hexagon-of-hexagons silhouette, frames that exist only to fit geometry ("a LOT of dead chrome"), food as a number on the leader's drawer (it reads as strength), and five separate elements on a void. He asked about a tilted board and pointed out that hexagons keep their shape in perspective; the tilt and the standing pieces followed.
- **Reactions on the look (2026-11-17), from the animal cards:** the spirit "in spirit of Clash of Clans", "very colorful and cheerful", "childlike without being childish", "playful, not dark and gloomy and aggressive".
- How Martin judges screens and motion, and how to work on them with him: the `ui-design` skill.
