"""Writes knowledge/puzzles/set-1-2026-11-05.md from the puzzle files and the notes below."""
import json, os, sys, warnings
warnings.filterwarnings('ignore')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tools', 'puzzles'))
from animal_kingdom import puzzles as P
from solve import board_text, describe
from notes import NOTES, INTRO

def say(d, s):
    """One action in words, on the position `s` it is played from."""
    name = lambda cid: s.cards[cid].name
    t = d.get('target')
    where = (lambda: "into the den" if t[0] == 'hq' else f"on {t[1]}")
    free = s.pending is not None
    if d['kind'] == 'place':
        return f"{'(free) ' if free else ''}{name(d['card_id'])} {where()}"
    if d['kind'] == 'roam':
        top = s.top_unit(d['from'])
        return f"the {name(top.card_id)} on {d['from']} roams {where().replace("on ", "to ", 1)}"
    if d['kind'] == 'pass':
        return "end the turn"
    if d['kind'] == 'choice':
        ch = d['choice']
        for cr, st in s.board.items():
            for u in st:
                if u.iid == ch:
                    return f"its Roar picks the {name(u.card_id)} on {cr}"
        if isinstance(ch, str) and ',' in ch:
            top = s.top_unit(ch)
            return f"its Roar picks {('the ' + name(top.card_id) + ' on ') if top else ''}{ch}"
        if ch == '__skip__':
            return "skip"
        return f"choose {ch}"
    return d['kind']

def words(line, state):
    out, s = [], state.clone()
    from animal_kingdom.engine import rules
    for d in line:
        out.append(say(d, s))
        rules.apply_action(s, P.actions_from([d])[0])
    return out

parts = [INTRO]
for pz in P.all_puzzles():
    n = NOTES.get(pz['id'])
    if n is None:
        continue
    s = P.build(pz)
    ml = pz['main_line']
    first = [d for d in ml][:len(pz['solution'])]
    rest = ml[len(pz['solution']):]
    b = board_text(pz).split('\n')
    parts.append(f"## {pz['title']} (`{pz['id']}`)\n\nIn {pz['turns']} turn{'s' if pz['turns'] > 1 else ''} · {pz['theme']} · difficulty {n['difficulty']} of 5"
                 + (f" · from a real game ({pz['source']})" if pz.get('source') else '') + "\n")
    parts.append("```\n" + "\n".join(b) + "\n```\n")
    parts.append(f"**The obvious move:** {n['obvious']}\n")
    parts.append(f"**The solution:** " + "; ".join(words(pz['solution'], s)) + ".")
    if rest:
        after = P.play_line(s, pz['solution'])
        bline = [d for d in rest if d['by'] == 'B']
        parts.append(f" The defence's best reply: " + ("; ".join(words(bline, after)) if bline else "nothing helps") + ".")
        fin = P.play_line(s, [d for d in ml[:len(pz['solution'])]] + [d for d in rest if True][:0])
        aline = []
        st = after
        from animal_kingdom.engine import rules
        for d in rest:
            if d['by'] == 'A':
                aline.append(say(d, st))
            rules.apply_action(st, P.actions_from([d])[0])
        parts.append(" Then: " + "; ".join(aline) + ".")
    parts.append(f"\n\n**The idea:** {pz['why']}\n\n**Hint:** {pz['hint']}\n")
open(os.path.join(ROOT, 'knowledge', 'puzzles', 'set-1-2026-11-05.md'), 'w').write("\n".join(parts) + "\n")
print('ok')
