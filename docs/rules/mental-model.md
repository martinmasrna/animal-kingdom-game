# Mental Model — read this before reasoning about cards or balance

**Why this doc exists:** *Animal Kingdom* shares surface vocabulary with Magic/Hearthstone/Slay-the-Spire
("strength", "battlecry", "draw", "remove"), so it is very easy to pattern-match onto their
mana + attack/health + combat-damage systems. **It has none of those.** Almost every recurring
design mistake in this project comes from importing that model. Recalibrate here first.

## The whole system in one breath

Two players place animal **units** onto a **graph of crossroads**. A turn is **2 actions**; each
action is either **draw 1** or **place 1 unit** (some effects grant *free* extra draws/places). You
win instantly by **capturing the enemy HQ** (place any unit on it) or **hitting the food threshold**
(control regions → they generate food each turn). That's the game.

## A unit is a single number

A unit has **one stat: strength (1–10)** and an optional effect. There is **no health/toughness, no
mana cost, no attack value, no summoning sickness**. Strength does exactly three things:

1. **Covering** — to place on top of an *enemy* unit you need **strictly greater** strength (5 covers
   4; 5 cannot cover 5). Placing on your *own* unit needs no strength.
2. **Surviving strength-gated removal** — many removal effects read "remove an enemy of strength ≤ X"
   or "≤ your strength". Higher strength dodges those.
3. **Being a wall** — a big unit is hard to cover, so it holds a crossroad until the opponent finds
   greater strength or an unconditional removal effect.

That's **all** strength does. It is **not** an HP pool and it does **not** help region control.

## How units leave play

Only two ways: **covered** (enemy places strictly-greater strength on top — the covered unit is
**buried in the stack, not discarded**, and resurfaces if the top is removed), or a **removal effect**
deletes it. **There is no chip/ping damage, no combat step, no trading, no debuff-to-death.**

## The board is a graph; placement is gated by *connection*

You may normally only place on a crossroad **connected back to your HQ through a chain of crossroads
you occupy**. This spatial tempo is the heart of the game — it's why "reach" effects (Flight = ignore
connection; Cougar = place adjacent to any of your units ignoring connection) are powerful: they let
you deploy *away from your established territory* instead of grinding a chain forward crossroad by
crossroad. Covering builds **stacks**; only the top unit counts (occupies, connects, is targetable,
owns the crossroad).

## Instinct → reality cheat-sheet

| Your trained instinct (MTG/HS) | Reality in *Animal Kingdom* |
|---|---|
| "STR 2 is fragile / dies to a ping" | No pings exist. A unit is only at risk if the enemy can **cover** it (strength ≥ 3) or has a **removal effect** that catches it. Low strength is not "low health." |
| "mana curve / this costs too much" | **No mana.** The only cost is **actions** (2/turn); a handful of cards also gate on **food**. Free extra placements are the real tempo swing. |
| "removal spell" | There are **no spells** — everything is a **unit placement**. Removal is a unit's *effect*. |
| "go wide to deal more damage / attack face" | **No damage, no face.** Going wide wins by **region control** (occupy every crossroad around a region) and **HQ pathing**. |
| "buff = survives combat" | Buff = strength = can **cover bigger things** + **dodge strength-gated removal**. Nothing to do with an HP bar. |
| "summoning sickness / haste" | None. A placed unit is **immediately active** — it can cover, capture, or trigger the same turn. |
| "tempo = playing on curve" | Tempo = **board presence + connection reach + action efficiency**. |
| "card draw is card advantage" | Drawing **costs an action** (half your turn), so "draw" riders mainly **refund tempo**; running dry risks **exhaustion loss**. |

## Strategic truths that follow (the ones easy to miss)

- **Region control ignores strength.** A STR 1 token holds a region corner exactly as well as a STR
  10. Cheap wide bodies are legitimately strong for the food win — don't dismiss them as "weak".
- **HQ capture ignores strength.** *Any* unit on the enemy HQ wins; the enemy can't sit on their own
  HQ to defend it. So the HQ rush is a **connection/pathing problem, not a strength problem** — reach
  (Flight/Cougar) matters more than big bodies for that line.
- **Covered units aren't dead.** They wait under the stack; recursion/resurface effects and removing
  the coverer bring them back.
- **The unit of resource is the action.** Evaluate a card by what it does *per action* and whether it
  grants free actions — not by an imaginary mana cost.

**Source of truth:** [`overview.md`](overview.md) (rules) and [`keywords.md`](keywords.md) (keywords).
If anything here conflicts with those, they win — and fix this doc.
