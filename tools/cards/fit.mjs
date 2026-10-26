// How many lines a card's text takes on the real card (static/card.js) at every width the client draws it, the way
// the web suite's cardtext.test.mjs measures the pool. Called by tools/cards/check.py with the card as JSON; prints
// {"143": lines, "180": lines, "220": lines, "300": lines} on the last line.
import { startServer, openBrowser } from '../../animal_kingdom/web/test/harness.mjs';

const card = JSON.parse(process.argv[2]);
const server = await startServer();
const browser = await openBrowser();
try {
  const page = await browser.newPage();
  await page.goto(`${server.url}/#/collection`, { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  const res = await page.evaluate(async c => {
    const { cardHTML } = await import('/static/card.js');
    const d = document.createElement('div'); d.style.cssText = 'position:absolute;left:0;top:0'; document.body.append(d);
    const out = {};
    for (const w of [143, 180, 220, 300]) {
      d.innerHTML = cardHTML(c); d.firstChild.style.setProperty('--w', w + 'px');
      const q = d.querySelector('.ctext p');
      out[w] = q ? Math.round(q.getBoundingClientRect().height / parseFloat(getComputedStyle(q).lineHeight)) : 0;
    }
    return out;
  }, card);
  console.log(JSON.stringify(res));
} finally {
  await browser.close(); server.stop();
}
