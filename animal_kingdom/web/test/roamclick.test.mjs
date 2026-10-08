// Roaming by hand: an animal that can roam wears a dashed ring; clicking it rings where it may go, clicking one of those
// sends the roam. No real card roams yet, so the lab's frozen view is given a roam by hand.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, feed } from './harness.mjs';

let server, browser, page;
before(async () => {
  server = await startServer(); browser = await openBrowser();
  page = await browser.newPage();
  page.errors = []; page.on('pageerror', e => page.errors.push(e.message));
  await page.goto(`${server.url}/?clicklog#/lab/mid`, { waitUntil: 'networkidle0' });   // ?clicklog shows what is sent
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
});
after(async () => { await browser?.close(); server?.stop(); });

test('click your roaming animal, then where it goes: the roam is sent', async () => {
  const v = await page.evaluate(() => JSON.parse(JSON.stringify(window.__ak().V)));
  const you = v.you, mine = Object.entries(v.game.board).filter(([, st]) => st[st.length - 1].owner === you).map(([cr]) => cr);
  assert.ok(mine.length, 'the lab view has an animal of yours');
  const [c, r] = mine[0].split(',').map(Number), to = `${c},${r === 1 ? 2 : r - 1}`;
  const next = { ...v, game: { ...v.game, toAct: you, current: you, pending: null, decision: 'yours', result: null,
    legal: { draw: false, place: {}, roam: { [mine[0]]: [['cr', to]] } }, events: v.game.events } };
  await feed(page, next);
  const dcr = cr => { if (you === 'A') return cr; const [c, r] = cr.split(','); return `${6 - c},${r}`; };   // map_b: 5 columns, mirrored for B
  const from = dcr(mine[0]), dest = dcr(to);
  assert.ok(await page.$eval(`#board .cr[data-cr="${from}"]`, e => e.classList.contains('roamable')), 'it wears the roam ring');
  await page.click(`#board .cr[data-cr="${from}"]`);
  assert.equal(await page.evaluate(() => window.__ak().ui.roam), from);
  assert.ok(await page.$eval(`#board .cr[data-cr="${dest}"]`, e => e.classList.contains('tgt')), 'its destination rings');
  await page.click(`#board .cr[data-cr="${dest}"]`);
  const log = await page.$eval('#clog', e => e.textContent);
  assert.match(log, new RegExp(`send \\{"kind":"roam","from":"${mine[0]}","target":\\["cr","${to}"\\]`));
  assert.deepEqual(page.errors, []);
});
