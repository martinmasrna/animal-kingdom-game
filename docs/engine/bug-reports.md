- [x] **Flying Squirrel text/const desync (fixed 2026-07-09).** Card text said "gain 10 food" but
  `config.flying_squirrel_food` was `8` (stale since commit 3129eca, Decision H). Shorted the
  food_otk combo: greywhisker(1)+squirrel(8)=9 < `fed_threshold` 10, so Groundhog/Hamster/Muskrat
  fizzled one food short despite the card promising enough. Synced constant to 10 to match text.
  Caught in human recording `human_v_referee_s6_food_otk-721d1a190e5c…jsonl` (turn 1). Paired 200g
  eval: food_otk 51.5%→53.0% (weak-pilot ./report), in-band, modest buff — helps an already
  slightly-weak deck (~38% strong-pilot). 352 tests green.

- [ ] Prince leo/princess Lea -- remove the "you may" and have it play automatically (but you choose target, not randomly)
  - waaait ... don't tell me it counts as two actions right now?

- [ ] Go over this replay: file:///Users/xx/%5B02%5D%20Coding/animal-kingdom-game/results/human_games/ad-hoc/ad-hoc_20260704T151801.744706Z_f2ea1077.jsonl
    -  Pufferfish vs. Tiger didn't seem to work there
    - pretty sure Porcupine didn't work preperly either, might be wrong tho

- [ ] chameleon on Porcupine works, but shouldn't (at least I think)
- [ ] Dingo RNG is broken, always selecting the same one
- [ ] Jaguar worked on strenght 5 minion???