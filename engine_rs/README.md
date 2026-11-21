# The engine in Rust

The same game as the Python package's `animal_kingdom/engine/`: the position, the rules, every card's effect, built as the Python module `ak_engine`. It reads the same card table (`data/cards.json`), the same map (`data/maps.json`) and the same `Config`, and saves a position in the same shape, so a match saved by either engine loads in the other. `tools/engine_rs/fuzz.py` proves the two agree position by position.

## Build

```
cd engine_rs && VIRTUAL_ENV=$PWD/../.venv PATH="$PWD/../.venv/bin:/opt/homebrew/bin:$PATH" ../.venv/bin/maturin develop --release
```

It needs the Rust toolchain (`brew install rust`) and maturin in the venv (`.venv/bin/pip install maturin`), and takes about fifteen seconds. Build output goes to `engine_rs/target/`, which git ignores.

## Use

```python
import ak_engine, dataclasses, json
eng = ak_engine.Engine(cards_json_text, maps_json_text, json.dumps(dataclasses.asdict(Config())), "map_hex19")
st = eng.new_game(deck_a, deck_b, seed, first_player=None, leaders={"A": "elf_legend", "B": "sage_legend"})
st = eng.from_dict(saved)            # a position saved by either engine
st.legal_actions()                   # action dicts, in the Python engine's order
st.apply_action({"kind": "place", "card_id": "wisp_2", "target": ["cr", "1,2"]})   # validate=False skips the legality check
st.can_pass(); st.is_terminal(); st.player_to_act(); st.clone(); st.to_dict()
st.record_events(True); st.take_events()     # the Python engine's event dicts; off by default, a search never needs them
```

`State` also answers what the server shows: `mana_left`, `mana_total`, `mana_cost`, `power_cost`, `leader_usable`, `region_income`, `card_strength`, `effective_strength`, and `apply_logged` / `early_mulligan` / `apply_early_mulligan` for the mulligan both players make at once. `tools/engine_rs/common.py` builds both engines from the bundled data.

## Proof

- `tools/engine_rs/fuzz.py --games 3000 --jobs 6 --coverage`: random games through both engines at once, compared after every action on the saved position (the board's tiles in the order they were taken), the legal actions in order, the events, the result, and each seat's mana, costs, strengths and income. Half the games add cards for the rules no card uses today (Armor, Stealth, Poison, a strength that is a count, a 0-strength body) and tight configs that reach the turn caps and the hand limit.
- `tools/engine_rs/oracle.py`: every logged game that still replays on today's Python engine, replayed side by side.
- `tools/engine_rs/speed.py`: clone-and-apply pairs a second for both engines on the same positions.

Run the fuzz and the oracle after any change to either engine. While the Python engine exists, a change to a rule or to a card's effect is made in both and the fuzz says whether they still agree; a change to a card's numbers is data and needs nothing.

## Layout

- `data.rs`: what never changes during a game: the card table, the map, the `Config`. A card id and a tile are small integers in the order of their names, so "sorted" is numeric.
- `cards.rs`: what each card does, keyed by card id (the Python `EFFECTS` table). A new card effect starts here.
- `state.rs`: the position. The board is a flat array of top units and one short list of what is beneath them; hands, decks and the effect stack sit inline, so a clone is a few flat copies with no allocation when nothing is resolving.
- `effects.rs`: strength and cost, placement, covering, removal, food, draws, the effect stack and its steps, the leaders' powers.
- `rules.rs`: legal actions, applying an action, the turn, the mulligan at once, the end of the game.
- `actions.rs`, `json.rs`, `events.rs`: the action dicts, the saved position, the event dicts.
- `rng.rs`: CPython's `random.Random`, bit for bit, so a game replays identically from its seed in either engine.
- `py.rs`: the Python module.

## Not here

The seat's view (`GameState.view_for`), the card loader's validation, the deck rules (`animal_kingdom/decks.py`) and the `MAKES` table the client reads are not ported: nothing in the rules reads them.
