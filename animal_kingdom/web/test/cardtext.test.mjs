// Card text fits three lines on the full card (docs/design/principles.md), measured on the card as drawn:
// Fira Sans Condensed at the full card's size, every card of the seven decks.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });

test('every card text fits three lines on the full card', async () => {
  const page = await browser.newPage();
  await page.goto(`${server.url}/static/lab/card5.html`, { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  const over = await page.evaluate(async () => {
    document.body.className = 'f-fira';
    const { cardHTML } = await import('/static/lab/card3.js');
    const pool = await fetch('/api/pool').then(r => r.json());
    const d = document.createElement('div'); d.className = 's-guide s-read'; document.body.append(d);
    const out = [];
    for (const c of pool.cards.filter(c => c.text)) {
      d.innerHTML = cardHTML(c); d.firstChild.style.setProperty('--w', '320px');
      const q = d.querySelector('.rules p'), lines = Math.round(q.getBoundingClientRect().height / parseFloat(getComputedStyle(q).lineHeight));
      if (lines > 3) out.push(`${c.name} (${lines} lines)`);
    }
    return out;
  });
  assert.deepEqual(over, []);
  await page.close();
});
