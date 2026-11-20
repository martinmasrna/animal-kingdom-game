// The mana rules' friend match in the browser (the prototype of 2026-11-20; static/mana.js, mana.css): home offers only a
// friend match, two windows create and join one, the opening hands are the full cards with their costs, and in play the
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
  assert.ok(await A.$('.mhome'), 'home in the mana rules is the friend match');
  assert.equal(await A.$('.home'), null, 'not the usual home');
  await click(A, '[data-deck="pool_1"]'); await click(A, '#mgo');
  await A.waitForSelector('.bigcode');
  const code = await A.$eval('.bigcode', e => e.textContent);
  await B.goto(`${server.url}/?rules=mana#/join/${code}`, { waitUntil: 'networkidle0' });
  await click(B, '[data-deck="pool_3"]'); await click(B, '#mgo');
  for (const p of [A, B]) assert.ok(await until(p, () => !!document.querySelector('#scr.mana #hand.mull .hc .mcard .plaque')), 'the opening hand in full');
  // each card in the opening hand: its cost in the gold hexagon, as the view says
  const costs = await A.evaluate(() => { const { V } = window.__ak(); return V.game.hand.map(h => [String(h.cost), document.querySelector(`#hand .hc[data-iid="${h.iid}"] .mcost text`)?.textContent]); });
  for (const [want, shown] of costs) assert.equal(shown, want);
  for (const p of [A, B]) await click(p, '#skip');
  // the first turn that can be played (a turn the mana pays for nothing in is skipped): the rail's six hexagons, the
  // board's 24 regions and two bases of three
  const mine = () => { const a = window.__ak(); return !!(a.d && a.d.mine && !a.PB.busy && a.V.game.decision === 'yours'); };
  assert.ok(await until(A, () => window.__ak().V.game.decision !== 'mulligan'));
  let P = null;
  for (let i = 0; i < 100 && !P; i++) { for (const p of [A, B]) if (await p.evaluate(mine)) P = p; await wait(100); }
  assert.ok(P, 'a player may act');
  const look = await P.evaluate(() => ({ pips: document.querySelectorAll('.mmana .mpips i').length, on: document.querySelectorAll('.mmana .mpips i.on').length,
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
    const after = await P.evaluate(() => { const { V } = window.__ak(); return { mine: V.game.current === V.you, spent: document.querySelectorAll('.mmana .mpips i.spent').length,
      label: document.querySelector('.mmana div').textContent, left: V.game.mana[V.you].left }; });
    if (after.mine) assert.equal(after.spent, play.cost, 'its cost spent');
    else assert.match(after.label, /^Next turn: \d mana$/);
    assert.ok(await P.evaluate(() => !document.querySelector('#board .cr.unit .mcost')), 'a piece on the board has no cost');
  }
  assert.deepEqual([...A.errors, ...B.errors], []);
});
