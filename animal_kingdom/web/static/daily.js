// Daily matches on home (docs/async-play.md; web/server.py /api/daily): take your turn when you visit. One granite piece
// of plain text rows, shown only when there is something in it: the matches where it is your turn (least time left first),
// challenges to you (Play takes home's chosen deck), the matches waiting on your friend, challenges you sent, and results
// you haven't opened yet. A turn passing or a challenge arriving reaches every open tab on the presence socket ('daily').
// The look is a stand-in in the menus' text style: where the list sits against the key art, how many rows before it
// scrolls, and whether a count belongs on the corner piece are for a design (the doc's "Where a design belongs").
import { onPresence } from './friends.js';

const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
let ctx = null;   // { api, toast, deck(), open(id, token), changed() }
const S = { data: null, rx: 0 };

export function initDaily(c) {
  ctx = c;
  onPresence(m => { if (m.t === 'daily') loadDaily().then(() => ctx.changed()); });
}

export async function loadDaily() {
  const r = await ctx.api('/api/daily').catch(() => null);
  if (!r || !r.ok) return S.data;
  S.data = await r.json(); S.rx = Date.now() / 1000;
  return S.data;
}
export const dailyData = () => S.data;

// Time left, in words a player reads at a glance: "1 day 4 h", "5 h", "40 min".
export function timeLeft(deadline, now = Date.now() / 1000) {
  const s = Math.max(0, deadline - now), d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.ceil(s % 3600 / 60);
  return d ? `${d} day${d > 1 ? 's' : ''}${h ? ` ${h} h` : ''}` : h ? `${h} h` : `${Math.max(1, m)} min`;
}
const now = () => S.data ? S.data.now + (Date.now() / 1000 - S.rx) : Date.now() / 1000;
const why = r => r.reason === 'timeout' ? ' · out of time' : r.reason === 'concede' ? ' · conceded' : '';

export function dailyPiece() {
  const d = S.data;
  if (!d) return '';
  const rows = [
    ...d.turn.map(r => `<button class="drow turn" data-open="${r.id}"><b>Your turn</b><span>${r.ranked ? 'Ranked · ' : ''}${esc(r.opp)} · ${timeLeft(r.deadline, now())} left</span></button>`),
    ...d.challenges.map(c => `<div class="drow ask"><b>${esc(c.from)} sends a daily challenge</b><span class="btns"><button class="slab" data-decline="${c.id}">Decline</button><button class="slab" data-accept="${c.id}">Play</button></span></div>`),
    ...d.results.map(r => `<button class="drow done" data-open="${r.id}"><b>${r.draw ? 'Draw' : r.won ? 'Won' : 'Lost'}</b><span>${r.won ? 'against' : r.draw ? 'with' : 'to'} ${esc(r.opp)}${why(r)}</span></button>`),
    ...d.waiting.map(r => `<button class="drow wait" data-open="${r.id}"><b>${esc(r.opp)}'s turn</b><span>${r.ranked ? 'Ranked · ' : ''}${timeLeft(r.deadline, now())} left</span></button>`),
    ...(d.queue || []).map(c => `<div class="drow sent"><b>Looking for a daily opponent</b><span>ranked · a bot in ${timeLeft(c.until, now())} if nobody comes</span><span class="btns"><button class="slab" data-withdraw="${c.id}">Leave</button></span></div>`),
    ...d.sent.map(c => `<div class="drow sent"><b>Challenge sent</b><span>to ${esc(c.to)}</span><span class="btns"><button class="slab" data-withdraw="${c.id}">Withdraw</button></span></div>`),
  ];
  return rows.length ? `<div class="daily" id="daily"><h4>Daily</h4>${rows.join('')}</div>` : '';
}

export function wireDaily(root) {
  const el = root.querySelector('#daily');
  if (!el) return;
  const all = () => [...S.data.turn, ...S.data.waiting, ...S.data.results];
  el.querySelectorAll('[data-open]').forEach(b => b.onclick = e => { e.stopPropagation();
    const r = all().find(x => x.id === b.dataset.open); if (r) ctx.open(r.id, r.token); });
  el.querySelectorAll('[data-accept]').forEach(b => b.onclick = async e => { e.stopPropagation();
    const deck = ctx.deck(); if (!deck) return ctx.toast('Choose a deck first');
    const r = await ctx.api(`/api/daily/${b.dataset.accept}/answer`, { method: 'POST', body: JSON.stringify({ accept: true, deck }) });
    if (!r.ok) { ctx.toast(await r.text()); await loadDaily(); return ctx.changed(); }
    const m = await r.json(); ctx.open(m.id, m.token); });
  el.querySelectorAll('[data-decline]').forEach(b => b.onclick = async e => { e.stopPropagation();
    await ctx.api(`/api/daily/${b.dataset.decline}/answer`, { method: 'POST', body: JSON.stringify({ accept: false }) });
    await loadDaily(); ctx.changed(); });
  el.querySelectorAll('[data-withdraw]').forEach(b => b.onclick = async e => { e.stopPropagation();
    await ctx.api(`/api/daily/${b.dataset.withdraw}`, { method: 'DELETE' });
    await loadDaily(); ctx.changed(); });
}

// A daily challenge to a friend, online or not: it waits on their home.
export async function sendDaily(friend, deck, who) {
  const r = await ctx.api('/api/daily', { method: 'POST', body: JSON.stringify({ friend, deck }) });
  if (!r.ok) return ctx.toast(await r.text());
  ctx.toast(`Daily challenge sent to ${who}`, true);
  await loadDaily(); ctx.changed();
}

// The daily ranked queue: paired with the next person who joins it, else with a bot at your rating after a day.
export async function dailyRanked(deck) {
  const r = await ctx.api('/api/daily/ranked', { method: 'POST', body: JSON.stringify({ deck }) });
  if (!r.ok) return ctx.toast(await r.text());
  const m = await r.json();
  ctx.toast(m.paired ? 'Daily opponent found: your match is on home' : 'In the daily queue: your match will be on home', true);
  await loadDaily(); ctx.changed();
}
