"""Determinization: re-sample a state's hidden information from one seat's perspective.

`determinize(state, me, rng)` returns an independent clone in which everything `me`
cannot legitimately know has been re-dealt at random, so a search bot may treat the
clone as a *possible world* and search it adversarially (clone / apply_action / let a
policy play the opponent's real reply) without ever reading the true hidden state.
This is the seam that keeps RefereeBot honest, and it is deliberately bot-agnostic so
a future ISMCTS bot can reuse it.

Honesty invariant: the function reads the opponent's hand only as a *multiset of card
ids* (their hand+deck combined pool) plus the public Skunk lock flags - never the true
hand/deck split, never either deck's order. The combined multiset is public knowledge
by conservation: decklists are open, and every card that has left the opponent's
hand+deck pool did so visibly (board placements and Remove Pile are public). Building
the pool from `state.hands[opp]`/`state.decks[opp]` rather than re-deriving it from
`starting_decks` minus sightings is therefore equivalent - and unambiguous where the
derivation is not (the Remove Pile is shared and owner-less, so "whose lion was
removed" cannot be attributed in mirror matches).

What is re-sampled:
  - my own deck's order (contents are known to me, order is not - this also
    deliberately forgets transient peek-order knowledge, e.g. Owl; conservative),
  - the opponent's hand/deck split and their deck's order,
  - the chance stream (`clone.rng` is reseeded from `rng`, so worlds sampled from one
    RNG resolve random effects - Black Swan discards, shuffle-backs, Grizzly Bear
    targets - differently instead of replaying the original stream's outcomes).

Documented approximations (both err toward the referee knowing *less*, never more):
  - Cards publicly returned to the opponent's hand without a lock marker (Shuck,
    Opossum) are treated as unknown and re-dealt into the pool.
  - Hidden-hand strength counters (Clarion / Red Wolf buffing Canines in hand) are
    dropped: re-dealt cards are fresh instances with counter 0.
Skunk-locked hand cards are the exception that *is* tracked: the bounce is public and
`locked_until_turn` gates legality, so locked instances stay in hand, lock intact.
"""

from __future__ import annotations

import random

from ..engine.state import GameState, UnitInstance, other_player


def determinize(state: GameState, me: str, rng: random.Random) -> GameState:
    """An independent clone of `state` with hidden info re-sampled from `me`'s
    perspective. `state` is never mutated; `rng` drives every random choice, so equal
    (state, me, rng-state) inputs yield identical worlds."""
    clone = state.clone()
    opp = other_player(me)

    # My own deck: contents known, order unknown. Sort before shuffling so the
    # sampled order depends only on the (known) contents, not the (hidden) incoming
    # order - same reasoning as the opponent-pool sort below.
    clone.decks[me].sort()
    rng.shuffle(clone.decks[me])

    # Opponent hand/deck: keep publicly-locked cards in hand, pool and re-deal the rest.
    hand = clone.hands[opp]
    kept = [u for u in hand if u.locked_until_turn > clone.turn_counter]
    hidden = [u for u in hand if u not in kept]
    pool = [u.card_id for u in hidden] + clone.decks[opp]
    # Sort before shuffling: the pool must be a pure multiset. Without this, the
    # incoming hand/deck order (hidden info) would seed the shuffle differently and
    # leak the true split into the sampled worlds.
    pool.sort()
    rng.shuffle(pool)
    dealt = len(hidden)
    clone.hands[opp] = kept + [
        UnitInstance(card_id, opp, clone.new_iid()) for card_id in pool[:dealt]
    ]
    clone.decks[opp] = pool[dealt:]

    # Independent chance stream per world (a plain clone would replay the original's).
    clone.rng = random.Random(rng.getrandbits(64))
    return clone
