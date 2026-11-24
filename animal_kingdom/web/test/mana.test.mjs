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
// A deck of the mana collection on the profile: 12 Wisps (1 to 6, two each), Flight 1, 3, 6 and Spikes 1 two each, two Spikes 3, two Cantrip 2s and the Warlord (25, legal in the mana rules).
const DECK = { ...Object.fromEntries([...Array(6).keys()].map(i => ['wisp_' + (i + 1), 2])), flight_1: 2, flight_3: 2, flight_6: 2, spikes_1: 2, spikes_3: 2, cantrip_2: 2, warlord_legend: 1 };
// A cheap one (nothing over 3 mana) for the matches that must get going: the Wisps 1 to 3, the cantrips, fliers, Spikes and Hungry, and the Warlord.
const CHEAP = { ...Object.fromEntries([1, 2, 3].map(i => ['wisp_' + i, 2])), cantrip_2: 2, cantrip_3: 2, flight_1: 2, sky_maw_2: 2, flight_3: 2, spikes_1: 2, spikes_3: 2, hungry_1: 2, hungry_3: 2, warlord_legend: 1 };
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

test('the collection in the mana rules: the mana card with its cost, sorted by cost, the deck in the side list, the mana deck rules, and the deck on home', async () => {
  const p = await seat();
  await p.goto(server.url + '/', { waitUntil: 'networkidle0' });
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
  // a new deck: its leader first, then cards; the side list holds a strip per card in cost order: its cost, the piece's
  // figure, the name, no strength; two copies as two dots; the deck rules are the mana ones (no stars)
  await click(p, '#dnew'); await p.waitForSelector('.lv'); await click(p, '.lv[data-id="warlord_legend"]');
  await p.keyboard.type('Mana test'); await p.keyboard.press('Enter');
  await p.waitForSelector('.side .st.mst');
  const want = ['wisp_1', 'wisp_1', 'wisp_2', 'wisp_2', 'wisp_3', 'wisp_3', 'wisp_4', 'wisp_4', 'wisp_5', 'wisp_5', 'wisp_6', 'wisp_6', 'spikes_3', 'spikes_3', 'flight_3', 'flight_3',
    'spikes_1', 'spikes_1', 'flight_6', 'flight_6', 'cantrip_2', 'cantrip_2', 'hungry_3', 'hungry_3'];
  for (const id of want) { await click(p, `.cgrid .tl[data-card="${id}"]`); await wait(30); }
  const all = [...want, 'warlord_legend'];
  const list = await p.evaluate(() => ({ strips: [...document.querySelectorAll('.side .st')].map(s => ({ id: s.dataset.card, cost: +(s.querySelector('.sc .mchip')?.dataset.n || 0),
      fig: !!s.querySelector('.hd img'), dots: s.querySelectorAll('.x i').length, x: s.querySelector('.x').textContent })), stars: !!document.querySelector('.coll .lvs, #fstars'),
    play: document.querySelector('#play').textContent, ok: !document.querySelector('#play').disabled,
    count: document.querySelector('.side .fcount b').textContent, name: document.querySelector('.side .dtile.on .nm-edit').textContent }));
  assert.equal(list.stars, false, 'no stars');
  assert.deepEqual(list.strips.map(s => s.cost), list.strips.map(s => C[s.id].mana).sort((a, b) => a - b), 'the list by cost');
  assert.deepEqual(list.strips.map(s => [s.id, s.fig, s.x, s.dots]), list.strips.map(s => [s.id, true, '', all.filter(id => id === s.id).length > 1 ? 2 : 0]), 'figure, and two dots for a pair');
  assert.deepEqual([list.count, list.name, list.ok, list.play], ['25/25', 'Mana test', true, 'Play this deck']);
  // clicking a strip takes one copy out
  await click(p, '.side .st[data-card="wisp_3"]'); await wait(50);
  assert.deepEqual(await p.evaluate(() => [document.querySelectorAll('.side .st[data-card="wisp_3"] .x i').length, document.querySelector('.side .fcount b').textContent]), [0, '24/25']);
  await click(p, '.cgrid .tl[data-card="wisp_3"]'); await wait(50);
  await click(p, '#play');
  await p.waitForSelector('.mhome');
  assert.match(await p.$eval('.mhome .dk.on', e => e.textContent), /Mana test/, 'the deck is on home, chosen');
  assert.deepEqual(p.errors, []);
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
      options: ['wisp_1', 'flight_3', 'cantrip_3'].map((id, i) => ({ kind: 'card', id, v: i })) } } }); });
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

// The target arrow (static/aim.js): asked to choose the enemy a Roar acts on, an arrow runs from the unit whose Roar it is
// to the pointer, settling on a legal target; once the target is chosen it is gone.
test('the target arrow: during a target prompt it starts at the source and settles on the target; after the choice it is gone', async () => {
  const sq = await startServer({ AK_MAP: 'map_sq16' }), p = await seat();
  try {
    await p.goto(sq.url + '/', { waitUntil: 'networkidle0' }); await giveDeck(p, 'w1', 'Cheap', CHEAP);
    await click(p, '#mprac'); await p.waitForSelector('.mhome [data-deck].on');
    for (let i = 0; i < 20 && !(await p.evaluate(() => location.hash.startsWith('#/m/'))); i++) { await click(p, '#mgo').catch(() => {}); await wait(300); }
    assert.ok(await until(p, () => !!document.querySelector('#scr.mana #hand.mull')), 'the opening hand');
    await click(p, '#skip'); assert.ok(await until(p, () => window.__ak().V.game.decision === 'yours' && !window.__ak().PB.busy, null, 30000));
    // your Hunter on 2,2 has just roared: the enemy on 3,2 or the one on 2,3 (a crafted view, fed twice so nothing lands)
    await p.evaluate(() => { const V = window.__ak().V, me = V.you, them = me === 'A' ? 'B' : 'A';
      const board = { '2,2': [{ iid: 901, id: 'hunter_5', owner: me, str: 4 }], '3,2': [{ iid: 902, id: 'wisp_3', owner: them, str: 6 }], '2,3': [{ iid: 903, id: 'wisp_2', owner: them, str: 4 }] };
      const v = { ...V, game: { ...V.game, board, decision: 'your_choice', legal: { place: {}, leader: false },
        pending: { mode: 'choice', kind: 'effect', source: 'hunter_5', sourceIid: 901, optional: false, options: ['3,2', '2,3'].map(c => ({ kind: 'cr', cr: c, v: c })) } } };
      window.__ak.feed(v); window.__ak.feed(v); });
    await wait(300);
    const at = sel => p.evaluate(sel => { const r = document.querySelector(sel).getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }, sel);
    const me = await p.evaluate(() => window.__ak().V.you), flip = c => me === 'A' ? c : `${5 - +c.split(',')[0]},${c.split(',')[1]}`;   // the board's columns turn for seat B
    assert.equal(await p.evaluate(() => document.getElementById('choicebar').classList.contains('on')), false, 'no prompt: the arrow and the rings say it');
    const [tx, ty] = await at(`#board .cr[data-cr="${flip('3,2')}"] .mstand`);
    await p.mouse.move(tx - 40, ty + 60); await p.mouse.move(tx, ty, { steps: 5 }); await wait(200);
    const arrow = await p.evaluate(sel => { const a = document.getElementById('aim'), st = document.getElementById('stage'), S = st.getBoundingClientRect(), k = S.width / st.offsetWidth;
      const r = document.querySelector(sel).getBoundingClientRect(), stg = (x, y) => [(x - S.left) / k, (y - S.top) / k];
      return { n: a ? a.querySelectorAll('polygon').length : 0, from: a && a.dataset.from && a.dataset.from.split(',').map(Number), fig: [...stg(r.left, r.top), ...stg(r.right, r.bottom)] }; },
      `#board .cr[data-cr="${flip('2,2')}"] .mstand`);
    assert.ok(arrow.n >= 3, 'the arrow is drawn: blocks and a head');
    const [x, y] = arrow.from, [l, t, r, b] = arrow.fig;
    assert.ok(x >= l && x <= r && y >= t && y <= b, `it starts on the Hunter's body: ${arrow.from} in ${arrow.fig.map(Math.round)}`);
    await p.mouse.click(tx, ty); await wait(100);
    assert.equal(await p.evaluate(() => document.querySelectorAll('#aim polygon').length), 0, 'chosen: the arrow is gone');
    assert.deepEqual(p.errors, []);
  } finally { await p.browserContext().close(); sq.stop(); }
});

// The gauntlet (#/gauntlet/DECK): your deck against each other deck of yours, once going first and once second; a row's
// game starts with the seat it names going first, and its result comes back to the row (Martin, 2026-11-24).
test('a gauntlet lists two games against each other deck, and a game starts with the player it says going first', async () => {
  const p = await seat();
  try {
    await p.goto(server.url + '/', { waitUntil: 'networkidle0' });
    await p.evaluate(async (decks, seen) => { const h = { 'X-AK-Key': localStorage.getItem('ak:key'), 'Content-Type': 'application/json' };
      await fetch('/api/me/decks', { method: 'PUT', headers: h, body: JSON.stringify(decks) });
      await fetch('/api/me/patch', { method: 'POST', headers: h, body: JSON.stringify({ version: seen }) }); },
      [{ id: 'g1', name: 'Mine', cards: CHEAP, leader: 'warlord_legend' }, { id: 'g2', name: 'Other', cards: DECK, leader: 'warlord_legend' }, { id: 'g3', name: 'Third', cards: CHEAP, leader: 'warlord_legend' }], NEWEST);
    await p.goto(server.url + '/#/gauntlet/mine', { waitUntil: 'networkidle0' }); await p.reload({ waitUntil: 'networkidle0' });   // the profile's new decks
    await p.waitForSelector('.glist .grow');
    const rows = await p.evaluate(() => [...document.querySelectorAll('.glist .grow')].map(r => r.textContent));
    assert.equal(rows.length, 4, 'two games against each of the two other decks');
    for (const [i, first] of [[1, 'B'], [0, 'A']]) {
      await p.goto(server.url + '/#/gauntlet/mine', { waitUntil: 'networkidle0' }); await p.waitForSelector('.glist .grow');
      await p.evaluate(i => document.querySelectorAll('[data-g]')[i].click(), i);
      assert.ok(await until(p, () => location.hash.startsWith('#/m/') && window.__ak().V && window.__ak().V.game), 'the game opens');
      await click(p, '#skip').catch(() => {});
      assert.ok(await until(p, () => window.__ak().V.game.decision && window.__ak().V.game.decision !== 'mulligan', null, 20000));
      assert.equal(await p.evaluate(() => window.__ak().V.game.first), first);
    }
    assert.deepEqual(p.errors, []);
  } finally { await p.browserContext().close(); }
});

// The held card over the board (Martin, 2026-11-24: "flickering like crazy"): the tile under the mouse comes from the board's
// geometry, so one slow pass over a tile it may take turns the card into its creature once and back once, not dozens of
// times; and over the enemy den, a card that may raid becomes its creature over the den's food.
test('a held card turns into its creature once per tile it passes, and over the den while it may raid', async () => {
  const sq = await startServer({ AK_MAP: 'map_sq16' }), p = await seat();
  try {
    await p.setViewport({ width: 1512, height: 800 });
    await p.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'no-preference' }]);   // the grip is motion: off when reduced
    await p.goto(sq.url + '/', { waitUntil: 'networkidle0' });
    await giveDeck(p, 'w1', 'Fly', { flight_1: 2, flight_3: 2, flight_6: 2, wisp_1: 2, wisp_2: 2, wisp_3: 2, cantrip_2: 2, cantrip_3: 2, mama_spore: 2, spikes_1: 2, spikes_3: 2, hungry_1: 2, warlord_legend: 1 });
    await click(p, '#mprac'); await p.waitForSelector('.mhome [data-deck].on');
    for (let i = 0; i < 20 && !(await p.evaluate(() => location.hash.startsWith('#/m/'))); i++) { await click(p, '#mgo').catch(() => {}); await wait(300); }
    assert.ok(await until(p, () => !!document.querySelector('#skip'))); await click(p, '#skip');
    assert.ok(await until(p, () => window.__ak().V.game.decision === 'yours' && !window.__ak().PB.busy, null, 30000));
    await wait(1200);
    const iid = await p.evaluate(() => { const g = window.__ak().V.game; const h = g.hand.find(c => c.id.startsWith('flight_') && c.cost <= 1) || g.hand.find(c => c.cost <= 1); return h ? h.iid : null; });
    if (iid == null) return;   // no card this cheap dealt: nothing to hold
    const c = await p.evaluate(i => { const r = document.querySelector(`#hand .hc[data-iid="${i}"]`).getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }, iid);
    for (let k = 0; k < 3 && !(await p.evaluate(() => !!document.querySelector('.flight.carry'))); k++) {   // picked up: it hangs on the pointer
      await p.mouse.move(c[0], c[1]); await p.mouse.down(); await p.mouse.up(); await until(p, () => !!document.querySelector('.flight.carry'), null, 2000);
    }
    assert.ok(await p.evaluate(() => !!document.querySelector('.flight.carry')), 'the card is picked up');
    await p.evaluate(() => { window.__fl = 0; new MutationObserver(() => window.__fl++).observe(document.querySelector('.flight.carry'), { attributes: true, attributeFilter: ['class'] }); });
    const t = await p.evaluate(() => { const cr = window.__ak().d.rings[0], r = document.querySelector(`#board [data-cr="${cr}"]`).getBoundingClientRect(); return [r.left + r.width / 2, r.top, r.height]; });
    for (let y = t[1] + t[2] + 20; y > t[1] - 60; y -= 2) { await p.mouse.move(t[0], y); await wait(6); }
    const switches = await p.evaluate(() => window.__fl);
    assert.ok(switches >= 1 && switches <= 4, `the card switched ${switches} times over one tile`);
    if (await p.evaluate(() => window.__ak().V.game.hand.find(h => h.iid === window.__ak().ui.selIid)?.id.startsWith('flight_'))) {
      const den = await p.evaluate(() => { const r = document.querySelector('#board .mden.B[data-hq] .core').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; });
      await p.mouse.move(den[0], den[1]); await wait(400);
      assert.ok(await p.evaluate(() => document.querySelector('.flight.carry').classList.contains('over')), 'over the den, the flier is its creature');
    }
    assert.deepEqual(p.errors, []);
  } finally { await p.browserContext().close(); sq.stop(); }
});
