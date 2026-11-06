// A practice match in the browser (the default, static/local/match.js): the game and the bot run on the page, no socket and
// no request a move; the finished match reaches the server and lands in the player's history. A browser engine built from
// other sources than the server's plays the match on the server, as without the flag.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { startServer, openBrowser } from './harness.mjs';

const MANIFEST = join(dirname(fileURLToPath(import.meta.url)), '..', 'static', 'wasm', 'manifest.json');
let server, browser, unplayable = null;   // why local play can't start here, when it can't
before(async () => {
  server = await startServer(); browser = await openBrowser();
  // Local play needs the committed wasm and a server engine built from the same sources (the venv's ak_engine); else the
  // client plays on the server, which the third test covers, and the first two say why they don't run.
  const built = existsSync(MANIFEST) ? JSON.parse(readFileSync(MANIFEST, 'utf8')).source_hash : null;
  const served = (await (await fetch(`${server.url}/api/local/engine`)).json()).source_hash;
  if (!built) unplayable = 'no wasm build in static/wasm: run engine_rs/wasm.sh';
  else if (served !== built) unplayable = `the venv's ak_engine (${served || 'no source hash: built before engine/wasm'}) is not the wasm's engine (${built}): `
    + 'rebuild it, cd engine_rs && ../.venv/bin/maturin develop --release';
});
after(async () => { await browser?.close(); server?.stop(); });

async function localPage() {
  const page = await browser.newPage(); await page.setViewport({ width: 1512, height: 800 });
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);   // each view drawn at once
  await page.evaluateOnNewDocument(() => { window.AK_BOT_PAUSE = 0; });
  const requests = [];
  page.on('request', r => requests.push(r.method() + ' ' + new URL(r.url()).pathname));
  page.errors = []; page.on('pageerror', e => page.errors.push(String(e)));
  return { page, requests };
}

// Plays the human seat at random (keeping the opening hand) until the game ends, or concedes after `concedeAfter` moves.
const playOut = (page, concedeAfter = Infinity) => page.evaluate(async concedeAfter => {
  const L = window.__ak.local(), sleep = ms => new Promise(r => setTimeout(r, ms));
  let mine = 0;
  for (let t0 = Date.now(); Date.now() - t0 < 90000;) {
    const V = window.__ak().V;
    if (L.phase !== 'playing') break;
    const g = V && V.game;
    if (g && g.toAct === 'A' && !window.__ak().PB.busy) {
      if (mine >= concedeAfter) { L.handle({ t: 'concede' }); break; }
      const p = g.pending;
      let action;
      if (p && p.kind === 'mulligan') action = { kind: 'choice', choice: '__skip__' };
      else { const legal = JSON.parse(L.state.legalActions()); action = legal[Math.floor(Math.random() * legal.length)]; }
      L.handle({ t: 'act', action }); mine++;
    }
    await sleep(5);
  }
  await L.flush();
  return { phase: L.phase, mine, saved: L.lastSaved || null, result: window.__ak().V.game.result, actions: L.actions.length,
    botMoves: L.thinkMs.length };
}, concedeAfter);

const history = page => page.evaluate(async () => (await (await fetch('/api/me', { headers: { 'X-AK-Key': localStorage.getItem('ak:key') || '' } })).json()).history || []);

test('a practice match plays in the browser, a full game with no socket, and counts when it ends', async t => {
  if (unplayable) return t.skip(unplayable);
  const { page, requests } = await localPage();
  await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  const before = (await history(page)).length;
  await page.click('#go');
  await page.waitForFunction(() => location.hash === '#/m/local' && window.__ak().V && window.__ak().V.game, { timeout: 20000 });
  await page.waitForSelector('#hand .hc');
  const r = await playOut(page);
  assert.equal(r.phase, 'match_over', 'the game was played to its end');
  assert.ok(r.result && r.result.reason !== 'concede' && r.botMoves > 0 && r.actions > 10);
  assert.ok(r.saved, 'the server took the finished match');
  const asked = requests.filter(q => /^(GET|POST) \/(ws\/(?!presence)|api\/match)/.test(q));
  assert.deepEqual(asked, [], 'no match socket and no server match');
  const h = await history(page), row = h.find(x => x.match.startsWith(r.saved + '-'));
  assert.equal(h.length, before + 1, 'the match is in the history');
  assert.equal(row.mode, 'practice'); assert.equal(row.won + row.lost, 1);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test('a conceded local game counts as a loss', async t => {
  if (unplayable) return t.skip(unplayable);
  const { page } = await localPage();
  await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await page.click('#go');
  await page.waitForFunction(() => location.hash === '#/m/local' && window.__ak().V && window.__ak().V.game, { timeout: 20000 });
  const r = await playOut(page, 6);
  assert.equal(r.result.reason, 'concede', JSON.stringify(r)); assert.equal(r.result.winner, 'B'); assert.ok(r.saved);
  const row = (await history(page)).find(x => x.match.startsWith(r.saved + '-'));
  assert.ok(row, 'the match is in the history'); assert.equal(row.won, 0); assert.equal(row.lost, 1);
  await page.close();
});

test('a browser engine that is not the server\'s plays the match on the server', async () => {
  const { page, requests } = await localPage();
  await page.setRequestInterception(true);
  page.on('request', async q => {
    if (!q.url().endsWith('/api/local/engine')) return q.continue();
    const r = await fetch(q.url()), doc = await r.json();
    q.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...doc, source_hash: 'another' }) });
  });
  await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await page.click('#go');
  await page.waitForFunction(() => /^#\/m\/(?!local)/.test(location.hash) && window.__ak().V && window.__ak().V.game, { timeout: 20000 });
  assert.ok(requests.includes('POST /api/match'));
  await page.close();
});
