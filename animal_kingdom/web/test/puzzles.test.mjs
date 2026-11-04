// Every shipped puzzle (animal_kingdom/data/puzzles) played through the client by clicks: its main line, the solver's moves
// clicked and the defender's played by the server's search, ends Solved. A puzzle whose line no longer clicks through (a
// card changed, a screen that no longer offers a move) fails here.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { startServer, openBrowser } from './harness.mjs';
import { playLine, waitMine } from './puzzleplay.mjs';

const DIR = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'data', 'puzzles');
const PUZZLES = readdirSync(DIR).filter(f => f.endsWith('.json')).sort().map(f => JSON.parse(readFileSync(join(DIR, f))));

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });

for (const pz of PUZZLES) {
  test(`${pz.id}: its solution clicked through to Solved`, async () => {
    const page = await browser.newPage();
    page.errors = []; page.on('pageerror', e => page.errors.push(e.message));
    await page.goto(`${server.url}/#/puzzle/${pz.id}`, { waitUntil: 'networkidle0' });
    await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
    await waitMine(page);
    const v = await page.evaluate(() => window.__ak().V);
    assert.equal(v.puzzle.id, pz.id);
    assert.deepEqual(v.game.revealedHand.map(h => h.id), pz.hands.B.map(c => typeof c === 'string' ? c : c.card), 'the defender\'s hand face up');
    await playLine(page, pz.main_line);
    await page.waitForFunction(() => document.querySelector('#endov.on .res')?.textContent === 'Solved', { timeout: 15000 });
    assert.deepEqual(page.errors, []);
    await page.close();
  });
}
