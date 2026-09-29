// Card text fits three lines on the full card (docs/design/principles.md), measured on the card as drawn:
// the real card (static/card.js) at every width the client lays it out (hand 143, choice 180, reveal 220, pop-up 300), every card in the pool.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });

test('every card text fits three lines on the full card', async () => {
  const page = await browser.newPage();
  await page.goto(`${server.url}/#/collection`, { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  const over = await page.evaluate(async () => {
    const { cardHTML } = await import('/static/card.js');
    const pool = await fetch('/api/pool').then(r => r.json());
    const d = document.createElement('div'); d.style.cssText = 'position:absolute;left:0;top:0'; document.body.append(d);
    const out = [];
    for (const w of [143, 180, 220, 300]) for (const c of pool.cards.filter(c => c.text)) {
      d.innerHTML = cardHTML(c); d.firstChild.style.setProperty('--w', w + 'px');
      const q = d.querySelector('.ctext p'), lines = Math.round(q.getBoundingClientRect().height / parseFloat(getComputedStyle(q).lineHeight));
      if (lines > 3) out.push(`${c.name} at ${w}px (${lines} lines)`);
    }
    return out;
  });
  assert.deepEqual(over, []);
  await page.close();
});
