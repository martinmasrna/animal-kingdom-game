"""Composer's bench: c.run(spec, obvious=[line, ...]) prints the board, the verdict, the winning first turns, and what
the defence does to each obvious line."""
import json, os, sys, time, warnings
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools', 'puzzles'))
from animal_kingdom import puzzles as P
from animal_kingdom.engine import rules
from solve import board_text, describe

def parse(board):
    out = {}
    for cr, s in board.items():
        st = []
        for tok in s.split():
            own = {'+': 'A', '-': 'B', '~': 'wild'}[tok[0]]
            card = tok[1:]; extra = {}
            if '^' in card: card, c = card.split('^'); extra['counter'] = int(c)
            st.append({'card': card, 'owner': own, **extra})
        out[cr] = st
    return out

def mk(board, a, b, turns, food=(0, 0), **kw):
    return {'id': kw.pop('id', 'x'), 'title': 'x', 'theme': 'x', 'to_move': 'A', 'turns': turns, 'board': parse(board),
            'hands': {'A': a, 'B': b}, 'food': {'A': food[0], 'B': food[1]}, 'solution': [], 'hint': '', 'why': '', **kw}

def P_(c, t): return {'kind': 'place', 'card_id': c, 'target': ['hq', 'B'] if t == 'den' else ['cr', t]}
def R_(f, t): return {'kind': 'roam', 'from': f, 'target': ['hq', 'B'] if t == 'den' else ['cr', t]}

def run(pz, obvious=(), cap=3_000_000, show=True):
    if show: print(board_text(pz))
    probs = P.position_problems(pz)
    if probs: print('PROBLEMS', probs); return None
    t0 = time.time()
    rep = P.solve(pz, cap)
    s = P.build(pz)
    print(f"== {rep['status']} in {pz['turns']}: {len(rep.get('winning_first_turns', []))} winning first turns, {rep.get('nodes')} nodes, {time.time()-t0:.1f}s")
    for w in rep.get('winning_first_turns', [])[:8]:
        print('  WIN: ' + '; '.join(describe(a, s) for a in w['line']))
        if w['reply']:
            after = P.play_line(s, w['line'])
            print('       reply: ' + '; '.join(describe(a, after) for a in w['reply']))
    sv = P.Solver(pz['turns'])
    for line in obvious:
        try:
            st = P.play_line(s, line)
        except Exception as e:
            print('  obvious', line, 'ILLEGAL', e); continue
        w = sv.wins(st)
        msg = '  OBVIOUS ' + '; '.join(describe(a, s) for a in line) + (' -> wins' if w else ' -> fails')
        if not w and st.player_to_act() == 'B' and sv.outcome(st) is None:
            msg += '   refutation: ' + '; '.join(describe(a.to_dict(), st) for a in sv.defence(st))
        print(msg)
    return rep
