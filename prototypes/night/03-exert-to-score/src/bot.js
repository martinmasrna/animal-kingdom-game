// Bots for Exert to score. Each returns one action for the player to move. None reads a hidden
// card: Expert redraws everything its player cannot see before every play-out (determinize).

import { CARDS, BOARD, TARGET, legalActions, _act, determinize, actionKey, canAct } from './engine.js';

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
const END = { t: 'end' };

// Random: a uniform choice among every legal action, ending the turn included.
export function randomBot(s, r) { return pick(legalActions(s), r); }

// The choices a person would consider: no damage spell on one's own unit, no scoring of 0 points
// (it only exposes the unit).
export function sensible(s) { return legalActions(s).filter(a => !(a.target && a.target.side === s.turn) && !(a.t === 'score' && s.p[s.turn].board[a.i].sc === 0)); }

const kills = (m, d) => m.str >= d.hp && d.str < m.hp;          // m destroys d and survives
const worth = (m) => CARDS[m.card].cost + m.sc;
function coinHelps(P) {
  if (!P.hand.includes('COIN')) return false;
  return P.hand.some(id => { const c = CARDS[id]; return c.kind !== 'Coin' && c.cost === P.mana + 1 && (c.kind !== 'Unit' || P.board.length < BOARD); });
}
// a Hit's best target: the most valuable enemy unit it destroys
function hitTarget(s, c) {
  const O = s.p[1 - s.turn]; let best = -1, bw = -1;
  O.board.forEach((d, j) => { if (d.hp <= c.dmg && worth(d) > bw) { bw = worth(d); best = j; } });
  return best;
}
function greedyPlay(s, spells) {
  const P = s.p[s.turn];
  if (coinHelps(P)) return { t: 'play', card: 'COIN' };
  const ids = [...new Set(P.hand)].filter(id => CARDS[id].kind !== 'Coin' && CARDS[id].cost <= P.mana).sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  for (const id of ids) {
    const c = CARDS[id];
    if (c.kind === 'Unit') { if (P.board.length < BOARD) return { t: 'play', card: id }; continue; }
    if (!spells) continue;
    if (c.kind === 'Draw') return { t: 'play', card: id };
    const j = hitTarget(s, c); if (j >= 0) return { t: 'play', card: id, target: { side: 1 - s.turn, i: j } };
  }
  return null;
}
// Greedy: the most expensive affordable card first (a Hit only where it destroys); then each ready
// unit challenges an exerted enemy unit it destroys and survives, otherwise scores (if it scores anything).
export function greedyBot(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const p = greedyPlay(s, true); if (p) return p;
  for (let i = 0; i < P.board.length; i++) {
    const m = P.board[i]; if (!canAct(m)) continue;
    let j = -1, bw = -1;
    O.board.forEach((d, k) => { if (d.ex && kills(m, d) && worth(d) > bw) { bw = worth(d); j = k; } });
    if (j >= 0) return { t: 'chal', i, j };
    if (m.sc > 0) return { t: 'score', i };
  }
  return END;
}
// Racer: plays units, scores with every unit that scores, never challenges, never casts.
export function racerBot(s) {
  const P = s.p[s.turn];
  const p = greedyPlay(s, false); if (p) return p;
  for (let i = 0; i < P.board.length; i++) if (canAct(P.board[i]) && P.board[i].sc > 0) return { t: 'score', i };
  return END;
}

// ------------------------------------------------------------------ Expert
// Play-out policy: Greedy's card play, then score out when that wins, take kills that survive
// or trade up, otherwise score most of the time; one action in ten random.
function policy(s, r) {
  if (r() < 0.1) return pick(sensible(s), r);
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  const p = greedyPlay(s, true); if (p) return p;
  let left = TARGET - P.pts;
  for (const m of P.board) if (canAct(m)) left -= m.sc;
  for (let i = 0; i < P.board.length; i++) {
    const m = P.board[i]; if (!canAct(m)) continue;
    if (left <= 0 && m.sc > 0) return { t: 'score', i };
    let j = -1, bw = -1;
    O.board.forEach((d, k) => { if (d.ex && d.hp <= m.str && (d.str < m.hp || worth(d) >= worth(m)) && worth(d) > bw) { bw = worth(d); j = k; } });
    if (j >= 0) return { t: 'chal', i, j };
    if (m.sc > 0 && r() < 0.85) return { t: 'score', i };
  }
  return END;
}
// A position's worth to `me` as a win chance: points, what the boards will score, cards in hand.
export function value(s, me) {
  const P = s.p[me], O = s.p[1 - me];
  let v = P.pts - O.pts;
  for (const m of P.board) v += 0.7 * m.sc + 0.12 * (m.str + m.hp) - (m.ex ? 0.3 : 0);
  for (const m of O.board) v -= 0.7 * m.sc + 0.12 * (m.str + m.hp) - (m.ex ? 0.3 : 0);
  v += 0.4 * (P.hand.length - O.hand.length) + (s.turn === me ? 0.5 : -0.5);
  return 1 / (1 + Math.exp(-v / 3));
}

// Information-set Monte Carlo tree search: every iteration redraws the hidden cards, walks the tree
// over the actions legal in that redraw (UCB with availability counts), plays out with the policy
// for CUTOFF turns, and scores the end by the win or by value().
export function ismcts(s, r, { iters = 1500, cutoff = 8, c = 0.7 } = {}) {
  const me = s.turn, rootActs = sensible(s);
  if (rootActs.length === 1) return rootActs[0];
  for (const a of rootActs) { const t = _act(determinize(s, me, r), a); if (t.winner === me) return a; }
  const root = { kids: new Map(), n: 0 };
  for (let it = 0; it < iters; it++) {
    const d = determinize(s, me, r), stop = d.turnNo + cutoff, path = [];
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
    while (d.winner === null && d.turnNo < stop) _act(d, policy(d, r));
    const v = d.winner === me ? 1 : d.winner === null ? value(d, me) : d.winner === 'draw' ? 0.5 : 0;
    root.n++;
    for (const ch of path) { ch.n++; ch.w += ch.player === me ? v : 1 - v; }
  }
  let best = rootActs[0], bn = -1;
  for (const a of rootActs) { const ch = root.kids.get(actionKey(s, a)); if (ch && ch.n > bn) { bn = ch.n; best = a; } }
  return best;
}
export const expertBot = (o) => (s, r) => ismcts(s, r, o);
