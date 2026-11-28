// Engine war as a game screen against the Expert. Your whole hand plays itself at the start of your
// turn; you buy from the row and shoot enemy Posts. The bot's turn plays out one action at a time;
// the win tally is kept in this browser and decides who goes first (alternating).

import { CARDS, TARGET, newMatch, act, legalActions } from './engine.js';
import { makeRng, mcExpert, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-10-engine-war-tally';
const expert = mcExpert({ ...EXPERT, timeMs: 900, minPlayouts: 300 });
const ui = { s: null, view: null, busy: false, over: false, hist: [], fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function face(id) {
  const c = CARDS[id];
  if (c.post) return `<div class="art post${c.wall ? ' wall' : ''}"><span class="hp">${c.hp}</span><span class="yl">${c.yld ? '+' + c.yld : '0'}</span></div>`;
  if (c.trash) return `<div class="art trash"><span class="big">✕</span></div>`;
  if (c.draw) return `<div class="art coin"><span class="big sm">+${c.coin}</span><span class="dr">+${c.draw}</span></div>`;
  if (c.coin) return `<div class="art coin"><span class="big">+${c.coin}</span></div>`;
  return `<div class="art shot"><span class="big">${c.dmg}</span></div>`;
}
function cardHTML(id, { cls = '', attrs = '', cost = true } = {}) {
  return `<button class="card ${cls}" ${attrs}>${cost && CARDS[id].cost ? `<span class="cgem">${CARDS[id].cost}</span>` : ''}${face(id)}<div class="nm">${CARDS[id].name}</div></button>`;
}
const myTurn = () => !ui.busy && !ui.over && ui.view.turn === ME;

function postsHTML(side, legal) {
  return ui.view.p[side].posts.map((x, i) => {
    const c = CARDS[x.card], tg = side === BOT && legal.some(a => a.t === 'shoot' && a.i === i);
    return `<div class="tpost s${side}${c.wall ? ' wall' : ''}${tg ? ' tgt' : ''}${ui.fx['x' + x.uid] ? ' ' + ui.fx['x' + x.uid] : ''}" id="x${x.uid}" data-post="${i}"><span class="hp">${c.hp}</span><span class="yl">${c.yld ? '+' + c.yld : '0'}</span></div>`;
  }).join('');
}
function scoreHTML(side) {
  const p = ui.view.p[side], f = Math.min(1, p.points / TARGET);
  return `<div class="score s${side}${ui.fx['score' + side] ? ' bump' : ''}" id="score${side}" style="--f:${f}"><span class="pts">${p.points}</span><span class="of">${TARGET}</span></div>`;
}
function pilesHTML(side) {
  const p = ui.view.p[side];
  return `<div class="pile s${side}" title="">${p.deck.length}</div><div class="pile disc s${side}" id="disc${side}">${p.discard.length}</div>`;
}
function poolsHTML(side) {
  const p = ui.view.p[side], on = ui.view.turn === side;
  return `<span class="pool coin${on ? '' : ' off'}">${on ? p.coin : 0}</span><span class="pool dmg${on ? '' : ' off'}">${on ? p.dmg : 0}</span>`;
}
function render() {
  const s = ui.view, t = loadTally(), legal = myTurn() ? legalActions(s) : [];
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  for (const side of [0, 1]) {
    $('score' + side + 'w').innerHTML = scoreHTML(side);
    $('posts' + side).innerHTML = postsHTML(side, legal);
    $('piles' + side).innerHTML = pilesHTML(side);
    $('pools' + side).innerHTML = poolsHTML(side);
  }
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  $('oppplayed').innerHTML = s.turn === BOT ? s.p[BOT].played.map(id => cardHTML(id, { cls: 'mini', cost: false })).join('') : '';
  $('row').innerHTML = s.row.map((id, i) => {
    if (!id) return '<div class="card empty"></div>';
    const ok = legal.some(a => a.t === 'buy' && a.i === i);
    return cardHTML(id, { cls: (ok ? 'ok' : myTurn() ? 'no' : '') + (ui.fx['row' + i] ? ' ' + ui.fx['row' + i] : ''), attrs: `data-buy="${i}" id="row${i}"${ok ? '' : ' disabled'}` });
  }).join('') + `<div class="pile market">${s.mdeck.length}</div>`;
  const P = s.p[ME];
  $('mine').innerHTML = (s.turn === ME ? P.played : P.hand).map(id => cardHTML(id, { cls: 'mini' + (s.turn === ME ? ' used' : ''), cost: false })).join('');
  const trash = myTurn() && P.trash > 0;
  $('trash').classList.toggle('show', trash);
  if (trash) {
    $('trashopts').innerHTML = legal.filter(a => a.card).map(a => cardHTML(a.card, { cls: 'ok ' + a.from, attrs: `data-trash="${a.from}:${a.card}"`, cost: false })).join('');
  }
  const mine = !ui.over && s.turn === ME, left = mine && !ui.busy && legal.some(a => a.t === 'buy' || a.t === 'shoot');
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !left ? 'done' : ''}"${mine && !ui.busy && !trash ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(h => `<div class="hist s${h.side}">${h.card ? cardHTML(h.card, { cls: 'chip', cost: false }) : `<span class="chipx ${h.kind}">${h.chip || ''}</span>`}<span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`).join('');
  ui.fx = {};
}

function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
async function flyTo(el, toEl) {
  if (!el || !toEl) return;
  const g = $('game').getBoundingClientRect(), a = el.getBoundingClientRect(), b = toEl.getBoundingClientRect(), d = document.createElement('div');
  d.className = 'flyer'; d.innerHTML = el.outerHTML; d.style.left = (a.left - g.left) + 'px'; d.style.top = (a.top - g.top) + 'px';
  $('game').appendChild(d);
  await d.animate([{ transform: 'translate(0,0) scale(1)', opacity: 1 }, { transform: `translate(${b.left - a.left}px, ${b.top - a.top}px) scale(.35)`, opacity: .3 }], { duration: 420, easing: 'ease-in' }).finished;
  d.remove();
}
function ghost(el) {
  if (!el) return;
  const g = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = el.outerHTML; d.style.left = (r.left - g.left) + 'px'; d.style.top = (r.top - g.top) + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 500);
}

async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  ui.s = next;
  const buy = ev.find(e => e.t === 'buy'), shot = ev.find(e => e.t === 'shoot'), tr = ev.find(e => e.t === 'trash');
  if (buy) await flyTo($('row' + buy.i), $('disc' + buy.side));
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (shot) { const el = $('x' + shot.uid); if (el) { floatAt(centerOf(el), '✕'); ghost(el); } }
  for (const e of ev) {
    if (e.t === 'turn' && e.side === ME) banner('Your turn');
    if (e.t === 'yield') ui.fx['score' + e.side] = 1;
    if (e.t === 'post') ui.fx['x' + e.uid] = 'new';
    if (e.t === 'buy') ui.fx['row' + e.i] = 'new';
  }
  ui.view = next; render();
  for (const e of ev) if (e.t === 'yield') { const el = $('score' + e.side); if (el) floatAt(centerOf(el), '+' + e.n, 'plus'); }
  if (buy) ui.hist.push({ side: buy.side, card: buy.card });
  if (shot) ui.hist.push({ side: shot.side, kind: 'shot', chip: CARDS[shot.card].hp, out: '✕', cls: 'kill' });
  if (tr) ui.hist.push({ side: tr.side, kind: 'trash', chip: '✕', out: CARDS[tr.card].name });
  for (const e of ev) if (e.t === 'yield') ui.hist.push({ side: e.side, kind: 'yield', chip: '+' + e.n, out: '' });
  if (ev.some(e => e.t === 'turn')) await wait(next.turn === ME ? 600 : 500);
  if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
  if (next.winner !== null) finish(ev.find(e => e.t === 'end'));
  render();
}
function finish(e) {
  if (ui.over) return;
  ui.over = true;
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><p class="sub">${ui.s.p[ME].points} – ${ui.s.p[BOT].points}</p><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}

async function startMatch() {
  const tok = ++ui.token, t = loadTally();
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT });
  ui.view = ui.s; ui.over = false; ui.hist = [];
  $('over').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(800);
  if (tok !== ui.token) return;
  if (ui.s.turn === BOT) await botMove(tok); else { ui.busy = false; render(); }
}
async function botMove(tok) {
  ui.busy = true; render();
  await wait(700);
  for (let k = 0; k < 60; k++) {
    if (tok !== ui.token || ui.over || ui.s.turn !== BOT) return;
    const a = expert(ui.s, ui.rng);
    await wait(a.t === 'end' ? 400 : 300);
    if (tok !== ui.token || ui.over) return;
    await apply(a);
    if (a.t === 'end') break;
  }
  if (tok !== ui.token || ui.over) return;
  ui.busy = false; render();
}
async function doAct(a) { if (!myTurn()) return; ui.busy = true; await apply(a); ui.busy = false; render(); }
async function myEndTurn() {
  if (!myTurn()) return;
  const tok = ui.token;
  ui.busy = true; render();
  await apply({ t: 'end' });
  if (tok !== ui.token || ui.over) return;
  await botMove(tok);
}

document.addEventListener('click', (e) => {
  if (e.target.closest('#rules')) { if (e.target.closest('#closerules')) $('rules').classList.remove('show'); return; }
  const post = e.target.closest('.tpost.tgt');
  if (post && myTurn()) return doAct({ t: 'shoot', i: +post.dataset.post });
  const b = e.target.closest('button');
  if (!b || b.disabled) return;
  if (b.dataset.buy !== undefined) return doAct({ t: 'buy', i: +b.dataset.buy });
  if (b.dataset.trash) { const [from, card] = b.dataset.trash.split(':'); return doAct({ t: 'trash', from, card }); }
  if (b.id === 'keep') return doAct({ t: 'trash', card: null });
  if (b.id === 'rematch' || b.id === 'newmatch') return startMatch();
  if (b.id === 'endturn') return myEndTurn();
  if (b.id === 'openrules') $('rules').classList.add('show');
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') $('rules').classList.remove('show'); });
startMatch();
