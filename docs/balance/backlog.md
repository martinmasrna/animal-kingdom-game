# Balance — Backlog

Open items only. Top-3 summary in [`../STATUS.md`](../STATUS.md). Two targets: every **deck** in **40–60%** winrate; every **card impact** within **±10%**. Roadmap: `simulation-platform-roadmap.md`. All conclusions **gated on trustworthy pilots (→ Bots)**.

- [ ] **Apply and re-test the locked card review:** [`card-balance-todo.md`](card-balance-todo.md)
  records the Cat trims, Aggro/Egg rarity moves, new Aggro designs, reviewed non-changes, and the
  deliberately short post-change watch list.
- [ ] **Deck equality → pull every deck into 40–60%.** Current Greedy-Bot outliers from the
  200-game full matrix: cats_midrange ~75% at the top; colony_food_swarm ~30%, food_otk ~34%,
  and egg_control ~38% at the bottom. Colony's lack of a favorable matchup is the strongest weak-deck
  signal; Food OTK is especially pilot-sensitive and should not be tuned from Greedy play alone.
  - **Decision H — re-derive the food economy on one shared scale** (vs `win_food` 100, region 10/20). *In progress:* Methuselah 10→5 and the food_otk one-off floor (Chipmunk 10+10, Squirrel 12, Flying Squirrel 8, Gazelle 40) shipped. **Still open:** the 20-cost bodies (Elephant / Borealis / Aquila / Bulwark) + Fig Tree / Watering Hole Landmarks; Egg Eater 10 / Vulture 5 / Eon 1-per-event; Colony numbers (Marabunta / Honoria / Worker Ant / Worker Bee / Falstaff); Scrooge doubler. Keep every number a placeholder in `engine/config.py`.
  - ⚠ **Watch:** Carmilla sac'ing 3 Gazelles now nets 120 food in one Battlecry (clears `win_food` before Scrooge applies) — check the OTK isn't now too consistent/early.
  - **★ food_otk OTK-realism review — flagged by pilot triage (2026-07-03).** The *entire search ladder* underperforms 1-ply greedy piloting food_otk: TurnBot −9.4% and RefereeBot −9.8% vs greedy (paired, vs greedy opp; artifacts `results/bot_quality/turnbot/` + scratchpad referee run). Search pilots "set up" the fragile Devourer+Gazelle+Keeper OTK and lose the food race; greedy just banks the standalone food-gainers (Squirrel/Chipmunk/Flying Squirrel) and wins — including ~2× as many HQ-capture games (315 vs 163). This is a strong **"is the OTK identity real?"** signal: either (a) the OTK is unrealistic and the deck is a goldfish where myopic racing ≈ optimal → the deck may be mis-designed/overrated, or (b) a shared `TurnSearcher` eval blind spot (→ Bots). **Split (a)/(b):** a human read (can a competent human beat greedy piloting food_otk?), or instrument whether the OTK ever fires (max single-turn food gain vs `win_food`). Until split, food_otk balance numbers stay pilot-suspect and shouldn't drive card changes. Ties into Decision H's OTK-consistency watch above.
  - **Card-design fixes for the confirmed-weak decks:** colony_food_swarm needs a cheap efficient early blocker or a faster engine payoff (loses to cats/canine before it turns on); food_otk may need cheaper protection or a faster kill window.
- [ ] **Card equality → every card impact within ±10%.** Blocked on the `metrics.py impact` fix (→ Engine) and trustworthy pilots (→ Bots).
- [ ] **Watch: cats_midrange vs ramp.** Moved from ramp-favored to even after the keyword split (Snow Leopard now extends to Tiger). "Even" is acceptable; further drift toward cats is not.
- [ ] **Verify still relevant (legacy "Combo" refs).** Queen Bee — keep additive (+F per food gain), watch multi-copy stacking. Hibernating Bear — confirm the 2-turn delay + "lose all food" + Immovable can't be abused. (Both name the retired "Combo" deck; confirm against the current pool.)
