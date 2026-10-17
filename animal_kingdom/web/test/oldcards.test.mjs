// A replay from before a card changed names cards the game no longer has: it must still play, a retired id as its
// successor and a card gone for good as a stand-in, never stopping the screen; and the collection never offers them.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, recordMatches, openBrowser, gamePage, feed, screenMismatches } from './harness.mjs';

let server, browser, views;
before(async () => { server = await startServer(); browser = await openBrowser(); views = recordMatches(1)[0].views; });
after(async () => { await browser?.close(); server?.stop(); });

test('an old replay naming retired and deleted cards plays without errors', async () => {
  const at = views.findIndex(v => v.game && Object.keys(v.game.board).length >= 2 && v.game.hand.length);
  const old = JSON.parse(JSON.stringify(views.slice(at, at + 3)));
  for (const v of old) {
    const [a, b] = Object.values(v.game.board);
    a[a.length - 1].id = 'stoop';                 // the old Hawk's id: its successor is the Hawk
    b[b.length - 1].id = 'raksha';                // a legendary deleted outright
    v.game.hand[0].id = 'house_cat';              // retired, its effect now the Alley Cat's
  }
  const page = await gamePage(browser, server.url);
  await page.evaluate(v => window.__ak.adopt(v), old);
  for (const v of old) { await feed(page, v); assert.deepEqual(await page.evaluate(screenMismatches), []); }
  assert.deepEqual(page.errors, []);
  const names = await page.evaluate(() => ['stoop', 'raksha', 'house_cat'].map(id => [window.__ak.cards()[id].name, window.__ak.cards()[id].deck]));
  assert.deepEqual(names, [['Hawk', 'reserve'], ['Raksha', 'reserve'], ['Alley Cat', 'reserve']]);
  await page.close();
});
