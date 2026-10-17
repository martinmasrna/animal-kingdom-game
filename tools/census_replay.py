"""Replay the census's flagged positions (tools/den_census.py) with today's Expert and the candidate: does each bot's
turn still leave the human a two-action den capture? Writes results/census/replay.json."""
import json, sys, time
from animal_kingdom.engine import rules
from animal_kingdom.engine.state import GameState
from animal_kingdom.sim.runner import make_bot
sys.path.insert(0, "tools"); from den_census import captures_in_two, end_turn
CANDIDATE = {"depth": 1, "w.pending_target": 1.5, "w.buried_presence": 0.25, "den_sense": True, "reply_turns": 3, "time_budget": 8.0}
data = json.load(open("results/census/den_census.json"))
out = []
for f in data["flagged"]:
    row = {k: f[k] for k in ("game", "turn", "kind", "played")}
    for name, extra in (("today", {}), ("candidate", CANDIDATE)):
        s = GameState.from_dict(json.loads(json.dumps(f["state"]))); bot_seat = s.player_to_act(); human = "B" if bot_seat == "A" else "A"
        bot = make_bot("referee", 1, extra=dict(extra)); turn = []; t0 = time.time()
        while s.result is None and s.current == bot_seat and len(turn) < 6:
            a = bot.choose(s.view_for(bot_seat), rules.legal_actions(s), s); turn.append(str(a)[:60]); rules.apply_action(s, a)
        won = s.result is not None and getattr(s.result, "winner", None) == bot_seat
        still = (not won) and rules.is_terminal(s) is None and captures_in_two(s, human)
        row[name] = {"turn": turn, "allows_capture": still, "captured": won, "secs": round(time.time() - t0, 1)}
    out.append(row); print(row["game"], row["turn"], row["kind"], "today allows:", row["today"]["allows_capture"], "| candidate allows:", row["candidate"]["allows_capture"], flush=True)
json.dump(out, open("results/census/replay.json", "w"), indent=1)
n = len(out); print("positions", n, "| today allows", sum(r["today"]["allows_capture"] for r in out), "| candidate allows", sum(r["candidate"]["allows_capture"] for r in out))
