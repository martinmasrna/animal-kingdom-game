// Both players mulligan at once in a match between two people (Martin, 2026-10-01): the second player's box is open while
// the first still chooses, a returned card is replaced at once, and the game starts when both are done.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser.close(); server.stop(); });
const wait = ms => new Promise(r => setTimeout(r, ms));

test('two people mulligan at the same time', async () => {
  const post = (url, body) => fetch(server.url + url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(r => r.json());
  const a = await post('/api/match', { deck: 'cats_midrange', name: 'Ann' });
  const b = await post(`/api/match/${a.id}/join`, { deck: 'ramp', name: 'Bob' });
  const open = async m => { const p = await browser.newPage();
    await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
    await p.evaluate(m => sessionStorage.setItem('ak:seat:' + m.id, m.token), m);
    await p.goto(`${server.url}/#/m/${m.id}`); await p.waitForFunction(() => window.__ak().V && window.__ak().V.game, { timeout: 8000 }); await wait(500); return p; };
  const pa = await open(a), pb = await open(b);
  const first = await pa.evaluate(() => window.__ak().V.game.first);
  const [p1, p2] = first === 'A' ? [pa, pb] : [pb, pa];
  const box = p => p.evaluate(() => { const b = document.querySelector('#choicebar.mull b'); return b ? b.textContent : null; });
  assert.match(await box(p1) || '', /0 of 3/, 'the first player mulligans');
  assert.match(await box(p2) || '', /0 of 4/, 'and so does the second, at the same time');
  await p2.evaluate(() => document.querySelector(".hc").click()); await wait(600);
  assert.match(await box(p2) || '', /1 of 4/, 'the second returns a card while the first still chooses');
  await p2.evaluate(() => document.getElementById("skip").click()); await wait(600);
  assert.equal(await p2.evaluate(() => { const g = window.__ak().V.game; return g.decision === 'mulligan' && g.toAct !== window.__ak().V.you; }), true, 'done: waiting for the first');
  await p1.evaluate(() => document.getElementById("skip").click()); await wait(800);
  for (const p of [p1, p2]) assert.equal(await p.evaluate(() => window.__ak().V.game.pending), null, 'the game has begun');
});
