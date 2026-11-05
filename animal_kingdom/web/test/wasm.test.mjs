// The browser build as shipped (static/wasm, engine_rs/wasm.sh): the brotli copy the server sends in its place is the same
// module, and the module loads and plays.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { brotliDecompressSync } from 'node:zlib';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..');
const WASM = join(ROOT, 'animal_kingdom/web/static/wasm');

test('the brotli copy is the module', () => {
  const raw = readFileSync(join(WASM, 'ak_engine_bg.wasm'));
  assert.ok(existsSync(join(WASM, 'ak_engine_bg.wasm.br')), 'engine_rs/wasm.sh writes it');
  assert.ok(brotliDecompressSync(readFileSync(join(WASM, 'ak_engine_bg.wasm.br'))).equals(raw), 'rerun engine_rs/wasm.sh');
});

test('the module plays a game from its first position, its hash the one in its manifest', async () => {
  const ak = await import(join(WASM, 'ak_engine.js'));
  ak.initSync({ module: readFileSync(join(WASM, 'ak_engine_bg.wasm')) });
  assert.equal(ak.sourceHash(), JSON.parse(readFileSync(join(WASM, 'manifest.json'), 'utf8')).source_hash);
  const data = f => readFileSync(join(ROOT, 'animal_kingdom/data', f), 'utf8');
  const PY = process.env.AK_PYTHON || join(ROOT, '.venv', ...(process.platform === 'win32' ? ['Scripts', 'python.exe'] : ['bin', 'python']));
  const config = execFileSync(PY, ['-c', 'import json, dataclasses; from animal_kingdom.engine.config import Config; print(json.dumps(dataclasses.asdict(Config.default())))'], { cwd: ROOT }).toString();
  const engine = new ak.Engine(data('cards.json'), data('maps.json'), config, 'map_b');
  const deck = JSON.stringify(Array(30).fill('lion'));
  const st = engine.newGame(deck, deck, 7, 'A', false), bot = new ak.Bot('greedy', 7, '');
  for (let i = 0; i < 400 && st.isTerminal() === 'null'; i++) st.applyAction(bot.choose(st), true);
  assert.notEqual(st.isTerminal(), 'null', 'thirty Lions a side finish a game');
  assert.equal(JSON.parse(st.view('A')).decision, 'over');
});
