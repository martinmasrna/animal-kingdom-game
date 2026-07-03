# 1. Document Scope

This document describes the **maps** for the **0.0.1** version of the game, plus the shared setup rules and the map-data format used to encode them. It is a companion to `overview.md` (rules) and `cards.md` (card pool).

A map is the board a single game is played on. A competitive match is a best-of-3 over three maps revealed in advance (`overview.md` §15).

---

# 2. Map Format (conventions)

Every map is a graph plus a food layout. Maps are encoded with these fields:

| Field | Meaning |
|---|---|
| **crossroads** | The vertices units may be placed on. Named `(col,row)`. |
| **edges (paths)** | Printed connections between two crossroads, or between a crossroad and an HQ. Determine adjacency and connection-to-HQ. |
| **hqs** | One per player. Each HQ lists the crossroads it connects to (its "front"). An HQ is **not** a crossroad — no unit is ever placed there by its owner (see §3). |
| **regions** | Closed cells. Each lists its bounding **corners** (crossroads) and its **food** output per turn. A player controls a region when they occupy *all* its corners. |
| **win_food** | Food total that wins the game on this map (`overview.md` §11.2). |

All food numbers (region output, `win_food`, and the card `F` values in `cards.md`) live on **one shared scale** and are tuned together. The numbers below are deliberate round **placeholders** — the simulator's first job is to tune them.

---

# 3. Setup Rules

Game-wide setup and HQ rules are the source of truth in `overview.md` — **§4 (Game Setup)** and **§6 (Legal Placement)**. As they apply to every map:

- **Empty board** start; both HQs unoccupied. *(`overview.md` §4.1)*
- **First player** draws **3** cards, **second player** draws **4**. *(`overview.md` §4.3; first-player determination still open — see §6)*
- A player **cannot place on their own HQ**; they defend it by holding the crossroads **in front of it** (the crossroads the HQ connects to). *(`overview.md` §6)*

**Capturing an enemy HQ** *(`overview.md` §11.1)*: the attacker places a unit onto the enemy HQ once it is connected to the attacker's own HQ through attacker-occupied crossroads — in practice, hold a front crossroad of the enemy HQ with a connected chain back home, then place onto the HQ to win. The defender's counterplay is to hold their own front crossroads with bodies strong enough not to be covered.

---

# 4. Map B — "Savanna Expanse" (the game map)

**This is the shipped map** — every game and sim runs on it. A 5×3 lattice of **15 crossroads**
(columns 1–5, rows 1–3), HQ_A fronting column 1 and HQ_B fronting column 5, with **8 regions**
(R1–R8; the four center cells R2/R3/R6/R7 output **20** food, the flanks **10**) and **win_food 100**.
The exact geometry (crossroads, edges, region corners) is canonical in
[`animal_kingdom/data/maps.json`](../../animal_kingdom/data/maps.json) — that file is the source of
truth; this section is the prose companion. The extra column over the old 4×3 map gives combo/food
decks room to develop and opens a genuine row-1/row-3 flank as an HQ-rush lane.

---

# 4L. Map A — "Savanna Crossing" (retired — test fixture only)

> **Legacy.** Map A is **not a playable ruleset** — it is retained in `maps.json` solely as a small,
> symmetric geometry fixture for engine unit tests. It is never a game or sim default. The section
> below is kept for those tests' reference only.

A 4×3 lattice of crossroads, HQs on opposite sides, square cells forming 6 regions.

```
        (1,3)──────(2,3)──────(3,3)──────(4,3)
         │   R4:10   │   R5:20   │   R6:10   │
[HQ_A]──(1,2)──────(2,2)──────(3,2)──────(4,2)──[HQ_B]
         │   R1:10   │   R2:20   │   R3:10   │
        (1,1)──────(2,1)──────(3,1)──────(4,1)
```

## 4.1 Topology
- **12 crossroads**, named `(col,row)`, columns 1–4 (left→right), rows 1–3 (bottom→top).
- **Paths:** the full orthogonal grid (each crossroad connects to its horizontal and vertical neighbors; no diagonals), plus each HQ's front edges. Totals: 9 horizontal + 8 vertical + 6 HQ = **23 paths**.
- **HQ_A** connects to all of column 1 — `(1,1) (1,2) (1,3)`. **HQ_B** connects to all of column 4 — `(4,1) (4,2) (4,3)`. (The diagram draws only the middle spine for readability.) The 3-wide base edge avoids a spawn chokepoint that would cause stalls.

## 4.2 Regions and food
| Region | Corners | Food/turn |
|---|---|---:|
| R1 | (1,1) (2,1) (1,2) (2,2) | 10 |
| R2 | (2,1) (3,1) (2,2) (3,2) | **20** |
| R3 | (3,1) (4,1) (3,2) (4,2) | 10 |
| R4 | (1,2) (2,2) (1,3) (2,3) | 10 |
| R5 | (2,2) (3,2) (2,3) (3,3) | **20** |
| R6 | (3,2) (4,2) (3,3) (4,3) | 10 |

**win_food: 100.**

## 4.3 Structured data
```yaml
name: Savanna Crossing
crossroads: [ (1,1),(2,1),(3,1),(4,1),
              (1,2),(2,2),(3,2),(4,2),
              (1,3),(2,3),(3,3),(4,3) ]
hqs:
  A: { connects: [ (1,1),(1,2),(1,3) ] }
  B: { connects: [ (4,1),(4,2),(4,3) ] }
edges: all orthogonal neighbor pairs + each hq's connects
regions:
  R1: { corners: [ (1,1),(2,1),(1,2),(2,2) ], food: 10 }
  R2: { corners: [ (2,1),(3,1),(2,2),(3,2) ], food: 20 }
  R3: { corners: [ (3,1),(4,1),(3,2),(4,2) ], food: 10 }
  R4: { corners: [ (1,2),(2,2),(1,3),(2,3) ], food: 10 }
  R5: { corners: [ (2,2),(3,2),(2,3),(3,3) ], food: 20 }
  R6: { corners: [ (3,2),(4,2),(3,3),(4,3) ], food: 10 }
win_food: 100
```

## 4.4 Design notes — why this shape
- **All three win conditions are live.** *HQ rush:* build a connected chain across the middle to a column-4 crossroad, then place onto `HQ_B` — long enough to cost real tempo (tests Aggro). *Food win:* the center rewards holding + removal; both centers together require 6 specific crossroads `(2,1)(3,1)(2,2)(3,2)(2,3)(3,3)` held under fire — a real achievement, not a freebie. *Exhaustion:* reachable in grindy mirrors.
- **Contested center.** Higher food in the middle pulls both players into the same squares, so removal, covering, and positioning all matter there — the interactions worth stress-testing.
- **Shared corners create economy.** Adjacent regions share crossroads, so holding two regions overlaps; board states get interesting without the map being large.
- **Symmetric**, so the only built-in imbalance is turn order — the thing to *measure*, not bury under map asymmetry.
- **HQ defense uses the front crossroads** (§3): a fat body on a column-4 crossroad is the wall, which is exactly why Matriarch Elephant (Str 8, Immovable) is the premier HQ defender and why Aggro needs Nile Crocodile to out-muscle it.

---

# 5. Tuning targets (Map B)
- **Food curve:** region outputs (10 / 20) and `win_food` (100) vs. the card `F` scale — set together in the simulator.
- **First-player win rate:** target ≈ 50% with the 3/4 opening-hand split; adjust the split or add another lever if skewed.
- **Win-condition split:** healthy if all three (HQ / food / exhaustion) appear; if exhaustion dominates, the map is too stally or decks too removal-heavy.

---

# 6. Open questions / parking
- **First-player determination** — coin flip for now; revisit (e.g. a bid system) if it matters competitively.
- **Setup rules now live in `overview.md`** — §4 (Game Setup) and §6 (Legal Placement) are the source of truth; §3 here just references them.
- **More maps** — a Map C (asymmetric or food-skewed) for the best-of-3, to complement the current Map B.
