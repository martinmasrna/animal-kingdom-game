// The game screen's controls do what they say: each opens its own panel, Escape backs out, painted controls keep their
// image on hover, and the menus stay usable in a short window.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, gamePage } from './harness.mjs';

let server, browser, page;
before(async () => { server = await startServer(); browser = await openBrowser(); page = await gamePage(browser, server.url); });
after(async () => { await browser?.close(); server?.stop(); });

const wait = ms => new Promise(r => setTimeout(r, ms));
const shown = sel => page.$eval(sel, e => getComputedStyle(e).display !== 'none');
const clickAt = async sel => { const b = await (await page.$(sel)).boundingBox(); await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2); await wait(80); };
const away = async () => { await page.mouse.click(760, 330); await wait(80); };

test('the series opens the history, the card backs the opponent\'s decklist', async () => {
  await clickAt('#series');
  assert.ok(await shown('#histp'), 'history open'); assert.ok(!(await shown('#theirs')), 'not their decklist');
  await away(); assert.ok(!(await shown('#histp')), 'a click elsewhere closes it');
  await clickAt('#opphand .back');
  assert.ok(await shown('#theirs'), 'their decklist open');
  await away();
});

test('hovering your deck shows your decklist', async () => {
  const b = await (await page.$('#deck')).boundingBox(); await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await wait(80);
  assert.ok(await shown('#mine')); await page.mouse.move(2, 2); await wait(80);
  assert.ok(!(await shown('#mine')));
});

test('Escape closes the menu, then a panel, then deselects the card', async () => {
  await clickAt('#menubtn'); assert.ok(await page.$eval('#menudrop', e => e.classList.contains('on')));
  await page.keyboard.press('Escape'); await wait(60);
  assert.ok(!(await page.$eval('#menudrop', e => e.classList.contains('on'))), 'menu closed');
  await clickAt('#series'); await page.keyboard.press('Escape'); await wait(60);
  assert.ok(!(await shown('#histp')), 'panel closed');
  await clickAt('#hand .hc.can'); await page.mouse.move(2, 2); await wait(60);
  assert.ok(await page.$('#hand .hc.sel'), 'a card is selected');
  await page.keyboard.press('Escape'); await wait(60);
  assert.equal(await page.$('#hand .hc.sel'), null, 'deselected');
});

test('End turn and the deck keep their painting on hover', async () => {
  for (const [sel, img] of [['#tbtn', 'btn_a'], ['#deck', 'deck']]) {
    const b = await (await page.$(sel)).boundingBox(); await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await wait(80);
    assert.match(await page.$eval(sel, e => getComputedStyle(e).backgroundImage), new RegExp(img), sel);
  }
  await page.mouse.move(2, 2);
});

test('the deck list on the play screen scrolls in a short window, so every deck can be picked', async () => {
  const p = await browser.newPage(); await p.setViewport({ width: 900, height: 800 });
  await p.goto(`${server.url}/#/play`, { waitUntil: 'networkidle0' });
  const last = await p.$$eval('[data-deck]', els => els.length);
  const tile = (await p.$$('[data-deck]'))[last - 1];
  await tile.scrollIntoView(); await wait(80);
  const b = await tile.boundingBox(), hit = await p.evaluate(({ x, y }) => { const e = document.elementFromPoint(x, y); return !!(e && e.closest('[data-deck]')); }, { x: b.x + b.width / 2, y: b.y + b.height * 0.85 });
  assert.ok(hit, 'the bottom of the last deck tile is clickable');
  await p.close();
});

test('the play screen\'s dropdowns pick, Escape closes an open one first and then goes back', async () => {
  const p = await browser.newPage();
  await p.goto(`${server.url}/#/play`, { waitUntil: 'networkidle0' });
  await p.click('.dd[data-dd="botDeck"] .sel'); await p.click('.ddo[data-v="ramp"]'); await wait(80);
  assert.equal(await p.$eval('.dd[data-dd="botDeck"] .sel', e => e.textContent), 'Ramp deck');
  await p.click('.dd[data-dd="level"] .sel'); await p.keyboard.press('Escape'); await wait(80);
  assert.equal(await p.$('.dd.open'), null, 'the dropdown closed');
  assert.match(await p.evaluate(() => location.hash), /play/, 'still on the play screen');
  await p.keyboard.press('Escape'); await wait(80);
  assert.equal(await p.evaluate(() => location.hash), '#/');
  await p.close();
});

test('the chosen deck shows its decklist in the column, and opens in the collection', async () => {
  const p = await browser.newPage();
  await p.goto(`${server.url}/#/play`, { waitUntil: 'networkidle0' });
  const name = await p.$eval('.dtile.on b', e => e.textContent);
  await p.hover('.dtile.on'); await p.click('#dlist'); await wait(80);
  assert.equal(await p.$$eval('.clist.editing .st', els => els.length > 5), true, 'its strips are listed');
  await p.keyboard.press('Escape'); await wait(80);
  assert.equal(await p.$('.clist.editing'), null, 'Escape closes the list, not the screen');
  await p.hover('.dtile.on'); await p.click('#dedit'); await wait(200);
  assert.equal(await p.evaluate(() => location.hash), '#/collection');
  assert.equal(await p.$eval('.coll .clist.editing .dtile.on b', e => e.textContent), name, 'the same deck, open');
  await p.close();
});

test('no page errors', () => assert.deepEqual(page.errors, []));
