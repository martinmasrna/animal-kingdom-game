// Ranked leagues (docs/ranked-leagues.md): the ladder screen and home say your league and stage, with a pip per win, the leaderboard
// says each person's league (the number only in the top league; bots as before), and a ranked game's end says what it did
// to your stars in one line. The server's side is tested in animal_kingdom/tests/test_tiers.py and test_ladder.py; here
// the server's answers are the real ones with a league put in, so the client is tested on the shapes the server sends.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser, gamePage } from './harness.mjs';

let server, browser, page;
before(async () => { server = await startServer(); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });

const wait = ms => new Promise(r => setTimeout(r, ms));
const FIVE = { league: 5, name: 'Silver', label: 'Silver 2', colour: '#c9d0d8', top: false, streak: 3, best: 'Silver', stage: 2, stages: 3, stars: 2, of: 5 };
const TOP = { league: 11, name: 'Legend', label: 'Legend', colour: '#f4f1e8', top: true, streak: 0, best: 'Legend', rating: '2011' };

// The page's own requests, answered by the real server, with `patch` applied to the JSON of the ones it names.
async function patched(patch) {
  const p = await browser.newPage();
  p.errors = [];
  p.on('pageerror', e => p.errors.push(e.message));
  await p.setRequestInterception(true);
  p.on('request', async req => {
    const path = new URL(req.url()).pathname;
    if (!patch[path] || req.method() !== 'GET') return req.continue();
    const r = await fetch(req.url(), { headers: req.headers() });
    req.respond({ status: r.status, contentType: 'application/json', body: JSON.stringify(patch[path](await r.json())) });
  });
  return p;
}

test('the ladder screen says your league, stars and streak; home\'s Ladder piece your league and place', async () => {
  const p = await patched({ '/api/me': me => ({ ...me, league: FIVE, rank: 7 }) });
  await p.goto(`${server.url}/#/ladder`, { waitUntil: 'networkidle0' });
  await p.waitForSelector('#lstand');
  assert.equal(await p.$eval('#lstand', e => e.textContent), 'Silver 2 · 3 wins in a row');
  assert.deepEqual(await p.$eval('#lstand', e => [e.querySelectorAll('.lgdisc s').length, e.querySelectorAll('.lgpips s').length, e.querySelectorAll('.lgpips s.on').length]), [2, 5, 2], 'a dot per stage, a pip per win');
  await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await p.waitForSelector('.backbtn.me small');
  assert.equal(await p.$eval('.backbtn.me small', e => e.textContent), 'Silver 2 · #7');
  assert.deepEqual(p.errors, []);
  await p.close();
});

test('in the top league the ladder screen shows the rating instead of stars', async () => {
  const p = await patched({ '/api/me': me => ({ ...me, league: TOP, rank: 2 }) });
  await p.goto(`${server.url}/#/ladder`, { waitUntil: 'networkidle0' });
  await p.waitForSelector('#lstand');
  assert.equal(await p.$eval('#lstand', e => e.textContent), 'Legend · 2011');
  await p.close();
});

test('the leaderboard: a person\'s league in the number\'s place and their stars by the name; the top league its number; bots unchanged', async () => {
  const p = await patched({
    '/api/me': me => ({ ...me, league: FIVE, rank: 2 }),
    '/api/leaderboard': j => ({ ...j, rows: [
      { name: 'Laras#0001', rating: '2213', league: TOP, bot: false, you: false },
      { name: 'Fish (Legendary Bot)', rating: '2175', bot: true, you: false, deck: 'fish' },
      { name: 'Martin#0002', rating: null, league: FIVE, bot: false, you: true },
      ...j.rows.filter(r => r.bot).slice(1, 4)] }),
  });
  await p.goto(`${server.url}/#/ladder`, { waitUntil: 'networkidle0' });
  await p.waitForSelector('#lboard .lr');
  const rows = await p.$$eval('#lboard .lr', els => els.map(e => [e.querySelector('.nm').textContent, e.querySelector('b').textContent]));
  assert.deepEqual(rows[0], ['Laras#0001Legend', '2213'], 'the top league: its name by the person, the rating as the number');
  assert.deepEqual(rows[1], ['Fish (Legendary Bot)', '2175'], 'a bot as before');
  assert.deepEqual(rows[2], ['Martin#0002', 'Silver 2'], 'below the top: the league and stage, no number');
  assert.ok(rows.slice(3).every(([, n]) => /^\d+\??$/.test(n)), 'the other bots keep their numbers');
  assert.deepEqual(p.errors, []);
  await p.close();
});

// A ranked game ending, fed to the lab page as the server would send it.
const endRanked = (pg, extra) => pg.evaluate(async extra => {
  const v = await fetch('/static/lab/mid.json').then(r => r.json()), o = v.you === 'A' ? 'B' : 'A';
  v.version += 50; v.phase = 'match_over'; v.results = [{ winner: v.you }]; v.score = { [v.you]: 1, [o]: 0 };
  v.game.result = { winner: v.you, reason: 'food' }; v.ranked = true; Object.assign(v, extra); window.__ak.feed(v);
}, extra);

test('a ranked game\'s end says in one line what it did to your stars, and shows no number below the top league', async () => {
  const pg = await gamePage(browser, server.url);
  await endRanked(pg, { rating: { before: '1512', after: '1530', delta: 18 },
    league: { ...FIVE, line: 'Silver 2, win streak: +2' } });
  await pg.waitForSelector('#lgline');
  assert.equal(await pg.$eval('#lgline', e => e.textContent), 'Silver 2, win streak: +2');
  assert.equal(await pg.$('#rnum'), null, 'no rating below the top league');
  assert.equal(await pg.$$eval('#endov .lgline', e => e.length), 1, 'one line');
  assert.deepEqual(pg.errors, []);
  await pg.close();
});

test('in the top league the end shows the rating, and the line only on the game that brought you there', async () => {
  const pg = await gamePage(browser, server.url);
  await endRanked(pg, { rating: { before: '1990', after: '2004', delta: 14 }, league: { ...TOP, rating: '2004', line: 'Legend: rating 2004' } });
  await pg.waitForSelector('#rnum');
  assert.equal(await pg.$('#lgline'), null, 'the number says it: no line');
  assert.equal(await pg.$eval('#rnum', e => e.textContent), '2004');
  await pg.goto(pg.url().replace(/#.*/, '#/lab/mid'), { waitUntil: 'networkidle0' });
  await endRanked(pg, { rating: { before: '1890', after: '1904', delta: 14 }, league: { ...TOP, rating: '1904', line: 'Up to Legend' } });
  await pg.waitForSelector('#lgline');
  assert.equal(await pg.$eval('#lgline', e => e.textContent), 'Up to Legend');
  assert.ok(await pg.$('#rnum'), 'and the number with it');
  await wait(100);
  assert.deepEqual(pg.errors, []);
  await pg.close();
});
