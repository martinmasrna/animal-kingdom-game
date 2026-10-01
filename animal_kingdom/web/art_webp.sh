#!/bin/sh
# The client loads card art as WebP (half the bytes of the JPEGs): run after adding or repainting a card's art.
# The JPEGs stay as the source (the design sandbox's pages read them); the fast tests fail while a WebP is missing or stale.
cd "$(dirname "$0")/static/art" || exit 1
for f in *.jpg; do w="${f%.jpg}.webp"; [ "$w" -nt "$f" ] || /opt/homebrew/bin/cwebp -quiet -q 82 -m 6 "$f" -o "$w"; done
