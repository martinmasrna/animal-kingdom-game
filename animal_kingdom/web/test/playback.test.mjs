// The timeline played on screen with motion on (the other browser tests run with reduced motion, which skips the steps):
// on a real recorded moment where the opponent plays a card and the turn passes to you, their card is shown large first,
// the piece lands, and only then "Your turn"; nothing can be clicked until the steps have played.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, gamePage, recordMatches } from './harness.mjs';
import { plan } from '../static/timeline.js';

let server, browser, pair;
before(async () => {
  server = await startServer(); browser = await openBrowser();
  for (const { views } of recordMatches(3)) for (let i = 1; i < views.length && !pair; i++) {
    const kinds = plan(views[i - 1], views[i]).map(s => s.step && s.step.kind);
    if (kinds.includes('reveal') && kinds.includes('yourturn')) pair = [views[i - 1], views[i], kinds];
  }
});
after(async () => { await browser.close(); server.stop(); });

test("the opponent's card shows, lands, then 'Your turn'; the controls wait for it", async () => {
  assert.ok(pair, 'a recorded moment with a reveal and your turn');
  const page = await gamePage(browser, server.url, { still: false });
  await page.evaluate(v => window.__ak.feed(v), pair[0]); await new Promise(r => setTimeout(r, 600));
  const t0 = Date.now();
  await page.evaluate(v => window.__ak.feed(v), pair[1]);
  const seen = {};
  for (let i = 0; i < 60 && !seen.final; i++) {
    const s = await page.evaluate(() => ({ reveal: document.getElementById('reveal').classList.contains('on'), plate: !!document.querySelector('.yourturn'),
      land: !!document.querySelector('#board .cr.land'), can: !!document.querySelector('#hand .hc.can'), step: !!window.__ak().ui.step }));
    const t = Date.now() - t0;
    if (s.reveal && seen.reveal === undefined) seen.reveal = t;
    if (s.land && seen.reveal !== undefined && seen.land === undefined) seen.land = t;
    if (s.plate && seen.plate === undefined) seen.plate = t;
    if (s.can && seen.can === undefined) seen.can = t;
    if (!s.step && seen.plate !== undefined) seen.final = t;
    await new Promise(r => setTimeout(r, 80));
  }
  assert.ok(seen.reveal < 300, `their card shows at once (${seen.reveal} ms)`);
  assert.ok(seen.land > seen.reveal, `then it lands (${seen.land} ms)`);
  assert.ok(seen.plate > seen.land, `then "Your turn" (${seen.plate} ms)`);
  assert.ok(seen.can === undefined || seen.can >= seen.plate, `nothing is playable before it (${seen.can} ms)`);
});
