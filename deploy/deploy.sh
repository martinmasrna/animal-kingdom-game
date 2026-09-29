#!/usr/bin/env bash
# Deploy the committed HEAD to Fly.io (never the working tree, which may hold other work in progress).
#   deploy/deploy.sh            build and release HEAD
#   deploy/deploy.sh pull       copy the server's human game logs into results/human_games/web/
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cfg="$repo/deploy/fly.toml"
app="$(sed -n 's/^app = "\(.*\)"/\1/p' "$cfg")"

if [[ "${1:-}" == "pull" ]]; then
  fly ssh console -a "$app" -q -C "sh -c 'cd /app/results && tar -czf - human_games | base64'" | base64 -d | tar -xzf - -C "$repo/results"
  echo "pulled into $repo/results/human_games/ (commit them)"
  exit 0
fi

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
git -C "$repo" archive HEAD animal_kingdom | tar -x -C "$tmp"
cp "$repo/deploy/Dockerfile" "$cfg" "$tmp/"
echo "deploying $(git -C "$repo" log --oneline -1)"
fly deploy "$tmp" --config "$tmp/fly.toml" --remote-only
