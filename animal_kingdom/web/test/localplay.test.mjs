// A practice match against a bot, from home with no flag, played to its end by clicks on the real game screen (the click
// driver of play.slow.mjs): it plays in the browser with no match socket and no request a move, then is in the match
// history (its replay, which a test server doesn't keep, is test_web_local.py's). When the browser's engine is not the server's, the same match plays on the server and
// lands in the history too.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, offsite } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });

const wait = ms => new Promise(r => setTimeout(r, ms));
const tap = async (page, sel) => { const el = await page.$(sel); if (!el) return false; const b = await el.boundingBox(); if (!b) return false;
  await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2); return true; };
const state = page => page.evaluate(() => { const { V } = window.__ak(), G = V.game;
  return { phase: V.phase, mine: G && G.toAct === V.you, pend: G && G.pending && (G.pending.kind === 'mulligan' ? 'mulligan' : G.pending.mode), version: V.version }; });

async function playOut(page, maxSteps = 600) {
  for (let i = 0; i < maxSteps; i++) {
    const s = await state(page);
    if (s.phase === 'match_over') return;
    if (!s.mine) { await wait(100); continue; }
    if (s.pend === 'mulligan') await tap(page, '#skip');
    else if (s.pend) { if (!(await tap(page, '#board .cr.tgt') || await tap(page, '#board .mouth.tgt') || await tap(page, '#opts [data-o]') ||
        await tap(page, '#hand .hc.pick') || await tap(page, '#opts .hc') || await tap(page, '#choicebar [data-x]') || await tap(page, '#skip') || await tap(page, '#hand .hc.can'))) assert.fail(`stuck on a ${s.pend} choice`); }
    else if ((await page.$$('#hand .hc.can')).length && Math.random() < 0.75) {
      await tap(page, '#hand .hc.can'); await wait(60);
      if (!(await tap(page, '#board .cr.tgt') || await tap(page, '#board .mouth.tgt'))) await page.keyboard.press('Escape');
    } else if (!(await tap(page, '#deck.can'))) { if (!(await tap(page, '#tbtn.can'))) await tap(page, '#hand .hc.can'); }
    await page.waitForFunction(v => window.__ak().V.version !== v, { timeout: 8000 }, s.version).catch(() => {});
  }
  assert.fail('the match did not end');
}

async function openHome(tamper) {
  const page = await browser.newPage(); await page.setViewport({ width: 1512, height: 800 });
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  page.errors = []; page.on('pageerror', e => page.errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error' && !offsite(m) && !/favicon/.test(m.text())) page.errors.push(m.text()); });
  const requests = [];
  page.on('request', q => requests.push(q.method() + ' ' + new URL(q.url()).pathname));
  await page.exposeFunction('akSocket', url => requests.push('WS ' + new URL(url).pathname));   // sockets are no requests to puppeteer
  await page.evaluateOnNewDocument(() => { const W = window.WebSocket;
    window.WebSocket = function (url, p) { window.akSocket(url); return new W(url, p); }; window.WebSocket.prototype = W.prototype; Object.assign(window.WebSocket, W); });
  if (tamper) {   // the server's engine reported as another build's: the browser must not play this match itself
    await page.setRequestInterception(true);
    page.on('request', async q => {
      if (!q.url().endsWith('/api/local/engine')) return q.continue();
      const doc = await (await fetch(q.url())).json();
      q.respond({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...doc, source_hash: 'another' }) });
    });
  }
  await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  return { page, requests };
}

const history = page => page.evaluate(async () => (await (await fetch('/api/me', { headers: { 'X-AK-Key': localStorage.getItem('ak:key') || '' } })).json()).history || []);

async function inHistoryAndReplays(page, before) {
  let h = [];
  for (let i = 0; i < 50 && h.length <= before; i++) { h = await history(page); if (h.length <= before) await wait(100); }   // a local match's log is sent as it ends
  assert.equal(h.length, before + 1, 'the match is in the history');
  assert.equal(h[0].mode, 'practice'); assert.equal(h[0].won + h[0].lost, 1);
  // its replay: a test server keeps none (AK_NO_GAME_LOGS); test_web_local.py builds one from a browser's log
}

test('a practice match from home, no flag: played in the browser to the end by clicks, then in the history', { timeout: 300000 }, async t => {
  const { page, requests } = await openHome(false);
  const engine = await page.evaluate(async () => (await (await fetch('/api/local/engine')).json()).source_hash);
  const built = await page.evaluate(async () => (await (await fetch('/static/wasm/manifest.json')).json()).source_hash);
  if (engine !== built) return t.skip(`the venv's ak_engine (${engine || 'no source hash'}) is not the wasm's engine (${built}): cd engine_rs && ../.venv/bin/maturin develop --release`);
  const before = (await history(page)).length;
  await page.click('#go');
  await page.waitForFunction(() => location.hash === '#/m/local' && window.__ak().V && window.__ak().V.phase === 'playing', { timeout: 20000 });
  const from = requests.length;
  await playOut(page);
  const during = requests.slice(from).filter(q => /^(WS \/ws\/(?!presence)|POST \/api\/match)/.test(q));
  assert.deepEqual(during, [], 'no match socket and no request a move while it played');
  assert.ok(await page.evaluate(() => window.__ak.local().thinkMs.length > 0), 'the bot moved in the browser');
  await inHistoryAndReplays(page, before);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test('when the browser\'s engine is not the server\'s, the match plays on the server and lands in the history', { timeout: 300000 }, async () => {
  const { page, requests } = await openHome(true);
  const before = (await history(page)).length;
  await page.click('#go');
  await page.waitForFunction(() => /^#\/m\/(?!local)/.test(location.hash) && window.__ak().V && window.__ak().V.phase === 'playing', { timeout: 20000 });
  assert.ok(requests.includes('POST /api/match') && requests.some(q => /^WS \/ws\/(?!presence)/.test(q)), 'a server match, over its socket');
  await playOut(page);
  await inHistoryAndReplays(page, before);
  assert.deepEqual(page.errors, []);
  await page.close();
});
