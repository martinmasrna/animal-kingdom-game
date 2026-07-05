Wrote 7350 games to results/matrix_referee_otk_rework/ (matchup_matrix.csv, per_card_stats.csv, summary.json)
Win conditions: exhaustion=0.1%, food=62.9%, hq_capture=37.0%
First-player win rate: 49.5%
Avg game length: 14.4 turns

Caveat: Balance conclusions are only as good as the bots. GreedyBot now credits scheduled/delayed single-card payoffs (Egg hatch, Bear removal) via pending_payoff, but a 1-ply eval still underplays multi-card combos and in-turn sequencing chains (e.g. Wild Dogs / Domestic Cat) that need turn search. Treat these numbers as bot-limited; confirm suspect verdicts with the turn/referee pilots.

"Drawn" is presence-only (was the card in hand at any point), not exact copy counts. A card returned to hand by an effect (e.g. a bounce) counts as drawn again, which can inflate draw_rate/impact slightly for bounce-heavy decks.

### Matchup matrix (row = A, column = B, cell = A's win rate)
```
                     cats   aggr   ramp   egg_   colo   food   cani   TotA   Both
cats_midrange        49%    61%    41%    73%    71%    71%    78%    66%    68% 
aggro_hq_rush        27%    46%    73%    61%    71%    72%    71%    62%    63% 
ramp                 60%    30%    57%    70%    39%    63%    85%    58%    55% 
egg_control          23%    38%    47%    45%    48%    54%    61%    45%    46% 
colony_food_swarm    24%    29%    71%    43%    53%    45%    55%    45%    44% 
food_otk             23%    27%    38%    39%    61%    47%    53%    40%    40% 
canine_buff_tempo    17%    29%    17%    39%    49%    53%    47%    34%    33% 
TotB                 71%    64%    52%    46%    44%    40%    33%    n/a    n/a 
```

### cats_midrange (deck win rate 68.3%)
```
   card             WR_drawn  impact   tag / str / text
🟡  prince_leo          70.5%   +2.3%   Cat · STR 3 · Battlecry: you may immediately play Princess Lea from your hand or deck.
🟡  princess_lea        70.3%   +2.1%   Cat · STR 3 · Battlecry: you may immediately play Prince Leo from your hand or deck.
🔵  jaguar              70.3%   +2.0%   Cat · STR 5 · Battlecry: remove an adjacent enemy of strength 5 or less.
⚪  tiger               69.9%   +1.7%   Cat · STR 7 · Apex Predator.
🟡  queen_adira         69.4%   +1.1%   Cat · STR 5 · When one of your Cats removes an enemy unit, draw 1 card.
🔵  snow_leopard        69.3%   +1.1%   Cat · STR 6 · Your other Cats may be placed onto enemy units of equal or lower strength.
🟡  king_theron         68.4%   +0.1%   Cat · STR 8 · When one of your Cats covers an enemy unit, remove that enemy.
⚪  lion                67.9%   -0.4%   Cat · STR 7 · (vanilla)
⚪  lynx                67.9%   -0.4%   Cat · STR 3 · Battlecry: if you control another Cat, draw 1.
⚪  house_cat           67.3%   -1.0%   Cat · STR 1 · Battlecry: if you control another Cat, play one more Cat from your hand (other than House Cat).
⚪  caracal             67.1%   -1.1%   Cat · STR 4 · Battlecry: if placed on top of an enemy unit, draw 1 card.
🔵  serval              67.0%   -1.2%   Cat · STR 2 · Battlecry: remove an adjacent enemy of strength 6 or more.
🔵  black_panther       66.8%   -1.5%   Cat · STR 6 · Stealth.
⚪  cougar              66.0%   -2.3%   Cat · STR 6 · You may place this adjacent to any Cat you control, ignoring connection.
```

### aggro_hq_rush (deck win rate 63.4%)
```
   card             WR_drawn  impact   tag / str / text
⚪  lemming             64.4%   +0.9%   Rodent · STR 1 · Battlecry: place all Lemmings from your hand and deck on random adjacent empty crossroads.
🔵  jerboa              63.8%   +0.4%   Rodent · STR 2 · Battlecry: play another unit.
🟡  verminus            63.4%   -0.0%   Rodent · STR 3 · Has +1 strength for each other unit you control.
🔵  hornet              62.4%   -1.1%   - · STR 2 · Flight. Battlecry: you may remove another Hornet from your hand or deck. If you do, destroy an adjacent enemy unit.
🟡  pestis              62.2%   -1.2%   Rodent · STR 3 · Battlecry: remove everything from an adjacent crossroad.
⚪  falcon              61.9%   -1.6%   Bird · STR 4 · Flight. Battlecry: if you play this next to the opponent's base, draw 1 card.
⚪  bat                 61.2%   -2.2%   - · STR 2 · Flight. Battlecry: draw 1 card.
⚪  mouse               61.1%   -2.3%   Rodent · STR 1 · Battlecry: draw a Rodent.
⚪  rat                 60.9%   -2.6%   Rodent · STR 2 · Battlecry: remove a card in your hand to destroy an adjacent enemy unit.
🟡  sirocco             60.6%   -2.9%   - · STR 5 · Battlecry: return all enemy units adjacent to this to their owner's hand.
⚪  cheetah             60.2%   -3.2%   Cat · STR 5 · Battlecry: if you play this next to the opponent's base, draw 1 card.
🔵  chameleon           59.1%   -4.3%   Lizard · STR dynamic · May be placed on any unit, and any unit may be placed on top of it.
🟡  gale                58.8%   -4.6%   Bird · STR 6 · Flight. The first time an enemy unit covers this, return that enemy unit to its owner's hand.
🔵  skunk               58.7%   -4.7%   - · STR 4 · Return an adjacent enemy to your opponent's hand. They can't play it next turn.
```

### ramp (deck win rate 55.0%)
```
   card             WR_drawn  impact   tag / str / text
🟡  methuselah          66.0%  +10.9%   Megafauna · STR 5 · Immovable. At the end of your turn, gain 5 food.
🔵  rhinoceros          58.4%   +3.4%   Megafauna · STR 6 · Battlecry: remove all adjacent enemies of strength 3 or less.
🔵  polar_bear          58.0%   +3.0%   Bear · STR 8 · Apex Predator.
🔵  hippopotamus        58.0%   +3.0%   Megafauna · STR 6 · When an enemy unit is placed on an adjacent crossroad, remove it if its strength is 3 or less.
⚪  grizzly_bear        57.8%   +2.8%   Bear · STR 6 · Battlecry: in 2 turns, remove a random adjacent enemy.
⚪  black_bear          57.2%   +2.2%   Bear · STR 5 · Battlecry: in 2 turns, draw 1 card.
🔵  andean_condor       57.1%   +2.1%   Bird · STR 4 · Flight. Reveal top card of both decks. If yours has higher strength, draw it.
🟡  bulwark             57.1%   +2.1%   Megafauna · STR 10 · Immovable. Costs 20 food. Battlecry: remove all adjacent units.
🟡  borealis            56.5%   +1.5%   Bear · STR 10 · Apex Predator. Costs 20 food.
⚪  elephant            55.8%   +0.8%   Megafauna · STR 8 · Immovable. Costs 20 food.
⚪  fig_tree            55.3%   +0.3%   - · STR 0 · Fragile. At the start of next turn, gain 20 food.
⚪  watering_hole       54.8%   -0.2%   - · STR 0 · Fragile. At the start of next turn, draw a unit with strength 6 or more.
🟡  aquila              53.0%   -2.0%   Bird · STR 8 · Flight. Apex Predator. Costs 20 food.
⚪  oxpecker            52.9%   -2.1%   Bird · STR 1 · Flight. Gain 1 food for each unit in your starting deck with strength 6 or more.
```

### egg_control (deck win rate 45.6%)
```
   card             WR_drawn  impact   tag / str / text
🟡  eon                 51.7%   +6.2%   Snake · STR 7 · Whenever a card is drawn, shuffled or removed, gain 1 food.
🟡  ember               50.3%   +4.8%   Bird · STR 6 · Flight. When this is removed, shuffle it back to your deck.
🟡  black_swan          50.2%   +4.7%   Bird · STR 3 · The first time each turn you draw Black Swan, your opponent removes a random card from their hand.
🔵  stoop               49.1%   +3.6%   Bird · STR 4 · Flight. Battlecry: remove an adjacent enemy of strength 4 or less.
⚪  raven               48.0%   +2.4%   Bird · STR 2 · Flight. Battlecry: draw 3 cards, then shuffle 2 cards back.
⚪  owl                 47.2%   +1.7%   Bird · STR 2 · Flight. Battlecry: look at the top 3 cards; draw 1 and shuffle the rest.
⚪  anaconda            46.9%   +1.3%   Snake · STR 7 · Apex Predator.
⚪  eagle               46.7%   +1.2%   Bird · STR 5 · Flight.
🟡  aurum               46.3%   +0.8%   Egg · STR 0 · Fragile. At the start of your turn, draw a card.
🔵  goliath             46.2%   +0.7%   Snake · STR dynamic · This unit's strength is equal to the number of removed units.
🔵  rattlesnake         45.8%   +0.2%   Snake · STR 0 · Whenever you shuffle a card, gain 1 strength (wherever this is).
⚪  bird_egg            44.9%   -0.7%   Egg · STR 0 · Fragile. After 2 turns, remove this and draw 2 Birds.
🔵  egg_eater           44.8%   -0.7%   Snake · STR 4 · Whenever an Egg is removed, gain 10 food.
⚪  snake_egg           44.7%   -0.8%   Egg · STR 0 · Fragile. After 2 turns, remove this and draw 2 Snakes.
```

### colony_food_swarm (deck win rate 44.1%)
```
   card             WR_drawn  impact   tag / str / text
🔵  termite_king        49.0%   +4.9%   Colony · STR 5 · Battlecry: if you control a Colony Queen, draw 1 card.
🟡  vesper              48.9%   +4.8%   Colony · STR 0 · Flight. Has +2 strength for each other friendly Colony unit.
🔵  termite_queen       48.3%   +4.2%   Colony/Queen · STR 3 · Battlecry: you may play one additional non-Queen Colony unit this turn.
🟡  queen_honoria       48.3%   +4.2%   Colony/Queen · STR 4 · Whenever you play a Colony unit, gain 4 food.
🔵  nurse_bee           46.9%   +2.9%   Colony · STR 2 · Flight. Battlecry: if you control two copies of the same Colony unit, draw 2 cards.
🟡  falstaff            46.0%   +1.9%   Colony · STR 3 · Flight. Whenever you gain food, gain 3 additional food.
⚪  worker_wasp         45.6%   +1.5%   Colony/Worker · STR 3 · Flight. At the end of your turn, gain 3 food.
🔵  nurse_bumblebee     45.0%   +0.9%   Colony · STR 3 · Flight. Battlecry: if you control 5 or more Colony units, draw 2 cards.
⚪  queen_bee           44.9%   +0.8%   Colony/Queen · STR 2 · Battlecry: play a Worker unit.
⚪  worker_bee          44.6%   +0.5%   Colony/Worker · STR 1 · Flight. Battlecry: gain 10 food; if you control another Worker, gain 10 more.
⚪  soldier_ant         44.2%   +0.1%   Colony · STR 2 · Battlecry: if you control 5 or more Colony units, remove an adjacent enemy.
⚪  guard_hornet        44.1%   +0.0%   Colony · STR 3 · Flight. Has +5 strength while you control 5 or more Colony units.
🟡  queen_marabunta     44.0%   -0.0%   Colony/Queen · STR 4 · Battlecry: gain 4 food for each other friendly Colony unit.
⚪  worker_ant          42.6%   -1.4%   Colony/Worker · STR 1 · Battlecry: gain 12 food.
```

### food_otk (deck win rate 40.3%)
```
   card             WR_drawn  impact   tag / str / text
🟡  rat_king            46.4%   +6.0%   Rodent · STR 4 · Battlecry: gain 4 food for each other Rodent you control. Draw 1 card.
⚪  chipmunk            45.2%   +4.9%   Rodent · STR 1 · Battlecry: gain 10 food. At the start of next turn, gain 10 more.
🟡  greywhisker         44.9%   +4.5%   Rodent · STR 1 · Battlecry: gain 1 food. Draw 1 card. You may play 1 more unit.
🔵  porcupine           44.5%   +4.2%   Rodent · STR 7 · Cannot be covered by enemy units.
⚪  muskrat             41.3%   +1.0%   Rodent · STR 2 · Battlecry: if you gained 10 or more food this turn, remove an adjacent enemy unit.
⚪  hamster             40.9%   +0.5%   Rodent · STR 3 · Battlecry: if you gained 10 or more food this turn, draw 2 cards.
🟡  fathom              40.4%   +0.1%   - · STR 4 · Battlecry: draw a legendary unit.
⚪  squirrel            40.1%   -0.3%   Rodent · STR 3 · Battlecry: gain 10 food.
🔵  armadillo           38.7%   -1.7%   - · STR 5 · Immovable. Adjacent friendly units can't be chosen by enemy abilities.
🔵  flying_squirrel     38.0%   -2.3%   Rodent · STR 4 · Flight. Battlecry: gain 8 food.
⚪  groundhog           37.5%   -2.9%   Rodent · STR 4 · Battlecry: if you gained 10 or more food this turn, gain +5 strength.
🟡  scrooge             37.4%   -2.9%   Rodent · STR 4 · Battlecry: gain food equal to the food you gained this turn.
⚪  hedgehog            37.1%   -3.2%   - · STR 4 · Immovable. Battlecry: gain 5 food.
🔵  chinchilla          36.1%   -4.2%   Rodent · STR 3 · Battlecry: next turn, take 1 additional action.
```

### canine_buff_tempo (deck win rate 33.3%)
```
   card             WR_drawn  impact   tag / str / text
🟡  raksha              38.2%   +4.8%   Canine · STR 5 · Your other Canines have +1 strength.
🟡  clarion             37.6%   +4.3%   Canine · STR 4 · Battlecry: give +1 strength to all other Canines in your hand and battlefield.
🟡  shuck               37.4%   +4.1%   Canine · STR 6 · Battlecry: return a removed Canine to your hand. Give it +2 strength.
🔵  red_wolf            36.3%   +2.9%   Canine · STR 5 · Battlecry: give +1 strength to all Canines in your hand.
⚪  dingo               35.9%   +2.6%   Canine · STR 5 · At the end of your turn, give a friendly adjacent Canine +1 strength.
⚪  fox                 35.7%   +2.4%   Canine · STR 3 · Whenever this gains strength, draw a card (once per turn).
⚪  gray_wolf           35.3%   +2.0%   Canine · STR 4 · Battlecry: remove an adjacent enemy with less or equal strength.
🟡  lobo                34.8%   +1.4%   Canine · STR 4 · Has +2 strength for each other Canine you control.
🔵  bush_dog            33.9%   +0.5%   Canine · STR 3 · Once a turn, when this gains strength, give all friendly adjacent Canines +1 strength.
⚪  african_wild_dog    33.8%   +0.4%   Canine · STR 2 · Has +1 strength for each friendly Canine.
⚪  dog                 33.7%   +0.4%   Canine · STR 1 · Battlecry: if you control another Canine, play another Canine from your hand (other than Dog).
🔵  jackal              32.8%   -0.5%   Canine · STR 5 · Whenever an adjacent unit is removed, gain 5 food.
🔵  dhole               32.3%   -1.0%   Canine · STR 3 · Battlecry: give all adjacent Canines +3 strength.
⚪  coyote              31.1%   -2.3%   Canine · STR 3 · Battlecry: if this has 5 or more strength, draw a card.
```
xx@M1 animal-kingdom-game % 