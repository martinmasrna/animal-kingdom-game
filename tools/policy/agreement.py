"""How often the Expert agrees with itself: the same decision positions searched under three seeds. The ceiling for any
net trained on its choices. Usage: agreement.py N_POSITIONS LOG.jsonl [...]"""
import json, os, random, sys
os.environ["AK_RUST_BOTS"] = "1"
from animal_kingdom.engine import rules
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game
from animal_kingdom.sim.runner import make_bot
from animal_kingdom.web.match import EXPERT
sys.path.insert(0, os.path.dirname(__file__))
from extract import lists_of
from animal_kingdom.engine.cards import load_cards
KNOWN = set(load_cards())

n_want, files = int(sys.argv[1]), sys.argv[2:]
rng = random.Random(3)
spots = []
for f in files:
    for line in open(f):
        if not line.strip():
            continue
        g = json.loads(line)
        if "human" not in (g.get("bots") or []):
            continue
        try:
            a, b = lists_of(g)
            if not set(a + b) <= KNOWN:
                continue
            st = new_game(a, b, g["seed"], map_id=g.get("map_id", "map_b"), config=Config.default().for_log(g), first_player=g["first_player"])
        except Exception:
            continue
        k = 0
        for act in g["actions"]:
            if st.pending is None and st.actions_taken_this_turn == 0 and st.turn_counter >= 4 and rules.is_terminal(st) is None:
                if len(rules.legal_actions(st)) >= 8:
                    spots.append(st.clone())
            try:
                rules.apply_logged(st, act)
            except Exception:
                break
rng.shuffle(spots); spots = spots[:n_want]
spec = EXPERT.replace("time_budget=8", "time_budget=0")
bots = [make_bot(spec, s) for s in (0, 1, 2)]
agree, n, legal_sum = 0, 0, 0
for st in spots:
    me = st.player_to_act()
    legal = rules.legal_actions(st)
    picks = [json.dumps(b.choose(st.view_for(me), legal, st).to_dict(), sort_keys=True) for b in bots]
    agree += (picks[0] == picks[1]) + (picks[0] == picks[2]) + (picks[1] == picks[2])
    n += 3; legal_sum += len(rules.legal_actions(st))
    if n % 60 == 0:
        print(n // 3, "positions, pairwise agreement", round(agree / n, 3), flush=True)
print("DONE", len(spots), "positions, pairwise agreement", round(agree / n, 3), "mean legal", round(legal_sum / len(spots), 1))
