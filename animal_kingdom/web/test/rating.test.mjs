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
