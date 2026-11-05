# Composing puzzles

The bench used to compose the puzzle sets (`knowledge/puzzles/set-1-2026-11-05.md`). Run from this folder with the
repo's venv (`../../../.venv/bin/python`).

- `c.py`: `c.mk(board, hand_a, hand_b, turns)` builds a puzzle from a compact board (`{"4,2": "+lion -pup"}`: + the
  solver's, - the defender's, bottom to top, `^n` a given strength counter); `c.run(pz, obvious=[line, ...])` prints the
  board, the verdict, the winning first turns with the defence's reply, and what the defence does to each obvious line.
- `gen1.py N [ideas...]`, `gen2.py N [ideas...]`: searches over open boards with an idea's card in hand, for one-turn and
  two-turn puzzles; a find is forced, has one winning first turn and plays the idea's card. Most finds are "play the one
  card that can": they are raw material to pick from by hand, not puzzles.
- `doc.py`: writes the set document from the puzzle files and `notes.py` (each puzzle's obvious move and difficulty).

The puzzle files in `animal_kingdom/data/puzzles` are the source of truth; `../solve.py write <id>` fills a file's
solution and main line, `../solve.py check` verifies them all.
