# The card board's changes file

`changes.json`, beside this note, is Martin's card design as he made it on the card board: every card he changed and every card he made, field by field. It never touches the game. When he says "implement changes from my card board", apply it as below, through `tools/cards/hq.py` as every card change goes, then show him what you applied and what you could not.

The board server keeps the file current: a change the game already has drops out by itself (on the board's next load), and `was` is always what the game has now. So the file is exactly the list of what still differs.

## `changed`: existing cards, by card id

```json
"action_4": {
  "name":     {"was": "Trainer", "now": "Drill Sergeant"},
  "strength": {"was": 3, "now": 5},
  "stars":    {"was": 0, "now": 1},
  "text":     {"was": "Action: give an animal in your hand +2 strength.", "now": "Action: ... Roar: Scout a Bird."},
  "tags":     {"was": ["Colony"], "now": ["Colony", "Queen"]}
}
```

Only the fields he changed are there. Each `now` is his value, to apply as is:

- `name`: the card's display name. `hq.py set ID animal` takes `{"name", "species"}`: keep the species, change the name.
- `strength`: `hq.py set ID strength N`. `was: null` is a planned card that had none.
- `stars`: the card's level, -1 to 3 (-1 small, 0 ordinary, 1 strong, 2 legendary, 3 monster). `was` is the card's `stars` field, or its rarity's default (common 0, rare 1, legendary 2) when it has none. Apply it however hq.py sets stars.
- `text`: the effect text, word for word: `hq.py set ID effect "TEXT"`. Words between `**` are ones Martin made bold. The game bolds only its own keywords (`KEYWORDS` in `animal_kingdom/web/static/card.js`), so apply the text without the asterisks, and tell him which bold words the game will not bold by itself: each is a keyword or rules term he means, which the game does not have yet.
- `tags`: the family line, a list: `hq.py set ID tag "A, B"`.

If `was` differs from what the game has when you apply it (someone changed the card since), stop and ask Martin about that card. If hq.py refuses a value as locked, report it; never force it.

## `new`: cards he made, by a board id (`new1`, `new2`, ...)

```json
"new1": {"copy_of": "action_4", "name": "Drill Sergeant II", "rarity": "common", "strength": 5, "stars": 0,
         "text": "...", "tags": [], "habitat": "Meadow", "species": "Trainer"}
```

`copy_of` is the card he started from (null: a blank card). The board shows a copy with its original's painting; the new card has no art of its own. The board id is not a game id: give it a real one by the game's rule (its animal), which usually means asking Martin what animal it is when `species` is empty or still the original's. Then `hq.py add`, and set its rarity, strength, stars, effect and tag. It lands in the reserve, as every new card does.

## After applying

Changed cards need no cleanup: once the game has his values, the board drops them from the file on its next load, and what remains is what was not applied. New cards do: take each one you made into the game out of `new`, and raise `rev` by one in the same write, so an open board reloads instead of saving its old copy back over yours. Then tell Martin to reload the board.
