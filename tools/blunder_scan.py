"""The candidate judging the Expert's play in the human games it lost: at every top-level decision the bot took, the
candidate (with its live time budget) searches the same position; where the move actually played scores well below the
candidate's best, or was not even among the moves it searched, the position is flagged. No human judgment: a list of
disagreements, ranked by gap, for Martin to look at. Writes results/census/blunders.json."""
import glob, json, time, sys
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ChoiceAction, SKIP, action_from_dict
from animal_kingdom.engine.state import new_game
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.sim.runner import make_bot
CARDS = load_cards()
CANDIDATE = {"depth": 1, "w.pending_target": 1.5, "w.buried_presence": 0.25, "den_sense": True, "reply_turns": 3, "time_budget": 8.0}
MAX_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 60

games = []
for f in sorted(glob.glob("results/human_games/**/*.jsonl", recursive=True)):
    for line in open(f):
        try: g = json.loads(line)
        except Exception: continue
        bots = tuple(g.get("bots", []))
        if "expert" not in bots or "human" not in bots: continue
        bot = "A" if bots[0] == "expert" else "B"
        if g.get("winner") == bot: continue
        lists = g.get("lists")
        if not lists or not all(c in CARDS for l in lists for c in l): continue
        games.append((g, bot, f))
games = games[-MAX_GAMES:]
print(len(games), "lost games to scan", flush=True)
flagged = []; decisions = 0; t0 = time.time()
for gi, (g, bot, f) in enumerate(games):
    human = "B" if bot == "A" else "A"
    try:
        state = new_game(list(g["lists"][0]), list(g["lists"][1]), g["seed"], map_id=g.get("map_id", "map_b"), config=Config.default().for_log(g), first_player=g["first_player"])
    except Exception: continue
    searcher = make_bot("referee", 1, extra=dict(CANDIDATE)); captured = {}
    orig = searcher._record_root_scores
    def rec(scores, captured=captured, orig=orig):
        captured["scores"] = list(scores); return orig(scores)
    searcher._record_root_scores = rec
    for i, adict in enumerate(g["actions"]):
        while state.pending is not None and state.effect_stack[-1].get("op") == "mulligan" and adict["kind"] != "choice":
            rules.apply_action(state, ChoiceAction(SKIP))
        if state.player_to_act() == bot and state.pending is None and rules.is_terminal(state) is None and adict["kind"] != "choice":
            legal = rules.legal_actions(state)
            if len(legal) > 1:
                captured.clear(); searcher._continuation_plan = {}
                before = state.clone()
                try: best = searcher.choose(state.view_for(bot), legal, state)
                except Exception as e: best = None
                scores = captured.get("scores") or []
                played = action_from_dict(adict)
                by = {a: sc for a, sc in scores}
                top = max(by.values()) if by else None
                if top is not None and best is not None and played != best:
                    gap = (top - by[played]) if played in by else None
                    flagged.append({"game": g.get("id") or f.rsplit("/", 1)[-1], "seed": g["seed"], "turn": before.turn_counter, "action_index": i,
                                    "played": adict, "candidate": str(best), "gap": gap, "top": top, "searched": played in by,
                                    "n_roots": len(by), "state": before.to_dict()})
                decisions += 1
        try: rules.apply_logged(state, adict)
        except Exception: break
    print(f"game {gi+1}/{len(games)}: {decisions} decisions, {len(flagged)} disagreements, {time.time()-t0:.0f}s", flush=True)
    json.dump({"decisions": decisions, "flagged": flagged}, open("results/census/blunders.json", "w"))
print("done", decisions, "decisions", len(flagged), "disagreements")
