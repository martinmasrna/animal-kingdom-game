// Ranked in the browser (static/ranked.js), on the square board staging plays: home's Ranked opens the ranked screen
// (your league, the deck you bring, Play); Play shows the versus moment over the match as it opens; the match ends on
// its own two screens, the verdict and then your rank, and Continue leads back to the ranked screen. First on a real
// server with nothing patched, so the server and the client agree; then the endings the server can send (wins landing,
// a division, a league, Legend, a draw), played by the real module. The server's side is tested in
// animal_kingdom/tests/test_ladder.py, test_tiers.py and test_pool.py.
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
const deck = (id, name, leader, more = {}) => ({ id, name, leader, cards: { ...WISPS, flight_1: 2, flight_3: 2, flight_6: 2, spikes_1: 2, spikes_3: 2, cantrip_2: 2, [leader]: 1, ...more } });
const lg = (league, name, colour, division, stars, streak = 0) => ({ league, name, label: `${name} ${division}`, colour, top: false, streak, best: name, division, stars, of: 5 });
const top = rating => ({ league: 11, name: 'Legend', label: 'Legend', colour: '#f4f1e8', top: true, streak: 0, best: 'Legend', rating });

// A page with a profile of its own and `decks` on it.
async function player(decks, { phone = false } = {}) {
  const ctx = await browser.createBrowserContext(), p = await ctx.newPage();
  p.errors = [];
  p.on('pageerror', e => p.errors.push(e.message));
  if (phone) await p.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
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
const stand = (p, root = '.rkscreen') => p.$eval(`${root} .rkstand`, e => ({ name: e.querySelector('h1').textContent, mark: e.querySelector('.rkmark b').textContent,
  wins: e.querySelectorAll('.rkwins i').length, won: e.querySelectorAll('.rkwins i.on').length, ghosts: e.querySelectorAll('.rkwins i.ghost').length, delta: (e.querySelector('.rkdelta') || {}).textContent ?? null }));
// The words on the screen: ranked says what it can with signs, so the list of words is short and each one is meant.
const words = (p, root) => p.$eval(root, e => e.innerText.split('\n').map(s => s.trim()).filter(Boolean));

test('Ranked: home\'s door, the ranked screen, versus, a match, its two-screen ending, and back', async () => {
  const p = await player([deck('a', 'Control', 'sage_legend'), deck('b', 'Wisps and the Warlord', 'warlord_legend'), deck('c', 'Short', 'raider_legend', { cantrip_2: 1 })]);
  assert.deepEqual(await p.$$eval('.mmenu .go', els => els.map(e => e.textContent)), ['Ranked', 'Play', 'Practice', 'Collection'], 'home: one door to ranked');
  await p.click('#mranked'); await p.waitForSelector('#rkgo');
  assert.deepEqual(await stand(p), { name: 'Wood 3', mark: '3', wins: 5, won: 0, ghosts: 0, delta: null }, 'everyone starts in Wood 3 with nothing won');
  assert.deepEqual(await words(p, '.rkfoot'), ['Control', 'Play'], 'the deck you bring by its name, and Play: no other word');
  assert.ok(await p.$('.rkfoot .rkdeck .tokpiece img') && await p.$('.rkfoot .rkdeck .rkic'), 'the deck\'s leader, and the sign that it opens');
  // your decks: the one that plays marked, one short of cards dimmed with its count and not to be chosen
  await p.click('#rkdeck');
  assert.deepEqual(await p.$$eval('.rkrows .rkdeck', els => els.map(e => [e.querySelector('b').textContent, e.classList.contains('on'), e.disabled, (e.querySelector('small') || {}).textContent || ''])),
    [['Control', true, false, ''], ['Wisps and the Warlord', false, false, ''], ['Short', false, true, '24/25']]);
  await p.click('[data-deck="my:b"]'); await p.waitForFunction(() => document.querySelector('.rkfoot .rkdeck b').textContent === 'Wisps and the Warlord');
  assert.ok(await p.$eval('#rksheet', e => e.hidden), 'choosing closes the sheet');
  // Play: the versus moment over the match as it opens, each player one card; a bot is called by its band, never by its deck
  await p.click('#rkgo'); await p.waitForSelector('#rkvs');
  const cards = await p.$$eval('#rkvs .rkcard', els => els.map(e => ({ who: e.classList.contains('you') ? 'you' : 'them', name: e.querySelector('.pname').textContent, fig: !!e.querySelector('img'), mark: e.querySelector('.rkmark b').textContent })));
  assert.equal(cards.length, 2); assert.ok(cards.every(c => c.fig && /^[123]$/.test(c.mark)), 'each card: its leader\'s picture and its league\'s mark');
  assert.deepEqual(cards.find(c => c.who === 'you').name, 'Player'); assert.match(cards.find(c => c.who === 'them').name, /^\w+ Bot$/);
  await inMatch(p);
  const V = await view(p);
  assert.ok(V.ranked && V.seats.B.bot && V.seats.B.name === cards.find(c => c.who === 'them').name, 'a rated match against that bot');
  await p.waitForFunction(() => !document.getElementById('rkvs'), { timeout: 6000 });   // it lifts by itself
  // the ending: the verdict (your card and the word, nothing else, nothing to press), then your rank and Continue
  await concede(p); await p.waitForSelector('.rkverdict');
  assert.deepEqual(await words(p, '#rkfin'), ['Defeat'], 'your leader\'s picture and the word: no name, and no rank before its own screen');
  assert.ok(await p.$('.rkverdict .rkcard img') && !(await p.$('.rkverdict .rkmark')));
  assert.equal(await p.$('#rkfin button'), null, 'the verdict has nothing to press');
  assert.equal(await p.$eval('#endov', e => e.classList.contains('on')), false, 'the match\'s own end box stays away');
  await p.waitForSelector('#rkrank', { timeout: 6000 });
  assert.deepEqual(await words(p, '#rkfin'), ['3', 'Wood 3', 'Continue']);
  assert.deepEqual(await stand(p, '#rkrank'), { name: 'Wood 3', mark: '3', wins: 5, won: 0, ghosts: 0, delta: null }, 'a loss with nothing won loses nothing');
  await p.click('#rkcont'); await p.waitForSelector('#rkgo');
  assert.equal(await p.evaluate(() => location.hash), '#/ranked', 'Continue leads to the ranked screen');
  assert.equal(await p.$('#rkfin'), null);
  assert.deepEqual(p.errors, []);
  await p.browserContext().close();
});

test('with no legal deck the deck\'s place asks for one and Play is out; on an upright phone every ranked screen fits', async () => {
  const none = await player([], { phone: true });
  await none.goto(`${server.url}/#/ranked`, { waitUntil: 'networkidle0' }); await none.waitForSelector('#rkgo');
  assert.ok(await none.$('a.rkdeck.none[href="#/collection"] .rkic') && await none.$eval('#rkgo', e => e.disabled));
  const fits = () => none.evaluate(() => document.scrollingElement.scrollWidth <= innerWidth && [...document.querySelectorAll('.rkscreen > *, #rkvs .rkcard, #rkfin .rkcard, #rkfin .rkstand, #rkfin .rkplay')].every(e => { const r = e.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth && r.top >= 0 && r.bottom <= innerHeight; }));
  assert.ok(await fits(), 'the ranked screen');
  await none.close();
  const p = await player([deck('a', 'Control', 'sage_legend')], { phone: true });
  await p.goto(`${server.url}/#/ranked`, { waitUntil: 'networkidle0' }); await p.waitForSelector('#rkgo');
  assert.ok(await p.$eval('#rkdeck', e => e.disabled) && !(await p.$('.rkfoot .rkdeck .rkic')), 'one deck: nothing opens');
  const fit = () => p.evaluate(() => document.scrollingElement.scrollWidth <= innerWidth && [...document.querySelectorAll('.rkscreen > *, #rkvs .rkcard, #rkfin .rkcard, #rkfin .rkstand, #rkfin .rkplay')].every(e => { const r = e.getBoundingClientRect(); return r.left >= -1 && r.right <= innerWidth + 1 && r.top >= -1 && r.bottom <= innerHeight + 1; }));
  assert.ok(await fit(), 'the ranked screen with a deck');
  await p.tap('#rkgo'); await p.waitForSelector('#rkvs'); await wait(300);
  assert.ok(await fit(), 'versus');
  await inMatch(p); await p.waitForFunction(() => !document.getElementById('rkvs'), { timeout: 6000 });
  await concede(p); await p.waitForSelector('.rkverdict'); assert.ok(await fit(), 'the verdict');
  await p.waitForSelector('#rkrank', { timeout: 6000 }); assert.ok(await fit(), 'your rank');
  assert.deepEqual(p.errors, []);
  await p.browserContext().close();
});

test('what a match did lands on your rank: wins, a streak\'s two, a division, a league, the rating in Legend; a draw ends on the verdict', async () => {
  const p = await player([deck('a', 'Control', 'sage_legend')]);
  await p.goto(`${server.url}/#/ranked`, { waitUntil: 'networkidle0' }); await p.waitForSelector('#rkgo');
  await p.click('#rkgo'); await inMatch(p); await concede(p); await p.waitForSelector('#rkrank', { timeout: 8000 });
  // an ending played by the real module on the real view, with the standing before and after as the server sends them
  const play = (word, before, after, rating) => p.evaluate(async (word, before, after, rating) => { const m = await import('/static/ranked.js'), a = window.__ak(), v = JSON.parse(JSON.stringify(a.V));
    document.getElementById('rkfin')?.remove(); v.id = 'T' + Math.random(); v.game.result.winner = word === 'Draw' ? null : word === 'Victory' ? v.you : (v.you === 'A' ? 'B' : 'A');
    v.league = after && { ...after, before }; v.rating = rating; window.__done = 0; m.finale(v, true, { cards: a.CARDS, done: () => { window.__done++; } }); }, word, before, after, rating);
  const silver = (...a) => lg(5, 'Silver', '#c9d0d8', ...a);
  // a win on a streak: the verdict first, then two wins land, and the next two wait
  await play('Victory', silver(2, 1, 2), silver(2, 3, 3));
  assert.deepEqual(await words(p, '#rkfin'), ['Victory']);
  await p.waitForSelector('#rkrank');
  assert.deepEqual(await stand(p, '#rkrank'), { name: 'Silver 2', mark: '2', wins: 5, won: 1, ghosts: 2, delta: null }, 'it opens on the standing going in');
  await p.waitForFunction(() => document.querySelectorAll('#rkrank .rkwins i.on').length === 3, { timeout: 5000 });
  await wait(1200); assert.deepEqual(await stand(p, '#rkrank'), { name: 'Silver 2', mark: '2', wins: 5, won: 3, ghosts: 2, delta: null });
  // a press on the verdict brings the rank at once; a division up turns the mark
  await play('Victory', silver(2, 4), silver(1, 0, 1));
  await p.click('.rkverdict'); await p.waitForSelector('#rkrank');
  await p.waitForFunction(() => document.querySelector('#rkrank h1').textContent === 'Silver 1', { timeout: 5000 });
  assert.deepEqual(await stand(p, '#rkrank'), { name: 'Silver 1', mark: '1', wins: 5, won: 0, ghosts: 0, delta: null });
  assert.equal(await p.$('#rkrank.took'), null, 'a division is not a league');
  // a league up: the screen becomes the new league's
  await play('Victory', silver(1, 4), lg(6, 'Gold', '#e2b23a', 3, 0, 1));
  await p.click('.rkverdict'); await p.waitForSelector('#rkrank.took', { timeout: 5000 });
  assert.deepEqual(await stand(p, '#rkrank'), { name: 'Gold 3', mark: '3', wins: 5, won: 0, ghosts: 0, delta: null });
  // a loss: one win leaves
  await play('Defeat', silver(2, 3), silver(2, 2));
  await p.click('.rkverdict'); await p.waitForFunction(() => document.querySelector('#rkrank') && document.querySelectorAll('#rkrank .rkwins i.on').length === 2, { timeout: 5000 });
  // Legend: the mark holds the rating, and what the match did to it stands under the name; no place, no wins
  await play('Victory', top('2043'), top('2056'), { before: '2043', after: '2056', delta: 13 });
  await p.click('.rkverdict'); await p.waitForFunction(() => (document.querySelector('#rkrank .rkdelta') || {}).textContent === '+13', { timeout: 5000 });
  assert.deepEqual(await stand(p, '#rkrank'), { name: 'Legend', mark: '2056', wins: 0, won: 0, ghosts: 0, delta: '+13' });
  assert.deepEqual(await words(p, '#rkfin'), ['2056', 'Legend', '+13', 'Continue']);
  // a draw moves nothing: the verdict is the last screen and carries Continue
  await play('Draw', null, null, null);
  assert.deepEqual(await words(p, '#rkfin'), ['Draw', 'Continue']);
  await p.click('#rkcont'); assert.equal(await p.evaluate(() => window.__done), 1); assert.equal(await p.$('#rkfin'), null);
  assert.deepEqual(p.errors, []);
  await p.browserContext().close();
});

test('the leaderboard: every league along the top, yours chosen and marked; a league\'s players under it, you outlined; on a phone too', async () => {
  for (const phone of [false, true]) {
    const p = await player([deck('a', 'Control', 'sage_legend')], { phone });
    await p.goto(`${server.url}/#/ranked`, { waitUntil: 'networkidle0' }); await p.waitForSelector('#rkboard');
    await p.click('#rkboard'); await p.waitForSelector('.rkrow');
    const strip = () => p.$$eval('.rklgb', els => els.map(e => [e.getAttribute('aria-label'), e.classList.contains('on'), e.classList.contains('mine')]));
    const rows = () => p.$$eval('.rkrow', els => els.map(e => ({ n: e.querySelector('.n').textContent, name: e.querySelector('.nm').textContent, you: e.classList.contains('you'),
      wins: e.querySelectorAll('.mini i').length, won: e.querySelectorAll('.mini i.on').length, mark: (e.querySelector('.rkmark b') || {}).textContent ?? null })));
    assert.deepEqual((await strip()).map(s => s[0]), ['Wood', 'Bone', 'Stone', 'Copper', 'Silver', 'Gold', 'Jade', 'Sapphire', 'Ruby', 'Diamond', 'Legend']);
    assert.deepEqual((await strip()).filter(s => s[1] || s[2]), [['Wood', true, true]], 'it opens on your own league');
    assert.equal(await p.$eval('#rklg', e => e.textContent), 'Wood');
    // you are on it from the start, before any rated game (the other rows are other tests' players on this server)
    const wood = await rows(), mine = wood.filter(r => r.you);
    assert.equal(mine.length, 1); assert.deepEqual([mine[0].name, mine[0].wins, mine[0].won, mine[0].mark], ['Player', 5, 0, '3']);
    assert.deepEqual(wood.map(r => r.n), wood.map((_, i) => String(i + 1)), 'places count from 1');
    assert.ok((await words(p, '.rklb')).every(w => /^(Wood|Player|\d+)$/.test(w)), 'a league\'s name, and a row\'s place, name and division: no other word');
    // another league: the bots stand in the league their rating falls in, called by their band; your mark stays on your own
    const board = await p.evaluate(async () => (await (await fetch('/api/leaderboard', { headers: { 'X-AK-Key': localStorage.getItem('ak:key') } })).json()));
    const bot = board.rows.find(r => r.bot), there = board.rows.filter(r => r.league.league === bot.league.league);
    await p.click(`[data-league="${bot.league.league}"]`); await p.waitForFunction(n => document.getElementById('rklg').textContent === n, {}, bot.league.name);
    assert.deepEqual((await rows()).map(r => [r.n, r.name, r.you]), there.map((r, i) => [String(i + 1), r.name, false]));
    assert.ok((await rows()).every(r => / Bot$/.test(r.name)));
    assert.deepEqual((await strip()).filter(s => s[1] || s[2]).map(s => [s[1], s[2]]).sort(), [[false, true], [true, false]].sort());
    await p.click('[data-league="11"]'); await p.waitForFunction(() => document.getElementById('rklg').textContent === 'Legend');
    assert.deepEqual(await rows(), [], 'nobody in Legend yet');
    assert.equal(await p.$eval('.rklist', e => getComputedStyle(e).backgroundImage + getComputedStyle(e).backgroundColor), 'nonergba(0, 0, 0, 0)', 'the list has no panel of its own behind it');
    assert.ok(await p.evaluate(() => document.scrollingElement.scrollWidth <= innerWidth && [...document.querySelectorAll('.rkback, #rklg, .rklist')].every(e => { const r = e.getBoundingClientRect(); return r.left >= 0 && r.right <= innerWidth; })), 'it fits the width');
    if (phone) assert.ok(await p.$eval('.rkstrip', s => { const on = s.querySelector('.on').getBoundingClientRect(); return s.scrollWidth > s.clientWidth && on.left >= 0 && on.right <= innerWidth; }), 'on a phone the row scrolls and the chosen league is in sight');
    await p.click('.rklb .rkback'); await p.waitForSelector('#rkgo');
    assert.deepEqual(p.errors, []);
    await p.browserContext().close();
  }
});
