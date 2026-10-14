#!/usr/bin/env bash
# Deploy the committed HEAD to the staging app (deploy/fly.staging.toml), never the live one. No news check:
# nobody but Martin plays there.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
git -C "$repo" archive HEAD animal_kingdom | tar -x -C "$tmp"
cp "$repo/deploy/Dockerfile" "$tmp/"
cp "$repo/deploy/fly.staging.toml" "$tmp/fly.toml"
echo "deploying $(git -C "$repo" log --oneline -1) to staging"
fly deploy "$tmp" --config "$tmp/fly.toml" --remote-only --ha=false
