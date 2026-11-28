# 29 Hidden runner

Every number here is a placeholder. Borrowed: Scotland Yard's hidden movement, where the hidden player reveals its position on set rounds and the seekers learn only the kind of move it made. The rest is not that game: a small grid, two seekers, and both sides play costed move cards from decks.

**The question.** When one side moves in secret and the other must deduce and corner it, with moves bought from small decks on both sides, does each side face real choices every round?

## Setup

- A 4×4 grid of nodes, orthogonal links only. Two roles: the **Runner** (one hidden piece) and the **Hunter** (two visible pawns). Roles alternate from game to game.
- The Hunter's pawns start on the two corners of row 4. The Runner secretly chooses any node of row 1 as its start.
- Each side has its own 12-card deck (lists below), shuffled, and draws 3. Energy: 2 each.

## A round

1. Both sides gain 2 energy (cap 5) and draw 1.
2. **Runner.** Plays one card (paying energy) or the basic Step (free: move 1 orthogonally, or stay). The kind of card is announced; the destination is not. The Runner can never enter a pawn's node or a Blocked node.
3. **Hunter.** Moves each pawn 1 orthogonally or leaves it (free), and may play one card, before or after moving.
4. If a pawn is on the Runner's node, the Hunter wins.
5. At the end of rounds 3, 6 and 9, the Runner's node is shown.

The engine answers Searches and catches honestly; the Runner bot sees only what a Hunter would see when it plays the Hunter.

## End

The Hunter wins by landing a pawn on the Runner's node. The Runner wins by surviving to the end of round 12.

## Runner deck (12)

| Card | Cost | Text | Copies |
|---|---|---|---|
| Dash | 1 | Move up to 2 orthogonally. | 4 |
| Slip | 1 | Move 1 diagonally. | 3 |
| Hide | 1 | Stay; Searches this round answer "no". | 2 |
| Smoke | 2 | Stay or Step; skip the next scheduled reveal. | 1 |
| Double | 2 | Step twice. | 2 |

## Hunter deck (12)

| Card | Cost | Text | Copies |
|---|---|---|---|
| Sprint | 1 | One pawn moves up to 3 orthogonally instead of 1. | 4 |
| Search | 1 | Name a node: you learn whether the Runner is on it or orthogonally next to it. | 4 |
| Flare | 3 | The Runner's node is shown now. | 2 |
| Block | 1 | Put a Block on a node for 3 rounds; the Runner cannot enter it. | 2 |

## Builder notes

- The Hunter bot keeps the set of nodes consistent with everything public (starting row, announced card kinds, reveals, Search answers, Blocks) and determinizes over it; it never reads the Runner's node.
- Greedy Hunter: moves both pawns toward the nearest possible node, Searches when the possible set has 4 nodes or fewer. Greedy Runner: moves to maximise distance from the nearest pawn, using its most expensive move card.
- The first-player check becomes a role check: the Runner's win rate over seats must lie within 30–70%.
- Set positions: Hunter lethal (the Runner was just shown next to a pawn with every exit covered: move onto it); Runner don't blunder (never step next to a pawn when a node out of reach exists); free Search (only two nodes possible: Search one of them).
