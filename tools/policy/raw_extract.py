"""Turn-start positions out of game logs, as the raw-position network sees them, from both seats.

Usage: raw_extract.py OUT.npz LOG.jsonl [LOG.jsonl ...]

Every turn start after the mulligan (a quiet position, the mover with all its actions) gives two rows, one from each
seat: the raw position (`bots.raw_position`), today's board_live description vector for the like-for-like comparison,
and the labels: whether this seat won the game, and whether this seat loses its den within three turns. A log names
its decks (self-play: `AK_EXTRA_DECKS` holds them) or carries their lists (web games). A game that stops replaying on
today's cards contributes the rows before the break.
"""
import json, os, sys, time
import numpy as np
from animal_kingdom.engine import rules
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game, other_player
from animal_kingdom.bots import features as F
from animal_kingdom.bots import raw_position as R

sys.path.insert(0, os.path.dirname(__file__))
from extract import lists_of  # noqa: E402


def rows_of(g):
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
                    yield raw, desc, y_win, y_den3, st.turn_counter, me == mover, bots[0 if me == "A" else 1]
            rules.apply_logged(st, a)
        except Exception:
            break


def main():
    out, files = sys.argv[1], sys.argv[2:]
    cr_card, cr_owner, top_num, under_num, glob, desc = [], [], [], [], [], []
    y_win, y_den3, turn, game, mover, seat_bot, deck_me, deck_opp = [], [], [], [], [], [], [], []
    bag_idx = {b: [] for b in R.BAGS}; bag_w = {b: [] for b in R.BAGS}; bag_off = {b: [0] for b in R.BAGS}
    games = 0; t0 = time.time(); seat_names = {}
    for f in files:
        for line in open(f):
            if not line.strip():
                continue
            g = json.loads(line)
            if g.get("winner") is None:
                continue
            n0 = len(y_win)
            for raw, d, yw, yd, t, is_mover, bot in rows_of(g):
                cr_card.append(raw["cr_card"]); cr_owner.append(raw["cr_owner"]); top_num.append(raw["top_num"])
                under_num.append(raw["under_num"]); glob.append(raw["globals"]); desc.append(d)
                y_win.append(yw); y_den3.append(yd); turn.append(t); game.append(games); mover.append(is_mover)
                seat_bot.append(seat_names.setdefault(bot, len(seat_names)))
                for b in R.BAGS:
                    for i, w in raw["bags"][b]:
                        bag_idx[b].append(i); bag_w[b].append(w)
                    bag_off[b].append(len(bag_idx[b]))
            games += 1
            if games % 500 == 0:
                print(f"{games} games {len(y_win)} rows {time.time() - t0:.0f}s", flush=True)
    arrays = {
        "cr_card": np.array(cr_card, dtype=np.int16), "cr_owner": np.array(cr_owner, dtype=np.int8),
        "top_num": np.array(top_num, dtype=np.float16), "under_num": np.array(under_num, dtype=np.float16),
        "globals": np.array(glob, dtype=np.float16), "desc": np.array(desc, dtype=np.float16),
        "y_win": np.array(y_win, dtype=np.float32), "y_den3": np.array(y_den3, dtype=np.float32),
        "turn": np.array(turn, dtype=np.int16), "game": np.array(game, dtype=np.int32), "mover": np.array(mover, dtype=bool),
        "seat_bot": np.array(seat_bot, dtype=np.int16), "seat_bot_names": np.array(sorted(seat_names, key=seat_names.get)),
        "desc_names": np.array(F.feature_names("board_live")), "globals_names": np.array(R.GLOBALS),
        "top_num_names": np.array(R.TOP_NUM), "under_num_names": np.array(R.UNDER_NUM), "bags": np.array(R.BAGS),
        "cards": np.array(sorted(__import__("animal_kingdom.engine.cards", fromlist=["load_cards"]).load_cards())),
    }
    for b in R.BAGS:
        arrays[f"bag_{b}_idx"] = np.array(bag_idx[b], dtype=np.int16)
        arrays[f"bag_{b}_w"] = np.array(bag_w[b], dtype=np.float16)
        arrays[f"bag_{b}_off"] = np.array(bag_off[b], dtype=np.int64)
    np.savez_compressed(out, **arrays)
    print(f"games {games} rows {len(y_win)} -> {out} ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
