// Ranked, outside the match: home's Play ranked with your deck and where you stand, the leaderboard, and what a ranked
// game did to your league, on its end. The server holds all of it (web/ladder.py, tiers.py, pool.py); this draws its answers.
// A plain prototype like the rest of home: grey boxes, the league emblems placeholders (static/kit2/league/).
import { leaderToken } from './mana.js';

const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);

// A league (the server's tiers.view): named by its material, three divisions in it counting 3, 2, 1, five wins a division;
// in the top league the rating instead. The emblem says league and division by itself, a pip stands for each win.
const emblem = lg => lg.top ? '' : `<img class="lgem" src="/static/kit2/league/${lg.emblem}.webp" alt="${esc(lg.label)}" draggable="false">`;
const pips = lg => lg.top ? '' : `<i class="lgpips" aria-label="${lg.stars} of ${lg.of} wins">${Array.from({ length: lg.of }, (_, i) => `<s${i < lg.stars ? ' class="on"' : ''}></s>`).join('')}</i>`;
const standing = lg => lg.top ? `<b>${esc(lg.label)}</b><span class="rnum">${esc(lg.rating)}</span>` : `${emblem(lg)}<b>${esc(lg.label)}</b>${pips(lg)}`;

// Home's ranked block: the button, the deck it plays (a click opens your legal decks in its place) and where you stand,
// which is the way to the leaderboard. `decks`: your legal decks as home lists them; `chosen`: the one that plays.
export function rankedHome({ me, decks, chosen, cards, picking }) {
  const face = d => `${d.leader && cards[d.leader] ? `<div class="tokpiece" style="--tw:36px">${leaderToken(d.leader, 'A', cards, 36)}</div>` : ''}<span>${esc(d.name)}</span>`;
  const deck = !chosen ? '<a class="rkdeck none" href="#/collection">Build a deck to play ranked</a>'
    : picking ? `<div class="rkpick">${decks.map(d => `<button class="rkdeck${d.id === chosen.id ? ' on' : ''}" data-rkdeck="${esc(d.id)}">${face(d)}</button>`).join('')}</div>`
    : `<button class="rkdeck" id="rkdeck"${decks.length > 1 ? '' : ' disabled'}>${face(chosen)}${decks.length > 1 ? '<small>Change</small>' : ''}</button>`;
  const lg = me && me.league;
  return `<div class="rk"><button class="go${chosen ? '' : ' off'}" id="rkgo">Play ranked</button>${deck}
    ${lg ? `<a class="rkstand" id="rkstand" href="#/ladder">${standing(lg)}${me.rank ? `<span class="rkplace">#${me.rank}</span>` : ''}</a>` : ''}</div>`;
}

// Start a ranked match with `deck` (a deck spec): the server answers with the match, at once. One at a time: a second
// click while the first is on its way starts nothing.
let starting = false;
export async function playRanked({ api, toast, deck, enter }) {
  if (!deck) return toast('Build a legal deck in the Collection first: 25 cards and a leader');
  if (starting) return;
  starting = true;
  try {
    const r = await api('/api/ranked', { method: 'POST', body: JSON.stringify({ deck }) });
    if (!r.ok) return toast(await r.text());
    enter(await r.json());
  } finally { starting = false; }
}

// The leaderboard: everyone on the ladder, best first. A bot's row is its deck's leader, its name and its rating; a
// person's their league in the number's place, and in the top league the number.
export async function leaderboardScreen(app, { api, me, cards }) {
  const lg = me && me.league;
  app.innerHTML = `<div class="mhome"><div class="box rkboard"><h1>Leaderboard</h1>
    ${lg ? `<div class="rkstand mine">${standing(lg)}${lg.streak >= 2 ? `<span class="rkstreak">${lg.streak} wins in a row</span>` : ''}</div>` : ''}
    <div class="rkrows" id="rkrows"></div>
    <div class="row"><a class="sec" href="#/">Back</a></div></div></div>`;
  const r = await api('/api/leaderboard'), rows = r.ok ? (await r.json()).rows : [], box = document.getElementById('rkrows');
  if (!box) return;   // the screen was left meanwhile
  const name = n => { const [nm, tag] = n.split('#'); return esc(nm) + (tag ? `<i class="tg">#${esc(tag)}</i>` : ''); };
  box.innerHTML = rows.map((x, i) => `<div class="rkrow${x.bot ? ' bot' : ''}${x.you ? ' you' : ''}"><span class="n">${i + 1}</span>`
    + `<span class="pc">${x.bot && x.leader && cards[x.leader] ? `<div class="tokpiece" style="--tw:30px">${leaderToken(x.leader, 'B', cards, 30)}</div>` : ''}</span>`
    + `<span class="nm">${name(x.name)}</span>`
    + `<b>${x.league && !x.league.top ? `${emblem(x.league)}${pips(x.league)}` : esc(x.rating)}</b></div>`).join('');
  const mine = box.querySelector('.you'); if (mine) mine.scrollIntoView({ block: 'nearest' });
}

// A ranked game's end (the view's `league` and `rating`, once the server has rated it): your league's emblem and wins, with
// its name, or in the name's place what the game did when it moved you (a division or a league up or down, the streak's
// second win); in the top league the rating, counting from before to after when the end was seen live. No rematch: Play
// again is the next match.
export function rankedEnd(V, live) {
  const lg = V.league, rt = lg && lg.top ? V.rating : null, d = rt ? rt.delta : 0;
  const moved = lg && lg.line && (!lg.top || /^Up to/.test(lg.line));   // in the top league only the game that brought you there says so
  const line = !lg ? '' : `<div class="rkend" id="rkend">${emblem(lg)}<b>${esc(moved ? lg.line : lg.label)}</b>${pips(lg)}</div>`;
  const rating = !rt ? '' : `<div class="rating"><small>Rating</small><div><b id="rnum">${live ? rt.before : rt.after}</b><span class="rd ${d >= 0 ? 'up' : 'down'}${live ? '' : ' on'}">${d >= 0 ? '+' : '−'}${Math.abs(d)}</span></div></div>`;
  return { html: line + rating, button: '<button class="play" id="again">Play again</button>',
    wire: again => { const b = document.getElementById('again'); if (b) b.onclick = again; if (live && rt) countRating(rt); } };
}
// The server sends the ratings as shown ("1781", "1500?" while provisional): count on the numbers, land on its text.
function countRating(rt) {
  const t0 = performance.now() + 700, dur = 1100, from = parseInt(rt.before, 10);
  const step = now => { const n = document.getElementById('rnum'); if (!n) return;
    const k = Math.min(1, Math.max(0, (now - t0) / dur)), e = 1 - (1 - k) ** 3;
    n.textContent = k < 1 ? Math.round(from + rt.delta * e) : rt.after;
    if (k < 1) requestAnimationFrame(step); else n.nextElementSibling.classList.add('on'); };
  requestAnimationFrame(step);
}
