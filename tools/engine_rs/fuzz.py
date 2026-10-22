"""Fuzz oracle: random games played through both engines at once, a random legal action each step chosen by one shared
stream, the position and the legal actions compared after every action. Random 30-card decks over every collectible
card reach the effects no logged game does.

    .venv/bin/python tools/engine_rs/fuzz.py [--games 200] [--seed 0] [--pass-rate 0.03] [--all-cards]
"""
import argparse, dataclasses, json, random, sys, time

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import PassAction, action_from_dict
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.resources import load_bundled_json
from animal_kingdom.engine.state import new_game
import ak_engine

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from oracle import canon, diff_keys, CARDS_JSON, MAPS_JSON


def random_deck(rng, pool, cards):
    """30 cards within the copy limits (legendary 1 / rare 2 / common 3)."""
    limits = {"common": 3, "rare": 2, "legendary": 1}
    deck = []
    tries = 0
    while len(deck) < 30 and tries < 10000:
        tries += 1
        c = rng.choice(pool)
        if deck.count(c) < limits.get(cards[c].rarity, 3):
            deck.append(c)
    return deck


def play(seed, pool, cards, config, eng, pass_rate):
    rng = random.Random(seed)
    deck_a, deck_b = random_deck(rng, pool, cards), random_deck(rng, pool, cards)
    py = new_game(list(deck_a), list(deck_b), seed, map_id="map_b", config=config)
    rs = eng.new_game(list(deck_a), list(deck_b), seed, None, False)
    rs.set_record_events(False)
    steps = 0

    def check(label):
        a, b = py.to_dict(), rs.to_dict()
        if canon(a) != canon(b):
            return f"state differs after {label}: " + "; ".join(f"{p}: py={x!r} rs={y!r}" for p, x, y in diff_keys(a, b))
        la = [x.to_dict() for x in rules.legal_actions(py)]
        lb = rs.legal_actions()
        if [canon(x) for x in la] != [canon(x) for x in lb]:
            sa, sb = {canon(x) for x in la}, {canon(x) for x in lb}
            if sa == sb:
                return f"legal action ORDER differs after {label}: py={la[:5]} rs={lb[:5]}"
            return f"legal actions differ after {label}: only py={[json.loads(x) for x in sorted(sa - sb)][:5]} only rs={[json.loads(x) for x in sorted(sb - sa)][:5]}"
        return None

    bad = check("setup")
    if bad:
        return bad, steps, deck_a, deck_b
    while rules.is_terminal(py) is None and steps < 600:
        legal = rules.legal_actions(py)
        if not legal:
            return f"no legal actions but not terminal at step {steps}", steps, deck_a, deck_b
        if rules.can_pass(py) and py.actions_taken_this_turn > 0 and rng.random() < pass_rate:
            action = PassAction()
        else:
            action = legal[rng.randrange(len(legal))]
        adict = action.to_dict()
        try:
            rules.apply_action(py, action)
        except Exception as e:
            return f"python raised at step {steps} on {adict}: {e}", steps, deck_a, deck_b
        try:
            rs.apply_action(adict)
        except Exception as e:
            return f"rust refused step {steps} {adict}: {e}", steps, deck_a, deck_b
        steps += 1
        bad = check(f"step {steps} {adict}")
        if bad:
            return bad, steps, deck_a, deck_b
    ta, tb = rules.is_terminal(py), rs.is_terminal()
    ta = ta.to_dict() if ta else None
    if canon(ta) != canon(tb):
        return f"terminal differs: py={ta} rs={tb}", steps, deck_a, deck_b
    return None, steps, deck_a, deck_b


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--pass-rate", type=float, default=0.03)
    ap.add_argument("--all-cards", action="store_true", help="draw from every card, reserve and tokens included")
    ap.add_argument("--stop", action="store_true")
    a = ap.parse_args()
    cards = load_cards()
    pool = sorted(c for c, card in cards.items() if a.all_cards or card.collectible)
    config = Config.default()
    eng = ak_engine.Engine(CARDS_JSON, MAPS_JSON, json.dumps(dataclasses.asdict(config)), "map_b")
    t0 = time.time()
    fails = 0
    total_steps = 0
    for k in range(a.games):
        seed = a.seed * 100000 + k
        try:
            bad, steps, da, db = play(seed, pool, cards, config, eng, a.pass_rate)
        except Exception as e:
            bad, steps, da, db = f"exception {type(e).__name__}: {e}", 0, [], []
        total_steps += steps
        if bad:
            fails += 1
            print(f"FAIL seed {seed} after {steps} steps: {bad}"[:900], flush=True)
            if a.stop:
                break
    print(f"=== {a.games - fails}/{a.games} games agree, {total_steps} actions, {time.time() - t0:.0f}s", flush=True)
