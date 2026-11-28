# 29 Hidden runner: rules

Asymmetric, two players: the **Runner** (one hidden piece) and the **Hunter** (two visible pawns). Roles alternate from game to game.

**Setup.** A 4×4 grid of nodes, orthogonal links only. The Hunter's pawns start on the two corners of row 4. The Runner secretly chooses any node of row 1 as its start. Each side has its own 12-card deck (below), shuffled, and draws 3. Energy: 2 each.

**A round.**

1. Both sides gain 2 energy (cap 5) and draw 1 (nothing once a deck is empty).
2. **Runner.** Plays one card (paying energy) or the basic Step (free: move 1 orthogonally, or stay). The kind of card is announced; the destination is not. The Runner can never enter a pawn's node or a Blocked node.
3. **Hunter.** Moves each pawn 1 orthogonally or leaves it (free), and may play one card, before or after moving (or between the two pawn moves).
4. If a pawn is on the Runner's node, the Hunter wins.
5. At the end of rounds 3, 6 and 9, the Runner's node is shown.

**End.** The Hunter wins by landing a pawn on the Runner's node. The Runner wins by surviving to the end of round 12.

**Runner deck (12).**

| Card | Cost | Text | Copies |
|---|---|---|---|
| Dash | 1 | Move 1 or 2 in a straight line. | 4 |
| Slip | 1 | Move 1 diagonally. | 3 |
| Hide | 1 | Stay; Searches this round answer "no". | 2 |
| Smoke | 2 | Stay or Step; skip the next scheduled reveal. | 1 |
| Double | 2 | Step twice. | 2 |

**Hunter deck (12).**

| Card | Cost | Text | Copies |
|---|---|---|---|
| Sprint | 1 | One pawn moves up to 2 orthogonally instead of 1 (only where it ends counts). | 4 |
| Search | 1 | Name a node: you learn whether the Runner is on it or orthogonally next to it. | 4 |
| Flare | 3 | The Runner's node is shown now. | 2 |
| Block | 1 | Put a Block on a node for 3 rounds (the Runner's moves of the next two rounds); the Runner cannot enter it. | 2 |

Changed after the first gate (the one change the brief allows): Sprint reaches 2, not 3. With 3, two pawns reach nearly every node of the 4×4 grid in one round, so any sighting ends the game.

Rulings the spec left open: Dash moves in a straight line (Double, "Step twice", can turn), so the two differ; a Runner already on a node that gets Blocked may stay; a Sprint counts as that pawn's move for the round.
