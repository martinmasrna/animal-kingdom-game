// Toy 4 as a game screen: pick one card, press Go; both cards are revealed and clash.
import { CARDS, DECK, newMatch, commit, deckSummary } from './engine.js';
import { makeRng, botChoose } from './bot.js';

const ME = 0, BOT = 1;
const ui = {
  s: null, view: null, busy: false, over: false, showDecks: false, sel: null,
  shown: { hp: [0, 0] }, lines: [[], []], marks: [{}, {}], hist: [], fresh: new Set(),
  rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0,
};
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
const label = (id) => CARDS[id].kind + ' ' + CARDS[id].n;

const ICON = {
  quick: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M14.5 2.5 21.5 2.5 21.5 9.5 10 21l-2-2-2.6 2.6-2.8-2.8L5.2 16.2l-2-2Z" opacity=".95"/></svg>',
  heavy: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M3 5h11v6H3zM14 6.5h3v3h-3zM8 11h3v11H8z"/></svg>',
  guard: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2 20 5v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5Z"/></svg>',
};
const KIND = {
  Quick: { cls: 'k-Light', icon: ICON.quick, text: (n) => `Deal ${n}. Interrupts a Heavy.` },
  Heavy: { cls: 'k-Heavy', icon: ICON.heavy, text: (n) => `Deal ${n}. Breaks a Guard. Interrupted by a Quick.` },
  Guard: { cls: 'k-Defence', icon: ICON.guard, text: (n) => `Blocks a Quick and deals ${n} back.` },
};

function cardHTML(id, { cls = '', attrs = '' } = {}) {
  const c = CARDS[id], k = KIND[c.kind];
  return `<button class="card ${k.cls} ${cls}" ${attrs}>
    <div class="art"><span class="big">${c.n}</span>${k.icon}</div>
    <div class="nm">${c.kind}</div>
    <div class="tx">${k.text(c.n)}</div></button>`;
}

function heroHTML(side) {
  const p = ui.view.p[side], hp = ui.shown.hp[side];
  return `<div class="left"></div>
    <div class="mid"><div class="plate" id="plate${side}"><div class="hp${hp <= 6 ? ' low' : ''}">${hp}</div></div></div>
    <div class="right"><div class="pile"><i></i><b>${p.deck.length}</b></div></div>`;
}
function lineHTML(side) {
  return ui.lines[side].map(id => {
    const m = ui.marks[side][id] || '';
    return `<div class="clash">${cardHTML(id, { cls: 'inline' + (m ? ' ' + m : '') })}</div>`;
  }).join('');
}
function handHTML() {
  const p = ui.view.p[ME];
  const R = { Quick: 0, Heavy: 1, Guard: 2 };
  const order = p.hand.map((n, i) => i).sort((a, b) => R[CARDS[p.hand[a]].kind] - R[CARDS[p.hand[b]].kind] || CARDS[p.hand[a]].n - CARDS[p.hand[b]].n);
  const choosing = !ui.busy && !ui.over;
  return order.map(i => {
    let cls = ui.sel === i ? 'sel' : choosing ? 'ok' : '';
    if (ui.fresh.has(i)) cls += ' drawn';
    return cardHTML(p.hand[i], { cls, attrs: `data-i="${i}"${choosing ? '' : ' disabled'}` });
  }).join('');
}
function trackerHTML(side) {
  return deckSummary(ui.view, side).map(r => {
    const c = CARDS[r.id], left = side === ME ? r.inDeck : r.unseen;
    const tk = c.kind === 'Quick' ? 'Strike' : c.kind === 'Heavy' ? 'Sword' : 'Guard';
    return `<div class="trow ${tk}${left ? '' : ' gone'}"><span class="tn">${label(r.id)}</span><span class="tc">×${left}</span></div>`;
  }).join('');
}

function render() {
  document.body.classList.add('playing');
  const s = ui.view;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  $('hero1').innerHTML = heroHTML(BOT);
  $('hero0').innerHTML = heroHTML(ME);
  $('wind1').innerHTML = lineHTML(BOT);
  $('wind0').innerHTML = lineHTML(ME);
  $('hand').innerHTML = handHTML();
  const ready = !ui.busy && !ui.over && ui.sel !== null;
  $('turnbox').innerHTML = `<button id="go" class="${ready ? 'ready' : ''}"${ready ? '' : ' disabled'}>Go</button>`;
  $('history').innerHTML = ui.hist.slice(-18).map(h => h.sep ? `<div class="hist sep"></div>`
    : `<div class="hist s${h.side}" data-card="${h.card}"><span class="hn">${label(h.card)}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`).join('');
  $('trk1').innerHTML = trackerHTML(BOT);
  $('trk0').innerHTML = trackerHTML(ME);
  ui.fresh.clear();
}

function centerOf(el) {
  const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect();
  return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 };
}
function floatAt(el, text, cls) {
  if (!el) return;
  const c = centerOf(el), f = document.createElement('div');
  f.className = 'float ' + cls; f.textContent = text;
  f.style.left = c.x + 'px'; f.style.top = c.y + 'px';
  $('game').appendChild(f);
  setTimeout(() => f.remove(), 1200);
}
function shake(side) { const el = $('plate' + side); if (!el) return; el.classList.remove('shake'); void el.offsetWidth; el.classList.add('shake'); }

const HOW = {
  interrupt: ['', ''], hit: ['', ''], counter: ['', ''], break: ['', ''],
  interrupted: ['Interrupted', 'warn'], blocked: ['Blocked', 'block'], broken: ['Broken', 'warn'], idle: ['', ''],
};

async function playRound(prev, next, ev) {
  const cards = [null, null];
  for (const e of ev) if (e.t === 'reveal') cards[e.side] = e.cards[0];
  ui.lines = [[cards[0]], [cards[1]]]; ui.marks = [{}, {}];
  ui.view = { ...prev, p: prev.p.map((p, i) => ({ ...p, hand: p.hand.filter((id, k) => i === ME ? true : k < p.hand.length - 1) })) };
  const mh = prev.p[ME].hand.slice(); mh.splice(mh.indexOf(cards[0]), 1); ui.view.p[ME].hand = mh;
  render();
  await wait(800);
  const clashes = ev.filter(e => e.t === 'clash');
  for (const c of clashes) { const [txt, cls] = HOW[c.how]; if (cls) ui.marks[c.side][c.card] = 'lost'; }
  for (const c of clashes) if (c.dmg) ui.shown.hp[1 - c.side] -= c.dmg;
  render();
  for (const c of clashes) {
    const [txt, cls] = HOW[c.how];
    const cardEl = $(c.side === ME ? 'wind0' : 'wind1').querySelector('.card');
    if (txt) floatAt(cardEl, txt, cls);
    if (c.dmg) { floatAt($('plate' + (1 - c.side)), '−' + c.dmg, 'dmg'); shake(1 - c.side); }
    ui.hist.push({ side: c.side, card: c.card, out: c.dmg ? '−' + c.dmg : txt.toLowerCase(), cls: c.dmg ? 'dmg' : cls });
  }
  ui.hist.push({ sep: true });
  render();
  await wait(1300);
  ui.lines = [[], []];
  ui.view = next; ui.shown.hp = [next.p[0].hp, next.p[1].hp];
  if (next.winner === null) ui.fresh.add(next.p[ME].hand.length - 1);
  render();
}

function finish() {
  ui.over = true;
  const w = ui.s.winner;
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><div class="row"><button id="rematch">Play again</button></div>`;
  $('over').classList.add('show');
}

async function go() {
  if (ui.busy || ui.over || ui.sel === null) return;
  const tok = ui.token;
  const mine = [ui.s.p[ME].hand[ui.sel]];
  ui.busy = true; ui.sel = null; render();
  await wait(30);
  const his = botChoose(ui.s, BOT, ui.rng);
  const prev = ui.s, ev = [];
  const next = commit(prev, [mine, his], ev);
  ui.s = next;
  await playRound(prev, next, ev);
  if (tok !== ui.token) return;
  if (next.winner !== null) finish();
  ui.busy = false; render();
}

function startMatch() {
  ui.token++;
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0 });
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = null; ui.lines = [[], []]; ui.busy = false;
  ui.shown.hp = [ui.s.p[0].hp, ui.s.p[1].hp];
  $('over').classList.remove('show');
  render();
}

function peek(e) {
  const h = e.target.closest && e.target.closest('.hist[data-card]');
  const box = $('peek');
  if (!h || !CARDS[h.dataset.card]) { box.innerHTML = ''; return; }
  const g = $('game').getBoundingClientRect(), r = h.getBoundingClientRect();
  box.innerHTML = cardHTML(h.dataset.card);
  box.style.left = (r.right - g.left + 12) + 'px';
  box.style.top = Math.max(8, Math.min(r.top - g.top - 60, g.height - 250)) + 'px';
}
document.addEventListener('mouseover', peek);
document.addEventListener('mouseout', (e) => { if (!e.relatedTarget || !e.relatedTarget.closest || !e.relatedTarget.closest('.hist')) $('peek').innerHTML = ''; });
document.addEventListener('click', (e) => {
  const t = e.target.closest('button');
  if (!t || t.disabled) return;
  if (t.dataset.i !== undefined) { const i = +t.dataset.i; ui.sel = ui.sel === i ? null : i; render(); return; }
  switch (t.id) {
    case 'rematch': case 'newmatch': startMatch(); return;
    case 'go': go(); return;
  }
});
startMatch();
