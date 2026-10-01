// Every card's art has its WebP (what the client loads), made from the current JPEG: run web/art_webp.sh after new art.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, statSync } from 'node:fs';

const dir = new URL('../static/art/', import.meta.url);
// A minute's slack: a fresh checkout writes both files a moment apart.
test('every JPEG has a WebP at least as new', () => {
  const stale = readdirSync(dir).filter(f => f.endsWith('.jpg')).filter(f => {
    try { return statSync(new URL(f.replace(/\.jpg$/, '.webp'), dir)).mtimeMs < statSync(new URL(f, dir)).mtimeMs - 60e3; } catch { return true; } });
  assert.deepEqual(stale, [], 'run animal_kingdom/web/art_webp.sh');
});
