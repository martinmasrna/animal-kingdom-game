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

test('game: a hold opens a hand card large until a tap, and picks nothing; a held or tapped piece opens its stack in the middle', async () => {
  await page.goto(`${server.url}/#/lab/mid`, { waitUntil: 'networkidle0' }); await wait(600);
  const up = await hold('.hc');
  assert.ok(await page.$('.readov .card'), 'the held card opens large');
  await up();
  assert.ok(await page.$('.readov'), 'and stays after the finger lifts');
  assert.equal(await page.$$eval('.hc.sel', e => e.length), 0, 'releasing a hold picks nothing');
  await page.tap('.readov'); await wait(200);
  assert.equal(await page.$('.readov'), null, 'a tap closes it');
  assert.equal(await page.$$eval('.hc.sel', e => e.length), 0, 'and picks nothing either');
  await page.tap('.hc'); await wait(300);   // the card held a moment ago still picks with a plain tap
  assert.equal(await page.$$eval('.hc.sel', e => e.length), 1, 'a tap after a hold picks the card');
  await page.tap('.hc'); await wait(300);   // and a second tap puts it back
  assert.equal(await page.$$eval('.hc.sel', e => e.length), 0);
  const cr = await page.evaluate(() => Object.entries(window.__ak().V.game.board).find(([, st]) => st && st.length)[0]);
  const up2 = await hold(`#board [data-cr="${cr}"]`);
  assert.ok(await page.$('.readov .sc .card'), 'a held piece opens its stack in the middle');
  await up2();
  const box = await page.$eval('.readov .card', e => { const r = e.getBoundingClientRect(); return [r.left, r.right]; });
  assert.ok(box[0] >= 0 && box[1] <= 390, `on screen (${box})`);
  await page.tap('.readov'); await wait(200);
  await page.tap(`#board [data-cr="${cr}"]`); await wait(300);
  assert.ok(await page.$('.readov .sc'), 'a tap on a piece reads it too');
  await page.tap('.readov'); await wait(200);
  assert.equal(await page.$('.readov'), null);
});

test('game: holding the deck opens your decklist and draws nothing; a tap beside it closes it', async () => {
  await page.goto(`${server.url}/#/lab/mid`, { waitUntil: 'networkidle0' }); await wait(600);
  const n = await page.$$eval('.hc', e => e.length);
  const up = await hold('#deck');
  assert.ok(await page.$eval('#mine', e => e.classList.contains('on')), 'the held deck opens your decklist');
  await up();
  assert.ok(await page.$eval('#mine', e => e.classList.contains('on')), 'and it stays after the finger lifts');
  assert.equal(await page.$$eval('.hc', e => e.length), n, 'releasing the hold draws nothing');
  const box = await page.$eval('#mine', e => { const r = e.getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom]; });
  assert.ok(box[0] >= 0 && box[1] <= 390 && box[2] >= 0 && box[3] <= 844, `on screen (${box})`);
  await page.screenshot({ path: process.env.SHOT || '/dev/null' });
  await page.tap('#board'); await wait(300);
  assert.ok(!(await page.$eval('#mine', e => e.classList.contains('on'))), 'a tap beside it closes it');
});

test('a laptop with a touchscreen or pen (a Surface): a pen hold reads a hand card, and so does a right-click', async () => {
  await page.setViewport({ width: 1512, height: 800 });   // a computer: hover and a mouse, plus a pen
  await page.goto(`${server.url}/#/lab/mid`, { waitUntil: 'networkidle0' }); await wait(600);
  const [x, y] = await page.$eval('.hc', e => { const r = e.getBoundingClientRect(); return [r.x + 20, r.y + r.height / 2]; });
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1, pointerType: 'pen' });
  await wait(600);
  assert.ok(await page.$('.readov .card'), 'a held pen reads the card');
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1, pointerType: 'pen' }); await wait(300);
  assert.ok(await page.$('.readov'), 'and it stays after the pen lifts');
  assert.equal(await page.$$eval('.hc.sel', e => e.length), 0, 'picking nothing');
  await page.mouse.click(30, 30); await wait(300);
  assert.equal(await page.$('.readov'), null, 'a click closes it');
  await page.mouse.click(x, y, { button: 'right' }); await wait(300);
  assert.ok(await page.$('.readov .card'), 'a right-click reads the card');
  await page.mouse.click(30, 30); await wait(300);
  assert.equal(await page.$('.readov'), null);
  await page.mouse.click(x, y); await wait(300);
  assert.equal(await page.$$eval('.hc.sel', e => e.length), 1, 'and a plain click still picks it');
});
