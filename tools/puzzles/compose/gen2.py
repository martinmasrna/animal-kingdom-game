"""Two-turn puzzle search: open boards, the idea's card in hand, a defender hand from a defensive pool; kept when forced
in two turns but not in one, with one winning first turn that plays the idea's card before its last action."""
import json, random, sys, multiprocessing as mp, warnings
warnings.filterwarnings('ignore')
import c
from animal_kingdom import puzzles as P
from gen1 import IDEAS, B_POOL, A_FILL
DEF = ['grizzly_bear', 'pigeon', 'black_mamba', 'lion', 'pup', 'mouse', 'cheetah', 'bobcat', 'hawk', 'stick_insect', 'tortoise']
def make(name, rng):
    need = IDEAS[name]; b = {}
    lane = rng.choice([1, 2, 3]); k = rng.choice([2, 3, 3])
    for r in range(1, k + 1):
        b[f"{r},{lane}"] = '+' + rng.choice(['lion', 'lion', 'cheetah', 'wolf', 'tortoise', 'bobcat'])
    if rng.random() < 0.5:
        l2 = rng.choice([l for l in (1, 2, 3) if l != lane])
        for r in range(1, rng.choice([1, 2, 3]) + 1):
            b[f"{r},{l2}"] = '+' + rng.choice(['lion', 'cheetah', 'pup', 'mouse', 'wolf'])
    for r in range(k, 6):
        for l in (1, 2, 3):
            cr = f"{r},{l}"
            if cr not in b and rng.random() < (0.7 if r >= 4 else 0.35):
                b[cr] = '-' + rng.choice(B_POOL)
    a = list(need) + rng.sample(A_FILL, rng.choice([1, 2, 3]))
    return c.mk(b, a, rng.sample(DEF, rng.choice([1, 2])), 2, food=(0, 20))
def judge(job):
    name, seed = job
    pz = make(name, random.Random(seed * 104729 + sum(map(ord, name))))
    if P.position_problems(pz): return None
    try:
        if P.solve({**pz, 'turns': 1}, node_cap=20_000)['status'] != 'not forced': return None
        rep = P.solve(pz, node_cap=60_000)
    except Exception:
        return None
    if rep['status'] != 'forced' or len(rep['winning_first_turns']) != 1: return None
    line = rep['winning_first_turns'][0]['line']
    if not any(a.get('card_id') in IDEAS[name] for a in line): return None
    return {'name': name, 'seed': seed, 'pz': pz, 'win': rep['winning_first_turns'], 'nodes': rep['nodes'], 'first_turns': rep['first_turns']}
if __name__ == '__main__':
    n = int(sys.argv[1]); names = sys.argv[2:] or list(IDEAS)
    with mp.Pool(4) as pool:
        for name in names:
            for r in pool.imap_unordered(judge, [(name, s) for s in range(n)], chunksize=2):
                if r:
                    with open(f'g2_{name}.jsonl', 'a') as fh: fh.write(json.dumps(r) + '\n')
            print(name, 'done', flush=True)
