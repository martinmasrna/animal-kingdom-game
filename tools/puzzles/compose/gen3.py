"""Two-turn puzzle search by deck: open boards (both flanks, the den approached from the side), the solver's cards from
one deck, the defender's from another; kept when forced in two turns but not in one, with one winning first turn whose
first action is not the plain walk-in."""
import json, os, random, sys, multiprocessing as mp, warnings
warnings.filterwarnings('ignore')
import c
from animal_kingdom import puzzles as P
DECKS = {
 'fish': ['cod', 'tuna', 'mahi_mahi', 'barracuda', 'remora', 'piranha', 'hammerhead', 'sardine', 'great_white_shark', 'manta_ray',
          'octopus', 'dolphin', 'jellyfish', 'sea_turtle', 'orca', 'krill'],
 'colony': ['worker_ant', 'soldier_ant', 'termite_queen', 'termite_king', 'worker_bee', 'guard_bee', 'nurse_bee', 'guard_wasp',
            'hornet', 'hornet', 'worker_wasp', 'young_ant'],
 'canines': ['wolf', 'wolf', 'bush_dog', 'dhole', 'jackal', 'african_wild_dog', 'coyote', 'street_dog', 'fox', 'pup'],
 'city': ['alley_cat', 'bat', 'macaque', 'mosquito', 'mouse', 'opossum', 'pigeon', 'raccoon', 'rat', 'street_dog', 'kitten'],
}
FOES = ['grizzly_bear', 'lion', 'tortoise', 'hedgehog', 'cheetah', 'bobcat', 'mouse', 'pup', 'boar', 'hippopotamus', 'zebra', 'toad',
        'stick_insect', 'gazelle', 'porcupine', 'golden_orb_weaver', 'gorilla', 'wildebeest', 'elephant', 'crocodile', 'giraffe']
DEF = ['grizzly_bear', 'pigeon', 'black_mamba', 'lion', 'pup', 'mouse', 'cheetah', 'bobcat', 'hawk', 'stick_insect', 'tortoise', 'jaguar']
OUT = os.environ.get('AK_COMPOSE_OUT', '.')   # where the finds are written (one JSONL a deck)
CRS = [f"{r},{l}" for r in range(1, 6) for l in (1, 2, 3)]
NB = {"1,1": ["1,2", "2,1"], "1,2": ["1,1", "1,3", "2,2"], "1,3": ["1,2", "2,3"], "2,1": ["1,1", "2,2", "3,1"], "2,2": ["1,2", "2,1", "2,3", "3,2"],
      "2,3": ["1,3", "2,2", "3,3"], "3,1": ["2,1", "3,2", "4,1"], "3,2": ["2,2", "3,1", "3,3", "4,2"], "3,3": ["2,3", "3,2", "4,3"],
      "4,1": ["3,1", "4,2", "5,1"], "4,2": ["3,2", "4,1", "4,3", "5,2"], "4,3": ["3,3", "4,2", "5,3"], "5,1": ["4,1", "5,2"],
      "5,2": ["4,2", "5,1", "5,3"], "5,3": ["4,3", "5,2"]}
def make(deck, rng):
    mine = DECKS[deck]; b = {}
    # a random connected A group grown from A's den front, reaching rank 3 or 4
    start = rng.choice(["1,1", "1,2", "1,3"]); grp = [start]
    target = rng.choice([5, 6, 7, 8])
    while len(grp) < target:
        cr = rng.choice(grp); nxt = [n for n in NB[cr] if n not in grp and int(n[0]) <= 4]
        if nxt: grp.append(rng.choice(nxt))
    for cr in grp:
        b[cr] = '+' + rng.choice(mine)
    for cr in CRS:
        if cr not in b and int(cr[0]) >= 3 and rng.random() < 0.55:
            b[cr] = '-' + rng.choice(FOES)
    a = rng.sample(mine, rng.choice([2, 3, 3, 4]))
    return c.mk(b, a, rng.sample(DEF, rng.choice([1, 2])), 2, food=(0, 20))
def judge(job):
    deck, seed = job
    pz = make(deck, random.Random(seed * 1299709 + sum(map(ord, deck))))
    if P.position_problems(pz): return None
    try:
        if P.solve({**pz, 'turns': 1}, node_cap=20_000)['status'] != 'not forced': return None
        rep = P.solve(pz, node_cap=60_000)
    except Exception:
        return None
    if rep['status'] != 'forced' or len(rep['winning_first_turns']) != 1: return None
    return {'name': deck, 'seed': seed, 'pz': pz, 'win': rep['winning_first_turns'], 'nodes': rep['nodes'], 'first_turns': rep['first_turns']}
if __name__ == '__main__':
    n = int(sys.argv[1]); decks = sys.argv[2:] or list(DECKS)
    with mp.Pool(4) as pool:
        jobs = [(d, s) for s in range(n) for d in decks]
        for r in pool.imap_unordered(judge, jobs, chunksize=2):
            if r:
                with open(fos.path.join(OUT, f'g3_{r["name"]}.jsonl'), 'a') as fh: fh.write(json.dumps(r) + '\n')
    print('done', flush=True)
