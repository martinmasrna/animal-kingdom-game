"""Readable move-by-move transcript of logged web games, replayed through the engine, with the
player's live commentary interleaved at the moves it was spoken during.

python -m animal_kingdom.sim.transcript results/human_games/web/FILE.jsonl [FIRST_GAME_INDEX]"""
import json, sys
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, action_from_dict
from animal_kingdom.engine.state import new_game
from animal_kingdom.engine.strength import effective_strength
from animal_kingdom.sim.agent_play import board_view

ME = "A"

def board(st):
    return "\n".join("   " + line for line in board_view(st))


def conn(st, p):
    return sorted(st.connected_occupied(p))

def run(rec, idx):
    st = new_game(load_premade_deck(rec["deck_a"]), load_premade_deck(rec["deck_b"]), rec["seed"],
                  map_id=rec["map_id"], first_player=rec["first_player"])
    who = {"A": "MARTIN", "B": "BOT"}
    print(f"\n######## GAME {idx}: Martin {rec['deck_a']} vs bot {rec['deck_b']} | first: {who[rec['first_player']]} | result: {who.get(rec['winner'],'draw')} wins by {rec['reason']}")
    print("opening hands: Martin " + ", ".join(st.cards[u.card_id].name for u in st.hands['A']) + " | bot " + ", ".join(st.cards[u.card_id].name for u in st.hands['B']))
    last_round = None
    notes = {}
    for n in rec.get("notes", []):
        notes.setdefault(n["at"], []).append(n)
    def say(i):
        for n in notes.get(i, []):
            print(f"   >>> MARTIN SAYS [{n.get('t', '?')}s, round {n['round']}]: {n['text']}")
    for i, ad in enumerate(rec["actions"]):
        say(i)
        a = action_from_dict(ad)
        actor = st.player_to_act()
        rnd = st.turn_counter // 2 + 1
        if rnd != last_round and st.pending is None:
            inc = {p: sum(r.food for r in rules.regions_controlled(st, p)) for p in "AB"}
            print(f"-- round {rnd} (food M {st.food['A']} +{inc['A']} / B {st.food['B']} +{inc['B']}); Martin hand: " + ", ".join(st.cards[u.card_id].name for u in st.hands['A']))
            print(board(st))
            last_round = rnd
        pend = st.pending
        rp = len(st.remove_pile)
        tgt_before = None
        if ad["kind"] == "place" and ad["target"][0] == "cr":
            s = st.board.get(ad["target"][1]); tgt_before = s[-1] if s else None
        rules.apply_action(st, a)
        name = lambda c: st.cards[c].name
        if ad["kind"] == "draw": txt = "draw"
        elif ad["kind"] == "place":
            txt = f"place {name(ad['card_id'])} → " + ("HQ!" if ad["target"][0] == "hq" else ad["target"][1])
            if tgt_before: txt += f" (on {tgt_before.owner}{name(tgt_before.card_id)})"
        else:
            if pend and pend.get("kind") == "mulligan":
                txt = "keep" if a.choice == SKIP else f"mulligan returns #{a.choice}"
            else:
                txt = "skip" if a.choice == SKIP else f"chooses {a.choice}"
        gone = st.remove_pile[rp:]
        if gone: txt += " — removed " + ", ".join(name(c) for c in gone)
        tm = rec.get("action_times", [])
        print(f"   {who[actor]}: {txt}" + (f"   [{tm[i]}s]" if i < len(tm) else ""))
    say(len(rec["actions"]))
    print(f"   END: food M {st.food['A']} / B {st.food['B']}")
    print(board(st))

if __name__ == "__main__":
    recs = [json.loads(l) for l in open(sys.argv[1])]
    first = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    for i, r in enumerate(recs[first:], 1):
        run(r, i)
