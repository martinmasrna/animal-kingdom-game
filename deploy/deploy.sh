#!/usr/bin/env bash
# Deploy the committed HEAD to Fly.io (never the working tree, which may hold other work in progress).
#   deploy/deploy.sh            build and release HEAD to the live app
#   deploy/deploy.sh staging    the same build to the staging app (deploy/fly.staging.toml): where Martin tests work that
#                               isn't released yet, from any device; it sleeps when idle. No news check: nobody else plays there.
#   deploy/deploy.sh pull [staging]   copy the server's human game logs into results/human_games/web/ (deploy/nightly.sh
#                               does it every night for both)
#   deploy/deploy.sh feedback   pull every feedback message into results/feedback.jsonl, print the new ones
#   deploy/deploy.sh players    pull who played what (profiles, match histories, their saved decks, events) into results/players.json
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# The Fly CLI: `fly` on the Mac, `flyctl` where winget installed it (Windows; its folder joins PATH only in new shells).
FLY="$(command -v fly || command -v flyctl || ls "${LOCALAPPDATA:-}"/Microsoft/WinGet/Packages/Fly-io.flyctl_*/flyctl.exe 2>/dev/null | head -1 || true)"
[[ -n "$FLY" ]] || { echo "the Fly CLI is not installed (winget install Fly-io.flyctl, then flyctl auth login)"; exit 1; }
fly() { "$FLY" "$@"; }
cfg="$repo/deploy/fly.toml"
target=live
if [[ "${1:-}" == "staging" ]]; then target=staging; shift; fi
if [[ "${1:-}" == "pull" && "${2:-}" == "staging" ]]; then target=staging; fi
[[ "$target" == staging ]] && cfg="$repo/deploy/fly.staging.toml"
app="$(sed -n 's/^app = "\(.*\)"/\1/p' "$cfg")"

if [[ "${1:-}" == "pull" ]]; then
  # staging: only its games (its web_decks.json would overwrite the live one); a sleeping machine is woken first
  files="human_games web_decks.json"
  if [[ "$target" == staging ]]; then
    files="human_games"
    for m in $(fly machine list -a "$app" --json | python3 -c 'import json,sys; print(*(m["id"] for m in json.load(sys.stdin)))'); do
      fly machine start -a "$app" "$m" >/dev/null 2>&1 || true
    done
    sleep 5
  fi
  fly ssh console -a "$app" -q -C "sh -c 'cd /app/results && tar -czf - $files 2>/dev/null | base64'" | base64 -d | tar -xzf - -C "$repo/results"
  echo "pulled into $repo/results/human_games/ (commit them) and results/web_decks.json (the decks people played under their own names)"
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
  fly ssh console -a "$app" -q -C "python3 -c \"import sqlite3,json; db=sqlite3.connect('/app/results/web.db'); db.row_factory=sqlite3.Row; print(json.dumps({'profiles': [dict(r) for r in db.execute('SELECT id, name, tag, created FROM profiles')], 'history': [dict(r) for r in db.execute('SELECT * FROM history ORDER BY ended')], 'decks': [dict(r) for r in db.execute('SELECT profile, id, name, cards, pos FROM decks ORDER BY profile, pos')], 'events': [dict(r) for r in db.execute('SELECT * FROM events ORDER BY t')] if db.execute(\\\"SELECT 1 FROM sqlite_master WHERE name='events'\\\").fetchone() else []}))\"" > "$out.tmp"
  mv "$out.tmp" "$out"
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(len(d['profiles']), 'profiles,', len(d['history']), 'matches in histories,', len(d.get('events', [])), 'events')" "$out"
  exit 0
fi

# News: a change to the rules or the cards after the newest release's day needs its release first (animal_kingdom/web/news/README.md).
# NEWS_OK=1 deploys anyway (a change players won't notice).
latest="$(ls "$repo/animal_kingdom/web/news" | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}\.md$' | sort | tail -1 | cut -c1-10)"
# a release covers its day until 06:00 the next morning (a night's session belongs to the day it began)
cutoff="$(date -j -v+1d -f %Y-%m-%d "$latest" +%Y-%m-%d 2>/dev/null || date -d "$latest +1 day" +%Y-%m-%d) 06:00:00"
unwritten="$(git -C "$repo" log --since="$cutoff" --format='  %h %s' -- animal_kingdom/engine animal_kingdom/data/cards.json | cut -c1-110)"
if [[ -n "$unwritten" && -z "${NEWS_OK:-}" && "$target" == live ]]; then
  echo "rules or cards changed since the last news ($latest), with no release written for them:"; echo "$unwritten"
  echo "write animal_kingdom/web/news/$(date -v-6H +%F 2>/dev/null || date -d "-6 hours" +%F).md (or NEWS_OK=1 if players won't notice), then deploy again"; exit 1
fi

# The web client's fast suite gates the deploy here (SKIP_TESTS=1 when it just passed); the Python fast tier runs in the
# image's build, against the compiled engine that ships (deploy/Dockerfile).
[[ -n "${SKIP_TESTS:-}" ]] || (cd "$repo/animal_kingdom/web/test" && node --test > /tmp/ak-deploy-web.txt 2>&1) \
  || { grep -vE '^# Subtest|^ok ' /tmp/ak-deploy-web.txt | tail -40; echo "web tests failed: not deploying"; exit 1; }

# one deploy at a time across sessions; a lock left by a killed deploy is taken over
cache="${XDG_CACHE_HOME:-$HOME/.cache}/animal-kingdom-deploy"; lock="$cache.lock"; mkdir -p "$cache"
until mkdir "$lock" 2>/dev/null; do
  kill -0 "$(cat "$lock/pid" 2>/dev/null)" 2>/dev/null || { rm -rf "$lock"; continue; }
  echo "another deploy is running: waiting"; sleep 10
done
echo $$ > "$lock/pid"
tmp="$(mktemp -d)"; trap 'rm -rf "$lock" "$tmp"' EXIT

# Fly's deploy sometimes hangs on its own API: give it 20 minutes, then stop it and try once more; a second hang fails loudly.
attempt() {
  fly deploy "$@" & local pid=$! waited=0
  while kill -0 "$pid" 2>/dev/null; do
    if (( waited >= 1200 )); then kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; echo "deploy hung for 20 minutes: stopped"; return 124; fi
    sleep 5; waited=$((waited + 5))
  done
  wait "$pid"
}
retry() { attempt "$@" || { echo "retrying once"; attempt "$@" || { echo "DEPLOY FAILED twice"; exit 1; }; }; }

# The paintings (static/art, static/kit2: 81 of the 85 MB) ship as their own image, built and pushed only when they change,
# keyed by their git trees; the app's build copies them from it, so a card or code change uploads a few MB. The Fly builder
# keeps no context between builds, so without this every deploy sent all of it (two minutes, ten on a slow line).
art="art-$(git -C "$repo" rev-parse HEAD:animal_kingdom/web/static/art HEAD:animal_kingdom/web/static/kit2 | shasum | cut -c1-16)"
artmark="$cache/art"; [[ "$target" == staging ]] && artmark="$cache/art-staging"   # each app's registry holds its own copy
if [[ "$(cat "$artmark" 2>/dev/null)" != "$art" ]]; then
  echo "the paintings changed: pushing them as $art"
  mkdir -p "$tmp/art"
  git -C "$repo" archive HEAD animal_kingdom/web/static/art animal_kingdom/web/static/kit2 | tar -x -C "$tmp/art" --strip-components 3
  printf 'FROM scratch\nCOPY art /art\nCOPY kit2 /kit2\n' > "$tmp/art/Dockerfile"
  cp "$cfg" "$tmp/art/fly.toml"
  retry "$tmp/art" --config "$tmp/art/fly.toml" --dockerfile "$tmp/art/Dockerfile" --remote-only --build-only --push --image-label "$art"
  echo "$art" > "$artmark"
fi

# Four trees for the image (deploy/Dockerfile): code/ (the engine, the bots, the server, the tests), data/ (cards, decks,
# maps), ui/ (the client's static files but the paintings, the news, the studies) and rs/ (the Rust engine and its oracles).
# The compiles run on code/ and rs/ alone, so a card or client change reuses both and pays only the tests.
mkdir -p "$tmp/app/code" "$tmp/app/ui/animal_kingdom/web" "$tmp/app/rs"
git -C "$repo" archive HEAD animal_kingdom | tar -x -C "$tmp/app/code"
git -C "$repo" archive HEAD engine_rs tools/engine_rs | tar -x -C "$tmp/app/rs"
mv "$tmp/app/code/animal_kingdom/data" "$tmp/app/data"
for d in static news studies; do [[ -d "$tmp/app/code/animal_kingdom/web/$d" ]] && mv "$tmp/app/code/animal_kingdom/web/$d" "$tmp/app/ui/animal_kingdom/web/"; done
rm -rf "$tmp/app/ui/animal_kingdom/web/static/art" "$tmp/app/ui/animal_kingdom/web/static/kit2"
cp "$repo/deploy/Dockerfile" "$tmp/app/"; cp "$cfg" "$tmp/app/fly.toml"
echo "deploying $(git -C "$repo" log --oneline -1) to $target ($app)"
retry "$tmp/app" --config "$tmp/app/fly.toml" --remote-only --build-arg "ART=registry.fly.io/$app:$art"
