"""The baselines the candidate network is measured against, on the same decisions: how often the taken action is in
the top 8 (and top 1) when the legal actions are ranked by the Expert's own evaluation of the position each one leads
to (prune-by-value, what the search does today), and by chance.

Usage: baseline.py {expert|human} LOG.jsonl [...] [--games N]  (expert logs need AK_EXTRA_DECKS as extract.py does)
"""
import json, os, sys, random
os.environ.setdefault("AK_PY_BOTS", "1")
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import action_from_dict
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game
from animal_kingdom.web.analyse import _expert
sys.path.insert(0, os.path.dirname(__file__))
from extract import lists_of, same

bot = _expert(0)


def value_after(st, me, a):
    s = st.clone()
    try:
        rules.apply_action(s, a, validate=False)
    except Exception:
        return -1e9
    # a choice may still be pending for me: the value of the half-resolved position, as the old search ranks it
    return bot._clamped_eval(s, me)


def run(mode, files, max_games):
    hits = {"top1": 0, "top8": 0, "chance8": 0.0, "n": 0, "wide_top8": 0, "wide_chance8": 0.0, "wide_n": 0}
    games = 0
    for f in files:
        for line in open(f):
            if not line.strip():
                continue
            g = json.loads(line)
            bots = g.get("bots") or []
            if mode == "human":
                if "human" not in bots:
                    continue
                seats = {"A" if bots[0] == "human" else "B"}
            else:
                seats = {"A", "B"}
            try:
                a_list, b_list = lists_of(g)
                st = new_game(a_list, b_list, g["seed"], map_id=g.get("map_id", "map_b"),
                              config=Config.default().for_log(g), first_player=g["first_player"])
            except Exception:
                continue
            games += 1
            for a in g["actions"]:
                if rules.is_terminal(st) is not None:
                    break
                me = st.player_to_act()
                act = action_from_dict(a)
                try:
                    if me in seats and not (st.pending and st.pending.get("kind") == "mulligan"):
                        legal = rules.legal_actions(st)
                        if len(legal) >= 2:
                            chosen = next((i for i, x in enumerate(legal) if same(x, act)), None)
                            if chosen is not None:
                                vals = [value_after(st, me, x) for x in legal]
                                order = sorted(range(len(legal)), key=lambda i: -vals[i])
                                rank = order.index(chosen)
                                hits["top1"] += rank < 1; hits["top8"] += rank < 8
                                hits["chance8"] += min(1.0, 8 / len(legal)); hits["n"] += 1
                                if len(legal) >= 12:
                                    hits["wide_top8"] += rank < 8; hits["wide_chance8"] += 8 / len(legal); hits["wide_n"] += 1
                    rules.apply_logged(st, a)
                except Exception:
                    break
            if games % 50 == 0:
                print(games, "games", hits["n"], "decisions", flush=True)
            if games >= max_games:
                break
        if games >= max_games:
            break
    n = hits["n"]; w = max(1, hits["wide_n"])
    print("DONE", mode, "games", games, "decisions", n, "top1", round(hits["top1"] / n, 3), "top8", round(hits["top8"] / n, 3),
          "chance8", round(hits["chance8"] / n, 3), "| wide n", hits["wide_n"], "top8", round(hits["wide_top8"] / w, 3),
          "chance8", round(hits["wide_chance8"] / w, 3))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mx = int(sys.argv[sys.argv.index("--games") + 1]) if "--games" in sys.argv else 10 ** 9
    run(args[0], args[1:], mx)
