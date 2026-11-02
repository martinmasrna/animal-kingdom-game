"""Self-play on the Rust engine, every game played whole in Rust, recording what the search learned and the games.

Both seats play one bot spec (the whole-turn search with the candidate net, capped per move) on Martin's current decks
(`results/policy/decks.json`, every pairing). Three outputs under OUT (a path stem):
  OUT.jsonl        the games, action by action (tools/policy/extract.py reads them for the candidate net)
  OUT_out.npz      every turn-start position and every afterstate the search scored, labelled by who won
                   (what learn/selfplay.py records; learn/slotnet.py --live fits it)
  OUT_search.npz   the turn-start positions only, labelled by the search's own score of the position turned into a
                   win chance (sigmoid(points / 47), the evaluation's scale): what the two-turn search found by looking
                   ahead, available at every decision without waiting for the game to end
Usage: selfplay_rs.py OUT GAMES [--spec SPEC] [--jobs 7] [--seed 20261102] [--epsilon 0.05]
A checkpoint of both npz files every 200 games (OUT_*.partial.npz); the jsonl is written as the games finish."""
import argparse, dataclasses, json, math, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("AK_RUST_BOTS", "1")
import numpy as np

from animal_kingdom.engine.config import Config
from animal_kingdom.engine.resources import load_bundled_json
from animal_kingdom.sim.replay import game_log_record
from animal_kingdom.recording.writer import JsonlGameWriter
from animal_kingdom.bots import features
from animal_kingdom.web.match import EXPERT

DECKS_PATH = "results/policy/decks.json"
FEATURE_SET = "board_live"
POINTS_PER_LOGIT = 47.0
DEFAULT_SPEC = (EXPERT.replace("referee_learned", "atomic_learned").replace("time_budget=8", "time_budget=3")
                + ",rounds=2,draws=1,inner=1,width2=6,beam=6,hands=5,cand=animal_kingdom/data/learned/cand_v4.json")

_engine = None


def engine():
    global _engine
    if _engine is None:
        import ak_engine
        cfg = json.dumps(dataclasses.asdict(Config.default()), sort_keys=True)
        _engine = ak_engine.Engine(json.dumps(load_bundled_json("cards.json")), json.dumps(load_bundled_json("maps.json")), cfg, "map_b")
    return _engine


_prepared = {}


def prepared(spec):
    """The Rust spec and the evaluation net's JSON for `spec`, as sim.runner builds a Rust bot: `eval=NAME` names the
    learned artifact, handed to the engine beside the spec."""
    if spec not in _prepared:
        from animal_kingdom.bots.learned_eval import load_eval
        from animal_kingdom.sim.runner import DEFAULT_LEARNED_EVAL
        kind, _, rest = spec.partition(":")
        parts = [x for x in rest.split(",") if x]
        name = next((x[5:] for x in parts if x.startswith("eval=")), DEFAULT_LEARNED_EVAL)
        rs = kind + ":" + ",".join(x for x in parts if not x.startswith("eval="))
        _prepared[spec] = (rs, json.dumps(load_eval(name).to_dict()))
    return _prepared[spec]


def play(job):
    import ak_engine
    deck_a, deck_b, list_a, list_b, seed, spec, epsilon = job
    rs, ev = prepared(spec)
    r = ak_engine.play_game(engine(), list_a, list_b, seed, rs, rs, None, FEATURE_SET, epsilon, ev, ev, False)
    r["deck_a"], r["deck_b"], r["seed"] = deck_a, deck_b, seed
    return r


@dataclasses.dataclass
class Rec:
    deck_a: str; deck_b: str; seed: int; first_player: str; winner: object; reason: str; turns: int; actions: tuple


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out")
    p.add_argument("games", type=int)
    p.add_argument("--spec", default=DEFAULT_SPEC)
    p.add_argument("--jobs", type=int, default=7)
    p.add_argument("--seed", type=int, default=20261102)
    p.add_argument("--epsilon", type=float, default=0.05)
    a = p.parse_args()
    decks = json.load(open(DECKS_PATH))
    names = sorted(decks)
    pairs = [(x, y) for i, x in enumerate(names) for y in names[i:]]
    jobs = [(x, y, decks[x], decks[y], a.seed + i * 1000 + k, a.spec, a.epsilon)
            for i, (x, y) in enumerate(pairs) for k in range(math.ceil(a.games / len(pairs)))]
    random.Random(a.seed).shuffle(jobs)
    jobs = jobs[:a.games]
    out = a.out
    cols = {k: [] for k in ("x", "y", "turn", "deck", "opp", "game", "reason")}
    scols = {k: [] for k in cols}
    feat = np.array(features.feature_names(FEATURE_SET))

    def save(suffix):
        for stem, c in ((out + "_out", cols), (out + "_search", scols)):
            tmp = stem + suffix + ".tmp.npz"       # written whole, then renamed: a run killed mid-save keeps its last checkpoint
            np.savez_compressed(tmp, x=np.array(c["x"], dtype=np.float32), y=np.array(c["y"]), turn=np.array(c["turn"]),
                                deck=np.array(c["deck"]), opp=np.array(c["opp"]), game=np.array(c["game"]), reason=np.array(c["reason"]),
                                features=feat, feature_set=np.array(FEATURE_SET), eval_path=np.array(""), pilot=np.array(a.spec), pilot_b=np.array(""))
            os.replace(tmp, stem + suffix)

    w = JsonlGameWriter(Path(out + ".jsonl"))
    t0 = time.time(); n = 0
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for r in ex.map(play, jobs, chunksize=1):
            n += 1
            rec = Rec(r["deck_a"], r["deck_b"], r["seed"], r["first_player"], r["winner"], r["reason"], r["turns"], tuple(r["actions"]))
            w.append(game_log_record(rec, map_id="map_b", bots=(a.spec, a.spec)))
            dk = {"A": r["deck_a"], "B": r["deck_b"]}
            for x, y, t, seat, v in zip(r["x"], r["y"], r["turn"], r["seat"], r["value"]):
                targets = [(cols, y)]
                if v is not None:
                    targets.append((scols, 1 / (1 + math.exp(-max(-30.0, min(30.0, v / POINTS_PER_LOGIT))))))
                for c, lab in targets:
                    c["x"].append(x); c["y"].append(lab); c["turn"].append(t); c["deck"].append(dk[seat])
                    c["opp"].append(dk["B" if seat == "A" else "A"]); c["game"].append(r["seed"]); c["reason"].append(r["reason"])
            if n % 20 == 0:
                el = time.time() - t0
                print(f"  {n}/{len(jobs)} games  {el:.0f}s  {n / el * 3600:.0f} games/h  {len(cols['x'])} positions, "
                      f"{len(scols['x'])} search-labelled", file=sys.stderr, flush=True)
            if n % 200 == 0:
                save(".partial.npz")
    w.close()
    save(".npz")
    print(f"done: {n} games, {len(cols['x'])} positions, {len(scols['x'])} search-labelled, {time.time() - t0:.0f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
