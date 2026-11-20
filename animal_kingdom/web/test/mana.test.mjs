// The mana rules' friend match in the browser (the prototype of 2026-11-20; static/mana.js, mana.css): home offers a
// friend match or the simple bot, two windows create and join one, the opening hands are the full cards with their costs, and in play the
// rail shows the mana, a card the mana can't pay for is dimmed, and a card played is paid for and lands on the board.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser({ mana: true }); });
after(async () => { await browser?.close(); server?.stop(); });
const wait = ms => new Promise(r => setTimeout(r, ms));
const until = async (page, fn, arg, ms = 10000) => { const t = Date.now(); while (Date.now() - t < ms) { if (await page.evaluate(fn, arg)) return true; await wait(100); } return false; };
const seat = async () => { const ctx = await browser.createBrowserContext(), p = await ctx.newPage(); p.errors = [];
  p.on('pageerror', e => p.errors.push(e.message)); await p.evaluateOnNewDocument(() => localStorage.setItem('ak:learned', '1'));
  await p.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]); return p; };
const click = async (p, sel) => { for (let i = 0; i < 5; i++) { try { await p.click(sel); return; } catch { await wait(150); } } throw new Error('no ' + sel); };

test('a mana friend match: home, the opening hands, the rail, a dimmed card and a card paid for', async () => {
  const A = await seat(), B = await seat();
  await A.goto(server.url + '/', { waitUntil: 'networkidle0' });
  assert.ok(await A.$('.mhome #mplay') && await A.$('.mhome #mprac') && await A.$('.mhome #mcoll'), 'home in the mana rules: Play, Practice, Collection');
  assert.equal(await A.$('.home'), null, 'not the usual home');
  await click(A, '#mplay'); await A.waitForSelector('[data-deck="pool_1"]');
  await click(A, '[data-deck="pool_1"]'); await click(A, '#mgo');
  await A.waitForSelector('.bigcode');
  const code = await A.$eval('.bigcode', e => e.textContent);
  await B.goto(`${server.url}/?rules=mana#/join/${code}`, { waitUntil: 'networkidle0' });
  await click(B, '[data-deck="pool_3"]'); await click(B, '#mgo');
  for (const p of [A, B]) assert.ok(await until(p, () => !!document.querySelector('#scr.mana #hand.mull .hc .mcard .plaque')), 'the opening hand in full');
  // each card in the opening hand: its cost in the gold hexagon, as the view says
  const costs = await A.evaluate(() => { const { V } = window.__ak(); return V.game.hand.map(h => [String(h.cost), document.querySelector(`#hand .hc[data-iid="${h.iid}"] .mcost`)?.dataset.n]); });
  for (const [want, shown] of costs) assert.equal(shown, want);
  for (const p of [A, B]) await click(p, '#skip');
  // the first turn that can be played (a turn the mana pays for nothing in is skipped): the rail's six hexagons, the
  // board's 24 regions and two bases of three
  const mine = () => { const a = window.__ak(); return !!(a.d && a.d.mine && !a.PB.busy && a.V.game.decision === 'yours'); };
  assert.ok(await until(A, () => window.__ak().V.game.decision !== 'mulligan'));
  let P = null;
  for (let i = 0; i < 100 && !P; i++) { for (const p of [A, B]) if (await p.evaluate(mine)) P = p; await wait(100); }
  assert.ok(P, 'a player may act');
  const look = await P.evaluate(() => ({ pips: document.querySelectorAll('.mmana.A .mpips i').length, on: document.querySelectorAll('.mmana.A .mpips i.on').length,
    left: window.__ak().V.game.mana[window.__ak().V.you].left, dots: document.querySelectorAll('#board .rdot').length, baseA: document.querySelectorAll('#board .cr.base.A').length, baseB: document.querySelectorAll('#board .cr.base.B').length,
    dens: document.querySelectorAll('#board .dentile, #board .pit, #board .dcount').length,
    hand: window.__ak().V.game.hand.map(h => ({ iid: h.iid, cost: h.cost, dim: document.querySelector(`#hand .hc[data-iid="${h.iid}"]`).classList.contains('dim'),
      can: !!(window.__ak().V.game.legal.place[h.id]) })) }));
  assert.deepEqual([look.pips, look.on], [6, look.left], 'the mana left, of six');
  assert.deepEqual([look.dots, look.baseA, look.baseB, look.dens], [24, 3, 3, 0]);
  for (const h of look.hand) assert.equal(h.dim, !h.can, `card ${h.iid} (cost ${h.cost}) dimmed exactly when it can't be played`);
  const play = look.hand.find(h => h.can);
  if (play) {
    await click(P, `#hand .hc[data-iid="${play.iid}"]`);
    await click(P, '#board .cr.tgt');
    assert.ok(await until(P, () => { const a = window.__ak(); return Object.keys(a.V.game.board).length === 1 && !a.PB.busy; }), 'the card is on the board');
    assert.equal(await P.evaluate(() => document.querySelectorAll('#board .cr.unit').length), 1);
    // its cost spent; with nothing left to pay for, the turn ends by itself and the rail shows the next turn's mana
    const after = await P.evaluate(() => { const { V } = window.__ak(); return { mine: V.game.current === V.you, spent: document.querySelectorAll('.mmana.A .mpips i.spent').length,
      label: document.querySelector('.mmana.A div').textContent, left: V.game.mana[V.you].left }; });
    if (after.mine) assert.equal(after.spent, play.cost, 'its cost spent');
    else assert.match(after.label, /^Next turn: \d mana$/);
    assert.ok(await P.evaluate(() => !document.querySelector('#board .cr.unit .mcost')), 'a piece on the board has no cost');
  }
  assert.deepEqual([...A.errors, ...B.errors], []);
});

test('a mana match against the bot: Practice starts it and the bot plays its cards', async () => {
  const p = await seat();
  await p.goto(server.url + '/', { waitUntil: 'networkidle0' });
  await click(p, '#mprac');   // Practice: straight into a match, both sides on a random pool deck
  assert.ok(await until(p, () => !!document.querySelector('#scr.mana #hand.mull')), 'the opening hand');
  await click(p, '#skip');
  // play on: end each of our turns at once; the bot's pieces reach the board
  const theirs = () => { const a = window.__ak(); return a.V && Object.values(a.V.game.board).flat().some(u => u.owner === 'B'); };
  let ok = false;
  for (let i = 0; i < 200 && !ok; i++) {
    ok = await p.evaluate(theirs);
    if (!ok && await p.evaluate(() => { const a = window.__ak(); return a.V.game.decision === 'yours' && !a.PB.busy; })) await p.keyboard.press('Space').catch(() => {});
    await wait(150);
  }
  if (process.env.SHOTS) await p.screenshot({ path: process.env.SHOTS + '/mana-bot.png' });
  assert.ok(ok, 'the bot has a piece on the board');
  assert.deepEqual(p.errors, []);
});

test('the collection in the mana rules: the mana card with its cost, sorted by cost, the deck as a tray of pieces, the mana deck rules, and the deck on home', async () => {
  const p = await seat();
  await p.goto(server.url + '/?deckview=tray', { waitUntil: 'networkidle0' });
  await click(p, '#mcoll');
  await p.waitForSelector('.coll .cgrid .tl .mcard');
  const grid = await p.evaluate(() => [...document.querySelectorAll('.cgrid .tl')].map(t => ({ id: t.dataset.card, cost: t.querySelector('.mcost')?.dataset.n, rect: !!t.querySelector('.card') })));
  const pool = await (await fetch(server.url + '/api/pool')).json(), C = Object.fromEntries(pool.cards.map(c => [c.id, c]));
  assert.ok(grid.length > 40 && grid.every(g => !g.rect && g.cost === String(C[g.id].mana)), 'every tile is the mana card with its cost');
  assert.deepEqual(grid.map(g => +g.cost), grid.map(g => +g.cost).sort((a, b) => a - b), 'the grid sorts by cost first');
  assert.ok(await p.$('.dd[data-k="cost"], [data-dd="cost"], .dd'), 'filters are there');
  // a new deck: its leader first, then cards; the tray holds a piece per copy in cost order, a count per cost, the rest
  // empty cells; the deck rules are the mana ones (no stars)
  await click(p, '#dnew'); await p.waitForSelector('.lv'); await click(p, '.lv[data-id="baboon_legend"]');
  await p.keyboard.type('Mana test'); await p.keyboard.press('Enter');
  assert.equal(await p.$('.coll .side'), null, 'an open deck is the tray, not the side column');
  assert.equal(await p.$$eval('.mtray .cell.empty', e => e.length), 24, 'the leader\'s card and 24 empty cells');
  const want = ['chipmunk', 'chipmunk', 'tarsier', 'tarsier', 'lion', 'lion', 'lynx', 'lynx', 'ocelot', 'ocelot', 'mole', 'mole', 'serval', 'serval', 'caracal', 'caracal',
    'cheetah', 'cheetah', 'black_panther', 'black_panther', 'jaguar', 'jaguar', 'bat', 'bat'];
  for (const id of want) { await click(p, `.cgrid .tl[data-card="${id}"]`); await wait(30); }
  const tray = await p.evaluate(() => ({ cells: [...document.querySelectorAll('.mtray .cell')].map(e => ({ id: e.dataset.card || null, cost: +(e.querySelector('.mcost')?.dataset.n || 0),
      x: e.getBoundingClientRect().left, y: e.getBoundingClientRect().top })),
    counts: [...document.querySelectorAll('.mtray .rcount')].map(b => +b.textContent), leader: document.querySelector('.mtray .tlead')?.dataset.card,
    stars: !!document.querySelector('#fstars, .coll .lvs'), play: document.querySelector('#play').textContent, ok: !document.querySelector('#play').disabled,
    count: document.querySelector('.mtray .fcount b').textContent, name: document.querySelector('.mtray .tname b').textContent }));
  const all = [...want, 'baboon_legend'];
  assert.equal(tray.cells.length, 25); assert.ok(tray.cells.every(c => c.id), 'every cell filled');
  assert.deepEqual(tray.cells.map(c => c.id).sort(), [...all].sort(), 'a piece per copy');
  assert.deepEqual(tray.cells.map(c => c.cost), tray.cells.map(c => C[c.id].mana).sort((a, b) => a - b), 'in cost order, each with its cost');
  assert.deepEqual(tray.counts, [1, 2, 3, 4, 5, 6].map(k => all.filter(id => C[id].mana === k).length).filter(Boolean), 'a count per cost');
  // two rows, interlocking: cell i in row i % 2, each half a piece right of the one before it, and wider gaps between costs
  const ys = [...new Set(tray.cells.map(c => Math.round(c.y)))]; assert.equal(ys.length, 2, 'two rows');
  tray.cells.forEach((c, i) => assert.equal(Math.round(c.y), Math.min(...ys) + (i % 2) * (Math.max(...ys) - Math.min(...ys))));
  const steps = tray.cells.slice(1).map((c, i) => c.x - tray.cells[i].x), split = tray.cells.slice(1).map((c, i) => c.cost !== tray.cells[i].cost);
  assert.ok(Math.min(...steps.filter((d, i) => split[i])) > Math.max(...steps.filter((d, i) => !split[i])) + 10, 'the costs are parted by a crack');
  assert.deepEqual([tray.leader, tray.stars, tray.count, tray.name], ['baboon_legend', false, '25/25', 'Mana test']);
  assert.deepEqual([tray.ok, tray.play], [true, 'Play this deck']);
  // hovering a piece shows its card above the tray; clicking it takes that copy out and leaves an empty cell
  const trayTop = await p.$eval('.mtray', e => e.getBoundingClientRect().top);
  const piece = await p.$('.mtray .cell[data-card="lion"]'), b = await piece.boundingBox();
  await p.mouse.move(b.x + 4, b.y + 4); await p.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
  const pop = await p.evaluate(() => { const e = document.getElementById('pop'); return { on: e.style.display !== 'none', bottom: e.getBoundingClientRect().bottom, name: e.querySelector('.pname')?.textContent }; });
  assert.ok(pop.on && pop.bottom <= trayTop && pop.name === C.lion.name, 'the full card, clear of the tray');
  await piece.click(); await wait(50);
  assert.deepEqual(await p.evaluate(() => [document.querySelectorAll('.mtray .cell[data-card="lion"]').length, document.querySelectorAll('.mtray .cell.empty').length,
    document.querySelector('.mtray .fcount b').textContent]), [1, 1, '24/25']);
  await click(p, '.cgrid .tl[data-card="lion"]'); await wait(50);
  await click(p, '#play');
  await p.waitForSelector('.mhome');
  assert.match(await p.$eval('.mhome .dk.on', e => e.textContent), /Mana test/, 'the deck is on home, chosen');
  // the same deck in the side list (?deckview=list, kept in the browser): each strip its cost, the piece's figure, the name
  // and the strength; two copies as two dots, no third number; no stars anywhere
  await p.goto(server.url + '/?deckview=list#/collection', { waitUntil: 'networkidle0' });
  await p.evaluate(() => [...document.querySelectorAll('.dtile[data-d]')].find(e => e.textContent.includes('Mana test')).click()); await p.waitForSelector('.side .st.mst');
  const list = await p.evaluate(() => ({ strips: [...document.querySelectorAll('.side .st')].map(s => ({ id: s.dataset.card, cost: +(s.querySelector('.sc .mchip')?.dataset.n || 0),
      fig: !!s.querySelector('.hd img'), dots: s.querySelectorAll('.x i').length, x: s.querySelector('.x').textContent })), stars: !!document.querySelector('.coll .lvs, #fstars'), tray: !!document.querySelector('.mtray') }));
  assert.equal(list.tray, false); assert.equal(list.stars, false, 'no stars');
  assert.deepEqual(list.strips.map(s => s.cost), list.strips.map(s => C[s.id].mana).sort((a, b) => a - b), 'the list by cost');
  assert.deepEqual(list.strips.map(s => [s.id, s.fig, s.x, s.dots]), list.strips.map(s => [s.id, true, '', all.filter(id => id === s.id).length > 1 ? 2 : 0]), 'figure, and two dots for a pair');
  await p.goto(server.url + '/?deckview=tray#/collection', { waitUntil: 'networkidle0' });
  assert.deepEqual(p.errors, []);
});

test('the tray fits the window: a deck of 25 at 1280 x 720, 1512 x 800 and 1920 x 1080', async () => {
  const p = await seat();
  await p.goto(server.url + '/', { waitUntil: 'networkidle0' });
  const r = await p.evaluate(async () => { const { trayGeo } = await import('/static/collection.js');
    return [[1280, 720], [1512, 800], [1920, 1080]].map(([W, H]) => { const g = trayGeo(W, H);
      return { W, H, w: g.w, used: 24 + g.lead + 22 + (24 * g.p / 2 + 6 * g.crack + g.w) + 22 + 250 + 24, tall: g.dy + g.h + 26 + 18 }; }); });
  for (const g of r) { assert.ok(g.used <= g.W, `${g.W} x ${g.H}: ${g.used} px wide`); assert.ok(g.w >= 48, `${g.W}: pieces ${g.w} px`); assert.ok(g.tall <= .26 * g.H, `${g.W} x ${g.H}: ${g.tall} px tall`); }
});

test('the mana deck rules in the deck builder: a card with no mana cost makes the deck illegal and says so', async () => {
  const p = await seat();
  await p.goto(server.url + '/', { waitUntil: 'networkidle0' });
  const r = await p.evaluate(async () => { const { deckIssue } = await import('/static/collection.js');
    const cards = { a: { name: 'Ant', rarity: 'common', status: 'collectible', mana: 1 }, w: { name: 'Wolf', rarity: 'common', status: 'collectible' },
      l: { name: 'Leo', rarity: 'legendary', status: 'collectible', mana: 3 } };
    const mana = { deckSize: 4, copies: { common: 2, legendary: 1 }, starBudget: null, needsCost: true }, old = { ...mana, starBudget: 0, needsCost: false };
    return [deckIssue(['a', 'a', 'w', 'l'], cards, mana, 'l', { l: {} }), deckIssue(['a', 'a', 'w', 'w', 'l'].slice(1), cards, mana, 'l', { l: {} }),
      deckIssue(['a', 'a', 'l'], cards, mana, 'l', { l: {} }), deckIssue(['a', 'a', 'w', 'l'], cards, old, 'l', { l: {} })]; });
  assert.deepEqual(r, ['Wolf has no mana cost', 'Wolf has no mana cost', '', ''], 'the mana rules refuse a card with no cost; no star budget; the default rules don\'t ask for a cost');
});
