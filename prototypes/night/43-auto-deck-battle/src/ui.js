// Auto deck battle as a game screen against Expert. You shop (buy, reroll, remove) while the
// bot shops in secret; then the battle plays itself out step by step in the middle: the two front
// cards strike each other, fallen cards leave, the next card steps up.

import { CARDS, GOLD, ROUNDS, REROLL, REMOVE, newMatch, act, isLegal } from './engine.js';
import { makeRng, expertBot, EXPERT } from './bot.js';

const ME = 0, BOT = 1, TALLY_KEY = 'night-43-tally';
const expert = expertBot(EXPERT);
const ui = { s: null, busy: false, over: false, removing: false, fresh: new Set(), arena: null, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0 };
const $ = (id) => document.getElementById(id);
const FAST = /fast/.test(location.hash), wait = (ms) => new Promise(r => setTimeout(r, FAST ? 0 : ms));
const botMs = (window.__botMs = { max: 0, n: 0 });

function loadTally() { try { const t = JSON.parse(localStorage.getItem(TALLY_KEY)); if (Array.isArray(t) && t.length === 2) return t; } catch (e) {} return [0, 0]; }
function saveTally(t) { try { localStorage.setItem(TALLY_KEY, JSON.stringify(t)); } catch (e) {} }

function cardHTML(id, side, { cls = '', attrs = '', atk, hp } = {}) {
  const c = CARDS[id], a = atk ?? c.atk, h = hp ?? c.hp;
  const tx = c.text ? `<div class="tx">${c.text}</div>` : '';
  return `<button class="card s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art"><span class="stat a${a > c.atk ? ' up' : ''}">${a}</span><span class="stat h${h < c.hp ? ' hurt' : h > c.hp ? ' up' : ''}">${h}</span></div><div class="nm">${c.name}</div>${tx}</button>`;
}
const myShop = () => !ui.busy && !ui.over && ui.s.phase === 'shop' && ui.s.toMove === ME;

// ------------------------------------------------------------------ rendering
// a deck as one tile per kind with a count; mine shows this round's buys, his the deck he showed
function deckHTML(side) {
  const p = ui.s.p[side], list = side === ME ? p.deck : p.shown;
  const ids = [...new Set(list)].sort((a, b) => CARDS[a].cost - CARDS[b].cost || (a < b ? -1 : 1));
  return ids.map(id => {
    const c = CARDS[id], n = list.filter(x => x === id).length;
    const rm = side === ME && ui.removing && isLegal(ui.s, { t: 'remove', card: id });
    return `<button class="dk${rm ? ' rm' : ''}${side === ME && ui.fresh.has(id) ? ' new' : ''}" data-rm="${rm ? id : ''}"${rm ? '' : ' disabled'}><span class="nm">${c.name}</span><span class="st">${c.atk}/${c.hp}</span>${n > 1 ? `<i class="n">${n}</i>` : ''}</button>`;
  }).join('');
}
function laneHTML(side) {
  const A = ui.arena;
  if (!A) return '';
  const f = A.front[side], q = `<div class="queue">${A.left[side] ? '<i></i>' + A.left[side] : ''}</div>`;
  return (side === BOT ? '' : q) + (f ? cardHTML(f.id, side, { atk: f.atk, hp: f.hp, cls: A.fx[side] || '', attrs: `id="front${side}" disabled` }) : '<div class="card" style="visibility:hidden"></div>') + (side === BOT ? q : '');
}
function render() {
  const s = ui.s, t = loadTally(), P = s.p[ME];
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  let pips = '';
  for (let r = 1; r <= ROUNDS; r++) pips += `<i class="pip${r < s.round ? ' done' : r === s.round ? ' now' : ''}"></i>`;
  $('rounds').innerHTML = pips;
  for (const side of [0, 1]) { $('life' + side).textContent = ui.arena ? ui.arena.life[side] : s.p[side].life; $('deck' + side).innerHTML = deckHTML(side); $('lane' + side).innerHTML = laneHTML(side); }
  $('result').innerHTML = ui.arena && ui.arena.result ? ui.arena.result : '';
  const shopping = myShop();
  let coins = ''; for (let i = 0; i < GOLD; i++) coins += `<i class="${i < P.gold ? '' : 'off'}"></i>`;
  $('gold').innerHTML = (shopping || ui.busy) && !ui.arena ? `<span class="g">${P.gold}</span><span class="coins">${coins}</span>` : '';
  // while a battle plays, the next round's shop stays hidden
  $('shop').innerHTML = ui.arena ? '' : P.shop.map((id, i) => {
    if (!id) return '<div class="slot"></div>';
    const ok = shopping && !ui.removing && isLegal(s, { t: 'buy', i });
    return cardHTML(id, ME, { cls: ok ? 'ok' : 'no', attrs: `data-buy="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
  const canRm = shopping && !P.removed && P.gold >= REMOVE;
  $('tools').innerHTML = `<button id="reroll"${shopping && P.gold >= REROLL && !ui.removing ? '' : ' disabled'}>Reroll <span class="c">${REROLL}</span></button>`
    + `<button id="remove" class="${ui.removing ? 'on' : ''}"${canRm ? '' : ' disabled'}>Remove <span class="c">${REMOVE}</span></button>`
    + `<button id="fight"${shopping ? '' : ' disabled'}>Fight</button>`;
}
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function floatOn(el, text, cls = '') {
  if (!el) return;
  const g = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(), f = document.createElement('div');
  f.className = 'float ' + cls; f.textContent = text; f.style.left = (r.left - g.left + r.width / 2) + 'px'; f.style.top = (r.top - g.top + r.height / 2) + 'px';
  $('game').appendChild(f); setTimeout(() => f.remove(), 1000);
}

// ------------------------------------------------------------------ the battle, replayed from its log
async function playBattle(log, prevLives) {
  const A = ui.arena = { front: [null, null], left: [log.decks[0].length, log.decks[1].length], fx: {}, life: prevLives.slice(), result: '' };
  const qtok = ui.token;
  render(); await wait(500);
  for (const e of log.steps) {
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    A.fx = {};
    if (e.t === 'enter') { A.front[e.side] = { id: e.card, atk: CARDS[e.card].atk, hp: CARDS[e.card].hp }; A.left[e.side] = e.left; render(); await wait(260); continue; }
    if (e.t === 'clash') {
      A.fx = { 0: 'strike', 1: 'strike' }; render(); await wait(150);
      A.front[0].hp = e.hp[0]; A.front[1].hp = e.hp[1]; A.fx = { 0: e.n[1] ? 'hit' : '', 1: e.n[0] ? 'hit' : '' }; render();
      if (e.n[1]) floatOn($('front0'), '−' + e.n[1]); if (e.n[0]) floatOn($('front1'), '−' + e.n[0]);
      await wait(320); continue;
    }
    if (e.t === 'fall') { A.fx = { [e.side]: 'fall' }; render(); await wait(300); A.front[e.side] = null; render(); continue; }
    if (e.t === 'bomb' || e.t === 'open') { const k = 1 - e.side; if (A.front[k]) { A.front[k].hp = e.hp; A.fx = { [k]: 'hit' }; render(); floatOn($('front' + k), '−' + e.n); } await wait(320); continue; }
    if (e.t === 'rally') { const m = A.front[e.side]; if (m) { m.atk = e.atk; m.hp = e.hp; render(); floatOn($('front' + e.side), '+2/+2', 'buff'); } await wait(320); continue; }
    if (e.t === 'result') {
      if (e.winner !== null) { A.life[1 - e.winner] -= e.dmg; A.result = `<span class="w${e.winner}">−${e.dmg}</span>`; render(); floatOn($('life' + (1 - e.winner)), '−' + e.dmg); }
      else { A.result = '='; render(); }
      await wait(1200);
    }
  }
}

// ------------------------------------------------------------------ flow
async function apply(a) {
  const qtok = ui.token;
  const prev = ui.s, ev = [];
  const next = act(prev, a, ev);
  if (prev.toMove === ME && a.t === 'buy') ui.fresh.add(prev.p[ME].shop[a.i]);
  ui.s = next;
  const b = ev.find(e => e.t === 'battle');
  if (b) {
    ui.busy = true;
    await playBattle(b, [prev.p[0].life, prev.p[1].life]);
    if (qtok !== ui.token) return new Promise(() => {}); // a new game started meanwhile
    ui.arena = null; ui.fresh = new Set();
    if (next.winner !== null) return finish();
    banner('Round ' + next.round);
  }
  render();
}
function finish() {
  if (ui.over) return;
  ui.over = true; render();
  const w = ui.s.winner;
  if (w === 0 || w === 1) { const t = loadTally(); t[w]++; saveTally(t); }
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><button id="rematch">Play again</button>`;
  $('over').classList.add('show');
}
async function startMatch() {
  const tok = ++ui.token;
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0 });
  ui.over = false; ui.removing = false; ui.arena = null; ui.fresh = new Set();
  $('over').classList.remove('show');
  ui.busy = false; render();
  banner('Round 1');

}
// you shop as seat 0; when you press Fight the bot shops (in secret) and the battle follows
async function doAct(a) {
  if (!myShop() || !isLegal(ui.s, a)) return;
  const tok = ui.token;
  ui.busy = true; ui.removing = false;
  await apply(a);
  if (tok !== ui.token) return;
  while (!ui.over && ui.s.toMove === BOT && ui.s.phase === 'shop') {
    const t0 = performance.now(), b = expert(ui.s, ui.rng), dt = performance.now() - t0;
    botMs.n++; if (dt > botMs.max) botMs.max = dt;
    await apply(b);
    if (tok !== ui.token) return;
  }
  ui.busy = false; render();
}

document.addEventListener('click', (e) => {
  const b = e.target.closest('button');
  if (b && (b.id === 'rematch' || b.id === 'newmatch')) return startMatch();
  if (b && b.id === 'rulesbtn') { $('rules').classList.toggle('show'); return; }
  if (e.target.closest('#rules')) { $('rules').classList.remove('show'); return; }
  if (!b || b.disabled || !myShop()) return;
  if (b.dataset.buy !== undefined) return doAct({ t: 'buy', i: +b.dataset.buy });
  if (b.dataset.rm) return doAct({ t: 'remove', card: b.dataset.rm });
  if (b.id === 'reroll') return doAct({ t: 'reroll' });
  if (b.id === 'remove') { ui.removing = !ui.removing; render(); return; }
  if (b.id === 'fight') return doAct({ t: 'done' });
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { ui.removing = false; $('rules').classList.remove('show'); render(); } });
startMatch();

