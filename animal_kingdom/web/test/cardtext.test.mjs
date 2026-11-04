// Card text fits its panel on the full card, measured on the card as drawn: the real card (static/card.js) at every width
// the client lays it out (hand 143, choice 180, reveal 220, pop-up 300), every card in the pool. A long effect sets smaller
// (fitNames) instead of running into the family line: length is no constraint on a card (Martin, 2026-10-30).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });

test('every card text fits its panel on the full card', async () => {
  const page = await browser.newPage();
  await page.goto(`${server.url}/#/collection`, { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  const over = await page.evaluate(async () => {
    const { cardHTML, fitNames } = await import('/static/card.js');
    const pool = await fetch('/api/pool').then(r => r.json());
    const d = document.createElement('div'); d.style.cssText = 'position:absolute;left:0;top:0'; document.body.append(d);
    const out = [];
    for (const w of [143, 180, 220, 300]) for (const c of pool.cards.filter(c => c.text)) {
      d.innerHTML = cardHTML(c); d.firstChild.style.setProperty('--w', w + 'px'); fitNames(d);
      const q = d.querySelector('.ctext p'), box = q.parentElement, cs = getComputedStyle(box);
      const room = box.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      if (q.offsetHeight > room + 1) out.push(`${c.name} at ${w}px (${q.offsetHeight}px of ${room})`);
    }
    return out;
  });
  assert.deepEqual(over, []);
  await page.close();
});
