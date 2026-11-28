// Bots for 34 Pitch to pay. Each is a function (state, rng) -> one action for s.toAct.
// None reads a hidden card: Expert reshuffles everything its side cannot see before each play-out
// (the cards pitched under a deck are public and stay where they are).

import { CARDS, BOARD, clone, _act, act, legalActions, actionKey } from './engine.js';

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
function shuffle(a, rng) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; } return a; }
const distinct = (a) => [...new Set(a)];
const worth = (id) => { const c = CARDS[id]; return c.kind === 'unit' ? c.atk + c.hp : c.dmg * 1.4; };

// ------------------------------------------------------------------ Random
export function randomBot(s, rng) { return pick(legalActions(s), rng); }

// ------------------------------------------------------------------ Greedy
// plays the most expensive card it can pay for, pitching its highest-pitch other cards first,
// and repeats; then attacks that destroy a unit and survive, then the enemy player.
function hitTarget(s, dmg) {
  const O = s.p[1 - s.toAct]; let best = -1;
  O.board.forEach((u, i) => { if (u.hp <= dmg && (best < 0 || CARDS[u.card].cost > CARDS[O.board[best].card].cost)) best = i; });
  return best;
}
// the next step towards paying for and playing the most expensive card affordable this turn
function payAndPlay(s, faceOnly) {
  const me = s.toAct, P = s.p[me];
  const ids = distinct(P.hand).sort((a, b) => CARDS[b].cost - CARDS[a].cost);
  for (const id of ids) {
    const c = CARDS[id];
    if (c.kind === 'unit' && P.board.length >= BOARD) continue;
    if (c.cost <= P.pool) {
      if (c.kind === 'unit') return { t: 'play', card: id };
      const i = faceOnly ? -1 : hitTarget(s, c.dmg);
      return { t: 'play', card: id, tgt: { side: 1 - me, i } };
    }
    const others = P.hand.slice(); others.splice(others.indexOf(id), 1);
    const sum = others.reduce((x, o) => x + CARDS[o].pitch, 0);
    if (P.pool + sum >= c.cost) { others.sort((a, b) => CARDS[b].pitch - CARDS[a].pitch); return { t: 'pitch', card: others[0] }; }
  }
  return null;
}
function tradeAttack(s) {
  const me = s.toAct, P = s.p[me], O = s.p[1 - me];
  for (let f = 0; f < P.board.length; f++) {
    const u = P.board[f]; if (!u.ready) continue;
    let best = -1;
    O.board.forEach((v, j) => { if (u.atk >= v.hp && v.atk < u.hp && (best < 0 || worth(v.card) > worth(O.board[best].card))) best = j; });
    if (best >= 0) return { t: 'attack', from: f, to: best };
  }
  return null;
}
function faceAttack(s) {
  const P = s.p[s.toAct];
  for (let f = 0; f < P.board.length; f++) if (P.board[f].ready) return { t: 'attack', from: f, to: -1 };
  return null;
}
export function greedyBot(s) { return payAndPlay(s, false) || tradeAttack(s) || faceAttack(s) || { t: 'end' }; }

// ------------------------------------------------------------------ Racer
// plays like Greedy, but every Hit and every attack goes at the enemy player
export function racerBot(s) { return payAndPlay(s, true) || faceAttack(s) || { t: 'end' }; }

// ------------------------------------------------------------------ evaluation
export function evaluate(s, me) {
  if (s.winner === me) return 1000;
  if (s.winner !== null) return s.winner === 'draw' ? 0 : -1000;
  let v = 0;
  for (const side of [0, 1]) {
    const P = s.p[side], sg = side === me ? 1 : -1;
    let x = 0.8 * P.life - 0.6 * Math.max(0, 8 - P.life) + 0.6 * P.hand.length;
    for (const u of P.board) x += 1.1 * u.atk + 0.7 * u.hp + 0.8;
    v += sg * x;
  }
  return v;
}
const winProb = (s, me) => s.winner === me ? 1 : s.winner === 'draw' ? 0.5 : s.winner !== null ? 0 : 1 / (1 + Math.exp(-evaluate(s, me) / 6));

// ------------------------------------------------------------------ Expert
// Determinized play-outs. Every candidate action is followed by a play-out on a world where the
// cards this side cannot see are reshuffled (both players play Greedy with lethal sense and a
// little noise), to the end of the game; successive halving spends the play-outs on the leaders,
// every arm seeing the same worlds.
function determinize(s, me, rng) {
  const t = clone(s);
  t.seed = (rng() * 4294967296) >>> 0;
  for (const side of [0, 1]) {
    const P = t.p[side], cut = P.deck.length - P.known;
    const top = P.deck.slice(0, cut), bottom = P.deck.slice(cut);
    if (side === me) { P.deck = shuffle(top, rng).concat(bottom); continue; }
    const pool = shuffle(P.hand.concat(top), rng);
    P.hand = pool.slice(0, P.hand.length); P.deck = pool.slice(P.hand.length).concat(bottom);
  }
  return t;
}
// lethal sense for play-outs: when the ready units and the Hits this turn can pay for reach his
// life, everything goes at him this turn
function faceMode(s) {
  const P = s.p[s.toAct], O = s.p[1 - s.toAct];
  let tot = 0; for (const u of P.board) if (u.ready) tot += u.atk;
  if (tot >= O.life) return true;
  let money = P.pool, cost = 0, dmg = 0;
  for (const id of P.hand) { const c = CARDS[id]; if (c.kind === 'spell') { cost += c.cost; dmg += c.dmg; } else money += c.pitch; }
  return tot + dmg >= O.life && money >= cost;
}
export function candidates(s) {
  const me = s.toAct, seen = new Set(), out = [];
  for (const a of legalActions(s)) {
    if (a.t === 'play' && a.tgt && a.tgt.side === me) continue;
    const k = actionKey(a); if (!seen.has(k)) { seen.add(k); out.push(a); }
  }
  return out;
}
// play-out policy: each side plays Greedy or Racer (drawn per play-out), with lethal sense and noise
function policy(t, rng, eps, style) {
  if (eps > 0 && rng() < eps) return pick(candidates(t), rng);
  if (style[t.toAct] === 'r' || faceMode(t)) return racerBot(t);
  return greedyBot(t);
}
function rollout(t, me, rng, eps, mix) {
  const style = [mix && rng() < 0.5 ? 'r' : 'g', mix && rng() < 0.5 ? 'r' : 'g'];
  let steps = 0;
  while (t.winner === null && steps < 1500) { _act(t, policy(t, rng, eps, style)); steps++; }
  return winProb(t, me);
}

// the settings the sim and the set positions use; the page uses the same with a clock
export const EXPERT = { playouts: 1500, eps: 0.03, mix: true };
export function expertBot({ playouts = 600, eps = 0.08, mix = true, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.toAct;
    const arms = candidates(s);
    if (arms.length === 1) return arms[0];
    for (const a of arms) { const t = act(s, a); if (t.winner === me) return a; }
    let alive = arms.map(a => ({ a, w: 0, n: 0 }));
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(3, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const world = determinize(s, me, rng), seed = (rng() * 4294967296) >>> 0;
        for (const st of alive) {
          const t = clone(world); _act(t, st.a);
          st.w += rollout(t, me, makeRng(seed), eps, mix); st.n++;
        }
        if (timeMs && Date.now() - t0 > timeMs) break;
      }
      alive.sort((x, y) => y.w / y.n - x.w / x.n);
      if (timeMs && Date.now() - t0 > timeMs) break;
      alive = alive.slice(0, Math.ceil(alive.length / 2));
    }
    return alive[0].a;
  };
}
