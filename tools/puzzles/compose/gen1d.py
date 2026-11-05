"""One-turn search by deck: an open board, the solver's cards from one deck; kept when forced in one turn with one winning
turn whose line has a free placement, a roam or a Roar's choice (more than "play the one card that can")."""
import json, os, random, sys, multiprocessing as mp, warnings
warnings.filterwarnings('ignore')
import c
from animal_kingdom import puzzles as P
from gen3 import DECKS, FOES, NB, CRS
OUT = os.environ.get('AK_COMPOSE_OUT', '.')
def make(deck, rng):
    mine = DECKS[deck]; b = {}
    start = rng.choice(["1,1", "1,2", "1,3"]); grp = [start]
    while len(grp) < rng.choice([6, 7, 8, 9]):
        cr = rng.choice(grp); nxt = [n for n in NB[cr] if n not in grp and int(n[0]) <= 4]
        if nxt: grp.append(rng.choice(nxt))
    for cr in grp: b[cr] = '+' + rng.choice(mine)
    for cr in CRS:
        if cr not in b and int(cr[0]) >= 3 and rng.random() < 0.6: b[cr] = '-' + rng.choice(FOES)
    return c.mk(b, rng.sample(mine, rng.choice([2, 3])), ['lion'], 1, food=(0, 20))
def judge(job):
    deck, seed = job
    pz = make(deck, random.Random(seed * 15485863 + sum(map(ord, deck))))
    if P.position_problems(pz): return None
    try: rep = P.solve(pz, node_cap=30_000)
    except Exception: return None
    if rep['status'] != 'forced' or len(rep['winning_first_turns']) != 1: return None
    line = rep['winning_first_turns'][0]['line']
    if len(line) < 3 or not any(a['kind'] in ('roam', 'choice') for a in line) and len(line) < 4: return None
    return {'name': deck, 'seed': seed, 'pz': pz, 'win': rep['winning_first_turns'], 'first_turns': rep['first_turns']}
if __name__ == '__main__':
    n = int(sys.argv[1]); decks = sys.argv[2:] or list(DECKS)
    with mp.Pool(4) as pool:
        for r in pool.imap_unordered(judge, [(d, s) for s in range(n) for d in decks], chunksize=8):
            if r:
                with open(os.path.join(OUT, f'g1d_{r["name"]}.jsonl'), 'a') as fh: fh.write(json.dumps(r) + '\n')
                print(r['name'], r['seed'], flush=True)
