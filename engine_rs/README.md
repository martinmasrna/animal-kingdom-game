# The engine

The game's rules: the position, what is legal, what every card does. It is the only implementation of them. The crate builds the Python module `ak_engine`; the server, the tools and the tests reach it through `animal_kingdom/game.py`, which holds no rules of its own. The bots (`src/bots/`) are Rust code calling the engine directly.

## Build

`./play`, `./test` and `./cards` build it themselves whenever its source is newer than the built module (`engine_rs/build.sh --if-stale`, about ten seconds). By hand: `engine_rs/build.sh`.

It needs the Rust toolchain (`brew install rust`, or rustup) and maturin in the venv (`.venv/bin/pip install maturin`). Build output goes to `engine_rs/target/`, which git ignores. A machine with no Rust toolchain cannot run the game from source; it plays on staging.

## Adding or changing a card

- **Its numbers and text** (cost, strength, keywords, the words on it) are data: `tools/cards/hq.py`, nothing to build.
- **An effect another card already has**: one line in `src/cards.rs` `behaviour()`, naming the card id under the effect.
- **A new effect**: a variant in `src/cards.rs` (`Roar`, `OnCover`, `OnDeath`, `OnRaid`, or a field of `Behaviour`), and what it does in `src/effects.rs` (`run_roar` and its neighbours). An effect that waits for a choice is a step on the effect stack: a `StepKind` in `src/state.rs`, run in `effects.rs` `run_op`, saved and loaded in `src/json.rs`.
- **Any number the effect uses** goes in the `config!` table in `src/data.rs`, never in effect code.
- **A test** for the rule in `animal_kingdom/tests/test_rules.py` (it sets positions up by hand and plays them through the engine), then `tools/engine_rs/fuzz.py`.

## Use

```python
from animal_kingdom import game
s = game.new_game(deck_a, deck_b, seed, leaders={"A": "elf_legend", "B": "sage_legend"})
game.legal_actions(s); game.apply_action(s, game.PlaceAction("wisp_2", ("cr", "1,2"))); game.is_terminal(s)
s.to_dict(); game.GameState.from_dict(saved)
```

`game.py` also gives the engine's data as Python values: `CARDS`, `LEADERS`, `MAKES`, `Config()` (the rules' numbers), `load_map()`, `deck_problems()`, `validate_card_record()`.

The module itself, for code that needs speed (a bot, a tool playing many games):

```python
import ak_engine
eng = ak_engine.Engine(cards_json_text, maps_json_text, config_json_text, "map_hex19")
st = eng.new_game(deck_a, deck_b, seed, None, {"A": "elf_legend", "B": "sage_legend"})
st.legal_actions(); st.apply_action({"kind": "place", "card_id": "wisp_2", "target": ["cr", "1,2"]}); st.clone(); st.to_dict()
```

A broken rule raises `ValueError`. A panic inside the engine is caught at the binding and raised as `RuntimeError`, so it never takes the server down; `game.py` turns both into `EngineError`.

## Checks

- `tools/engine_rs/fuzz.py --games 3000 --jobs 6 --coverage`: random games over every card, and after every action the checks no position may fail (a saved position loads the same, a finished game offers nothing, no animal stays buried, no hand past its limit, a refused action changes nothing). Half the games add cards for the rules no card uses today (Armor, Stealth, Poison, a strength that is a count, a 0-strength body) and tight configs that reach the turn caps, the turn limit and the hand limit.
- `animal_kingdom/tests/test_rules.py`: each rule and each card's effect, on positions set up by hand.
- `tools/engine_rs/speed.py`: clone-and-apply pairs a second, the number a bot's thinking time buys (about 4 million on one core of the M1 Pro).

The deploy image compiles the engine and runs the fuzz and the tests on that build before it ships (`deploy/Dockerfile`).

## Layout

- `data.rs`: what never changes during a game: the card table and what makes a record valid, the map, the rules' numbers (`config!`). A card id and a tile are small integers in the order of their names, so "sorted" is numeric.
- `cards.rs`: what each card does, keyed by card id; the leaders and their texts; the cards a card makes.
- `state.rs`: the position. The board is a flat array of top units and one short list of what is beneath them; hands, decks and the effect stack sit inline, so a clone is a few flat copies with no allocation when nothing is resolving.
- `effects.rs`: strength and cost, placement, covering, removal, food, draws, the effect stack and its steps, the leaders' powers.
- `rules.rs`: legal actions, applying an action, the turn and its caps, the mulligan at once, the end of the game.
- `view.rs`: what the server reads beyond the rules: a seat's view, how a unit shows, the leaders, the deck rules.
- `actions.rs`, `json.rs`, `events.rs`: the action dicts, the saved position, the event dicts.
- `rng.rs`: CPython's `random.Random`, bit for bit, so a logged game replays from its seed and a saved position keeps its random stream.
- `py.rs`: the Python module.
- `bots/`, `bin/bot_bench.rs`: the bots and their benchmark (`tools/bot_bench/README.md`).
