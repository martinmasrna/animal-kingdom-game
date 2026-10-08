---
name: deck-design
description: >-
  Design or finish a launch deck's cards with Martin: frame the archetype, play imagined games on the real map, propose cards for the open slots, pick animals, record the result. Use when Martin shares a deck sheet (a screenshot of a deck's cards), says "let's do the usual procedure / usual analysis", asks to design a deck, fill a deck's open slots, find an animal for an effect, or propose a legendary. Not for balance measurement (that's balance-eval).
---

# Deck design

Martin brings a sheet: a deck's 30 cards as 4 legendaries (1 copy), 4 rares (2 copies), 6 commons (3 copies), some filled, some open. The work is to understand the deck, find what it lacks, and propose cards and animals he'll lock. Read `docs/rules/mental-model.md`, `docs/design/principles.md` (power anchors, the checks before proposing a card, naming rules) and the deck's section in `docs/design/effects-pass.md` first. Every card you propose passes the principles' checks before he sees it; this skill adds the ones that kept failing.

## 1. The framing round ("the usual")

Answer from first principles, briefly, in this order:

- The closest equivalents in Hearthstone, Magic and Gwent, and which one fits best.
- The deck's identity in one line: how it wins and what every card is for.
- What makes it fun to play (the decision each turn, the big moment) and the feeling it should give.
- Why a player picks it over every other deck.
- Its meta role: what it beats, what beats it, and what it forces other decks to carry. Name the counterplay it must keep (an aggro deck stays fragile, a combo deck stays answerable).
- What the sheet already shows: gaps, cards that break an anchor, notes Martin left on the sheet.

## 2. Imagined games

Two or three games, turn by turn, against decks of different shapes (an aggro, a midrange, a control). Play them on map_b's real geometry (`animal_kingdom/data/maps.json`): a 5×3 orthogonal grid, dens behind columns 1 and 5, regions are 2×2 squares (flanks 10 food, centre 15), food is paid at the end of the owner's turn, win at 100, two actions a turn, first player draws 3. Count the turn each side reaches 100 or the den. Opponents race on their own regions even when they can't touch yours; check for games where neither side interacts.

Write the games as reasoning, then the findings: what works as intended, what doesn't, and what the deck lacks. Games imagined are not evidence; say so in the doc.

## 3. Proposing cards

The failures this procedure exists to stop, each a real miss:

- **The default play.** Compare the card with simply placing the card it consumes, or pressing Draw (2 cards for one action). Drawing one card is tempo, not value. A card that replaces itself is not card draw. Discarding a big animal to remove a smaller one is worse than covering with it.
- **The real grid.** A crossroad has at most 4 neighbours (corners 2). Count them before stating any "for each adjacent" payoff.
- **Answerable without losing a card every time.** "Protect it and it wins" is a control card; at home behind walls it may be unreachable. Static auras that make every corner uncoverable are unbreakable walls.
- **Timing.** Food or cards arriving after the game is decided count for nothing; ask when the deck needs the resource.
- **Legendaries amplify the plan, they don't replace it** (Theron and Adira in Cats). One clear, unique idea worth a legendary, good in other decks too, a strong fit here. Never another win condition, never a reprint of an existing card, never a plain card-draw or +1 anthem.
- **Power ladders climb evenly.** A card with stages (the Butterfly) adds one thing or one number per stage; no single giant jump at the end.
- **No loops.** "Whenever one gains, the other gains" loops forever; share one number instead.
- **Card text fits three lines.** Clunky conditions (three keywords and a count) are the wrong card, not a wording problem.
- **Don't flip-flop.** When Martin corrects one point, fix that point; don't rebuild the rest to defend the earlier answer.

Give a recommendation, not a menu. For a legendary, three to five proposals are fine when Martin asks for them.

## 4. Animals

- The effect is the animal's most famous trait as a normal person knows it, and the animal is the first one the effect brings to mind.
- A legendary needs its species on a common or rare in the pool. Metamorphosis and Colony castes are the only species exceptions.
- Rarity is the card's role, but the most special effects go on the most special animals; an ordinary animal on a premium effect reads wrong.
- Strength follows real size for commons and rares; when size forces a small body, give a stronger effect.
- Tags follow what players believe (a Meerkat, Mole or Hare is a Rodent; a Hyena is no Canine).
- No pets, no farm animals. Check the habitat rosters (`docs/design/habitats.md`) and the existing pool (`cards.json`, `effects-pass.md`) before naming an animal: most launch rodents, birds and fish are already taken.
- Give the Slovak name for an animal Martin may not know.

## 5. Recording

After each decision, write the deck's section in `docs/design/effects-pass.md` (framing, the table, rejected ideas with reasons) and commit it by explicit path. Banked ideas for other decks go under "Elsewhere, settled in passing". Roster changes (animals added to a habitat) are listed for the roster pass, not edited into `habitats.md` mid-deck.

End each turn on the recommendation, never a closing question.
