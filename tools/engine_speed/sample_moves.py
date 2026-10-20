"""A sampling profile of the Expert's first eight moves (no per-call overhead, unlike cProfile, which inflated the small
functions): a thread reads the main thread's stack every millisecond. Prints self time and inclusive time by function.   .venv/bin/python tools/engine_speed/sample_moves.py"""
import sys, threading, time, collections, os
from animal_kingdom.sim.runner import make_bot
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine.state import new_game
from animal_kingdom.engine import rules
EXPERT = "referee:depth=1,time_budget=0,den_sense=true,reply_turns=3,w.pending_target=1.5,w.buried_presence=0.25"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + "/"
self_c, incl_c, n = collections.Counter(), collections.Counter(), [0]
main = threading.main_thread().ident; stop = False
def sampler():
    while not stop:
        f = sys._current_frames().get(main)
        if f is not None:
            n[0] += 1; seen = set()
            key = lambda fr: f"{fr.f_code.co_filename.replace(ROOT, '').replace('/Users/martin/Work/fun/animal-kingdom/game/', '')}:{fr.f_code.co_name}"
            self_c[key(f)] += 1
            while f is not None:
                k = key(f)
                if k not in seen:
                    seen.add(k); incl_c[k] += 1
                f = f.f_back
        time.sleep(0.001)
bots = {"A": make_bot(EXPERT, 1), "B": make_bot("turn", 2)}
state = new_game(list(load_premade_deck("cats")), list(load_premade_deck("fish")), 11, map_id="map_b")
th = threading.Thread(target=sampler, daemon=True); th.start()
moves = 0; t0 = time.perf_counter()
while moves < 8 and state.result is None:
    p = state.player_to_act(); legal = rules.legal_actions(state)
    act = bots[p].choose(state.view_for(p), legal, state)
    if p == "A": moves += 1
    rules.apply_action(state, act)
stop = True; th.join(); total = n[0]
print(f"{time.perf_counter() - t0:.1f}s, {total} samples")
print("-- self time"); [print(f"{100*c/total:5.1f}%  {k}") for k, c in self_c.most_common(22)]
print("-- inclusive"); [print(f"{100*c/total:5.1f}%  {k}") for k, c in incl_c.most_common(28)]
