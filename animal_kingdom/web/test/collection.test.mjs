// The collection (static/collection.js), clicked through in a browser against a private server: building a deck from a
// starter, the limits and why they refuse, what saves, deck codes both ways, the cover, delete, and the way back.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser, page;
const wait = ms => new Promise(r => setTimeout(r, ms));
const card = id => `.cgrid [data-card="${id}"]`;
const toList = async () => { if (await page.$('#done')) { await page.click('#done'); await wait(50); } };
const openDeck = async sel => { if (await page.$(sel + '.on')) return; await toList(); await page.click(sel); await wait(50); };
const has = (sel, cls) => page.$eval(sel, (e, c) => e.classList.contains(c), cls);
const myDecks = () => page.evaluate(() => fetch('/api/me', { headers: { 'X-AK-Key': localStorage.getItem('ak:key') } }).then(r => r.json()).then(m => m.decks));
const paste = text => page.evaluate(t => { const e = new Event('paste', { bubbles: true }); e.clipboardData = { getData: () => t }; document.dispatchEvent(e); }, text);

before(async () => {
  server = await startServer(); browser = await openBrowser();
  page = await browser.newPage(); page.errors = [];
  page.on('pageerror', e => page.errors.push(e.message));
  await page.goto(`${server.url}/#/collection`, { waitUntil: 'networkidle0' });
  await page.evaluate(() => { navigator.clipboard.writeText = t => { window.__clip = t; return Promise.resolve(); }; });
});
after(async () => { await browser?.close(); server?.stop(); });

test('the screen: the grid beside the deck column, the header on the grid\'s edges', async () => {
  const b = await page.evaluate(() => { const R = s => { const r = document.querySelector(s).getBoundingClientRect(); return { left: r.left, right: r.right }; };
    return { grid: R('.cgrid .tl'), side: R('.side'), tabs: R('.chead .tab'), search: R('.chead .search'), cards: document.querySelectorAll('.cgrid .tl').length }; });
  assert.ok(b.cards > 90, 'every card of the seven decks'); assert.ok(b.side.left > b.grid.right, `the deck column is right of the grid (${JSON.stringify(b.side)})`);
  assert.equal(Math.round(b.tabs.left), Math.round(b.grid.left), 'the header starts on the grid\'s edge');
});

test('a new profile has the seven starter decks as its own, the first one open', async () => {
  const decks = await myDecks();
  assert.deepEqual(decks.map(d => d.name), ['Cats', 'Canines', 'Aggro', 'Colony', 'Egg', 'Food', 'Ramp']);
  assert.equal(await page.$('.dtile.on'), null, 'the screen opens on the deck list');
  assert.match(await page.$eval('.fcount', e => e.textContent), /7\/20/, 'the foot counts decks against the limit');
  assert.ok(await page.$('.clist #dnew'), 'New deck is the slot after the last deck');
  await openDeck('[data-d="cats_midrange"]');
  assert.equal(await page.$$eval('.clist .dtile', t => t.length), 1, 'editing shows only that deck');
  await page.click('.side .st[data-card="lion"]'); await wait(100);
  const [cats] = await myDecks();
  assert.equal(cats.name, 'Cats'); assert.equal(Object.values(cats.cards).reduce((a, n) => a + n, 0), 29, 'a starter is edited in place: it is yours');
  assert.equal((await myDecks()).length, 7, 'no copy');
  assert.match(await page.$eval('.fcount', e => e.textContent), /29\/30/); assert.ok(await page.$('#play[disabled]'), 'Play waits for 30 cards');
});

test('adding says where the card went, and a refused add says why', async () => {
  await page.click(card('lion')); await wait(80);
  assert.ok(await has('.side .st[data-card="lion"]', 'flash'), 'the strip flashes');
  assert.match(await page.$eval('.play', e => e.textContent), /Play this deck/);
  await page.click(card('lion')); await wait(30);
  assert.ok(await has(card('lion'), 'shake'), 'a full deck refuses'); assert.ok(await has('.fcount', 'shake'), 'and the card count shows why');
  await page.click('.side .st[data-card="lion"]'); await wait(80);                   // clicking its strip takes one out: 29
  await page.click(card('lion')); await page.click(card('lion')); await wait(30);        // back to 3 of 3 (30), then one too many
  assert.ok(await has(card('lion'), 'max'), 'all copies in: dimmed');
  assert.equal(await page.$(card('lion') + ' .pips'), null, 'a used-up card needs no dots: its dimming says it');
  assert.ok(!(await has(card('dog'), 'max')), 'a full deck does not dim the cards it lacks: only used-up cards are dimmed');
});

test('a chosen name and cover save with the deck', async () => {
  await page.click('.nm-edit'); await page.keyboard.down('Meta'); await page.keyboard.press('a'); await page.keyboard.up('Meta');
  await page.keyboard.type('Big Cats'); await page.keyboard.press('Enter'); await wait(80);
  await page.hover('.dtile.on'); await page.click('#dcover'); await wait(80);
  await page.click('.cv[data-id="tiger"]'); await wait(120);
  const [d] = await myDecks(); assert.equal(d.name, 'Big Cats'); assert.equal(d.cover, 'tiger');
  await page.reload({ waitUntil: 'networkidle0' }); await page.evaluate(() => { navigator.clipboard.writeText = t => { window.__clip = t; return Promise.resolve(); }; });
  assert.equal(await page.$('.dtile.on'), null, 'a reload lands on the deck list');
  await openDeck('.clist .dtile:first-child');
  assert.equal(await page.$eval('.dtile.on b', e => e.textContent), 'Big Cats', 'the name kept');
  assert.match(await page.$eval('.dtile.on', e => e.style.backgroundImage), /tiger/);
});

test('a deck code copies, and pasting it (or a plain list) makes a deck', async () => {
  await openDeck('.clist .dtile:first-child');
  await page.hover('.dtile.on'); await page.click('#dcopy'); await wait(50);
  const code = await page.evaluate(() => window.__clip);
  assert.match(code, /^### Big Cats\n/); assert.ok(code.split('\n').pop().length < 50);
  const before = (await myDecks()).length; await paste(code); await wait(120);
  assert.equal((await myDecks()).length, before + 1);
  let decks = await myDecks(); const n = decks.length; assert.deepEqual(decks[n - 1].cards, decks[0].cards, 'the pasted deck is the same deck');
  await paste('### From an agent\n3x Lion\n2x House Cat'); await wait(120);
  decks = await myDecks(); assert.equal(decks[n].name, 'From an agent'); assert.deepEqual(decks[n].cards, { lion: 3, house_cat: 2 });
});

test('delete asks first', async () => {
  await openDeck('.clist .dtile:first-child');
  const n = (await myDecks()).length;
  await page.hover('.dtile.on'); await page.click('#ddel'); await wait(50);
  await page.keyboard.press('Escape'); await wait(50);
  assert.equal((await myDecks()).length, n, 'Escape keeps it'); assert.ok(page.url().endsWith('#/collection'), 'and stays on the screen');
  await page.hover('.dtile.on'); await page.click('#ddel'); await page.click('.dbtns .danger'); await wait(120);
  assert.equal((await myDecks()).length, n - 1);
});

test('New deck starts an empty deck, open, with its name ready to type', async () => {
  await toList(); const n = (await myDecks()).length;
  await page.click('#dnew'); await wait(80);
  assert.ok(await page.$('.nm-in'), 'the name is being edited');
  await page.keyboard.type('Scratch'); await page.keyboard.press('Enter'); await wait(120);
  const decks = await myDecks(); assert.equal(decks.length, n + 1);
  assert.deepEqual([decks[n].name, decks[n].cards], ['Scratch', {}]);
  assert.match(await page.$eval('.fcount', e => e.textContent), /0\/30/);
  await page.click(card('lion')); await wait(80);
  assert.deepEqual((await myDecks())[n].cards, { lion: 1 }, 'cards go into the new deck');
});

test('an opened deck is the column alone, starting at its top; Done returns to the list; a former starter is yours to rename and delete', async () => {
  await openDeck('[data-d="ramp"]'); await wait(80);
  const off = await page.evaluate(() => document.querySelector('.dtile.on').getBoundingClientRect().top - document.querySelector('.clist').getBoundingClientRect().top);
  assert.ok(off >= 0 && off < 30, `the open deck starts at the top (${off})`);
  const n = (await myDecks()).length;
  await page.hover('.dtile.on'); assert.ok(await page.$('#dcover')); assert.ok(await page.$('#ddel'), 'it can be deleted like any deck');
  await page.click('.nm-edit'); await page.keyboard.down('Meta'); await page.keyboard.press('a'); await page.keyboard.up('Meta'); await page.keyboard.type('Big Ramp'); await page.keyboard.press('Enter'); await wait(120);
  const decks = await myDecks(); assert.equal(decks.length, n); assert.equal(decks.find(d => d.id === 'ramp').name, 'Big Ramp');
  await page.click('#done'); await wait(60); assert.ok(await page.$('[data-d="ramp"]:not(.on)'), 'Done shows the list again');
  await openDeck('[data-d="ramp"]'); await page.keyboard.press('Escape'); await wait(60); assert.ok(await page.$('#dnew'), 'Escape is Done while editing');
});

test('right-click opens a card large, its keywords explained', async () => {
  await page.click(card('eagle'), { button: 'right' }); await wait(80);
  assert.ok(await page.$('.modal.zoom .card'), 'the card opens');
  assert.deepEqual(await page.$$eval('.kw b', b => b.map(e => e.textContent)), ['Flight']);
  await page.keyboard.press('Escape'); await wait(50); assert.equal(await page.$('.modal.zoom'), null, 'Escape closes it');
  assert.ok(page.url().endsWith('#/collection'), 'without leaving the screen');
});

test('the strength and rarity lists are the screen\'s own and close on a click elsewhere', async () => {
  const count = () => page.$$eval('.cgrid .tl', t => t.length);
  await page.click('[data-dd=str] .sel'); assert.ok(await page.$('.dd.open'));
  await page.click('[data-dd=str] .ddo[data-v="4"]'); const four = await count();
  assert.ok(four > 0 && four < 60); assert.equal(await page.$eval('[data-dd=str] .sel', e => e.textContent), 'Strength 4');
  await page.click('[data-dd=str] .sel'); await page.click('[data-dd=str] .ddo[data-v="9+"]');
  const big = await page.$$eval('.cgrid .tl .n img, .cgrid .tl', els => els.length); assert.ok(big > 0, 'Strength 9+ finds the 9s and 10s');
  assert.equal(await page.$$eval('[data-dd=str] .ddo', o => o.length), 11, 'Any, 0 to 8, and 9+');
  await page.click('[data-dd=str] .sel'); await page.click('[data-dd=str] .ddo[data-v=""]');
  await page.click('[data-dd=rar] .sel'); await page.mouse.click(600, 500); assert.equal(await page.$('.dd.open'), null);
});

test('filters: a family, clearing it, and an empty result', async () => {
  const count = () => page.$$eval('.cgrid .tl', t => t.length);
  const all = await count();
  await page.click('[data-t="Rodent"]'); const rodents = await count(); assert.ok(rodents > 0 && rodents < all);
  await page.click('[data-t="Rodent"]'); assert.equal(await count(), all, 'clicking the selected family clears it');
  await page.click('[data-t="Snake"]'); const snakes = await count(); await page.click('[data-t="Bird"]'); const both = await count();
  assert.ok(both > snakes, 'families combine: Snake and Bird shows both'); await page.click('[data-t="Snake"]'); await page.click('[data-t="Bird"]');
  await page.type('#q', 'zzzz'); await wait(50); assert.match(await page.$eval('.cgrid', e => e.textContent), /No cards match/);
  await page.click('#clearf'); assert.equal(await count(), all);
});

test('Play opens the play screen with the deck chosen; Back and Escape leave', async () => {
  await openDeck('.clist .dtile:first-child');             // the first of your decks (complete)
  if (!(await page.$('#play'))) return assert.fail('the open deck should be complete');
  await page.click('#play'); await wait(150);
  assert.ok(page.url().endsWith('#/play')); assert.match(await page.evaluate(() => localStorage.getItem('ak:deck')), /^my:/);
  await page.goto(`${server.url}/#/collection`, { waitUntil: 'networkidle0' });
  await page.keyboard.press('Escape'); await wait(60); assert.ok(await page.$('#dnew'), 'Escape first closes the deck');
  await page.keyboard.press('Escape'); await wait(80); assert.ok(page.url().endsWith('#/'), 'then goes back to the menu');
  assert.deepEqual(page.errors, []);
});
