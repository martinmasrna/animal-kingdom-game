# 32 Hidden contracts

Every number here is a placeholder.

**The question.** When points come from face-down contracts whose conditions you must meet and the opponent must guess and deny, does reading the opponent's goal shape every attack?

## Setup

- Each player has the same 30-card main deck (list below), shuffled, and a separate contract deck of the 8 contracts below, shuffled. Each draws 2 contracts and keeps them face-down.
- There is no life total. Board max 6 units. Units attack enemy units only.
- Random first player; the first player draws 3 main cards, the second draws 4 and gets the Coin (0 mana: gain 1 mana this turn).
- Points start at 0. Target: 10.

## Turn

1. Your maximum mana goes up by 1 (cap 10) and refills. Your units become ready. Draw 1. Drawing from an empty main deck gives the opponent 1 point.
2. **Contracts.** Every contract you hold whose condition is true now is revealed and scores its points; it is discarded and you draw a replacement (if your contract deck has any). You never hold more than 2.
3. Play cards by paying their cost; a unit cannot attack on the turn it is played. Once per turn you may pay 1 mana to discard a held contract face-down and draw a replacement.
4. Each ready unit may attack an enemy unit once: both deal their attack to each other. Damage stays.
5. End the turn.

## End

- Reaching 10 points wins at once.
- If both players hold no contracts and both contract decks are empty, the higher score wins; equal is a draw.

## Contracts (8 per player; condition at the start of your turn)

| Contract | Condition | Points |
|---|---|---|
| Crowd | You control 4 or more units. | 3 |
| Tower | You control a unit with 6 or more health. | 2 |
| Clean | The opponent controls no units. | 3 |
| More | You control more units than the opponent. | 2 |
| Hunter | You destroyed 2 or more enemy units during your last turn. | 2 |
| Force | Your units' total attack is 10 or more. | 3 |
| Spread | You control units of 3 different costs. | 2 |
| Patience | You hold 6 or more cards in hand. | 2 |

## Main deck (30, both players)

The template deck of `hs/vanilla`, spells hitting units only: Striker 1: 2/1, Raider 2: 3/2, Guard 2: 2/3, Line 3: 3/4, Heavy 4: 4/5, Big 5: 5/5, Huge 6: 6/7, Hit 2 (1 mana), Hit 3 (2 mana), Hit 6 (4 mana): 2, 3 or 6 damage to a unit. Three copies of each.

## Builder notes

- Hidden information: the Expert determinizes the opponent's held contracts from the contracts not yet revealed, and never reads them.
- Greedy: plays the most expensive affordable cards; attacks that destroy an enemy unit and survive.
- Set positions: free trade (your ready Heavy against an enemy Raider: attack it); don't waste (never pay to replace a contract whose condition already holds); don't waste (never Hit 6 a 2-health unit while Hit 2 is in hand). There is no one-move lethal here, because contracts score only at the start of your turn.
