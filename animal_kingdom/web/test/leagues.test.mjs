// Ranked leagues (docs/ranked-leagues.md): the ladder screen and home say your league and stars in text, the leaderboard
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
// a league as shown: "<emblem> <lit stars>/<stars> <any words>"
const lgSum = e => `${e.querySelector('.lgem')?.alt || ''} ${[...e.querySelectorAll('.pip')].filter(p => /\/star\.webp$/.test(p.src)).length}/${e.querySelectorAll('.pip').length}${e.textContent.trim() ? ' ' + e.textContent.trim() : ''}`;
const FIVE = { league: 5, name: 'League 5', top: false, streak: 3, best: 'League 5', stars: 2, of: 5 };
const TOP = { league: 10, name: 'League 10', top: true, streak: 0, best: 'League 10', rating: '2011' };

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

test('the ladder screen shows your emblem, its name and its stars; home\'s Ladder piece the emblem and stars', async () => {
  const p = await patched({ '/api/me': me => ({ ...me, league: FIVE, rank: 7 }) });
  await p.goto(`${server.url}/#/ladder`, { waitUntil: 'networkidle0' });
  await p.waitForSelector('#lstand');
  assert.equal(await p.evaluate(`(${lgSum})(document.querySelector('#lstand'))`), 'Silver 2/5 Silver');
  await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await p.waitForSelector('.backbtn.me .pips');
  assert.equal(await p.evaluate(`(${lgSum})(document.querySelector('.backbtn.me'))`), 'Silver 2/5 Ladder', 'home: the emblem and the pips, no words but the button\'s');
  assert.deepEqual(p.errors, []);
  await p.close();
});

test('in the top league the ladder screen shows the rating instead of stars', async () => {
  const p = await patched({ '/api/me': me => ({ ...me, league: TOP, rank: 2 }) });
  await p.goto(`${server.url}/#/ladder`, { waitUntil: 'networkidle0' });
  await p.waitForSelector('#lstand');
  assert.equal(await p.evaluate(`(${lgSum})(document.querySelector('#lstand'))`), 'Diamond 0/0 Diamond2011');
  await p.close();
});

test('the leaderboard shows no league: a person below the top no number, the top league its rating, bots unchanged', async () => {
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
  assert.deepEqual(rows[0], ['Laras#0001', '2213'], 'the top league: the rating as the number, no league mark');
  assert.deepEqual(rows[1], ['Fish (Legendary Bot)', '2175'], 'a bot as before');
  assert.deepEqual(rows[2], ['Martin#0002', ''], 'below the top: no league mark and no number');
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

test('a ranked game\'s end shows your emblem and its stars, words only for a bonus star, and no number below the top league', async () => {
  const pg = await gamePage(browser, server.url);
  await endRanked(pg, { rating: { before: '1512', after: '1530', delta: 18 },
    league: { ...FIVE, line: '+2 stars (win streak): League 5, 2 of 5 stars' } });
  await pg.waitForSelector('#lgline');
  assert.equal(await pg.evaluate(`(${lgSum})(document.querySelector('#lgline'))`), 'Silver 2/5 Win streak: bonus star');
  assert.equal(await pg.$('#rnum'), null, 'no rating below the top league');
  assert.equal(await pg.$$eval('#endov .lgend', e => e.length), 1, 'one emblem');
  assert.deepEqual(pg.errors, []);
  await pg.close();
});

test('in the top league the end shows the rating, and the emblem only on the game that brought you there', async () => {
  const pg = await gamePage(browser, server.url);
  await endRanked(pg, { rating: { before: '1990', after: '2004', delta: 14 }, league: { ...TOP, rating: '2004', line: 'League 10: rating 2004' } });
  await pg.waitForSelector('#rnum');
  assert.equal(await pg.$('#lgline'), null, 'the number says it: no line');
  assert.equal(await pg.$eval('#rnum', e => e.textContent), '2004');
  await pg.goto(pg.url().replace(/#.*/, '#/lab/mid'), { waitUntil: 'networkidle0' });
  await endRanked(pg, { rating: { before: '1890', after: '1904', delta: 14 }, league: { ...TOP, rating: '1904', line: 'Up to League 10' } });
  await pg.waitForSelector('#lgline');
  assert.equal(await pg.evaluate(`(${lgSum})(document.querySelector('#lgline'))`), 'Diamond 0/0 Diamond');
  assert.ok(await pg.$('#rnum'), 'and the number with it');
  await wait(100);
  assert.deepEqual(pg.errors, []);
  await pg.close();
});
