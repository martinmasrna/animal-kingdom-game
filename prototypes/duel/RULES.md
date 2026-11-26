# Duel prototypes: the rules they implement

Three throwaway toys for one question each. They are not the game and carry none of its rules or its world. Every name and number here is a plain placeholder chosen by an agent on 2026-11-26 so the feel can be tested; nothing here is decided.

- `nogrid/` holds two versions on one page, **Hidden** and **Open**, with a switch.
- `grid/` holds the third, **Grid**.

What each one is for: Hidden asks whether guessing feels like reading the opponent or like a coin flip. Open asks whether a mind game survives when everything is visible. Grid asks whether position adds a read worth its rules.

## Shared base (all three versions)

### Winning

Two heroes. A hero at 0 health or less loses. If both reach 0 in the same step, the match is a draw.

### Heroes

| | Heavy | Quick |
|---|---|---|
| Health | 31 | 28 |
| Mana regained per turn | 3 | 4 |
| Passive | **Unstoppable:** damage of 2 or less never cancels your cards. | **Light feet:** the first Fast action you take each turn costs 1 less (never below 0). |

### Mana

Both heroes start at 10 mana. The cap is 10. A hero regains its regeneration at the start of each of its turns (in Hidden and Grid: at the start of each round), never above the cap. Mana that is not spent is kept.

### Cards

Each hero has its own 20-card deck (lists below), shuffled. Opening hand 4. Draw 1 at the start of each of your turns (each round in Hidden and Grid), the first included. A deck does not cycle: when it is empty nothing is drawn and nothing else happens. No hand limit. Both deck lists are public, and so is every card already played; only the order of the deck and the contents of a hand are hidden.

### Actions

On a turn a hero takes up to 2 actions. An action is a card from hand or a basic. Each basic can be used at most once a turn. Basics cost mana and are never used up.

Basics, the same for both heroes:

| Basic | Cost | Speed | Kind | Effect |
|---|---|---|---|---|
| Jab | 1 | Fast | Light attack | 2 damage. |
| Block | 1 | Fast | Defence | Guard: the first Light hit against you this turn is stopped. |

### Kinds of card

- **Light attack:** deals its damage unless a guard stops it.
- **Heavy attack:** deals its damage; guards do nothing against it.
- **Defence:** puts up a guard. A stopped hit deals no damage and cancels nothing.
- **Setup:** everything else (mana, healing, drawing, lasting bonuses).

### Speed and cancelling

Every card and basic has a speed: Fast, Normal or Slow. Faster resolves first.

**Cancelling:** when a hero takes damage from an attack, every Slow card of that hero that has not resolved yet is cancelled. The mana stays spent and the card goes back to its owner's hand. Fast and Normal cards are never cancelled. Heavy's passive means damage of 2 or less does not cancel his cards.

### The cards

| Card | Cost | Speed | Kind | Effect |
|---|---|---|---|---|
| Slash | 2 | Normal | Light attack | 4 damage. |
| Lunge | 3 | Fast | Light attack | 4 damage. |
| Flurry | 3 | Normal | Light attack | Two separate hits of 2 damage. |
| Smash | 4 | Slow | Heavy attack | 8 damage. |
| Haymaker | 6 | Slow | Heavy attack | 12 damage. |
| Parry | 2 | Fast | Defence | Guard: the first Light hit against you this turn is stopped, and its attacker takes 3 damage. That damage is not an attack: it cancels nothing. |
| Brace | 2 | Fast | Defence | Guard: every Light hit against you this turn is stopped. |
| Meditate | 0 | Slow | Setup | Gain 3 mana (up to the cap). |
| Bandage | 2 | Slow | Setup | Heal 5 (not above starting health). |
| Sharpen | 3 | Slow | Setup | For the rest of the match each of your attack hits deals 1 more damage. Stacks. |
| Study | 2 | Normal | Setup | Draw 2 cards. |

A hero with two guards up uses them in the order played; each guard that stops "the first Light hit" is used up by one hit.

### Decks

- **Heavy:** 2 Slash, 1 Lunge, 2 Flurry, 3 Smash, 3 Haymaker, 2 Parry, 2 Brace, 1 Meditate, 2 Bandage, 1 Sharpen, 1 Study.
- **Quick:** 3 Slash, 3 Lunge, 3 Flurry, 2 Smash, 3 Parry, 1 Brace, 2 Meditate, 1 Bandage, 1 Sharpen, 1 Study.

## Version 1: Hidden

The match is played in rounds; both heroes act in every round.

1. Both regain mana and draw.
2. Both choose up to 2 actions in secret (the total cost must be affordable) and commit. Choosing nothing is allowed.
3. Everything is revealed and mana is paid.
4. Resolution in three steps: all Fast actions, then all Normal, then all Slow. Inside a step both heroes' actions resolve at the same time: all damage of the step is worked out first and applied together, and cancelling caused by a step only affects later steps.
5. Guards put up in a round last until the end of that round.

## Version 2: Open

Alternating turns; everything played is visible at once. The first player is chosen at random, and the second player starts with one extra card.

On your turn:

1. Your Slow cards that are winding up resolve now, in the order they were played.
2. Regain mana and draw.
3. Take up to 2 actions, one at a time, face up. A Fast or Normal action resolves immediately. A Slow card is paid for and placed in front of you, **winding up**: it resolves at step 1 of your next turn.
4. A guard you put up lasts until the start of your next turn.

Cancelling applies to cards that are winding up: if you take damage from an attack (more than 2 for Heavy), your winding-up cards are cancelled and go back to your hand.

## Version 3: Grid

Version 1 (Hidden), plus position.

### The board

Each hero has its own 3 by 3 area. The two areas face each other. Columns, from the centre line outwards: **front**, **middle**, **back**. Rows: top, middle, bottom. A hero stands on one tile of its own area and starts on the middle tile.

### Stepping

Every round, in addition to up to 2 actions, a hero may take one free step to a tile next to its own (up, down, forward or back, never diagonal, never out of its area). The step is chosen in secret with the actions.

### Order of a round

All Fast actions, then both steps, then all Normal actions, then all Slow actions. So a Fast attack hits a hero where he stood at the start of the round, and a Normal or Slow attack hits where he stands after stepping.

### Aiming

An attack names its target tiles on the enemy area when it is chosen. It hits only if the enemy hero stands on one of them when the attack resolves. A miss does nothing.

**Melee** attacks can be used only if the attacker stands in his own front column when the attack resolves (otherwise the action does nothing and its mana is spent), and they reach only the tiles listed below. **Ranged** attacks work from anywhere.

| Attack | Reach | Tiles it covers |
|---|---|---|
| Jab (basic) | Melee | One tile of the enemy front column. |
| Slash | Melee | The whole enemy front column. |
| Lunge | Melee | One whole row (all three tiles). |
| Flurry | Melee | Two different tiles of the enemy front column, one hit of 2 on each. |
| Smash | Melee | A 2 by 2 block anywhere in the enemy area. |
| Haymaker | Melee | The whole enemy front and middle columns. |

Two ranged cards exist only in this version:

| Card | Cost | Speed | Kind | Effect |
|---|---|---|---|---|
| Bolt | 2 | Normal | Light attack, ranged | 3 damage to one tile anywhere. |
| Blast | 5 | Slow | Heavy attack, ranged | 7 damage to one whole row. |

Decks in this version: each deck swaps 1 Slash and 1 Flurry for 2 Bolt, and 1 Smash for 1 Blast. Heavy also swaps 1 Haymaker for 1 Slash, and Quick 1 Meditate for 1 Smash.

Health in this version: Heavy 26, Quick 34. With position in play Heavy's big attacks are worth far more than in the other two versions, and it took these numbers and the two extra swaps to bring bot matches between the heroes near even.

### Fatigue (this version only)

At the start of a round, a hero whose deck is empty takes damage instead of drawing: 1 the first time, 2 the next, then 3, and so on, counted per hero. If this brings both heroes to 0 in the same round the match is a draw. Without it a match with two empty decks never ends: a Block each round stops the only attack left.

Guards, cancelling, mana, cards and everything else are as in Version 1.
