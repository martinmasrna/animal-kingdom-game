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

## Phase 2: den_reach in Rust (done here: the port and the oracle; the benchmark runs on the Mac)

The port (64f3b00, `engine_rs/src/bots/search.rs`): `den_reach` (on only with `den_open`) in the beam, the root screen, the reply shortlist, the safety filter and the budget-cut lines, as in `turn_search.py`; `sim.runner` no longer hands a `den_reach` spec to the Python bot. `tests/test_den_reach.py` plays its two puzzles on the Rust bot too: with the dial the egg under the Hyena and the Bush Dog roam are found; with it off, or on an engine without the port, the egg is missed.

Bot oracle, the live Expert untimed, Python against Rust, moves and root scores:

- 60 random positions (seed 0): dial off 60/60, dial on 60/60.
- The mined den-capture positions (`--puzzles tools/puzzles/forced_captures-2026-11-05.jsonl`, 153 of 154; the one in LBFBOA holds a card renamed since its game): dial off 153/153, dial on DIALON.

The paired benchmark (wins, den captures, time per move) did not run here: the cloud credit ends at 09:00 CET (animal-kingdom-74, 2026-11-05). Its commands are below.

## Phases 3 and 4: ready to run on the Mac

Setup, once, from a checkout of `bot/rust-bench` (the benchmark plays what the venv's `ak_engine` is, so build it from this branch; the oracles after any build):

```
git fetch origin bot/rust-bench && git checkout bot/rust-bench
cd engine_rs && ../.venv/bin/maturin develop --release && cd ..
.venv/bin/python -m pytest -q animal_kingdom/tests/test_den_reach.py     # 7 passed: the Rust puzzles need the port
E=$(.venv/bin/python -c 'from animal_kingdom.web.match import EXPERT; print(EXPERT.replace("time_budget=8","time_budget=0"))')
D=colony,canines,den_rush,cats,fish,food_aggro,handlock,giants,hoofed,bot_optimized
A=results/rust-bench/arms
J=8     # worker processes: the Mac's free cores
```

How an arm runs (`tools/bot_bench/arm.py`, docstring has the rest): the pilot spec in seat A on every deck of `$D` against every deck of `$D` (mirror included), 10 seeds a pairing, each seed with both first movers: 200 games a deck, 2,000 an arm. Seeds are `683470156 + pair index * 1000 + i`, so every arm on the same `$D` is paired game for game with every other. The opponent is always the live Expert untimed (`$E`), so no move depends on the machine's load. Each game appends one line to the arm's file (winner, reason, turns, every pilot move's seconds) and its log to `<file>.logs.jsonl`; a killed arm resumes where it stopped. Here one game took about 15 core-seconds (the live spec), so an arm is about 8 core-hours; wider dials cost more. Run under `nice -n 15`, one arm at a time.

`tools/bot_bench/pair.py BASE CAND [--md]` reads two arms: per deck and pooled, both win rates, the paired difference and its 95% interval (the bootstrap of `sim.bot_comparison`), dens taken, dens lost, dens lost by turn 5, seconds a move; then each arm's move-time median, 95th and 99th percentile, slowest, and how many moves took over 8 s and over 30 s.

Phase 2 benchmark (den_reach on against off):

```
nice -n 15 .venv/bin/python tools/bot_bench/arm.py --spec "$E" --opponent "$E" --decks $D --games 10 --jobs $J --out $A/live.jsonl
nice -n 15 .venv/bin/python tools/bot_bench/arm.py --spec "$E,den_reach=true" --opponent "$E" --decks $D --games 10 --jobs $J --out $A/den_reach.jsonl
.venv/bin/python tools/bot_bench/pair.py $A/live.jsonl $A/den_reach.jsonl --md
```

Phase 3, the budget question. (a) How much of 8 s the live spec uses: the `live.jsonl` arm above is untimed, so its move times are what the search needs when nothing cuts it; `pair.py`'s timing lines give the share of moves over 8 s (where the live budget binds) and over 30 s. Measure on a quiet Mac with `--jobs` at or under the core count; the arm's times are under the load of its own workers. (b) Wider searches, one dial at a time, each an arm read against `live.jsonl`:

```
nice -n 15 .venv/bin/python tools/bot_bench/arm.py --spec "$E,determinizations=10" --opponent "$E" --decks $D --games 10 --jobs $J --out $A/hands10.jsonl   # more imagined hands (5)
nice -n 15 .venv/bin/python tools/bot_bench/arm.py --spec "$E,beam_width=16" --opponent "$E" --decks $D --games 10 --jobs $J --out $A/beam16.jsonl          # a wider beam (8)
nice -n 15 .venv/bin/python tools/bot_bench/arm.py --spec "${E/depth=1/depth=2}" --opponent "$E" --decks $D --games 10 --jobs $J --out $A/depth2.jsonl       # a third round (depth 1)
nice -n 15 .venv/bin/python tools/bot_bench/arm.py --spec "${E/reply_turns=3/reply_turns=6}" --opponent "$E" --decks $D --games 10 --jobs $J --out $A/reply6.jsonl   # deeper reply search (3 openings)
for x in hands10 beam16 depth2 reply6; do .venv/bin/python tools/bot_bench/pair.py $A/live.jsonl $A/$x.jsonl --md; done
```

Before a long arm, play a few games of it (`--games 1 --decks cats --opponents den_rush`) and read its slowest move: a dial whose 99th percentile is past 30 s on the Mac does not fit Martin's budget whatever it wins. A dial is a real gain when its pooled interval clears zero with no deck down beyond its own interval (the bot-change skill's rule).

Phase 4, ladder decks (docs/wave-2.md step 2): `tools/bot_bench/deck_climb.py` hill-climbs a list from a shipped bot deck, the Expert untimed in both seats, against the ten decks of `$D`. A neighbour swaps every copy of one card for an unused collectible card of the same rarity (the seed's shape stays; `decks.decklist_problems` checks every list). Fitness is the mean win rate on 2 seeds a field deck, both movers (40 games a list); 6 neighbours a step, at most 10 steps, stop after 3 barren. Then `--check 10`: the seed list and the finalist on 10 fresh seeds a field deck, both movers (200 games each), paired. Three archetypes, three seeds (all legal lists; Rodents is 29 cards, so not a seed):

```
for s in den_rush hoofed giants; do
  nice -n 15 .venv/bin/python tools/bot_bench/deck_climb.py --seed-deck $s --field $D --spec "$E" --games 2 --neighbors 6 --steps 10 --patience 3 --check 10 --jobs $J --out results/rust-bench/climb_$s.json
done
```

A climb is at most 1 + 60 lists of 40 games plus 400 check games, about 2,800 games (about 12 core-hours here) per seed. The JSON keeps every step, the finalist (`best`) and the check with its per-opponent rates. The lists go to `knowledge/bots/ladder-decks-2026-11-05.md` for Martin as card lists with the check's numbers; nothing ships, no `decklists.json` edit.

## Known limits

- The search fitness uses 40 games a list, so a step's accept is noisy (about ±8 points); the 200-game check is the verdict, against the seed list on other seeds.
- Every arm's opponent is the live Expert untimed, as in `bench.sh`; a candidate that wins only by out-searching is still read against the same opponent every time.
