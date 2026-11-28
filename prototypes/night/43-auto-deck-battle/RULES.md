# Auto deck battle

Your deck fights by itself; your skill is what you put in it. Life 10 each. Bring the opponent to 0, or have more life after 12 rounds.

- Your deck starts as 3 Pips and holds at most 10 cards. Both decks are public (the opponent's as it stood at the start of the round); shops are secret.

## A round

- **Shop**, both players at once: 6 gold (what is left is lost). Your shop shows 4 random cards from the 8 below.
  - Buy a shop card: pay its cost; it joins your deck.
  - Reroll: 1 gold for 4 new shop cards.
  - Remove: 1 gold, one card out of your deck (once per round).
- **Battle**: both decks are shuffled; the top card of each is its front card. Each step the two front cards deal their attack to each other at once. A card at 0 health falls (it stays in your deck for later rounds) and your next card becomes the front card, its Enters text happening then. Damage lasts for this battle only.
- The battle ends when a side has no front card and no cards left. The other side deals 1 damage plus 1 per card it still has (front and undrawn), at most 4. Both out at the same step: no damage.

## Cards

| Card | Cost | Attack/Health | Text |
|---|---|---|---|
| Pip | 1 | 1/2 | |
| Brawler | 2 | 3/2 | |
| Wall | 2 | 1/5 | |
| Bomb | 3 | 2/1 | When it falls, 3 damage to the enemy front card. |
| Opener | 3 | 2/3 | Enters: 2 damage to the enemy front card. |
| Rally | 3 | 1/3 | When it falls, your next front card gets +2/+2. |
| Guardian | 3 | 2/4 | Takes 1 less damage from each hit. |
| Heavy | 4 | 4/6 | |
