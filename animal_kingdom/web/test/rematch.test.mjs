// A friend match's Rematch is an offer the other player accepts or declines (Martin, 2026-11-05, as on chess.com): the
// end panel shows who offered, the offered-to player gets Decline beside Rematch, and a declined offer leaves only Menu.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, gamePage } from './harness.mjs';

let server, browser, page;
before(async () => { server = await startServer(); browser = await openBrowser(); page = await gamePage(browser, server.url); });
after(async () => { await browser?.close(); server?.stop(); });
const wait = ms => new Promise(r => setTimeout(r, ms));

// the lab's view as a friend match just over (a concede), with `rematch` as the server sends it
const feedOver = (rematch, version) => page.evaluate(async (rematch, version) => {
  const v = await fetch('/static/lab/mid.json').then(r => r.json()), o = v.you === 'A' ? 'B' : 'A';
  v.version = version; v.phase = 'match_over'; v.results = [{ winner: v.you, reason: 'concede', turns: 5 }];
  v.score = { [v.you]: 1, [o]: 0 }; v.ranked = false;
  for (const p of ['A', 'B']) v.seats[p].bot = null;
  v.game.result = { winner: v.you, reason: 'concede' }; v.game.events = [];
  if (rematch) v.rematch = { offer: rematch.offer === 'you' ? v.you : rematch.offer === 'them' ? o : null,
                              declined: rematch.declined === 'them' ? o : rematch.declined === 'you' ? v.you : null };
  window.__ak.feed(v);
}, rematch, version);
const panel = () => page.evaluate(() => ({
  text: [...document.querySelectorAll('#endov .how')].map(e => e.textContent).join(' | '),
  buttons: [...document.querySelectorAll('#endov .btns button, #endov .btns a')].map(b => b.textContent),
}));

test('the end panel follows a friend\'s rematch offer', async () => {
  await feedOver(null, 200); await wait(400);
  assert.ok((await panel()).buttons.includes('Rematch'), 'no offer yet: Rematch');
  await feedOver({ offer: 'you' }, 201); await wait(200);
  let p = await panel();
  assert.match(p.text, /Rematch offered/); assert.ok(!p.buttons.includes('Rematch'), 'offered: waiting, no second Rematch');
  await feedOver({ offer: 'them' }, 202); await wait(200);
  p = await panel();
  assert.match(p.text, /Your opponent wants a rematch/); assert.deepEqual(p.buttons.slice(-2), ['Decline', 'Rematch']);
  await feedOver({ declined: 'them' }, 203); await wait(200);
  p = await panel();
  assert.match(p.text, /declined the rematch/); assert.ok(!p.buttons.includes('Rematch'));
  assert.deepEqual(page.errors, []);
});
