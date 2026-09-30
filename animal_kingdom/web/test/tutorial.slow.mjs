// The tutorial played through by clicks, as a new player would: Learn to play on home, each forced step (the hinted
// card, the one ringed crossroad, the deck), then free play toward the den until the win, and Play a match back home.
// SHOTS=<dir> saves a 2x screenshot at every lesson (for judging the coach's look and words).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser({ newPlayer: true }); });
after(async () => { await browser?.close(); server?.stop(); });

const wait = ms => new Promise(r => setTimeout(r, SHOTS ? ms : ms / 3));   // screenshots need settled animations; state checks don't
const SHOTS = process.env.SHOTS;

test('a new player learns the game in both lessons and wins them', { timeout: 600000 }, async () => {
  const page = await browser.newPage(); page.errors = [];
  page.on('pageerror', e => page.errors.push(String(e)));
  if (SHOTS) await page.setViewport({ width: 1512, height: 800, deviceScaleFactor: 2 });
  await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  assert.ok(await page.$('#learn'), 'a first visit offers the tutorial');
  // the menu leaves a tutorial for home at once
  await page.click('#learn'); await page.waitForFunction(() => window.__ak().V && window.__ak().V.phase === 'playing', { timeout: 10000 });
  assert.equal(await page.$eval('#menubtn', e => e.dataset.tip), 'Leave tutorial');   // the flag leaves a tutorial at once
  await page.click('#menubtn'); await page.waitForSelector('.home #learn');
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/0-home.png` });
  await page.click('#learn');
  await page.waitForFunction(() => window.__ak().V && window.__ak().V.phase === 'playing', { timeout: 10000 });

  const state = () => page.evaluate(() => { const { V, d } = window.__ak();
    return { phase: V.phase, mine: !!(d && d.mine), lesson: d && d.lesson ? d.lesson.id : null, at: d && d.lesson ? d.lesson.at || null : null, only: d && d.lesson ? d.lesson.only || null : null, next: !!(d && d.lesson && d.lesson.next),
      places: d ? d.places : {}, pend: !!V.game.pending, hand: V.game.hand.map(h => h.id), board: V.game.board, canDraw: !!(V.game.legal && V.game.legal.draw) }; });
  const click = async sel => { let el, b;   // the target may still be appearing: wait up to 2 s for it to be on screen
    for (let t = 0; t < 40 && !b; t++) { el = await page.$(sel); b = el && await el.boundingBox(); if (!b) await new Promise(r => setTimeout(r, 50)); }
    assert.ok(b, `nothing to click at ${sel}`);
    await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2); await wait(250); await page.mouse.move(5, 5); await wait(150); };
  const owner = (s, cr) => { const st = s.board[cr]; return st && st.length ? st[st.length - 1].owner : null; };

  const picked = new Set();   // SHOTS: each step also once right after its card is picked (its second line, its circles)
  const shootPicked = async (lesson, s) => { const k = `${lesson}-${s.lesson}`; if (!SHOTS || !s.lesson || picked.has(k)) return;
    picked.add(k); await wait(350); await page.screenshot({ path: `${SHOTS}/${lesson}-p-${s.lesson}.png` }); };
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
      if (sel !== s.only.card) { await click(`.hc[data-id="${s.only.card}"]`); await shootPicked(lesson, s); continue; }   // pick it, and read the next line
      const rings = (await state()).places[s.only.card].filter(t => t[0] === 'cr'), t = process.env.PICK === 'last' ? rings[rings.length - 1] : rings[0];   // any ringed crossroad: the lesson allows them all
      await click(`#board [data-cr="${t[1]}"]`);
      continue;
    }
    // free play, as a newcomer following the coach: the den when it's open, the corner it points at, a cover, else push
    // right; draw when the hand is empty
    const moves = Object.entries(s.places).flatMap(([id, ts]) => ts.map(t => ({ id, t })));
    const pick = moves.find(m => m.t[0] === 'hq')
      || moves.find(m => owner(s, m.t[1]) === 'B') || moves.filter(m => !s.board[m.t[1]]).sort((a, b) => b.t[1][0] - a.t[1][0])[0];
    if (!pick) { await click(s.canDraw ? '#deck' : '#tbtn'); continue; }
    await click(`.hc[data-id="${pick.id}"]`); await shootPicked(lesson, s);
    await click(pick.t[0] === 'hq' ? '#board [data-hq="B"]' : `#board [data-cr="${pick.t[1]}"]`);
  } };

  // lesson 1: the basics, won by taking the den ('watch', on the opponent's turn, passes too fast to catch with no bot pause)
  const seen1 = []; await play(1, seen1);
  await page.waitForFunction(() => window.__ak().V.phase === 'match_over', { timeout: 20000 });
  await wait(1200);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/1-end.png` });
  assert.match(await page.$eval('#endov', e => e.textContent), /Victory/);
  assert.equal(await page.evaluate(() => window.__ak().V.game.result.reason), 'hq_capture', 'lesson 1 is won by taking the den');
  const byDen = true;
  for (const id of ['welcome', 'yourden', 'theirden', 'foodcount', 'oppfood', 'cards', 'lion', 'lion2', 'buffalo', 'patch', 'wolf', 'corner', 'food', 'actions', 'draw', 'cover', 'food2', 'roarinfo', 'roar', 'roared', 'free', ...(byDen ? ['den'] : [])])
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
  for (const id of ['intro2', 'lion', 'glow', 'lynx', 'eagleinfo', 'eagle', 'alone', 'buffalo2', 'draw2', 'squirrelinfo', 'squirrel', 'covered', 'mambainfo', 'mamba', 'uncovered', 'goal2', 'draw3', 'apexinfo', 'apex', 'free2', 'feed'])
    assert.ok(seen2.includes(id), `lesson 2's ${id} came up (${seen2})`);
  await page.click('.endbox .play');
  await page.waitForSelector('.home .bar:not(.first)');   // home, with the full piece: the tutorial counts as learned
  assert.deepEqual(page.errors, []);
  await page.close();
});
