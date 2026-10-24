#!/usr/bin/env bash
# Every night (launchd, deploy/com.animal-kingdom.nightly.plist): the human games from the live app and from staging into
# results/human_games/, committed and pushed, so the playtest record never waits on a session remembering
# `deploy/deploy.sh pull`. Commits only that folder, by path: other sessions' work in the tree is never swept in.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.fly/bin:$PATH"
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "== $(date '+%F %T')"
"$repo/deploy/deploy.sh" pull || echo "live pull failed"
"$repo/deploy/deploy.sh" pull staging || echo "staging pull failed"
git -C "$repo" add results/human_games
if git -C "$repo" diff --cached --quiet -- results/human_games; then echo "no new games"; exit 0; fi
n="$(git -C "$repo" diff --cached --name-only -- results/human_games | wc -l | tr -d ' ')"
git -C "$repo" commit -q -m "Human games pulled from live and staging, $(date +%F) (deploy/nightly.sh): $n files" -- results/human_games \
  && git -C "$repo" push -q || echo "commit or push failed: the games stay in results/human_games for the next session"
echo "committed $n files"
