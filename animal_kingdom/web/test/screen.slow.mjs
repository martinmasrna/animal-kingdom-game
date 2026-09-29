// Every view of recorded bot-vs-bot matches, played through the client with animations off, must show exactly the
// game state: each unit visible at its crossroad in its owner's colour with its strength and buried count, nothing on
// empty crossroads, each den's gem at its food and each pit holding the right ripe and ghost fruit, both hands, the
// turn button, the end-of-game overlay, and no page errors.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, recordMatches, openBrowser, gamePage, feed, screenMismatches } from './harness.mjs';

let server, browser, matches;
before(async () => { server = await startServer(); browser = await openBrowser(); matches = recordMatches(7); });
after(async () => { await browser?.close(); server?.stop(); });

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
