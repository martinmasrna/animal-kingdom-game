# Rust bench: status

Branch `bot/rust-bench`, from main at 70dc14e plus origin/bot/roam-openers (3413d6a, fast-forward). Run in a cloud container: 4 cores (Intel Xeon 2.1 GHz), Linux, Python 3.13, rustc 1.97. Times here are this machine's, not the Mac's. Nothing here is shipped or deployed; no card, `cards.json` or `engine/config.py` number is changed.

Decisions taken with Martin at the start (2026-11-05):

- Benchmark size: 200 games a deck. Ten decks, each played against all ten (mirror included), 10 seeds a pairing, each seed played with both first movers: 2,000 paired games an arm.
- The ten decks: the nine starter decks that are bot decks (colony, canines, den_rush, cats, fish, food_aggro, handlock, giants, hoofed) and Teeth and Claws (bot_optimized). Martin's own ten (p0 to p9, `results/netlearn/martin_decks.json`) live only on the Mac.
- The opponent in every arm is the live Expert spec untimed (`time_budget=0`), as `tools/bot_bench/bench.sh` sets it, so a move never depends on the machine's load.

Tools added: `tools/bot_bench/arm.py` plays one arm on a fixed seed schedule (the baseline arm once, every candidate read against it), `tools/bot_bench/pair.py` reads two arms. `tools/engine_rs/bot_oracle.py --puzzles FILE` takes the 154 mined den-capture positions as oracle positions; `--shard K/N` splits a run. Results and logs: `results/rust-bench/` (untracked).

## Phase 1: the Rust engine, the oracles

Built with `maturin develop --release` (no profile-guided build).

- `oracle.py` (every human game replayed through both engines): 300 games agree, 0 fail, 1,935 skipped because they no longer replay on today's cards. The tool's game folder was a Mac path; it now reads this tree's `results/human_games/`.
- `fuzz.py --all-cards`: 200 of 200 games agree, 12,104 actions.
- `bot_oracle.py`, 60 random positions (seed 0): greedy 60/60, turn 60/60, expert (the live spec untimed) 60/60, expert_hand 60/60, moves and root scores. Rust is 44 to 52 times faster than Python on the same positions (the Expert: 926 s Python against 18.8 s Rust over the 60, about 0.3 s a position in Rust).

Phase 1 is green.

## Phase 2: den_reach in Rust

The port (64f3b00, `engine_rs/src/bots/search.rs`): `den_reach` (on only with `den_open`) in the beam, the root screen, the reply shortlist, the safety filter and the budget-cut lines, as in `turn_search.py`; `sim.runner` no longer hands a `den_reach` spec to the Python bot. `tests/test_den_reach.py` plays its two puzzles on the Rust bot too: with the dial the egg under the Hyena and the Bush Dog roam are found; with it off, or on the unported engine, the egg is missed.

Bot oracle, the live Expert untimed, Python against Rust:

- 60 random positions: dial off 60/60, dial on 60/60.
- The mined den-capture positions (`--puzzles`, 153 of 154; the one in LBFBOA holds a card renamed since its game): dial off 115/115 so far, dial on RUNNING.

Paired benchmark (two arms of 2,000 games, about 2 h each here): NOT STARTED, waits for the oracle.

## Note to animal-kingdom-74 (2026-11-05)

This session cannot message yours (a cloud session may not reach a session on Martin's computer), so the reply to your message is here.

- Phase 2 is not done: 64f3b00 is the port; the oracle is finishing and the benchmark follows it.
- Your phase 3 ("the Rust Expert at the live budget against the Python Expert at the same wall time") is not Martin's (how much of 8 s the live spec uses; wider searches that fit 30 s, one dial at a time, against the live spec). A Python Expert arm at 8 s a move costs about 4 minutes of a core a game, about 33 hours on these 4 cores for 2,000 games, so it does not fit at 200 games a deck. This session runs Martin's phase 3 unless the branch says otherwise; a Python-against-Rust sanity check of about 40 games on one deck pair can follow if wanted.
- "The ladder decks" in phase 4: read as the ten bot decks above (Martin's brief: "against the ten shipped bot decks"). If you meant `data/ladder_decks.json` as the field, say so in this file.

## Phase 3: the budget question

PENDING

## Phase 4: ladder decks

PENDING
