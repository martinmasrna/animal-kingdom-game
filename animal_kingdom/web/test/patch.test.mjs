// Patch notes (static/patch.js, static/patches/): every patch parses and names only real cards' shapes; a returning
// player sees the newest once, and Back leaves it for good.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { startServer, openBrowser } from './harness.mjs';

const dir = new URL('../static/patches/', import.meta.url);
const index = JSON.parse(readFileSync(new URL('index.json', dir)));

test('every patch in the index parses, and every card it shows has a figure on disk', () => {
  assert.ok(index.length >= 1);
  for (const v of index) {
    const P = JSON.parse(readFileSync(new URL(`${v}.json`, dir)));
    assert.equal(P.name, `Patch ${v}`);
    for (const c of [...P.changed.flatMap(p => [p.was, p.now]), ...P.added, ...P.removed])
      if (c.fig) assert.ok(existsSync(new URL(`../static/hex/fig/${c.id}.webp`, import.meta.url)), `${v}: ${c.id}'s figure`);
  }
});

test('a returning player gets the newest patch once, as a window; the Patch Notes button opens it again', async () => {
  const server = await startServer(), browser = await openBrowser();
  try {
    const p = await browser.newPage(); await p.setViewport({ width: 1512, height: 800 });
    await p.evaluateOnNewDocument(() => localStorage.setItem('ak:learned', '1'));
    await p.goto(server.url + '/', { waitUntil: 'networkidle0' }); await new Promise(r => setTimeout(r, 400));
    assert.equal(await p.$('#patchpop'), null, 'a new player (no deck) gets no window');
    await p.evaluate(() => fetch('/api/me/decks', { method: 'PUT', headers: { 'X-AK-Key': localStorage.getItem('ak:key'), 'Content-Type': 'application/json' },
      body: JSON.stringify([{ id: 'x', name: 'X', cards: { wisp_1: 2 }, leader: null }]) }));
    await p.goto(server.url + '/#/collection', { waitUntil: 'networkidle0' }); await p.reload({ waitUntil: 'networkidle0' });   // opened on any screen, not only home
    await p.waitForSelector('#patchpop .patch h1');
    assert.equal(await p.$eval('#patchpop h1', h => h.textContent), `Patch ${index[0]}`);
    await p.click('#patchpop .pclose');
    assert.equal(await p.$('#patchpop'), null, 'closed');
    await p.goto(server.url + '/', { waitUntil: 'networkidle0' }); await new Promise(r => setTimeout(r, 400));
    assert.equal(await p.$('#patchpop'), null, 'seen: it does not come back');
    await p.click('#mpatch'); await p.waitForSelector('#patchpop h1');
    await p.keyboard.press('Escape');
    assert.equal(await p.$('#patchpop'), null, 'Escape closes it');
  } finally { await browser.close(); server.stop(); }
});
