// Bots for Time track. Each returns one action for the player to act. None reads a hidden card:
// Expert redraws everything its player cannot see before every play-out.

import { CARDS, BOARD, HAND, legalActions, _act, determinize, actionKey, isReady } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const pick = (a, r) => a[Math.floor(r() * a.length)];

export function randomBot(s, r) { return pick(legalActions(s), r); }
// The choices a person would consider: no damage on one's own units, no Haste on a ready unit.
export function sensible(s) {
  const me = s.turn;
  return legalActions(s).filter(a => !(a.t === 'play' && CARDS[a.card].kind === 'Hit' && a.target.side === me) && !(a.t === 'play' && CARDS[a.card].kind === 'Haste' && isReady(s, me, s.p[me].board[a.target.i])));
}

const worth = (m) => CARDS[m.card].time + m.atk;
const killSurvive = (m, d) => m.atk >= d.hp && d.atk < m.hp;
function bestKill(s, i) {
  const me = s.turn, m = s.p[me].board[i]; let j = -1, bw = -1;
  s.p[1 - me].board.forEach((d, k) => { if (killSurvive(m, d) && worth(d) > bw) { bw = worth(d); j = k; } });
  return j;
}
function hitTarget(s, c) {
  const O = s.p[1 - s.turn]; let j = -1, bw = -1;
  O.board.forEach((d, k) => { if (d.hp <= c.dmg && worth(d) > bw) { bw = worth(d); j = k; } });
  return j;
}
function hasteTarget(s) {
  const me = s.turn; let j = -1, ba = -1;
  s.p[me].board.forEach((m, k) => { if (!isReady(s, me, m) && m.atk > ba) { ba = m.atk; j = k; } });
  return j;
}
// the most expensive card that can be played to some use
function playBig(s, unitsOnly, faceHits) {
  const me = s.turn, P = s.p[me];
  const ids = [...new Set(P.hand)].sort((a, b) => CARDS[b].time - CARDS[a].time);
  for (const id of ids) {
    const c = CARDS[id];
    if (c.kind === 'Unit') { if (P.board.length < BOARD) return { t: 'play', card: id }; continue; }
    if (unitsOnly) continue;
    if (c.kind === 'Hit') { const j = faceHits ? -1 : hitTarget(s, c); return { t: 'play', card: id, target: { side: 1 - me, i: j } }; }
    const j = hasteTarget(s); if (j >= 0) return { t: 'play', card: id, target: { side: me, i: j } };
  }
  return null;
}
const canDraw = (P) => P.deck.length > 0 && P.hand.length < HAND;

// Greedy: a ready unit's attack that destroys and survives; else the most expensive card (a Hit at
// the best unit it destroys, else the enemy); else a ready unit at the enemy; else Draw.
export function greedyBot(s) {
  const me = s.turn, P = s.p[me];
  for (let i = 0; i < P.board.length; i++) if (isReady(s, me, P.board[i])) { const j = bestKill(s, i); if (j >= 0) return { t: 'atk', i, j }; }
  const p = playBig(s, false, false); if (p) return p;
  for (let i = 0; i < P.board.length; i++) if (isReady(s, me, P.board[i])) return { t: 'atk', i, j: -1 };
  if (canDraw(P)) return { t: 'draw' };
  return legalActions(s)[0];
}
// Racer: every attack at the enemy, every Hit at the enemy, units played biggest first.
export function racerBot(s) {
  const me = s.turn, P = s.p[me];
  for (let i = 0; i < P.board.length; i++) if (isReady(s, me, P.board[i])) return { t: 'atk', i, j: -1 };
  const p = playBig(s, false, true); if (p) return p;
  if (canDraw(P)) return { t: 'draw' };
  return legalActions(s)[0];
}

// ------------------------------------------------------------------ Expert
function policy(s, r) {
  if (r() < 0.1) return pick(sensible(s), r);
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  let readyAtk = 0; const ready = [];
  P.board.forEach((m, i) => { if (isReady(s, me, m)) { ready.push(i); readyAtk += m.atk; } });
  if (ready.length && readyAtk >= O.life) return { t: 'atk', i: ready[0], j: -1 };
  for (const i of ready) { const j = bestKill(s, i); if (j >= 0) return { t: 'atk', i, j }; }
  if (ready.length && r() < 0.75) return { t: 'atk', i: pick(ready, r), j: -1 };
  const plays = [];
  for (const id of new Set(P.hand)) {
    const c = CARDS[id];
    if (c.kind === 'Unit') { if (P.board.length < BOARD) plays.push({ t: 'play', card: id }); }
    else if (c.kind === 'Hit') plays.push({ t: 'play', card: id, target: { side: 1 - me, i: hitTarget(s, c) } });
    else { const j = hasteTarget(s); if (j >= 0) plays.push({ t: 'play', card: id, target: { side: me, i: j } }); }
  }
  if (plays.length && (P.hand.length > 2 || !canDraw(P) || r() < 0.6)) return pick(plays, r);
  if (canDraw(P)) return { t: 'draw' };
  if (ready.length) return { t: 'atk', i: pick(ready, r), j: -1 };
  if (plays.length) return pick(plays, r);
  return legalActions(s)[0];
}

export function ismcts(s, r, { iters = 1500, c = 0.7 } = {}) {
  const me = s.turn, rootActs = sensible(s);
  if (rootActs.length === 1) return rootActs[0];
  for (const a of rootActs) { const t = _act(determinize(s, me, r), a); if (t.winner === me) return a; }
  const root = { kids: new Map(), n: 0 };
  for (let it = 0; it < iters; it++) {
    const d = determinize(s, me, r), path = [];
    let node = root;
    while (d.winner === null) {
      const acts = sensible(d), player = d.turn, fresh = [];
      let best = null, bv = -Infinity, ba = null;
      for (const a of acts) {
        const k = actionKey(d, a), ch = node.kids.get(k);
        if (!ch) { fresh.push([k, a]); continue; }
        ch.avail++;
        const u = ch.w / ch.n + c * Math.sqrt(Math.log(ch.avail) / ch.n);
        if (u > bv) { bv = u; best = ch; ba = a; }
      }
      if (fresh.length) {
        const [k, a] = pick(fresh, r);
        const ch = { kids: new Map(), n: 0, w: 0, avail: 1, player };
        node.kids.set(k, ch); path.push(ch); _act(d, a);
        break;
      }
      path.push(best); _act(d, ba); node = best;
    }
    while (d.winner === null) _act(d, policy(d, r));
    const v = d.winner === me ? 1 : d.winner === 'draw' ? 0.5 : 0;
    root.n++;
    for (const ch of path) { ch.n++; ch.w += ch.player === me ? v : 1 - v; }
  }
  let best = rootActs[0], bn = -1;
  for (const a of rootActs) { const ch = root.kids.get(actionKey(s, a)); if (ch && ch.n > bn) { bn = ch.n; best = a; } }
  return best;
}
export const expertBot = (o) => (s, r) => ismcts(s, r, o);
