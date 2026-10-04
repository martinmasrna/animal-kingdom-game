// A click never waits on an animation (player report 2026-10-04: clicks on cards did nothing while steps were playing,
// the clock running): a press during the 'your turn' step skips to your move, and the card under the pointer is picked.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });

test('a card clicked while your turn is still being announced is picked at once', async () => {
  for (let tries = 0; tries < 12; tries++) {   // a deal where you go first (the opponent's opening otherwise comes first)
    const page = await browser.newPage(); await page.setViewport({ width: 1512, height: 800 });
    await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' }); await page.click('#go');
    await page.waitForSelector('#hand .hc', { timeout: 20000 });
    await page.click('#skip').catch(() => {});   // keep the opening hand
    const yours = await page.waitForFunction(() => { const s = window.__ak(); return s.PB.busy && s.ui.step && s.ui.step.kind === 'yourturn'; }, { timeout: 4000 }).then(() => true, () => false);
    if (!yours) { await page.close(); continue; }
    const b = await (await page.$('#hand .hc')).boundingBox(), x = b.x + b.width / 2, y = b.y + 40;
    await page.mouse.click(x, y, { delay: 80 }); await new Promise(r => setTimeout(r, 100));
    const r = await page.evaluate(([x, y]) => { const s = window.__ak(), el = document.elementFromPoint(x, y).closest('.hc');
      return { busy: s.PB.busy, sel: s.ui.sel, card: el && el.dataset.id, can: el && el.classList.contains('can') }; }, [x, y]);
    await page.close();
    assert.equal(r.busy, false, 'the announcement gave way to your move');
    if (r.can) assert.equal(r.sel, r.card, 'and the playable card under the pointer was picked');
    return;
  }
  assert.fail('no deal where you go first in 12 tries');
});
