// News (web/news.py, the releases in web/news/*.md): the News screen, and "Since you last played", the piece a returning
// player sees once on home when a release changed a rule or a card in one of their decks (design sandbox news/).
import { cardHTML, fitNames } from './card.js';

let N = null;   // the last /api/news answer: { releases, unread, newest, since }
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

export async function loadNews(api) {
  const r = await api('/api/news').catch(() => null);
  N = r && r.ok ? await r.json() : N;
  return N;
}
export const unread = () => !!(N && N.unread);

// The words of `now` that aren't in `was`, in order (a longest common subsequence of words), marked as the change.
function markNew(was, now) {
  const a = was.split(/\s+/), b = now.split(/\s+/), L = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) for (let j = b.length - 1; j >= 0; j--) L[i][j] = a[i] === b[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const out = []; let i = 0, j = 0;
  while (j < b.length) {
    if (i < a.length && a[i] === b[j]) { out.push(b[j]); i++; j++; }
    else if (i < a.length && L[i + 1][j] >= L[i][j + 1]) i++;
    else out.push(`<mark>${b[j++]}</mark>`);
  }
  return out.join(' ').replace(/<\/mark> <mark>/g, ' ');
}
// A card change shows the card as it is with the change marked on it (as Hearthstone does): a strength that went up or down
// tinted as a changed strength is in the hand, new rules words highlighted. A rule or a new thing is words alone.
function itemHTML(it, cards) {
  const c = it.cards.length === 1 && Object.keys(it.was || {}).length ? cards[it.cards[0]] : null;
  const card = c ? `<div class="ncard">${cardHTML({ ...c, str: it.was.str ?? c.str, text: it.was.text ? markNew(it.was.text, c.text) : c.text }, { str: c.str })}</div>` : '';
  const words = `<p>${esc(it.text)}</p>${it.why ? `<p class="why">${esc(it.why[0].toUpperCase() + it.why.slice(1))}</p>` : ''}`;
  return card ? `<li class="chg">${card}<div class="nwords">${words}</div></li>` : `<li>${words}</li>`;   // a card change: the card beside its words
}
function releaseHTML(r, open, cards) {
  return `<section class="nrel${open ? ' open' : ''}" data-rel="${r.id}"><button class="nhead"><b>${esc(r.date.replace(/ \d{4}$/, ''))}</b><i class="chev"></i></button>`
    + (open ? `<div class="nbody">${r.groups.map(g => `<h3>${g.name}</h3><ul>${g.items.map(it => itemHTML(it, cards)).join('')}</ul>`).join('')}</div>` : '')
    + '</section>';
}

export async function newsScreen(app, { api, cards, back, onOpened }) {
  const n = await loadNews(api);
  const rels = (n && n.releases) || [];
  let open = rels.length ? rels[0].id : null;
  const draw = () => {
    app.innerHTML = `<div class="mscr lead news"><div class="lcol"><div class="hhead"><h2>News</h2></div>
      <div class="lbody">${rels.map(r => releaseHTML(r, r.id === open, cards)).join('') || '<p class="none">Nothing yet.</p>'}</div>
      <div class="sfoot"><button class="backbtn" id="back"><span>Back</span></button></div></div></div>`;
    fitNames(app);
    app.querySelector('#back').onclick = back;
    app.querySelectorAll('.nrel .nhead').forEach(h => h.onclick = () => { const id = h.parentElement.dataset.rel; open = open === id ? null : id; draw(); });
  };
  draw();
  if (n && n.newest && n.unread) {   // opening News reads it: the corner piece's dot goes
    n.unread = false; onOpened && onOpened();
    api('/api/news/seen', { method: 'POST', body: JSON.stringify({ opened: n.newest }) });
  }
}

// Once, on home: the changes since a returning player last saw this piece that are rules or touch their decks.
export function showSince(api, { onRead }) {
  if (!N || !N.since || !N.since.length || document.getElementById('since')) return;
  const order = it => it.group === 'Rules' ? 0 : 1;   // rules touch everyone: first
  const all = [...N.since].sort((a, b) => order(a) - order(b)), items = all.slice(0, 3), more = all.length - items.length;
  const el = document.createElement('div'); el.id = 'since'; el.className = 'chal since';
  el.innerHTML = `<b>Since you last played</b><ul>${items.map(it => `<li><p>${esc(it.text)}</p>${it.decks && it.decks.length && it.group !== 'Rules'
      ? `<p class="why">In your ${it.decks.length > 1 ? 'decks' : 'deck'} ${it.decks.map(esc).join(', ')}</p>` : ''}</li>`).join('')}</ul>`
    + (more > 0 ? `<p class="more">and ${more} more</p>` : '')
    + '<div class="btns"><button class="slab" data-x="read">Read all news</button><button class="play" data-x="ok">OK</button></div>';
  document.body.appendChild(el);
  const done = () => { el.remove(); api('/api/news/seen', { method: 'POST', body: JSON.stringify({ shown: N.newest }) }); N.since = []; };
  el.querySelector('[data-x="ok"]').onclick = done;
  el.querySelector('[data-x="read"]').onclick = () => { done(); onRead(); };
}
export const hideSince = () => { const el = document.getElementById('since'); if (el) el.remove(); };
