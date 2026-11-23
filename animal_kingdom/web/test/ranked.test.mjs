// Ranked in the browser (static/ranked.js), on the square board staging plays: home's Play ranked puts you straight into
// a rated match against a bot with the deck shown; its end says what it did to your league and offers the next match, not
// a rematch; home and the leaderboard say where you stand. First on a real server with nothing patched, so the server and
// the client agree; then every shape the server can send (a division's wins, a promotion, the top league), put into the
// real answers. The server's side is tested in animal_kingdom/tests/test_ladder.py, test_tiers.py and test_pool.py.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { startServer, openBrowser } from './harness.mjs';
const NEWEST = JSON.parse(readFileSync(new URL('../static/patches/index.json', import.meta.url)))[0];

let server, browser;
before(async () => { server = await startServer({ AK_MAP: 'map_sq16' }); browser = await openBrowser(); });
after(async () => { await browser?.close(); server?.stop(); });

const wait = ms => new Promise(r => setTimeout(r, ms));
const WISPS = Object.fromEntries([1, 2, 3, 4, 5, 6].map(i => ['wisp_' + i, 2]));
const deck = (id, name, leader) => ({ id, name, leader, cards: { ...WISPS, flight_1: 2, flight_2: 2, flight_3: 2, flight_5: 2, spikes_3: 2, cantrip_2: 2, [leader]: 1 } });
const FIVE = { league: 5, name: 'Silver', label: 'Silver 2', colour: '#c9d0d8', emblem: 'silver_2', top: false, streak: 3, best: 'Silver', division: 2, stars: 2, of: 5 };
const TOP = { league: 11, name: 'Legend', label: 'Legend', colour: '#f4f1e8', top: true, streak: 0, best: 'Legend', rating: '2011' };

// A page with a profile of its own and `decks` on it. `patch`: path -> a function over the JSON the real server answers a GET with.
async function player(decks, { patch = {}, phone = false } = {}) {
  const ctx = await browser.createBrowserContext(), p = await ctx.newPage();
  p.errors = [];
  p.on('pageerror', e => p.errors.push(e.message));
  if (phone) await p.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await p.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  if (Object.keys(patch).length) {
    await p.setRequestInterception(true);
    p.on('request', async req => {
      const path = new URL(req.url()).pathname;
      if (!patch[path] || req.method() !== 'GET') return req.continue();
      const r = await fetch(req.url(), { headers: req.headers() });
      req.respond({ status: r.status, contentType: 'application/json', body: JSON.stringify(patch[path](await r.json())) });
    });
  }
  await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await p.evaluate(async (decks, seen) => { const h = { 'X-AK-Key': localStorage.getItem('ak:key'), 'Content-Type': 'application/json' };
    await fetch('/api/me/decks', { method: 'PUT', headers: h, body: JSON.stringify(decks) });
    await fetch('/api/me/patch', { method: 'POST', headers: h, body: JSON.stringify({ version: seen }) }); }, decks, NEWEST);   // the patch notes seen: they don't open over the test
  await p.reload({ waitUntil: 'networkidle0' });
  return p;
}
const view = p => p.evaluate(() => { const a = window.__ak && window.__ak(); return a && a.V; });
const inMatch = p => p.waitForFunction(() => { const a = window.__ak && window.__ak(); return a && a.V && a.V.game && a.V.phase === 'playing'; }, { timeout: 30000 });
const concede = p => p.evaluate(() => { document.getElementById('concov').classList.add('on'); document.getElementById('concede').click(); });
const fits = p => p.evaluate(() => document.scrollingElement.scrollWidth <= innerWidth && [...document.querySelectorAll('.rkrow .nm, .rkdeck > span')].every(e => e.scrollWidth <= e.clientWidth));

test('Play ranked: straight into a rated match against a bot, its end says your league and offers the next match, home and the leaderboard say where you stand', async () => {
  const p = await player([deck('a', 'Sage deck', 'sage_legend'), deck('b', 'Warlord deck', 'warlord_legend')]);
  // home: the button, the deck it plays, your league (no place before a rated game); the other three ways in under it
  assert.deepEqual(await p.$$eval('.mmenu .go', els => els.map(e => e.textContent)), ['Play ranked', 'Play', 'Practice', 'Collection']);
  assert.equal(await p.$eval('#rkdeck > span', e => e.textContent), 'Sage deck');
  assert.equal(await p.$eval('#rkstand .lgem', e => e.naturalWidth > 0 && e.alt), 'Wood 3', 'the league\'s emblem, loaded');
  assert.deepEqual(await p.$eval('#rkstand', e => [e.querySelector('b').textContent, e.querySelectorAll('.lgpips s').length, e.querySelectorAll('.lgpips s.on').length, !!e.querySelector('.rkplace')]), ['Wood 3', 5, 0, false]);
  // another deck: the deck line opens your legal decks in its place, a click takes one
  await p.click('#rkdeck'); await p.click('[data-rkdeck="my:b"]');
  assert.equal(await p.$eval('#rkdeck > span', e => e.textContent), 'Warlord deck');
  // one click: the match, rated, against a bot named by its band, with that deck
  await p.click('#rkgo'); await inMatch(p);
  let V = await view(p);
  const first = V.id;
  assert.ok(V.ranked && V.seats.B.bot && / Bot\)$/.test(V.seats.B.name), 'a bot from the ladder');
  assert.equal(V.seats.A.deckName, 'Warlord deck');
  // conceded, a loss: the end shows your league (nothing to lose at no wins in the bottom league), no number below the
  // top league, and Play again in a rematch's place
  await concede(p); await p.waitForSelector('#rkend', { timeout: 30000 });
  assert.deepEqual(await p.$eval('#rkend', e => [e.querySelector('.lgem').alt, e.querySelector('b').textContent, e.querySelectorAll('.lgpips s.on').length]), ['Wood 3', 'Wood 3', 0]);
  assert.deepEqual([await p.$('#rnum'), await p.$('#rematch')], [null, null]);
  assert.deepEqual(await p.$$eval('#endov .btns > *', els => els.map(e => e.textContent)), ['Menu', 'See the board', 'Play again']);
  // Play again: another match, against another deck than the one just met
  const met = V.seats.B.deck;
  await p.click('#again');
  await p.waitForFunction(id => { const a = window.__ak(); return a.V && a.V.id !== id && a.V.phase === 'playing'; }, { timeout: 30000 }, first);
  V = await view(p);
  assert.ok(V.ranked && V.seats.B.deck !== met, 'the next bot plays another deck');
  await concede(p); await p.waitForSelector('#rkend', { timeout: 30000 });
  // home again: your place among the bots, from the fresh profile; the leaderboard marks your row, and lists every bot
  // with its deck's leader and its rating, best first
  await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await p.waitForSelector('#rkstand .rkplace');
  const place = await p.$eval('#rkstand .rkplace', e => e.textContent);
  await p.click('#rkstand'); await p.waitForSelector('.rkrow.you');
  assert.equal('#' + await p.$eval('.rkrow.you .n', e => e.textContent), place, 'home\'s place is your row\'s');
  assert.equal(await p.$eval('.rkrow.you b .lgem', e => e.alt), 'Wood 3', 'your row: your emblem in the number\'s place');
  const bots = await p.$$eval('.rkrow.bot', els => els.map(e => [e.querySelector('.nm').textContent, +e.querySelector('b').textContent, !!e.querySelector('.pc .tokpiece')]));
  assert.ok(bots.length >= 5 && bots.every(([name, rating, piece]) => / Bot\)$/.test(name) && rating > 0 && piece));
  assert.deepEqual(bots.map(b => b[1]), bots.map(b => b[1]).sort((a, b) => b - a));
  assert.deepEqual(p.errors, []);
  await p.close();
});

test('with no legal deck Play ranked says to build one; on an upright phone home and the leaderboard fit the width', async () => {
  const none = await player([], { phone: true });
  assert.ok(await none.$('#rkgo.off') && await none.$('a.rkdeck.none[href="#/collection"]'));
  await none.click('#rkgo'); await wait(200);
  assert.match(await none.$eval('#toast', e => e.textContent), /Build a legal deck/);
  assert.ok(await fits(none), 'home, no deck');
  await none.close();
  const p = await player([deck('a', 'A deck with quite a long name of its own', 'sage_legend'), deck('b', 'Warlord deck', 'warlord_legend'), deck('c', 'Raid', 'raider_legend')], { phone: true });
  assert.equal(await p.evaluate(() => document.scrollingElement.scrollWidth <= innerWidth), true, 'home');
  await p.click('#rkdeck');
  assert.equal(await p.$$eval('[data-rkdeck]', e => e.length), 3);
  await p.click('[data-rkdeck="my:c"]');
  await p.goto(`${server.url}/#/ladder`, { waitUntil: 'networkidle0' }); await p.waitForSelector('.rkrow');
  assert.ok(await fits(p), 'the leaderboard: no row runs off the screen and no name is cut');
  assert.deepEqual(p.errors, []);
  await p.close();
});

test('the leaderboard: a person\'s league in the number\'s place, the top league its number, a bot its rating; your standing above it', async () => {
  const p = await player([deck('a', 'Sage deck', 'sage_legend')], { patch: {
    '/api/me': me => ({ ...me, league: FIVE, rank: 3 }),
    '/api/leaderboard': j => ({ rows: [
      { name: 'Laras#0001', rating: '2213', league: TOP, bot: false, you: false },
      j.rows.find(r => r.bot),
      { name: 'Martin#0002', rating: null, league: FIVE, bot: false, you: true },
      ...j.rows.filter(r => r.bot).slice(1, 4)] }) } });
  assert.equal(await p.$eval('#rkstand .rkplace', e => e.textContent), '#3', 'home: your place');
  await p.goto(`${server.url}/#/ladder`, { waitUntil: 'networkidle0' }); await p.waitForSelector('.rkrow');
  assert.deepEqual(await p.$eval('.rkstand.mine', e => [e.querySelector('.lgem').alt, e.querySelector('b').textContent, e.querySelectorAll('.lgpips s.on').length, e.querySelector('.rkstreak').textContent]),
    ['Silver 2', 'Silver 2', 2, '3 wins in a row']);
  const rows = await p.$$eval('.rkrow', els => els.map(e => [e.querySelector('.nm').textContent, e.querySelector('b').textContent]));
  assert.deepEqual(rows[0], ['Laras#0001', '2213'], 'the top league: the rating');
  assert.match(rows[1].join(' '), / Bot\) \d+$/, 'a bot: its rating');
  assert.deepEqual(rows[2], ['Martin#0002', ''], 'below the top: the emblem and the wins, no number');
  assert.deepEqual(await p.$eval('.rkrow.you b', e => [e.querySelector('.lgem').alt, e.querySelectorAll('.lgpips s.on').length]), ['Silver 2', 2]);
  assert.deepEqual(p.errors, []);
  await p.close();
});

test('a ranked game\'s end: the wins in your division, what moved you in the name\'s place, and in the top league the rating', async () => {
  const p = await player([deck('a', 'Sage deck', 'sage_legend')]);
  await p.click('#rkgo'); await inMatch(p); await concede(p); await p.waitForSelector('#rkend', { timeout: 30000 });
  // the real finished view, with the server's other shapes put in (tiers.Change.line, tiers.view)
  const end = (league, rating) => p.evaluate((league, rating) => { const a = window.__ak(), v = JSON.parse(JSON.stringify(a.V));
    Object.assign(v, { league, rating, version: v.version + 1 }); v.game.result.winner = v.result.winner = v.you; v.game.result.reason = 'food'; window.__ak.feed(v); }, league, rating);
  const shown = () => p.$eval('#endov', e => [e.querySelector('#rkend .lgem')?.alt ?? null, e.querySelector('#rkend b').textContent, e.querySelectorAll('#rkend .lgpips s.on').length, e.querySelector('#rnum')?.textContent ?? null]);
  await end({ ...FIVE, line: '' }, { before: '1432', after: '1447', delta: 15 });
  assert.deepEqual(await shown(), ['Silver 2', 'Silver 2', 2, null], 'a win inside a division: the league and its wins, no number');
  await end({ ...FIVE, stars: 4, line: 'Win streak: +2' }, { before: '1432', after: '1447', delta: 15 });
  assert.deepEqual(await shown(), ['Silver 2', 'Win streak: +2', 4, null]);
  await end({ ...FIVE, label: 'Gold 3', emblem: 'gold_3', stars: 1, line: 'Up to Gold 3' }, { before: '1499', after: '1512', delta: 13 });
  assert.deepEqual(await shown(), ['Gold 3', 'Up to Gold 3', 1, null]);
  await end({ ...TOP, rating: '1904', line: 'Up to Legend' }, { before: '1890', after: '1904', delta: 14 });
  assert.deepEqual(await shown(), [null, 'Up to Legend', 0, '1904'], 'the game that brought you to the top league says so, with the number');
  await end({ ...TOP, line: 'Legend: rating 2011' }, { before: '1998', after: '2011', delta: 13 });
  assert.deepEqual(await shown(), [null, 'Legend', 0, '2011'], 'in the top league: its name and the rating');
  assert.equal(await p.$eval('#endov .rd', e => e.textContent), '+13');
  assert.deepEqual(p.errors, []);
  await p.close();
});
