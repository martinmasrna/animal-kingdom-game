"""Rank a saved position with the whole-turn search on the Rust engine, under given search settings: time and the top
turns. Usage: rank_pos.py POSITION.json "extra=settings,..." [SEED]
Settings are the atomic bot's spec keys (rounds, width1, width2, inner, draws, beam, cand=<net json>, hands, ...)."""
import json, os, sys, time
os.environ["AK_RUST_BOTS"] = "1"
from animal_kingdom.engine.state import GameState
from animal_kingdom.sim.runner import make_bot
from animal_kingdom.web.analyse import texts
from animal_kingdom.web.match import EXPERT


def rank(state, extra, seed=0):
    spec = EXPERT.replace("referee_learned", "atomic_learned").replace("time_budget=8", "time_budget=0")
    if extra:
        spec += "," + extra
    bot = make_bot(spec, seed)
    t = time.time()
    rows = bot.ranking(state)
    return rows, time.time() - t


if __name__ == "__main__":
    st = GameState.from_dict(json.load(open(sys.argv[1])))
    extra = sys.argv[2] if len(sys.argv) > 2 else ""
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    rows, secs = rank(st, extra, seed)
    me = st.player_to_act()
    print(f"{os.path.basename(sys.argv[1])} [{extra}] {secs:.1f} s, {len(rows)} turns")
    for r in rows[:5]:
        lv = r.get("levels") or []
        print("  ", " ".join(f"{v:7.1f}" if v is not None else "      -" for v in ([r.get("board", 0.0)] + lv)), "·", " · ".join(texts(st, r["turn"]))[:110])
