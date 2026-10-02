#!/usr/bin/env bash
# Deploy the committed HEAD to Fly.io (never the working tree, which may hold other work in progress).
#   deploy/deploy.sh            build and release HEAD
#   deploy/deploy.sh pull       copy the server's human game logs into results/human_games/web/
#   deploy/deploy.sh feedback   pull every feedback message into results/feedback.jsonl, print the new ones
#   deploy/deploy.sh players    pull who played what (profiles, match histories, events) into results/players.json
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cfg="$repo/deploy/fly.toml"
app="$(sed -n 's/^app = "\(.*\)"/\1/p' "$cfg")"

if [[ "${1:-}" == "pull" ]]; then
  fly ssh console -a "$app" -q -C "sh -c 'cd /app/results && tar -czf - human_games | base64'" | base64 -d | tar -xzf - -C "$repo/results"
  echo "pulled into $repo/results/human_games/ (commit them)"
  exit 0
fi

if [[ "${1:-}" == "feedback" ]]; then
  # Every feedback message (with its context and view) into the untracked results/feedback.jsonl; prints the ones new since the last pull.
  out="$repo/results/feedback.jsonl"; last="$( [[ -s "$out" ]] && tail -1 "$out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sent"])' || echo 0)"
  fly ssh console -a "$app" -q -C "python3 -c \"import sqlite3,json; db=sqlite3.connect('/app/results/web.db'); [print(json.dumps(dict(zip(('sent','profile','sender','text','context','view'),r)))) for r in db.execute('SELECT * FROM feedback ORDER BY sent')]\"" > "$out.tmp"
  mv "$out.tmp" "$out"
  python3 - "$out" "$last" <<'PY'
import json, sys, time
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
new = [r for r in rows if r["sent"] > float(sys.argv[2])]
print(f"{len(rows)} messages, {len(new)} new")
for r in new:
    ctx = json.loads(r["context"])
    print(f"\n{time.strftime('%Y-%m-%d %H:%M', time.localtime(r['sent']))}  {r['sender']}  {ctx}{'  +view' if r['view'] else ''}\n{r['text']}")
PY
  exit 0
fi

if [[ "${1:-}" == "players" ]]; then
  # Who played what: every profile (name#tag, when created; never keys or sign-ins), every match in its history and what
  # players did (web/events.py),
  # into the untracked results/players.json, to read the game logs player by player.
  out="$repo/results/players.json"
  fly ssh console -a "$app" -q -C "python3 -c \"import sqlite3,json; db=sqlite3.connect('/app/results/web.db'); db.row_factory=sqlite3.Row; print(json.dumps({'profiles': [dict(r) for r in db.execute('SELECT id, name, tag, created FROM profiles')], 'history': [dict(r) for r in db.execute('SELECT * FROM history ORDER BY ended')], 'events': [dict(r) for r in db.execute('SELECT * FROM events ORDER BY t')] if db.execute(\\\"SELECT 1 FROM sqlite_master WHERE name='events'\\\").fetchone() else []}))\"" > "$out.tmp"
  mv "$out.tmp" "$out"
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(len(d['profiles']), 'profiles,', len(d['history']), 'matches in histories,', len(d.get('events', [])), 'events')" "$out"
  exit 0
fi

# News: a change to the rules or the cards after the newest release's day needs its release first (animal_kingdom/web/news/README.md).
# NEWS_OK=1 deploys anyway (a change players won't notice).
latest="$(ls "$repo/animal_kingdom/web/news" | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}\.md$' | sort | tail -1 | cut -c1-10)"
unwritten="$(git -C "$repo" log --since="$latest 23:59:59" --format='  %h %s' -- animal_kingdom/engine animal_kingdom/data/cards.json | cut -c1-110)"
if [[ -n "$unwritten" && -z "${NEWS_OK:-}" ]]; then
  echo "rules or cards changed since the last news ($latest), with no release written for them:"; echo "$unwritten"
  echo "write animal_kingdom/web/news/$(date +%F).md (or NEWS_OK=1 if players won't notice), then deploy again"; exit 1
fi

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
git -C "$repo" archive HEAD animal_kingdom | tar -x -C "$tmp"
cp "$repo/deploy/Dockerfile" "$cfg" "$tmp/"
echo "deploying $(git -C "$repo" log --oneline -1)"
# Fly's deploy sometimes hangs on its own API: give it 10 minutes, then stop it and try once more; a second hang fails loudly.
attempt() {
  fly deploy "$tmp" --config "$tmp/fly.toml" --remote-only & local pid=$! waited=0
  while kill -0 "$pid" 2>/dev/null; do
    if (( waited >= 600 )); then kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; echo "deploy hung for 10 minutes: stopped"; return 124; fi
    sleep 5; waited=$((waited + 5))
  done
  wait "$pid"
}
attempt || { echo "retrying the deploy once"; attempt || { echo "DEPLOY FAILED twice"; exit 1; }; }
