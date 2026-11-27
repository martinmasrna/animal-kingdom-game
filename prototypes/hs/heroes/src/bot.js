// Bots for Hero HS, after Vanilla HS's: Greedy (lethal or the 50 line when either is there,
// otherwise the one-step best action) and Expert (Greedy's turn unless play-outs clearly
// prefer another). None reads a hidden card: play-outs reshuffle what the mover cannot see.

import { CARDS, HEROES, WIN, FIRE, clone, _act, _endTurn, legalActions, targetKind } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const pick = (a, rng) => a[Math.floor(rng() * a.length)];

// The actions a sensible player considers: damage and destroy at the enemy, buffs on its own.
export function sensible(s) {
  const me = s.turn;
  return legalActions(s).filter(a => {
    if (!a.target) return true;
    if (a.t === 'power') return true;
    const c = CARDS[a.card];
    if (c.buff) return a.target.side === me;
    return a.target.side !== me;
  });
}
export function randomBot(s, rng) {
  const t = clone(s), out = [];
  for (;;) {
    const opts = sensible(t);
    if (!opts.length || t.winner !== null || rng() < 0.08) return out;
    const a = pick(opts, rng); _act(t, a); out.push(a);
  }
}

// A position's worth to `me`. Energy counts at both ends: each point is worth more near 0 and
// near 50, for both heroes, so gaining and damaging are two halves of one race. A gainer whose
// owner will cross 50 at the end of his own turn is that turn's win.
export const W = { e: 0.5, edge: 0.6, low: 12, high: 38, atk: 1.5, mhp: 1, card: 2 };
const eWorth = (e) => W.e * e - W.edge * Math.max(0, W.low - e) + W.edge * Math.max(0, e - W.high);
const EXTRA = { e3: 2, g2: 1.5, d2b: 1.5, HA: 5, HM: 2 };
function minionWorth(m) { const c = CARDS[m.card]; return W.atk * m.atk + W.mhp * m.hp + (c.taunt ? 1 : 0) + (EXTRA[m.card] || 0); }
// Burn in hand keeps its reach: worth nearly what it would do to his face now, so it goes at his
// face only to win (the search) or when nothing better is left.
function cardWorth(id, oe) {
  const c = CARDS[id];
  let v = c.fire !== undefined ? 1 + 0.5 * c.dmg : id === 'HM8' ? 6 : W.card;
  if (c.dmg) v = Math.max(v, 0.9 * (eWorth(Math.max(oe, 0)) - eWorth(Math.max(oe - c.dmg, 0))));
  return v;
}
const eotGain = (P) => P.board.reduce((n, m) => n + ((CARDS[m.card].eot || {}).gain || 0), 0);
export function evaluate(s, me) {
  if (s.winner === me) return 1e4;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1e4;
  const P = s.p[me], O = s.p[1 - me];
  if (s.turn === me && P.energy + eotGain(P) >= WIN) return 5e3;
  if (s.turn === me && O.energy + eotGain(O) >= WIN) return -5e3; // he crosses 50 at the end of his next turn
  let v = eWorth(Math.max(P.energy, 0)) - eWorth(Math.max(O.energy, 0));
  for (const m of P.board) v += minionWorth(m);
  for (const m of O.board) v -= minionWorth(m);
  for (const id of P.hand) v += cardWorth(id, O.energy);
  for (const id of O.hand) v -= cardWorth(id, P.energy);
  return v;
}

// ------------------------------------------------------------------ winning this turn
// An upper bound on the damage and the gain this turn can bring, so most turns skip the search.
function bounds(s) {
  const me = s.turn, P = s.p[me];
  let dmg = 0, gn = eotGain(P), atkers = P.board.some(m => m.ready);
  for (const m of P.board) if (m.ready) dmg += m.atk;
  for (const id of P.hand) {
    const c = CARDS[id];
    if (c.dmg) dmg += c.dmg; if (c.bc && c.bc.dmg) dmg += c.bc.dmg; if (c.rush) dmg += c.atk;
    if (c.buff && atkers) dmg += c.buff;
    if (c.gain) gn += c.gain; if (c.bc && c.bc.gain) gn += c.bc.gain; if (c.eot) gn += c.eot.gain;
  }
  const H = HEROES[P.hero];
  if (!P.powered && P.mana >= H.power) {
    if (P.hero === 'P') dmg += FIRE[Math.min(3, Math.floor(P.uses / 3))].dmg;
    if (P.hero === 'A' && atkers) dmg += 2;
    if (P.hero === 'M' && !P.deck.length) gn += P.fatigue + 1;
  }
  return { dmg, gn };
}
const key = (t) => JSON.stringify([t.p.map(p => [p.energy, p.mana, p.powered, p.hand.slice().sort(), p.board.map(m => m.card + ':' + m.atk + ':' + m.hp + (m.ready ? 'r' : ''))])]);
// The actions that can matter for a win this turn: anything at his face or at a Taunt in the way,
// the Coin, the hero power, gain, Rush, a buff on a ready minion.
function winMoves(t, wantDmg, wantGain) {
  const me = t.turn, O = t.p[1 - me], taunt = O.board.some(m => CARDS[m.card].taunt);
  const isT = (i) => i >= 0 && CARDS[O.board[i].card].taunt;
  const out = [];
  for (const a of sensible(t)) {
    if (a.t === 'attack') { if (wantDmg && (a.to < 0 || isT(a.to))) out.push(a); continue; }
    if (a.t === 'power') { const h = t.p[me].hero; if ((h === 'M' && wantGain) || (h !== 'M' && wantDmg)) if (h !== 'A' || t.p[me].board[a.target.i].ready) out.push(a); continue; }
    const c = CARDS[a.card];
    if (c.kind === 'Coin') { out.push(a); continue; }
    if (wantDmg) {
      if ((c.dmg || (c.bc && c.bc.dmg)) && (a.target.i < 0 || isT(a.target.i))) { out.push(a); continue; }
      if (c.destroy && isT(a.target.i)) { out.push(a); continue; }
      if (c.area && taunt) { out.push(a); continue; }
      if (c.rush) { out.push(a); continue; }
      if (c.buff && t.p[me].board[a.target.i].ready) { out.push(a); continue; }
      if (c.bc && c.bc.upFire) { out.push(a); continue; }
    }
    if (wantGain && (c.gain || (c.bc && c.bc.gain) || c.eot)) out.push(a);
  }
  // faces first: the search finds the plain kill before the clever one
  return out.sort((a, b) => ((b.to === -1 || (b.target && b.target.i < 0)) ? 1 : 0) - ((a.to === -1 || (a.target && a.target.i < 0)) ? 1 : 0));
}
// The action list that wins this turn (by 0 or by 50, the end-of-turn gain included), or null.
export function findWin(s, budget = 3000) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const b = bounds(s);
  const wantDmg = b.dmg >= O.energy, wantGain = P.energy + b.gn >= WIN;
  if (!wantDmg && !wantGain) return null;
  let nodes = 0; const seen = new Set();
  const rec = (t, path) => {
    if (t.winner === me) return path;
    if (t.winner !== null) return null;
    if (t.p[me].energy + eotGain(t.p[me]) >= WIN) return path;
    if (++nodes > budget) return null;
    const k = key(t); if (seen.has(k)) return null; seen.add(k);
    for (const a of winMoves(t, wantDmg, wantGain)) {
      const x = clone(t); _act(x, a);
      const r = rec(x, path.concat([a]));
      if (r) return r;
      if (nodes > budget) return null;
    }
    return null;
  };
  return rec(clone(s), []);
}

// A hit on an enemy minion that survives it: the uid of that minion, so Greedy can judge the hit
// together with the one that finishes it (two 3/4s into a 3/5 is one kill, not two bad trades).
function follow(t, a, x) {
  const O = t.p[1 - t.turn];
  const i = a.t === 'attack' ? a.to : a.t === 'play' && a.target && a.target.side !== t.turn && (CARDS[a.card].dmg || (CARDS[a.card].bc || {}).dmg) ? a.target.i : -1;
  if (i < 0) return null;
  const uid = O.board[i].uid;
  return x.p[1 - t.turn].board.some(m => m.uid === uid) ? uid : null;
}
function hitsUid(x, b, uid) {
  const O = x.p[1 - x.turn];
  const i = b.t === 'attack' ? b.to : b.t === 'play' && b.target && b.target.side !== x.turn && (CARDS[b.card].dmg || (CARDS[b.card].bc || {}).dmg) ? b.target.i : -1;
  return i >= 0 && O.board[i].uid === uid;
}
// Greedy: the win when it is there; otherwise each step the action that most improves the worth
// (the Coin judged by the best action it opens), and the turn ends when none does.
export function greedyBot(s, rng, budget = 3000) {
  const kill = findWin(s, budget);
  if (kill) return kill;
  const me = s.turn, out = [];
  let t = clone(s);
  const val = (x) => evaluate(x, me);
  let cur = val(t);
  for (;;) {
    if (t.winner !== null) return out;
    let best = null, bv = cur + 1e-9;
    for (const a of sensible(t)) {
      const x = clone(t); _act(x, a);
      let v = val(x);
      const f = follow(t, a, x);
      if (f) for (const b of sensible(x)) if (hitsUid(x, b, f)) { const y = clone(x); _act(y, b); v = Math.max(v, val(y)); }
      if (a.t === 'play' && a.card === 'COIN') { v = -Infinity; for (const b of sensible(x)) { if (b.t === 'play' && b.card === 'COIN') continue; const y = clone(x); _act(y, b); v = Math.max(v, val(y)); } }
      if (v > bv) { bv = v; best = { a, x }; }
    }
    if (!best) return out;
    out.push(best.a); t = best.x; cur = val(t);
  }
}

function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
const play = (t, acts) => { for (const a of acts) { if (t.winner !== null) break; _act(t, a); } return t; };
// cards everyone can see in a hand: the hero card, Fireballs, the Coin
const PUBLIC = (id) => CARDS[id].hero || CARDS[id].fire !== undefined || id === 'COIN';
// Expert: candidate turns are Greedy's own and each first action finished the way Greedy would;
// the best TOPN by Greedy's judgement are each played out R times DEPTH turns ahead with Greedy
// on both sides, after reshuffling the cards the mover cannot see. Greedy's turn stands unless
// another wins clearly more play-outs.
const MARGIN = 0.2;
export function rolloutBot(TOPN = 8, R = 16, DEPTH = 8, budget = 200) {
  return function (s, rng) {
    const me = s.turn, cands = [];
    const kill = findWin(s, 6000);
    if (kill) return kill;
    const add = (acts) => { const t = play(clone(s), acts); cands.push({ acts, t, v: evaluate(t, me) }); };
    add(greedyBot(s, rng, 0)); cands[0].greedy = true; add([]);
    for (const a of sensible(s)) { const t = play(clone(s), [a]); add([a, ...greedyBot(t, rng, 0)]); }
    const seen = new Set(), top = [];
    for (const c of cands.sort((a, b) => b.v - a.v)) {
      const k = key(c.t);
      if (!seen.has(k)) { seen.add(k); top.push(c); }
      if (top.length >= TOPN) break;
    }
    if (top.length === 1 || top[0].t.winner === me) return top[0].acts;
    const g = cands.find(c => c.greedy);
    if (!top.includes(g)) top.push(g);
    const scored = [];
    for (const c of top) {
      let w = 0;
      for (let r = 0; r < R; r++) {
        const t = clone(c.t), O = t.p[1 - me];
        const hidden = O.hand.filter(id => !PUBLIC(id)), shown = O.hand.filter(PUBLIC);
        const pool = shuffle(hidden.concat(O.deck), rng);
        O.hand = shown.concat(pool.slice(0, hidden.length)); O.deck = pool.slice(hidden.length);
        shuffle(t.p[me].deck, rng);
        if (t.winner === null) _endTurn(t);
        for (let d = 0; t.winner === null && d < DEPTH; d++) { play(t, greedyBot(t, rng, budget)); if (t.winner !== null) break; _endTurn(t); }
        if (t.winner === me) w += 1; else if (t.winner === 'draw') w += 0.5;
        else if (t.winner === null) { const e = evaluate(t, me); w += e > 0 ? 0.75 : e < 0 ? 0.25 : 0.5; }
      }
      scored.push({ c, w });
    }
    const gw = scored.find(x => x.c === g).w;
    let best = g, bw = gw;
    for (const x of scored) if (x.w > bw) { bw = x.w; best = x.c; }
    return bw > gw + MARGIN * R ? best.acts : g.acts;
  };
}
