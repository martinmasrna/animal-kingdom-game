"""Turn-start positions out of game logs, as the raw-position network sees them, from both seats.

Usage: raw_extract.py OUT.npz LOG.jsonl [LOG.jsonl ...] [--afterstates K]

With --afterstates K, every turn start also yields K afterstates reached by random whole turns from it (random legal
actions until the turn passes), read from both seats and labelled by the same outcome: the positions a search visits
are mostly ones reached by moves nobody would play, and a network trained on logged positions alone has never seen
them (`kind` 1; a logged turn start is `kind` 0).

Every turn start after the mulligan (a quiet position, the mover with all its actions) gives two rows, one from each
seat: the raw position (`bots.raw_position`), today's board_live description vector for the like-for-like comparison,
and the labels: whether this seat won the game, and whether this seat loses its den within three turns. A log names
its decks (self-play: `AK_EXTRA_DECKS` holds them) or carries their lists (web games). A game that stops replaying on
today's cards contributes the rows before the break.
"""
import json, os, random, sys, time
import numpy as np
from animal_kingdom.engine import rules
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game, other_player
from animal_kingdom.bots import features as F
from animal_kingdom.bots import raw_position as R

sys.path.insert(0, os.path.dirname(__file__))
from extract import lists_of  # noqa: E402


def random_turn(st, rng, mover):
    """A copy of `st` after a random whole turn by `mover`, or None if the game ended or the turn did not close."""
    s = st.clone()
    for _ in range(12):
        if rules.is_terminal(s) is not None:
            return None
        if s.pending is None and s.player_to_act() != mover:
            return s if not s.effect_stack else None
        legal = rules.legal_actions(s)
        if not legal:
            return None
        rules.apply_action(s, rng.choice(legal))
    return None


def rows_of(g, afterstates=0):
    rng = random.Random(g["seed"])
    try:
        a_list, b_list = lists_of(g)
        st = new_game(a_list, b_list, g["seed"], map_id=g.get("map_id", "map_b"),
                      config=Config.default().for_log(g), first_player=g["first_player"])
    except Exception:
        return
    bots = g.get("bots") or ["?", "?"]
    for a in g["actions"]:
        if rules.is_terminal(st) is not None:
            break
        try:
            if st.pending is None and not st.effect_stack and st.actions_taken_this_turn == 0 and st.turn_counter >= 1:
                mover = st.player_to_act()
                for me in ("A", "B"):
                    opp = other_player(me)
                    raw = R.extract(st, me)
                    desc = F.extract(st, me, "board_live")
                    y_win = float(g["winner"] == me)
                    y_den3 = float(g["winner"] == opp and g["reason"] == "hq_capture" and g["turns"] - st.turn_counter <= 3)
                    yield raw, desc, y_win, y_den3, st.turn_counter, me == mover, bots[0 if me == "A" else 1], 0
                for _ in range(afterstates):
                    after = random_turn(st, rng, mover)
                    if after is None:
                        continue
                    for me in ("A", "B"):
                        opp = other_player(me)
                        y_win = float(g["winner"] == me)
                        y_den3 = float(g["winner"] == opp and g["reason"] == "hq_capture" and g["turns"] - st.turn_counter <= 3)
                        yield R.extract(after, me), F.extract(after, me, "board_live"), y_win, y_den3, st.turn_counter, me == after.player_to_act(), bots[0 if me == "A" else 1], 1
            rules.apply_logged(st, a)
        except Exception:
            break


def main():
    args = sys.argv[1:]
    afterstates = 0
    if "--afterstates" in args:
        i = args.index("--afterstates"); afterstates = int(args[i + 1]); del args[i:i + 2]
    no_desc = "--no-desc" in args
    if no_desc:
        args.remove("--no-desc")
    out, files = args[0], args[1:]
    chunks = {k: [] for k in ("cr_card", "cr_owner", "top_num", "under_num", "globals", "desc", "y_win", "y_den3", "turn", "game", "mover", "seat_bot", "kind")}
    bag_idx = {b: [] for b in R.BAGS}; bag_w = {b: [] for b in R.BAGS}; bag_len = {b: [] for b in R.BAGS}
    games = 0; rows = 0; t0 = time.time(); seat_names = {}
    for f in files:
        for line in open(f):
            if not line.strip():
                continue
            g = json.loads(line)
            if g.get("winner") is None:
                continue
            loc = {k: [] for k in chunks}
            for raw, d, yw, yd, t, is_mover, bot, k in rows_of(g, afterstates):
                loc["cr_card"].append(raw["cr_card"]); loc["cr_owner"].append(raw["cr_owner"]); loc["top_num"].append(raw["top_num"])
                loc["under_num"].append(raw["under_num"]); loc["globals"].append(raw["globals"]); loc["desc"].append([] if no_desc else d)
                loc["y_win"].append(yw); loc["y_den3"].append(yd); loc["turn"].append(t); loc["game"].append(games); loc["mover"].append(is_mover); loc["kind"].append(k)
                loc["seat_bot"].append(seat_names.setdefault(bot, len(seat_names)))
                for b in R.BAGS:
                    bag_idx[b].append(np.array([i for i, _ in raw["bags"][b]], dtype=np.int16)); bag_w[b].append(np.array([w for _, w in raw["bags"][b]], dtype=np.float16))
                    bag_len[b].append(len(raw["bags"][b]))
            if loc["y_win"]:
                dt = {"cr_card": np.int16, "cr_owner": np.int8, "top_num": np.float16, "under_num": np.float16, "globals": np.float16, "desc": np.float16,
                      "y_win": np.float32, "y_den3": np.float32, "turn": np.int16, "game": np.int32, "mover": bool, "seat_bot": np.int16, "kind": np.int8}
                for k in chunks:
                    chunks[k].append(np.array(loc[k], dtype=dt[k]).reshape(len(loc[k]), -1) if k == "desc" else np.array(loc[k], dtype=dt[k]))
                rows += len(loc["y_win"])
            games += 1
            if games % 500 == 0:
                print(f"{games} games {rows} rows {time.time() - t0:.0f}s", flush=True)
    cat = lambda k: np.concatenate(chunks[k]) if chunks[k] else np.zeros(0)
    arrays = {k: cat(k) for k in chunks}
    arrays.update({ "seat_bot_names": np.array(sorted(seat_names, key=seat_names.get)),
        "desc_names": np.array(F.feature_names("board_live")), "globals_names": np.array(R.GLOBALS),
        "top_num_names": np.array(R.TOP_NUM), "under_num_names": np.array(R.UNDER_NUM), "bags": np.array(R.BAGS),
        "cards": np.array(sorted(__import__("animal_kingdom.engine.cards", fromlist=["load_cards"]).load_cards())),
    })
    for b in R.BAGS:
        arrays[f"bag_{b}_idx"] = np.concatenate(bag_idx[b]) if bag_idx[b] else np.zeros(0, dtype=np.int16)
        arrays[f"bag_{b}_w"] = np.concatenate(bag_w[b]) if bag_w[b] else np.zeros(0, dtype=np.float16)
        arrays[f"bag_{b}_off"] = np.concatenate([[0], np.cumsum(bag_len[b])]).astype(np.int64)
    np.savez_compressed(out, **arrays)
    print(f"games {games} rows {rows} -> {out} ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
