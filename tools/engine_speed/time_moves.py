"""Time the Expert's first eight moves against Fish (Normal in the other seat), no profiler, and the moves it chose, to compare runs.   .venv/bin/python tools/engine_speed/time_moves.py"""
import time, sys, platform
from animal_kingdom.sim.runner import make_bot
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine.state import new_game
from animal_kingdom.engine import rules
EXPERT = "referee:depth=1,time_budget=0,den_sense=true,reply_turns=3,w.pending_target=1.5,w.buried_presence=0.25"
bots = {"A": make_bot(EXPERT, 1), "B": make_bot("turn", 2)}
state = new_game(list(load_premade_deck("cats")), list(load_premade_deck("fish")), 11, map_id="map_b")
moves = 0; t_exp = 0.0; per = []; acts = []
while moves < int(sys.argv[1] if len(sys.argv) > 1 else 8) and state.result is None:
    p = state.player_to_act(); legal = rules.legal_actions(state)
    t = time.perf_counter(); act = bots[p].choose(state.view_for(p), legal, state); dt = time.perf_counter() - t
    if p == "A":
        t_exp += dt; per.append(round(dt, 1)); moves += 1
    acts.append(str(act)); rules.apply_action(state, act)
print(f"{platform.python_implementation()} {platform.python_version()}: {moves} expert moves, {t_exp:.1f}s, per move {per}")
print("moves:", " | ".join(acts))
