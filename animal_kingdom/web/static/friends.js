// Friends and challenges on the client (web/friends.py, server.py): the presence socket that keeps you online and brings
// challenges, the challenge piece, the friend-link confirmation, links shared through the phone's share sheet (copied on
// a computer), and a friend's row as home and the profile show it.

const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
import { play as sfx } from './sound.js';
let ctx = null, ws = null, pending = null, asks = [];
const hears = [];   // others listening on the presence socket (chat.js)
export const onPresence = fn => hears.push(fn);   // asks: friend requests waiting for an answer   // ctx: { api, toast, key(), busy(), accept(challenge) }

// Online while this is open; a challenge arrives on it. Reconnects after a drop.
export function openPresence(c) {
  ctx = c;
  const connect = () => {
    if (!ctx.key()) return;
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/presence?key=${encodeURIComponent(ctx.key())}`);
    ws.onmessage = e => { const m = JSON.parse(e.data);
      if (m.t === 'build') ctx.build(m.build);
      if (m.t === 'challenge') { pending = m; showChallenge(); sfx('challenge'); }
      if (m.t === 'challenge_gone' && pending && pending.id === m.id) { pending = null; showChallenge(); }
      if (m.t === 'friendreq' && !asks.some(a => a.from === m.from)) { asks.push(m); showChallenge(); }
      hears.forEach(fn => fn(m)); };
    ws.onclose = () => setTimeout(connect, 3000);
  };
  connect();
}

// The challenge piece: at the top centre over any menu, never over a match in play (it waits until that ends).
export function showChallenge() {
  showAsk();
  let el = document.getElementById('chal');
  if (!pending || ctx.busy()) { if (el) el.remove(); return; }
  if (el && el.dataset.id === pending.id) return;
  if (el) el.remove();
  el = document.createElement('div'); el.id = 'chal'; el.className = 'chal'; el.dataset.id = pending.id;
  el.innerHTML = `<b>${esc(pending.from)} challenges you</b><div class="btns"><button class="slab" data-x="no">Decline</button><button class="play" data-x="yes">Play</button></div>`;
  document.body.appendChild(el);
  const c = pending, answer = async accept => {
    pending = null; el.remove();
    const r = await ctx.api(`/api/challenge/${c.id}/answer`, { method: 'POST', body: JSON.stringify({ accept, deck: ctx.deck() }) });
    if (!r.ok) return accept && ctx.toast(await r.text());
    if (accept) ctx.accept(await r.json());
  };
  el.querySelector('[data-x="no"]').onclick = () => answer(false);
  el.querySelector('[data-x="yes"]').onclick = () => answer(true);
}

// A friend request (sent from the leaderboard): the same piece as a challenge, after any challenge, one at a time.
function showAsk() {
  let el = document.getElementById('fask');
  const a = asks[0];
  if (!a || ctx.busy() || document.getElementById('chal')) { if (el) el.remove(); return; }
  if (el && el.dataset.from === a.from) return;
  if (el) el.remove();
  el = document.createElement('div'); el.id = 'fask'; el.className = 'chal'; el.dataset.from = a.from;
  el.innerHTML = `<b>${esc(a.name)} wants to be friends</b><div class="btns"><button class="slab" data-x="no">Not now</button><button class="play" data-x="yes">Add friend</button></div>`;
  document.body.appendChild(el);
  const answer = async accept => {
    asks.shift(); el.remove();
    const r = await ctx.api(`/api/friends/request/${encodeURIComponent(a.from)}/answer`, { method: 'POST', body: JSON.stringify({ accept }) });
    if (r.ok && accept) ctx.toast(`You and ${a.name.split('#')[0]} are friends`, true);
    showChallenge();
  };
  el.querySelector('[data-x="no"]').onclick = () => answer(false);
  el.querySelector('[data-x="yes"]').onclick = () => answer(true);
}

// A friend link opened: who it is, then the question; Add makes you friends both ways.
export async function confirmFriend(code, done) {
  const r = await ctx.api(`/api/friends/link/${encodeURIComponent(code)}`);
  if (!r.ok) { ctx.toast(await r.text()); return done(); }
  const f = await r.json();
  if (f.self) { ctx.toast('That\'s your own friend link'); return done(); }
  if (f.already) { ctx.toast(`You and ${f.name} are friends`, true); return done(); }
  const ov = document.createElement('div'); ov.className = 'fbov';
  ov.innerHTML = `<div class="fbbox ask"><b>Add ${esc(f.name)} as a friend?</b>
    <div class="btns"><button class="slab" data-x="no">Not now</button><button class="play" data-x="yes">Add friend</button></div></div>`;
  document.body.appendChild(ov);
  ov.querySelector('[data-x="no"]').onclick = () => { ov.remove(); done(); };
  ov.querySelector('[data-x="yes"]').onclick = async () => {
    const a = await ctx.api('/api/friends', { method: 'POST', body: JSON.stringify({ code }) });
    ov.remove();
    if (!a.ok) ctx.toast(await a.text()); else ctx.toast(`You and ${f.name} are friends`, true);
    done();
  };
}

// A link to send: the phone's share sheet, else copied.
export async function shareLink(url, text) {
  if (navigator.share && matchMedia('(hover: none)').matches) { try { await navigator.share({ url, text }); return; } catch { return; } }
  try { await navigator.clipboard.writeText(url); ctx.toast('Link copied', true); } catch { ctx.toast(url); }
}

// When a friend was last on, in words.
export const seen = f => {
  if (f.online) return 'online';
  if (!f.seen) return '';
  const d = Math.floor((Date.now() / 1000 - f.seen) / 86400);
  return d < 1 ? 'today' : d < 2 ? 'yesterday' : `${d} days ago`;
};
// A friend's name without its #tag, unless another of your friends shares the name.
export const friendLabel = (f, all) => { const first = f.name.split('#')[0];
  return (all || []).filter(g => g.name.split('#')[0] === first).length > 1 ? f.name : first; };
export const friendRow = (f, extra = '', all = []) => `<span class="dot${f.online ? ' on' : ''}"></span><span class="nm">${esc(friendLabel(f, all))}</span><small>${seen(f)}</small>${extra}`;
