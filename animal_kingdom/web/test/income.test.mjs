// A region's income flies as fruit from its stone to the den: recorded bot matches fed through the client, every flight's
// fruit checked to start on the board, at a stone (a comment that swallowed the stones' positions sent it all from the
// window's corner, off screen; Martin, 2026-10-02).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, recordMatches, gamePage, feed } from './harness.mjs';

let server, browser, matches;
before(async () => { matches = recordMatches(1); server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });
const wait = ms => new Promise(r => setTimeout(r, ms));

test('income fruit leaves from the region stones, on the board', async () => {
  const page = await gamePage(browser, server.url, { still: false });
  await page.evaluate(() => { window.__fly = []; const board = document.getElementById('board');
    new MutationObserver(() => { for (const f of board.querySelectorAll('.flyfruit')) window.__fly.push([parseFloat(f.style.left), parseFloat(f.style.top)]); })
      .observe(board, { childList: true }); });
  const views = matches[0].views;
  for (const v of views.slice(0, 30)) { await feed(page, v); await wait(400); }
  await wait(3000);
  const fly = await page.evaluate(() => window.__fly);
  assert.ok(fly.length > 0, 'some income flew');
  for (const [x, y] of fly) assert.ok(Number.isFinite(x) && Number.isFinite(y) && x > 150 && x < 1360 && y > 60 && y < 740, `a fruit starts at (${x}, ${y}), off the board`);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test("a held region's stone shows what it pays its holder (the legendary Wildebeest and Boar move it)", async () => {
  const page = await gamePage(browser, server.url);
  const stones = () => page.evaluate(() => [...document.querySelectorAll('#board .stone.pboss')]
    .map(s => ({ held: s.classList.contains('A') || s.classList.contains('B'), text: [...s.querySelectorAll('img')].map(i => i.alt).join('') })));
  let held = null;
  for (const v of matches[0].views) {
    await feed(page, v);
    if ((await stones()).some(s => s.held)) { held = v; break; }
  }
  assert.ok(held, 'some view has a held region');
  const pays = Object.fromEntries(Object.keys(held.game.regionFood.A).map(id => [id, 37]));
  await feed(page, { ...held, version: held.version + 1, game: { ...held.game, events: [], regionFood: { A: pays, B: pays } } });
  await wait(300);
  const now = await stones();
  assert.ok(now.filter(s => s.held).every(s => s.text === '+37'), JSON.stringify(now));
  assert.ok(now.filter(s => !s.held).every(s => s.text !== '+37'), 'a stone no one holds shows the printed food');
  assert.deepEqual(page.errors, []);
  await page.close();
});
