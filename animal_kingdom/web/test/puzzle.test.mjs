// Puzzles through the client: #/puzzles lists them, #/puzzle/<id> opens one on the game screen with the defender's hand face
// up and the brief where a card's question stands; following the solution by clicks solves it, a move that lets the den go
// fails it at once, and Try again starts it over. The server runs on two fixture puzzles (AK_PUZZLE_DIR).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { startServer, openBrowser } from './harness.mjs';
import { playLine, waitMine } from './puzzleplay.mjs';

const LION = { card: 'lion', owner: 'A' };
const ONE = { id: 'p_one', title: 'One step', theme: 'Covering', to_move: 'A', turns: 1,
  board: { '1,2': [LION], '2,2': [LION], '3,2': [LION], '4,2': [LION], '5,2': [{ card: 'hamster', owner: 'B' }] },
  hands: { A: ['lion', 'lion'], B: ['tortoise'] }, food: { A: 0, B: 0 }, hint: 'Cover first.', why: 'test',
  solution: [{ kind: 'place', card_id: 'lion', target: ['cr', '5,2'] }, { kind: 'place', card_id: 'lion', target: ['hq', 'B'] }] };
const TWO = { ...ONE, id: 'p_two', title: 'Two steps', turns: 2, board: { '1,2': [LION], '2,2': [LION] },
  hands: { A: ['lion', 'lion', 'lion', 'lion'], B: ['pup', 'pup'] } };

let server, browser;
before(async () => {
  const dir = mkdtempSync(join(tmpdir(), 'ak-puzzles-'));
  for (const p of [ONE, TWO]) writeFileSync(join(dir, `${p.id}.json`), JSON.stringify(p));
  server = await startServer({ AK_PUZZLE_DIR: dir }); browser = await openBrowser();
});
after(async () => { await browser?.close(); server?.stop(); });

async function open(id) {
  const page = await browser.newPage();
  page.errors = []; page.on('pageerror', e => page.errors.push(e.message));
  await page.goto(`${server.url}/#/puzzles`, { waitUntil: 'networkidle0' });
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.waitForSelector(`[data-puzzle="${id}"]`);
  await page.click(`[data-puzzle="${id}"]`);
  await waitMine(page);
  return page;
}

test('the list shows each puzzle with its theme and turns', async () => {
  const page = await browser.newPage();
  await page.goto(`${server.url}/#/puzzles`, { waitUntil: 'networkidle0' });
  await page.waitForSelector('[data-puzzle="p_one"]');
  const rows = await page.$$eval('[data-puzzle]', els => els.map(e => e.textContent.trim()));
  assert.deepEqual(rows, ['One step Covering · 1 turn', 'Two steps Covering · 2 turns']);
  await page.close();
});

test('a puzzle followed to its solution is solved, and the list remembers it', async () => {
  const page = await open('p_one');
  const g = await page.evaluate(() => window.__ak().V);
  assert.deepEqual(g.game.revealedHand.map(h => h.id), ['tortoise'], 'the defender\'s hand is in the view');
  assert.equal(await page.$$eval('#opphand .oc', els => els.length), 1, 'and face up on the screen');
  assert.match(await page.$eval('#choicebar', e => e.textContent), /Take the den this turn\./);
  await page.click('#hintbtn');
  assert.match(await page.$eval('#choicebar', e => e.textContent), /Cover first\./);
  await playLine(page, ONE.solution);
  await page.waitForFunction(() => document.querySelector('#endov.on .res')?.textContent === 'Solved', { timeout: 10000 });
  await page.goto(`${server.url}/#/puzzles`, { waitUntil: 'networkidle0' });
  await page.waitForSelector('[data-puzzle="p_one"]');
  assert.match(await page.$eval('[data-puzzle="p_one"]', e => e.textContent), /Solved/);
  assert.deepEqual(page.errors, []);
  await page.close();
});

test('a move that lets the den go fails it at once, and Try again starts it over', async () => {
  const page = await open('p_two');
  assert.match(await page.$eval('#choicebar', e => e.textContent), /Take the den in 2 turns\.2 turns left\./);
  await playLine(page, [{ kind: 'place', card_id: 'lion', target: ['cr', '2,1'] }]);   // three actions left, four needed
  await page.waitForFunction(() => document.querySelector('#endov.on .res')?.textContent === 'Not solved', { timeout: 10000 });
  await page.click('#again');
  await waitMine(page);
  const v = await page.evaluate(() => window.__ak().V);
  assert.equal(v.phase, 'playing'); assert.deepEqual(Object.keys(v.game.board).sort(), ['1,2', '2,2']);
  assert.equal(v.game.hand.length, 4);
  assert.deepEqual(page.errors, []);
  await page.close();
});
