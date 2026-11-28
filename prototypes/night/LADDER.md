# Skill ladder

How far each alive prototype's skill ceiling sits, by proxy: a ladder of bots, Random < Greedy < Expert N < Expert 4N < Expert 16N, where N is the Expert budget (play-outs or iterations) its builder gated with, and 16N drops to 8N where it would not finish in time. Each adjacent pair plays 200 games, every deal twice with the seats swapped; a cell is the stronger rung's score in percent (wins + half the draws), with its 95% interval. "Top > Random" is the top rung over 100 games where the gate's Expert N lost any games to Random, otherwise the gate's own Expert N number. "Mirror draws" is the draw rate of the gate's Expert N mirror. Each folder's `ladder.json` has every count and `ladder.mjs` reruns it.

A clear win means the interval sits above 50. Near 50 at 4N against N means more search buys nothing: either the game has little left to find (big gaps, Expert against Random or Greedy, still win big) or luck decides (even big gaps win modestly). The ladder measures each prototype's own search: these bots sample play-outs under a fixed play-out rule, so a rung near 50 can also mean the search stopped improving before the game did.

41 is one player against the game: every rung plays the same 200 seeded games and a pair is compared game by game (a win beats a loss, then more Wall, then more rounds); "Mirror draws" is the share of even pairs at the top.

| Prototype | N | Greedy > Random | N > Greedy | 4N > N | Top > 4N | Top > Random | Mirror draws | Reading |
|---|---|---|---|---|---|---|---|---|

