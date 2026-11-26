// Toy 3 as a game screen. Each round: pick cards (they lift), press the button;
// both lines are revealed on the table in speed order and resolve fastest first.
import { CARDS, DECK, MAX_E, newMatch, commit, validSet, strikeDmg, deckSummary } from './engine.js';
import { makeRng, botChoose } from './bot.js';

const ME = 0, BOT = 1;
const ui = {
  s: null, view: null, busy: false, over: false, showDecks: false, sel: [],
  shown: { hp: [0, 0], block: [0, 0], sword: [0, 0], mana: [0, 0] }, lines: [[], []], step: null, done: new Set(),
  hist: [], fresh: new Set(), pop: { sword: [0, 0], guard: [0, 0] },
  rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0,
};
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));
const NAME = { Strike: 'Strike', Guard: 'Guard', Sword: 'Sword' };
const label = (id) => CARDS[id].kind === 'Sword' ? 'Sword' : NAME[CARDS[id].kind] + ' ' + CARDS[id].n;

const ICON = {
  sword: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M14.5 2.5 21.5 2.5 21.5 9.5 10 21l-2-2-2.6 2.6-2.8-2.8L5.2 16.2l-2-2Z" opacity=".95"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2 20 5v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5Z"/></svg>',
};
const shieldSVG = '<svg viewBox="0 0 46 54"><path d="M23 2 43 9v15c0 13-9 22-20 28C12 46 3 37 3 24V9Z" fill="#5f7891" stroke="#fff" stroke-width="3"/></svg>';

// ------------------------------------------------------------------ cards
function cardHTML(id, { cls = '', attrs = '', owner = null } = {}) {
  const c = CARDS[id];
  const spd = `<span class="spd">⏱${c.speed}</span>`;
  if (c.kind === 'Sword') return `<button class="card k-Heavy ${cls}" ${attrs}>
    <span class="cgem">${c.cost}</span>${spd}
    <div class="art"><span class="big">+${c.n}</span>${ICON.sword}</div>
    <div class="nm">Sword</div>
    <div class="tx">Your strikes deal ${c.n} more. Dropped when you're hit.</div></button>`;
  const strike = c.kind === 'Strike';
  const dmg = strike && owner ? c.n + owner.sword : c.n;
  return `<button class="card k-${strike ? 'Light' : 'Defence'} ${cls}" ${attrs}>
    <span class="cgem">${c.cost}</span>${spd}
    <div class="art"><span class="big${dmg > c.n ? ' up' : ''}">${dmg}</span>${strike ? ICON.sword : ICON.shield}</div>
    <div class="nm">${NAME[c.kind]}</div>
    <div class="tx">${strike ? `Deal ${dmg} damage.` : `Absorb ${c.n} damage this round.`}</div></button>`;
}

// ------------------------------------------------------------------ rendering
function selCost() { return ui.sel.reduce((a, i) => a + CARDS[ui.view.p[ME].hand[i]].cost, 0); }

function heroHTML(side) {
  const s = ui.view, p = s.p[side], mine = side === ME;
  const hp = ui.shown.hp[side], mana = ui.shown.mana[side], block = ui.shown.block[side], sword = ui.shown.sword[side];
  const spend = mine && !ui.busy ? selCost() : 0;
  const shield = block > 0 ? `<div class="shield${ui.pop.guard[side] ? ' pop' : ''}" id="shield${side}">${shieldSVG}<span style="font-size:18px">${block}</span></div>` : '';
  const sw = sword ? `<div class="swordb${ui.pop.sword[side] ? ' pop' : ''}" id="sword${side}">${ICON.sword}<span>+${sword}</span></div>` : '';
  let gems = '';
  for (let i = 0; i < MAX_E; i++) gems += `<i class="gemc${i < mana - spend ? ' on' : i < mana ? ' spend' : ''}"></i>`;
  return `<div class="left"><div class="guards">${sw}${shield}</div></div>
    <div class="mid"><div class="plate${mine ? ' mine' : ''}" id="plate${side}">
      <div class="hp${hp <= 8 ? ' low' : ''}">${hp}</div>
    </div></div>
    <div class="right">
      <div class="mana" id="mana${side}">${gems}</div>
      <div class="pile" title="deck"><i></i><b>${p.deck.length}</b></div>
    </div>`;
}

function lineHTML(side) {
  const p = ui.view.p[side];
  return ui.lines[side].map((id, k) => {
    const c = CARDS[id];
    const st = ui.done.has(side + ':' + k) ? ' resolved' : ui.step === c.speed ? ' now' : '';
    return cardHTML(id, { cls: 'inline' + st, owner: p });
  }).join('');
}

function handHTML() {
  const s = ui.view, p = s.p[ME];
  const order = p.hand.map((n, i) => i).sort((a, b) => {
    const A = CARDS[p.hand[a]], B = CARDS[p.hand[b]], R = { Sword: 0, Strike: 1, Guard: 2 };
    return (R[A.kind] - R[B.kind]) || A.cost - B.cost;
  });
  const choosing = !ui.busy && !ui.over;
  const ids = ui.sel.map(i => p.hand[i]);
  return order.map(i => {
    const id = p.hand[i];
    const on = ui.sel.includes(i);
    const ok = choosing && (on || validSet(s, ME, ids.concat([id])));
    let cls = on ? 'sel' : ok ? 'ok' : (choosing ? 'no' : '');
    if (ui.fresh.has(i)) cls += ' drawn';
    return cardHTML(id, { cls, owner: p, attrs: `data-i="${i}"${ok ? '' : ' disabled'}` });
  }).join('');
}

function trackerHTML(side) {
  const s = ui.view, mine = side === ME;
  return deckSummary(s, side).map(r => {
    const c = CARDS[r.id], left = mine ? r.inDeck : r.unseen;
    return `<div class="trow ${c.kind}${left ? '' : ' gone'}"><span class="tg">${c.cost}</span><span class="tn">${label(r.id)}</span><span class="tc">×${left}</span></div>`;
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
  // overlap the hand when it is wider than the room it has
  const hand = $('hand'), n = s.p[ME].hand.length;
  if (n > 1) {
    const cw = hand.querySelector('.card').offsetWidth, room = hand.clientWidth - 24;
    const ov = Math.min(14, (room - n * cw) / (n - 1));
    hand.style.setProperty('--ov', ov + 'px');
  }
  const choosing = !ui.busy && !ui.over;
  $('turnbox').innerHTML = `<button id="go" class="${choosing ? 'ready' : ''}"${choosing ? '' : ' disabled'}>Go</button>`;
  $('history').innerHTML = ui.hist.slice(-18).map(h => h.sep
    ? `<div class="hist sep"></div>`
    : `<div class="hist s${h.side}" data-card="${h.card}"><span class="hn">${label(h.card)}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`).join('');
  $('trk1').innerHTML = trackerHTML(BOT);
  $('trk0').innerHTML = trackerHTML(ME);
  $('decks').classList.toggle('show', ui.showDecks);
  if (ui.showDecks) $('decks').innerHTML = `<button class="x" id="closedecks">×</button><div class="wrap"><div>${trackerHTML(BOT)}</div><div>${trackerHTML(ME)}</div></div>`;
  ui.fresh.clear(); ui.pop = { sword: [0, 0], guard: [0, 0] };
}

// ------------------------------------------------------------------ playback
function centerOf(el) {
  const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect();
  return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 };
}
function floater(side, text, cls, dy = 0) {
  const el = $('plate' + side); if (!el) return;
  const c = centerOf(el);
  const f = document.createElement('div');
  f.className = 'float ' + cls; f.textContent = text;
  f.style.left = c.x + 'px'; f.style.top = (c.y + dy) + 'px';
  $('game').appendChild(f);
  setTimeout(() => f.remove(), 1200);
}
function shake(side) {
  const el = $('plate' + side); if (!el) return;
  el.classList.remove('shake'); void el.offsetWidth; el.classList.add('shake');
}
function sync(s) {
  ui.shown.hp = [s.p[0].hp, s.p[1].hp];
  ui.shown.block = [s.p[0].block, s.p[1].block];
  ui.shown.sword = [s.p[0].sword, s.p[1].sword];
  ui.shown.mana = [s.p[0].mana, s.p[1].mana];
}

async function playRound(prev, next, ev) {
  // reveal: both lines go on the table, fastest first
  const rev = ev.filter(e => e.t === 'reveal');
  for (const e of rev) {
    ui.lines[e.side] = e.cards.slice().sort((a, b) => CARDS[a].speed - CARDS[b].speed);
    ui.shown.mana[e.side] = e.mana;
  }
  ui.view = prev; ui.view = { ...prev, p: prev.p.map((p, i) => ({ ...p, hand: p.hand.filter((_, k) => true) })) };
  // hide committed cards from my hand while they are on the table
  const myHand = prev.p[ME].hand.slice();
  for (const id of ui.lines[ME]) myHand.splice(myHand.indexOf(id), 1);
  const oppHand = prev.p[BOT].hand.slice(0, prev.p[BOT].hand.length - ui.lines[BOT].length);
  ui.view.p[ME].hand = myHand; ui.view.p[BOT].hand = oppHand;
  ui.done = new Set(); ui.step = null;
  render();
  await wait(900);
  // resolve speed by speed
  let i = 0;
  const steps = [];
  for (const e of ev) {
    if (e.t === 'step') steps.push({ speed: e.speed, evs: [] });
    else if (steps.length && !['round', 'start'].includes(e.t)) steps[steps.length - 1].evs.push(e);
  }
  for (const st of steps) {
    ui.step = st.speed; render();
    await wait(350);
    const dmgTo = [0, 0], out = {};
    for (const e of st.evs) {
      if (e.t === 'guard') { ui.shown.block[e.side] = e.block; ui.pop.guard[e.side] = 1; out[e.side + e.card] = { out: '+' + e.n + ' ⛨', cls: 'block' }; }
      if (e.t === 'sword') { ui.shown.sword[e.side] = CARDS.SW.n; ui.pop.sword[e.side] = 1; out[e.side + e.card] = { out: '+2', cls: 'gold' }; }
      if (e.t === 'stop') { ui.shown.block[e.side] = e.block; floater(e.side, '⛨ ' + e.n, 'block', -24); out[(1 - e.side) + e.card] = { out: 'absorbed', cls: 'block' }; }
      if (e.t === 'hit') { ui.shown.hp[1 - e.side] -= e.dmg; dmgTo[1 - e.side] += e.dmg; out[e.side + e.card] = { out: '−' + e.dmg, cls: 'dmg' }; }
      if (e.t === 'drop') { ui.shown.sword[e.side] = 0; floater(e.side, 'Sword dropped', 'warn', 46); }
    }
    for (const side of [0, 1]) ui.lines[side].forEach((id, k) => {
      if (CARDS[id].speed !== st.speed) return;
      ui.done.add(side + ':' + k);
      const o = out[side + id] || {};
      ui.hist.push({ side, card: id, out: o.out || '', cls: o.cls || '' });
    });
    render();
    for (const side of [0, 1]) if (dmgTo[side]) { floater(side, '−' + dmgTo[side], 'dmg'); shake(side); }
    for (const e of st.evs) if (e.t === 'drop') ui.hist.push({ side: e.side, card: 'SW', out: 'dropped', cls: 'warn' });
    await wait(750);
  }
  ui.hist.push({ sep: true });
  // clear the table, start the next round
  ui.lines = [[], []]; ui.step = null; ui.done = new Set();
  ui.view = next; sync(next);
  const drew = ev.find(e => e.t === 'start' && e.side === ME);
  if (drew) for (let k = next.p[ME].hand.length - drew.drew; k < next.p[ME].hand.length; k++) ui.fresh.add(k);
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
  if (ui.busy || ui.over) return;
  const tok = ui.token;
  const mine = ui.sel.map(i => ui.s.p[ME].hand[i]);
  if (!validSet(ui.s, ME, mine)) return;
  ui.busy = true; ui.sel = []; render();
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
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.sel = []; ui.lines = [[], []]; ui.busy = false;
  sync(ui.s);
  $('over').classList.remove('show');
  render();
}

// ------------------------------------------------------------------ input
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
  if (t.dataset.i !== undefined) {
    const i = +t.dataset.i, k = ui.sel.indexOf(i);
    if (k >= 0) ui.sel.splice(k, 1); else ui.sel.push(i);
    render(); return;
  }
  switch (t.id) {
    case 'rematch': case 'newmatch': startMatch(); return;
    case 'showdecks': ui.showDecks = !ui.showDecks; render(); return;
    case 'closedecks': ui.showDecks = false; render(); return;
    case 'go': go(); return;
  }
});
startMatch();
