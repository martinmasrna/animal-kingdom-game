# Balance — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Two targets: every **deck** in **40–60%** winrate; every **card impact** within **±10%**. Roadmap: `simulation-platform-roadmap.md`. All conclusions **gated on trustworthy pilots (→ Bots)**.

- [ ] **Deck equality → pull every deck into 40–60%.** Current outliers: colony_food_swarm ~23% (worst; real signal), food_otk overrated by greedy (referee-confirmed).
  - **Decision H — re-derive the food economy on one shared scale** (vs `win_food` 100, region 10/20). *In progress:* Methuselah 10→5 and the food_otk one-off floor (Chipmunk 10+10, Squirrel 12, Flying Squirrel 8, Gazelle 40) shipped. **Still open:** the 20-cost bodies (Elephant / Borealis / Aquila / Bulwark) + Fig Tree / Watering Hole Landmarks; Egg Eater 10 / Vulture 5 / Eon 1-per-event; Colony numbers (Marabunta / Honoria / Worker Ant / Worker Bee / Falstaff); Scrooge doubler. Keep every number a placeholder in `engine/config.py`.
  - ⚠ **Watch:** Carmilla sac'ing 3 Gazelles now nets 120 food in one Battlecry (clears `win_food` before Scrooge applies) — check the OTK isn't now too consistent/early.
  - **Card-design fixes for the confirmed-weak decks:** colony_food_swarm needs a cheap efficient early blocker or a faster engine payoff (loses to cats/canine before it turns on); food_otk may need cheaper protection or a faster kill window.
- [ ] **Card equality → every card impact within ±10%.** Blocked on the `metrics.py impact` fix (→ Engine) and trustworthy pilots (→ Bots).
- [ ] **Watch: cats_midrange vs ramp.** Moved from ramp-favored to even after the keyword split (Snow Leopard now extends to Tiger). "Even" is acceptable; further drift toward cats is not.
- [ ] **Verify still relevant (legacy "Combo" refs).** Queen Bee — keep additive (+F per food gain), watch multi-copy stacking. Hibernating Bear — confirm the 2-turn delay + "lose all food" + Immovable can't be abused. (Both name the retired "Combo" deck; confirm against the current pool.)
