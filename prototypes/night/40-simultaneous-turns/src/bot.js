// Bots for 40 Simultaneous turns. Each is a function (state, rng) -> the plan for s.toAct.
// None reads a hidden card or the other seat's plan: Expert reshuffles what its side cannot see
// and samples the other side's plan from a model of it.

import { CARDS, BOARD, clone, _act, hidePlans, planKey } from './engine.js';

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
const val = (u) => u.atk + u.hp;

// ------------------------------------------------------------------ plan pieces
// the most expensive cards first, while mana and board slots last
function costliestSet(P, rng, noise = 0) {
  const ids = P.hand.slice().sort((a, b) => CARDS[b].cost - CARDS[a].cost || (a < b ? -1 : 1));
  if (noise && rng) shuffle(ids, rng);
  let mana = P.mana, slots = BOARD - P.board.length; const out = [];
  for (const id of ids) {
    const c = CARDS[id];
    if (c.cost > mana || (c.kind === 'unit' && slots <= 0)) continue;
    if (noise && rng && rng() < noise) continue;
    mana -= c.cost; if (c.kind === 'unit') slots--; out.push(id);
  }
  return out;
}
// spells at the most valuable enemy unit each one destroys (counting earlier spells), else at the player
function targetSpells(s, side, ids, face) {
  const O = s.p[1 - side], left = new Map(O.board.map(u => [u.uid, u.hp])), plays = [];
  const spells = ids.filter(id => CARDS[id].kind === 'spell').sort((a, b) => CARDS[a].dmg - CARDS[b].dmg);
  for (const id of ids) if (CARDS[id].kind === 'unit') plays.push({ card: id });
  for (const id of spells) {
    const d = CARDS[id].dmg; let best = null;
    if (!face) for (const u of O.board) { const h = left.get(u.uid); if (h > 0 && h <= d && (!best || val(u) > val(best))) best = u; }
    if (best) { left.set(best.uid, 0); plays.push({ card: id, tgt: { side: 1 - side, uid: best.uid } }); }
    else plays.push({ card: id, tgt: { side: 1 - side, uid: -1 } });
  }
  return { plays, left };
}
// each unit attacks the enemy unit it destroys and survives against (the most valuable, not one
// already dealt with), otherwise the enemy player
function tradeAttacks(s, side, left) {
  const P = s.p[side], O = s.p[1 - side], out = [], taken = new Set();
  for (const u of P.board.slice().sort((a, b) => b.atk - a.atk)) {
    let best = null;
    for (const v of O.board) { const h = left.get(v.uid); if (h > 0 && !taken.has(v.uid) && u.atk >= h && v.atk < u.hp && (!best || val(v) > val(best))) best = v; }
    if (best) { taken.add(best.uid); out.push({ from: u.uid, to: best.uid }); } else out.push({ from: u.uid, to: -1 });
  }
  return out;
}
const faceAttacks = (s, side) => s.p[side].board.map(u => ({ from: u.uid, to: -1 }));

export function greedyBot(s) {
  const side = s.toAct, ids = costliestSet(s.p[side]);
  const { plays, left } = targetSpells(s, side, ids, false);
  return { t: 'plan', plays, attacks: tradeAttacks(s, side, left) };
}
export function racerBot(s) {
  const side = s.toAct, ids = costliestSet(s.p[side]);
  return { t: 'plan', plays: targetSpells(s, side, ids, true).plays, attacks: faceAttacks(s, side) };
}
export function randomBot(s, rng) {
  const side = s.toAct, P = s.p[side], O = s.p[1 - side];
  const ids = shuffle(P.hand.slice(), rng); let mana = P.mana, slots = BOARD - P.board.length; const plays = [];
  for (const id of ids) {
    const c = CARDS[id]; if (c.cost > mana || rng() < 0.5) continue;
    if (c.kind === 'unit') { if (slots <= 0) continue; slots--; plays.push({ card: id }); }
    else { const tside = rng() < 0.5 ? 1 - side : side, B = s.p[tside].board, k = Math.floor(rng() * (B.length + 1)); plays.push({ card: id, tgt: { side: tside, uid: k === B.length ? -1 : B[k].uid } }); }
    mana -= c.cost;
  }
  const attacks = [];
  for (const u of P.board) { const k = Math.floor(rng() * (O.board.length + 2)); if (k === O.board.length + 1) continue; attacks.push({ from: u.uid, to: k === O.board.length ? -1 : O.board[k].uid }); }
  return { t: 'plan', plays, attacks };
}

// ------------------------------------------------------------------ Expert
// Candidate plans: card sets the mana allows (the fullest ones), spells aimed by the kill rule or at
// the player, and attack schemes (all at the player; trades that survive; trades that kill a unit
// worth at least the attacker; ganging up on their best unit). Each candidate is scored by
// play-outs: a world with the hidden cards reshuffled, the other side's plan drawn from a model of
// it (Greedy, Racer, or a noisy one of those on its reshuffled hand), then both sides playing on
// to the end as Greedy or Racer. Successive halving, every arm seeing the same worlds.
function cardSets(P) {
  const ids = [...new Set(P.hand)], cnt = ids.map(id => P.hand.filter(x => x === id).length), sets = [];
  const slots = BOARD - P.board.length;
  const rec = (k, cur, mana, units) => {
    if (k === ids.length) {
      // maximal: no card left in hand fits
      const rest = P.hand.slice(); for (const c of cur) rest.splice(rest.indexOf(c), 1);
      const fits = rest.some(id => CARDS[id].cost <= P.mana - mana && (CARDS[id].kind !== 'unit' || units < slots));
      sets.push({ ids: cur.slice(), mana, maximal: !fits, units }); return;
    }
    const c = CARDS[ids[k]];
    for (let n = 0; n <= cnt[k]; n++) {
      if (mana + n * c.cost > P.mana) break;
      if (c.kind === 'unit' && units + n > slots) break;
      for (let i = 0; i < n; i++) cur.push(ids[k]);
      rec(k + 1, cur, mana + n * c.cost, units + (c.kind === 'unit' ? n : 0));
      for (let i = 0; i < n; i++) cur.pop();
    }
  };
  rec(0, [], 0, 0);
  const max = sets.filter(x => x.maximal).sort((a, b) => b.mana - a.mana || b.ids.length - a.ids.length);
  const keep = max.slice(0, 6);
  // the fullest set that keeps every spell in hand
  const noSpell = sets.filter(x => x.ids.every(id => CARDS[id].kind === 'unit')).sort((a, b) => b.mana - a.mana)[0];
  if (noSpell) keep.push(noSpell);
  return keep.map(x => x.ids);
}
function attackSchemes(s, side, left) {
  const P = s.p[side], O = s.p[1 - side], out = [faceAttacks(s, side), tradeAttacks(s, side, left)];
  // value trades: kill a unit worth at least the attacker, even dying
  {
    const taken = new Set(), at = [];
    for (const u of P.board.slice().sort((a, b) => b.atk - a.atk)) {
      let best = null;
      for (const v of O.board) { const h = left.get(v.uid); if (h > 0 && !taken.has(v.uid) && u.atk >= h && (v.atk < u.hp || val(v) >= val(u)) && (!best || val(v) > val(best))) best = v; }
      if (best) { taken.add(best.uid); at.push({ from: u.uid, to: best.uid }); } else at.push({ from: u.uid, to: -1 });
    }
    out.push(at);
  }
  // gang up on their most valuable unit still standing: the fewest attackers that destroy it
  const targets = O.board.filter(v => left.get(v.uid) > 0).sort((a, b) => val(b) - val(a));
  if (targets.length) {
    const v = targets[0], at = []; let need = left.get(v.uid);
    for (const u of P.board.slice().sort((a, b) => b.atk - a.atk)) { if (need > 0) { at.push({ from: u.uid, to: v.uid }); need -= u.atk; } else at.push({ from: u.uid, to: -1 }); }
    if (need <= 0) out.push(at);
  }
  return out;
}
export function candidates(s) {
  const side = s.toAct, P = s.p[side], seen = new Set(), out = [];
  const add = (pl) => { const k = planKey(pl); if (!seen.has(k)) { seen.add(k); out.push(pl); } };
  add(greedyBot(s)); add(racerBot(s));
  for (const ids of cardSets(P)) {
    for (const face of [false, true]) {
      if (face && !ids.some(id => CARDS[id].kind === 'spell')) continue;
      const { plays, left } = targetSpells(s, side, ids, face);
      for (const attacks of attackSchemes(s, side, left)) add({ t: 'plan', plays, attacks });
    }
  }
  return out;
}
// the model of the other side, on its reshuffled hand
function modelPlan(s, rng) {
  const r = rng();
  if (r < 0.35) return greedyBot(s);
  if (r < 0.6) return racerBot(s);
  const side = s.toAct, ids = costliestSet(s.p[side], rng, 0.2);
  const { plays, left } = targetSpells(s, side, ids, rng() < 0.3);
  const schemes = attackSchemes(s, side, left);
  return { t: 'plan', plays, attacks: pick(schemes, rng) };
}
function determinize(s, me, rng) {
  const t = hidePlans(s);
  t.seed = (rng() * 4294967296) >>> 0;
  const O = t.p[1 - me], pool = shuffle(O.hand.concat(O.deck), rng);
  O.hand = pool.slice(0, O.hand.length); O.deck = pool.slice(O.hand.length);
  shuffle(t.p[me].deck, rng);
  return t;
}
function rollout(t, me, rng, style) {
  let k = 0;
  while (t.winner === null && k++ < 200) {
    const pl = style[t.toAct] === 'r' ? racerBot(t) : style[t.toAct] === 'n' ? modelPlan(t, rng) : greedyBot(t);
    _act(t, pl);
  }
  return t.winner === me ? 1 : t.winner === 'draw' || t.winner === null ? 0.5 : 0;
}
export const EXPERT = { playouts: 2500 };
export function expertBot({ playouts = 1500, timeMs = 0 } = {}) {
  return function (s, rng) {
    const me = s.toAct;
    const arms = candidates(s);
    if (arms.length === 1) return arms[0];
    let alive = arms.map(a => ({ a, w: 0, n: 0 }));
    const rounds = Math.max(1, Math.ceil(Math.log2(alive.length)));
    const t0 = timeMs ? Date.now() : 0;
    for (let r = 0; r < rounds && alive.length > 1; r++) {
      const per = Math.max(4, Math.floor(playouts / rounds / alive.length));
      for (let i = 0; i < per; i++) {
        const world = determinize(s, me, rng);
        // the other side's plan, made on its own (reshuffled) view
        const view = clone(world); view.toAct = 1 - me;
        const theirs = modelPlan(view, rng);
        const seed = (rng() * 4294967296) >>> 0, st0 = rng(), st1 = rng();
        const style = [st0 < 0.4 ? 'g' : st0 < 0.8 ? 'r' : 'n', st1 < 0.4 ? 'g' : st1 < 0.8 ? 'r' : 'n'];
        for (const st of alive) {
          const t = clone(world);
          t.plans = [null, null]; t.plans[1 - me] = theirs; t.plans[me] = null;
          // submit in seat order
          t.toAct = 0;
          if (me === 0) { _act(t, st.a); t.toAct === 1 && _act(t, theirs); }
          else { _act(t, theirs); _act(t, st.a); }
          st.w += rollout(t, me, makeRng(seed), style); st.n++;
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
