"""Double-oracle metagame mapping: does the 'goodstuff' pile have a predator, or is it dominant?

The deck_optimizer answers "what beats this fixed field?". This driver iterates that oracle to map
the top of the metagame (empirical game theory / double-oracle):

  * `counter` mode - one best-response against a *target* deck (default: goodstuff). Directly asks
    "can this deck be beaten heads-up, and by what?" - the sharp checkpoint.
  * `expand` mode - the full loop. Start from S = {7 premades, goodstuff}; each round build the deck
    that best beats the current set S (a best-response from several random starts to dodge local
    optima), and if it clears the field above a margin AND isn't a near-clone of a deck already in S,
    add it and repeat. Stop when no new deck exploits S (an approximate equilibrium). Then measure a
    clean out-of-sample matchup matrix over all of S and hand it to the `metagame_evolution`
    replicator: a goodstuff monoculture => dominant strategy; a stable mix => rock-paper-scissors.

Everything here runs under GreedyBot (fast); it's a GreedyBot-world map, to be referee/human
spot-checked on the decks that matter. Best-response is a hill-climb, so "no counter found" is
evidence, not proof (it's an equilibrium over the decks we *generated*, not all legal decks)."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Optional, Sequence

from ..engine.cards import DECK_SLUGS
from ..engine.config import Config, load_config_overrides
from ..decks import load_premade_deck
from .runner import run_round_robin
from . import metagame_evolution
from .deck_optimizer import (
    Evaluation, Recipe, evaluate, hill_climb, make_recipe, random_recipe,
    register_synthetic, format_recipe, _card_names,
)

GOODSTUFF_SLUG = "goodstuff"
DEFAULT_GOODSTUFF = Path("results/deck_optimizer/finalist_recipe.json")


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b) if (a or b) else 1.0


def _recipe_from_premade(slug: str) -> frozenset[str]:
    return frozenset(load_premade_deck(slug))


# --------------------------------------------------------------------------- best response

def best_response(
    opponents: Sequence[str],
    *,
    restarts: int,
    rng: random.Random,
    search_games: int,
    search_seed: int,
    steps: int,
    neighbors: int,
    patience: int,
    pilot: str,
    jobs: int,
    config: Optional[Config],
    objective: str = "mean",
) -> tuple[Recipe, Evaluation]:
    """Best deck vs `opponents`, hill-climbed from `restarts` independent random starts (keep best).

    Multiple random starts is the local-optimum hedge: one climb finds one basin; several sample
    several. The returned evaluation is in-sample (on the search seeds) - callers re-score fresh."""
    best_recipe: Optional[Recipe] = None
    best_eval: Optional[Evaluation] = None
    for r in range(restarts):
        start = random_recipe(rng)
        result = hill_climb(
            start, opponents, n_games=search_games, base_seed=search_seed, pilot=pilot,
            jobs=jobs, config=config, max_steps=steps, neighbors=neighbors, patience=patience,
            objective=objective, rng=random.Random(rng.random()),
        )
        score = result.best_eval.mean if objective == "mean" else result.best_eval.minimum
        best_score = (
            -1.0 if best_eval is None
            else (best_eval.mean if objective == "mean" else best_eval.minimum)
        )
        if score > best_score:
            best_recipe, best_eval = result.best_recipe, result.best_eval
        print(f"    restart {r+1}/{restarts}: mean {result.best_eval.mean:.1%} "
              f"min {result.best_eval.minimum:.1%}", file=sys.stderr)
    assert best_recipe is not None and best_eval is not None
    return best_recipe, best_eval


# --------------------------------------------------------------------------- matchup matrix

def matchup_matrix(
    slugs: Sequence[str],
    *,
    n_games: int,
    base_seed: int,
    pilot: str,
    jobs: int,
    config: Optional[Config],
) -> dict[str, dict[str, float]]:
    """Out-of-sample win-rate matrix over `slugs` (both movers pooled per pair; complementary)."""
    records = run_round_robin(list(slugs), n_games, base_seed,
                              bots=(pilot, pilot), config=config, jobs=jobs)
    agg: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0])
    for rec in records:
        credit = rec.credit("A")
        cell = agg[(rec.deck_a, rec.deck_b)]
        cell[0] += credit
        cell[1] += 1
    wr: dict[str, dict[str, float]] = {s: {} for s in slugs}
    for (a, b), (credit, count) in agg.items():
        wr[a][b] = credit / count
        wr[b][a] = 1.0 - credit / count
    for s in slugs:
        wr[s][s] = 0.5
    return wr


def write_matrix_csv(path: Path, slugs: Sequence[str], wr: dict[str, dict[str, float]]) -> None:
    """CSV in the format `metagame_evolution.load_matrix` reads (blank diagonal)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["", *slugs])
        for a in slugs:
            w.writerow([a, *("" if a == b else f"{wr[a][b]:.6f}" for b in slugs)])


def field_winrates(slugs: Sequence[str], wr: dict[str, dict[str, float]]) -> dict[str, float]:
    """Each deck's mean win rate vs the rest of the field (excluding its own mirror)."""
    others = {s: [wr[s][o] for o in slugs if o != s] for s in slugs}
    return {s: sum(v) / len(v) for s, v in others.items()}


# --------------------------------------------------------------------------- driver

def load_goodstuff(path: Path) -> list[str]:
    data = json.loads(path.read_text())
    recipe = make_recipe(data["legendary"], data["rare"], data["common"])
    return recipe.decklist()


def run_counter(args, config) -> None:
    """One best-response against a target set (the 'does it have a predator?' checkpoint)."""
    register_synthetic(GOODSTUFF_SLUG, load_goodstuff(args.goodstuff))
    target = _resolve_targets(args.target)
    print(f"Counter search vs {target} "
          f"({args.restarts} restarts, {2*args.search_games} games/opp, {args.pilot})\n",
          file=sys.stderr)
    rng = random.Random(args.rng_seed)
    recipe, _ = best_response(
        target, restarts=args.restarts, rng=rng, search_games=args.search_games,
        search_seed=args.search_seed, steps=args.steps, neighbors=args.neighbors,
        patience=args.patience, pilot=args.pilot, jobs=args.jobs, config=config,
    )
    # Fresh out-of-sample score of the found deck vs the target.
    ev = evaluate(recipe, target, n_games=args.val_games, base_seed=args.search_seed + 777,
                  pilot=args.pilot, jobs=args.jobs, config=config)
    print("\nBest counter found:")
    print(format_recipe(recipe))
    overlap = jaccard(recipe.all_ids(), frozenset(load_goodstuff(args.goodstuff)))
    print(f"\n  vs {', '.join(target)} (out-of-sample, {ev.games_per_field} games each):")
    for t, wrate in sorted(ev.per_field.items(), key=lambda kv: kv[1]):
        print(f"    beats {t:<12} {wrate:.1%}")
    print(f"  mean {ev.mean:.1%} | worst {ev.minimum:.1%}")
    print(f"  card overlap with goodstuff (Jaccard): {overlap:.0%} "
          f"-> {'a goodstuff MIRROR' if overlap > 0.5 else 'a DISTINCT archetype'}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "mode": "counter", "target": list(target), "pilot": args.pilot,
            "recipe": asdict(recipe),
            "eval": {"mean": ev.mean, "min": ev.minimum, "per_target": ev.per_field},
            "goodstuff_overlap": overlap,
        }, indent=2) + "\n")
        print(f"\nWrote {args.out}", file=sys.stderr)


def run_expand(args, config) -> None:
    """Full double-oracle loop -> matchup matrix -> replicator verdict."""
    register_synthetic(GOODSTUFF_SLUG, load_goodstuff(args.goodstuff))
    field = [*sorted(DECK_SLUGS), GOODSTUFF_SLUG]
    card_sets: dict[str, frozenset[str]] = {
        **{s: _recipe_from_premade(s) for s in DECK_SLUGS},
        GOODSTUFF_SLUG: frozenset(load_goodstuff(args.goodstuff)),
    }
    rng = random.Random(args.rng_seed)
    discovered: list[tuple[str, Recipe, float]] = []  # (slug, recipe, mean-vs-field-when-found)
    out_dir = args.out or Path("results/deck_optimizer/metagame")
    out_dir.mkdir(parents=True, exist_ok=True)
    names = _card_names()

    def _checkpoint() -> None:
        """Persist discovered decks as they're accepted, so the current leader is readable mid-run."""
        (out_dir / "discovered_live.json").write_text(json.dumps([
            {"slug": slug, "mean_vs_field": mean, "recipe": asdict(r),
             "cards": {rar: [names.get(c, c) for c in getattr(r, rar)]
                       for rar in ("legendary", "rare", "common")}}
            for slug, r, mean in discovered
        ], indent=2) + "\n")

    for rnd in range(1, args.rounds + 1):
        print(f"\n=== round {rnd}: best-response vs {len(field)}-deck set ===", file=sys.stderr)
        recipe, _ = best_response(
            field, restarts=args.restarts, rng=rng, search_games=args.search_games,
            search_seed=args.search_seed + rnd, steps=args.steps, neighbors=args.neighbors,
            patience=args.patience, pilot=args.pilot, jobs=args.jobs, config=config,
        )
        ev = evaluate(recipe, field, n_games=args.val_games,
                      base_seed=args.search_seed + rnd + 5000, pilot=args.pilot,
                      jobs=args.jobs, config=config)
        dup = max((jaccard(recipe.all_ids(), cs) for cs in card_sets.values()), default=0.0)
        accept = ev.mean > 0.5 + args.margin and dup < args.dup_threshold
        print(f"  best-response: mean {ev.mean:.1%} vs field | max overlap {dup:.0%} | "
              f"{'ACCEPT' if accept else 'STOP (converged)'}", file=sys.stderr)
        if not accept:
            break
        slug = f"counter{len(discovered)+1}"
        register_synthetic(slug, recipe.decklist())
        field.append(slug)
        card_sets[slug] = recipe.all_ids()
        discovered.append((slug, recipe, ev.mean))
        _checkpoint()

    # Clean out-of-sample matrix over the whole populated set, then replicator dynamics.
    print(f"\nBuilding out-of-sample matrix over {len(field)} decks "
          f"({args.matrix_games} games/pair)...", file=sys.stderr)
    wr = matchup_matrix(field, n_games=args.matrix_games, base_seed=args.search_seed + 90000,
                        pilot=args.pilot, jobs=args.jobs, config=config)
    fw = field_winrates(field, wr)
    matrix_path = out_dir / "matchup_matrix.csv"
    write_matrix_csv(matrix_path, field, wr)

    decks, dense = metagame_evolution.load_matrix(str(matrix_path))
    sim = metagame_evolution.run_simulation(dense, max_generations=5000)
    final = dict(zip(decks, sim.trace[-1]))

    print("\n--- field win rates (out-of-sample, vs rest of field) ---")
    for s, w in sorted(fw.items(), key=lambda kv: -kv[1]):
        print(f"  {s:<20} {w:.1%}")
    print(f"\n--- replicator stable population ({sim.stop_reason}) ---")
    for s, share in sorted(final.items(), key=lambda kv: -kv[1]):
        if share > 0.005:
            print(f"  {s:<20} {share:.1%}")
    survivors = sorted((s for s, share in final.items() if share > 0.05),
                       key=lambda s: -final[s])
    if len(survivors) <= 1:
        verdict = f"DOMINANT ({survivors[0] if survivors else '?'} monoculture)"
    else:
        premade_survivors = [s for s in survivors if s in DECK_SLUGS]
        verdict = (f"MIX of {len(survivors)} strategies "
                   f"({len(premade_survivors)} premade) - check for goodstuff-family clones")
    print(f"\nVerdict: {verdict}")

    (out_dir / "decks.json").write_text(json.dumps({
        "field": field, "field_winrates": fw, "final_population": final,
        "discovered": {slug: {"mean_vs_field": mean, "recipe": asdict(r),
                              "cards": [names.get(c, c) for c in sorted(r.all_ids())]}
                       for slug, r, mean in discovered},
    }, indent=2) + "\n")
    print(f"\nWrote {out_dir}/matchup_matrix.csv and decks.json", file=sys.stderr)


def _resolve_targets(spec: str) -> tuple[str, ...]:
    if spec == "premades":
        return tuple(sorted(DECK_SLUGS))
    return tuple(part.strip() for part in spec.split(",") if part.strip())


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("mode", choices=("counter", "expand"))
    p.add_argument("--goodstuff", type=Path, default=DEFAULT_GOODSTUFF,
                   help="JSON recipe for the goodstuff deck to register")
    p.add_argument("--target", default=GOODSTUFF_SLUG,
                   help="counter mode: opponents to beat (comma slugs, or 'premades')")
    p.add_argument("--pilot", default="greedy")
    p.add_argument("--restarts", type=int, default=3, help="random starts per best-response")
    p.add_argument("--search-games", type=int, default=30, help="games/opp PER MOVER during search")
    p.add_argument("--val-games", type=int, default=100, help="games/opp per mover for fresh re-score")
    p.add_argument("--matrix-games", type=int, default=100, help="games/pair per mover for the matrix")
    p.add_argument("--steps", type=int, default=30)
    p.add_argument("--neighbors", type=int, default=12)
    p.add_argument("--patience", type=int, default=6)
    p.add_argument("--rounds", type=int, default=4, help="expand mode: max best-response rounds")
    p.add_argument("--margin", type=float, default=0.02, help="min edge over 50%% to accept a deck")
    p.add_argument("--dup-threshold", type=float, default=0.6,
                   help="reject a best-response whose card Jaccard vs an existing deck exceeds this")
    p.add_argument("--rng-seed", type=int, default=0)
    p.add_argument("--search-seed", type=int, default=515000)
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes")
    p.add_argument("--config", default=None)
    p.add_argument("--out", type=Path)
    args = p.parse_args(argv)

    config = load_config_overrides(args.config)
    start = time.monotonic()
    if args.mode == "counter":
        run_counter(args, config)
    else:
        run_expand(args, config)
    print(f"\n({time.monotonic() - start:.0f}s)", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
