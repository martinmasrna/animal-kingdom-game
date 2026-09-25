# CLAUDE.md

*Animal Kingdom* is a two-player tactical deckbuilding game Martin is designing, meant to become a digital game people play competitively. This repo holds its rules engine, the bots, the simulation tools used to design and balance it, and a terminal interface.

**Start every session at [`docs/STATUS.md`](docs/STATUS.md)**: where the game stands, its open problems, and what's waiting on Martin. Before reasoning about any card, effect or balance change, read [`docs/rules/mental-model.md`](docs/rules/mental-model.md).

## The trap

The game has no mana, no attack or health, no combat damage. A unit is a single number, strength, and the only resource is the action (two per turn). It borrows Magic/Hearthstone vocabulary ("Battlecry", "draw", "removal"), and pattern-matching onto those games ("dies to a ping", "mana curve", "go wide for damage") is the most common mistake made here.

## Commands

Python ≥3.11 with a venv at `.venv`: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev,cli]'` (add `analysis` for self-play training and plots).

- Tests: `.venv/bin/python -m pytest -q` (about a minute).
- Web client: `./play` (serves `animal_kingdom/web/` at localhost:8000; `AK_NO_GAME_LOGS=1` keeps test games out of `results/human_games/web/`). Terminal: `./run` (interactive setup; `--help` for flags). Recorder UI: `./record` (needs the `tui` extra).
- Balance report: `./report 200` (round-robin; `--deck X --opponent Y` to scope, `--format files --out DIR` for CSV/JSON, `--log FILE` to record games). Replay a logged game with no bot compute: `.venv/bin/python -m animal_kingdom.sim.replay FILE`.
- Paired bot A/B: `.venv/bin/python -m animal_kingdom.sim.bot_comparison --games 200 --out results/bot_quality/<name>`.
- Deckbuilding and the goodstuff problem: `sim.deck_optimizer`, `sim.metagame_search`, `sim.measure_deck`, `sim.benchmark_set` (see `docs/design/goodstuff.md`).
- After changing `cards.json`, regenerate the deck docs' card tables: `.venv/bin/python -m animal_kingdom.render.deck_docs`.

The ruleset (map_b, two actions per turn, Draw draws 2) is the default everywhere; no flags needed. `results/` is untracked except `results/human_games/`: human recordings are irreplaceable, so commit them.

## Invariants

- `engine/` is stdlib-only and transport-agnostic; file loading happens only at construction. `apply_action` validates every action; only bot search, which applies actions it just generated, passes `validate=False`.
- Card numbers live in `cards.json` (strength, food cost, text) or `engine/config.py` (effect magnitudes), never as literals in effect code. `test_card_text_consistency.py` checks printed numbers against config; extend it when a card gains a new kind of number.
- Bots are generalist (no deck slugs, archetype names or card ids in policy) and honest (never read hidden information). Both are regression-tested.
- Never nerf a card to fix a bot. A simulation finding is either a card signal or a pilot flaw; triage it first (the `balance-eval` skill).
- Balance and bot claims need ≥200 games per matchup, paired seeds, both seats.
