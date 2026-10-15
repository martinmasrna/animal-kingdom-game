// Winning on food by a card's food (a Squirrel at 90): its landing and fruit play out before the end shows (the view that
// ends a game used to skip its own animations), and the gem counts 90 -> 100 even while the pointer moves over the board
// (each hover redraw used to cut the count short). Martin, 2026-10-02.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, gamePage } from './harness.mjs';

let server, browser, page;
before(async () => { server = await startServer(); browser = await openBrowser(); page = await gamePage(browser, server.url, { still: false }); });
after(async () => { await browser?.close(); server?.stop(); });
const wait = ms => new Promise(r => setTimeout(r, ms));

test('a food win plays its last move before the end shows, and the gem counts through hover redraws', async () => {
  await page.evaluate(async () => { const v = await fetch('/static/lab/mid.json').then(r => r.json()); window.__base = v;
    v.version += 10; v.game.food[v.you] = 90; v.game.events = [{ e: 'turn_start', player: v.you, seq: 1 }]; window.__ak.feed(v); });
  await wait(1200);
  await page.evaluate(() => { const v = JSON.parse(JSON.stringify(window.__base)), o = v.you === 'A' ? 'B' : 'A';
    v.version += 20; v.game.food[v.you] = 100; v.phase = 'match_over'; v.results = [{ winner: v.you }]; v.score = { [v.you]: 1, [o]: 0 };
    v.game.result = { winner: v.you, reason: 'food' }; v.game.board['5,3'] = [{ iid: 950, id: 'squirrel', owner: v.you, str: 2 }];
    v.game.events = [{ e: 'turn_start', player: v.you, seq: 1 }, { e: 'place', player: v.you, iid: 950, card: 'squirrel', cr: '5,3', from_hand: true, seq: 2 },
      { e: 'food', player: v.you, n: 10, seq: 3 }];
    window.__ak.feed(v); window.__ak().ui.sel = (v.game.hand[0] || {}).id; });
  const seen = [];
  let endEarly = false;
  for (let k = 0; k < 40; k++) {
    await page.mouse.move(600 + (k % 10) * 20, 300 + (k % 3) * 15);
    const s = await page.evaluate(() => { const gem = [...document.querySelectorAll('.dcount')].find(g => g.dataset.to === '100');
      return { n: gem ? +[...gem.querySelectorAll('img')].map(i => i.alt).join('') : null, busy: window.__ak().PB.busy, end: document.getElementById('endov').classList.contains('on') }; });
    if (s.busy && s.end) endEarly = true;
    if (s.n != null) seen.push(s.n);
    await wait(40);
  }
  assert.ok(!endEarly, 'the end waits for the last move to play');
  assert.ok(seen.some(n => n > 90 && n < 100), `the gem counts through (saw ${[...new Set(seen)].join(' ')})`);
  for (let i = 1; i < seen.length; i++) assert.ok(seen[i] >= seen[i - 1], 'never back down');
  await page.waitForFunction(() => document.getElementById('endov').classList.contains('on'), { timeout: 4000 });   // then the end shows
});
