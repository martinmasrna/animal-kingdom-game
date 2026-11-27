// Hero HS as a game screen against the play-out Expert: a start screen to pick both heroes and
// build your deck, then Vanilla HS's board with energy bars, hero powers and both deck lists.
// Each action is animated from the state before and the state after.

import { CARDS, POOL, HEROES, HERO_IDS, DEFAULT_DECKS, MAX_MANA, WIN, START, DECK_SIZE, COPIES, FIRE, newMatch, act, endTurn, legalActions, targetKind } from './engine.js';
import { makeRng, rolloutBot } from './bot.js';

const ME = 0, BOT = 1, KEY = 'hero-hs-1';
const expert = rolloutBot();
const ui = { s: null, view: null, busy: false, over: false, sel: null, hist: [], fresh: 0, fx: {}, rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0, lists: null };
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

// ------------------------------------------------------------------ what this browser remembers
function load() { try { const v = JSON.parse(localStorage.getItem(KEY)); if (v && typeof v === 'object') return v; } catch (e) {} return {}; }
function save(v) { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} }
const store = load();
const setup = {
  me: HERO_IDS.includes(store.me) ? store.me : 'P',
  opp: HERO_IDS.includes(store.opp) || store.opp === '?' ? store.opp : '?',
  decks: Object.fromEntries(HERO_IDS.map(h => [h, store.decks && Array.isArray(store.decks[h]) && store.decks[h].every(id => POOL.some(c => c.id === id)) ? store.decks[h].slice(0, DECK_SIZE) : DEFAULT_DECKS[h].slice()])),
};
const tallies = store.tally && typeof store.tally === 'object' ? store.tally : {};
const remember = () => save({ me: setup.me, opp: setup.opp, decks: setup.decks, tally: tallies });

// ------------------------------------------------------------------ cards
const FIRE_NAMES = ['Baby', 'Young', 'Adult', 'Elder'];
function text(c) {
  if (c.kind === 'Coin') return 'Gain 1 mana this turn.';
  if (c.id === 'HP') return 'Played: upgrade your Fireballs.';
  if (c.id === 'HA') return 'Turn start: your other minions +1/+1.';
  if (c.id === 'HM') return 'Deck empty: becomes 8/8, played: gain 10.';
  const t = [];
  if (c.taunt) t.push('<b>Taunt</b>');
  if (c.rush) t.push('Attacks at once.');
  if (c.bc && c.bc.draw) t.push('Played: draw a card.');
  if (c.bc && c.bc.dmg) t.push(`Played: deal ${c.bc.dmg}.`);
  if (c.bc && c.bc.gain) t.push(`Played: gain ${c.bc.gain}.`);
  if (c.dies) t.push('Dies: draw a card.');
  if (c.eot) t.push(`Turn end: gain ${c.eot.gain}.`);
  if (c.sot) t.push('Turn start: +1 attack.');
  if (c.kind === 'Spell') {
    if (c.dmg) t.push(`Deal ${c.dmg}.`);
    if (c.area) t.push(`Deal ${c.area} to all enemy minions.`);
    if (c.draw) t.push(`Draw ${c.draw}.`);
    if (c.destroy) t.push('Destroy a minion.');
    if (c.buff) t.push(`Give a minion +${c.buff}/+${c.buff}.`);
    if (c.gain) t.push(`Gain ${c.gain}.`);
  }
  return t.join(' ');
}
// a few characters for the deck lists and the history
function short(c) {
  if (c.kind === 'Minion') return `${c.atk}/${c.hp}` + (c.taunt ? ' Taunt' : c.rush ? ' at once' : c.bc && c.bc.draw ? ' draw' : c.dies ? ' dies: draw' : c.bc && c.bc.dmg ? ' deal ' + c.bc.dmg : c.bc && c.bc.gain ? ' gain ' + c.bc.gain : c.eot ? ' gain 1/turn' : c.sot ? ' grows' : '');
  if (c.dmg) return `Deal ${c.dmg}`;
  if (c.area) return `${c.area} to all`;
  if (c.draw) return `Draw ${c.draw}`;
  if (c.destroy) return 'Destroy';
  if (c.buff) return `+${c.buff}/+${c.buff}`;
  if (c.gain) return `Gain ${c.gain}`;
  return c.id;
}
function spellArt(c) {
  if (c.dmg) return `<span class="big">${c.dmg}</span>`;
  if (c.area) return `<span class="big">${c.area}<small>×all</small></span>`;
  if (c.draw) return `<span class="big">${c.draw}<i class="cardic"></i></span>`;
  if (c.destroy) return `<span class="big">✕</span>`;
  if (c.buff) return `<span class="big">+${c.buff}</span>`;
  if (c.gain) return `<span class="big e">+${c.gain}</span>`;
  return '';
}
function cardHTML(id, side, { cls = '', attrs = '', tag = 'button' } = {}) {
  const c = CARDS[id];
  let art, nm = '', kind = c.kind;
  if (c.kind === 'Minion') art = `<span class="stat a">${c.atk}</span><span class="stat h">${c.hp}</span>${c.taunt ? '<span class="shield"></span>' : ''}`;
  else if (c.kind === 'Spell') { art = spellArt(c); if (c.gain) kind += ' gainc'; }
  else art = `<span class="big">+1</span>`;
  if (c.hero) { nm = HEROES[c.hero].name; kind += ' herocard h' + c.hero; }
  if (c.fire !== undefined) { nm = FIRE_NAMES[c.fire] + ' Fireball'; kind += ' fire'; }
  if (c.kind === 'Coin') nm = 'Coin';
  return `<${tag} class="card ${kind} s${side} ${cls}" ${attrs}><span class="cgem">${c.cost}</span><div class="art">${art}</div>${nm ? `<div class="nm">${nm}</div>` : ''}<div class="tx">${text(c)}</div></${tag}>`;
}
function powerCardHTML(hero, side) {
  const H = HEROES[hero];
  return `<div class="card Power h${hero} s${side}"><span class="cgem">${H.power}</span><div class="art"><span class="big">${powerGlyph(hero, ui.view ? ui.view.p[side] : null)}</span></div><div class="nm">${H.name}</div><div class="tx">${H.active}</div></div>`;
}
const PORTRAIT = { P: '🔥', A: '⚔️', M: '🔮' };
function powerGlyph(hero, p) {
  if (hero === 'P') return FIRE[Math.min(3, Math.floor((p ? p.uses : 0) / 3))].dmg;
  if (hero === 'A') return '+2';
  return '+1';
}

// ------------------------------------------------------------------ what can be done now
const myTurn = () => !ui.busy && !ui.over && ui.view && ui.view.turn === ME;
function targetsNow() {
  const out = { heroes: new Set(), minions: new Set() };
  if (!ui.sel || !myTurn()) return out;
  for (const a of legalActions(ui.view)) {
    let t = null;
    if (ui.sel.kind === 'card' && a.t === 'play' && a.card === ui.sel.id && a.target) t = a.target;
    if (ui.sel.kind === 'power' && a.t === 'power' && a.target) t = a.target;
    if (ui.sel.kind === 'minion' && a.t === 'attack' && a.from === ui.sel.i) t = { side: BOT, i: a.to };
    if (t) { if (t.i < 0) out.heroes.add(t.side); else out.minions.add(t.side + ':' + t.i); }
  }
  return out;
}
const canAttack = (i) => myTurn() && legalActions(ui.view).some(a => a.t === 'attack' && a.from === i);
const canPower = () => myTurn() && legalActions(ui.view).some(a => a.t === 'power');

// ------------------------------------------------------------------ rendering the match
function energyHTML(side) {
  const e = ui.view.p[side].energy, x = Math.max(0, Math.min(WIN, e)) / WIN * 100;
  const zone = e <= 8 ? ' low' : e >= WIN - 8 ? ' high' : '';
  return `<div class="ebar${zone}" id="ebar${side}"><span class="end lo">0</span><div class="track"><div class="fill" style="width:${x}%"></div><span class="start" style="left:${START / WIN * 100}%"></span><span class="knob" style="left:${x}%">${e}</span></div><span class="end hi">${WIN}</span></div>`;
}
function heroHTML(side, T) {
  const p = ui.view.p[side], H = HEROES[p.hero];
  const pw = side === ME ? canPower() : false, sel = side === ME && ui.sel && ui.sel.kind === 'power';
  let pips = '';
  if (p.hero === 'P') { const n = p.uses >= 9 ? 3 : p.uses % 3; pips = `<span class="pips">${[0, 1, 2].map(k => `<i class="${k < n ? 'on' : ''}"></i>`).join('')}</span>`; }
  const used = p.powered ? ' used' : '';
  const portrait = `<div class="hero h${p.hero} s${side}${T.heroes.has(side) ? ' tgt' : ''} ${ui.fx['hero' + side] || ''}" id="hero${side}x" data-side="${side}" data-i="-1"><span class="face">${PORTRAIT[p.hero]}</span><div class="passive"><b>${H.name}</b>${H.passive}</div></div>`;
  const power = `<button class="power h${p.hero}${used}${pw ? ' ok' : ''}${sel ? ' sel' : ''}" id="power${side}" data-power="${side}"${pw ? '' : ' disabled'}><span class="cgem">${H.power}</span><span class="pg">${powerGlyph(p.hero, p)}</span>${pips}<div class="passive"><b>${H.active}</b></div></button>`;
  return energyHTML(side) + portrait + power;
}
function minionGlyph(c) {
  if (c.hero === 'A') return '<span class="mg gold">✶</span>';
  if (c.eot) return '<span class="mg e">+1</span>';
  if (c.sot) return '<span class="mg">▲</span>';
  if (c.dies) return '<span class="mg">▮</span>';
  return '';
}
function boardHTML(side, T) {
  return ui.view.p[side].board.map((m, i) => {
    const c = CARDS[m.card];
    let cls = '';
    if (side === ME && ui.sel && ui.sel.kind === 'minion' && ui.sel.i === i) cls += ' sel';
    else if (side === ME && !ui.sel && canAttack(i)) cls += ' can';
    if (T.minions.has(side + ':' + i)) cls += ' tgt';
    if (side === ui.view.turn && !m.ready) cls += ' sleep';
    if (c.taunt) cls += ' taunt';
    if (c.hero) cls += ' herocard h' + c.hero;
    if (ui.fx['m' + m.uid]) cls += ' ' + ui.fx['m' + m.uid];
    return `<div class="minion s${side}${cls}" id="m${m.uid}" data-side="${side}" data-i="${i}" data-card="${m.card}">${minionGlyph(c)}<span class="stat a${m.atk > c.atk ? ' up' : ''}">${m.atk}</span><span class="stat h${m.hp < m.max ? ' hurt' : m.max > c.hp ? ' up' : ''}">${m.hp}</span></div>`;
  }).join('');
}
function resHTML(side) {
  const p = ui.view.p[side];
  let gems = '';
  for (let i = 0; i < MAX_MANA; i++) gems += `<i class="gemc${i < p.mana ? ' on' : i < p.maxMana ? '' : ' off'}"></i>`;
  return `<div class="mana"><span class="manatxt">${p.mana}/${p.maxMana}</span>${gems}</div><div class="pile s${side}">${p.deck.length}</div>`;
}
// The deck lists: for me, what is left in my deck; for him, what he has not shown yet (deck and hand).
function trackHTML(side) {
  const p = ui.view.p[side], list = ui.lists[side], n = {}, left = {};
  for (const id of list) n[id] = (n[id] || 0) + 1;
  if (side === ME) for (const id of p.deck) left[id] = (left[id] || 0) + 1;
  else { for (const id in n) left[id] = n[id]; for (const id of p.played) if (left[id]) left[id]--; }
  const ids = Object.keys(n).sort((a, b) => CARDS[a].cost - CARDS[b].cost || short(CARDS[a]).localeCompare(short(CARDS[b])));
  const hc = HEROES[p.hero].card, heroDone = side === ME ? true : !p.hand.includes(hc) && !p.hand.includes('HM8');
  const head = `<div class="trow thero h${p.hero}${heroDone ? ' gone' : ''}"><span class="tg">${CARDS[hc].cost}</span><span class="tn">${HEROES[p.hero].name}</span></div>`;
  return `<div class="tlist s${side}">` + (side === ME ? '' : head) + ids.map(id => {
    const c = CARDS[id], k = left[id] || 0;
    return `<div class="trow ${c.kind}${k ? '' : ' gone'}" data-card="${id}"><span class="tg">${c.cost}</span><span class="tn">${short(c)}</span><span class="tk">${k > 1 ? '×' + k : ''}</span></div>`;
  }).join('') + '</div>';
}
function handHTML() {
  const p = ui.view.p[ME], legal = myTurn() ? legalActions(ui.view) : [];
  const R = { Coin: 0, Minion: 1, Spell: 2 };
  const order = p.hand.map((_, i) => i).sort((a, b) => {
    const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]];
    return (B.hero ? 1 : 0) - (A.hero ? 1 : 0) || R[A.kind] - R[B.kind] || A.cost - B.cost;
  });
  return order.map(i => {
    const id = p.hand[i], ok = legal.some(a => a.t === 'play' && a.card === id);
    let cls = ok ? 'ok' : (myTurn() ? 'no' : '');
    if (ok && ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i) cls += ' sel';
    if (ui.fresh && i >= p.hand.length - ui.fresh) cls += ' drawn';
    return cardHTML(id, ME, { cls, attrs: `data-hand="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}
function histHTML(h) { return `<div class="hist s${h.side}">${h.chip}<span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`; }
function oppHandHTML() {
  return ui.view.p[BOT].hand.map(id => {
    const c = CARDS[id];
    if (c.hero) return `<i class="back herob h${c.hero}"></i>`;
    if (c.fire !== undefined) return `<i class="back fireb">${c.dmg}</i>`;
    if (c.kind === 'Coin') return `<i class="back coinb"></i>`;
    return '<i class="back"></i>';
  }).join('');
}
function render() {
  if (!ui.view) return;
  const s = ui.view, T = targetsNow();
  const t = tallies[pairKey()] || [0, 0];
  $('tally').innerHTML = `<span class="tally"><b class="t0">${t[0]}</b><b class="t1">${t[1]}</b></span>`;
  $('opphand').innerHTML = oppHandHTML();
  for (const side of [0, 1]) { $('hero' + side).innerHTML = heroHTML(side, T); $('board' + side).innerHTML = boardHTML(side, T); $('res' + side).innerHTML = resHTML(side); $('track' + side).innerHTML = trackHTML(side); }
  const hand = $('hand'); hand.innerHTML = handHTML();
  hand.style.setProperty('--squeeze', Math.max(0, s.p[ME].hand.length - 10) * 9 + 'px');
  const mine = !ui.over && s.turn === ME, canAct = mine && !ui.busy && legalActions(s).some(a => a.t === 'attack' || a.t === 'power' || (a.t === 'play' && !(a.target && a.target.side === ME && !CARDS[a.card].buff)));
  $('turnbox').innerHTML = `<button id="endturn" class="${mine && !canAct ? 'done' : ''}"${mine && !ui.busy ? '' : ' disabled'}>End turn</button>`;
  $('history').innerHTML = ui.hist.slice(-15).map(histHTML).join('');
  ui.fresh = 0; ui.fx = {};
}

// ------------------------------------------------------------------ effects
function centerOf(el) { const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect(); return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 }; }
function floatAt(p, text, cls = '') { const f = document.createElement('div'); f.className = 'float ' + cls; f.textContent = text; f.style.left = p.x + 'px'; f.style.top = p.y + 'px'; $('game').appendChild(f); setTimeout(() => f.remove(), 1200); }
function banner(text) { const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show'); }
function snapshot() { const out = {}; document.querySelectorAll('.minion, .hero').forEach(el => { out[el.id] = { c: centerOf(el), html: el.outerHTML, rect: el.getBoundingClientRect() }; }); return out; }
async function spotlight(html) {
  const g = $('game').getBoundingClientRect(), b = $('board1').getBoundingClientRect();
  $('spot').style.left = (b.left - g.left + b.width / 2) + 'px'; $('spot').style.top = (b.bottom - g.top) + 'px';
  $('spot').innerHTML = html;
  await wait(750);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(180); $('spot').innerHTML = '';
}
async function lunge(fromEl, toEl) {
  if (!fromEl || !toEl) return;
  const a = fromEl.getBoundingClientRect(), b = toEl.getBoundingClientRect();
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2), dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  fromEl.style.zIndex = 10;
  await fromEl.animate([{ transform: 'translate(0,0)' }, { transform: `translate(${dx * .8}px, ${dy * .8}px)`, offset: .55 }, { transform: 'translate(0,0)' }], { duration: 420, easing: 'ease-in-out' }).finished;
}
function ghost(snap) {
  const g = $('game').getBoundingClientRect(), d = document.createElement('div');
  d.className = 'ghost'; d.innerHTML = snap.html; d.style.left = (snap.rect.left - g.left) + 'px'; d.style.top = (snap.rect.top - g.top) + 'px';
  $('game').appendChild(d); setTimeout(() => d.remove(), 500);
}
function chipFor(card, side) {
  const c = CARDS[card];
  if (c.kind === 'Coin') return '<span class="chip Coin"></span>';
  if (c.kind === 'Minion') return `<span class="chip Minion s${side}${c.hero ? ' herocard h' + c.hero : ''}">${c.atk}/${c.hp}</span>`;
  return `<span class="chip Spell${c.fire !== undefined ? ' fire' : ''}${c.gain ? ' gainc' : ''}">${c.dmg || c.area || (c.draw ? '+' + c.draw : c.destroy ? '✕' : c.buff ? '+' + c.buff : c.gain ? '+' + c.gain : '')}</span>`;
}
function outcome(ev, side) {
  const kills = ev.filter(e => e.t === 'die' && e.side !== side).length;
  const face = ev.filter(e => e.t === 'hit' && e.i < 0 && e.side !== side).reduce((n, e) => n + e.n, 0);
  const gained = ev.filter(e => e.t === 'gain' && e.side === side).reduce((n, e) => n + e.n, 0);
  const parts = [];
  if (kills) parts.push('✕'.repeat(kills));
  if (face) parts.push('−' + face + ' face');
  if (gained) parts.push('+' + gained);
  return { out: parts.join(' '), cls: gained && !face && !kills ? 'gain' : kills ? 'kill' : face ? 'face' : 'dmg' };
}

// ------------------------------------------------------------------ playback
async function apply(fn) {
  const prev = ui.s, ev = [];
  const next = fn(prev, ev);
  ui.s = next;
  const playE = ev.find(e => e.t === 'play'), atkE = ev.find(e => e.t === 'attack'), powE = ev.find(e => e.t === 'power');
  if (playE && (playE.side === BOT || CARDS[playE.card].kind === 'Spell')) await spotlight(cardHTML(playE.card, playE.side, { tag: 'div' }));
  if (powE && powE.side === BOT) await spotlight(powerCardHTML(powE.hero, BOT));
  if (atkE) await lunge($('m' + atkE.uid), atkE.to < 0 ? $('hero' + (1 - atkE.side) + 'x') : $('m' + atkE.tuid));
  const before = snapshot();
  for (const e of ev) {
    if (e.t === 'turn') { ui.sel = null; if (e.side === ME) banner('Your turn'); }
    if (e.t === 'summon') ui.fx['m' + e.uid] = 'new';
    if (e.t === 'buff' || e.t === 'transform') ui.fx['m' + e.uid] = 'buffed';
    if (e.t === 'hit' && e.i >= 0 && e.hp > 0) ui.fx['m' + e.uid] = 'shake';
    if (e.t === 'hit' && e.i < 0) ui.fx['hero' + e.side] = 'shake';
    if ((e.t === 'draw' || e.t === 'fire') && e.side === ME) ui.fresh++;
  }
  ui.view = next; render();
  for (const e of ev) {
    if (e.t === 'hit') { const id = e.i < 0 ? 'hero' + e.side + 'x' : 'm' + e.uid; const p = before[id]; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'die') { const p = before['m' + e.uid]; if (p) ghost(p); }
    if (e.t === 'fatigue') { const p = before['hero' + e.side + 'x']; if (p) floatAt(p.c, '−' + e.n); }
    if (e.t === 'gain') { const p = before['hero' + e.side + 'x']; if (p) floatAt(p.c, '+' + e.n, 'g'); }
  }
  if (playE) ui.hist.push({ side: playE.side, chip: chipFor(playE.card, playE.side), ...outcome(ev, playE.side) });
  if (powE) ui.hist.push({ side: powE.side, chip: `<span class="chip Power h${powE.hero}">${PORTRAIT[powE.hero]}</span>`, ...outcome(ev, powE.side) });
  if (atkE) {
    const atk = prev.p[atkE.side].board[atkE.from].atk, o = outcome(ev, atkE.side);
    ui.hist.push({ side: atkE.side, chip: `<span class="chip Attack s${atkE.side}">${atk}</span>`, out: o.out || '−' + atk, cls: o.cls });
  }
  const eot = ev.filter(e => e.t === 'gain' && !playE && !powE && !atkE);
  if (eot.length) { const n = eot.reduce((k, e) => k + e.n, 0); ui.hist.push({ side: eot[0].side, chip: '<span class="chip Spell gainc">⟳</span>', out: '+' + n, cls: 'gain' }); }
  if (ev.some(e => e.t === 'turn')) await wait(next.turn === ME ? 600 : 250);
  if (next.winner !== null) finish();
  render();
}

function pairKey() { return ui.heroes ? ui.heroes.join('') : ''; }
function finish() {
  if (ui.over) return;
  ui.over = true;
  const w = ui.s.winner, k = pairKey();
  if (w === 0 || w === 1) { const t = tallies[k] || [0, 0]; t[w]++; tallies[k] = t; remember(); }
  const how = w === 'draw' ? '' : ui.s.p[w].energy >= WIN ? `<span class="how e">${WIN}</span>` : `<span class="how">0</span>`;
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2>${how}<div class="obtn"><button id="rematch">Play again</button><button id="todecks2" class="ghostb">Decks</button></div>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token;
  const opp = setup.opp === '?' ? HERO_IDS[Math.floor(Math.random() * 3)] : setup.opp;
  ui.heroes = [setup.me, opp];
  ui.lists = [setup.decks[setup.me].slice(), DEFAULT_DECKS[opp].slice()];
  const t = tallies[pairKey()] || [0, 0];
  ui.s = newMatch({ seed: (Math.random() * 4294967296) >>> 0, first: (t[0] + t[1]) % 2 === 0 ? ME : BOT, heroes: ui.heroes, decks: ui.lists });
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = null;
  $('over').classList.remove('show'); $('start').classList.remove('show');
  ui.busy = true; render();
  if (ui.s.first === ME) banner('Your turn');
  await wait(900);
  if (tok !== ui.token) return;
  if (ui.s.turn === BOT) await botMove(tok); else { ui.busy = false; render(); }
}
async function botMove(tok) {
  ui.busy = true; render();
  await wait(350);
  const acts = expert(ui.s, ui.rng);
  for (const a of acts) {
    if (tok !== ui.token || ui.over) return;
    await wait(250);
    await apply((s, ev) => act(s, a, ev));
  }
  if (tok !== ui.token || ui.over) return;
  await wait(300);
  await apply((s, ev) => endTurn(s, ev));
  if (tok !== ui.token || ui.over) return;
  ui.busy = false; render();
}
async function doAct(a) {
  if (!myTurn()) return;
  ui.busy = true; ui.sel = null;
  await apply((s, ev) => act(s, a, ev));
  ui.busy = false; render();
}
async function myEndTurn() {
  if (!myTurn()) return;
  const tok = ui.token;
  ui.busy = true; ui.sel = null; render();
  await apply((s, ev) => endTurn(s, ev));
  if (tok !== ui.token || ui.over) return;
  await botMove(tok);
}

// ------------------------------------------------------------------ the start screen
function heroTile(h, which) {
  const H = HEROES[h], on = (which === 'me' ? setup.me : setup.opp) === h;
  if (which === 'opp') return `<button class="otile h${h}${on ? ' on' : ''}" data-opp="${h}"><span class="face">${PORTRAIT[h]}</span></button>`;
  return `<button class="htile h${h}${on ? ' on' : ''}" data-me="${h}"><span class="face">${PORTRAIT[h]}</span><span class="hn">${H.name}</span><span class="hcard">${cardHTML(H.card, ME, { tag: 'span' })}</span>
    <span class="hl">${H.passive}</span><span class="hl"><i class="pgem">${H.power}</i>${H.active}</span></button>`;
}
function renderStart() {
  const deck = setup.decks[setup.me], n = {};
  for (const id of deck) n[id] = (n[id] || 0) + 1;
  const pool = POOL.slice().sort((a, b) => a.cost - b.cost || (a.kind === b.kind ? 0 : a.kind === 'Minion' ? -1 : 1));
  const grid = pool.map(c => {
    const k = n[c.id] || 0, full = k >= COPIES;
    return `<div class="slot">${cardHTML(c.id, ME, { cls: (full ? 'full' : '') + (k ? ' indeck' : ''), attrs: `data-add="${c.id}"` })}${k ? `<span class="copies">${'●'.repeat(k)}</span>` : ''}</div>`;
  }).join('');
  const ids = Object.keys(n).sort((a, b) => CARDS[a].cost - CARDS[b].cost || short(CARDS[a]).localeCompare(short(CARDS[b])));
  const hc = HEROES[setup.me].card;
  const list = `<div class="trow thero h${setup.me}"><span class="tg">${CARDS[hc].cost}</span><span class="tn">${HEROES[setup.me].name}</span></div>` +
    ids.map(id => `<button class="trow ${CARDS[id].kind}" data-remove="${id}"><span class="tg">${CARDS[id].cost}</span><span class="tn">${short(CARDS[id])}</span><span class="tk">${n[id] > 1 ? '×' + n[id] : ''}</span></button>`).join('');
  const ok = deck.length === DECK_SIZE;
  $('start').innerHTML = `
    <div class="pick">
      <div class="mine">${HERO_IDS.map(h => heroTile(h, 'me')).join('')}</div>
      <div class="vs">vs</div>
      <div class="theirs">${HERO_IDS.map(h => heroTile(h, 'opp')).join('')}<button class="otile rnd${setup.opp === '?' ? ' on' : ''}" data-opp="?"><span class="face">?</span></button></div>
    </div>
    <div class="build">
      <div class="pool">${grid}</div>
      <div class="decklist">
        <div class="dhead"><span class="count${ok ? ' full' : ''}">${deck.length}/${DECK_SIZE}</span><button id="defdeck" class="ghostb">Default</button></div>
        <div class="tlist s0">${list}</div>
        <button id="play"${ok ? '' : ' disabled'}>Play</button>
      </div>
    </div>`;
}
function showStart() { ++ui.token; ui.over = true; $('over').classList.remove('show'); renderStart(); $('start').classList.add('show'); }

// ------------------------------------------------------------------ input
document.addEventListener('click', (e) => {
  if ($('start').classList.contains('show')) {
    const b = e.target.closest('[data-me], [data-opp], [data-add], [data-remove], button');
    if (!b) return;
    const deck = setup.decks[setup.me];
    if (b.dataset.me) setup.me = b.dataset.me;
    else if (b.dataset.opp) setup.opp = b.dataset.opp;
    else if (b.dataset.add) { const id = b.dataset.add; if (deck.length < DECK_SIZE && deck.filter(x => x === id).length < COPIES) deck.push(id); }
    else if (b.dataset.remove) deck.splice(deck.indexOf(b.dataset.remove), 1);
    else if (b.id === 'defdeck') setup.decks[setup.me] = DEFAULT_DECKS[setup.me].slice();
    else if (b.id === 'play' && !b.disabled) { remember(); startMatch(); return; }
    remember(); renderStart(); return;
  }
  const tgt = e.target.closest('.minion, .hero');
  if (tgt && myTurn()) {
    const side = +tgt.dataset.side, i = +tgt.dataset.i;
    if (ui.sel && tgt.classList.contains('tgt')) {
      if (ui.sel.kind === 'card') return doAct({ t: 'play', card: ui.sel.id, target: { side, i } });
      if (ui.sel.kind === 'power') return doAct({ t: 'power', target: { side, i } });
      return doAct({ t: 'attack', from: ui.sel.i, to: i });
    }
    if (side === ME && i >= 0 && canAttack(i)) { ui.sel = ui.sel && ui.sel.kind === 'minion' && ui.sel.i === i ? null : { kind: 'minion', i }; render(); return; }
  }
  const b = e.target.closest('button');
  if (b && !b.disabled && b.dataset.hand !== undefined && myTurn()) {
    const i = +b.dataset.hand, id = ui.view.p[ME].hand[i], c = CARDS[id];
    if (targetKind(c)) { ui.sel = ui.sel && ui.sel.kind === 'card' && ui.sel.hand === i ? null : { kind: 'card', id, hand: i }; render(); return; }
    return doAct({ t: 'play', card: id });
  }
  if (b && !b.disabled && b.dataset.power === String(ME) && myTurn()) {
    if (HEROES[ui.view.p[ME].hero].target) { ui.sel = ui.sel && ui.sel.kind === 'power' ? null : { kind: 'power' }; render(); return; }
    return doAct({ t: 'power' });
  }
  if (b && !b.disabled) {
    if (b.id === 'rematch') return startMatch();
    if (b.id === 'todecks' || b.id === 'todecks2') return showStart();
    if (b.id === 'endturn') return myEndTurn();
  }
  if (ui.sel) { ui.sel = null; render(); }
});
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && ui.sel) { ui.sel = null; render(); } });
// a minion on the board shows its card while the pointer rests on it
document.addEventListener('mouseover', (e) => {
  const m = e.target.closest('.minion[data-card], .trow[data-card]'), pk = $('peek');
  if (!m || $('start').classList.contains('show')) { pk.innerHTML = ''; return; }
  const g = $('game').getBoundingClientRect(), r = m.getBoundingClientRect();
  const left = m.classList.contains('trow') ? r.left - g.left - 140 : r.right - g.left + 12;
  pk.style.left = left + 'px'; pk.style.top = Math.max(8, Math.min(r.top - g.top - 20, g.height - 220)) + 'px';
  pk.innerHTML = cardHTML(m.dataset.card, +(m.dataset.side || 0), { tag: 'div' });
});
showStart();
