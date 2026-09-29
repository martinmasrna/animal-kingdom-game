// Every view of recorded bot-vs-bot matches, played through the client with animations off, must show exactly the
// game state: each unit visible at its crossroad in its owner's colour with its strength and buried count, nothing on
// empty crossroads, each den's gem at its food and each pit holding the right ripe and ghost fruit, both hands, the
// turn button, the end-of-game overlay, and no page errors.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, recordMatches, openBrowser, gamePage, feed } from './harness.mjs';

let server, browser, matches;
before(async () => { server = await startServer(); browser = await openBrowser(); matches = recordMatches(7); });
after(async () => { await browser?.close(); server?.stop(); });

// Runs in the page: what the screen shows, against what the current view says it should show. Returns a list of
// mismatches (empty when the screen is right).
function screenMismatches() {
  const { V } = window.__ak(), G = V.game, out = [];
  if (!G) return out;
  const you = V.you, them = you === 'A' ? 'B' : 'A', rel = p => (p === you ? 'A' : 'B');
  const dcr = cr => { if (you === 'A') return cr; const [c, r] = cr.split(','); return `${6 - +c},${r}`; };
  const visible = e => { const s = getComputedStyle(e), r = e.getBoundingClientRect(); return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0.5 && r.width > 20; };
  const digits = e => [...e.querySelectorAll('img')].map(i => i.alt).join('');

  // the board
  const want = {};
  for (const [cr, st] of Object.entries(G.board)) want[dcr(cr)] = st;
  for (const el of document.querySelectorAll('#board .cr[data-cr]')) {
    const cr = el.dataset.cr, st = want[cr];
    if (!st) { if (el.classList.contains('unit') && !el.classList.contains('ghost')) out.push(`${cr}: a unit shown on an empty crossroad`); continue; }
    if (el.classList.contains('ghost')) continue;   // a placement preview under the pointer
    const top = st[st.length - 1];
    if (!el.classList.contains('unit')) { out.push(`${cr}: ${top.id} missing`); continue; }
    if (!visible(el)) out.push(`${cr}: ${top.id} not visible`);
    if (!el.classList.contains(rel(top.owner))) out.push(`${cr}: ${top.id} in the wrong colour`);
    const str = digits(el.querySelector('.boss'));
    if (str !== String(top.str)) out.push(`${cr}: ${top.id} shows strength ${str}, is ${top.str}`);
    const buried = el.querySelectorAll('.buried').length;
    if (buried !== Math.min(3, st.length - 1)) out.push(`${cr}: ${buried} buried discs for a stack of ${st.length}`);
    delete want[cr];
  }
  for (const cr of Object.keys(want)) out.push(`${cr}: no crossroad element for ${want[cr].slice(-1)[0].id}`);

  // the dens: the gem shows the food; pit i holds the ripe and ghost fruit of food and income, ten to a pit
  for (const side of ['A', 'B']) {
    const seat = side === 'A' ? you : them, food = G.food[seat], inc = G.income[seat], win = G.winFood;
    const gem = document.querySelector(`#board .dcount.${side}`);
    if (!gem || digits(gem) !== String(food)) out.push(`den ${side}: gem shows ${gem && digits(gem)}, food is ${food}`);
    const ripe = Math.min(food, win), green = Math.max(0, Math.min(inc, win - ripe));
    const pits = [...document.querySelectorAll('#board .pit img.now')].filter(i => i.src.includes(`/${side.toLowerCase()}pit`));
    if (pits.length !== 10) out.push(`den ${side}: ${pits.length} pits`);
    pits.forEach((img, i) => {
      const r = Math.max(0, Math.min(10, ripe - i * 10)), t = Math.max(0, Math.min(10, ripe + green - i * 10));
      if (!img.src.endsWith(`_${r}_${t - r}.webp`)) out.push(`den ${side} pit ${i}: shows ${img.src.split('/').pop()}, should hold ${r} ripe ${t - r} ghost`);
    });
  }

  // both hands
  const backs = document.querySelectorAll('#opphand .back').length;
  if (backs !== G.handCount[them]) out.push(`${backs} card backs, they hold ${G.handCount[them]}`);
  const hand = [...document.querySelectorAll('#hand .hc')].map(e => +e.dataset.iid);
  if (hand.join() !== G.hand.map(h => h.iid).join()) out.push(`hand shows ${hand}, is ${G.hand.map(h => h.iid)}`);

  // whose turn, and the end of a game
  const tb = document.getElementById('tbtn').textContent;
  if (V.phase === 'playing' && !(G.current === you ? /End turn/.test(tb) : /Their turn/.test(tb))) out.push(`turn button says "${tb}"`);
  const ended = V.phase === 'game_over' || V.phase === 'match_over';
  if (ended !== document.getElementById('endov').classList.contains('on')) out.push(`end overlay ${ended ? 'missing' : 'shown mid-game'}`);
  return out;
}

test('every recorded view is drawn exactly as the game state says', async t => {
  for (const { name, views } of matches) {
    await t.test(name, async () => {
      const page = await gamePage(browser, server.url);
      for (let i = 0; i < views.length; i++) {
        await feed(page, views[i]);
        const bad = await page.evaluate(screenMismatches);
        assert.deepEqual(bad, [], `view ${i} of ${name}`);
      }
      assert.deepEqual(page.errors, [], `page errors in ${name}`);
      await page.close();
    });
  }
});

// With animations on, after each view settles, no unit is left invisible and nothing is stuck mid-animation.
test('animations settle with every unit visible', async () => {
  const { name, views } = { name: matches[0].name, views: matches[0].views.slice(0, 40) }, page = await gamePage(browser, server.url, { still: false });
  for (let i = 0; i < views.length; i++) {
    await feed(page, views[i]);
    await new Promise(r => setTimeout(r, 2200));
    const hidden = await page.evaluate(() => [...document.querySelectorAll('#board .cr.unit')]
      .filter(e => { const s = getComputedStyle(e); return s.display === 'none' || +s.opacity < 0.5; }).map(e => e.dataset.cr));
    assert.deepEqual(hidden, [], `view ${i} of ${name}: units left invisible`);
  }
  assert.deepEqual(page.errors, []);
  await page.close();
});
