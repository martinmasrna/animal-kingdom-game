// The mana rules' friend match in the browser (the prototype of 2026-11-20; static/mana.js, mana.css): home offers a
// friend match or the simple bot, two windows create and join one, the opening hands are the full cards with their costs, and in play the
// rail shows the mana, a card the mana can't pay for is dimmed, and a card played is paid for and lands on the board.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { startServer, openBrowser } from './harness.mjs';
const NEWEST = JSON.parse(readFileSync(new URL('../static/patches/index.json', import.meta.url)))[0];   // the patch notes are covered in patch.test.mjs

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });
const wait = ms => new Promise(r => setTimeout(r, ms));
const until = async (page, fn, arg, ms = 10000) => { const t = Date.now(); while (Date.now() - t < ms) { if (await page.evaluate(fn, arg)) return true; await wait(100); } return false; };
const seat = async () => { const ctx = await browser.createBrowserContext(), p = await ctx.newPage(); p.errors = [];
  p.on('pageerror', e => p.errors.push(e.message)); await p.evaluateOnNewDocument(() => localStorage.setItem('ak:learned', '1'));
  await p.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]); return p; };
// A deck of the mana collection on the profile: 12 Wisps (1 to 6, two each), Flight 1, 2, 3 and 5 two each, two Spikes 3, two Cantrip 2s and the Warlord (25, legal in the mana rules).
const DECK = { ...Object.fromEntries([...Array(6).keys()].map(i => ['wisp_' + (i + 1), 2])), flight_1: 2, flight_2: 2, flight_3: 2, flight_5: 2, spikes_3: 2, cantrip_2: 2, warlord_legend: 1 };
// A cheap one (nothing over 3 mana) for the matches that must get going: the Wisps 1 to 3, the cantrips, fliers, Spikes and Hungry, and the Warlord.
const CHEAP = { ...Object.fromEntries([1, 2, 3].map(i => ['wisp_' + i, 2])), cantrip_2: 2, cantrip_3: 2, flight_1: 2, flight_2: 2, flight_3: 2, spikes_1: 2, spikes_3: 2, hungry_1: 2, hungry_3: 2, warlord_legend: 1 };
const giveDeck = async (p, id, name, cards = DECK, leader = 'warlord_legend') => {
  await p.evaluate(async (d, seen) => { const r = await fetch('/api/me/decks', { method: 'PUT', headers: { 'X-AK-Key': localStorage.getItem('ak:key'), 'Content-Type': 'application/json' }, body: JSON.stringify([d]) }); if (!r.ok) throw new Error(await r.text());
    await fetch('/api/me/patch', { method: 'POST', headers: { 'X-AK-Key': localStorage.getItem('ak:key'), 'Content-Type': 'application/json' }, body: JSON.stringify({ version: seen }) }); },   // the patch notes seen: they don't open over the test
    { id, name, cards, leader }, NEWEST);
  await p.reload({ waitUntil: 'networkidle0' });
};
const click = async (p, sel) => { for (let i = 0; i < 5; i++) { try { await p.click(sel); return; } catch { await wait(150); } } throw new Error('no ' + sel); };

test('a mana friend match: home, the opening hands, the rail, a dimmed card and a card paid for', async () => {
  const A = await seat(), B = await seat();
  await A.goto(server.url + '/', { waitUntil: 'networkidle0' }); await giveDeck(A, 'w1', 'Wisps A');
  assert.ok(await A.$('.mhome #mplay') && await A.$('.mhome #mprac') && await A.$('.mhome #mcoll'), 'home in the mana rules: Play, Practice, Collection');
  assert.equal(await A.$('.home'), null, 'not the usual home');
  await click(A, '#mplay'); await A.waitForSelector('[data-deck="my:w1"]');
  await click(A, '[data-deck="my:w1"]'); await click(A, '#mgo');
  await A.waitForSelector('.bigcode');
  const code = await A.$eval('.bigcode', e => e.textContent);
  await B.goto(`${server.url}/`, { waitUntil: 'networkidle0' }); await giveDeck(B, 'w2', 'Wisps B');
  await B.goto(`${server.url}/#/join/${code}`, { waitUntil: 'networkidle0' });
  await click(B, '[data-deck="my:w2"]'); await click(B, '#mgo');
  for (const p of [A, B]) assert.ok(await until(p, () => !!document.querySelector('#scr.mana #hand.mull .hc .mcard .plaque')), 'the opening hand in full');
  // each card in the opening hand: its cost in the gold hexagon, as the view says
  const costs = await A.evaluate(() => { const { V } = window.__ak(); return V.game.hand.map(h => [String(h.cost), document.querySelector(`#hand .hc[data-iid="${h.iid}"] .mcost`)?.dataset.n]); });
  for (const [want, shown] of costs) assert.equal(shown, want);
  for (const p of [A, B]) await click(p, '#skip');
  // the first turn that can be played (a turn the mana pays for nothing in is skipped): the rail's ten hexagons, the
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
  assert.deepEqual([look.pips, look.on], [1, look.left], 'the crystals earned (turn 1: one), the mana left lit (Martin, 2026-11-22: only the earned crystals show)');
  assert.deepEqual([look.dots, look.baseA, look.baseB, look.dens], [24, 3, 3, 0]);
  for (const h of look.hand) assert.equal(h.dim, !h.can, `card ${h.iid} (cost ${h.cost}) dimmed exactly when it can't be played`);
  const play = look.hand.find(h => h.can);
  if (play) {
    await click(P, `#hand .hc[data-iid="${play.iid}"]`);
    await click(P, '#board .cr.tgt');
    assert.ok(await until(P, () => { const a = window.__ak(); return Object.keys(a.V.game.board).length === 1 && !a.PB.busy; }), 'the card is on the board');
    assert.equal(await P.evaluate(() => document.querySelectorAll('#board .cr.unit').length), 1);
    // its cost spent; with nothing left to pay for, the turn ends by itself and the rail shows the next turn's mana
    await until(P, () => !!document.querySelector('.mmana.A .mpips') && !window.__ak().PB.busy);   // the rail is redrawn as the turn passes
    const after = await P.evaluate(() => { const { V } = window.__ak(); return { mine: V.game.current === V.you, spent: document.querySelectorAll('.mmana.A .mpips i.spent').length,
      left: V.game.mana[V.you].left }; });
    if (after.mine) assert.equal(after.spent, play.cost, 'its cost spent');
    else assert.equal(after.spent, 0, 'the turn passed: the rail shows the next turn\'s mana, unspent');
    assert.ok(await P.evaluate(() => !document.querySelector('#board .cr.unit .mcost')), 'a piece on the board has no cost');
  }
  assert.deepEqual([...A.errors, ...B.errors], []);
});

test('a mana match against the bot: Practice starts it and the bot plays its cards', async () => {
  const p = await seat();
  await p.goto(server.url + '/', { waitUntil: 'networkidle0' }); await giveDeck(p, 'w1', 'Cheap', CHEAP);
  // the bot plays the deck chosen for it, ours here (server.py); two idle turns in a row end a match, and a hand with nothing for the bot's first mana
  // is a coin toss, so a match that ends before the bot has played is dealt again
  const theirs = () => { const a = window.__ak(); return a.V && Object.values(a.V.game.board).flat().some(u => u.owner === 'B'); };
  const myPlay = () => { const a = window.__ak(); return a.V.game.decision === 'yours' && !a.PB.busy ? (a.V.game.hand.find(h => a.V.game.legal.place[h.id]) || {}).iid || 0 : null; };
  let ok = false;
  for (let game = 0; game < 6 && !ok; game++) {
    if (game) await p.goto(server.url + '/', { waitUntil: 'networkidle0' });
    await click(p, '#mprac');   // Practice: your deck and the bot's (both ours here), then Start
    await p.waitForSelector('.mhome [data-opp]');
    assert.ok(await p.$('.mhome [data-deck].on') && await p.$('.mhome [data-opp].on'), 'both decks chosen');
    await click(p, '#mgo');
    assert.ok(await until(p, () => !!document.querySelector('#scr.mana #hand.mull')), 'the opening hand');
    const costs = await p.evaluate(() => [...document.querySelectorAll('#hand .hc')].sort((a, b) => a.offsetLeft - b.offsetLeft)
      .map(el => window.__ak().V.game.hand.find(h => String(h.iid) === el.dataset.iid).cost));
    assert.deepEqual(costs, [...costs].sort((a, b) => a - b), 'the opening hand from cheapest to dearest, left to right');
    // a swap: the new card takes the old one's place and nothing else moves
    const row = () => p.evaluate(() => [...document.querySelectorAll('#hand .hc')].sort((a, b) => a.offsetLeft - b.offsetLeft).map(el => el.dataset.iid));
    const before = await row(), out = before[1];
    await click(p, `#hand .hc[data-iid="${out}"]`);
    assert.ok(await until(p, o => !document.querySelector(`#hand .hc[data-iid="${o}"]`), out), 'the swapped card left');
    await wait(400);
    const after = await row();
    assert.deepEqual(after.filter((_, i) => i !== 1), before.filter((_, i) => i !== 1), 'the others stay where they were');
    assert.ok(!before.includes(after[1]), 'the new card in the swapped one\'s place');
    await click(p, '#skip');
    // the offered cards' row spans the screen: it lets the pointer through to the prompt's buttons (Hide cards; Martin, 2026-11-21)
    assert.equal(await p.evaluate(() => getComputedStyle(document.getElementById('opts')).pointerEvents), 'none', 'the card row never covers a button');
    // the order holds once the mulligan ends: the kept hand as it was, a card drawn on its right
    assert.ok(await until(p, () => !document.querySelector('#hand.mull')), 'the mulligan ends');
    await wait(600);
    const played = await row();
    assert.deepEqual(played.slice(0, after.length), after, 'the hand keeps its order after the mulligan');
    for (let i = 0; i < 200 && !ok; i++) {
      ok = await p.evaluate(theirs);
      if (ok || await p.evaluate(() => window.__ak().V.game.decision === 'over')) break;
      const iid = await p.evaluate(myPlay);
      if (iid) { await click(p, `#hand .hc[data-iid="${iid}"]`); await click(p, '#board .cr.tgt').catch(() => {}); }
      else if (iid === 0) await p.keyboard.press('Space').catch(() => {});
      await wait(150);
    }
  }
  if (process.env.SHOTS) await p.screenshot({ path: process.env.SHOTS + '/mana-bot.png' });
  assert.ok(ok, 'the bot has a piece on the board');
  assert.deepEqual(p.errors, []);
});

test('the food lines: none at rest; a side connected from its base row to the enemy\'s draws its circuit; a loose piece on the far row draws none', async () => {
  const p = await seat();
  await p.goto(server.url + '/', { waitUntil: 'networkidle0' }); await giveDeck(p, 'w1', 'Cheap', CHEAP);
  await click(p, '#mprac'); await p.waitForSelector('.mhome [data-opp].on'); await click(p, '#mgo');
  assert.ok(await until(p, () => !!document.querySelector('#scr.mana #hand.mull')), 'the opening hand');
  await click(p, '#skip');
  assert.ok(await until(p, () => { const a = window.__ak(); return a.V.game.decision === 'yours' && !a.PB.busy; }), 'my turn');
  const lines = () => ({ A: document.querySelectorAll('#board .mtrails.A path').length, B: document.querySelectorAll('#board .mtrails.B path').length });
  assert.deepEqual(await p.evaluate(lines), { A: 0, B: 0 }, 'no lines at the start of a match');
  // a view with the board replaced: `chain` my pieces on the shortest path from my base row to theirs (M.edges), else one
  // of mine alone on their base row
  const show = chain => p.evaluate(async chain => { const a = window.__ak(), V = a.V, G = V.game, me = V.you, them = me === 'A' ? 'B' : 'A';
    const { map } = await (await fetch('/api/pool')).json(), nb = {};
    for (const [u, v] of map.edges) { (nb[u] = nb[u] || []).push(v); (nb[v] = nb[v] || []).push(u); }
    const from = new Map(G.bases[me].map(t => [t, null])), q = [...G.bases[me]];
    let end = null; while (q.length && !end) { const t = q.shift(); if (G.bases[them].includes(t)) end = t; else for (const v of nb[t] || []) if (!from.has(v)) { from.set(v, t); q.push(v); } }
    const tiles = chain ? [] : [G.bases[them][0]]; if (chain) for (let t = end; t; t = from.get(t)) tiles.push(t);
    const board = Object.fromEntries(tiles.map((t, i) => [t, [{ iid: 900 + i, id: 'wisp_1', owner: me, str: 2 }]]));
    window.__ak.feed({ ...V, game: { ...G, board } }); return tiles.length; }, chain);
  assert.ok(await show(true) >= 2);
  assert.ok(await until(p, () => document.querySelectorAll('#board .mtrails path').length > 0), 'the circuit is drawn');
  // a shortest chain stands on one tile of each base row: a line from my ball to my base tile, one from theirs into their ball, in my colour
  assert.deepEqual(await p.evaluate(lines), { A: 2, B: 0 }, 'my circuit, and none of theirs');
  await show(false); await wait(300);
  assert.deepEqual(await p.evaluate(lines), { A: 0, B: 0 }, 'a piece on their base row connected to nothing draws no line');
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
  // the filter bar: a row of costs 0 to 10 in place of the animal families, no habitat or cost menu; one cost at a time, again for every cost
  assert.deepEqual(await p.evaluate(() => [document.querySelectorAll('.chead .ctab').length, document.querySelectorAll('.chead .tab').length, !!document.querySelector('.chead [data-k="hab"], .chead [data-k="cost"]')]), [7, 0, false], 'a cost row (1 to 6 and 7+), no families, no habitat or cost menu');
  await click(p, '.chead .ctab[data-cost="3"]'); await wait(80);
  const only3 = await p.evaluate(() => [...document.querySelectorAll('.cgrid .tl')].map(t => t.querySelector('.mcost')?.dataset.n));
  assert.ok(only3.length > 3 && only3.every(n => n === '3'), 'one cost shows only its cards');
  await click(p, '.chead .ctab[data-cost="3"]'); await wait(80);
  assert.equal(await p.$$eval('.cgrid .tl', e => e.length), grid.length, 'the same cost again: every card');
  await click(p, '.chead .ctab[data-cost="7"]'); await wait(80);   // 7+: every card that costs 7 or more
  const top = await p.evaluate(() => [...document.querySelectorAll('.cgrid .tl')].map(t => +t.querySelector('.mcost')?.dataset.n));
  assert.ok(top.some(n => n > 7) && top.every(n => n >= 7), 'the last tab is 7 and up');
  await click(p, '.chead .ctab[data-cost="7"]'); await wait(80);
  await click(p, '#fheroes'); await wait(80);   // Heroes only: the legendaries alone
  const heroes = await p.evaluate(() => [...document.querySelectorAll('.cgrid .tl')].map(t => t.dataset.card));
  assert.ok(heroes.length && heroes.every(id => C[id].rarity === 'legendary'), 'Heroes only shows only legendaries');
  await click(p, '#fheroes'); await wait(80);
  // a new deck: its leader first, then cards; the tray holds a piece per copy in cost order, a count per cost, the rest
  // empty cells; the deck rules are the mana ones (no stars)
  await click(p, '#dnew'); await p.waitForSelector('.lv'); await click(p, '.lv[data-id="warlord_legend"]');
  await p.keyboard.type('Mana test'); await p.keyboard.press('Enter');
  assert.equal(await p.$('.coll .side'), null, 'an open deck is the tray, not the side column');
  assert.equal(await p.$$eval('.mtray .cell.empty', e => e.length), 24, 'the leader\'s card and 24 empty cells');
  const want = ['wisp_1', 'wisp_1', 'wisp_2', 'wisp_2', 'wisp_3', 'wisp_3', 'wisp_4', 'wisp_4', 'wisp_5', 'wisp_5', 'wisp_6', 'wisp_6', 'spikes_3', 'spikes_3', 'flight_2', 'flight_2',
    'spikes_1', 'spikes_1', 'flight_6', 'flight_6', 'cantrip_2', 'cantrip_2', 'hungry_3', 'hungry_3'];
  for (const id of want) { await click(p, `.cgrid .tl[data-card="${id}"]`); await wait(30); }
  const tray = await p.evaluate(() => ({ cells: [...document.querySelectorAll('.mtray .cell')].map(e => ({ id: e.dataset.card || null, cost: +(e.querySelector('.mcost')?.dataset.n || 0),
      x: e.getBoundingClientRect().left, y: e.getBoundingClientRect().top })),
    counts: [...document.querySelectorAll('.mtray .rcount')].map(b => +b.textContent), leader: document.querySelector('.mtray .tlead')?.dataset.card,
    stars: !!document.querySelector('#fstars, .coll .lvs'), play: document.querySelector('#play').textContent, ok: !document.querySelector('#play').disabled,
    count: document.querySelector('.mtray .fcount b').textContent, name: document.querySelector('.mtray .tname b').textContent }));
  const all = [...want, 'warlord_legend'];
  assert.equal(tray.cells.length, 25); assert.ok(tray.cells.every(c => c.id), 'every cell filled');
  assert.deepEqual(tray.cells.map(c => c.id).sort(), [...all].sort(), 'a piece per copy');
  assert.deepEqual(tray.cells.map(c => c.cost), tray.cells.map(c => C[c.id].mana).sort((a, b) => a - b), 'in cost order, each with its cost');
  // two rows, interlocking: cell i in row i % 2, each half a piece right of the one before it, and wider gaps between costs
  const ys = [...new Set(tray.cells.map(c => Math.round(c.y)))]; assert.equal(ys.length, 2, 'two rows');
  tray.cells.forEach((c, i) => assert.equal(Math.round(c.y), Math.min(...ys) + (i % 2) * (Math.max(...ys) - Math.min(...ys))));
  const steps = tray.cells.slice(1).map((c, i) => c.x - tray.cells[i].x), split = tray.cells.slice(1).map((c, i) => c.cost !== tray.cells[i].cost);
  assert.ok(Math.min(...steps.filter((d, i) => split[i])) > Math.max(...steps.filter((d, i) => !split[i])) + 10, 'the costs are parted by a crack');
  assert.deepEqual([tray.leader, tray.stars, tray.count, tray.name], ['warlord_legend', false, '25/25', 'Mana test']);
  assert.deepEqual([tray.ok, tray.play], [true, 'Play this deck']);
  // hovering a piece shows its card above the tray; clicking it takes that copy out and leaves an empty cell
  const trayTop = await p.$eval('.mtray', e => e.getBoundingClientRect().top);
  const piece = await p.$('.mtray .cell[data-card="wisp_3"]'), b = await piece.boundingBox();
  await p.mouse.move(b.x + 4, b.y + 4); await p.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
  const pop = await p.evaluate(() => { const e = document.getElementById('pop'); return { on: e.style.display !== 'none', bottom: e.getBoundingClientRect().bottom, name: e.querySelector('.pname')?.textContent }; });
  assert.ok(pop.on && pop.bottom <= trayTop && pop.name === C.wisp_3.name, 'the full card, clear of the tray');
  await piece.click(); await wait(50);
  assert.deepEqual(await p.evaluate(() => [document.querySelectorAll('.mtray .cell[data-card="wisp_3"]').length, document.querySelectorAll('.mtray .cell.empty').length,
    document.querySelector('.mtray .fcount b').textContent]), [1, 1, '24/25']);
  await click(p, '.cgrid .tl[data-card="wisp_3"]'); await wait(50);
  await click(p, '#play');
  await p.waitForSelector('.mhome');
  assert.match(await p.$eval('.mhome .dk.on', e => e.textContent), /Mana test/, 'the deck is on home, chosen');
  // the same deck in the side list (?deckview=list, kept in the browser): each strip its cost, the piece's figure, the name
  // no strength; two copies as two dots, a legendary its gem; no stars anywhere
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


// The square board (AK_MAP=map_sq16) draws its own card everywhere, learned from the map at load: the collection, outside any
// match, shows it with both numbers, and so does the opening hand.
test('on the square board every card is the rectangular one, its cost and strength showing', async () => {
  const sq = await startServer({ AK_MAP: 'map_sq16' }), p = await seat();
  try {
    await p.goto(sq.url + '/', { waitUntil: 'networkidle0' }); await giveDeck(p, 'w1', 'Cheap', CHEAP);
    await p.goto(sq.url + '/#/collection', { waitUntil: 'networkidle0' }); await p.waitForSelector('.coll .cgrid .tl .mcard');
    const tiles = await p.evaluate(() => { const C = window.__ak.cards(); return [...document.querySelectorAll('.cgrid .tl')].map(t => ({ rc: !!t.querySelector('.mcard.rc'), hex: !!t.querySelector('.mpiece'),
      cost: t.querySelector('.mcost')?.dataset.n, str: t.querySelector('.mstr')?.dataset.n, want: [String(C[t.dataset.card].mana), String(C[t.dataset.card].str)] })); });
    assert.ok(tiles.length > 10 && tiles.every(t => t.rc && !t.hex), 'the collection draws the rectangular card');
    for (const t of tiles) assert.deepEqual([t.cost, t.str], t.want);
    await p.goto(sq.url + '/', { waitUntil: 'networkidle0' }); await click(p, '#mprac'); await p.waitForSelector('.mhome [data-deck].on');
    for (let i = 0; i < 20 && !(await p.evaluate(() => location.hash.startsWith('#/m/'))); i++) { await click(p, '#mgo').catch(() => {}); await wait(300); }
    assert.ok(await until(p, () => !!document.querySelector('#scr.mana #hand.mull .hc .mcard.rc .mstr')), 'the opening hand in the rectangular card');
    const hand = await p.evaluate(() => window.__ak().V.game.hand.map(h => { const el = document.querySelector(`#hand .hc[data-iid="${h.iid}"]`);
      return [String(h.cost), el.querySelector('.mcost')?.dataset.n, String(h.str), el.querySelector('.mstr')?.dataset.n]; }));
    for (const [c, cs, s, ss] of hand) { assert.equal(cs, c); assert.equal(ss, s); }
    // a choice of cards (Scout) lays them out over the board, on screen: the hand's own placing once took them below it (2026-11-23)
    await click(p, '#skip'); assert.ok(await until(p, () => window.__ak().V.game.decision === 'yours' && !window.__ak().PB.busy, null, 30000));
    await p.evaluate(() => { const V = window.__ak().V; window.__ak.feed({ ...V, game: { ...V.game, pending: { mode: 'choice', kind: 'scout', source: 'scout_3',
      options: ['wisp_1', 'flight_2', 'cantrip_3'].map((id, i) => ({ kind: 'card', id, v: i })) } } }); });
    assert.ok(await until(p, () => document.querySelectorAll('#opts.on .hc').length === 3), 'three cards offered');
    const boxes = await p.evaluate(() => [...document.querySelectorAll('#opts .hc')].map(e => { const r = e.getBoundingClientRect(); return [r.top, r.bottom, r.width, innerHeight]; }));
    for (const [t, b, w, H] of boxes) assert.ok(t >= 0 && b <= H && w > 100, `an offered card on screen: ${t}-${b}`);
    assert.deepEqual(p.errors, []);
  } finally { await p.browserContext().close(); sq.stop(); }
});

// A phone held upright on the square board gets the upright match screen (app.js fitStage, mana.css .game.port): every card
// of the hand and End turn on screen and a thumb's size (40 CSS px and more), on a short phone and a tall one; a wide window
// keeps the desktop screen.
test('upright on the square board: the phone layout, its hand and End turn on screen and thumb-sized', async () => {
  const sq = await startServer({ AK_MAP: 'map_sq16' }), p = await seat();
  try {
    await p.goto(sq.url + '/', { waitUntil: 'networkidle0' }); await giveDeck(p, 'w1', 'Cheap', CHEAP);
    await p.setViewport({ width: 390, height: 664, deviceScaleFactor: 1, isMobile: true, hasTouch: true });
    await p.goto(sq.url + '/', { waitUntil: 'networkidle0' }); await click(p, '#mprac'); await p.waitForSelector('.mhome [data-deck].on');
    for (let i = 0; i < 20 && !(await p.evaluate(() => location.hash.startsWith('#/m/'))); i++) { await click(p, '#mgo').catch(() => {}); await wait(300); }
    assert.ok(await until(p, () => !!document.querySelector('#scr.mana #hand.mull')), 'the opening hand');
    await click(p, '#skip'); assert.ok(await until(p, () => window.__ak().V.game.decision === 'yours' && !window.__ak().PB.busy, null, 30000));
    for (const [w, h] of [[390, 664], [430, 850]]) {
      await p.setViewport({ width: w, height: h, deviceScaleFactor: 1, isMobile: true, hasTouch: true }); await wait(400);
      const m = await p.evaluate(() => { const box = e => { const r = e.getBoundingClientRect(); return { l: r.left, t: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height }; };
        return { port: document.getElementById('scr').classList.contains('port'), cards: [...document.querySelectorAll('#hand .hc')].map(box), end: box(document.getElementById('tbtn')), W: innerWidth, H: innerHeight }; });
      assert.ok(m.port, `upright at ${w} x ${h}`);
      assert.ok(m.cards.length >= 3, 'a hand');
      for (const b of [...m.cards, m.end]) {
        assert.ok(b.l >= 0 && b.t >= 0 && b.r <= m.W && b.b <= m.H, `on screen at ${w} x ${h}: ${JSON.stringify(b)}`);
        assert.ok(b.w >= 40 && b.h >= 40, `a thumb's size at ${w} x ${h}: ${JSON.stringify(b)}`);
      }
    }
    await p.setViewport({ width: 1512, height: 800, deviceScaleFactor: 1, isMobile: true, hasTouch: true }); await wait(400);
    assert.ok(!(await p.evaluate(() => document.getElementById('scr').classList.contains('port'))), 'a wide window keeps the desktop screen');
    assert.deepEqual(p.errors, []);
  } finally { await p.browserContext().close(); sq.stop(); }
});
