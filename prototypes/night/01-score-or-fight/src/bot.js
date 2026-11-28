// Bots for the score-or-fight duel. Each is a step function: given a position, the one action
// it takes next ({ t: 'end' } ends its turn). None reads a hidden card: the Expert deals the
// unseen cards again before every play-out.

import { CARDS, TARGET, BOARD, clone, _act, legalActions, key, determinize } from './engine.js';

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const END = { t: 'end' };

// Random: a uniform choice among every legal action, ending the turn included.
export function randomBot(s, rng) { const o = legalActions(s); return o[Math.floor(rng() * o.length)]; }

// Coin first when it lets a dearer card be played than the mana alone allows.
function coinHelps(P, playable) {
  if (!P.hand.includes('COIN')) return false;
  let now = -1, withCoin = -1;
  for (const id of P.hand) { const c = CARDS[id]; if (c.kind === 'Coin' || !playable(id)) continue; if (c.cost <= P.mana) now = Math.max(now, c.cost); else if (c.cost <= P.mana + 1) withCoin = Math.max(withCoin, c.cost); }
  return withCoin > now;
}

// Greedy (the spec's rule): score out when the ready units' health reaches the target; otherwise
// play the dearest affordable card first (a spell at the enemy unit with the most health it
// destroys, else the enemy unit with the most health); then each ready unit attacks if it destroys
// an enemy unit and survives, otherwise it scores.
export function greedyBot(s) {
  const me = s.turn, P = s.p[me], O = s.p[1 - me];
  let readyHp = 0, firstReady = -1;
  P.board.forEach((m, i) => { if (m.ready) { readyHp += m.hp; if (firstReady < 0) firstReady = i; } });
  if (firstReady >= 0 && P.score + readyHp >= TARGET) return { t: 'score', from: firstReady };
  const playable = (id) => { const c = CARDS[id]; return c.kind === 'Unit' ? P.board.length < BOARD : c.kind === 'Spell' ? O.board.length > 0 : false; };
  if (coinHelps(P, playable)) return { t: 'play', card: 'COIN' };
  let best = null;
  for (const id of P.hand) { const c = CARDS[id]; if (c.cost > P.mana || !playable(id)) continue; if (!best || c.cost > CARDS[best].cost || (c.cost === CARDS[best].cost && c.kind === 'Unit')) best = id; }
  if (best) {
    const c = CARDS[best];
    if (c.kind === 'Unit') return { t: 'play', card: best };
    let to = -1, th = -1, kill = false;
    O.board.forEach((m, i) => { const k = m.hp <= c.dmg; if ((k && !kill) || (k === kill && m.hp > th)) { to = i; th = m.hp; kill = k; } });
    return { t: 'play', card: best, to };
  }
  for (let i = 0; i < P.board.length; i++) {
    const m = P.board[i];
    if (!m.ready) continue;
    let to = -1, th = -1;
    O.board.forEach((d, j) => { if (m.atk >= d.hp && m.hp > d.atk && d.hp > th) { to = j; th = d.hp; } });
    return to >= 0 ? { t: 'attack', from: i, to } : { t: 'score', from: i };
  }
  return END;
}

// Racer: plays units only (dearest first), never attacks, scores with every ready unit.
export function racerBot(s) {
  const me = s.turn, P = s.p[me];
  const playable = (id) => CARDS[id].kind === 'Unit' && P.board.length < BOARD;
  if (coinHelps(P, playable)) return { t: 'play', card: 'COIN' };
  let best = null;
  for (const id of P.hand) { const c = CARDS[id]; if (c.kind === 'Unit' && c.cost <= P.mana && P.board.length < BOARD && (!best || c.cost > CARDS[best].cost)) best = id; }
  if (best) return { t: 'play', card: best };
  const i = P.board.findIndex(m => m.ready);
  return i >= 0 ? { t: 'score', from: i } : END;
}

// A position's worth to `me` as a win chance: the score lead, and what each board will score or
// kill over the next turns (health scores, attack removes enemy health), and cards in hand.
export function evaluate(s, me) {
  const P = s.p[me], O = s.p[1 - me];
  let v = P.score - O.score;
  for (const m of P.board) v += 1.2 * m.hp + 0.6 * m.atk;
  for (const m of O.board) v -= 1.2 * m.hp + 0.6 * m.atk;
  v += 1.5 * (P.hand.length - O.hand.length) + 0.8 * (P.maxMana - O.maxMana);
  return 1 / (1 + Math.exp(-v / 7));
}

// Play-out policy: Greedy, with an occasional random legal action so play-outs do not all agree.
function policy(t, rng, eps) { return rng() < eps ? randomBot(t, rng) : greedyBot(t); }
function rollout(t, me, rng, depth, eps, start) {
  for (let steps = 0; t.winner === null && t.turnNo - start < depth && steps < 400; steps++) _act(t, policy(t, rng, eps));
  if (t.winner === null) return evaluate(t, me);
  return t.winner === me ? 1 : t.winner === 'draw' ? 0.5 : 0;
}

// Expert: flat Monte Carlo with UCB1 over the distinct actions now (actions that give the same
// position count once). Each play-out deals the unseen cards again, takes the action, and plays on
// with the play-out policy for `depth` turns; an unfinished one is scored by evaluate().
// `playouts` is the budget per action; with `timeMs` it also stops at that time (after at least
// `minPlayouts`), so the page never waits long.
export function mcExpert({ playouts = 3000, depth = 99, eps = 0, C = 0.5, timeMs = 0, minPlayouts = 200 } = {}) {
  return function expert(s, rng) {
    const me = s.turn, opts = [], seen = new Set();
    for (const a of legalActions(s)) {
      const t = clone(s); _act(t, a);
      if (t.winner === me) return a;
      const k = a.t === 'end' ? 'end' : key(t);
      if (!seen.has(k)) { seen.add(k); opts.push({ a, n: 0, w: 0 }); }
    }
    if (opts.length === 1) return opts[0].a;
    const t0 = timeMs ? Date.now() : 0;
    for (let total = 0; ; total++) {
      if (total >= playouts) break;
      if (timeMs && total >= minPlayouts && (total & 15) === 0 && Date.now() - t0 > timeMs) break;
      let o;
      if (total < opts.length) o = opts[total];
      else { let bu = -1; const lg = Math.log(total); for (const x of opts) { const u = x.w / x.n + C * Math.sqrt(lg / x.n); if (u > bu) { bu = u; o = x; } } }
      const t = determinize(s, me, rng), start = t.turnNo; _act(t, o.a);
      o.w += rollout(t, me, rng, depth, eps, start); o.n++;
    }
    let best = opts[0];
    for (const x of opts) if (x.n > best.n || (x.n === best.n && x.w > best.w)) best = x;
    return best.a;
  };
}
// Full-game play-outs with plain Greedy beat depth-limited ones scored by evaluate() by a wide
// margin here (the score race is easier to play out than to judge).
export const EXPERT = { playouts: 3000, depth: 99, eps: 0, C: 0.5 };
