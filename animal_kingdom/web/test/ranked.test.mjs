// Ranked leagues end to end on a real server, nothing patched (docs/ranked-leagues.md): a ranked match against a bot played
// to its end (conceded: a loss), whose end says what it did to the stars; a ranked match between two people, whose winner's
// end says the stars gained; and the leaderboard listing a person with their league. leagues.test.mjs covers the screens'
// every shape on patched answers; this checks the server and the client agree.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });

// A page of its own (its own profile: a browser context keeps its own storage), home loaded so the profile exists.
async function player() {
  const ctx = await browser.createBrowserContext();
  const page = await ctx.newPage();
  await page.evaluateOnNewDocument(() => { try { localStorage.setItem('ak:learned', '1'); } catch { /* no storage */ } });
  page.errors = [];
  page.on('pageerror', e => page.errors.push(e.message));
  await page.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => !!localStorage.getItem('ak:key'));
  return page;
}

// Join the ranked queue as the client does (POST /api/ranked), then open the match.
const queue = page => page.evaluate(async () => {
  const r = await fetch('/api/ranked', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-AK-Key': localStorage.getItem('ak:key') }, body: JSON.stringify({ deck: 'cats' }) });
  return r.json();
});
const open = async (page, m) => {
  await page.evaluate(m => { sessionStorage.setItem('ak:seat:' + m.id, m.token); location.hash = '#/m/' + m.id; }, m);
  await page.waitForFunction(() => { const s = window.__ak && window.__ak(); return s && s.V && s.V.game; }, { timeout: 30000 });
};
const concede = async page => {
  await page.waitForFunction(() => window.__ak().V.phase === 'playing', { timeout: 30000 });
  await page.click('#menubtn'); await page.waitForSelector('#concov.on'); await page.click('#concede');
};
const endLine = page => page.waitForSelector('#lgline', { timeout: 30000 }).then(() => page.$eval('#lgline', e => e.textContent));

test('a ranked match against a bot, conceded: its end says your league and stars (nothing to lose at 0 stars in league 1), and shows no number', async () => {
  const p = await player();
  const m = await queue(p);   // nobody else queues: after the wait, the nearest bot
  assert.ok(m.id && m.token, 'a match');
  await open(p, m);
  assert.equal(await p.evaluate(() => window.__ak().V.seats[window.__ak().V.you].league), 'Wood 3', 'your seat states your league');
  await concede(p);
  assert.equal(await endLine(p), '');
  assert.equal(await p.$eval('#lgline .lgem', e => e.alt), 'Wood 3');
  assert.equal(await p.$('#rnum'), null, 'no rating below the top league');
  assert.deepEqual(p.errors, []);
  await p.close();
});

test('a ranked match between two people: the winner\'s end says the stars gained; the leaderboard lists them with their league', async () => {
  const a = await player(), b = await player();
  const [ma, mb] = await Promise.all([queue(a), queue(b)]);
  assert.equal(ma.id, mb.id, 'two people queueing at once meet');
  await Promise.all([open(a, ma), open(b, mb)]);
  await concede(b);
  assert.equal(await endLine(a), '');
  assert.equal(await a.$$eval('#lgline .lgpips s.on', e => e.length), 1, 'the win shows as a pip');
  assert.equal(await endLine(b), '');
  await a.goto(`${server.url}/#/ladder`, { waitUntil: 'networkidle0' });
  // the ladder draws at once from the profile it holds, then again from the fresh one (app.js route), and the list fills
  // after each draw: wait for the fresh draw and its list before reading
  await a.waitForFunction(() => document.querySelector('#lstand .lgpips s.on') && document.querySelector('#lboard .lr.you b .lgem'), { timeout: 15000 });
  assert.equal(await a.$eval('#lboard .lr.you b .lgem', e => e.alt), 'Wood 3', 'your row: your emblem in the number\'s place');
  assert.equal(await a.$eval('#lstand', e => e.textContent), 'Wood');
  assert.equal(await a.$$eval('#lstand .lgpips s.on', e => e.length), 1, 'one win of five');
  assert.ok(await a.$$eval('#lboard .lr.bot b', els => els.length > 0 && els.every(e => /^\d+\??$/.test(e.textContent))), 'bots keep their numbers');
  assert.deepEqual([...a.errors, ...b.errors], []);
  await a.close(); await b.close();
});
