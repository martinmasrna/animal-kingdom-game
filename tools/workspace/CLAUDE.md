# Animal Kingdom workspace

Start every session here, never in a subfolder. Two git repos live inside, each committed and pushed on its own (`git -C`):

- `game/`: the game itself: rules engine, bots, simulation, web client, card data, docs. Its `CLAUDE.md` is the project's instructions; read it next, then `game/docs/STATUS.md`.
- `design/`: the design sandbox: mockups, design notes, the painted masters the game's art is exported from, the card-art tooling. An asset store and a workbench the game's skills reach into, never a product of its own; `design/HANDOFF.md` is its map.

The `.claude/` here (the card-data hook, permissions) and this file are copies of `game/tools/workspace/`; edit them there and copy up.
