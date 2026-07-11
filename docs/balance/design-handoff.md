# Handoff prompt — game-design strategy session

_Copy the block below into a fresh session. It is written to that agent. It deliberately contains
**no proposed solutions** — only the problem, the evidence, and the goal — so the design thinking
starts unbiased._

---

You are a **game-design strategist**. I need you to reason about a fundamental design problem in my
2-player tactical card game *Animal Kingdom*, **entirely at the conceptual level**. Do **not** propose
specific card changes, numbers, or tuning — I want the discussion to stay on fundamental design
principles. Work from first principles; do not pattern-match onto Magic/Hearthstone (this game has
none of their systems — see the mechanics below).

## The game (mechanics)

Two players place animal **units** onto a **graph of crossroads**. A turn is **2 actions**; each
action is either **draw 1 card** or **place 1 unit**. You win by **capturing the enemy HQ** (place
any unit on it) or by hitting a **food threshold** (control board regions → they generate food each
turn). A unit has **one stat: strength (1–10)** plus an optional effect. To place onto an enemy unit
you need **strictly greater strength** ("covering"); placement is otherwise gated by **connection**
back to your HQ through crossroads you occupy.

Critically: **there is no mana, no attack/health, no combat damage.** Strength is a *free* stat and
an effect is a *free rider* on top of it — there is **no cost/stat tradeoff**. The **only resource is
the action** (2 per turn). The game is a **deckbuilding game**: players build a 30-card deck from an
open pool of ~100 cards (currently shipped as 7 pre-made themed decks, but open construction is the
intent).

## The problem

There is a **dominant strategy**: a deck assembled from the individually-strongest cards across all
themes (a "good-stuff" pile) beats everything, and nothing beats it. The intended variety of viable,
distinct decks collapses into one best pile. Part of this is because the pre-made decks are not optimized,
and they each have some "dead" cards. But we have a suspicion that this is more of a fundamental issue,
give the game format is "create deck from ALL available cards", and all cards have equal "cost".

## The evidence (measured, via bot-vs-bot simulation + human play)

- A deck built from the strongest cards across all themes beats **every** pre-made deck by huge
  margins (~85–90% under our strongest AI), and a top human player **could not beat it** while
  piloting the themed decks.
- An automated search for a **counter** to that pile **found none**: when you repeatedly build the
  best-possible deck against the current field, it keeps producing *more of the same* pile. The
  metagame converges to a **monoculture**, not a rock-paper-scissors mix.
- The dominance is **not** caused by a handful of over-tuned cards. After removing the pile's cards
  from the pool entirely, the *leftover* cards still build a **winning** deck. The pool contains
  **many** individually-strong cards, not a few.
- The strongest, most-picked cards share a pattern: they generate **extra actions / extra
  placements** (the game's only resource), or they are efficient stand-alone bodies/removal that are
  good in **any** deck with no set-up.
- By contrast, the themed decks rely on cards that are **weak on their own** and only pay off in
  combination — and in practice those cards are frequently **dead draws**.
- Structural note (fact, not a proposed fix): the game currently imposes **no constraint on which
  cards may be combined** in a deck, and **no cost to play a card** beyond spending one of your two
  actions.

## The goal

Design, at a **fundamental/conceptual level**, what would turn this into the game I actually want:

- A **small set of distinct decks / archetypes** that are **roughly equal in power** and relate to
  each other in a **rock-paper-scissors** way (each has good and bad matchups), so a player can
  **choose the deck that fits their playstyle**.
- **Pilot skill should matter more than deck choice at the margin** — a strong player on a slightly
  weaker deck should be able to beat a weaker player on a stronger deck.
- The current "good-stuff" pile is **allowed to remain as one archetype** (it is essentially a
  generalist midrange deck). The goal is **not** to delete it — it is to give it **predators** and
  bring the other archetypes up to parity, so it is one option among several.

## Hard constraints (these are off-brief — do not propose them)

- **No mana / no per-card resource cost.** (A design pillar; and the obvious in-game resource, food,
  is earned by being ahead, so pricing cards in it would just reward the leader.)
- **No colors/classes** in the Magic/Hearthstone sense (a hard rule restricting which cards a deck
  may contain). Rejected as importing another game wholesale, doesn't fit the Animal Kingdom theme.
- **It remains an open-construction deckbuilding game** — not a fixed-roster "pick a character" game,
  and not a shared-pool / drafting game. (Those were considered and set aside as not fitting the
  theme.)
- **Acceptable but not required:** incentives that *reward* committing to a theme without a hard rule
  (the pool already has tribal tags like Cat / Canine / Colony-insects / Rodent / Bird / Snake).

## Your task

Start by reading `docs/rules/mental-model.md` (it exists to prevent Magic/Hearthstone
pattern-matching, the most common mistake here). Then, at the conceptual level only:

1. What is the **fundamental nature** of this problem — why does the dominant pile exist, given the
   mechanics and constraints above?
2. What **fundamental design principle(s)** could produce the goal (distinct, roughly-equal,
   RPS-related decks with a high skill ceiling) **within** the hard constraints?

Keep it conceptual. I am explicitly **not** looking for card lists or number tweaks — I want to get
the underlying design philosophy right first. A simulation harness exists to test any principle we
land on later.

---

_A detailed record of the prior investigation (with that session's exploration and opinions) exists
at `docs/balance/goodstuff-investigation.md` — but reason your own way to a view first before reading
it, so it doesn't anchor you._
