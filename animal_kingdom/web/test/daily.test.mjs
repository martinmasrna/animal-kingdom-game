// Daily matches (docs/async-play.md; daily.js, web/server.py /api/daily): take your turn when you visit. Two people, each
// in their own browser profile. A daily challenge goes from home's Friend choice to a friend who is away, waits on their
// home, and starts when they press Play; each then takes a turn while the other is away, and is sent home once their turn
// is done. Both in the match at once, it plays as a live match. A turn not taken in time loses, and says so on home.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, quick, browser;
const wait = ms => new Promise(r => setTimeout(r, ms));
const person = async url => {   // a browser profile of its own: its own local storage, so its own player
  const ctx = await browser.createBrowserContext(), p = await ctx.newPage();
  await p.evaluateOnNewDocument(() => { try { localStorage.setItem('ak:learned', '1'); } catch { /* none */ } });
  p.errors = []; p.on('pageerror', e => p.errors.push(e.message));
  await p.goto(`${url}/#/`, { waitUntil: 'networkidle0' });
  await p.waitForFunction(() => localStorage.getItem('ak:key'));
  p.home = url; p.key = await p.evaluate(() => localStorage.getItem('ak:key'));
  return p;
};
const call = (p, url, body, method) => fetch(p.home + url, { method: method || (body ? 'POST' : 'GET'),   // from here, as that player
  headers: { 'Content-Type': 'application/json', 'X-AK-Key': p.key }, body: body && JSON.stringify(body) }).then(r => r.json());
const friends = async (a, b) => { const { code } = await call(a, '/api/friends'); await call(b, '/api/friends', { code });
  await a.reload({ waitUntil: 'networkidle0' }); await b.reload({ waitUntil: 'networkidle0' }); };
const until = (p, fn, what, timeout = 8000, ...args) => p.waitForFunction(fn, { timeout, polling: 50 }, ...args).catch(() => assert.fail(what));
const dailyText = p => p.evaluate(() => (document.getElementById('daily') || {}).textContent || '');
const away = p => p.goto('about:blank');
const back = p => p.goto(`${p.home}/#/`, { waitUntil: 'networkidle0' });

// Take whatever this seat must do in the open match, by clicks, until it is no longer theirs: keep the opening hand, draw
// once, end the turn, answer a choice with its first option.
async function takeTurn(p) {
  await until(p, () => window.__ak().V && window.__ak().V.daily, 'the match opened');
  for (let i = 0; i < 80; i++) {
    const done = await p.evaluate(() => {
      const V = window.__ak().V; if (!V || !V.daily) return location.hash === '#/';
      if (!V.daily.yours) return true;
      const g = V.game, $ = s => document.querySelector(s);
      if (g.decision === 'mulligan' && $('#skip')) $('#skip').click();
      else if (g.decision === 'yours' && g.actionsLeft === g.actionsTotal && $('#deck.can')) $('#deck').click();
      else if (g.decision === 'yours' && $('#tbtn.can')) $('#tbtn').click();
      else if (g.decision === 'your_choice') { const o = $('#opts [data-v], #skip, .hc'); if (o) o.click(); }
      return false;
    });
    if (done) return;
    await wait(250);
  }
  assert.fail('the turn never ended');
}
const openTurn = async p => {   // home's "Your turn" row opens the match
  await until(p, () => !!document.querySelector('#daily .drow.turn'), 'home shows your turn');
  await p.click('#daily .drow.turn');
  await until(p, () => /^#\/m\//.test(location.hash) && window.__ak().V && window.__ak().V.daily, 'the match opened');
};

before(async () => {
  [server, quick] = await Promise.all([startServer(), startServer({ AK_DAILY_DAYS: String(10 / 86400), AK_DAILY_SWEEP: '0.5' })]);
  browser = await openBrowser();
});
after(async () => { await browser.close(); server.stop(); quick.stop(); });

test('a daily challenge reaches a friend who is away, and each takes a turn while the other is away', async () => {
  const ann = await person(server.url), bob = await person(server.url);
  await friends(ann, bob);
  await away(bob);
  // Ann: Friend, her friend, Daily, then the challenge
  await ann.click('#oppbtn'); await ann.waitForSelector('[data-opp="friend"]'); await ann.click('[data-opp="friend"]');
  await ann.waitForSelector('[data-friend]'); await ann.click('[data-friend]');
  await ann.click('[data-pace="daily"]');
  assert.match(await ann.$eval('#go', e => e.textContent), /Daily challenge to/);
  await ann.click('#go');
  await until(ann, () => /Challenge sent/.test((document.getElementById('daily') || {}).textContent || ''), 'the challenge shows as sent');
  // Bob comes back: the challenge waits on his home; Play starts the match with his chosen deck
  await back(bob);
  await until(bob, () => /sends a daily challenge/.test((document.getElementById('daily') || {}).textContent || ''), 'the challenge waits on his home');
  await bob.click('#daily [data-accept]');
  await until(bob, () => /^#\/m\//.test(location.hash) && window.__ak().V && window.__ak().V.daily, 'Play opens the match');
  const id = await bob.evaluate(() => window.__ak().V.id);
  await takeTurn(bob);
  await until(bob, () => location.hash === '#/', 'his mulligan done and Ann away, he is sent home');
  assert.match(await dailyText(bob), /'s turn/);
  // turns in alternation, each while the other is away, until both have played a turn of the game
  const moved = new Set();
  for (let k = 0; k < 6 && moved.size < 2; k++) {
    const [p, q] = (await call(ann, '/api/daily')).turn.length ? [ann, bob] : [bob, ann];
    await away(q); await back(p);
    await openTurn(p);
    const seat = await p.evaluate(() => window.__ak().V.you), mulligan = await p.evaluate(() => window.__ak().V.game.decision === 'mulligan');
    await takeTurn(p);
    await until(p, () => location.hash === '#/', 'the turn done and the friend away: home');
    assert.match(await dailyText(p), /'s turn/, 'home says it is the friend\'s turn now');
    if (!mulligan) moved.add(seat);
  }
  assert.equal(moved.size, 2, 'each took a turn of the game');
  const hist = (await call(ann, '/api/daily')).turn.concat((await call(ann, '/api/daily')).waiting);
  assert.equal(hist.length, 1); assert.equal(hist[0].id, id);
  assert.deepEqual([...ann.errors, ...bob.errors], []);
});

test('both in the match at once it plays live: nobody is sent home after a turn', async () => {
  const ann = await person(server.url), bob = await person(server.url);
  await friends(ann, bob);
  const ch = await call(ann, '/api/daily', { friend: (await call(ann, '/api/friends')).friends[0].id, deck: 'cats' });
  const acc = await call(bob, `/api/daily/${ch.id}/answer`, { accept: true, deck: 'giants' });
  for (const [p, m] of [[ann, ch], [bob, acc]]) {
    await p.evaluate(m => sessionStorage.setItem('ak:seat:' + m.id, m.token), m);
    await p.goto(`${server.url}/#/m/${m.id}`);
    await until(p, () => window.__ak().V && window.__ak().V.daily, 'the match opened');
  }
  for (const p of [ann, bob]) await until(p, () => window.__ak().V.daily.oppHere, 'each sees the other in the match');
  await Promise.all([takeTurn(ann), takeTurn(bob)]);   // both mulligans, at once
  await wait(1500);
  for (const p of [ann, bob]) assert.match(await p.evaluate(() => location.hash), /^#\/m\//, 'still in the match');
  assert.deepEqual([...ann.errors, ...bob.errors], []);
});

test('a turn not taken in time loses the match, and home says so until the match is opened', async () => {
  const ann = await person(quick.url), bob = await person(quick.url);   // a server whose daily clock is 10 seconds
  await friends(ann, bob);
  const ch = await call(ann, '/api/daily', { friend: (await call(ann, '/api/friends')).friends[0].id, deck: 'cats' });
  await call(bob, `/api/daily/${ch.id}/answer`, { accept: true, deck: 'giants' });
  await back(bob);
  await openTurn(bob);
  await takeTurn(bob);                                  // Bob keeps his hand; Ann never does
  await until(bob, () => location.hash === '#/', 'Bob is home');
  await until(bob, () => /Won.*out of time/.test((document.getElementById('daily') || {}).textContent || ''), 'Bob\'s home: won, on time', 15000);
  await back(ann);
  await until(ann, () => /Lost.*out of time/.test((document.getElementById('daily') || {}).textContent || ''), 'Ann\'s home: lost, out of time');
  await ann.click('#daily .drow.done');
  await until(ann, () => /You ran out of time/.test((document.getElementById('endov') || {}).textContent || ''), 'the match ends on her timeout');
  await back(ann);
  await wait(500);
  assert.doesNotMatch(await dailyText(ann), /Lost/, 'opened once, the result leaves home');
  const hist = await call(ann, '/api/me');
  assert.ok((hist.history || hist.profile?.history || []).some(h => h.mode === 'daily'), 'in the match history, as daily');
  assert.deepEqual([...ann.errors, ...bob.errors], []);
});

test('daily ranked: the next person who chooses it is your opponent, and home says so', async () => {
  const ann = await person(server.url), bob = await person(server.url);   // strangers: the queue needs no friendship
  const queue = async p => {
    await p.click('#oppbtn'); await p.waitForSelector('[data-opp="ranked"]'); await p.click('[data-opp="ranked"]');
    await p.click('[data-pace="daily"]');
    assert.equal(await p.$eval('#go', e => e.textContent), 'Find a daily opponent');
    await p.click('#go');
  };
  await queue(ann);
  await until(ann, () => /Looking for a daily opponent/.test((document.getElementById('daily') || {}).textContent || ''), 'Ann waits in the queue');
  await away(ann);
  await queue(bob);
  await until(bob, () => /Your turn.*Ranked/.test((document.getElementById('daily') || {}).textContent || ''), 'Bob is paired at once');
  await back(ann);
  await until(ann, () => /Your turn.*Ranked/.test((document.getElementById('daily') || {}).textContent || ''), 'and Ann finds the match on home');
  assert.deepEqual([...ann.errors, ...bob.errors], []);
});
