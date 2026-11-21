"""The engine's fuzz: random games played on the Rust engine, a random legal action each step, and after every action
the checks no position may fail. A panic inside the engine arrives as an error and fails the game it happened in.

    .venv/bin/python tools/engine_rs/fuzz.py [--games 500] [--seed 0] [--jobs 6] [--mode real|synthetic|mixed] [--stop]

What a game covers: 25-card decks over every card the table holds (the collectible ones, and the Spore token as a card in
hand), a leader for most decks; ending the turn wherever it is legal, not only when nothing else is; both players'
mulligans, in turn and at once; an illegal action, which must be refused and change nothing. `--mode synthetic` adds
cards no deck holds yet, for the rules no card uses today (Armor, Stealth, Poison, a strength that is a count, a
0-strength body), and plays some games under tight caps, a small hand limit or no mulligan, so the turn caps, the turn
limit and the burn are reached.

What is checked after every action:
  - saving the position and loading it gives the same position, the same legal actions and the same answers;
  - a game that is over offers no action, lets no turn end and refuses any action; one that is not offers at least one;
  - every unit's instance id is unique, the Remove Pile's owners stay in step with it, no hand is past the hand limit;
  - food never goes below 0, and the mana left is never below 0;
  - with nothing resolving, no tile holds more than one animal and no animal on the board has strength 0;
  - a clone is independent: acting on it leaves the position it came from untouched.
"""
import argparse, copy, json, os, random, sys, time
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # this tree, not an installed copy
import ak_engine
from animal_kingdom.game import COPY_LIMITS, DECK_SIZE, LEADERS, MAP_ID, SKIP, Config, load_bundled_json

RAW_CARDS = load_bundled_json("cards.json")
MAPS_JSON = json.dumps(load_bundled_json("maps.json"))


def synthetic_cards():
    """The real table plus cards for the rules no card uses today."""
    raw = copy.deepcopy(RAW_CARDS)
    def card(cid, strength, cost, keywords=(), dynamic=None):
        rec = {"id": cid, "name": cid, "status": "collectible", "rarity": "common", "base_strength": strength, "cost": cost,
               "keywords": list(keywords), "text": ""}
        if dynamic:
            rec["base_strength"], rec["dynamic_strength"] = "dynamic", dynamic
        raw["cards"].append(rec)
    card("t_armor_2", 2, 1, ["Armor"])
    card("t_armor_5", 5, 3, ["Armor"])
    card("t_armor_flight_3", 3, 2, ["Armor", "Flight"])
    card("t_stealth_2", 2, 1, ["Stealth"])
    card("t_stealth_6", 6, 3, ["Stealth"])
    card("t_poison_1", 1, 1, ["Poison"])
    card("t_poison_4", 4, 2, ["Poison"])
    card("t_poison_spikes_2", 2, 2, ["Poison", "Spikes"])
    card("t_armor_spikes_3", 3, 2, ["Armor", "Spikes"])
    card("t_hungry_armor_6", 6, 3, ["Hungry", "Armor"])
    card("t_hungry_flight_5", 5, 3, ["Hungry", "Flight"])
    card("t_zero", 0, 0)
    card("t_zero_flight", 0, 1, ["Flight"])
    card("t_shade_hand", 0, 2, dynamic="hand_count")
    card("t_shade_ally", 0, 2, dynamic="ally_count")
    card("t_shade_region", 0, 1, dynamic="region_count")
    card("t_shade_played", 0, 1, ["Flight"], dynamic="played_count")
    return raw


CONFIGS = [
    {},
    {"max_actions_per_turn": 5},
    {"max_effect_steps_per_turn": 6},
    {"max_effect_steps_per_turn": 3, "max_actions_per_turn": 8},
    {"hand_limit": 4},
    {"hand_limit": 5, "turn_draw_count": 2, "mama_spores": 4},
    {"mulligan": False},
    {"mana_cap": 30, "start_food": 40, "scout_look": 5, "assassin_nth_card": 2, "max_turns": 30},
    {"first_player_opening_draw": 6, "second_player_opening_draw": 7, "leader_power_cost": 1, "elf_power_cost": 0},
    {"shade_growth": 1, "crush_max": 12, "double_raid_factor": 3, "raider_leader_bonus": 4, "warlord_leader_food": 3, "hungry_food": 2},
]

_cache = {}


def setup(mode, k):
    """(pool of card ids, each card's rarity, the config, the engine) for game `k` of a run."""
    synthetic = mode == "synthetic" or (mode == "mixed" and k % 2 == 1)
    over = CONFIGS[(k // 2) % len(CONFIGS)] if synthetic else {}
    key = (synthetic, tuple(sorted(over.items())))
    if key not in _cache:
        config = Config(**over)
        eng = ak_engine.Engine(json.dumps(synthetic_cards() if synthetic else RAW_CARDS), MAPS_JSON, json.dumps(config.as_dict()), MAP_ID)
        rarity = {c["id"]: c["rarity"] for c in eng.cards()}
        _cache[key] = (sorted(rarity), rarity, config, eng)
    return _cache[key]


def random_deck(rng, pool, rarity, heavy):
    """25 cards within the copy limits; `heavy` cards (the ones under test) come up three times as often."""
    deck, weights = [], [3 if c in heavy else 1 for c in pool]
    while len(deck) < DECK_SIZE:
        c = rng.choices(pool, weights)[0]
        if deck.count(c) < COPY_LIMITS[rarity[c]]:
            deck.append(c)
    lead = None
    if rng.random() < 0.9:
        lead = rng.choice(sorted(LEADERS))
        if lead not in deck:
            deck[rng.randrange(len(deck))] = lead
    return deck, lead


def illegal_action(rng, tiles, pool, legal):
    """Some action that is not legal now."""
    for _ in range(20):
        a = rng.choice([{"kind": "place", "card_id": rng.choice(pool), "target": ["cr", rng.choice(tiles)]},
                        {"kind": "place", "card_id": rng.choice(pool), "target": ["hq", rng.choice("AB")]},
                        {"kind": "choice", "choice": rng.choice(tiles)}, {"kind": "choice", "choice": rng.randrange(60)},
                        {"kind": "choice", "choice": SKIP}, {"kind": "choice", "choice": "deck:1"}, {"kind": "leader"}])
        if a not in legal:
            return a
    return None


def answers(st, d):
    """Everything a position answers beyond its saved form."""
    units = [u["iid"] for stack in d["board"].values() for u in stack] + [u["iid"] for p in "AB" for u in d["hands"][p]]
    return {"legal": st.legal_actions(), "can_pass": st.can_pass(), "terminal": st.is_terminal(), "to_act": st.player_to_act(),
            "units": {i: st.unit_view(i) for i in units},
            "seats": {p: [st.mana_left(p), st.mana_total(p), st.power_cost(p), st.leader_usable(p), st.region_income(p),
                          st.mulligan_cap(p), st.early_mulligan(p), st.view_for(p), st.connected_occupied(p)] for p in "AB"}}


def check(eng, st, config, label):
    """None when the position passes every check, else what fails."""
    d = st.to_dict()
    a = answers(st, d)
    again = eng.from_dict(json.loads(json.dumps(d)))
    d2 = again.to_dict()
    if d2 != d or list(d2["board"]) != list(d["board"]):
        return f"a saved position loads differently after {label}"
    if answers(again, d2) != a:
        return f"a loaded position answers differently after {label}"
    over = d["result"] is not None
    if (a["terminal"] is not None) != over:
        return f"is_terminal and the position's result disagree after {label}: {a['terminal']} against {d['result']}"
    if over and (a["legal"] or a["can_pass"]):
        return f"the game is over and something is still legal after {label}: {a['legal'][:3]}"
    if not over and not a["legal"]:
        return f"the game goes on and nothing is legal after {label}"
    iids = [u["iid"] for stack in d["board"].values() for u in stack] + [u["iid"] for p in "AB" for u in d["hands"][p]]
    if len(set(iids)) != len(iids) or any(i >= d["next_iid"] for i in iids):
        return f"instance ids clash after {label}: {sorted(iids)} next {d['next_iid']}"
    if len(d["pile_owners"]) != len(d["remove_pile"]):
        return f"the Remove Pile and its owners are out of step after {label}"
    for p in "AB":
        if len(d["hands"][p]) > config.hand_limit:
            return f"{p} holds {len(d['hands'][p])} cards, past the hand limit, after {label}"
        if d["food"][p] < 0:
            return f"{p}'s food is {d['food'][p]} after {label}"
        if st.mana_left(p) < 0:
            return f"{p}'s mana left is {st.mana_left(p)} after {label}"
    if d["pending"] is None and not d["effect_stack"]:
        for cr, stack in d["board"].items():
            if len(stack) != 1:
                return f"{cr} holds {len(stack)} animals with nothing resolving after {label}: {[u['card_id'] for u in stack]}"
            if not over and a["units"][stack[0]["iid"]]["str"] <= 0:
                return f"{stack[0]['card_id']} stands on {cr} at strength 0 after {label}"
    elif d["pending"] is not None and d["pending"]["chooser"] != a["to_act"]:
        return f"the chooser is not the one to act after {label}"
    return None


def play(seed, mode, k, max_steps=1500):
    pool, rarity, config, eng = setup(mode, k)
    rng = random.Random(seed)
    tiles = eng.map()["crossroads"]
    heavy = {c for c in pool if c.startswith("t_")} | {"spore"}
    (deck_a, lead_a), (deck_b, lead_b) = random_deck(rng, pool, rarity, heavy), random_deck(rng, pool, rarity, heavy)
    game_seed = rng.choice([seed, rng.getrandbits(32), rng.getrandbits(64), rng.getrandbits(100), -rng.getrandbits(40), 0])
    first = rng.choice([None, None, "A", "B"])
    stats = Counter()
    try:
        st = eng.new_game(deck_a, deck_b, game_seed, first, {"A": lead_a, "B": lead_b})
        st.record_events(True)
        bad = check(eng, st, config, "the deal")
        steps = 0
        while bad is None and st.is_terminal() is None and steps < max_steps:
            steps += 1
            legal = st.legal_actions()
            d = st.to_dict()
            if rng.random() < 0.03:                     # an illegal action: refused, and the position untouched
                a = illegal_action(rng, tiles, pool, legal)
                if a is not None:
                    try:
                        st.apply_action(a)
                        bad = f"an illegal action was accepted at step {steps}: {a}"
                        break
                    except ValueError:
                        stats["illegal actions refused"] += 1
                    if st.to_dict() != d:
                        bad = f"a refused action changed the position at step {steps}: {a}"
                        break
            if rng.random() < 0.05:                     # a clone is its own position
                c = st.clone()
                c.apply_action(rng.choice(legal), False)
                if st.to_dict() != d:
                    bad = f"acting on a clone changed the position at step {steps}"
                    break
            other = "B" if st.player_to_act() == "A" else "A"
            if st.early_mulligan(other) is not None and rng.random() < 0.5:   # the other seat's mulligan, at the same time
                hand = [u["iid"] for u in d["hands"][other]]
                a = {"kind": "choice", "choice": rng.choice(hand + [SKIP])}
                st.apply_early_mulligan(other, a)
                stats["mulligan choices out of turn"] += 1
            else:
                a = {"kind": "pass"} if st.can_pass() and rng.random() < 0.12 else rng.choice(legal)
                if a["kind"] == "pass" and len(legal) > 1:
                    stats["turns ended with plays still legal"] += 1
                st.apply_action(a, validate=rng.random() < 0.5)
            for e in st.take_events():
                stats["event: " + e["e"]] += 1
            bad = check(eng, st, config, f"step {steps} {a}")
        if bad is None and st.is_terminal() is None:
            bad = f"no end after {max_steps} steps"
        if bad is None:
            stats[f"games ended by {st.is_terminal()['reason']}"] += 1
            try:
                st.apply_action({"kind": "pass"})
                bad = "an action was accepted after the game's end"
            except ValueError:
                pass
    except (ValueError, RuntimeError) as e:
        bad, steps = f"the engine raised {type(e).__name__}: {e}", -1
    return seed, k, bad, steps, stats


def _job(args):
    return play(*args)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--games", type=int, default=500)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--jobs", type=int, default=6)
    p.add_argument("--mode", choices=["real", "synthetic", "mixed"], default="mixed")
    p.add_argument("--stop", action="store_true", help="stop at the first game that fails")
    p.add_argument("--coverage", action="store_true", help="print what the games exercised")
    args = p.parse_args()
    t0, jobs = time.time(), [(args.seed * 1_000_000 + k, args.mode, k) for k in range(args.games)]
    failed, steps, stats = 0, 0, Counter()
    with Pool(args.jobs) as pool:
        for seed, k, bad, n, st in pool.imap_unordered(_job, jobs, chunksize=8):
            steps += max(n, 0)
            stats.update(st)
            if bad:
                failed += 1
                print(f"FAIL seed {seed} (game {k}): {bad}")
                if args.stop:
                    pool.terminate()
                    break
    if args.coverage:
        for name, n in sorted(stats.items()):
            print(f"{n:>11}  {name}")
    print(f"=== {args.mode}: {args.games - failed}/{args.games} games pass, {steps} actions checked, {time.time() - t0:.0f}s")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
