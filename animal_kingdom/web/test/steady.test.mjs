// Numbers that change in place hold still (Martin, 2026-10-02): every value of a count takes the same width, so a count
// never shifts its neighbours or itself as it ticks. The turn clock, the food gem counting up (painted digits, one cell
// each), the rating counting after a ranked game; the search's count on Play again is held in rating.test.mjs.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, gamePage } from './harness.mjs';

let server, browser, page;
before(async () => { server = await startServer(); browser = await openBrowser(); page = await gamePage(browser, server.url, { still: false }); });
after(async () => { await browser?.close(); server?.stop(); });

const widths = (fn, arg) => page.evaluate(fn, arg).then(a => [...new Set(a.map(w => w.toFixed(2)))]);

test('the turn clock takes one width at every second, and the pips beside it stay put', async () => {
  const w = await widths(() => {
    const tb = document.getElementById('tbtn');
    tb.innerHTML = '<b>End turn</b><span class="pips"><i></i><i></i><span class="clock" id="clock"><b>0:00</b></span></span>';
    const b = tb.querySelector('#clock b'), pip = tb.querySelector('.pips i'), out = [];
    for (let s = 0; s < 240; s++) { b.textContent = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
      out.push(b.getBoundingClientRect().width * 1000 + pip.getBoundingClientRect().left); }
    return out;
  });
  assert.equal(w.length, 1, `clock widths ${w}`);
});

test('the food gem counts up in place: painted digits each take one cell, so every number of the same length is as wide', async () => {
  for (const [from, to] of [[0, 10], [10, 100]]) {
    const w = await widths(async ([from, to]) => {
      const { gemDigits } = await import('/static/board.js');
      await Promise.all([...Array(10).keys()].map(d => new Promise(r => { const i = new Image(); i.onload = i.onerror = r; i.src = `/static/kit2/gemnum/${d}.webp`; })));
      const gem = document.querySelector('.dcount'), out = [];
      for (let n = from; n < to; n++) { gem.innerHTML = gemDigits(n); out.push(gem.querySelector('.gemnum').getBoundingClientRect().width); }
      return out;
    }, [from, to]);
    assert.equal(w.length, 1, `gem widths ${from}–${to - 1}: ${w}`);
  }
});

test('the rating counts in place: every four-digit rating is as wide', async () => {
  const w = await widths(() => {
    const box = document.querySelector('.game').appendChild(document.createElement('div'));
    box.className = 'endbox'; box.innerHTML = '<div class="rating"><div><b>1500</b></div></div>';
    const b = box.querySelector('b'), out = [];
    for (let n = 1000; n < 2000; n++) { b.textContent = n; out.push(b.getBoundingClientRect().width); }
    box.remove(); return out;
  });
  assert.equal(w.length, 1, `rating widths ${w}`);
});
