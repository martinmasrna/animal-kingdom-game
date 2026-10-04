// Chat between friends (web/chat.py; design sandbox ladder/chat/greybox.html, approved by Martin 2026-10-04). The Friends
// button (home's corner piece, the game's icon row) opens a panel down the right edge: your friends with the last line
// and an unread count, then one conversation. A message that arrives while the panel is elsewhere slides in as a small
// piece by the Friends button for a few seconds, with a soft pop; in a match its bell mutes them (they only count), and
// that choice is remembered. Messages come on the presence socket (friends.js).
import { play as sfx } from './sound.js';
import { onPresence, friendLabel, seen, shareLink } from './friends.js';

const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch { return null; } };
export const ICON_FRIENDS = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/><path d="M15.5 4.8a3.5 3.5 0 0 1 0 6.4"/><path d="M18 14.3c2.1.7 3.5 2.8 3.5 5.7"/></svg>';
const BELL = '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>';
const BELL_OFF = BELL + '<path d="M4 4l16 16"/>';
const TRASH = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16"/><path d="M10 11v6M14 11v6"/><path d="M6 7l1 13h10l1-13"/><path d="M9 7V4h6v3"/></svg>';
const SEND = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h13"/><path d="M13 6l6 6-6 6"/></svg>';
const bell = off => `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${off ? BELL_OFF : BELL}</svg>`;

let ctx = null;   // { api, inMatch(), challenge(friend, friends), toast(msg, ok) }
const S = { friends: null, code: null, unread: {}, msgs: {}, open: false, with: null };
export const mutedInMatch = () => store('ak:chatmute') === '1';
const setMuted = on => store('ak:chatmute', on ? '1' : '0');
const total = () => Object.values(S.unread).reduce((a, b) => a + b, 0);
export const hasFriends = () => !!(S.friends && S.friends.length);

export function initChat(c) {
  ctx = c;
  onPresence(m => {
    if (m.t === 'unread') { S.unread = { ...m.unread }; badges(); }
    if (m.t === 'msg') arrive(m);
    if (m.t === 'online') loadFriends();   // a friend came on or went away: the count and the list follow
  });
  addEventListener('keydown', e => { if (e.key === 'Escape' && S.open) { e.stopImmediatePropagation(); closeChat(); } }, true);
  // a press anywhere off the panel closes it, as a popup does (the Friends button toggles it itself; the message piece and
  // the remove-friend question belong to it). On the press, not the click: a redraw inside the panel would detach the target.
  addEventListener('pointerdown', e => { if (S.open && !e.target.closest('#chatp, .chatbtn, #chatt, .fbov')) closeChat(); }, true);
  loadFriends();
}

async function loadFriends() {
  const r = await ctx.api('/api/friends').catch(() => null);
  if (!r || !r.ok) return;
  const j = await r.json();
  S.friends = j.friends; S.code = j.code;
  S.unread = Object.fromEntries(j.friends.filter(f => f.unread).map(f => [f.id, f.unread]));
  badges(); ctx.changed && ctx.changed();
  if (S.open && !S.with) draw();
}

// The Friends button's counts, wherever a Friends button stands: unread messages (a red badge) and friends online now
// (a plain number beside the icon, as Hearthstone's social button has it).
const online = () => (S.friends || []).filter(f => f.online).length;
export const badge = () => `<i class="cbadge"${total() ? '' : ' hidden'}>${total()}</i><i class="conline"${online() ? '' : ' hidden'}>${online()}</i>`;
function badges() {
  document.querySelectorAll('.chatbtn .cbadge').forEach(b => { b.textContent = total(); b.hidden = !total(); });
  document.querySelectorAll('.chatbtn .conline').forEach(b => { b.textContent = online(); b.hidden = !online(); });
}
export const wireChatButton = el => { el.onclick = e => { e.stopPropagation(); S.open && !S.with ? closeChat() : openChat(); }; };

function arrive(m) {
  const other = m.with, mine = m.msg.from !== other, conv = S.msgs[other];
  if (conv && !conv.some(x => x.id === m.msg.id)) conv.push(m.msg);
  const f = S.friends && S.friends.find(x => x.id === other);
  if (f) f.last = { text: m.msg.text, at: m.msg.at, mine };
  if (S.open && S.with === other) {
    draw();
    if (!mine) ctx.api(`/api/chat/${other}/read`, { method: 'POST' });
    return;
  }
  if (mine) { if (S.open) draw(); return; }
  S.unread[other] = (S.unread[other] || 0) + 1; badges();
  if (S.open) draw();
  const quiet = ctx.inMatch() && mutedInMatch();
  if (!quiet) { piece(m.name || (f ? friendLabel(f, S.friends) : 'A friend'), m.msg.text, other); sfx('msg'); }
}

// A message arriving: a small granite piece by the Friends button (in a match, beside the icon row; on a menu, under the
// corner piece) for six seconds. Clicking it opens the conversation; in a match its bell mutes them.
function piece(name, text, other) {
  let el = document.getElementById('chatt');
  if (!el) { el = document.createElement('div'); el.id = 'chatt'; el.className = 'chatt'; document.body.appendChild(el); }
  const match = ctx.inMatch();
  el.innerHTML = `<div class="who"><b>${esc(name)}</b><span>${esc(text)}</span></div>${match ? `<button class="mute" aria-label="Mute messages during matches" data-tip="Mute during matches">${bell(true)}</button>` : ''}`;
  const btn = [...document.querySelectorAll('.chatbtn')].find(b => b.offsetParent), top = document.querySelector('.home .top');
  el.style.left = el.style.right = el.style.top = '';
  el.classList.toggle('inmatch', match);
  if (match && btn) { const r = btn.getBoundingClientRect(); el.style.right = (innerWidth - r.left + 8) + 'px'; el.style.top = r.top + 'px'; }
  else if (top) { const r = top.getBoundingClientRect(); el.style.right = (innerWidth - r.right) + 'px'; el.style.top = (r.bottom + 8) + 'px'; }
  else { el.style.right = '16px'; el.style.top = '16px'; }
  el.classList.remove('on'); void el.offsetWidth; el.classList.add('on');
  el.onclick = e => {
    if (e.target.closest('.mute')) { setMuted(true); el.classList.remove('on'); ctx.toast('Messages muted during matches', true); return; }
    el.classList.remove('on'); openChat(other);
  };
  clearTimeout(piece.h); piece.h = setTimeout(() => el.classList.remove('on'), 6000);
}

export function openChat(other = null) {
  S.open = true; S.with = other;
  const t = document.getElementById('chatt'); if (t) t.classList.remove('on');
  draw();
  if (other) loadConv(other); else loadFriends();   // who is on now, and the last lines
}
export function closeChat() {
  S.open = false; S.with = null;
  const p = document.getElementById('chatp'); if (p) p.remove();
  document.querySelectorAll('.chatbtn').forEach(b => b.classList.remove('open')); document.body.classList.remove('chatopen');
}

async function loadConv(other) {
  const r = await ctx.api(`/api/chat/${other}`);
  if (!r.ok) return;
  S.msgs[other] = (await r.json()).messages;
  delete S.unread[other]; badges();
  if (S.with === other) draw(true);
}

// When a burst of messages started, in words: the time today, else "yesterday", else the date.
const when = at => {
  const d = new Date(at * 1000), now = new Date(), hm = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const days = Math.round((new Date(now.toDateString()) - new Date(d.toDateString())) / 864e5);
  return days === 0 ? hm : days === 1 ? `yesterday ${hm}` : d.toLocaleDateString([], { day: 'numeric', month: 'short' });
};

function draw(scrollDown) {
  if (!S.open) return;
  let p = document.getElementById('chatp');
  const keep = p && p.querySelector('#chatin'), typed = keep ? keep.value : '', focused = keep && document.activeElement === keep;
  if (!p) { p = document.createElement('div'); p.id = 'chatp'; p.className = 'chatp'; document.body.appendChild(p); }
  p.classList.toggle('inmatch', ctx.inMatch());
  document.querySelectorAll('.chatbtn').forEach(b => b.classList.add('open'));
  document.body.classList.add('chatopen');   // the Feedback tab on the edge steps aside
  const all = S.friends || [], f = S.with && all.find(x => x.id === S.with);
  if (!f) {   // the list
    S.with = null;
    const html = `<div class="chead"><b>Friends</b><button class="cx" id="chatx" aria-label="Close">×</button></div>
      <div class="clist">${all.length ? all.map(x => `<button class="slab cfr" data-with="${x.id}"><span class="dot${x.online ? ' on' : ''}"></span><span class="nm">${esc(friendLabel(x, all))}</span>${S.unread[x.id] ? `<i class="n">${S.unread[x.id]}</i>` : ''}
        <small>${x.last ? esc((x.last.mine ? 'You: ' : '') + x.last.text) + (x.online ? '' : ` · ${seen(x)}`) : seen(x) || 'away'}</small></button>`).join('')
        : `<p class="none">${S.friends ? 'No friends yet. Send someone your friend link.' : ''}</p>`}</div>
      <button class="slab" id="chatadd">Add a friend</button>`;
    if (p.dataset.view === 'list' && p._html === html) return;   // unchanged: a redraw under the pointer would eat a click
    p.innerHTML = p._html = html; p.dataset.view = 'list';
    p.querySelectorAll('[data-with]').forEach(el => el.onclick = () => openChat(el.dataset.with));
    p.querySelector('#chatadd').onclick = () => S.code && shareLink(`${location.origin}/#/friend/${S.code}`, 'Be my friend in Animal Kingdom');
  } else {   // one conversation
    const name = friendLabel(f, all), msgs = S.msgs[f.id], match = ctx.inMatch();
    let prev = 0;
    const lines = (msgs || []).map(m => { const gap = m.at - prev > 600; prev = m.at;
      return (gap ? `<span class="when">${when(m.at)}</span>` : '') + `<div class="msg${m.from === f.id ? '' : ' me'}">${esc(m.text)}</div>`; }).join('');
    const html = `<div class="chead"><button class="cx back" id="chatback" aria-label="All friends">‹</button><b><span class="dot${f.online ? ' on' : ''}"></span>${esc(name)}</b>
        ${match ? `<button class="cx" id="chatmute" aria-label="${mutedInMatch() ? 'Unmute' : 'Mute'} messages during matches" data-tip="${mutedInMatch() ? 'Muted during matches' : 'Mute during matches'}">${bell(mutedInMatch())}</button>` : ''}${match ? '' : `<button class="cx" id="chatrm" aria-label="Remove friend" data-tip="Remove friend">${TRASH}</button>`}<button class="cx" id="chatx" aria-label="Close">×</button></div>
      ${f.online ? '' : `<p class="away">Away · they'll see it when they're back</p>`}
      ${match ? '' : `<button class="play" id="chatchal">${f.online ? `Challenge ${esc(name)}` : 'Send a match link'}</button>`}
      <div class="msgs" id="chatmsgs">${msgs ? lines || `<p class="none">Say hello to ${esc(name)}.</p>` : ''}</div>
      <div class="csend"><input class="field" id="chatin" maxlength="500" placeholder="Message ${esc(name)}…" autocomplete="off"><button class="play" id="chatgo" aria-label="Send">${SEND}</button></div>`;
    if (p.dataset.view === f.id && p._html === html) return;
    p.innerHTML = p._html = html; p.dataset.view = f.id;
    p.querySelector('#chatin').value = typed;
    p.querySelector('#chatback').onclick = () => { S.with = null; draw(); };
    const ch = p.querySelector('#chatchal'); if (ch) ch.onclick = () => { closeChat(); ctx.challenge(f, all); };
    const rm = p.querySelector('#chatrm'); if (rm) rm.onclick = () => removeFriend(f, name);
    const mu = p.querySelector('#chatmute'); if (mu) mu.onclick = () => { setMuted(!mutedInMatch()); draw(); };
    const box = p.querySelector('#chatmsgs'); if (scrollDown !== false) box.scrollTop = box.scrollHeight;
    const inp = p.querySelector('#chatin');
    const send = async () => {
      if (!inp.value.trim()) return;
      const text = inp.value; inp.value = '';
      const r = await ctx.api(`/api/chat/${f.id}`, { method: 'POST', body: JSON.stringify({ text }) });
      if (!r.ok) { inp.value = text; return ctx.toast(await r.text()); }
      arrive({ with: f.id, msg: await r.json() });   // the socket echoes it too; the id keeps it once
    };
    inp.onkeydown = e => { e.stopPropagation(); if (e.key === 'Enter') send(); };   // Space and D belong to the box here, not the game
    // Send by the box (Enter alone was invisible, above all on a phone); the box keeps the focus and the keyboard stays up
    const go = p.querySelector('#chatgo'); go.onpointerdown = e => e.preventDefault(); go.onclick = () => { send(); inp.focus(); };
    if (focused || (!('ontouchstart' in window) && !typed)) inp.focus();
  }
  p.querySelector('#chatx').onclick = closeChat;
}

// Removing a friend is asked first, as deleting a deck is; the panel goes back to the list.
function removeFriend(f, name) {
  const ov = document.createElement('div'); ov.className = 'fbov';
  ov.innerHTML = `<div class="fbbox ask"><b>Remove ${esc(name)} from your friends?</b><div class="btns"><button class="slab" data-x="no">Keep</button><button class="play danger" data-x="yes">Remove</button></div></div>`;
  document.body.appendChild(ov); ov.onclick = e => { if (e.target === ov) ov.remove(); };
  ov.querySelector('[data-x="no"]').onclick = () => ov.remove();
  ov.querySelector('[data-x="yes"]').onclick = async () => { ov.remove(); await ctx.api('/api/friends/' + f.id, { method: 'DELETE' }); S.with = null; loadFriends(); };
}

// Your friends list changed elsewhere (added one, removed one): the panel's list follows.
export const refreshChat = () => loadFriends();
