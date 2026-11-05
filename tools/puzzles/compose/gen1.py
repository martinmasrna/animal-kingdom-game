"""One-turn puzzle search: an open board near the defender's den, the idea's card in hand; kept when forced in one turn
with exactly one winning turn that plays the idea's card, and the strongest-card cover (the obvious move) fails."""
import json, random, sys, multiprocessing as mp, warnings
warnings.filterwarnings('ignore')
import c
from animal_kingdom import puzzles as P
B_POOL = ['grizzly_bear', 'grizzly_bear', 'lion', 'tortoise', 'hedgehog', 'cheetah', 'bobcat', 'mouse', 'pup', 'hamster', 'boar',
          'hippopotamus', 'zebra', 'toad', 'stick_insect', 'gazelle', 'porcupine', 'armadillo', 'golden_orb_weaver']
A_FILL = ['lion', 'lion', 'pup', 'mouse', 'cheetah', 'bobcat', 'squirrel', 'tortoise', 'wolf']
IDEAS = {
 'ocelot': ['ocelot'], 'mole': ['mole'], 'rabbit': ['rabbit'], 'impala': ['impala'], 'leo': ['lion_legend', 'lion_legend_2'],
 'remora': ['remora'], 'barracuda': ['barracuda'], 'termite_queen': ['termite_queen'], 'coyote': ['coyote'],
 'street_dog': ['street_dog'], 'african_wild_dog': ['african_wild_dog'], 'warthog': ['warthog'], 'gopher': ['gopher', 'squirrel'],
 'chimpanzee': ['chimpanzee'], 'serval': ['serval'], 'hammerhead': ['hammerhead'], 'cuckoo_legend': ['cuckoo_legend'],
 'hawk': ['hawk'], 'albatross': ['albatross'], 'jaguar': ['jaguar'], 'black_mamba': ['black_mamba'], 'honey_badger': ['honey_badger'],
 'skunk': ['skunk'], 'opossum': ['opossum'], 'wolverine': ['wolverine'], 'viper': ['viper'], 'mosquito': ['mosquito'],
 'octopus': ['octopus'], 'hercules_beetle': ['hercules_beetle'], 'tiger': ['tiger'], 'eagle': ['eagle'], 'crocodile': ['crocodile'],
 'jackal': ['jackal'], 'bush_dog': ['bush_dog'], 'vole': ['vole', 'rabbit'], 'woodpecker': ['woodpecker'], 'leopard': ['leopard'],
 'rhinoceros': ['rhinoceros'], 'krill': ['krill', 'sperm_whale'], 'king_theron': ['lion_legend_3'], 'piranha': ['piranha'],
}
def make(name, rng):
    need = IDEAS[name]
    b = {}
    # an A group reaching rank 2-4 by some path, sometimes two lanes
    lane = rng.choice([1, 2, 3]); k = rng.choice([3, 3, 4])
    for r in range(1, k + 1):
        b[f"{r},{lane}"] = '+' + rng.choice(['lion', 'lion', 'cheetah', 'wolf', 'tortoise', 'bobcat'])
    if rng.random() < 0.4:
        l2 = rng.choice([l for l in (1, 2, 3) if l != lane])
        for r in range(1, rng.choice([2, 3]) + 1):
            b[f"{r},{l2}"] = '+' + rng.choice(['lion', 'cheetah', 'pup', 'mouse'])
    for r in range(k, 6):
        for l in (1, 2, 3):
            cr = f"{r},{l}"
            if cr not in b and rng.random() < (0.75 if r >= 4 else 0.4):
                b[cr] = '-' + rng.choice(B_POOL)
    a = list(need) + rng.sample(A_FILL, rng.choice([1, 2]))
    return c.mk(b, a, ['lion'], 1, food=(0, 20))

def judge(job):
    name, seed = job
    rng = random.Random(seed * 7919 + hash(name) % 1000)
    pz = make(name, rng)
    if P.position_problems(pz):
        return None
    try:
        rep = P.solve(pz, node_cap=30_000)
    except Exception:
        return None
    if rep['status'] != 'forced' or len(rep['winning_first_turns']) != 1:
        return None
    line = rep['winning_first_turns'][0]['line']
    if not any(a.get('card_id') in IDEAS[name] for a in line):
        return None
    if len([a for a in line if a['kind'] != 'choice']) < 2:
        return None
    return {'name': name, 'seed': seed, 'pz': pz, 'win': rep['winning_first_turns'], 'nodes': rep['nodes'], 'first_turns': rep['first_turns']}

if __name__ == '__main__':
    names = sys.argv[2:] or list(IDEAS)
    n = int(sys.argv[1])
    with mp.Pool(4) as pool:
        for name in names:
            got = [r for r in pool.imap_unordered(judge, [(name, s) for s in range(n)], chunksize=8) if r]
            with open(f'g1_{name}.jsonl', 'w') as fh:
                for r in got:
                    fh.write(json.dumps(r) + '\n')
            print(name, len(got), flush=True)
