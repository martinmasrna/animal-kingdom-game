// Back into a match from anywhere (Martin, 2026-10-01): a tab that never held the match, opening the game, lands in it.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser.close(); server.stop(); });

test('opening the game in a new tab takes you back into the match you are playing against a person', async () => {
  const one = await browser.newPage();
  await one.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  const id = await one.evaluate(async () => {
    const r = await fetch('/api/match', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-AK-Key': localStorage.getItem('ak:key') },
      body: JSON.stringify({ deck: 'cats_midrange' }) });
    const id = (await r.json()).id;   // a friend joins: a match between two people, which always brings you back
    await fetch(`/api/match/${id}/join`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ deck: 'ramp', name: 'Friend' }) });
    return id; });
  await one.close();   // the tab, and its seat token, are gone
  const two = await browser.newPage();
  await two.goto(`${server.url}/#/`, { waitUntil: 'domcontentloaded' });
  await two.waitForFunction(m => location.hash === '#/m/' + m && window.__ak().V, { timeout: 8000 }, id);
  assert.equal(await two.evaluate(() => window.__ak().V.you), 'A', 'in your own seat');
  const three = await browser.newPage();   // the match's link opened in a fresh tab works too
  await three.goto(`${server.url}/#/m/${id}`, { waitUntil: 'domcontentloaded' });
  await three.waitForFunction(() => window.__ak().V, { timeout: 8000 });
  assert.equal(await three.evaluate(() => location.hash), '#/m/' + id);
});
