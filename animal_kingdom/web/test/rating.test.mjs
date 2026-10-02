// A ranked game's end counts the rating from before to after. The server sends the ratings as shown, text ("1781",
// "1500?" while provisional): the count must land on that text, never glue it to a number ("178111", 2026-10-01).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, gamePage } from './harness.mjs';

let server, browser, page;
before(async () => { server = await startServer(); browser = await openBrowser(); page = await gamePage(browser, server.url, { still: false }); });
after(async () => { await browser?.close(); server?.stop(); });

const wait = ms => new Promise(r => setTimeout(r, ms));
const endRanked = rating => page.evaluate(async rating => {
  const v = await fetch('/static/lab/mid.json').then(r => r.json()), o = v.you === 'A' ? 'B' : 'A';
  v.version += 50; v.phase = 'match_over'; v.results = [{ winner: v.you }]; v.score = { [v.you]: 1, [o]: 0 };
  v.game.result = { winner: v.you, reason: 'food' }; v.ranked = true; v.rating = rating; window.__ak.feed(v);
}, rating);

test('a live ranked win counts the rating up to the server\'s number', async () => {
  await endRanked({ before: '1781', after: '1792', delta: 11 });
  await wait(3200);   // the result's entrance, then the count
  assert.equal(await page.$eval('#rnum', e => e.textContent), '1792');
  assert.ok(await page.$eval('#rnum + .rd', e => e.classList.contains('on')), 'the change shows when the count lands');
  assert.deepEqual(page.errors, []);
});

test('a provisional rating ("1500?") counts and lands on the server\'s text, never NaN', async () => {
  await page.goto(page.url().replace(/#.*/, '#/lab/mid'), { waitUntil: 'networkidle0' });
  await endRanked({ before: '1500?', after: '1532?', delta: 32 });
  await wait(1600);
  assert.match(await page.$eval('#rnum', e => e.textContent), /^\d+\??$/, 'mid-count: a number');
  await wait(1600);
  assert.equal(await page.$eval('#rnum', e => e.textContent), '1532?');
  assert.deepEqual(page.errors, []);
});

test('Play again holds still while it searches: the timer counts inside the button, nothing grows or shifts as it ticks', async () => {
  await page.goto(page.url().replace(/#.*/, '#/lab/mid'), { waitUntil: 'networkidle0' });
  await endRanked({ before: '1781', after: '1792', delta: 11 });
  await wait(3200);
  const size = () => page.$eval('#endov .endbox', e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
  const btn = () => page.$eval('#again', e => Math.round(e.getBoundingClientRect().width));
  const was = await size(), b0 = await btn();
  await page.setRequestInterception(true);   // the search never finds anyone here: it stays open while we measure
  const hold = r => { if (r.url().includes('/api/ranked')) return; r.continue(); };
  page.on('request', hold);
  await page.click('#again');
  let label = null;
  for (const t of [300, 1200, 2200, 3200, 4200, 5200, 6200, 7200, 8200, 9200, 10200]) {
    await wait(t === 300 ? 300 : 1000);
    assert.ok(await page.$eval('#again', e => e.classList.contains('searching')), 'searching');
    assert.deepEqual(await size(), was, `the box at ${t} ms`);
    assert.equal(await btn(), b0, `the button at ${t} ms`);
    assert.ok(await page.$eval('#again', e => e.scrollWidth <= e.clientWidth), `its label fits at ${t} ms`);
    const lw = await page.$eval('#again .search', e => e.firstChild.parentElement.getBoundingClientRect().width);
    label ??= lw; assert.equal(lw, label, `the label's width at ${t} ms`);
  }
  page.off('request', hold); await page.setRequestInterception(false);
  assert.deepEqual(page.errors, []);
});
