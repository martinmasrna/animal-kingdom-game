# Simulation Results

Here's the complete referee run (referee vs referee, 150 games/matchup, 1,800 games per card, seed 0, map_b + 2-action, pending_payoff=20).

Row = deck as seat A, cell = that deck's win % vs the column deck. (~±8% CI per cell at 150 games.)

┌───────────────────┬───────┬────────┬──────┬────────┬──────┬──────┬──────┐
│      ↓A \ B→      │ aggro │ canine │ cats │ colony │ egg  │ food │ ramp │
├───────────────────┼───────┼────────┼──────┼────────┼──────┼──────┼──────┤
│ aggro_hq_rush     │  47.3 │   60.0 │ 33.3 │   78.0 │ 56.7 │ 79.3 │ 65.3 │
├───────────────────┼───────┼────────┼──────┼────────┼──────┼──────┼──────┤
│ canine_buff_tempo │  40.0 │   42.0 │ 29.3 │   49.3 │ 48.7 │ 54.0 │ 24.7 │
├───────────────────┼───────┼────────┼──────┼────────┼──────┼──────┼──────┤
│ cats_midrange     │  62.0 │   72.0 │ 44.7 │   82.7 │ 73.3 │ 69.3 │ 28.7 │
├───────────────────┼───────┼────────┼──────┼────────┼──────┼──────┼──────┤
│ colony_food_swarm │  26.0 │   48.7 │ 23.3 │   45.3 │ 47.3 │ 66.7 │ 57.3 │
├───────────────────┼───────┼────────┼──────┼────────┼──────┼──────┼──────┤
│ egg_control       │  44.7 │   48.0 │ 22.0 │   50.0 │ 58.0 │ 62.7 │ 28.0 │
├───────────────────┼───────┼────────┼──────┼────────┼──────┼──────┼──────┤
│ food_otk          │  20.0 │   42.7 │ 32.7 │   27.3 │ 36.7 │ 46.0 │ 33.3 │
├───────────────────┼───────┼────────┼──────┼────────┼──────┼──────┼──────┤
│ ramp              │  37.3 │   82.0 │ 71.3 │   50.0 │ 70.0 │ 66.7 │ 54.0 │
└───────────────────┴───────┴────────┴──────┴────────┴──────┴──────┴──────┘

Deck strength (both-seat avg):

1. cats 62.6%
2. aggro 60.2%
3. ramp 60.0%
4. colony 45.1%
5. egg 44.5%
6. canine 42.3%
7. OTK food 35.3%

Run-level: food win 70.8% / HQ-capture 29.2%, first-player 50.1%, avg 13.6 turns.

cats_midrange (deck win rate 64.7%)

   card               WR_drawn  impact   tag / str / text
🟡  prince_leo          67.9%   +3.3%   Cat · STR 3 · Battlecry: you may immediately play Princess Lea from your hand or deck.
🟡  princess_lea        67.7%   +3.0%   Cat · STR 3 · Battlecry: you may immediately play Prince Leo from your hand or deck.
🔵  jaguar              67.6%   +2.9%   Cat · STR 5 · Battlecry: remove an adjacent enemy of strength 5 or less.
🟡  king_theron         67.0%   +2.3%   Cat · STR 8 · When one of your Cats covers an enemy unit, remove that enemy.
⚪  tiger               65.9%   +1.2%   Cat · STR 7 · Apex Predator.
🟡  queen_adira         65.7%   +1.0%   Cat · STR 5 · When one of your Cats removes an enemy unit, draw 1 card.
🔵  serval              65.6%   +0.9%   Cat · STR 2 · Battlecry: remove an adjacent enemy of strength 6 or more.
⚪  lynx                65.5%   +0.8%   Cat · STR 3 · Battlecry: if you control another Cat, draw 1.
🔵  snow_leopard        65.1%   +0.5%   Cat · STR 6 · Your other Cats may be placed onto enemy units of equal or lower strength.
🔵  black_panther       64.7%   +0.0%   Cat · STR 6 · Stealth.
⚪  house_cat           64.4%   -0.2%   Cat · STR 1 · Battlecry: if you control another Cat, play one more Cat from your hand (other than House Cat).
⚪  caracal             64.2%   -0.4%   Cat · STR 4 · Battlecry: if placed on top of an enemy unit, draw 1 card.
⚪  lion                63.7%   -1.0%   Cat · STR 7 · (vanilla)
⚪  cougar              61.9%   -2.7%   Cat · STR 6 · You may place this adjacent to any Cat you control, ignoring connection.

aggro_hq_rush (deck win rate 61.9%)

   card               WR_drawn  impact   tag / str / text
⚪  lemming             63.2%   +1.4%   Rodent · STR 1 · Battlecry: place all Lemmings from your hand and deck on random adjacent empty crossroads.
🔵  hornet              62.1%   +0.2%   — · STR 2 · Flight. Battlecry: you may remove another Hornet from your hand or deck. If you do, destroy an adjacent enemy unit.
⚪  mouse               60.7%   -1.2%   Rodent · STR 1 · Battlecry: draw a Rodent.
🔵  jerboa              60.6%   -1.3%   Rodent · STR 2 · Battlecry: play another unit.
🟡  pestis              59.8%   -2.1%   Rodent · STR 3 · Battlecry: remove everything from an adjacent crossroad.
⚪  bat                 59.6%   -2.3%   — · STR 2 · Flight. Battlecry: draw 1 card.
⚪  cheetah             59.2%   -2.7%   Cat · STR 5 · Battlecry: if you play this next t card.
🟡  verminus            59.0%   -2.9%   Rodent · STR 3 · Has +1 strength for each other
🔵  chameleon           59.0%   -2.9%   Lizard · STR dyn · May be placed on any unit, and any unit may be placed on top of it.
⚪  falcon              58.9%   -3.0%   Bird · STR 4 · Flight. Battlecry: if you play the, draw 1 card.
⚪  rat                 58.7%   -3.2%   Rodent · STR 2 · Battlecry: remove a card in your hand to destroy an adjacent enemy unit.
🟡  sirocco             58.5%   -3.4%   — · STR 5 · Battlecry: return all enemy units adjacent to this to their owner's hand.
🔵  skunk               57.8%   -4.1%   — · STR 4 · Return an adjacent enemy to your opponent's hand. They can't play it next turn.
🟡  gale                54.8%   -7.1%   Bird · STR 4 · Flight. The first time an enemy unit covers this, return that enemy unit to its owner's hand.

ramp (deck win rate 61.7%)

   card               WR_drawn  impact   tag / str / text
🟡  bulwark             69.2%   +7.6%   Megafauna · STR 10 · Immovable. Costs 20 food. Battlecry: remove all adjacent enemy units.
🟡  methuselah          69.1%   +7.5%   Megafauna · STR 5 · Immovable. At the end of your turn, gain 5 food.
🔵  rhinoceros          65.3%   +3.7%   Megafauna · STR 6 · Battlecry: remove all adjacent enemies of strength 5 or less.
⚪  grizzly_bear        64.6%   +2.9%   Bear · STR 7 · Battlecry: in 2 turns, remove a random adjacent enemy.
🔵  polar_bear          64.4%   +2.7%   Bear · STR 8 · Apex Predator.
🔵  andean_condor       64.2%   +2.5%   Bird · STR 4 · Flight. Reveal top card of both decks. If yours has higher strength, draw it.
🔵  hippopotamus        63.9%   +2.3%   Megafauna · STR 6 · When an enemy unit is placed on an adjacent crossroad, remove it if its strength is 3 or less.
⚪  black_bear          63.6%   +2.0%   Bear · STR 5 · Battlecry: in 2 turns, draw 1 card.
🟡  borealis            62.2%   +0.5%   Bear · STR 10 · Apex Predator. Costs 20 food.
🟡  aquila              61.3%   -0.4%   Bird · STR 8 · Flight. Apex Predator. Costs 20 food.
⚪  elephant            61.0%   -0.7%   Megafauna · STR 8 · Immovable. Costs 20 food.
⚪  oxpecker            60.8%   -0.9%   Bird · STR 1 · Flight. Gain 1 food for each unit in your starting deck with strength 6 or more.
⚪  watering_hole       60.7%   -1.0%   — · STR 0 · Fragile. At the start of next turn, draw a unit with strength 6 or more.
⚪  fig_tree            60.1%   -1.6%   — · STR 0 · Fragile. At the start of next turn, gain 20 food.

colony_food_swarm (deck win rate 44.3%)

   card               WR_drawn  impact   tag / str / text
🔵  termite_queen       50.3%   +6.0%   Colony / Queen · STR 5 · Battlecry: you may play one additional non-Queen Colony unit this turn.
🟡  queen_honoria       50.3%   +6.0%   Colony / Queen · STR 5 · Whenever you play a Colony unit, gain 5 food.
🟡  vesper              49.9%   +5.6%   Colony · STR 2 · Flight. Has +2 strength for each other friendly Colony unit.
🟡  falstaff            48.3%   +4.0%   Colony · STR 3 · Flight. Whenever you gain food, gain 3 additional food.
🟡  queen_marabunta     46.3%   +1.9%   Colony / Queen · STR 4 · Battlecry: gain 4 food for each other friendly Colony unit.
🔵  nurse_bee           46.1%   +1.8%   Colony · STR 2 · Flight. Battlecry: if you control two copies of the same Colony unit, draw 2 cards.
🔵  termite_king        45.6%   +1.2%   Colony · STR 5 · Battlecry: if you control a Colony Queen, draw 1 card.
⚪  soldier_ant         44.0%   -0.4%   Colony · STR 2 · Battlecry: if you control 5 or more Colony units, remove an adjacent enemy.
⚪  worker_wasp         43.8%   -0.5%   Colony / Worker · STR 3 · Flight. At the end of your turn, gain 3 food.
🔵  nurse_bumblebee     43.5%   -0.8%   Colony · STR 2 · Flight. Battlecry: if you control 5 or more Colony units, draw 2 cards.
⚪  queen_bee           43.5%   -0.8%   Colony / Queen · STR 2 · Battlecry: play a Worker unit.
⚪  worker_bee          43.5%   -0.9%   Colony / Worker · STR 1 · Flight. Battlecry: gain 5 food; if you control another Worker, gain 5 more.
⚪  guard_hornet        43.5%   -0.9%   Colony · STR 3 · Flight. Has +5 strength while you control 5 or more Colony units.
⚪  worker_ant          43.1%   -1.2%   Colony / Worker · STR 1 · Battlecry: gain 8 food.

egg_control (deck win rate 43.6%)

   card               WR_drawn  impact   tag / str / text
🟡  eon                 50.4%   +6.8%   Snake · STR 7 · Whenever a card is drawn, shuffled or removed, gain 1 food.
🟡  black_swan          48.3%   +4.7%   Bird · STR 3 · The first time each turn you draw Black Swan, your opponent removes a random card from their hand.
🟡  ember               47.9%   +4.3%   Bird · STR 6 · Flight. When this is removed, shuffle it back to your deck.
🔵  stoop               46.6%   +3.1%   Bird · STR 4 · Flight. Battlecry: remove an adjacent enemy of strength 4 or less.
⚪  raven               46.3%   +2.8%   Bird · STR 2 · Flight. Battlecry: draw 3 cards, then shuffle 2 cards back.
⚪  owl                 45.7%   +2.1%   Bird · STR 2 · Flight. Battlecry: look at the top 3 cards; draw 1 and shuffle the rest.
⚪  anaconda            45.2%   +1.6%   Snake · STR 7 · Apex Predator.
🟡  aurum               44.9%   +1.3%   Egg · STR 0 · Fragile. At the start of your turn, draw a card.
🔵  rattlesnake         44.7%   +1.2%   Snake · STR 0 · Whenever you shuffle a card, gain 1 strength (wherever this is).
⚪  eagle               44.6%   +1.0%   Bird · STR 5 · Flight.
⚪  bird_egg            43.9%   +0.3%   Egg · STR 0 · Fragile. After 2 turns, remove this and draw 2 Birds.
⚪  snake_egg           43.6%   +0.1%   Egg · STR 0 · Fragile. After 2 turns, remove this and draw 2 Snakes.
🔵  goliath             43.3%   -0.2%   Snake · STR dyn · This unit's strength is equal to the number of removed units.
🔵  egg_eater           43.1%   -0.5%   Snake · STR 4 · Whenever an Egg is removed, gain 10 food.

canine_buff_tempo (deck win rate 41.1%)

   card               WR_drawn  impact   tag / str / text
🟡  raksha              53.7%  +12.6%   Canine · STR 4 · Your other Canines have +2 strength.
🟡  shuck               46.9%   +5.8%   Canine · STR 6 · Battlecry: return a removed Canine to your hand. Give it +2 strength.
🟡  clarion             46.6%   +5.5%   Canine · STR 4 · Battlecry: give +1 strength to all other Canines in your hand and battlefield.
⚪  fox                 46.1%   +5.1%   Canine · STR 5 · Whenever this gains strength, draw a card (once per turn).
🟡  lobo                44.8%   +3.8%   Canine · STR 4 · Has +2 strength for each other Canine you control.
⚪  dingo               44.6%   +3.6%   Canine · STR 5 · At the end of your turn, give a friendly adjacent Canine +1 strength.
🔵  red_wolf            44.6%   +3.5%   Canine · STR 6 · Battlecry: give +1 strength to all Canines in your hand.
⚪  dog                 42.4%   +1.4%   Canine · STR 1 · Battlecry: if you control another Canine, play another Canine from your hand (other than Dog).
⚪  gray_wolf           41.9%   +0.9%   Canine · STR 4 · Battlecry: remove an adjacent enemy with less or equal strength.
⚪  african_wild_dog    41.8%   +0.7%   Canine · STR 2 · Has +1 strength for each friendly Canine.
🔵  bush_dog            40.6%   -0.4%   Canine · STR 3 · Once a turn, when this gains strength, give all friendly adjacent Canines +1 strength.
🔵  dhole               40.0%   -1.1%   Canine · STR 3 · Battlecry: give all adjacent Canines +2 strength.
⚪  coyote              39.6%   -1.5%   Canine · STR 3 · Battlecry: if this has 5 or more strength, draw a card.
🔵  jackal              38.2%   -2.9%   Canine · STR 3 · Whenever an adjacent unit is removed, gain 3 food.

food_otk (deck win rate 32.8%)

   card               WR_drawn  impact   tag / str / text
🟡  greywhisker         39.1%   +6.3%   Rodent · STR 1 · Battlecry: gain 1 food. Draw 1 card. You may play 1 more unit.
🔵  giant_tortoise      36.6%   +3.7%   — · STR 7 · Immovable.
⚪  chipmunk            35.5%   +2.7%   Rodent · STR 1 · Battlecry: gain 10 food. At the start of next turn, gain 10 more.
🔵  porcupine           35.5%   +2.7%   Rodent · STR 7 · Cannot be covered by enemy units.
🟡  fathom              35.0%   +2.1%   — · STR 4 · Battlecry: draw a legendary unit.
🟡  carmilla            34.8%   +2.0%   Arachnid · STR 5 · Battlecry: remove up to 3 friendly units. Draw a card for each.
🔵  flying_squirrel     34.0%   +1.1%   Rodent · STR 4 · Flight. Battlecry: gain 8 food.
⚪  black_widow         33.5%   +0.7%   Arachnid · STR 3 · Battlecry: remove an adjacent
⚪  gazelle             33.2%   +0.3%   — · STR 2 · When this is removed, gain 30 food.
🔵  opossum             33.1%   +0.3%   — · STR 2 · Battlecry: gain 5 food and draw 1 card. Deathrattle: return this to your hand.
⚪  squirrel            32.5%   -0.4%   Rodent · STR 3 · Battlecry: gain 12 food.
⚪  impala              30.9%   -2.0%   — · STR 2 · When this is removed, draw 2.
🟡  scrooge             29.6%   -3.3%   Rodent · STR 4 · Immovable. Battlecry: store all your food. In 2 turns, recover twice as much.
⚪  pufferfish          29.5%   -3.3%   Fish · STR 2 · When an enemy unit is placed on top of this, remove that enemy unit and this unit. Draw 1 card.

# Martin Notes

- Cats are in a good shape, despite having the highest winrate. But the deck is *internally balanced*, each card sits within ±5% impact score, with legendaries being at the top and commons being at the bottom. That's an amazing signal, and it means the balance must be done from bottom-up -- we must improve and re-balance other decks, not overnerf cats.

- Food OTK is clearly the biggest problem, and by a wide margin. From my own gameplay, I can confirm that the deck simply sucks. Scrooge being 2nd lowerst winrate card tells the whole story -- the OTK is never happening. This should be the #1 goal of the session -- complete overhaul of the food OTK deck.

- Aggro's highest impact card is a common (Lemming), but I think that's okay. It's a unique card, perfect flavor, and it fits the deck well. Plus, it's not like its winrate is over the top compared to other cards. Overall, I would say Aggro sits in the same category as Cats -- good deck that should serve as a benchmark that other decks need to clear.

- Egg control should be left alone for now -- we have a strong suspision deck is very good, but the bots are not yet at a level to pilot it to it's full potential.

## Proposed Specific Changes

### Cats

- [ ] Nerf Jaguar to destroy enemies with strength 4 or less, not 5 or less -- this is the only change I'd make to Cats

## Aggro

- [ ] Gale needs to get changed or reworked, because this clearly isn't working. Maybe just buffing to 6 strength or so is enough?

### Ramp

- [ ] Bullwark seems turbo omega broken -- maybe make it so that he removes all adjanced units, including allies?
- [ ] Same for Rhino, seems too strong as it is
- [ ] Nerf Grizzly bear to 6 strength

### Colony

- [ ] Nerf termite queen to 3 strength, it's too strong as a rare like this
- [ ] Nerf queen Honoria to: STR 4 · Whenever you play a Colony unit, gain 4 food.
- [ ] Nerf Vesper to strength 0
- [ ] Buff worker ant to give 15 food (just compare the current state to squirrel xd)
- [ ] Buff worker bee to "gain 10 food; if you control another Worker, gain 10 more." might be too much, but we'll see.
- [ ] Buff Nurse Bumblebee to 3 strength

### Canine

- [ ] Nerf Raksha to "your other Canines have +1 strength". Buff it's own stregth to 5 to compensate.
- [ ] Nerf fox to 3 strength -- it's way too strong for a common as it is
- [ ] Buff Dhole to "Battlecry: give all adjacent Canines +3 strength."
- [ ] Buff Jackal to "STR 5 · Whenever an adjacent unit is removed, gain 5 food."
