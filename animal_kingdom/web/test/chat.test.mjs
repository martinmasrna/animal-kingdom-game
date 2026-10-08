// Chat between friends (chat.js, web/chat.py; design sandbox ladder/chat/greybox.html, Martin 2026-10-04): two people,
// each in their own browser profile. A message reaches a friend on home as a piece under the corner and a count on the
// Friends button; the piece opens the conversation, which reads it. In a match the piece stands beside the icon row,
// over nothing that matters, and its bell mutes messages there: they only count, and the choice is remembered.
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { startServer, openBrowser } from './harness.mjs';

let server, browser, ann, bob;
const wait = ms => new Promise(r => setTimeout(r, ms));
const person = async () => {   // a browser profile of its own: its own local storage, so its own player
  const ctx = await browser.createBrowserContext(), p = await ctx.newPage();
  await p.evaluateOnNewDocument(() => { try { localStorage.setItem('ak:learned', '1'); } catch { /* none */ } });
  p.errors = []; p.on('pageerror', e => p.errors.push(e.message));
  await p.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await p.waitForFunction(() => localStorage.getItem('ak:key'));
  return p;
};
const call = (p, url, body) => p.evaluate(async (url, body) => {
  const r = await fetch(url, { method: body ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json', 'X-AK-Key': localStorage.getItem('ak:key') }, body: body && JSON.stringify(body) });
  return r.json();
}, url, body);
const count = p => p.evaluate(() => { const b = [...document.querySelectorAll('.chatbtn .cbadge')].find(e => e.offsetParent); return b && !b.hidden ? +b.textContent : 0; });
const say = async (p, text) => { await p.type('#chatin', text); await p.keyboard.press('Enter'); };

before(async () => {
  server = await startServer(); browser = await openBrowser();
  ann = await person(); bob = await person();
  const { code } = await call(ann, '/api/friends');
  await call(bob, '/api/friends', { code });   // friends, both ways
  await ann.reload({ waitUntil: 'networkidle0' }); await bob.reload({ waitUntil: 'networkidle0' });
});
after(async () => { await browser.close(); server.stop(); });

test('a message reaches a friend on home: a piece under the corner, a count, and the piece opens the conversation', async () => {
  await ann.click('#hchat');
  await ann.waitForSelector('#chatp [data-with]');
  await ann.click('#chatp [data-with]');
  await ann.waitForSelector('#chatin');
  await say(ann, 'want a game tonight?');
  await ann.waitForFunction(() => [...document.querySelectorAll('#chatp .msg.me')].some(m => m.textContent === 'want a game tonight?'));
  await bob.waitForSelector('#chatt.on', { timeout: 4000 });
  assert.match(await bob.$eval('#chatt', e => e.textContent), /want a game tonight\?/);
  const [t, top] = await bob.evaluate(() => [document.getElementById('chatt').getBoundingClientRect().toJSON(), document.querySelector('.home .top').getBoundingClientRect().toJSON()]);
  assert.ok(t.top >= top.bottom && Math.abs(t.right - top.right) < 1.5, 'under the corner piece, flush with its right edge');
  assert.equal(await count(bob), 1);
  await bob.click('#chatt');
  await bob.waitForFunction(() => [...document.querySelectorAll('#chatp .msg:not(.me)')].some(m => m.textContent === 'want a game tonight?'));
  await bob.waitForFunction(() => document.querySelector('#hchat .cbadge').hidden, { timeout: 3000 });   // read
  await bob.type('#chatin', 'yes! after dinner'); await bob.click('#chatgo');   // the send button, as Enter
  await ann.waitForFunction(() => [...document.querySelectorAll('#chatp .msg:not(.me)')].some(m => m.textContent === 'yes! after dinner'), { timeout: 4000 });
  assert.equal(await count(ann), 0, 'a message into the open conversation is read at once');
  await bob.keyboard.press('Escape');
  assert.equal(await bob.$('#chatp'), null, 'Escape closes the panel');
  await ann.mouse.click(200, 300);
  assert.equal(await ann.$('#chatp'), null, 'a press off the panel closes it');
  assert.deepEqual([...ann.errors, ...bob.errors], []);
});

test('a message waits for a friend who is away, counted when they come back', async () => {
  const bobId = (await call(ann, '/api/friends')).friends[0].id;
  await bob.goto('about:blank');   // Bob leaves
  await call(ann, `/api/chat/${bobId}`, { text: 'you around?' });
  await bob.goto(`${server.url}/#/`, { waitUntil: 'networkidle0' });
  await bob.waitForFunction(() => +document.querySelector('#hchat .cbadge').textContent === 1 && !document.querySelector('#hchat .cbadge').hidden, { timeout: 4000 });
  await bob.click('#hchat');
  await bob.waitForFunction(() => /you around\?/.test(document.querySelector('#chatp [data-with] small').textContent) && document.querySelector('#chatp .cfr .n'));
  await bob.keyboard.press('Escape');
});

test('in a match the piece stands beside the icon row, and its bell mutes messages there (they only count)', async () => {
  const m = await call(bob, '/api/match', { deck: 'cats', name: 'You', bot: { level: 'easy', deck: 'giants' } });
  await bob.evaluate(m => sessionStorage.setItem('ak:seat:' + m.id, m.token), m);
  await bob.goto(`${server.url}/#/m/${m.id}`, { waitUntil: 'networkidle0' });
  await bob.waitForFunction(() => window.__ak().V && window.__ak().V.phase === 'playing', { timeout: 8000 });
  await bob.waitForFunction(() => document.getElementById('chatbtn').offsetParent, { timeout: 4000 });   // you have a friend: the button shows
  const bobId = (await call(ann, '/api/friends')).friends[0].id, before = await count(bob);
  await call(ann, `/api/chat/${bobId}`, { text: 'gl!' });
  await bob.waitForSelector('#chatt.on .mute', { timeout: 4000 });
  const clear = await bob.evaluate(() => {   // beside the icons, over neither hand nor either den's gem
    const t = document.getElementById('chatt').getBoundingClientRect(), hit = el => { const r = el.getBoundingClientRect(); return r.width && !(r.right <= t.left || r.left >= t.right || r.bottom <= t.top || r.top >= t.bottom); };
    return { beside: t.right <= document.getElementById('chatbtn').getBoundingClientRect().left,
      over: ['#opphand .oc, #opphand .back', '#board .dcount', '#hand .hc'].flatMap(s => [...document.querySelectorAll(s)]).filter(hit).map(e => e.className) }; });
  assert.ok(clear.beside, 'left of the Friends button'); assert.deepEqual(clear.over, [], 'over nothing in play');
  assert.equal(await count(bob), before + 1);
  await bob.click('#chatt .mute');
  assert.equal(await bob.evaluate(() => localStorage.getItem('ak:chatmute')), '1');
  await wait(300);
  await call(ann, `/api/chat/${bobId}`, { text: 'still there?' });
  await bob.waitForFunction(n => +document.querySelector('#chatbtn .cbadge').textContent === n, { timeout: 4000 }, before + 2);
  assert.ok(!(await bob.$eval('#chatt', e => e.classList.contains('on'))), 'muted: nothing slides in');
  await bob.click('#chatbtn'); await bob.waitForSelector('#chatp [data-with]'); await bob.click('#chatp [data-with]');
  await bob.waitForSelector('#chatp .msg');   // the conversation has loaded (the header drew before it)
  assert.equal(await bob.$('#chatchal'), null, 'no Challenge in a match');
  await bob.click('#chatmute');
  assert.equal(await bob.evaluate(() => localStorage.getItem('ak:chatmute')), '0', 'the bell in the header unmutes');
  assert.deepEqual([...ann.errors, ...bob.errors], []);
});
