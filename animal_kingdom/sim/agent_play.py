"""Let an agent play Animal Kingdom one decision at a time from the shell, against a bot, seeing the
board the way the web client shows it (lit paths, connected units, stacks, regions, HQ fronts).

Single game: python -m animal_kingdom.sim.agent_play new ME OPP [--bot turn] [--seed N], then
`draw` / `place CARD CR|hq` / `choose VALUE` / `skip` / `show`.
Simultaneous games (one round trip plays a turn on every board):
python -m animal_kingdom.sim.agent_play simul new N ME OPP, then `simul "1: place x 3,2; draw" "2: skip" ...`.
Games are kept in results/agent-games/ (untracked); these are agent games, never human data.

"""
import json, os, random, sys
from collections import Counter
from animal_kingdom.decks import load_premade_deck
from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, DrawAction, PlaceAction, action_from_dict
from animal_kingdom.engine.state import GameState, new_game
from animal_kingdom.engine.strength import effective_strength, placement_strength
from animal_kingdom.sim.runner import make_bot

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "results", "agent-games")
FILE = os.path.join(HERE, "game.json")
GAMES = os.path.join(HERE, "simul")
ME, OPP = "A", "B"


os.makedirs(HERE, exist_ok=True)


def load():
    g = json.load(open(FILE))
    return g, GameState.from_dict(g["state"])


def save(g, st):
    g["state"] = st.to_dict()
    json.dump(g, open(FILE, "w"))


def name(st, cid):
    return st.cards[cid].name


def unit(st, u):
    tm = next((s["remaining"] for s in st.scheduled if s["iid"] == u.iid), None)
    return f"{u.owner}:{name(st, u.card_id)} {effective_strength(st, u)}" + (f" ⏱{tm}" if tm else "")


def board_view(st, drawing=False):
    """The position as facts, not a picture: each side's units (with what's buried under them and
    timers), which crossroads connect to each HQ, both HQs' fronts, and every region's state.
    Coordinates are col,row on the 5x3 grid; col 1 is A's HQ side, col 5 is B's."""
    if drawing:
        return board_drawing(st)
    gm = st.game_map
    conn = {p: st.connected_occupied(p) for p in "AB"}
    timers = {x["iid"]: x["remaining"] for x in st.scheduled}
    out = []
    for p in "AB":
        units = []
        for cr in sorted(st.board, key=lambda c: tuple(map(int, c.split(",")))[::-1]):
            s_ = st.board[cr]
            if not s_ or s_[-1].owner != p:
                continue
            u = s_[-1]
            t = f"{cr} {name(st, u.card_id)} {effective_strength(st, u)}"
            if u.iid in timers:
                t += f" ⏱{timers[u.iid]}"
            if len(s_) > 1:
                t += " [under: " + ", ".join(f"{v.owner}:{name(st, v.card_id)}" for v in reversed(s_[:-1])) + "]"
            units.append(t)
        out.append(f"{p} units: " + (" | ".join(units) if units else "none"))
    for p in "AB":
        loose = sorted(cr for cr, s_ in st.board.items() if s_ and s_[-1].owner == p and cr not in conn[p])
        line = f"connected to {p}'s HQ: " + (" ".join(sorted(conn[p])) or "none")
        if loose:
            line += f"   (cut off: {' '.join(loose)})"
        out.append(line)
    out.append("HQ fronts: A's " + " ".join(f"{cr}={st.owner_of(cr) or '·'}" for cr in sorted(gm.hq_front("A")))
               + " | B's " + " ".join(f"{cr}={st.owner_of(cr) or '·'}" for cr in sorted(gm.hq_front("B"))))
    regs = []
    for reg in gm.regions.values():
        own = [st.owner_of(cr) for cr in reg.corners]
        tag = next((f"{p}✓" for p in "AB" if own.count(p) == 4), None) or f"A{own.count('A')} B{own.count('B')}"
        regs.append(f"{reg.corners[0]}–{reg.corners[-1]} +{reg.food} {tag}")
    out.append("regions: " + " | ".join(regs))
    return out


def board_drawing(st):
    """The same position as an ASCII picture, for a human looking at it."""
    gm = st.game_map
    conn = {p: st.connected_occupied(p) for p in "AB"}
    W = 17

    def cell(cr):
        s_ = st.board.get(cr)
        if not s_:
            return "·".center(W)
        u = s_[-1]
        t = f"{u.owner}:{name(st, u.card_id)[:9]} {effective_strength(st, u)}" + ("*" if cr in conn[u.owner] else "")
        if len(s_) > 1:
            t += f"+{len(s_)-1}"
        return t[:W].center(W)

    def link(a_, b_, horiz):
        oa, ob = st.owner_of(a_), st.owner_of(b_)
        if oa and oa == ob and a_ in conn[oa] and b_ in conn[oa]:
            return f"═{oa}═" if horiz else oa
        return "───" if horiz else "│"

    out = []
    for r in range(1, 4):
        out.append("HQA─" + "".join(cell(f"{c},{r}") + (link(f"{c},{r}", f"{c+1},{r}", True) if c < 5 else "") for c in range(1, 6)) + "─HQB")
        if r < 3:
            out.append("    " + "   ".join(link(f"{c},{r}", f"{c},{r+1}", False).center(W) for c in range(1, 6)))
    return out


def describe(st, a, who):
    if isinstance(a, DrawAction):
        return f"{who} drew"
    if isinstance(a, PlaceAction):
        return f"{who} placed {name(st, a.card_id)} on {'their HQ' if a.target[0]=='hq' else a.target[1]}"
    if a.choice == SKIP:
        return f"{who} declined"
    return f"{who} chose {a.choice}"


def run_bot(g, st):
    """Apply bot decisions until it's my decision or the game ends; log what happened."""
    bot = make_bot(g["bot"], g["seed"] + 1000 + len(g["log"]))
    while rules.is_terminal(st) is None and st.player_to_act() == OPP:
        before = {cr: [(u.card_id, u.owner) for u in s] for cr, s in st.board.items()}
        rp = len(st.remove_pile)
        a = bot.choose(st.view_for(OPP), rules.legal_actions(st), st.clone())
        line = describe(st, a, "THEY")
        if isinstance(a, PlaceAction) and a.target[0] == "cr" and before.get(a.target[1]):
            line += f" (on top of {before[a.target[1]][-1][1]}:{name(st, before[a.target[1]][-1][0])})"
        rules.apply_action(st, a)
        gone = st.remove_pile[rp:]
        if gone:
            line += " — removed: " + ", ".join(name(st, c) for c in gone)
        g["log"].append(line)
    res = rules.is_terminal(st)
    if res and not st.result:
        st.result = res


def show(g, st):
    gm = st.game_map
    out = []
    res = st.result or rules.is_terminal(st)
    inc = {p: sum(r.food for r in rules.regions_controlled(st, p)) for p in "AB"}
    turn = f"round {st.turn_counter // 2 + 1}, {'YOUR' if st.current == ME else 'THEIR'} turn"
    left = st.config.actions_per_turn + st.turn_flags.get(f"bonus_actions_{st.current}", 0) - st.actions_taken_this_turn
    out.append(f"== {turn}, actions left {left} | food: you {st.food[ME]} (+{inc[ME]}/turn), them {st.food[OPP]} (+{inc[OPP]}/turn), win at {gm.win_food}")
    if res:
        out.append(f"== GAME OVER: {'YOU WIN' if res.winner == ME else 'YOU LOSE' if res.winner else 'DRAW'} by {res.reason}")
    new = g["log"][g.get("shown", 0):]
    if new:
        out.append("since your last decision: " + " | ".join(new))
    g["shown"] = len(g["log"])
    out.extend(board_view(st, drawing="--drawing" in sys.argv))
    mine_left = Counter(st.decks[ME])
    out.append("your deck (copies left): " + ", ".join(f"{name(st,c)} {st.cards[c].base_strength}×{n}" for c, n in sorted(mine_left.items(), key=lambda x: str(st.cards[x[0]].base_strength))))
    out.append(f"your hand: " + " ; ".join(f"{name(st,u.card_id)} [{placement_strength(st,u)}] {st.cards[u.card_id].text}" for u in st.hands[ME]))
    out.append(f"their hand: {len(st.hands[OPP])} cards | decks: you {len(st.decks[ME])}, them {len(st.decks[OPP])}")
    unseen = Counter(st.decks[OPP]) + Counter(u.card_id for u in st.hands[OPP])
    out.append("their unseen cards: " + ", ".join(f"{name(st,c)} {st.cards[c].base_strength}×{n}" for c, n in sorted(unseen.items())))
    if st.remove_pile:
        out.append("remove pile: " + ", ".join(name(st, c) for c in st.remove_pile))
    if not res and st.player_to_act() == ME:
        legal = rules.legal_actions(st)
        if st.pending:
            step = st.effect_stack[-1] if st.effect_stack else {}
            opts = []
            for a in legal:
                if isinstance(a, PlaceAction):
                    opts.append(f"place {a.card_id} {a.target[1] if a.target[0]=='cr' else 'hq'}")
                elif a.choice == SKIP:
                    opts.append("skip")
                else:
                    lab = a.choice
                    for u in st.hands[ME]:
                        if u.iid == a.choice:
                            lab = f"{a.choice} (= {name(st,u.card_id)} in hand)"
                    opts.append(f"choose {lab}")
            out.append(f"DECISION ({step.get('op','effect')}): " + " | ".join(opts))
        else:
            by = {}
            for a in legal:
                if isinstance(a, PlaceAction):
                    by.setdefault(a.card_id, []).append(a.target[1] if a.target[0] == "cr" else "HQ!")
            out.append("DECISION: " + ("draw | " if any(isinstance(a, DrawAction) for a in legal) else "")
                       + " | ".join(f"place {cid} → {' '.join(t)}" for cid, t in by.items()))
    print("\n".join(out))


def apply_cmd(st, words):
    cmd = words[0]
    if cmd == "draw":
        a = DrawAction()
    elif cmd == "place":
        tgt = ("hq", OPP) if words[2].lower() == "hq" else ("cr", words[2])
        a = PlaceAction(words[1], tgt)
    elif cmd == "skip":
        a = ChoiceAction(SKIP)
    elif cmd == "choose":
        a = ChoiceAction(int(words[1]) if words[1].isdigit() else words[1])
    else:
        raise ValueError(cmd)
    rules.apply_action(st, a)
    return a


def simul(argv):
    """simul new N ME OPP [--bot turn] | simul show | simul "1: place x 3,2" "2: draw" ..."""
    import contextlib, io, glob
    os.makedirs(GAMES, exist_ok=True)
    global FILE
    if argv and argv[0] == "new":
        n, me, opp = int(argv[1]), argv[2], argv[3]
        bot = argv[argv.index("--bot") + 1] if "--bot" in argv else "turn"
        for f in glob.glob(os.path.join(GAMES, "*.json")):
            os.remove(f)
        for i in range(1, n + 1):
            seed = 10_000 + i
            st = new_game(load_premade_deck(me), load_premade_deck(opp), seed)
            g = {"me": me, "opp": opp, "bot": bot, "seed": seed, "log": [], "mine": []}
            run_bot(g, st)
            FILE = os.path.join(GAMES, f"{i}.json"); save(g, st)
        argv = ["show"]
    moves = {}
    if argv and argv[0] != "show":
        for m in argv:
            gid, rest = m.split(":", 1)
            moves[int(gid)] = [c.split() for c in rest.split(";") if c.strip()]
    done = []
    for f in sorted(glob.glob(os.path.join(GAMES, "*.json")), key=lambda p: int(os.path.basename(p)[:-5])):
        gid = int(os.path.basename(f)[:-5])
        FILE = f
        g, st = load()
        if gid in moves:
            for words in moves[gid]:
                if rules.is_terminal(st) or st.player_to_act() != ME:
                    print(f"#### GAME {gid}: skipped '{' '.join(words)}' (not your decision any more)")
                    break
                try:
                    a = apply_cmd(st, words)
                except Exception as e:
                    print(f"#### GAME {gid}: '{' '.join(words)}' rejected ({e}); stopped there")
                    break
                g["mine"].append(a.to_dict()); g["log"].append(describe(st, a, "YOU"))
                run_bot(g, st)
        res = st.result or rules.is_terminal(st)
        if res:
            done.append(f"{gid}:{'W' if res.winner == ME else 'L' if res.winner else 'D'}({res.reason},r{st.turn_counter//2+1})")
            save(g, st); continue
        if gid in moves or (argv and argv[0] == "show"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                show(g, st)
            text = "\n".join(l for l in buf.getvalue().splitlines()
                              if not l.startswith("their unseen") and not l.startswith("regions"))
            print(f"#### GAME {gid}\n{text}")
        save(g, st)
    if done:
        print("finished: " + " ".join(done))


def main():
    cmd = sys.argv[1]
    if cmd == "simul":
        return simul(sys.argv[2:])
    if cmd == "new":
        me, opp = sys.argv[2], sys.argv[3]
        bot = sys.argv[sys.argv.index("--bot") + 1] if "--bot" in sys.argv else "turn"
        seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else random.randrange(1 << 30)
        st = new_game(load_premade_deck(me), load_premade_deck(opp), seed)
        g = {"me": me, "opp": opp, "bot": bot, "seed": seed, "log": [], "mine": []}
        run_bot(g, st)
        save(g, st); show(g, st); save(g, st)
        return
    g, st = load()
    if cmd != "show":
        if cmd == "draw":
            a = DrawAction()
        elif cmd == "place":
            tgt = ("hq", OPP) if sys.argv[3].lower() == "hq" else ("cr", sys.argv[3])
            a = PlaceAction(sys.argv[2], tgt)
        elif cmd == "skip":
            a = ChoiceAction(SKIP)
        elif cmd == "choose":
            v = sys.argv[2]
            a = ChoiceAction(int(v) if v.isdigit() else v)
        rules.apply_action(st, a)            # raises if illegal
        g["mine"].append(a.to_dict())
        g["log"].append(describe(st, a, "YOU"))
        run_bot(g, st)
    save(g, st); show(g, st); save(g, st)


if __name__ == "__main__":
    main()
