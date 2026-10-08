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

test('Escape closes the concede question, then a panel, then deselects the card', async () => {
  await clickAt('#menubtn'); assert.ok(await page.$eval('#concov', e => e.classList.contains('on')));
  await page.keyboard.press('Escape'); await wait(60);
  assert.ok(!(await page.$eval('#concov', e => e.classList.contains('on'))), 'question closed');
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

test('home starts a match: the deck chooser lists every deck and scrolls in a short window', async () => {
  const p = await browser.newPage(); await p.setViewport({ width: 1100, height: 640 });
  await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await p.evaluate(() => { const ok = document.querySelector('#since [data-x="ok"]'); if (ok) ok.click(); });   // a release from today greets this new profile
  await p.click('#deckbtn'); await wait(80);
  const tiles = await p.$$('.chooser [data-deck]'), last = tiles[tiles.length - 1];
  await last.scrollIntoView(); await wait(80);
  const b = await last.boundingBox(), hit = await p.evaluate(({ x, y }) => { const e = document.elementFromPoint(x, y); return !!(e && e.closest('[data-deck]')); }, { x: b.x + b.width / 2, y: b.y + b.height / 2 });
  assert.ok(hit, 'the last deck can be clicked');
  const id = await p.evaluate(e => e.dataset.deck, last); await last.click(); await wait(80);
  assert.equal(await p.evaluate(() => localStorage.getItem('ak:deck')), id, 'clicking a deck chooses it');
  assert.ok(await p.$('.chooser'), 'and keeps the chooser open to read its list');
  await p.close();
});

test('the deck chooser shows the clicked deck\'s list, not the one under the pointer, and opens it in the collection', async () => {
  const p = await browser.newPage();
  await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await p.click('#deckbtn'); await wait(80);
  const second = (await p.$$('.chooser [data-deck]'))[1], name = await p.evaluate(e => e.textContent, second);
  const before = await p.$eval('.dl', e => e.textContent);
  await second.hover(); await wait(80);
  assert.equal(await p.$eval('.dl', e => e.textContent), before, 'hovering leaves the list alone');
  await second.click(); await wait(80);
  assert.notEqual(await p.$eval('.dl', e => e.textContent), before, 'a click shows that deck');
  await p.click('#dedit'); await wait(200);
  assert.equal(await p.evaluate(() => location.hash), '#/collection');
  assert.equal(await p.$eval('.coll .clist.editing .dtile.on b', e => e.textContent), name, 'that deck, open');
  await p.close();
});

test('the opponent chooser picks with its own dropdowns; Escape closes an open dropdown, then the chooser', async () => {
  const p = await browser.newPage();
  await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await p.click('#oppbtn'); await wait(80);
  await p.click('.dd[data-dd="botDeck"] .sel'); await p.click('.ddo[data-v="giants"]'); await wait(80);
  assert.match(await p.$eval('#oppbtn', e => e.textContent), /Ramp/, 'the slot says what was chosen');
  assert.ok(await p.$('.chooser'), 'the chooser stays open for the next setting');
  await p.click('[data-level="expert"]'); await wait(80); assert.match(await p.$eval('#oppbtn', e => e.textContent), /Expert/, 'the level is a picker');
  await p.click('.dd[data-dd="botDeck"] .sel'); await p.keyboard.press('Escape'); await wait(80);
  assert.equal(await p.$('.dd.open'), null, 'the dropdown closed'); assert.ok(await p.$('.chooser'), 'the chooser stays');
  await p.keyboard.press('Escape'); await wait(80);
  assert.equal(await p.$('.chooser'), null, 'then the chooser closes');
  await p.goto(`${server.url}/#/play`, { waitUntil: 'networkidle0' });
  assert.equal(await p.evaluate(() => location.hash), '#/', 'the old Play address lands on home');
  await p.close();
});

test('the flag concedes the game, after a question in the middle of the board', async () => {
  const p = await browser.newPage();
  await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await p.click('#go');
  await p.waitForFunction(() => window.__ak().V && window.__ak().V.phase === 'playing', { timeout: 10000 });
  await p.waitForSelector('#intro', { timeout: 3000 });   // the match opens on its versus moment; a click skips it
  await p.click('#intro'); await wait(700);
  assert.equal(await p.$('#intro'), null, 'the versus moment is gone after a click');
  const asking = () => p.$eval('#concov', e => e.classList.contains('on'));
  await p.click('#menubtn'); await wait(80);
  assert.ok(await asking(), 'it asks first');
  await p.click('#keep'); await wait(80);
  assert.ok(!(await asking()) && await p.evaluate(() => window.__ak().V.phase) === 'playing', 'Keep playing goes back to the game');
  await p.click('#menubtn'); await p.keyboard.press('Escape'); await wait(80);
  assert.ok(!(await asking()), 'Escape says no too');
  await p.click('#menubtn'); await wait(80);
  await p.click('#concede');
  await p.waitForFunction(() => window.__ak().V.phase === 'match_over', { timeout: 5000 });
  assert.match(await p.$eval('#endov', e => e.textContent), /You conceded/);
  // See the board lifts the results away; Back to results brings them back
  await p.click('#peek'); await wait(80);
  assert.ok(await p.$eval('#endov', e => getComputedStyle(e).display === 'none'), 'the board shows');
  await p.click('#unpeek'); await wait(80);
  assert.ok(await p.$eval('#endov', e => getComputedStyle(e).display !== 'none'), 'the results are back');
  await p.close();
});

test('a hover label in the game does not stay on screen after leaving', async () => {
  const p = await browser.newPage();
  await p.goto(`${server.url}/#/lab/mid`, { waitUntil: 'networkidle0' });
  const b = await (await p.$('#board [data-tip]')).boundingBox(); await p.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await wait(80);
  assert.ok(await p.$eval('#tip', e => getComputedStyle(e).display !== 'none'), 'the label shows');
  await p.evaluate(() => { location.hash = '#/'; }); await wait(150);
  assert.ok(await p.$eval('#tip', e => getComputedStyle(e).display === 'none'), 'and is gone at home');
  await p.close();
});

test('a hover label by the window\'s right edge opens to the left, on screen', async () => {
  const b = await (await page.$('#menubtn')).boundingBox();
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.move(b.x + b.width / 2 + 1, b.y + b.height / 2); await wait(60);
  const [text, right, left] = await page.$eval('#tip', e => { const r = e.getBoundingClientRect(); return [e.textContent, r.right, r.left]; });
  assert.equal(text, 'Concede');
  assert.ok(right <= await page.evaluate(() => innerWidth) && left < b.x, 'left of the flag, inside the window');
  await page.mouse.move(2, 2);
});

test('no page errors', () => assert.deepEqual(page.errors, []));
