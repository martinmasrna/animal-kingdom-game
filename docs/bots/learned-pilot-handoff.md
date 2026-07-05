# Handoff — a learning game-pilot for *Animal Kingdom*

**Audience:** an AI/ML specialist agent. **This document is the *what* and the *why* only.**
The *how* — algorithms, architecture, libraries, code — is deliberately left to you. Nothing
here prescribes a method; treat every mention of an approach as context, not instruction.

---

## 1. Why this matters (the real goal)

We want to produce **trustworthy balance data**: play the game bot-vs-bot thousands
of times to learn whether the seven premade decks are fair. Every balance conclusion is only as
good as the bot piloting it. If the bot systematically can't execute a whole *kind* of strategy,
then the win-rate matrix lies about any deck built around that strategy — and we tune the game
against a distorted mirror.

The target is *breadth of competence* — a pilot that can play every deck's actual game plan at least
passably — more than raw peak strength. A bot that plays six of seven decks brilliantly and is blind
to the seventh's plan is worse for us than one that plays all seven decently.

## 2. What we've learned — the ceiling is real, and we've measured it

We have three bots of increasing effort. We used to call the strongest one the "oracle" and treat
its judgement as ground truth. **That was wrong**, and we now have a concrete counter-example.

In one matchup (the egg deck vs the cats deck) the strongest bot scores the egg deck at roughly a
one-in-five win rate. A human piloting the same egg deck against that same bot opponent goes
roughly even. The reason is specific and instructive: the egg deck's plan is to play cards that
*start weak and grow strong over many turns* (a snake that gets bigger every time you shuffle your
deck; another whose size equals how many cards have been removed). By the late game these
out-grow everything the cats deck has, and the egg deck takes over. **The bot cannot see this
plan at all** — its judgement scores a card by how strong it is *right now*, so a card that is
weak now and dominant later reads as worthless, and the bot never invests in the plan.

That is not a bug in one card. It is a structural limit of how the bot forms judgement, and it
generalises: the same blindness applies to slow combos, to multi-turn setups, to any plan whose
payoff isn't visible in the current position.

## 3. The core problem, conceptually

The bot's "judgement" today is a **fixed list of rules of thumb we wrote by hand** ("controlling
more of the board is good; having more food is good; threatening the enemy base is good"). Thinking
ahead (searching through possible moves) only ever *amplifies* that hand-written judgement — it
cannot repair a judgement that is blind to half the game. Three limits stack up:

- **It only sees the present.** It cannot value what a position will *become*, only what it *is*.
- **It has no sense of "plan" or "matchup."** It scores any position with the same rules of thumb;
  it has no notion of "I am the egg deck, and against cats my plan is to out-grow them."
- **It never learns.** It cannot get better from experience the way a human does across games.

## 4. What we want

We want a pilot whose judgement is **learned from experience** rather than hand-written by us —
one that discovers for itself which situations tend to lead to wins, including situations where the
value is in the *future* (the growing snake), not the present. Concretely, we want it to:

- **Have no strategy-class blind spots** — it should be able to play each deck's real plan
  (scaling, combo, tempo, control, rush) at least competently, not just the plans our hand-written
  rules happened to encode.
- **Close the gap to human play** across *multiple* matchups — measured, not asserted — using the
  human games we can record as the yardstick.
- **Not overfit.** A fix that only rescues the one egg-vs-cats matchup is a failure. The bar is
  general improvement across all decks and matchups.

Note a philosophical fit worth knowing: this project already forbids hand-coding specific card or
deck knowledge into the bot — the standing principle is that *deck knowledge should emerge from
generic features of the game state*. A pilot that learns judgement from experience is exactly that
principle taken to its conclusion, not a departure from it.

## 5. The direction we've chosen (and the one we deferred)

We considered two starting postures:

- **Build first (chosen).** Build one sensible learning pilot reasonably soon, measure it with the
  tools and human games we already have, and improve it with real results in hand. We chose this
  because we're in an unusually good position to *try things*: the game engine itself is fast, we
  already have tools to measure whether one bot is better than another, and we now have human games
  to aim at. That setup rewards learning from results over deciding everything on paper.
- **Survey first (deferred to a future to-do).** First survey how the best game-AI systems in the
  world handle games like this, write up the options and trade-offs, and recommend before building.
  Sound, but slower to anything that actually plays, with a real risk of analysis-paralysis. We've
  parked it as a follow-up, not a prerequisite.

So: **start by building something concrete, then iterate.** The survey can inform later rounds.

## 6. Things you must respect (constraints, not methods)

- **This is a hidden-information game.** Players cannot see each other's hands or deck order, and
  there is shuffle randomness. This is fundamentally unlike perfect-information games such as chess
  or Go, and the standard perfect-information playbook does not transfer directly. How you handle
  the hidden information is your call — but treating the game as if everything were visible will
  produce a confidently wrong pilot. (Mitigating factor: the *decklists themselves* are public —
  both players know the 30 cards in each deck from the start; only the draw order and current hand
  are hidden.)
- **No cheating.** The bot must never peek at the opponent's hidden cards. This is a hard, tested
  invariant. Whatever you build has to reach its decisions from only what a fair player could know.
- **The engine stays clean.** The rules engine is a pure, self-contained library with no outside
  dependencies. Learning machinery lives around it, not inside it.
- **Training is a real cost even though the engine is fast.** The bare engine plays extremely fast,
  but the moment a bot *thinks hard* on every move it slows down by orders of magnitude — our
  current strong bot is hundreds of times slower than the raw engine. A pilot that learns by
  playing itself has exactly this cost, multiplied by however many games training takes. So the
  compute budget — how many games, on what hardware — is a first-order question you'll have to
  scope early, not an afterthought. Two mitigations already exist: the learned judgement, once
  trained, is *cheap to run* (a quick calculation, not a deep search — so the finished pilot could
  end up both stronger *and* faster than today's), and the human games can give training a decent
  starting point instead of forcing it to learn from random flailing.
- **Throughput has a downstream consumer.** The whole reason the bot exists is to run large balance
  simulations. If the strong pilot is too slow to run thousands of games, we may need a fast pilot
  for bulk runs and a strong one for spot-checks. Keep that tension in view.

## 7. What success looks like

- The pilot plays every deck's actual plan at least competently — demonstrably no whole-strategy
  blind spots (the growing-snake plan is the canonical test case, but not the only one).
- Its win rates track human judgement more closely than today's bot does, across several matchups,
  measured against recorded human games — not just the one that motivated this.
- The balance matrix it produces is therefore trustworthy enough to tune the game on.

## 8. Open questions for you to decide

These are yours to answer; we have opinions but no commitments.

- Learn only the bot's *judgement* first, keeping its existing way of thinking ahead — the smallest
  useful step — or go straight for a more ambitious learned player?
- How much does the hidden information really matter in practice, given the decklists are public?
  That answer should drive how heavily you invest in handling it.
- Start the pilot off by imitating recorded human play, or let it learn purely from playing itself?
- Favour a judgement that's simple and inspectable and fast, or one with a higher ceiling that's
  heavier and more opaque?
- What compute, on what hardware, for the training run — and does that force us into the fast-pilot
  /strong-pilot split above?