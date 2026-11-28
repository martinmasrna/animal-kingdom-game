// 40 Simultaneous turns. Both players plan the whole round at once (cards to play with their
// spell targets, every unit's attack target), then everything resolves together: spells, then
// new units enter, then all attacks at the same time. No first player.
// Plans are submitted one after the other through act() (seat 0, then seat 1); a bot never reads
// the other plan. Pure from the outside: act() clones; _act() mutates.

export const LIFE = 20, BOARD = 6, MAX_MANA = 10, ROUND_LIMIT = 60;

export const CARDS = {
  STR: { id: 'STR', name: 'Striker', kind: 'unit', cost: 1, atk: 2, hp: 1 },
  RAI: { id: 'RAI', name: 'Raider', kind: 'unit', cost: 2, atk: 3, hp: 2 },
  GRD: { id: 'GRD', name: 'Guard', kind: 'unit', cost: 2, atk: 2, hp: 3 },
  LIN: { id: 'LIN', name: 'Line', kind: 'unit', cost: 3, atk: 3, hp: 4 },
  HEV: { id: 'HEV', name: 'Heavy', kind: 'unit', cost: 4, atk: 4, hp: 5 },
  BIG: { id: 'BIG', name: 'Big', kind: 'unit', cost: 5, atk: 5, hp: 5 },
  HUG: { id: 'HUG', name: 'Huge', kind: 'unit', cost: 6, atk: 6, hp: 7 },
  H2: { id: 'H2', name: 'Hit 2', kind: 'spell', cost: 1, dmg: 2 },
  H3: { id: 'H3', name: 'Hit 3', kind: 'spell', cost: 2, dmg: 3 },
  H6: { id: 'H6', name: 'Hit 6', kind: 'spell', cost: 4, dmg: 6 },
};
export function deckList() { const out = []; for (const id of Object.keys(CARDS)) for (let i = 0; i < 3; i++) out.push(id); return out; }

export function rand(s) {
  let t = (s.seed = (s.seed + 0x6D2B79F5) | 0);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
function shuffleInPlace(s, a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rand(s) * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

let UID = 1;
function newPlayer() { return { life: LIFE, mana: 0, fatigue: 0, hand: [], deck: deckList(), board: [] }; }
export function clone(s) {
  return { ...s, plans: s.plans.slice(), p: s.p.map(p => ({ ...p, hand: p.hand.slice(), deck: p.deck.slice(), board: p.board.map(u => ({ ...u })) })) };
}
function emit(s, ev, e) { if (ev) { e.round = s.round; ev.push(e); } }
function drawOne(s, side, ev) {
  const P = s.p[side];
  if (P.deck.length) { P.hand.push(P.deck.shift()); emit(s, ev, { t: 'draw', side }); return; }
  P.fatigue++; P.life -= P.fatigue; emit(s, ev, { t: 'fatigue', side, n: P.fatigue, life: P.life });
}

export function newMatch({ seed } = {}) {
  const s = { seed: (seed >>> 0) || 1, round: 0, toAct: 0, first: null, winner: null, capped: false, plans: [null, null], p: [newPlayer(), newPlayer()] };
  for (const P of s.p) shuffleInPlace(s, P.deck);
  for (const side of [0, 1]) for (let i = 0; i < 4; i++) drawOne(s, side, null);
  startRound(s, null);
  return s;
}
function checkWin(s, ev) {
  if (s.winner !== null) return true;
  const a = s.p[0].life <= 0, b = s.p[1].life <= 0;
  if (!a && !b) return false;
  s.winner = a && b ? 'draw' : a ? 1 : 0;
  emit(s, ev, { t: 'end', winner: s.winner });
  return true;
}
function startRound(s, ev) {
  s.round++; s.plans = [null, null]; s.toAct = 0;
  emit(s, ev, { t: 'round' });
  for (const P of s.p) P.mana = Math.min(MAX_MANA, s.round);
  for (const side of [0, 1]) drawOne(s, side, ev);
  checkWin(s, ev);
}

// A plan: { t: 'plan', plays: [{ card, tgt? }], attacks: [{ from: uid, to: uid | -1 }] }
// tgt for a spell: { side, uid } with uid -1 for the player. Units listed in no attack stay home.
export function planError(s, side, plan) {
  const P = s.p[side], O = s.p[1 - side];
  if (!plan || plan.t !== 'plan') return 'not a plan';
  const hand = P.hand.slice(); let cost = 0, units = 0;
  for (const x of plan.plays) {
    const k = hand.indexOf(x.card); if (k < 0) return 'card not in hand ' + x.card;
    hand.splice(k, 1); const c = CARDS[x.card]; cost += c.cost;
    if (c.kind === 'unit') { units++; if (x.tgt) return 'unit with a target'; }
    else {
      if (!x.tgt) return 'spell without target';
      const B = s.p[x.tgt.side] && s.p[x.tgt.side].board; if (!B) return 'bad side';
      if (x.tgt.uid !== -1 && !B.some(u => u.uid === x.tgt.uid)) return 'spell target not on board';
    }
  }
  if (cost > P.mana) return 'over mana';
  if (P.board.length + units > BOARD) return 'board full';
  const used = new Set();
  for (const a of plan.attacks) {
    if (used.has(a.from)) return 'unit attacks twice'; used.add(a.from);
    if (!P.board.some(u => u.uid === a.from)) return 'attacker not mine';
    if (a.to !== -1 && !O.board.some(u => u.uid === a.to)) return 'attack target not an enemy unit';
  }
  return null;
}
export const planKey = (pl) => JSON.stringify([pl.plays.map(x => x.card + (x.tgt ? ':' + x.tgt.side + ':' + x.tgt.uid : '')).sort(), pl.attacks.map(a => a.from + '>' + a.to).sort()]);

function sweep(s, ev) {
  for (const side of [0, 1]) {
    const B = s.p[side].board;
    for (let i = B.length - 1; i >= 0; i--) if (B[i].hp <= 0) { emit(s, ev, { t: 'die', side, uid: B[i].uid, card: B[i].card }); B.splice(i, 1); }
  }
}
function resolve(s, ev) {
  const [A, B] = s.plans;
  emit(s, ev, { t: 'reveal', plans: [A, B] });
  for (const side of [0, 1]) { const P = s.p[side]; for (const x of s.plans[side].plays) { P.hand.splice(P.hand.indexOf(x.card), 1); P.mana -= CARDS[x.card].cost; } }
  // 1. all spells at once
  const dmgU = new Map(), dmgP = [0, 0];
  for (const side of [0, 1]) for (const x of s.plans[side].plays) {
    const c = CARDS[x.card]; if (c.kind !== 'spell') continue;
    emit(s, ev, { t: 'spell', side, card: x.card, tgt: x.tgt });
    if (x.tgt.uid === -1) dmgP[x.tgt.side] += c.dmg; else dmgU.set(x.tgt.uid, (dmgU.get(x.tgt.uid) || 0) + c.dmg);
  }
  const phase = (name) => { if (ev) ev.push({ t: 'phase', name, snap: clone(s) }); };
  phase('reveal');
  if (dmgU.size || dmgP[0] || dmgP[1]) {
    for (const side of [0, 1]) {
      for (const u of s.p[side].board) { const d = dmgU.get(u.uid); if (d) { u.hp -= d; emit(s, ev, { t: 'hit', side, uid: u.uid, n: d, hp: u.hp }); } }
      if (dmgP[side]) { s.p[side].life -= dmgP[side]; emit(s, ev, { t: 'hit', side, uid: -1, n: dmgP[side], life: s.p[side].life }); }
    }
    sweep(s, ev);
  }
  phase('spells');
  // 2. all new units enter, not ready
  for (const side of [0, 1]) for (const x of s.plans[side].plays) {
    const c = CARDS[x.card]; if (c.kind !== 'unit') continue;
    const u = { uid: UID++, card: x.card, atk: c.atk, hp: c.hp, max: c.hp, ready: false };
    s.p[side].board.push(u); emit(s, ev, { t: 'summon', side, uid: u.uid, card: x.card });
  }
  phase('enter');
  // 3. all attacks at once; an attack whose attacker or target is gone does not happen
  const live = [];
  for (const side of [0, 1]) for (const a of s.plans[side].attacks) {
    const u = s.p[side].board.find(v => v.uid === a.from && v.ready);
    if (!u) continue;
    if (a.to !== -1 && !s.p[1 - side].board.some(v => v.uid === a.to)) continue;
    live.push({ side, from: a.from, to: a.to, atk: u.atk });
  }
  if (live.length) {
    const dU = new Map(), dP = [0, 0], atkOf = new Map();
    for (const side of [0, 1]) for (const u of s.p[side].board) atkOf.set(u.uid, u.atk);
    for (const x of live) {
      if (x.to === -1) dP[1 - x.side] += x.atk;
      else { dU.set(x.to, (dU.get(x.to) || 0) + x.atk); dU.set(x.from, (dU.get(x.from) || 0) + atkOf.get(x.to)); }
    }
    emit(s, ev, { t: 'attacks', list: live });
    for (const side of [0, 1]) {
      for (const u of s.p[side].board) { const d = dU.get(u.uid); if (d) { u.hp -= d; emit(s, ev, { t: 'hit', side, uid: u.uid, n: d, hp: u.hp }); } }
      if (dP[side]) { s.p[side].life -= dP[side]; emit(s, ev, { t: 'hit', side, uid: -1, n: dP[side], life: s.p[side].life }); }
    }
    sweep(s, ev);
  }
  // 4. every surviving unit becomes ready
  for (const P of s.p) for (const u of P.board) u.ready = true;
  phase('attacks');
  if (checkWin(s, ev)) return;
  if (s.round >= ROUND_LIMIT) { s.winner = 'draw'; s.capped = true; emit(s, ev, { t: 'end', winner: 'draw' }); return; }
  startRound(s, ev);
}

function mAct(s, a, ev) {
  if (s.winner !== null) throw new Error('match over');
  const err = planError(s, s.toAct, a);
  if (err) throw new Error('illegal plan: ' + err);
  s.plans[s.toAct] = a;
  if (s.toAct === 0) { s.toAct = 1; return; }
  resolve(s, ev);
}
export function act(s, a, ev) { const t = clone(s); mAct(t, a, ev); return t; }
export function _act(t, a) { mAct(t, a, null); return t; }
// the state the other seat sees while planning: the first plan is not visible to it
export function hidePlans(s) { const t = clone(s); t.plans = [null, null]; return t; }
