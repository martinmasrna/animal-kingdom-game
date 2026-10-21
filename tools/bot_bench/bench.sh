#!/usr/bin/env bash
# One paired benchmark of a bot change on a frozen checkout (the procedure: .claude/skills/bot-change/SKILL.md).
#   tools/bot_bench/bench.sh run <name> <candidate> [baseline]   freeze origin/main (AT=<commit> for another) and launch in the background
#   tools/bot_bench/bench.sh report <name>                        the per-deck table so far, the pooled mean, done or not
#   tools/bot_bench/bench.sh clean <name>                         remove the run's checkout; the results stay
# A spec is a bot kind string ("referee:depth=1,..."). A candidate starting with "+" appends to the baseline ("+quiesce=true").
# The baseline defaults to the shipped Expert without its time budget, and is the opponent too. GAMES (20) and JOBS (7)
# size the run; AFTER=<name> makes it wait for that run to finish first. Everything of a run lives in results/bot_quality/<name>:
# tree/ (the checkout), run.json (what ran on what), run.sh, run.log, logs/ (every game).
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cmd="${1:-}"; name="${2:-}"
[[ -n "$cmd" && -n "$name" ]] || { sed -n '2,9p' "$0"; exit 1; }
out="$repo/results/bot_quality/$name"; tree="$out/tree"

case "$cmd" in
run)
  cand="${3:?candidate spec}"; base="${4:-}"
  [[ ! -e "$out" ]] || { echo "$out exists: another name, or clean it first"; exit 1; }
  git -C "$repo" fetch -q origin
  at="$(git -C "$repo" rev-parse "${AT:-origin/main}")"
  mkdir -p "$out"
  git -C "$repo" worktree add -q --detach "$tree" "$at"
  ln -s "$repo/.venv" "$tree/.venv"
  py() { (cd "$tree" && PYTHONPATH="$tree" .venv/bin/python "$@"); }
  [[ -n "$base" ]] || base="$(py -c 'import re; from animal_kingdom.web.match import EXPERT; print(re.sub(r"time_budget=\d+", "time_budget=0", EXPERT))')"
  [[ "$cand" == +* ]] && cand="$base,${cand#+}"
  cards="$(git -C "$repo" rev-parse "$at:animal_kingdom/data/cards.json")"
  lists="$(git -C "$repo" rev-parse "$at:animal_kingdom/data/decklists.json")"
  games="${GAMES:-20}"; jobs="${JOBS:-7}"
  python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2], sys.argv[2::2])), indent=2))' \
    commit "$at" cards "$cards" decklists "$lists" candidate "$cand" baseline "$base" games "$games" jobs "$jobs" after "${AFTER:-}" started "$(date '+%Y-%m-%d %H:%M')" > "$out/run.json"
  {
    echo '#!/bin/zsh'
    echo "cd '$tree'"
    [[ -z "${AFTER:-}" ]] || echo "until grep -q '=== done' '$repo/results/bot_quality/$AFTER/run.log' || ! pgrep -f 'bot_quality/$AFTER/run.sh' >/dev/null; do sleep 60; done"
    echo 'echo "=== start $(date)"'
    echo "PYTHONPATH=\$PWD .venv/bin/python -m animal_kingdom.sim.bot_comparison --games $games --jobs $jobs --candidate-kind '$cand' --baseline-kind '$base' --opponent-kind '$base' --out '$out'"
    echo 'echo "=== done $(date)"'
  } > "$out/run.sh"
  nohup zsh "$out/run.sh" > "$out/run.log" 2>&1 &
  echo "$name: ${at:0:8}, cards ${cards:0:8}, $games games a deck${AFTER:+, after $AFTER}; the table grows in $out/run.log"
  ;;
report)
  [[ -f "$out/run.log" ]] || { echo "no run named $name"; exit 1; }
  python3 - "$out" <<'PY'
import json, re, sys, math
out = sys.argv[1]; meta = json.load(open(f"{out}/run.json")); log = open(f"{out}/run.log").read()
rows = {}
for m in re.finditer(r"^([a-z0-9_]+) +([\d.]+)% +([\d.]+)% +([+-][\d.]+)% \[ *([+-][\d.]+)%, *([+-][\d.]+)%\]", log, re.M):
    rows[m[1]] = tuple(float(x) for x in m.groups()[1:])
print(f"{meta['candidate']}\n  vs {meta['baseline']}\n  on {meta['commit'][:8]} (cards {meta['cards'][:8]}), {meta['games']} games a deck, started {meta['started']}")
print("done" if "=== done" in log else f"running, {len(rows)} decks so far")
for d, (b, c, delta, lo, hi) in sorted(rows.items(), key=lambda r: -r[1][2]):
    print(f"  {d:<16}{b:5.1f} -> {c:5.1f}  {delta:+5.1f}  [{lo:+5.1f}, {hi:+5.1f}]{'  clear' if lo > 0 or hi < 0 else ''}")
if rows:
    n = len(rows); mean = sum(r[2] for r in rows.values()) / n
    se = math.sqrt(sum(((r[4] - r[3]) / 3.92) ** 2 for r in rows.values())) / n
    print(f"  mean {mean:+.1f} points over {n} decks, 95% interval {mean - 1.96 * se:+.1f} to {mean + 1.96 * se:+.1f}")
PY
  ;;
clean)
  [[ -d "$tree" ]] && git -C "$repo" worktree remove --force "$tree" && echo "removed $tree" || echo "no checkout at $tree"
  ;;
*) sed -n '2,9p' "$0"; exit 1 ;;
esac
