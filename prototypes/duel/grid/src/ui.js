// Duel: Grid. The page. The player is side 0 (blue), the bot side 1 (red).
// Uses the engine and the bot through their exported functions only.
import { HEROES, CARDS, DECKS, CARD_ORDER, SHAPES, NEIGHBOURS, BASICS, colOf, rowOf, tileOf, popcount, tilesOf, isAttack,
  newMatch, startRound, resolveRound, checkChoice, choiceCost, posAtSpeed, makeRng, deckList } from './engine.js';
import { botChoose, canonicalOrder } from './bot.js';

const ME = 0, OP = 1;
const COLS = ['front', 'middle', 'back'];
const LANES = ['left', 'centre', 'right'];
const SPEED_NAME = { fast: 'Fast', normal: 'Normal', slow: 'Slow' };
const KIND_NAME = { light: 'Light', heavy: 'Heavy', defence: 'Defence', setup: 'Setup' };
const BEAT_MS = /[?#&]fast\b/.test(location.href) ? 30 : 700;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const tileName = (t) => `${COLS[colOf(t)]}-${LANES[rowOf(t)]}`;

const app = {
  settings: { me: 'Heavy', op: 'Quick' },
  state: null, mode: 'start',
  sel: null, botChoice: null, botTimer: null,
  log: [], play: null, rng: null, errors: [],
};
window.__duel = app;   // for the automated page check
app.render = () => render();

// ---------------------------------------------------------------- describing things
function describeTarget(card, mask) {
  if (mask == null) return 'tap his area';
  const ts = tilesOf(mask);
  switch (card) {
    case 'Jab': case 'Bolt': return tileName(ts[0]);
    case 'Slash': return 'his front column';
    case 'Haymaker': return 'his front + middle';
    case 'Lunge': return `${LANES[rowOf(ts[0])]} lane`;
    case 'Blast': return `${LANES[rowOf(ts[0])]} lane`;
    case 'Flurry': return ts.map(tileName).join(' + ');
    case 'Smash': { const rows = [...new Set(ts.map(rowOf))], cols = [...new Set(ts.map(colOf))]; return `${cols.map((c) => COLS[c]).join('+')}, ${rows.map((r) => LANES[r]).join('+')}`; }
  }
  return '';
}
function stepWord(from, to) {
  if (to == null) return null;
  const dc = colOf(to) - colOf(from), dr = rowOf(to) - rowOf(from);
  return dc < 0 ? 'forward' : dc > 0 ? 'back' : dr < 0 ? 'left' : 'right';
}
const who = (side) => (side === ME ? 'you' : 'he');
const whose = (side) => (side === ME ? 'your' : 'his');
const whom = (side) => (side === ME ? 'you' : 'him');
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function actionText(a) {
  return isAttack(a.card) ? `${a.card} (${describeTarget(a.card, a.tiles)})` : a.card;
}

function eventText(e) {
  const P = SPEED_NAME[e.ph] ? SPEED_NAME[e.ph] + ': ' : '';
  const s = e.side;
  switch (e.k) {
    case 'reveal': {
      const acts = e.actions.length ? e.actions.map(actionText).join(', ') : 'no actions';
      const st = e.step == null ? 'no step' : `step ${stepWord(e.from, e.step)}`;
      return `${s === ME ? 'You play' : 'He plays'} ${acts}; ${st}. Mana spent: ${e.cost}.`;
    }
    case 'guard': return `${P}${who(s)} raise${s === ME ? '' : 's'} ${e.card}.`;
    case 'step': return `${cap(who(s))} step${s === ME ? '' : 's'} ${stepWord(e.from, e.to)} to ${tileName(e.to)}.`;
    case 'attack': {
      const d = 1 - s;
      if (e.outcome === 'hit') return `${P}${whose(s)} ${e.card} hits ${whom(d)} on ${tileName(e.at)} for ${e.amount}.`;
      if (e.outcome === 'blocked') return `${P}${whose(s)} ${e.card} is stopped by ${whose(d)} ${e.guard}${e.reflect ? `; ${who(s)} take${s === ME ? '' : 's'} ${e.reflect}` : ''}.`;
      if (e.outcome === 'nothing') return `${P}${whose(s)} ${e.card} does nothing: ${who(s)} ${s === ME ? 'are' : 'is'} not in ${whose(s)} front column.`;
      if (e.reason === 'moved') return `${P}${whose(s)} ${e.card} misses: ${who(d)} stepped from ${tileName(e.startAt)} to ${tileName(e.at)}.`;
      return `${P}${whose(s)} ${e.card} misses: ${who(d)} ${d === ME ? 'are' : 'is'} on ${tileName(e.at)}.`;
    }
    case 'setup': {
      if (e.card === 'Meditate') return `${P}${who(s)} meditate${s === ME ? '' : 's'}: +${e.value} mana.`;
      if (e.card === 'Bandage') return `${P}${who(s)} bandage${s === ME ? '' : 's'}: +${e.value} health.`;
      if (e.card === 'Study') return `${P}${who(s)} stud${s === ME ? 'y' : 'ies'}: ${e.value} card${e.value === 1 ? '' : 's'} drawn.`;
      if (e.card === 'Sharpen') return `${P}${who(s)} sharpen${s === ME ? '' : 's'}: ${whose(s)} hits now deal +${e.value}.`;
      return '';
    }
    case 'cancel': return `${P}${whose(s)} ${e.card} is cancelled and returns to ${whose(s)} hand.`;
    case 'end': return e.winner === 'draw' ? 'Both fall in the same step: draw.' : e.winner === ME ? 'He falls. You win.' : 'You fall. He wins.';
  }
  return '';
}
const capFirst = (t) => (/^(Fast|Normal|Slow): /.test(t) ? t : t.charAt(0).toUpperCase() + t.slice(1));

// ---------------------------------------------------------------- start screen
function heroOpt(h, cls, on) {
  const H = HEROES[h];
  return `<button class="opt ${cls}${on ? ' on' : ''}" data-hero="${h}" data-for="${cls}"><b>${h}</b>Health ${H.hp}, +${H.regen} mana a round<br>${H.passive}: ${H.passiveText}</button>`;
}
function renderStart() {
  $('pickMe').innerHTML = ['Heavy', 'Quick'].map((h) => heroOpt(h, 'me', app.settings.me === h)).join('');
  $('pickOp').innerHTML = ['Heavy', 'Quick'].map((h) => heroOpt(h, 'op', app.settings.op === h)).join('');
}

function showScreen(name) {
  $('start').classList.toggle('hidden', name !== 'start');
  $('game').classList.toggle('hidden', name === 'start');
}

// ---------------------------------------------------------------- match flow
function newGame() {
  clearTimers();
  const seed = (Date.now() ^ (Math.random() * 4294967296)) >>> 0;
  app.rng = makeRng(seed ^ 0x9e3779b9);
  app.state = newMatch(app.settings.me, app.settings.op, seed);
  app.log = [];
  app.play = null;
  $('endov').classList.add('hidden');
  showScreen('game');
  beginRound();
}

function goStart() {
  clearTimers(); app.play = null; app.mode = 'start'; $('endov').classList.add('hidden'); renderStart(); showScreen('start');
}

function clearTimers() {
  if (app.botTimer) clearTimeout(app.botTimer);
  if (app.play && app.play.timer) clearTimeout(app.play.timer);
  app.botTimer = null;
}

function beginRound() {
  app.state = startRound(app.state);
  app.sel = { actions: [], step: null, active: null };
  app.botChoice = null;
  app.log.push({ rh: true, text: `Round ${app.state.round}` });
  app.state.fatigueTaken.forEach((n, side) => {
    if (n) app.log.push({ side, text: side === ME ? `Your deck is empty: you take ${n}.` : `His deck is empty: he takes ${n}.` });
  });
  if (app.state.over) {
    const w = app.state.winner;
    app.log.push({ end: true, text: w === 'draw' ? 'Both fall to fatigue: draw.' : w === ME ? 'He falls. You win.' : 'You fall. He wins.' });
    return showEnd();
  }
  app.mode = 'choose';
  render();
  // the bot decides now, from public information only, before the player has chosen anything
  const st = app.state;
  app.botTimer = setTimeout(() => { app.botTimer = null; if (app.state === st) app.botChoice = botChoose(st, OP, app.rng).choice; }, 40);
}

// ---------------------------------------------------------------- selection
function selChoice() {
  return { actions: app.sel.actions.map((a) => ({ card: a.card, tiles: isAttack(a.card) ? a.tiles : 0 })), step: app.sel.step };
}
function selCost(actions) { return choiceCost(app.state.p[ME].hero, actions.map((a) => ({ card: a.card }))); }

function countSelected(card) { return app.sel.actions.filter((a) => a.card === card).length; }
function countInHand(card) { return CARDS[card].basic ? 1 : app.state.p[ME].hand.filter((c) => c === card).length; }

function canAdd(card) {
  if (app.sel.actions.length >= 2) return false;
  if (countSelected(card) >= countInHand(card)) return false;
  return selCost([...app.sel.actions, { card }]) <= app.state.p[ME].mana;
}

function defaultTarget(card) {
  const pos = app.state.p[OP].pos;
  if (card === 'Flurry') return { tiles: null, partial: colOf(pos) === 0 ? 1 << pos : 0 };
  const m = SHAPES[card].find((x) => (x >> pos) & 1);
  return { tiles: m === undefined ? (SHAPES[card].length === 1 ? SHAPES[card][0] : null) : m, partial: 0 };
}

function addAction(card) {
  if (!canAdd(card)) return;
  const a = { card, tiles: 0, partial: 0 };
  if (isAttack(card)) Object.assign(a, defaultTarget(card));
  app.sel.actions.push(a);
  app.sel.active = isAttack(card) ? app.sel.actions.length - 1 : app.sel.active;
  render();
}
function removeAction(i) {
  app.sel.actions.splice(i, 1);
  if (app.sel.active === i) app.sel.active = null;
  else if (app.sel.active > i) app.sel.active--;
  if (app.sel.active == null) { const j = app.sel.actions.findIndex((a) => isAttack(a.card)); app.sel.active = j >= 0 ? j : null; }
  render();
}
function tapEnemyTile(t) {
  const i = app.sel.active;
  if (i == null) return;
  const a = app.sel.actions[i];
  if (!a || !isAttack(a.card)) return;
  if (a.card === 'Flurry') {
    if (colOf(t) !== 0) return;
    let m = a.tiles != null ? a.tiles : a.partial;
    if ((m >> t) & 1) m &= ~(1 << t);
    else if (popcount(m) >= 2) m = 1 << t;
    else m |= 1 << t;
    if (popcount(m) === 2) { a.tiles = m; a.partial = 0; } else { a.tiles = null; a.partial = m; }
  } else {
    const cands = SHAPES[a.card].filter((m) => (m >> t) & 1);
    if (!cands.length) return;
    const k = cands.indexOf(a.tiles);
    a.tiles = k >= 0 ? cands[(k + 1) % cands.length] : cands[0];
  }
  render();
}
function tapOwnTile(t) {
  const pos = app.state.p[ME].pos;
  if (t === pos || t === app.sel.step) app.sel.step = null;
  else if (NEIGHBOURS[pos].includes(t)) app.sel.step = t;
  render();
}
function meleeWarning(a) {
  const C = CARDS[a.card];
  if (!isAttack(a.card) || !C.melee) return false;
  return colOf(posAtSpeed(app.state.p[ME].pos, app.sel.step, C.speed)) !== 0;
}
function commitReady() {
  if (app.mode !== 'choose') return false;
  if (app.sel.actions.some((a) => isAttack(a.card) && a.tiles == null)) return false;
  return checkChoice(app.state, ME, selChoice()) === null;
}

function commit() {
  if (!commitReady()) return;
  if (app.botTimer) { clearTimeout(app.botTimer); app.botTimer = null; }
  if (!app.botChoice) app.botChoice = botChoose(app.state, OP, app.rng).choice;
  const mine = { actions: canonicalOrder(selChoice().actions), step: app.sel.step };
  const before = app.state;
  const res = resolveRound(before, [mine, app.botChoice]);
  startPlayback(before, res);
}

// ---------------------------------------------------------------- playback
function snapOf(s) { return s.p.map((q) => ({ hp: q.hp, mana: q.mana, pos: q.pos, sharpen: q.sharpen, hand: q.hand.length, deck: q.deck.length })); }

function buildBeats(events) {
  const beats = [];
  for (const e of events) {
    if (e.k === 'phase') { if (beats.length) beats[beats.length - 1].snaps.push(e.snap); continue; }
    const last = beats[beats.length - 1];
    if (last && (e.k === 'reveal' || e.k === 'step') && last.events[0].k === e.k) { last.events.push(e); continue; }
    beats.push({ events: [e], snaps: [] });
  }
  return beats;
}

function startPlayback(before, res) {
  app.mode = 'play';
  app.play = { before, res, beats: buildBeats(res.events), i: -1, timer: null, snap: snapOf(before), marks: [{}, {}], targets: null, ghosts: [null, null], guards: [[], []], caption: '' };
  nextBeat();
}

function nextBeat() {
  const pl = app.play;
  if (!pl) return;
  if (pl.timer) { clearTimeout(pl.timer); pl.timer = null; }
  pl.i++;
  if (pl.i >= pl.beats.length) return finishPlayback();
  const b = pl.beats[pl.i];
  pl.marks = [{}, {}];
  pl.flash = [{}, {}];
  const lines = [];
  for (const e of b.events) {
    const text = capFirst(eventText(e));
    if (text) lines.push(text);
    if (e.k === 'reveal') {
      // show both choices on the board: each side's targets on the other's area, steps as ghosts
      if (!pl.targets) pl.targets = [[], []];
      pl.targets[1 - e.side] = e.actions.filter((a) => isAttack(a.card)).map((a) => a.tiles);
      pl.ghosts[e.side] = e.step;
    } else if (e.k === 'step') {
      pl.ghosts[e.side] = null;
    } else if (e.k === 'guard') {
      pl.guards[e.side].push(e.card);
    } else if (e.k === 'attack') {
      const d = 1 - e.side;
      for (const t of tilesOf(e.tiles)) pl.flash[d][t] = e.side === ME ? 'flash-b' : 'flash-r';
      if (e.outcome === 'hit') pl.marks[d][e.at] = { cls: 'hit', text: `-${e.amount}` };
      else if (e.outcome === 'blocked') { pl.marks[d][e.at] = { cls: '', text: 'blocked' }; if (e.reflect) pl.marks[e.side][e.from] = { cls: 'hit', text: `-${e.reflect}` }; }
      else if (e.outcome === 'miss') pl.marks[d][e.at] = { cls: '', text: 'miss' };
      else pl.marks[e.side][e.from] = { cls: '', text: 'no reach' };
    } else if (e.k === 'setup') {
      const txt = e.card === 'Meditate' ? `+${e.value} mana` : e.card === 'Bandage' ? `+${e.value}` : e.card === 'Study' ? `+${e.value} cards` : `sharpen ${e.value}`;
      pl.marks[e.side][pl.snap[e.side].pos] = { cls: 'heal', text: txt };
    } else if (e.k === 'cancel') {
      pl.marks[e.side][pl.snap[e.side].pos] = { cls: '', text: 'cancelled' };
    }
    if (e.k !== 'reveal') pl.targets = e.k === 'attack' ? null : pl.targets;
  }
  for (const sn of b.snaps) pl.snap = sn;
  pl.caption = lines.join(' ');
  for (const t of lines) app.log.push({ text: t, side: b.events[0].side, end: b.events[0].k === 'end' });
  render();
  const dur = b.events[0].k === 'reveal' ? BEAT_MS * 2 : BEAT_MS;
  pl.timer = setTimeout(nextBeat, dur);
}

function skipPlayback() {
  const pl = app.play;
  if (!pl) return;
  while (pl.i < pl.beats.length - 1) {
    pl.i++;
    const b = pl.beats[pl.i];
    for (const e of b.events) { const t = capFirst(eventText(e)); if (t) app.log.push({ text: t, side: e.side, end: e.k === 'end' }); }
  }
  finishPlayback();
}

function finishPlayback() {
  const pl = app.play;
  if (pl.timer) clearTimeout(pl.timer);
  app.state = pl.res.state;
  app.play = null;
  if (app.state.over) return showEnd();
  beginRound();
}

function showEnd() {
  app.mode = 'over';
  render();
  const w = app.state.winner;
  $('endRes').textContent = w === 'draw' ? 'Draw' : w === ME ? 'You win' : 'He wins';
  $('endov').classList.remove('hidden');
}

// ---------------------------------------------------------------- rendering
function view() {
  if (app.play) return { snap: app.play.snap, play: app.play };
  return { snap: snapOf(app.state), play: null };
}

function renderGrid(side) {
  const v = view(), pl = v.play;
  const pos = v.snap[side].pos;
  const order = side === OP ? [2, 1, 0] : [0, 1, 2];    // opponent's front is at the bottom, mine at the top
  const choosing = app.mode === 'choose';
  const active = choosing && app.sel.active != null ? app.sel.actions[app.sel.active] : null;
  let html = '';
  for (const c of order) for (let r = 0; r < 3; r++) {
    const t = tileOf(c, r);
    const cls = ['tile'];
    if (c === 0) cls.push('front');
    const badges = [];
    let tok = '', mark = '';
    if (pos === t) tok = `<div class="tok ${side === ME ? 'b' : 'r'}">${app.state.p[side].hero[0]}</div>`;
    if (choosing && side === OP) {
      app.sel.actions.forEach((a, i) => {
        const m = a.tiles != null ? a.tiles : a.partial;
        if (isAttack(a.card) && m && ((m >> t) & 1)) { cls.push(i === 0 ? 't1' : 't2'); badges.push(`<span class="badge b">${i + 1}</span>`); }
      });
      if (active && isAttack(active.card) && SHAPES[active.card].some((m) => (m >> t) & 1)) cls.push('aim');
    }
    if (choosing && side === ME) {
      if (app.sel.step === t) tok = `<div class="tok ghost b">${app.state.p[ME].hero[0]}</div>`;
      else if (NEIGHBOURS[app.state.p[ME].pos].includes(t)) cls.push('stepok');
    }
    if (pl) {
      if (pl.targets) pl.targets[side].forEach((m, i) => {
        if ((m >> t) & 1) { cls.push(side === ME ? (i === 0 ? 'r1' : 'r2') : (i === 0 ? 't1' : 't2')); badges.push(`<span class="badge ${side === ME ? 'r' : 'b'}">${i + 1}</span>`); }
      });
      if (pl.ghosts[side] === t && pos !== t) tok = `<div class="tok ghost ${side === ME ? 'b' : 'r'}">${app.state.p[side].hero[0]}</div>`;
      if (pl.flash && pl.flash[side][t]) cls.push(pl.flash[side][t]);
      const mk = pl.marks[side][t];
      if (mk) mark = `<div class="mark ${mk.cls}"><span>${esc(mk.text)}</span></div>`;
    }
    html += `<button class="${cls.join(' ')}" data-area="${side}" data-t="${t}" aria-label="${tileName(t)}"><div class="badges">${badges.join('')}</div>${tok}${mark}</button>`;
  }
  return html;
}

function renderStats(side) {
  const v = view(), sn = v.snap[side], q = app.state.p[side];
  const color = side === ME ? 'b' : 'r';
  const pct = Math.max(0, sn.hp) / q.maxHp * 100;
  const guards = v.play ? v.play.guards[side] : [];
  const known = side === OP && q.known.length ? `<div class="known">Known in hand: ${q.known.join(', ')}</div>` : '';
  return `<div class="who ${color}">${side === ME ? 'You' : 'He'}: ${q.hero}</div>
    <div>Health <b>${sn.hp}</b>/${q.maxHp}</div><div class="hpbar"><i style="width:${pct}%;background:var(--${side === ME ? 'blue' : 'red'})"></i></div>
    <div>Mana <b>${sn.mana}</b>/10 <span class="known">+${q.regen}/round</span></div>
    <div>Hand <b>${sn.hand}</b> &middot; Deck <b>${sn.deck}</b>${sn.deck === 0 ? ` &middot; <span class="fat">fatigue next ${q.fatigue + 1}</span>` : ''}</div>
    <div>Sharpen <b>+${sn.sharpen}</b></div>
    ${guards.length ? `<div class="guard">Guard: ${guards.join(', ')}</div>` : ''}${known}`;
}

function miniDiagram(card) {
  if (!isAttack(card)) return '';
  const shapes = SHAPES[card];
  const union = shapes.reduce((a, b) => a | b, 0);
  const pick = { Jab: shapes[1], Bolt: shapes[4], Lunge: shapes[1], Blast: shapes[1], Flurry: shapes[0], Smash: shapes[0] }[card] ?? shapes[0];
  let h = '<div class="mini">';
  for (const c of [2, 1, 0]) for (let r = 0; r < 3; r++) {
    const t = tileOf(c, r);
    const cls = ((pick >> t) & 1) ? 'ex' : ((union >> t) & 1) ? 'can' : '';
    h += `<i class="${cls}${c === 0 ? ' fr' : ''}"></i>`;
  }
  return h + '</div>';
}

function cardHtml(card, n, selected, enabled) {
  const C = CARDS[card];
  const reach = isAttack(card) ? (C.melee ? 'Melee' : 'Ranged') : '';
  let cost = C.cost;
  return `<button class="card${C.basic ? ' basic' : ''}${selected ? ' sel' : ''}" data-card="${card}" ${enabled ? '' : 'disabled'}>
    <div class="nm"><span>${card}</span><span class="cost">${cost}</span></div>
    <div class="meta">${SPEED_NAME[C.speed]} &middot; ${KIND_NAME[C.kind]}${C.basic ? ' &middot; basic' : ''}</div>
    <div class="fx">${esc(C.text)}</div>
    <div class="foot">${miniDiagram(card)}<span>${reach}</span><span class="cnt">${!C.basic && n > 1 ? `x${n}` : ''}</span></div></button>`;
}

function renderHand() {
  const q = app.state.p[ME];
  const choosing = app.mode === 'choose';
  const counts = {};
  for (const c of q.hand) counts[c] = (counts[c] || 0) + 1;
  const list = [...BASICS, ...CARD_ORDER.filter((c) => counts[c])];
  return list.map((c) => {
    const sel = choosing && countSelected(c) > 0;
    const full = sel && countSelected(c) >= countInHand(c);
    const enabled = choosing && (canAdd(c) || full);
    return cardHtml(c, counts[c] || 1, sel, enabled);
  }).join('');
}

function renderTray() {
  if (app.mode === 'play') return `<span>${app.play ? 'Revealing' : ''}</span><button id="skip">Skip</button>`;
  if (app.mode === 'over') return `<button class="big" data-act="rematch">Rematch</button><button class="small" data-act="new">New match</button>`;
  if (app.mode !== 'choose') return '';
  const q = app.state.p[ME];
  const chips = app.sel.actions.map((a, i) => {
    const warn = meleeWarning(a);
    const incomplete = isAttack(a.card) && a.tiles == null;
    const tgt = isAttack(a.card) ? ` &rarr; ${esc(describeTarget(a.card, a.tiles))}` : '';
    return `<span class="chip${app.sel.active === i ? ' active' : ''}${warn ? ' warn' : ''}${incomplete ? ' incomplete' : ''}" data-chip="${i}">
      <span class="num">${i + 1}</span><span>${a.card}${tgt}${warn ? ` <span class="wtxt">does nothing: not in front</span>` : ''}</span>
      <button class="x" data-remove="${i}" aria-label="remove">&times;</button></span>`;
  });
  if (app.sel.step != null) chips.push(`<span class="chip" data-stepchip="1"><span>Step ${stepWord(q.pos, app.sel.step)}</span><button class="x" data-clearstep="1" aria-label="remove">&times;</button></span>`);
  const cost = selCost(app.sel.actions);
  return chips.join('') + `<span id="cost">Cost ${cost}/${q.mana}</span><button id="commit" ${commitReady() ? '' : 'disabled'}>Commit</button>`;
}

function deckTable(side) {
  const q = app.state.p[side];
  const list = DECKS[q.hero];
  const played = {}, known = {}, inHand = {};
  for (const c of q.discard) played[c] = (played[c] || 0) + 1;
  for (const c of q.known) known[c] = (known[c] || 0) + 1;
  for (const c of q.hand) inHand[c] = (inHand[c] || 0) + 1;
  const td = (n) => `<td class="${n ? '' : 'zero'}">${n}</td>`;
  let rows = '';
  for (const c of CARD_ORDER) {
    if (!list[c]) continue;
    const pl = played[c] || 0;
    if (side === ME) rows += `<tr><td>${c}</td><td>${CARDS[c].cost}</td>${td(list[c])}${td(pl)}${td(inHand[c] || 0)}${td(list[c] - pl - (inHand[c] || 0))}</tr>`;
    else rows += `<tr><td>${c}</td><td>${CARDS[c].cost}</td>${td(list[c])}${td(pl)}${td(known[c] || 0)}${td(list[c] - pl - (known[c] || 0))}</tr>`;
  }
  const head = side === ME ? '<th>Card</th><th>Cost</th><th>Copies</th><th>Played</th><th>In hand</th><th>In deck</th>'
    : '<th>Card</th><th>Cost</th><th>Copies</th><th>Played</th><th>Known</th><th>Unseen</th>';
  const H = HEROES[q.hero];
  return `<h3 class="${side === ME ? 'b' : 'r'}">${side === ME ? 'Your' : 'His'} deck: ${q.hero}</h3>
    <p class="passive">${H.passive}: ${H.passiveText}</p>
    <table class="dl"><tr>${head}</tr>${rows}</table>`;
}
function renderDecks() { return deckTable(OP) + deckTable(ME); }

function renderLog() {
  return app.log.map((l) => l.rh ? `<div class="rh">${esc(l.text)}</div>`
    : `<div class="ln${l.end ? ' end' : l.side === ME ? ' you' : l.side === OP ? ' him' : ''}">${esc(l.text)}</div>`).join('');
}

function render() {
  if (!app.state) return;
  $('roundLbl').textContent = `Round ${app.state.round}`;
  $('gridOp').innerHTML = renderGrid(OP);
  $('gridMe').innerHTML = renderGrid(ME);
  $('statsOp').innerHTML = renderStats(OP);
  $('statsMe').innerHTML = renderStats(ME);
  const mid = $('midline');
  mid.textContent = app.play ? app.play.caption : app.mode === 'over' ? (app.state.winner === 'draw' ? 'Draw.' : app.state.winner === ME ? 'You win.' : 'He wins.') : '';
  mid.classList.toggle('playing', !!app.play);
  $('tray').innerHTML = renderTray();
  $('hand').innerHTML = renderHand();
  const decks = renderDecks(), log = renderLog();
  for (const id of ['decksDesk', 'decksPhone']) $(id).innerHTML = decks;
  for (const id of ['logDesk', 'logPhone']) {
    const el = $(id);
    const atEnd = el.scrollTop + el.clientHeight >= el.scrollHeight - 30;
    el.innerHTML = id === 'logDesk' ? '<h3>Log</h3><div id="log">' + log + '</div>' : '<div id="log2">' + log + '</div>';
    if (atEnd || app.play) el.scrollTop = el.scrollHeight;
  }
  const lp = $('logOv').querySelector('.body'); if (lp) lp.scrollTop = lp.scrollHeight;
}

// ---------------------------------------------------------------- input
document.addEventListener('click', (ev) => {
  const el = ev.target.closest('button, [data-chip], #midline, .grid');
  if (!el) return;
  try { onClick(el, ev); } catch (err) { app.errors.push(String(err && err.stack || err)); throw err; }
});

function onClick(el, ev) {
  if (el.dataset.close) { $(el.dataset.close).classList.add('hidden'); return; }
  if (el.dataset.act === 'rematch') { newGame(); return; }
  if (el.dataset.act === 'new') { goStart(); return; }
  if (el.dataset.hero) { app.settings[el.dataset.for] = el.dataset.hero; renderStart(); return; }
  switch (el.id) {
    case 'btnStart': newGame(); return;
    case 'btnNew': goStart(); return;
    case 'btnDecks': $('decksOv').classList.remove('hidden'); return;
    case 'btnLog': case 'btnEndLog':
      $('endov').classList.add('hidden');
      if (el.id === 'btnLog' || window.innerWidth < 1000) { $('logOv').classList.remove('hidden'); const b = $('logPhone'); b.scrollTop = b.scrollHeight; }
      return;
    case 'commit': commit(); return;
    case 'skip': skipPlayback(); return;
  }
  if (app.mode === 'play') {
    // a tap anywhere on the board or the centre line moves the reveal on
    if (el.id === 'midline' || el.classList.contains('tile') || el.classList.contains('grid')) nextBeat();
    return;
  }
  if (app.mode !== 'choose') return;
  if (el.dataset.remove != null) { ev.stopPropagation(); removeAction(+el.dataset.remove); return; }
  if (el.dataset.clearstep) { app.sel.step = null; render(); return; }
  if (el.dataset.chip != null) { const i = +el.dataset.chip; if (isAttack(app.sel.actions[i].card)) { app.sel.active = i; render(); } return; }
  if (el.dataset.card) {
    const c = el.dataset.card;
    if (canAdd(c)) addAction(c);
    else if (countSelected(c)) { let k = -1; app.sel.actions.forEach((a, i) => { if (a.card === c) k = i; }); removeAction(k); }
    return;
  }
  if (el.dataset.t != null) {
    const t = +el.dataset.t, side = +el.dataset.area;
    if (side === OP) tapEnemyTile(t); else tapOwnTile(t);
  }
}

// a mouse wheel scrolls the hand sideways
document.getElementById('hand').addEventListener('wheel', (ev) => {
  const h = ev.currentTarget;
  if (Math.abs(ev.deltaY) > Math.abs(ev.deltaX) && h.scrollWidth > h.clientWidth) { h.scrollLeft += ev.deltaY; ev.preventDefault(); }
}, { passive: false });

window.addEventListener('error', (e) => app.errors.push(String(e.message)));
renderStart();
