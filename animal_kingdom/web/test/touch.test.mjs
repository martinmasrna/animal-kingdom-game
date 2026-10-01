// Touch reads a card by holding it, as hover does with a mouse (feedback 2026-10-01: on a phone the cards couldn't be read):
// a long press never selects text, and a held finger's natural wobble doesn't cancel the hold.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser, page, cdp;
const wait = ms => new Promise(r => setTimeout(r, ms));
before(async () => { server = await startServer(); browser = await openBrowser(); page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }); cdp = await page.target().createCDPSession(); });
after(async () => { await browser.close(); server.stop(); });

// Press `sel`, wobble a few pixels for 600 ms; returns the release.
async function hold(sel) {
  const [x, y] = await page.$eval(sel, e => { const r = e.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; });
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
  for (let i = 0; i < 6; i++) { await wait(100); await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: x + (i % 2 ? 4 : -4), y: y + 2 }] }); }
  return async () => { await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); await wait(300); };
}

test('collection: a tap reads a card while browsing; while building, a hold reads it and adds nothing', async () => {
  await page.goto(`${server.url}/#/collection`, { waitUntil: 'networkidle0' }); await wait(400);
  assert.equal(await page.evaluate(() => getComputedStyle(document.body).userSelect), 'none', 'a long press selects no text');
  await page.tap('.cgrid .tl'); await wait(300);
  assert.ok(await page.$eval('#cmodal', e => e.classList.contains('zoom')), 'browsing, a tap reads the card');
  await page.evaluate(() => document.querySelector('#cmodal').click()); await wait(200);
  await page.evaluate(() => document.querySelector('.dtile').click()); await wait(400);
  const n = await page.$eval('.fcount b', e => e.textContent);
  await (await hold('.cgrid .tl:nth-child(5)'))();
  assert.ok(await page.$eval('#cmodal', e => e.classList.contains('zoom')), 'a wobbly hold reads it');
  assert.equal(await page.$eval('.fcount b', e => e.textContent), n, 'and adds nothing');
});

test('game: a hold opens a hand card large until a tap, and picks nothing; a held piece shows its stack', async () => {
  await page.goto(`${server.url}/#/lab/mid`, { waitUntil: 'networkidle0' }); await wait(600);
  const up = await hold('.hc');
  assert.ok(await page.$('.readov .card'), 'the held card opens large');
  await up();
  assert.ok(await page.$('.readov'), 'and stays after the finger lifts');
  assert.equal(await page.$$eval('.hc.sel', e => e.length), 0, 'releasing a hold picks nothing');
  await page.tap('.readov'); await wait(200);
  assert.equal(await page.$('.readov'), null, 'a tap closes it');
  assert.equal(await page.$$eval('.hc.sel', e => e.length), 0, 'and picks nothing either');
  const cr = await page.evaluate(() => Object.entries(window.__ak().V.game.board).find(([, st]) => st && st.length)[0]);
  const up2 = await hold(`#board [data-cr="${cr}"]`);
  assert.ok(await page.$eval('#stackpop', e => e.style.display !== 'none'), 'a held piece shows its stack while held');
  await up2();
});
