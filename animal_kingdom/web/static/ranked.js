// Ranked, around the match: the ranked screen (where you are between matches), the versus moment before a match, and a
// ranked match's ending. The server holds all of it (web/ladder.py, tiers.py, pool.py); this draws its answers.
//
// A grey prototype of the structure Martin went through on 2026-11-23 and 24 ("greybox-wise it all looks good"); what a
// league looks like comes with the world's art. Until then a league's mark is a disc in the colour the server holds for
// it, with its division's number in it, and in Legend your rating (Martin, 2026-11-24: "it should be inside it, of course").
// No word stands where a sign, a colour or a state can say it (Martin, 2026-11-23: "the label is laziest, ugliest
// possible way to do it"): the words left are names, the verdict, Play and Continue.
import { leaderToken, manaCard } from './mana.js';

const esc = t => String(t).replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
const ICON = { open: '<svg class="rkic" viewBox="0 0 24 24"><path d="M5 9l7 7 7-7"/></svg>', plus: '<svg class="rkic" viewBox="0 0 24 24"><path d="M12 4v16M4 12h16"/></svg>',
  back: '<svg class="rkic" viewBox="0 0 24 24"><path d="M15 5l-7 7 7 7"/></svg>' };

// A standing is the server's tiers.view: {name, label, colour, top, division, stars, of, streak, rating}.
const mark = lg => `<div class="rkmark" style="--c:${esc(lg.colour)}"><b${lg.top ? ' class="num"' : ''}>${esc(lg.top ? lg.rating : lg.division)}</b></div>`;
// The five wins of your division. On a streak the two wins your next win brings wait in the row, faint (the third win in
// a row and every one after it counts double).
const wins = lg => `<div class="rkwins" style="--c:${esc(lg.colour)}">${Array.from({ length: lg.of }, (_, i) => `<i class="${i < lg.stars ? 'on' : lg.streak >= 2 && i < lg.stars + 2 ? 'ghost' : ''}"></i>`).join('')}</div>`;
// Where you stand: the mark, the league's name, and under it the five wins; in Legend that row is what the last match did to the rating.
const standing = (lg, delta) => `<div class="rkstand">${mark(lg)}<h1>${esc(lg.label)}</h1>${lg.top ? `<div class="rkdelta ${delta > 0 ? 'up' : 'down'}">${delta ? `${delta > 0 ? '+' : '−'}${Math.abs(delta)}` : ''}</div>` : wins(lg)}</div>`;

// A player as one card (Martin, 2026-11-24: "fold all 3 (portrait, name rank) ... into a single frame/border of the card"):
// their deck's leader as the game's own card, their name where the card's name goes, their league's mark set into its
// corner where a card carries its cost. A person's deck name is never shown to their opponent.
function playerCard(who, p, cards) {
  const c = cards[p.leader];
  const card = c ? manaCard({ ...c, name: p.name, text: '' }, { str: null, cost: null, owner: who === 'you' ? 'A' : 'B', w: 240 }) : `<div class="rknocard"><b>${esc(p.name)}</b></div>`;
  return `<div class="rkcard ${who}">${card}${p.league ? mark(p.league) : ''}</div>`;
}
// A long name is set smaller until it fits its card, down to 60% of its size.
function fitNames(root) {
  root.querySelectorAll('.rkcard .pname').forEach(n => { let k = 1; n.style.fontSize = '';
    const base = parseFloat(getComputedStyle(n).fontSize); while (n.scrollWidth > n.clientWidth + 1 && k > .6) n.style.fontSize = base * (k -= .05) + 'px'; });
}

// ---------------------------------------------------------------- the ranked screen
// `me`: your profile (its `league` is your standing); `decks`: your decks as home lists them, legal or not; `chosen`: the
// legal one that plays; `choose(id)` keeps another and draws the screen again; `play()` starts a match with the chosen one.
export function rankedScreen(app, { me, decks, chosen, cards, deckSize, choose, play }) {
  const legal = decks.filter(d => !d.short), token = d => `<div class="tokpiece">${d.leader && cards[d.leader] ? leaderToken(d.leader, 'A', cards, 96) : ''}</div>`;   // its size is the plate's (ranked.css --tw)
  const plate = !chosen ? `<a class="rkdeck none" id="rkdeck" href="#/collection" aria-label="Build a deck">${ICON.plus}</a>`
    : `<button class="rkdeck" id="rkdeck"${legal.length > 1 ? '' : ' disabled'} aria-label="Your deck">${token(chosen)}<b>${esc(chosen.name)}</b>${legal.length > 1 ? ICON.open : ''}</button>`;
  app.innerHTML = `<div class="rkscreen"><a class="rkback" href="#/" aria-label="Back">${ICON.back}</a>
    ${me && me.league ? standing(me.league) : '<div class="rkstand"></div>'}
    <div class="rkfoot">${plate}<button class="rkplay${chosen ? '' : ' off'}" id="rkgo"${chosen ? '' : ' disabled'}>Play</button></div>
    <div class="rksheet" id="rksheet" hidden><div class="rkrows">${decks.map(d => `<button class="rkdeck${chosen && d.id === chosen.id ? ' on' : ''}${d.short ? ' bad' : ''}" data-deck="${esc(d.id)}"${d.short ? ' disabled' : ''}>${token(d)}<b>${esc(d.name)}</b>${d.short > 0 ? `<small>${d.list.length}/${deckSize}</small>` : ''}</button>`).join('')}</div></div></div>`;
  const sheet = document.getElementById('rksheet'), deck = document.getElementById('rkdeck');
  if (chosen && legal.length > 1) deck.onclick = () => { sheet.hidden = false; };
  sheet.onclick = e => { const b = e.target.closest('[data-deck]'); if (b && !b.disabled) return choose(b.dataset.deck); if (!e.target.closest('.rkrows')) sheet.hidden = true; };
  document.getElementById('rkgo').onclick = () => play();
}

// Start a ranked match with `deck` (a deck spec): the server answers with the match at once, and with the two players for
// the versus moment. One at a time: a second press while the first is on its way starts nothing.
let starting = false;
export async function playRanked({ api, toast, deck, cards, enter }) {
  if (!deck || starting) return;
  starting = true;
  try {
    const r = await api('/api/ranked', { method: 'POST', body: JSON.stringify({ deck }) });
    if (!r.ok) return toast(await r.text());
    const m = await r.json();
    if (m.versus) versus(m.versus, cards);
    enter(m);
  } finally { starting = false; }
}

// The versus moment: over the match as it opens, the other player above and you below (side by side on a wide screen).
// Nothing to press: it lifts by itself, and the first press sends it off and still reaches what is under it (Martin,
// 2026-10-02: the first mulligan clicks were lost to the old one).
function versus(vs, cards) {
  const old = document.getElementById('rkvs'); if (old) old.remove();
  const el = document.createElement('div'); el.className = 'rkvs'; el.id = 'rkvs';
  el.innerHTML = `<div class="rkside them">${playerCard('them', vs.them, cards)}</div><div class="rkside you">${playerCard('you', vs.you, cards)}</div><i class="rkmid">VS</i>`;
  document.body.append(el); fitNames(el);
  const done = () => { removeEventListener('pointerdown', done, true); el.classList.add('out'); setTimeout(() => el.remove(), 400); };
  addEventListener('pointerdown', done, true);
  setTimeout(done, matchMedia('(prefers-reduced-motion: reduce)').matches ? 1600 : 2600);
}

// ---------------------------------------------------------------- a ranked match's ending
// Two full screens, one straight after the other, the match's own last word (Martin, 2026-11-23: the rank change "should
// land as close to victory screen as possible, and it should be on fullscreen. It should be the highlight, the
// culmination of the match itself"). First the verdict: your card and the word, about two seconds, nothing to press.
// Then your rank: your standing as it was going in, and what the match did lands on it. Continue leads to the ranked
// screen. `V`: the match's view (its `league` is your standing after, with `before`; its `rating` the change in Legend);
// `live`: the end was seen happening (else, a finished match opened again, the last screen as it ended); `done()`: Continue.
let ended = null;
export function finale(V, live, { cards, done }) {
  const key = `${V.id}-${V.rematches}`;   // the match screen's own name for this game's end
  if (ended === key && document.getElementById('rkfin')) return;
  live = live && ended !== key;   // played through once; opened again, the last screen as it stands
  ended = key;
  const old = document.getElementById('rkfin'); if (old) old.remove();
  const el = document.createElement('div'); el.className = 'rkfin'; el.id = 'rkfin';
  const you = V.you, w = V.game.result.winner, word = w === null ? 'Draw' : w === you ? 'Victory' : 'Defeat';
  const lg = V.league, before = lg && lg.before, lead = V.game.leaders && V.game.leaders[you];
  const me = { name: ((V.seats[you] || {}).name || '').split('#')[0], leader: lead && lead.id, league: before };
  const goOn = '<button class="rkplay" id="rkcont">Continue</button>';
  const wire = () => { el.querySelector('#rkcont').onclick = () => { el.remove(); done(); }; };
  const rank = () => {   // the match's last screen
    if (!lg || !el.isConnected) return;   // a draw moves nothing: the verdict is the last screen; a match left meanwhile has no ending to show
    const d = lg.top && before.top && V.rating ? V.rating.delta : 0;
    el.innerHTML = `<div class="rkrank" id="rkrank">${standing(live ? before : lg, live ? 0 : d)}${goOn}</div>`; wire();
    if (live) land(el.querySelector('#rkrank'), before, lg, d);
  };
  el.innerHTML = `<div class="rkverdict ${w === null ? 'drawn' : w === you ? 'won' : 'lost'}">${playerCard('you', me, cards)}<h1>${word}</h1>${lg ? '' : goOn}</div>`;
  document.body.append(el); fitNames(el);
  if (!lg) return wire();
  if (!live) return rank();
  const t = setTimeout(rank, 2000); el.onpointerdown = () => { if (el.querySelector('.rkverdict')) { clearTimeout(t); rank(); } };   // a press brings the rank at once
}
// Leaving the match by another way (the browser's back, a link) takes its ending with it.
export function endFinale() { const el = document.getElementById('rkfin'); if (el) el.remove(); }

// What the match did, played on your standing: wins land one after the other or one leaves; a division turns the mark;
// a league takes the whole screen in its colour as its mark arrives; in Legend the rating counts inside the mark.
function land(root, b, a, delta) {
  const at = (ms, f) => setTimeout(() => { if (root.isConnected) f(); }, ms);
  const pip = i => root.querySelectorAll('.rkwins i')[i];
  const settle = cls => { root.querySelector('.rkstand').outerHTML = standing(a, delta); if (cls) root.querySelector('.rkmark').classList.add(cls); };
  if (a.top && b.top) {
    const n = root.querySelector('.rkmark b'), from = parseInt(b.rating, 10), to = parseInt(a.rating, 10), t0 = performance.now() + 600;
    const tick = now => { if (!n.isConnected) return; const k = Math.min(1, Math.max(0, (now - t0) / 900)), e = 1 - (1 - k) ** 3;
      if (k < 1) { n.textContent = Math.round(from + (to - from) * e); requestAnimationFrame(tick); } else settle(); };
    return requestAnimationFrame(tick);
  }
  const moved = a.league !== b.league || a.division !== b.division, up = a.league > b.league || (a.league === b.league && a.division < b.division);
  const pop = (i, ms) => at(ms, () => { const p = pip(i); if (p) { p.classList.remove('ghost'); p.classList.add('on', 'pop'); } });
  const drop = (i, ms) => at(ms, () => { const p = pip(i); if (p) { p.classList.add('drop'); setTimeout(() => p.classList.remove('on', 'drop'), 400); } });
  if (!moved) {
    for (let i = b.stars; i < a.stars; i++) pop(i, 600 + (i - b.stars) * 300);
    for (let i = b.stars - 1; i >= a.stars; i--) drop(i, 600);
    return at(1500, () => settle());
  }
  if (!up) return at(700, () => settle());   // down a division or a league: no ceremony
  for (let i = b.stars; i < b.of; i++) pop(i, 600 + (i - b.stars) * 300);
  at(600 + (b.of - b.stars) * 300 + 400, () => { if (a.league !== b.league) { root.style.setProperty('--c', a.colour); root.classList.add('took'); settle('land'); } else settle('turn'); });
}
