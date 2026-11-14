"""Simulations for the energy prototype: bot games over the sample decks with the numbers that matter for the rules:
length, how games end, the first player's edge, decks running out, energy left unspent, and each card's record.

    AK_ENERGY=1 AK_RUST_BOTS=1 nice -n 15 .venv/bin/python tools/energy/sim.py rr --bot referee --games 20
    ... sim.py duel --bots referee,greedy --games 30          # which bot plays the rules better (mirror decks)
    ... sim.py rr --set first_turn_actions=2                  # a rule number tried without touching the data

Every run appends its games to results/energy/<label>.jsonl (one game a line, with the action log)."""
import argparse, collections, dataclasses, itertools, json, os, statistics, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
assert os.environ.get("AK_ENERGY") == "1", "run with AK_ENERGY=1"

from animal_kingdom.engine import rules
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game
from animal_kingdom.decks import BOT_DECKS, load_premade_deck
from animal_kingdom.sim.runner import make_bot


def play(job):
    deck_a, deck_b, seed, bot_a, bot_b, first, overrides = job
    cfg = dataclasses.replace(Config.default(), **overrides) if overrides else Config.default()
    st = new_game(load_premade_deck(deck_a), load_premade_deck(deck_b), seed, config=cfg, first_player=first)
    bots = {"A": make_bot(bot_a, seed), "B": make_bot(bot_b, seed + 7919)}
    played = {"A": collections.Counter(), "B": collections.Counter()}
    seen = {"A": set(u.card_id for u in st.hands["A"]), "B": set(u.card_id for u in st.hands["B"])}
    draws = {"A": 0, "B": 0}; unspent = {"A": 0, "B": 0}; turns_taken = {"A": 0, "B": 0}
    lead_changes = 0; leader = None
    turn = st.turn_counter; cur = st.current
    steps = 0
    res = rules.is_terminal(st)
    while res is None:
        actor = st.player_to_act()
        legal = rules.legal_actions(st)
        act = bots[actor].choose(st.view_for(actor), legal, st)
        d = act.to_dict()
        top = st.pending is None
        if top and d.get("kind") == "place":
            played[actor][d["card_id"]] += 1
        elif top and d.get("kind") == "draw":
            draws[actor] += 1
        left_before = rules.turn_actions(st) - st.actions_taken_this_turn
        rules.apply_action(st, act)
        steps += 1
        for s in ("A", "B"):
            seen[s].update(u.card_id for u in st.hands[s])
        if st.turn_counter != turn:            # the turn ended: what was left of its energy
            turns_taken[cur] += 1
            turn, cur = st.turn_counter, st.current
            l = "A" if st.food["A"] > st.food["B"] else "B" if st.food["B"] > st.food["A"] else None
            if l and leader and l != leader:
                lead_changes += 1
            leader = l or leader
        res = rules.is_terminal(st)
        if steps > 4000:
            break
    return {"a": deck_a, "b": deck_b, "seed": seed, "bots": [bot_a, bot_b], "first": st.first_player,
            "winner": res.winner if res else None, "reason": res.reason if res else "stuck", "turns": st.turn_counter,
            "food": [st.food["A"], st.food["B"]], "deck_left": [len(st.decks["A"]), len(st.decks["B"])],
            "hand_left": [len(st.hands["A"]), len(st.hands["B"])], "draws": [draws["A"], draws["B"]],
            "played": [dict(played["A"]), dict(played["B"])], "seen": [sorted(seen["A"]), sorted(seen["B"])],
            "lead_changes": lead_changes}


def run(jobs, label, workers):
    out = ROOT / "results" / "energy"; out.mkdir(parents=True, exist_ok=True)
    t = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        games = list(ex.map(play, jobs, chunksize=4))
    with open(out / f"{label}.jsonl", "w") as fh:
        for g in games:
            fh.write(json.dumps(g) + "\n")
    print(f"{len(games)} games in {time.time() - t:.0f}s -> results/energy/{label}.jsonl")
    return games


def summary(games):
    n = len(games)
    turns = [g["turns"] for g in games]
    reasons = collections.Counter(g["reason"] for g in games)
    first = sum(1 for g in games if g["winner"] == g["first"]) / max(1, sum(1 for g in games if g["winner"]))
    out_of_cards = sum(1 for g in games if 0 in g["deck_left"]) / n
    print(f"games {n} | player-turns median {statistics.median(turns)} (p10 {sorted(turns)[n // 10]}, p90 {sorted(turns)[9 * n // 10]})"
          f" | ends: {dict(reasons)} | first player wins {first:.0%} | a deck ran out {out_of_cards:.0%}"
          f" | draws per player {statistics.mean(d for g in games for d in g['draws']):.1f}"
          f" | food lead changes {statistics.mean(g['lead_changes'] for g in games):.2f}")


def deck_table(games):
    w = collections.defaultdict(lambda: [0, 0])
    for g in games:
        for seat, d in (("A", g["a"]), ("B", g["b"])):
            if g["a"] == g["b"]:
                continue
            w[d][1] += 1
            w[d][0] += g["winner"] == seat
    for d, (a, b) in sorted(w.items()):
        print(f"  {d}: {a}/{b} = {a / max(1, b):.0%}")
    return {d: a / max(1, b) for d, (a, b) in w.items()}


def card_table(games, top=14):
    """Per card: how often it was played when seen, and its side's win rate when played against the deck's own rate."""
    seen = collections.Counter(); played = collections.Counter(); wins = collections.Counter(); deck_games = collections.Counter(); deck_wins = collections.Counter()
    card_deck = {}
    for g in games:
        for k, seat in enumerate("AB"):
            deck = g["a"] if seat == "A" else g["b"]
            deck_games[deck] += 1; deck_wins[deck] += g["winner"] == seat
            for c in g["seen"][k]:
                seen[(deck, c)] += 1
            for c in g["played"][k]:
                played[(deck, c)] += 1; wins[(deck, c)] += g["winner"] == seat
    rows = []
    for (deck, c), s in seen.items():
        p = played[(deck, c)]
        base = deck_wins[deck] / deck_games[deck]
        rows.append((c, deck, s, p / s, (wins[(deck, c)] / p - base) if p >= 15 else None))
    rated = [r for r in rows if r[4] is not None]
    print("  most winning when played:", [(r[0], f"{r[4]:+.0%}", f"played {r[3]:.0%}") for r in sorted(rated, key=lambda r: -r[4])[:top]])
    print("  least winning when played:", [(r[0], f"{r[4]:+.0%}", f"played {r[3]:.0%}") for r in sorted(rated, key=lambda r: r[4])[:top]])
    print("  least played when seen:", [(r[0], f"{r[3]:.0%}") for r in sorted(rows, key=lambda r: r[3]) if r[2] >= 20][:top])
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["rr", "duel"])
    ap.add_argument("--bot", default="referee")
    ap.add_argument("--bots", default="referee,greedy")
    ap.add_argument("--games", type=int, default=10, help="per pairing and seat")
    ap.add_argument("--set", action="append", default=[], help="Config field=value, tried for this run only")
    ap.add_argument("--label", default=None)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    overrides = {}
    for kv in a.set:
        k, v = kv.split("=")
        overrides[k] = json.loads(v)
    decks = list(BOT_DECKS)
    jobs = []
    if a.mode == "rr":
        for (x, y) in itertools.combinations(decks, 2):
            for k in range(a.games):
                jobs.append((x, y, a.seed + 1000 * len(jobs) + k, a.bot, a.bot, "A", overrides))
                jobs.append((x, y, a.seed + 1000 * len(jobs) + k, a.bot, a.bot, "B", overrides))
        games = run(jobs, a.label or f"rr_{a.bot}_{int(time.time())}", a.workers)
        summary(games); deck_table(games); card_table(games)
    else:
        b1, b2 = a.bots.split(";") if ";" in a.bots else a.bots.split(",")
        for d in decks:
            for k in range(a.games):
                s = a.seed + 1000 * len(jobs) + k
                jobs.append((d, d, s, b1, b2, "A", overrides)); jobs.append((d, d, s + 1, b1, b2, "B", overrides))
                jobs.append((d, d, s + 2, b2, b1, "A", overrides)); jobs.append((d, d, s + 3, b2, b1, "B", overrides))
        games = run(jobs, a.label or f"duel_{b1}_{b2}_{int(time.time())}", a.workers)
        summary(games)
        w = sum(1 for g in games if g["winner"] and g["bots"][0 if g["winner"] == "A" else 1] == b1)
        print(f"  {b1} beats {b2}: {w}/{len(games)} = {w / len(games):.0%}")
