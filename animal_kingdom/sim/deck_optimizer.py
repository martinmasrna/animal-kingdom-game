"""Automated cross-deck deckbuilding: hill-climb a 30-card list to beat the premade field.

The experiment this powers: can a legal deck assembled *across* all 7 premade pools beat every
premade deck under competent play? A deck is a `Recipe` - 4 legendary + 4 rare + 6 common designs
(the 4-4-6 shape) expanded to 30 cards via the per-rarity copy limits, exactly like a premade deck.
Recipes are injected into `decks.PREMADE_DECKS` under a synthetic slug, so the whole existing sim
harness (run_pairs, play_game) plays them and the generalist bots pilot them with no slug knowledge.

Method (see docs/balance for the two hazards this design guards):
  * Fitness = win rate of the candidate vs the 7-deck field, both movers, on a FIXED paired seed
    set. Reusing the same seeds every evaluation makes a one-card swap a paired comparison, so the
    *sign* of a swap's effect is low-variance even at a modest games/matchup - the trick that lets
    the search run cheaply and the finalist be validated separately at >=200 games.
  * Search = stochastic steepest-ascent hill-climb: each step samples K one-card neighbors (swap a
    single design for an unused one of the same rarity), evaluates them on the shared seeds, and
    takes the best strict improvement; stops after `patience` barren steps.
  * `--pilot greedy` (fast, the default for search) vs `--pilot referee` (the oracle gate). The
    same tool runs the final RefereeBot verification - just slower.

GreedyBot caveat (GREEDY_CAVEAT): a deck tuned to beat a GreedyBot field, piloted by GreedyBot, is
partly overfit to GreedyBot's blind spots (it underplays combo/delayed decks). Treat the search
winrates as a hypothesis; the RefereeBot pass is the verdict.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Sequence

from ..decks import PREMADE_DECKS
from ..engine.cards import COPY_LIMITS, NON_DECK_SLUGS, load_cards
from ..engine.config import Config, load_config_overrides
from ..engine.cards import DECK_SLUGS
from .runner import run_pairs

RARITIES = ("legendary", "rare", "common")
SLOTS = {"legendary": 4, "rare": 4, "common": 6}  # 4-4-6, expands to 4*1 + 4*2 + 6*3 = 30
CANDIDATE_SLUG = "_candidate"  # synthetic deck slug the recipe is injected under


def draftable_by_rarity(cards=None, exclude: frozenset[str] = frozenset()) -> dict[str, list[str]]:
    """All draftable card ids grouped by rarity (tokens/reserve excluded), id-sorted for determinism.

    `exclude` drops specific card ids too - used to build a deck from the pool *minus* another
    deck's cards (the disjoint-roster constraint)."""
    cards = cards or load_cards()
    pools: dict[str, list[str]] = {r: [] for r in RARITIES}
    for card in cards.values():
        if card.deck in NON_DECK_SLUGS or card.id in exclude:
            continue
        pools[card.rarity].append(card.id)
    return {r: sorted(ids) for r, ids in pools.items()}


@dataclass(frozen=True)
class Recipe:
    """A legal 4-4-6 decklist as its unique designs (order-insensitive; stored sorted)."""

    legendary: tuple[str, ...]
    rare: tuple[str, ...]
    common: tuple[str, ...]

    def __post_init__(self):
        for rarity in RARITIES:
            ids = getattr(self, rarity)
            if len(ids) != SLOTS[rarity]:
                raise ValueError(f"{rarity}: need {SLOTS[rarity]} designs, got {len(ids)}")
            if len(set(ids)) != len(ids):
                raise ValueError(f"{rarity}: duplicate design in {ids}")

    def slot(self, rarity: str) -> tuple[str, ...]:
        return getattr(self, rarity)

    def with_slot(self, rarity: str, ids: Sequence[str]) -> "Recipe":
        return Recipe(**{**asdict(self), rarity: tuple(sorted(ids))})

    def decklist(self) -> list[str]:
        """Expand to the 30-card id list via the per-rarity copy limits."""
        out: list[str] = []
        for rarity in RARITIES:
            for cid in self.slot(rarity):
                out.extend([cid] * COPY_LIMITS[rarity])
        return out

    def all_ids(self) -> frozenset[str]:
        return frozenset(self.legendary + self.rare + self.common)


def make_recipe(legendary, rare, common) -> Recipe:
    return Recipe(tuple(sorted(legendary)), tuple(sorted(rare)), tuple(sorted(common)))


def random_recipe(rng: random.Random, pools: Optional[dict[str, list[str]]] = None) -> Recipe:
    """A uniformly-sampled legal 4-4-6 deck - a diverse start for a best-response search so it
    doesn't just converge back to whatever deck it was seeded from."""
    pools = pools or draftable_by_rarity()
    return make_recipe(
        legendary=rng.sample(pools["legendary"], SLOTS["legendary"]),
        rare=rng.sample(pools["rare"], SLOTS["rare"]),
        common=rng.sample(pools["common"], SLOTS["common"]),
    )


# The LLM hypothesis seed: premium *standalone*-value midrange - big bodies for region
# control/walls + efficient unconditional removal + a little flight for reach. Every card fires
# with no "if you control N friendly X" precondition, so cross-deck mixing doesn't break synergy.
SEED_RECIPE = make_recipe(
    legendary=("gale", "sirocco", "pestis", "alpha"),
    rare=("jaguar", "stoop", "polar_bear", "rhinoceros"),  # stoop = Peregrine Falcon
    common=("lion", "tiger", "anaconda", "dire_wolf", "eagle", "bat"),
)


# --------------------------------------------------------------------------- evaluation

@dataclass(frozen=True)
class Evaluation:
    mean: float                       # mean per-field win rate (equal weight per matchup)
    minimum: float                    # worst single-matchup win rate (the maximin objective)
    per_field: dict[str, float]       # slug -> candidate win rate vs that field deck
    games_per_field: int


# Fixed synthetic opponent decks (goodstuff + any discovered counters) that must be loadable
# alongside the premades - e.g. the double-oracle metagame set. The mutating candidate is layered
# on top of these at eval time. Kept module-level so it survives across evaluate() calls.
_SYNTHETIC_DECKS: dict[str, list[str]] = {}


def _sync_registry(candidate: Optional[list[str]] = None) -> None:
    """Publish the synthetic decks (+ optional candidate) into this process's PREMADE_DECKS and
    into $AK_EXTRA_DECKS, so `spawn`ed sim workers (which re-import decks.py) reconstruct them all."""
    decks = dict(_SYNTHETIC_DECKS)
    if candidate is not None:
        decks[CANDIDATE_SLUG] = candidate
    PREMADE_DECKS.update(decks)
    os.environ["AK_EXTRA_DECKS"] = json.dumps(decks)


def register_synthetic(slug: str, decklist: Sequence[str]) -> None:
    """Register a fixed synthetic deck (a non-premade opponent) under `slug`, visible to workers."""
    if slug in DECK_SLUGS:
        raise ValueError(f"{slug!r} collides with a premade deck slug")
    _SYNTHETIC_DECKS[slug] = list(decklist)
    _sync_registry()


def evaluate(
    recipe: Recipe,
    field: Sequence[str],
    *,
    n_games: int,
    base_seed: int,
    pilot: str,
    jobs: int,
    config: Optional[Config],
    map_id: str = "map_b",
) -> Evaluation:
    """Win rate of `recipe` vs each field deck (both movers, `n_games` each way => 2*n_games/field).

    The candidate is always deck_a/seat A; `run_pairs` forces first-player both ways per pair, so
    the mover axis is balanced. Seeds are a deterministic function of `base_seed`, so passing the
    same `base_seed` across candidates makes swaps paired comparisons."""
    _sync_registry(recipe.decklist())
    pairs = [(CANDIDATE_SLUG, f) for f in field]
    records = run_pairs(
        pairs, n_games, base_seed,
        bots=(pilot, pilot), config=config, map_id=map_id, jobs=jobs,
    )
    wins: dict[str, float] = {f: 0.0 for f in field}
    counts: dict[str, int] = {f: 0 for f in field}
    for rec in records:
        f = rec.deck_b  # candidate is always deck_a
        counts[f] += 1
        if rec.winner == "A":
            wins[f] += 1.0
        elif rec.winner is None:
            wins[f] += 0.5
    per_field = {f: wins[f] / counts[f] for f in field}
    return Evaluation(
        mean=sum(per_field.values()) / len(per_field),
        minimum=min(per_field.values()),
        per_field=per_field,
        games_per_field=2 * n_games,
    )


def _objective(ev: Evaluation, objective: str) -> float:
    return ev.minimum if objective == "min" else ev.mean


# --------------------------------------------------------------------------- search

def _neighbor(recipe: Recipe, pools: dict[str, list[str]], rng: random.Random) -> Recipe:
    """One random single-card swap: replace a design in a random slot with an unused same-rarity one."""
    rarity = rng.choice(RARITIES)
    current = list(recipe.slot(rarity))
    used = recipe.all_ids()
    choices = [cid for cid in pools[rarity] if cid not in used]
    if not choices:
        return recipe
    out = list(current)
    out[rng.randrange(len(out))] = rng.choice(choices)
    return recipe.with_slot(rarity, out)


@dataclass
class SearchResult:
    seed_recipe: Recipe
    seed_eval: Evaluation
    best_recipe: Recipe
    best_eval: Evaluation
    steps_run: int
    accepted: int
    history: list[dict]


def hill_climb(
    seed: Recipe,
    field: Sequence[str],
    *,
    n_games: int,
    base_seed: int,
    pilot: str,
    jobs: int,
    config: Optional[Config],
    max_steps: int,
    neighbors: int,
    patience: int,
    objective: str,
    rng: random.Random,
    pools: Optional[dict[str, list[str]]] = None,
    on_step=None,
) -> SearchResult:
    pools = pools or _POOLS  # restrict the card pool (e.g. exclude another deck's cards)

    def ev(recipe: Recipe) -> Evaluation:
        return evaluate(recipe, field, n_games=n_games, base_seed=base_seed,
                        pilot=pilot, jobs=jobs, config=config)

    best, best_ev = seed, ev(seed)
    seed_ev = best_ev
    history: list[dict] = []
    barren = 0
    accepted = 0
    step = 0
    while step < max_steps and barren < patience:
        step += 1
        # Sample distinct neighbors, evaluate on the shared seed set, take the best improvement.
        proposals: dict[frozenset, Recipe] = {}
        attempts = 0
        while len(proposals) < neighbors and attempts < neighbors * 10:
            attempts += 1
            cand = _neighbor(best, pools, rng)
            key = cand.all_ids()
            if key != best.all_ids():
                proposals[key] = cand
        scored = [(ev(c), c) for c in proposals.values()]
        cand_ev, cand = max(scored, key=lambda t: _objective(t[0], objective))
        improved = _objective(cand_ev, objective) > _objective(best_ev, objective) + 1e-9
        if improved:
            best, best_ev = cand, cand_ev
            accepted += 1
            barren = 0
        else:
            barren += 1
        rec = {
            "step": step, "accepted": improved,
            "best_mean": best_ev.mean, "best_min": best_ev.minimum,
            "tried_best_mean": cand_ev.mean, "tried_best_min": cand_ev.minimum,
            "barren": barren,
        }
        history.append(rec)
        if on_step:
            on_step(rec, best, best_ev)
    return SearchResult(seed, seed_ev, best, best_ev, step, accepted, history)


_POOLS = draftable_by_rarity()


# --------------------------------------------------------------------------- reporting

def _card_names():
    return {cid: c.name for cid, c in load_cards().items()}


def format_recipe(recipe: Recipe) -> str:
    names = _card_names()
    lines = []
    for rarity in RARITIES:
        cards = ", ".join(names.get(c, c) for c in recipe.slot(rarity))
        lines.append(f"  {rarity:<9} x{COPY_LIMITS[rarity]}: {cards}")
    return "\n".join(lines)


def format_eval(ev: Evaluation) -> str:
    rows = "\n".join(
        f"    vs {f:<20} {wr:.1%}" for f, wr in sorted(ev.per_field.items(), key=lambda t: t[1])
    )
    beats_all = "YES" if ev.minimum > 0.5 else "no"
    return (f"  mean {ev.mean:.1%}  |  worst {ev.minimum:.1%}  |  beats all 7: {beats_all}"
            f"  ({ev.games_per_field} games/field)\n{rows}")


# --------------------------------------------------------------------------- CLI

def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pilot", default="greedy",
                        help="bot kind for both seats (greedy=fast search, referee=oracle gate)")
    parser.add_argument("--games", type=int, default=40,
                        help="games per field deck PER MOVER (total per field = 2x this)")
    parser.add_argument("--base-seed", type=int, default=20260710)
    parser.add_argument("--steps", type=int, default=40, help="max hill-climb steps")
    parser.add_argument("--neighbors", type=int, default=12, help="neighbors sampled per step")
    parser.add_argument("--patience", type=int, default=6, help="stop after this many barren steps")
    parser.add_argument("--objective", choices=("mean", "min"), default="mean",
                        help="maximize mean field winrate, or the worst matchup (maximin)")
    parser.add_argument("--rng-seed", type=int, default=0, help="seed for neighbor proposals")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--config", default=None)
    parser.add_argument("--seed-recipe", type=Path,
                        help="JSON {legendary:[...],rare:[...],common:[...]} to start from "
                             "(default: the built-in premium-standalone seed)")
    parser.add_argument("--evaluate-only", action="store_true",
                        help="just score the seed recipe vs the field and exit (no search)")
    parser.add_argument("--out", type=Path, help="write the finalist recipe + eval as JSON")
    args = parser.parse_args(argv)

    config = load_config_overrides(args.config)
    field = sorted(DECK_SLUGS)

    if args.seed_recipe:
        data = json.loads(args.seed_recipe.read_text())
        seed = make_recipe(data["legendary"], data["rare"], data["common"])
    else:
        seed = SEED_RECIPE

    print(f"Field ({len(field)} decks): {', '.join(field)}", file=sys.stderr)
    print(f"Pilot: {args.pilot} | {2*args.games} games/field | base_seed {args.base_seed}\n",
          file=sys.stderr)
    print("Seed recipe:")
    print(format_recipe(seed))

    start = time.monotonic()
    if args.evaluate_only:
        ev = evaluate(seed, field, n_games=args.games, base_seed=args.base_seed,
                      pilot=args.pilot, jobs=args.jobs, config=config)
        print("\nSeed evaluation:")
        print(format_eval(ev))
        result = SearchResult(seed, ev, seed, ev, 0, 0, [])
    else:
        def on_step(rec, best, best_ev):
            tag = "ACCEPT" if rec["accepted"] else "  --  "
            print(f"  step {rec['step']:>3} {tag}  best mean {best_ev.mean:.1%} "
                  f"min {best_ev.minimum:.1%}  (barren {rec['barren']})", file=sys.stderr)
        result = hill_climb(
            seed, field, n_games=args.games, base_seed=args.base_seed, pilot=args.pilot,
            jobs=args.jobs, config=config, max_steps=args.steps, neighbors=args.neighbors,
            patience=args.patience, objective=args.objective, rng=random.Random(args.rng_seed),
            on_step=on_step,
        )
        print(f"\nSeed:      mean {result.seed_eval.mean:.1%} | worst {result.seed_eval.minimum:.1%}")
        print("\nFinalist recipe:")
        print(format_recipe(result.best_recipe))
        print("\nFinalist evaluation:")
        print(format_eval(result.best_eval))

    print(f"\n({result.steps_run} steps, {result.accepted} accepted, "
          f"{time.monotonic()-start:.0f}s)", file=sys.stderr)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "pilot": args.pilot, "games_per_field": 2 * args.games, "base_seed": args.base_seed,
            "objective": args.objective,
            "seed_recipe": asdict(result.seed_recipe),
            "seed_eval": {"mean": result.seed_eval.mean, "min": result.seed_eval.minimum,
                          "per_field": result.seed_eval.per_field},
            "finalist_recipe": asdict(result.best_recipe),
            "finalist_eval": {"mean": result.best_eval.mean, "min": result.best_eval.minimum,
                              "per_field": result.best_eval.per_field},
            "history": result.history,
        }, indent=2) + "\n")
        print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
