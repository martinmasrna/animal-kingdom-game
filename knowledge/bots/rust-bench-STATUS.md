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

PENDING

## Phase 3: the budget question

PENDING

## Phase 4: ladder decks

PENDING
