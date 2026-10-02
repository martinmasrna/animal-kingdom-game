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

// A card change shows the card as it was, faded, beside the card as it is; a rule or a new thing is words alone.
function itemHTML(it, cards) {
  const c = it.cards.length === 1 && Object.keys(it.was || {}).length ? cards[it.cards[0]] : null;
  const pair = c ? `<div class="npair"><div class="ncard was">${cardHTML({ ...c, ...it.was })}</div><i class="narrow"></i><div class="ncard">${cardHTML(c)}</div></div>` : '';
  return `<li><p>${esc(it.text)}</p>${it.why ? `<p class="why">${esc(it.why[0].toUpperCase() + it.why.slice(1))}</p>` : ''}${pair}</li>`;
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
