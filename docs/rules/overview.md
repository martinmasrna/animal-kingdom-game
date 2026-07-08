# 1. Document Scope
This document describes a proposed fast-paced strategy game set in a theme of Animal Kingdom.
---

# 2. Game Overview
- competitive tactical board game for two players.
- theme: Animal Kingdom
- Players deploy unit (themed as various animals) onto a connected graph of vertices.
- Units expand the player's territory, capture enemy positions, surround regions with food, and create paths toward the enemy headquarters.

A player wins immediately by either:
(a) placing a unit on an enemy headquarters; or
(b) collecting the required number of food

The game can also end through exhaustion if a player can neither draw nor place a unit.

---

# 3. Important Terms

## 3.1 Unit
Each unit has:
- a name;
- a strength from `1` to `10`;
- an optional effect.

## 3.2 Map
A map is board on which the game is played. It contains:
- each player's headquarters
- crossroads (vertices in a graph), on which units may be placed
- paths connecting vertices and headquarters;
- closed regions with food;

## 3.3 Path
A path is a printed connection between two crossroads. Paths determine:
- whether crossroads are adjacent;
- whether a crossroad is connected to a player's headquarters;
- whether a unit can legally be placed.

## 3.4 Region
A region is a closed area surrounded by paths and crossroads. A player controls a region when they occupy every crossroad surrounding it.

## 3.5 Hand
'Hand' stands for available units of each player. A hand can contain no more than eight units.

## 3.6 Deck
Player's face-down cards, pile he draws from.

## 3.7 Remove Pile
The Remove Pile is one shared, visible area for cards removed from hands, decks, or the map (there is no separate discard pile). Unless an effect states otherwise, cards in the Remove Pile do not return to the game. Sending any card here is a **remove** (fires remove triggers); a *unit leaving the board* is the narrower case that also fires **Deathrattle**. See `keywords.md` for the two trigger tiers.

# 4. Game Setup

Performed once, before the first turn.

## 4.1 Starting board
Both players start with an **empty board** — no units pre-placed, and both headquarters unoccupied.

## 4.2 First player
One player is chosen to go first (by coin flip, until a better method is decided).

## 4.3 Opening hands
The **first player** draws **3** cards; the **second player** draws **4** cards. The extra card compensates the second player for the turn-order disadvantage of a place-or-draw game. Whether 3/4 is the right split is a tuning question — measure the first-player win rate before changing it.

---

# 5. Turn Structure
Players alternate turns. On a turn, the active player performs **two actions**; each action is one of:

1. **Draw 1 card**
2. **Place one unit**

The turn ends after two actions, or earlier if no legal action remains. Some troop effects can allow additional placements or draws during the same turn (these are free — they do not consume an action). When taking the place action:

1. Choose one unit from the rack.
2. Choose a legal placement.
3. Place the unit.
4. Resolve the unit's effect, if applicable.
5. Check whether any regions have become controlled.
6. Check all victory conditions.

The placed unit immediately becomes the visible unit occupying that location.

---

# 6. Legal Placement
A unit may be placed on:

- an empty crossroad;
- a crossroad occupied by one of the active player's troops;
- a crossroad occupied by an enemy unit with strictly lower strength;
- an enemy headquarters.

The crossroad must be connected to the player's headquarters if he wants to place a unit there. Certain troop or map effects can modify these requirements.

A player **cannot place a unit on their own headquarters** — it is not in the list above. A player defends their HQ only by occupying the crossroads **in front of it** (the crossroads the HQ connects to). An enemy headquarters *is* a legal target: placing a unit onto it captures it (§11.1), provided it is connected to the active player through their occupied crossroads.

---

# 7. Strength and Covering
When placing onto an enemy-occupied base, the newly placed unit must normally have strictly greater strength than the visible enemy troop. For example:

- strength `5` may cover strength `4`;
- strength `5` may not cover strength `5`;
- strength `4` may not cover strength `5`.

Placing on top of one's own unit does not require greater strength.

## 7.1 Stacks
When a unit is placed on an occupied base, it is added to the top of the existing stack. There is no stack-height limit. Only the topmost visible unit:

- occupies the crossroad;
- contributes to connection;
- can normally be selected by effects;
- determines the crossroad's current owner.

When a visible unit is removed, the unit underneath becomes visible and immediately determines control of the crossroad.

---

# 8. Connection to Headquarters

A unit must normally be placed on a location connected to the active player's headquarters. A location is connected when a continuous path can be traced:

1. starting from the player's headquarters;
2. following printed paths;
3. passing only through crossroads currently occupied by that player;
4. ending at the destination.

---

# 9. Unit Effects

Unless stated otherwise, a units's effect is resolved after it is placed. Effects can cause additional actions, including:

- drawing units;
- placing an additional unit;
- removing units from a hand or deck;
- ignoring connection;
- removing visible units.

---

# 10. Controlling Regions and Gaining Food

A player takes control of a region immediately upon occupying every crossroad surrounding it. Each region generates specified amount of food. At the end of each player's turn, they produce food in all of the regions they control. Collected food is added to that player's food store. If the total amount of food crosses specified threshold, that player wins the game.

---

# 11. Victory Conditions

## 11.1 Capturing an Enemy Headquarters
If a player places one of their troops on an enemy headquarters, that player wins immediately.
If a map gives one player multiple headquarters, capturing any single enemy headquarters is sufficient.

## 11.2 Reaching the Food Objective
If a player obtains at least certain amount of food (specified by the map), the player wins immediately.

## 11.3 Exhaustion
The game also ends when the active player can perform neither standard action:
- they cannot legally draw; and
- they cannot legally place any unit from their rack.

When this happens:
1. compare collected food;
2. the player with more food wins;
3. if tied, the player whose inability to act ended the game loses.


# 12. Deck-Building Premise

For 0.0.1 the game ships a set of **premade decks**, each with a distinct identity, game plan, and win condition. (A personalized construction format may follow; the deck rules in §13 are the legality ruleset either way.) The premise delivers:

- distinct archetype identity;
- matchup differences (a rock-paper-scissors metagame);
- increased replayability;
- a generalist constraint — one deck that must hold up across the match's three different maps (§14), since there is no per-map reconfiguration.

Decklists are **open**: both players see each other's full list at the start of the match.

---

# 13. Deck Rules

Each deck contains exactly **30 cards** and must satisfy all of the following:

- no more than 3 copies of any common unit;
- no more than 2 copies of any rare unit;
- no more than 1 copy of any legendary unit;
- no more than 8 rare cards in total;
- no more than 4 legendary cards in total (so at least 18 commons).

In practice every deck is built to the clean **4–4–6** shape: 4 legendary designs (×1), 4 rare designs (×2), and 6 common designs (×3) = 30 cards. This is the lowest-legendary split that still keeps a healthy rarity pyramid — more common designs than rare, commons the plurality of cards — which is why decks don't run fewer legendaries even though the rules permit it.

# 14. Match Structure

A competitive match is played as a best-of-3 series. Both players use the **same 30-card deck** for the whole match — there is no per-map reconfiguration. Decklists are **open**, revealed to both players at the start of the match.

Before the match begins, three maps are revealed — the maps for the 3 possible games of the series. The sequence is known in advance. For example:

- Game 1 uses Map A.
- Game 2 uses Map B.
- Game 3, if required, uses Map C.

Knowing all three maps and the opponent's list up front, each player commits to a single deck that must perform across every battlefield.