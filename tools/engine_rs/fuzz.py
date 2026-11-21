"""The parity fuzz: random games played through the Python engine and the Rust engine at once, a random legal action each
step chosen by one shared stream, everything a player or a bot can read compared after every action (common.compare).
The Rust engine is the same game when every game agrees.

    .venv/bin/python tools/engine_rs/fuzz.py [--games 500] [--seed 0] [--jobs 6] [--mode real|synthetic|mixed] [--stop]

What a game covers: 25-card decks over every card the table holds (the collectible ones, and the Spore token as a card in
hand), a leader for most decks; ending the turn wherever it is legal, not only when nothing else is; both players'
mulligans, in turn and at once (a choice "by" the player not being asked); a position saved by one engine and loaded by
the other, mid-game and mid-choice; an illegal action refused by both. `--mode synthetic` adds cards no deck holds yet,
for the rules no card uses today (Armor, Stealth, Poison, a strength that is a count, a 0-strength body), and plays some
games under a config with tight caps, a small hand limit or no mulligan, so the turn caps and the burn are reached.
"""
import argparse, copy, random, sys, time
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import RAW_CARDS, compare, engines

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, PassAction, PlaceAction
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.leaders import LEADERS
from animal_kingdom.engine.state import GameState, new_game

DECK_SIZE = 25
COPIES = {"common": 2, "legendary": 1}


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
    """(pool of card ids, cards, config, Rust engine) for game `k` of a run."""
    synthetic = mode == "synthetic" or (mode == "mixed" and k % 2 == 1)
    over = CONFIGS[(k // 2) % len(CONFIGS)] if synthetic else {}
    key = (synthetic, tuple(sorted(over.items())))
    if key not in _cache:
        cards, config, eng = engines(synthetic_cards() if synthetic else None, Config().sweep(**over))
        _cache[key] = (sorted(cards), cards, config, eng)
    return _cache[key]


def random_deck(rng, pool, cards, heavy):
    """25 cards within the copy limits; `heavy` cards (the ones under test) come up three times as often."""
    deck, weights = [], [3 if c in heavy else 1 for c in pool]
    while len(deck) < DECK_SIZE:
        c = rng.choices(pool, weights)[0]
        if deck.count(c) < COPIES[cards[c].rarity]:
            deck.append(c)
    lead = None
    if rng.random() < 0.9:
        lead = rng.choice(sorted(LEADERS))
        if lead not in deck:
            deck[rng.randrange(len(deck))] = lead
    return deck, lead


def illegal_action(rng, py, pool, legal):
    """Some action that is not legal now."""
    tiles = sorted(py.game_map.crossroads)
    for _ in range(20):
        a = rng.choice([PlaceAction(rng.choice(pool), ("cr", rng.choice(tiles))), PlaceAction(rng.choice(pool), ("hq", rng.choice("AB"))),
                        ChoiceAction(rng.choice(tiles)), ChoiceAction(rng.randrange(60)), ChoiceAction(SKIP), ChoiceAction("deck:1")])
        if a not in legal:
            return a
    return None


def play(seed, mode, k, max_steps=1500):
    pool, cards, config, eng = setup(mode, k)
    rng = random.Random(seed)
    heavy = {c for c in pool if c.startswith("t_")} | {"spore"}
    (deck_a, lead_a), (deck_b, lead_b) = random_deck(rng, pool, cards, heavy), random_deck(rng, pool, cards, heavy)
    leaders = {"A": lead_a, "B": lead_b}
    game_seed = rng.choice([seed, rng.getrandbits(32), rng.getrandbits(64), rng.getrandbits(100), -rng.getrandbits(40), 0])
    first = rng.choice([None, None, "A", "B"])
    pass_rate = rng.choice([0.02, 0.1, 0.3])
    py = new_game(list(deck_a), list(deck_b), game_seed, cards=cards, config=config, first_player=first, leaders=leaders)
    rs = eng.new_game(list(deck_a), list(deck_b), game_seed, first, leaders)
    rs.record_events(True)
    steps, stats = 0, Counter()
    bad = compare(py, rs, "setup", stats=stats)
    while bad is None and rules.is_terminal(py) is None and steps < max_steps:
        legal = rules.legal_actions(py)
        if not legal:
            return f"no legal actions but not terminal at step {steps}", steps, stats
        r = rng.random()
        if r < 0.02:        # an illegal action: both refuse it, and neither position moves
            a = illegal_action(rng, py, pool, legal)
            if a is not None:
                refused = []
                for name, call in (("python", lambda: rules.apply_action(py, a)), ("rust", lambda: rs.apply_action(a.to_dict()))):
                    try:
                        call()
                        return f"{name} accepted the illegal {a.to_dict()} at step {steps}", steps, stats
                    except Exception as e:
                        refused.append(e)
                stats["illegal actions refused by both"] += 1
                bad = compare(py, rs, f"the refused {a.to_dict()}", stats=stats)
                continue
        if r < 0.05:        # the position saved by each engine and loaded by the other
            rs2 = eng.from_dict(py.to_dict())
            py2 = GameState.from_dict(rs.to_dict(), cards=cards, config=config)
            rs2.record_events(True)
            bad = compare(py2, rs2, f"a save and load at step {steps}")
            if bad:
                break
            stats["saves loaded by the other engine" + (", mid-choice" if py.pending else "")] += 1
            if rng.random() < 0.5:
                py, rs = py2, rs2
            else:
                py, rs = py.clone(), rs.clone()
        other = "B" if py.player_to_act() == "A" else "A"
        early = rules.early_mulligan(py, other) is not None
        if early != (rs.early_mulligan(other) is not None):
            return f"early mulligan differs at step {steps}", steps, stats
        if early and rng.random() < 0.5:      # the player not being asked chooses their mulligan first
            choice = rng.choice([u.iid for u in py.hands[other]] + [SKIP])
            adict = {"kind": "choice", "choice": choice, "by": other}
            try:
                rules.apply_logged(py, adict)
            except Exception as e:
                return f"python raised at step {steps} on {adict}: {e!r}", steps, stats
            try:
                rs.apply_logged(adict)
            except Exception as e:
                return f"rust refused step {steps} {adict}: {e}", steps, stats
            stats["mulligan choices made out of turn"] += 1
        else:
            if rules.can_pass(py) and rng.random() < pass_rate:
                action = PassAction()
            else:
                action = legal[rng.randrange(len(legal))]
            adict = action.to_dict()
            validate = rng.random() < 0.7
            try:
                rules.apply_action(py, action, validate=validate)
            except Exception as e:
                return f"python raised at step {steps} on {adict}: {e!r}", steps, stats
            try:
                rs.apply_action(adict, validate)
            except Exception as e:
                return f"rust refused step {steps} {adict}: {e}", steps, stats
            if adict["kind"] == "pass" and len(legal) > 1 or adict["kind"] == "pass" and legal[0].kind != "pass":
                stats["turns ended with plays still legal"] += 1
        steps += 1
        bad = compare(py, rs, f"step {steps} {adict}", stats=stats)
    res = rules.is_terminal(py)
    stats["games ended by " + (res.reason if res else "the step limit")] += 1
    for c in py.caps:
        stats["turns ended by the cap on " + c["cap"]] += 1
    stats["turns"] += py.turn_counter
    return bad, steps, stats


def run(args):
    seed, mode, k = args
    try:
        out = play(seed, mode, k)
    except Exception as e:
        import traceback
        out = (f"exception {type(e).__name__}: {e}\n{traceback.format_exc()}", 0, Counter())
    return (seed, k) + tuple(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--mode", choices=["real", "synthetic", "mixed"], default="mixed")
    ap.add_argument("--stop", action="store_true", help="stop at the first game that differs")
    ap.add_argument("--coverage", action="store_true", help="print what the games exercised: events, choices, saves, caps")
    a = ap.parse_args()
    jobs = [(a.seed * 1_000_000 + k, a.mode, k) for k in range(a.games)]
    ap_stats = Counter()
    t0, fails, actions = time.time(), 0, 0
    with Pool(a.jobs) as pool:
        for seed, k, bad, steps, stats in (pool.imap_unordered(run, jobs, chunksize=4) if a.jobs > 1 else map(run, jobs)):
            actions += steps
            ap_stats.update(stats)
            if bad:
                fails += 1
                print(f"FAIL seed {seed} (game {k}) after {steps} steps: {bad}"[:1500], flush=True)
                if a.stop:
                    pool.terminate()
                    break
    if a.coverage:
        for key, n in sorted(ap_stats.items()):
            print(f"  {n:>9}  {key}")
    print(f"=== {a.mode}: {a.games - fails}/{a.games} games agree, {actions} actions compared over {ap_stats['turns']} turns, {time.time() - t0:.0f}s", flush=True)
    sys.exit(1 if fails else 0)
