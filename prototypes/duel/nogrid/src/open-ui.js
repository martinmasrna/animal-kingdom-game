// The Open version as a game screen. Drives the engine through its exported
// transitions only; everything the player sees comes from engine events,
// played back one beat at a time.
import { CARDS, HEROES, DECKS, BASICS, MANA_CAP, newMatch, playAction, endTurn, canPlay, seqCost, deckSummary } from './engine.js';
import { makeRng, botOpenAction } from './bot.js';

const ME = 0, BOT = 1;
const ui = {
  cfg: { me: 'Heavy', opp: 'Quick' },
  s: null, view: null, busy: false, over: false, showDecks: false,
  shown: { hp: [0, 0], mana: [0, 0] }, hist: [], fresh: new Set(), freshWind: new Set(), freshGuard: [0, 0],
  rng: makeRng((Date.now() ^ (Math.random() * 1e9)) >>> 0), token: 0,
};
const $ = (id) => document.getElementById(id);
const wait = (ms) => new Promise(r => setTimeout(r, ms));

// ------------------------------------------------------------------ icons
const ICON = {
  sword: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M14.5 2.5 21.5 2.5 21.5 9.5 10 21l-2-2-2.6 2.6-2.8-2.8L5.2 16.2l-2-2Z" opacity=".95"/></svg>',
  hammer: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M3 5h11v6H3zM14 6.5h3v3h-3zM8 11h3v11H8z"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 2 20 5v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5Z"/></svg>',
  spark: '<svg viewBox="0 0 24 24" fill="#fff"><path d="M12 1l2.6 8.4L23 12l-8.4 2.6L12 23l-2.6-8.4L1 12l8.4-2.6Z"/></svg>',
};
function shieldSVG(color) {
  return `<svg viewBox="0 0 46 54"><path d="M23 2 43 9v15c0 13-9 22-20 28C12 46 3 37 3 24V9Z" fill="${color}" stroke="#fff" stroke-width="3"/></svg>`;
}
const GUARD_COLOR = { Block: '#7d93aa', Parry: '#b5763a', Brace: '#4f6d8c' };
const GUARD_LABEL = { Block: '1', Parry: '1↺3', Brace: 'all' };

// ------------------------------------------------------------------ card faces
function cardText(name) {
  return {
    Jab: '2 damage.', Slash: '4 damage.', Lunge: '4 damage.', Flurry: 'Two hits of 2.',
    Smash: '8 damage. Unblockable.', Haymaker: '12 damage. Unblockable.',
    Block: 'Blocks the next hit.', Parry: 'Blocks the next hit and deals 3 back.', Brace: 'Blocks every hit.',
    Meditate: 'Gain 3 mana.', Bandage: 'Heal 5.', Sharpen: 'Your hits deal 1 more, for good.', Study: 'Draw 2 cards.',
  }[name];
}
function cardBig(name, sharpen) {
  const c = CARDS[name];
  if (c.kind === 'Light' || c.kind === 'Heavy') {
    const d = c.dmg + sharpen, up = sharpen > 0 ? ' up' : '';
    return `<span class="big${up}">${c.hits > 1 ? c.hits + '×' + d : d}</span>${c.kind === 'Heavy' ? ICON.hammer : ICON.sword}`;
  }
  if (c.kind === 'Defence') return ICON.shield.replace('<svg', '<svg style="width:40%"') + (name === 'Parry' ? '<span class="big" style="font-size:calc(var(--cardw)*.2)">↺3</span>' : name === 'Brace' ? '<span class="big" style="font-size:calc(var(--cardw)*.2)">all</span>' : '');
  return `<span class="big">${{ Meditate: '+3', Bandage: '+5', Sharpen: '+1', Study: '+2' }[name]}</span>${ICON.spark}`;
}
function speedLine(name) {
  const sp = CARDS[name].speed;
  if (sp === 'Slow') return '<div class="sp Slow">⏳ Next turn</div>';
  if (sp === 'Fast') return '<div class="sp Fast">⚡ Fast</div>';
  return '<div class="sp"> </div>';
}
function cardHTML(name, { cost = CARDS[name].cost, sharpen = 0, cls = '', attrs = '' } = {}) {
  const cheap = cost < CARDS[name].cost ? ' cheap' : '';
  return `<button class="card k-${CARDS[name].kind} ${cls}" ${attrs}>
    <span class="cgem${cheap}">${cost}</span>
    <div class="art">${cardBig(name, sharpen)}</div>
    <div class="nm">${name}</div>
    <div class="tx">${cardText(name)}</div>
    ${speedLine(name)}</button>`;
}

// ------------------------------------------------------------------ rendering
function heroHTML(side) {
  const s = ui.view, p = s.p[side], mine = side === ME;
  const hp = ui.shown.hp[side], mana = ui.shown.mana[side];
  const active = !ui.over && s.turn === side;
  const guards = p.guards.filter(g => g.type === 'Brace' || !g.used).map((g, i) => {
    const pop = ui.freshGuard[side] && i === p.guards.length - 1 ? ' pop' : '';
    return `<div class="shield${pop}" title="${g.type}">${shieldSVG(GUARD_COLOR[g.type])}<span>${GUARD_LABEL[g.type]}</span></div>`;
  }).join('');
  let gems = '';
  for (let i = 0; i < MANA_CAP; i++) gems += `<i class="gemc${i < mana ? ' on' : ''}"></i>`;
  const passive = HEROES[p.hero].passive.replace(/^\w+: /, '').replace('his', 'the').replace('never cancels his cards', 'never breaks a winding card');
  const basics = mine ? `<div class="basics" style="display:flex;gap:10px">${BASICS.map(b => {
    const ok = !ui.busy && !ui.over && s.turn === ME && canPlay(s, b);
    const cost = s.turn === ME ? seqCost(p, [b]) : CARDS[b].cost;
    return `<button class="basic${ok ? ' ok' : ''}" data-play="${b}"${ok ? '' : ' disabled'}><span class="bgem">${cost}</span><span class="bn">${b === 'Jab' ? 2 + p.sharpen : '⛨'}</span><b>${b}</b></button>`;
  }).join('')}</div>` : '';
  return `<div class="left"><div class="guards">${guards}</div></div>
    <div class="mid"><div class="plate${active ? ' active' : ''}" id="plate${side}">
      <div class="hname">${p.hero}</div><div class="hpass">${passive}</div>
      <div class="hpmax">/${p.maxHp}</div>
      <div class="hp${hp <= 8 ? ' low' : ''}">${hp}</div>
      ${p.sharpen ? `<div class="atk">+${p.sharpen}</div>` : ''}
    </div></div>
    <div class="right">${basics}
      <div class="mana" id="mana${side}">${gems}<span class="manatxt">${mana}<small> +${p.regen}/turn</small></span></div>
      <div class="counts">Deck ${p.deck.length}${mine ? '' : ' · Hand ' + p.hand.length}</div>
    </div>`;
}

function windHTML(side) {
  const s = ui.view, p = s.p[side], o = s.p[1 - side];
  if (!p.winding.length) return '';
  const breaks = p.hero === 'Heavy' ? 'Breaks if hit for 3+' : 'Breaks if hit';
  return p.winding.map(n => {
    const c = CARDS[n];
    const what = (c.kind === 'Heavy' || c.kind === 'Light') ? `<b>${c.dmg + p.sharpen} to ${side === ME ? 'him' : 'you'}</b>` : `<b>${n}</b>`;
    const when = side === ME ? 'at the start of your turn' : 'at the start of his turn';
    return `<div class="wind${ui.freshWind.has(side + n) ? ' in' : ''}">${cardHTML(n, { sharpen: p.sharpen })}<div class="wt">⏳ ${what}<br>lands ${when}<br>${breaks}</div></div>`;
  }).join('');
}

function handHTML() {
  const s = ui.view, p = s.p[ME];
  const order = p.hand.map((n, i) => i).sort((a, b) => CARDS[p.hand[a]].cost - CARDS[p.hand[b]].cost || p.hand[a].localeCompare(p.hand[b]));
  const myTurn = !ui.busy && !ui.over && s.turn === ME;
  const fresh = new Set(ui.fresh);
  return order.map(i => {
    const n = p.hand[i];
    const ok = myTurn && canPlay(s, n);
    const cost = s.turn === ME ? seqCost(p, [n]) : CARDS[n].cost;
    let cls = ok ? 'ok' : (myTurn ? 'no' : '');
    if (fresh.has(i)) cls += ' drawn';
    return cardHTML(n, { cost, sharpen: p.sharpen, cls, attrs: `data-play="${n}"${ok ? '' : ' disabled'}` });
  }).join('');
}

function render() {
  document.body.classList.toggle('playing', !!ui.s);
  if (!ui.s) { renderStart(); return; }
  const s = ui.view;
  $('opphand').innerHTML = '<i class="back"></i>'.repeat(s.p[BOT].hand.length);
  $('hero1').innerHTML = heroHTML(BOT);
  $('hero0').innerHTML = heroHTML(ME);
  $('wind1').innerHTML = windHTML(BOT);
  $('wind0').innerHTML = windHTML(ME);
  $('hand').innerHTML = handHTML();
  const myTurn = !ui.over && s.turn === ME;
  const left = myTurn ? 2 - s.p[ME].actions : 0;
  const canAct = myTurn && !ui.busy && [...new Set(s.p[ME].hand.concat(BASICS))].some(n => canPlay(s, n));
  $('turnbox').innerHTML = `<div class="pips">${'<i class="pip on"></i>'.repeat(left)}${'<i class="pip"></i>'.repeat(2 - left)}</div>
    <button id="endturn" class="${myTurn && !canAct ? 'done' : ''}"${myTurn && !ui.busy ? '' : ' disabled'}>${myTurn ? 'End turn' : 'His turn'}</button>`;
  $('history').innerHTML = ui.hist.slice(-14).map(h => h.sep
    ? `<div class="hist sep">${h.sep}</div>`
    : `<div class="hist s${h.side}" data-card="${h.name || h.card}"><span class="hn">${h.card}</span><span class="ho ${h.cls || ''}">${h.out || ''}</span></div>`).join('');
  $('decks').classList.toggle('show', ui.showDecks);
  if (ui.showDecks) $('decks').innerHTML = `<button class="x" id="closedecks">Close</button><div class="wrap">${deckTable(BOT)}${deckTable(ME)}</div>`;
  ui.fresh.clear(); ui.freshWind.clear(); ui.freshGuard = [0, 0];
}

function deckTable(side) {
  const s = ui.s, p = s.p[side], mine = side === ME;
  const rows = deckSummary(s, side).map(r => {
    const left = mine ? r.inDeck : r.unseen;
    return `<tr><td>${r.name}</td><td>${CARDS[r.name].cost}</td><td>${r.total}</td><td class="${r.played ? '' : 'z'}">${r.played}</td><td class="${left ? '' : 'z'}"><b>${left}</b></td></tr>`;
  }).join('');
  return `<div><h3>${mine ? 'Your' : 'His'} deck: ${p.hero}</h3><p>${HEROES[p.hero].passive}</p>
    <table><thead><tr><th>Card</th><th>Cost</th><th>In list</th><th>Played</th><th>${mine ? 'In deck' : 'Not seen'}</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function renderStart() {
  const c = ui.cfg;
  const seg = (key) => ['Heavy', 'Quick'].map(v => `<button data-cfg="${key}" data-v="${v}" class="${c[key] === v ? 'on' : ''}">${v}</button>`).join('');
  const d = (h) => `<b>${h}</b>: ${HEROES[h].hp} health, ${HEROES[h].regen} mana a turn. ${HEROES[h].passive.replace('his', 'the')}`;
  $('start').innerHTML = `<h1>Open Duel</h1>
    <div class="grp"><div class="lbl">You play</div><div class="seg">${seg('me')}</div></div>
    <div class="grp"><div class="lbl">He plays</div><div class="seg">${seg('opp')}</div></div>
    <p class="herodesc">${d('Heavy')}<br>${d('Quick')}</p>
    <button class="go" id="go">Fight</button>`;
}

// ------------------------------------------------------------------ playback
function centerOf(el) {
  const a = $('game').getBoundingClientRect(), r = el.getBoundingClientRect();
  return { x: r.left - a.left + r.width / 2, y: r.top - a.top + r.height / 2 };
}
function floater(side, text, cls, where = 'plate', dy = 0) {
  const el = $(where + side); if (!el) return;
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
function banner(text) {
  const b = $('banner'); b.textContent = text; b.classList.remove('show'); void b.offsetWidth; b.classList.add('show');
}

async function spotlight(card, side, lands, sharpen) {
  const t = centerOf($('table'));
  $('spot').style.left = t.x + 'px'; $('spot').style.top = t.y + 'px';
  $('spot').innerHTML = cardHTML(card, { sharpen, cls: `from${side}${lands ? ' lands' : ''}` });
  await wait(side === ME && !lands ? 380 : 850);
  const c = $('spot').querySelector('.card'); if (c) c.classList.add('out');
  await wait(200);
  $('spot').innerHTML = '';
}

// split events into beats: each played or landing card opens a new beat
function beats(ev) {
  const out = []; let cur = null;
  for (const e of ev) {
    if (e.t === 'play' || e.t === 'unwind') { cur = { card: e.card, side: e.side, lands: e.t === 'unwind', evs: [e] }; out.push(cur); }
    else { if (!cur) { cur = { evs: [] }; out.push(cur); } cur.evs.push(e); }
  }
  return out;
}

async function playBeats(ev, prev, next) {
  const bs = beats(ev);
  for (let k = 0; k < bs.length; k++) {
    const b = bs[k], last = k === bs.length - 1;
    for (const e of b.evs) if (e.t === 'turn') {
      ui.hist.push({ sep: e.side === ME ? 'Your turn' : 'His turn' });
      banner(e.side === ME ? 'Your turn' : 'His turn');
      await wait(e.side === ME ? 700 : 450);
    }
    if (b.card) {
      const pv = ui.view;
      await spotlight(b.card, b.side, b.lands, pv.p[b.side].sharpen);
    }
    // apply this beat
    let out = '', cls = '';
    const dmgTo = [0, 0];
    for (const e of b.evs) {
      if (e.t === 'hit') { ui.shown.hp[1 - e.side] -= e.dmg; dmgTo[1 - e.side] += e.dmg; }
      else if (e.t === 'parry') { ui.shown.hp[1 - e.side] -= 3; }
      else if (e.t === 'heal') ui.shown.hp[e.side] = e.hp;
      else if (e.t === 'play' || e.t === 'start' || e.t === 'meditate') ui.shown.mana[e.side] = e.mana;
    }
    ui.view = last ? next : prev;
    if (last) {
      ui.shown.hp = [next.p[0].hp, next.p[1].hp];
      ui.shown.mana = [next.p[0].mana, next.p[1].mana];
    }
    for (const e of b.evs) {
      if (e.t === 'wind') ui.freshWind.add(e.side + e.card);
      if (e.t === 'guard') ui.freshGuard[e.side] = 1;
    }
    for (const e of b.evs) if ((e.t === 'start' && e.drew && e.side === ME) || (e.t === 'study' && e.side === ME) || (e.t === 'cancel' && e.side === ME)) {
      // mark the newest hand cards as fresh (they sit at the end of the hand array)
      const n = e.t === 'start' ? 1 : e.t === 'study' ? e.drew : 1;
      const h = ui.view.p[ME].hand.length;
      for (let i = h - n; i < h; i++) if (i >= 0) ui.fresh.add(i);
    }
    render();
    for (const e of b.evs) {
      switch (e.t) {
        case 'hit': break;
        case 'stop': floater(e.side, 'Blocked', 'block', 'plate', -20); if (!out) { out = 'blocked'; cls = 'block'; } break;
        case 'parry': floater(1 - e.side, '−3', 'dmg'); shake(1 - e.side); break;
        case 'heal': floater(e.side, '+' + e.amount, 'heal'); out = '+' + e.amount; cls = 'heal'; break;
        case 'meditate': floater(e.side, '+' + e.amount, 'mana', 'mana'); out = '+' + e.amount + ' mana'; cls = 'mana'; break;
        case 'sharpen': floater(e.side, '+1 to every hit', 'gold'); out = '+1'; cls = 'mana'; break;
        case 'study': floater(e.side, '+' + e.drew + ' cards', 'gold'); out = '+' + e.drew; cls = 'mana'; break;
        case 'wind': out = '⏳'; cls = 'warn'; break;
        case 'guard': out = '⛨'; cls = 'block'; break;
        case 'cancel': floater(e.side, e.card + ' broken', 'warn', 'plate', 46); ui.hist.push({ side: e.side, card: e.card, out: 'broken', cls: 'warn' }); break;
      }
    }
    for (const side of [0, 1]) if (dmgTo[side]) { floater(side, '−' + dmgTo[side], 'dmg'); shake(side); out = '−' + dmgTo[side]; cls = 'dmg'; }
    if (b.card) {
      // the played card goes before any "broken" line it caused
      const entry = { side: b.side, name: b.card, card: (b.lands ? '⏳ ' : '') + b.card, out, cls };
      const brokeAt = ui.hist.length - b.evs.filter(e => e.t === 'cancel').length;
      ui.hist.splice(brokeAt, 0, entry);
      render();
    }
    if (b.card || dmgTo[0] || dmgTo[1]) await wait(b.side === ME && !b.lands ? 350 : 650);
  }
}

async function apply(fn) {
  const prev = ui.s, ev = [];
  const next = fn(prev, ev);
  ui.s = next;
  await playBeats(ev, prev, next);
  ui.view = next; ui.shown.hp = [next.p[0].hp, next.p[1].hp]; ui.shown.mana = [next.p[0].mana, next.p[1].mana];
  if (next.winner !== null) finish();
  render();
}

function finish() {
  ui.over = true;
  const w = ui.s.winner;
  const t = w === 'draw' ? ['Draw', ''] : w === ME ? ['Victory', 'win'] : ['Defeat', 'lose'];
  $('over').innerHTML = `<h2 class="${t[1]}">${t[0]}</h2><div class="row"><button id="rematch">Rematch</button><button class="sec" id="newmatch2">Change heroes</button></div>`;
  $('over').classList.add('show');
}

// ------------------------------------------------------------------ flow
async function startMatch() {
  const tok = ++ui.token;
  ui.s = newMatch({ version: 'open', heroes: [ui.cfg.me, ui.cfg.opp], seed: (Math.random() * 4294967296) >>> 0 });
  ui.view = ui.s; ui.over = false; ui.hist = []; ui.showDecks = false;
  ui.shown.hp = [ui.s.p[0].hp, ui.s.p[1].hp]; ui.shown.mana = [ui.s.p[0].mana, ui.s.p[1].mana];
  $('over').classList.remove('show');
  ui.busy = true; render();
  ui.hist.push({ sep: ui.s.first === ME ? 'Your turn' : 'His turn' });
  banner(ui.s.first === ME ? 'You go first' : 'He goes first');
  await wait(900);
  if (tok !== ui.token) return;
  if (ui.s.turn === BOT) await botTurn(tok);
  else { ui.busy = false; render(); }
}

async function botTurn(tok) {
  ui.busy = true; render();
  while (tok === ui.token && !ui.over) {
    await wait(450);
    if (tok !== ui.token) return;
    const a = botOpenAction(ui.s, ui.rng);
    if (a === null) break;
    await apply((s, ev) => playAction(s, a, ev));
  }
  if (tok !== ui.token || ui.over) return;
  await wait(300);
  await apply((s, ev) => endTurn(s, ev));
  if (tok !== ui.token) return;
  ui.busy = false; render();
}

async function myPlay(name) {
  if (ui.busy || ui.over || ui.s.turn !== ME || !canPlay(ui.s, name)) return;
  ui.busy = true;
  await apply((s, ev) => playAction(s, name, ev));
  ui.busy = false; render();
}

async function myEndTurn() {
  if (ui.busy || ui.over || ui.s.turn !== ME) return;
  const tok = ui.token;
  ui.busy = true; render();
  await apply((s, ev) => endTurn(s, ev));
  if (tok !== ui.token || ui.over) return;
  await botTurn(tok);
}

// ------------------------------------------------------------------ input
// hovering (or tapping) a history line shows that card beside the list
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
  if (t.dataset.cfg) { ui.cfg[t.dataset.cfg] = t.dataset.v; render(); return; }
  if (t.dataset.play) { myPlay(t.dataset.play); return; }
  switch (t.id) {
    case 'go': case 'rematch': startMatch(); return;
    case 'newmatch': case 'newmatch2': ui.token++; ui.s = null; ui.over = false; $('over').classList.remove('show'); render(); return;
    case 'showdecks': ui.showDecks = !ui.showDecks; render(); return;
    case 'closedecks': ui.showDecks = false; render(); return;
    case 'endturn': myEndTurn(); return;
  }
});
render();
