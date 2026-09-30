// The tutorial played through by clicks, as a new player would: Learn to play on home, each forced step (the hinted
// card, the one ringed crossroad, the deck), then free play toward the den until the win, and Play a match back home.
// SHOTS=<dir> saves a 2x screenshot at every lesson (for judging the coach's look and words).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser({ newPlayer: true }); });
after(async () => { await browser?.close(); server?.stop(); });

const wait = ms => new Promise(r => setTimeout(r, ms));
const SHOTS = process.env.SHOTS;

test('a new player learns the game in both lessons and wins them', { timeout: 600000 }, async () => {
  const page = await browser.newPage(); page.errors = [];
  page.on('pageerror', e => page.errors.push(String(e)));
  if (SHOTS) await page.setViewport({ width: 1512, height: 800, deviceScaleFactor: 2 });
  await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  assert.ok(await page.$('#learn'), 'a first visit offers the tutorial');
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/0-home.png` });
  await page.click('#learn');
  await page.waitForFunction(() => window.__ak().V && window.__ak().V.phase === 'playing', { timeout: 10000 });

  const state = () => page.evaluate(() => { const { V, d } = window.__ak();
    return { phase: V.phase, mine: !!(d && d.mine), lesson: d && d.lesson ? d.lesson.id : null, at: d && d.lesson ? d.lesson.at || null : null, only: d && d.lesson ? d.lesson.only || null : null, next: !!(d && d.lesson && d.lesson.next),
      places: d ? d.places : {}, pend: !!V.game.pending, hand: V.game.hand.map(h => h.id), board: V.game.board, canDraw: !!(V.game.legal && V.game.legal.draw) }; });
  const click = async sel => { const el = await page.$(sel); assert.ok(el, `nothing to click at ${sel}`); const b = await el.boundingBox();
    await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2); await wait(250); await page.mouse.move(5, 5); await wait(150); };
  const owner = (s, cr) => { const st = s.board[cr]; return st && st.length ? st[st.length - 1].owner : null; };

  const play = async (lesson, seen) => { for (let step = 0; step < 300; step++) {
    await wait(300);
    const s = await state();
    if (s.phase !== 'playing') break;
    if (s.lesson && !seen.includes(s.lesson)) { seen.push(s.lesson); if (SHOTS) await page.screenshot({ path: `${SHOTS}/${lesson}-${seen.length}-${s.lesson}.png` }); }
    if (s.next) { await click('#coachnext'); continue; }   // an opening step: read it, then Next
    if (!s.mine) continue;
    if (s.pend) {   // a Roar asking for a target: take the first ringed crossroad, or skip
      const ring = await page.$('#board .cr.tgt'); if (ring) await click('#board .cr.tgt'); else await click('#skip'); continue;
    }
    if (s.only && (s.only.card || s.only.deck)) {   // a forced step: exactly one thing can be done
      if (s.only.deck) { await click('#deck'); continue; }
      const sel = await page.evaluate(() => window.__ak().ui.sel);
      if (sel !== s.only.card) { await click(`.hc[data-id="${s.only.card}"]`); continue; }   // pick it, and read the next line
      const rings = (await state()).places[s.only.card].filter(t => t[0] === 'cr'), t = process.env.PICK === 'last' ? rings[rings.length - 1] : rings[0];   // any ringed crossroad: the lesson allows them all
      await click(`#board [data-cr="${t[1]}"]`);
      continue;
    }
    // free play, as a newcomer following the coach: the den when it's open, the corner it points at, a cover, else push
    // right; draw when the hand is empty
    const moves = Object.entries(s.places).flatMap(([id, ts]) => ts.map(t => ({ id, t })));
    const pick = moves.find(m => m.t[0] === 'hq') || (s.lesson === 'corner' && moves.find(m => m.t[1] === s.at.cr))
      || moves.find(m => owner(s, m.t[1]) === 'B') || moves.filter(m => !s.board[m.t[1]]).sort((a, b) => b.t[1][0] - a.t[1][0])[0];
    if (!pick) { await click(s.canDraw ? '#deck' : '#tbtn'); continue; }
    await click(`.hc[data-id="${pick.id}"]`);
    await click(pick.t[0] === 'hq' ? '#board [data-hq="B"]' : `#board [data-cr="${pick.t[1]}"]`);
  } };

  // lesson 1: the basics, won by taking the den
  const seen1 = []; await play(1, seen1);
  await page.waitForFunction(() => window.__ak().V.phase === 'match_over', { timeout: 20000 });
  await wait(1200);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/1-end.png` });
  assert.match(await page.$eval('#endov', e => e.textContent), /Victory/);
  assert.equal(await page.evaluate(() => window.__ak().V.game.result.reason), 'hq_capture', 'lesson 1 is won by taking the den');
  const byDen = true;
  for (const id of ['welcome', 'yourden', 'theirden', 'foodcount', 'oppfood', 'cards', 'lion', 'lion2', 'buffalo', 'watch', 'patch', 'wolf', 'draw', 'actions', 'corner', 'food', 'cover', 'roar', 'roared', 'free', ...(byDen ? ['den'] : [])])
    assert.ok(seen1.includes(id), `lesson ${id} came up (${seen1})`);
  await page.waitForSelector('#nextlesson', { visible: true }); await wait(300);
  await page.click('#nextlesson');   // lesson 1 leads straight on to lesson 2
  await page.waitForFunction(() => window.__ak().V && window.__ak().V.phase === 'playing' && window.__ak().V.seats.B.bot === 'tutorial2', { timeout: 30000 });
  // lesson 2: the deeper mechanics, won on food (the den is walled off)
  const seen2 = []; await play(2, seen2);
  await page.waitForFunction(() => window.__ak().V.phase === 'match_over', { timeout: 20000 });
  await wait(1200);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/2-end.png` });
  assert.equal(await page.evaluate(() => window.__ak().V.game.result.reason), 'food', 'lesson 2 is won on food');
  for (const id of ['intro2', 'lion', 'glow', 'lynx', 'wall', 'eagle', 'buffalo2', 'draw2', 'squirrel', 'foodroar', 'covered', 'mamba', 'uncovered', 'goal2', 'draw3', 'apex', 'free2', 'feed'])
    assert.ok(seen2.includes(id), `lesson 2's ${id} came up (${seen2})`);
  await page.click('.endbox .play');
  await page.waitForSelector('.home .bar:not(.first)');   // home, with the full piece: the tutorial counts as learned
  assert.deepEqual(page.errors, []);
  await page.close();
});
