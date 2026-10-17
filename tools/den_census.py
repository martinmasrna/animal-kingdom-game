"""Tactical census of the human games the Expert lost: facts the engine verifies by exhaustion, no judgment.

For every logged human-vs-Expert game the bot lost, at the start of each bot turn:
  threatened   the human could capture the bot's den within two actions had the bot passed;
  defensible   some two-action turn of the bot's removed every such capture;
  allowed      the bot's actual turn left a two-action capture standing (the game then usually ended there);
  missed_own   the bot could capture the human's den within two actions and did not capture this turn.
Writes results/census/den_census.json: the counts, and every flagged position (state dict, game, turn, what the bot
played) so the positions can be replayed by other bots and turned into puzzles.
"""
import glob, json, sys, time, collections
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import ChoiceAction, SKIP, PassAction
from animal_kingdom.engine.state import new_game
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.cards import load_cards

CARDS = load_cards()

def captures_in_two(state, who):
    if state.player_to_act() != who or state.pending is not None:
        return False
    for a1 in rules.legal_actions(state):
        if getattr(a1, "is_hq_capture", False):
            return True
        s1 = state.clone()
        try: rules.apply_action(s1, a1, validate=False)
        except Exception: continue
        if s1.player_to_act() == who and s1.pending is None and \
           any(getattr(a2, "is_hq_capture", False) for a2 in rules.legal_actions(s1)):
            return True
    return False

def end_turn(state, me):
    guard = 0
    while state.player_to_act() == me and rules.is_terminal(state) is None and guard < 6:
        guard += 1
        if state.pending is not None:
            legal = rules.legal_actions(state)
            if not legal: break
            rules.apply_action(state, legal[0], validate=False)   # a pending choice: first option
        else:
            try: rules.apply_action(state, PassAction(), validate=False)
            except Exception: break
    return state

def threatened_if_passed(state, bot, human):
    s = end_turn(state.clone(), bot)
    return rules.is_terminal(s) is None and captures_in_two(s, human)

def defensible(state, bot, human, limit=400):
    """Some two-action turn of the bot after which the human has no two-action capture."""
    tried = 0
    for a1 in rules.legal_actions(state):
        s1 = state.clone()
        try: rules.apply_action(s1, a1, validate=False)
        except Exception: continue
        if rules.is_terminal(s1) is not None: return True   # the bot wins outright
        seconds = rules.legal_actions(s1) if (s1.player_to_act() == bot and s1.pending is None) else [None]
        for a2 in seconds:
            s2 = s1.clone()
            if a2 is not None:
                try: rules.apply_action(s2, a2, validate=False)
                except Exception: continue
            if rules.is_terminal(s2) is not None: return True
            end_turn(s2, bot)
            tried += 1
            if rules.is_terminal(s2) is None and not captures_in_two(s2, human): return True
            if tried >= limit: return None   # too wide to settle cheaply
    return False

def main():
    files = sorted(glob.glob("results/human_games/**/*.jsonl", recursive=True))
    counts = collections.Counter(); flagged = []; t0 = time.time(); games = 0
    for f in files:
        for line in open(f):
            try: g = json.loads(line)
            except Exception: continue
            bots = tuple(g.get("bots", []))
            if "expert" not in bots or "human" not in bots: continue
            bot = "A" if bots[0] == "expert" else "B"; human = "B" if bot == "A" else "A"
            if g.get("winner") == bot: continue
            lists = g.get("lists")
            if not lists or not all(c in CARDS for l in lists for c in l): counts["skipped_unknown_cards"] += 1; continue
            try:
                state = new_game(list(lists[0]), list(lists[1]), g["seed"], map_id=g.get("map_id", "map_b"),
                                 config=Config.default().for_log(g), first_player=g["first_player"])
            except Exception: counts["skipped_setup"] += 1; continue
            games += 1; ok = True; turn_facts = []
            actions = g["actions"]; i = 0
            while i < len(actions):
                adict = actions[i]
                while state.pending is not None and state.effect_stack[-1].get("op") == "mulligan" and adict["kind"] != "choice":
                    rules.apply_action(state, ChoiceAction(SKIP))
                if state.player_to_act() == bot and state.pending is None and state.actions_taken_this_turn == 0 and rules.is_terminal(state) is None:
                    before = state.clone()
                    own = captures_in_two(state, bot)
                    thr = threatened_if_passed(state, bot, human)
                    # play the bot's whole turn from the log
                    played = []
                    while i < len(actions) and state.player_to_act() == bot and rules.is_terminal(state) is None:
                        try: rules.apply_logged(state, actions[i])
                        except Exception: ok = False; break
                        played.append(actions[i]); i += 1
                    if not ok: break
                    captured = rules.is_terminal(state) is not None and state.result is not None and getattr(state.result, "winner", None) == bot
                    fact = {"game": g.get("id") or f.rsplit("/", 1)[-1], "seed": g["seed"], "turn": before.turn_counter, "played": played}
                    if own and not captured and rules.is_terminal(state) is None:
                        counts["missed_own_capture"] += 1; fact["kind"] = "missed_own_capture"; fact["state"] = before.to_dict(); flagged.append(dict(fact))
                    if thr:
                        counts["threatened"] += 1
                        d = defensible(before, bot, human)
                        counts["defensible" if d else ("defensible_unsettled" if d is None else "indefensible")] += 1
                        allowed = rules.is_terminal(state) is None and captures_in_two(state, human)
                        if allowed and d:
                            counts["allowed_with_defence"] += 1
                            fact["kind"] = "allowed_with_defence"; fact["state"] = before.to_dict(); flagged.append(dict(fact))
                    continue
                try: rules.apply_logged(state, adict)
                except Exception: ok = False; break
                i += 1
            counts["games_replayed" if ok else "games_replay_broke"] += 1
            if games % 50 == 0:
                print(f"{games} games, {time.time()-t0:.0f}s, {dict(counts)}", flush=True)
    json.dump({"counts": counts, "flagged": flagged}, open("results/census/den_census.json", "w"))
    print("done", dict(counts), "flagged", len(flagged), f"{time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
