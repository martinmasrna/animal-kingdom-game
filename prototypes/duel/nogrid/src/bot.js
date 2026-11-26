// The bot. It only ever works from publicView(): the opponent's hand, both deck
// orders and the seed are blanked before any search, so it cannot peek.
import {
  CARDS, DECKS, clone, legalSets, seqCost, playedCards, openLegalActions,
  _playRoundInPlace, _playInPlace, _endTurnInPlace,
} from './engine.js';

export const BOT_DEFAULTS = { hiddenSamples: 6, hiddenIters: 300, hiddenBudget: 16000, openSamples: 8, purify: 0.03 };

export function makeRng(seed) {
  let a = (seed >>> 0) || 0x9e3779b9;
  return function () {
    let t = (a = (a + 0x6D2B79F5) | 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function shuffle(rng, a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); const x = a[i]; a[i] = a[j]; a[j] = x; }
  return a;
}

// What `side` is allowed to know. Hidden parts become null.
export function publicView(s, side) {
  const v = clone(s);
  const me = v.p[side], op = v.p[1 - side];
  v.seed = 0;
  op.hand = op.known.slice().concat(new Array(op.hand.length - op.known.length).fill(null));
  op.deck = new Array(op.deck.length).fill(null);
  me.deck = me.deck.slice().sort(); // contents are known (list minus seen cards), order is not
  return v;
}

// Cards of `q` the viewer has not seen: list minus face-up cards minus known hand cards.
function unseenPool(v, q) {
  const p = v.p[q];
  const left = { ...DECKS[p.hero] };
  for (const n of playedCards(v, q)) left[n]--;
  for (const n of p.known) left[n]--;
  const out = [];
  for (const [n, c] of Object.entries(left)) for (let i = 0; i < c; i++) out.push(n);
  return out;
}

// One complete world consistent with the view: the opponent's unknown hand cards and
// both deck orders are drawn at random.
export function sampleWorld(v, side, rng) {
  const w = clone(v);
  const op = w.p[1 - side], me = w.p[side];
  const pool = shuffle(rng, unseenPool(v, 1 - side));
  const unknown = op.hand.length - op.known.length;
  if (pool.length !== unknown + op.deck.length) throw new Error('sampleWorld: pool size mismatch');
  op.hand = op.known.concat(pool.slice(0, unknown));
  op.deck = pool.slice(unknown);
  me.deck = shuffle(rng, me.deck.slice());
  w.seed = Math.floor(rng() * 4294967296) | 0;
  return w;
}

// ---------- evaluation ----------
const WIN = 1000;
function windValue(p, name) {
  const c = CARDS[name];
  if (c.kind === 'Heavy') return 0.6 * (c.dmg + p.sharpen);
  if (name === 'Bandage') return 0.6 * Math.min(5, p.maxHp - p.hp);
  if (name === 'Sharpen') return 2;
  if (name === 'Meditate') return 0.5;
  return 0;
}
function sideValue(p) {
  const h = p.hand.length; // cards in hand matter less once there are plenty
  let v = p.hp * 1.0 + p.mana * 0.35 + 0.8 * Math.min(h, 4) + 0.2 * Math.max(0, h - 4) + p.sharpen * 2.5;
  if (p.hp <= 8) v -= (9 - p.hp) * 0.5; // being in lethal range costs extra
  for (const g of p.guards) v += g.type === 'Brace' ? 2 : g.used ? 0 : 1.5;
  for (const n of p.winding) v += windValue(p, n);
  return v;
}
// Open: the most damage the side to move can deal right now with Fast and Normal
// attacks (Slow ones only wind up), against the guards the other side has up.
function immediateDamage(s) {
  const p = s.p[s.turn], o = s.p[1 - s.turn];
  const opts = [...new Set(p.hand)].filter(n => CARDS[n].kind === 'Light' || (CARDS[n].kind === 'Heavy' && CARDS[n].speed !== 'Slow'));
  if (!p.usedBasics.includes('Jab')) opts.push('Jab');
  const dealt = (seq) => {
    const guards = o.guards.map(g => ({ ...g }));
    let d = 0;
    for (const n of seq) {
      const c = CARDS[n];
      for (let h = 0; h < c.hits; h++) {
        if (c.kind === 'Light') { const g = guards.find(g => g.type === 'Brace' || !g.used); if (g) { if (g.type !== 'Brace') g.used = true; continue; } }
        d += c.dmg + p.sharpen;
      }
    }
    return d;
  };
  let best = 0;
  const left = 2 - p.actions;
  for (let i = 0; i < opts.length; i++) {
    if (left >= 1 && seqCost(p, [opts[i]]) <= p.mana) best = Math.max(best, dealt([opts[i]]));
    if (left < 2) continue;
    for (let j = 0; j < opts.length; j++) {
      if (i === j && (opts[i] === 'Jab' || p.hand.filter(n => n === opts[i]).length < 2)) continue;
      const q = [opts[i], opts[j]];
      if (seqCost(p, q) <= p.mana) best = Math.max(best, dealt(q));
    }
  }
  return best;
}
const LETHAL = 25;
export function evaluate(s, side) {
  if (s.winner !== null) return s.winner === 'draw' ? 0 : s.winner === side ? WIN : -WIN;
  let v = sideValue(s.p[side]) - sideValue(s.p[1 - side]);
  // in Open, a kill already on the table for the side to move is nearly a win
  if (s.version === 'open' && immediateDamage(s) >= s.p[1 - s.turn].hp) v += s.turn === side ? LETHAL : -LETHAL;
  return v;
}

// =====================================================================
// Hidden: a simultaneous game per round, solved by regret matching
// =====================================================================

function keyOf(set) { return set.join('+'); }

function payoffMatrix(world, side, rows, cols) {
  const R = rows.length, C = cols.length, A = new Float64Array(R * C);
  const choices = [null, null];
  for (let r = 0; r < R; r++) for (let c = 0; c < C; c++) {
    choices[side] = rows[r]; choices[1 - side] = cols[c];
    const t = _playRoundInPlace(clone(world), choices);
    A[r * C + c] = evaluate(t, side);
  }
  return A;
}

function rmStrategy(reg, out) {
  let sum = 0;
  for (let i = 0; i < reg.length; i++) sum += reg[i] > 0 ? reg[i] : 0;
  if (sum <= 0) { out.fill(1 / reg.length); return out; }
  for (let i = 0; i < reg.length; i++) out[i] = reg[i] > 0 ? reg[i] / sum : 0;
  return out;
}

// Bot (rows) against a player whose hand is one of K sampled hands; the player has
// his own strategy per sampled hand (he knows his hand). Payoff averaged over hands.
export function solveBayesian(mats, R, Cs, iters) {
  const K = mats.length;
  const rReg = new Float64Array(R), rSum = new Float64Array(R), x = new Float64Array(R), u = new Float64Array(R);
  const cReg = Cs.map(C => new Float64Array(C)), ys = Cs.map(C => new Float64Array(C)), v = Cs.map(C => new Float64Array(C));
  for (let it = 1; it <= iters; it++) {
    rmStrategy(rReg, x);
    for (let k = 0; k < K; k++) rmStrategy(cReg[k], ys[k]);
    u.fill(0);
    for (let k = 0; k < K; k++) {
      const A = mats[k], C = Cs[k], y = ys[k], vk = v[k];
      vk.fill(0);
      for (let r = 0; r < R; r++) {
        let acc = 0; const base = r * C, xr = x[r];
        for (let c = 0; c < C; c++) { const a = A[base + c]; acc += a * y[c]; vk[c] -= xr * a; }
        u[r] += acc / K;
      }
      let ev = 0; for (let c = 0; c < C; c++) ev += y[c] * vk[c];
      const reg = cReg[k];
      for (let c = 0; c < C; c++) { const n = reg[c] + vk[c] - ev; reg[c] = n > 0 ? n : 0; }
    }
    let ev = 0; for (let r = 0; r < R; r++) ev += x[r] * u[r];
    for (let r = 0; r < R; r++) { const n = rReg[r] + u[r] - ev; rReg[r] = n > 0 ? n : 0; rSum[r] += it * x[r]; }
  }
  let tot = 0; for (let r = 0; r < R; r++) tot += rSum[r];
  return Array.from(rSum, a => a / tot);
}

// Choose the bot's set for this round. Returns { choice, strategy: [{set, p}] }.
export function botHiddenDetail(s, side, rng, opt = BOT_DEFAULTS) {
  const view = publicView(s, side);
  let rows = legalSets(view, side);
  if (rows.length === 1) return { choice: rows[0], strategy: [{ set: rows[0], p: 1 }] };
  let K = opt.hiddenSamples;
  let worlds = Array.from({ length: K }, () => sampleWorld(view, side, rng));
  let colsK = worlds.map(w => legalSets(w, 1 - side));
  const cost = () => rows.length * colsK.reduce((a, c) => a + c.length, 0);
  while (K > 2 && cost() > opt.hiddenBudget) { K--; worlds.pop(); colsK.pop(); }
  if (cost() > opt.hiddenBudget) {
    // prune: score rows and columns on the first world, keep the best of each
    const A = payoffMatrix(worlds[0], side, rows, colsK[0]);
    const R = rows.length, C = colsK[0].length;
    const keep = Math.max(8, Math.floor(Math.sqrt(opt.hiddenBudget / K)));
    const rowScore = rows.map((_, r) => { let m = Infinity, sum = 0; for (let c = 0; c < C; c++) { const a = A[r * C + c]; sum += a; if (a < m) m = a; } return sum / C + Math.max(m, -WIN / 2); });
    const colScore = colsK[0].map((_, c) => { let m = -Infinity, sum = 0; for (let r = 0; r < R; r++) { const a = A[r * C + c]; sum += a; if (a > m) m = a; } return -(sum / R) - Math.min(m, WIN / 2); });
    const rIdx = rows.map((_, i) => i).sort((a, b) => rowScore[b] - rowScore[a]).slice(0, keep);
    const cKeys = new Set(colsK[0].map((_, i) => i).sort((a, b) => colScore[b] - colScore[a]).slice(0, keep).map(i => keyOf(colsK[0][i])));
    cKeys.add('');
    rows = rIdx.map(i => rows[i]);
    colsK = colsK.map(cols => { const f = cols.filter(c => cKeys.has(keyOf(c))); return f.length ? f.slice(0, keep) : cols.slice(0, keep); });
  }
  const mats = worlds.map((w, k) => payoffMatrix(w, side, rows, colsK[k]));
  let x = solveBayesian(mats, rows.length, colsK.map(c => c.length), opt.hiddenIters);
  // drop the noise of the average strategy, then sample
  let tot = 0; x = x.map(p => (p < opt.purify ? 0 : p)); for (const p of x) tot += p;
  if (tot <= 0) { x = x.map(() => 1); tot = x.length; }
  let r = rng() * tot, pick = 0;
  for (let i = 0; i < x.length; i++) { r -= x[i]; if (r <= 0 && x[i] > 0) { pick = i; break; } pick = x[i] > 0 ? i : pick; }
  const strategy = rows.map((set, i) => ({ set, p: x[i] / tot })).filter(e => e.p > 0).sort((a, b) => b.p - a.p);
  return { choice: rows[pick], strategy };
}
export function botHidden(s, side, rng, opt) { return botHiddenDetail(s, side, rng, opt).choice; }

// =====================================================================
// Open: search own turn, assume the opponent's best reply on sampled hands
// =====================================================================

function canonicalSecond(a, b) {
  // [a, b] and [b, a] reach the same state unless one draws cards or the order of
  // two Light attacks or two guards matters; keep one order otherwise.
  if (a === 'Study' || b === 'Study') return true;
  const ka = CARDS[a].kind, kb = CARDS[b].kind;
  if ((ka === 'Light' && kb === 'Light') || (ka === 'Defence' && kb === 'Defence')) return true;
  return a <= b;
}

// All states the side to move can reach by the end of its turn (sequences of its remaining actions).
function turnLeaves(s, fn) {
  fn(s, null);
  if (s.winner !== null) return;
  for (const a of openLegalActions(s)) {
    const t = _playInPlace(clone(s), a);
    fn(t, a);
    if (t.winner !== null) continue;
    for (const b of openLegalActions(t)) {
      if (!canonicalSecond(a, b)) continue;
      fn(_playInPlace(clone(t), b), a);
    }
  }
}

// Value for `side` of a state at the end of side's turn: the opponent plays his best
// turn, then side's winding cards resolve at the start of side's next turn.
function replyValue(t, side) {
  if (t.winner !== null) return evaluate(t, side);
  const o = _endTurnInPlace(clone(t));
  if (o.winner !== null) return evaluate(o, side);
  let best = Infinity;
  turnLeaves(o, (u) => {
    let val;
    if (u.winner !== null) val = evaluate(u, side);
    else val = evaluate(_endTurnInPlace(clone(u)), side);
    if (val < best) best = val;
  });
  return best;
}

// Next action for the side to move, or null to end the turn.
export function botOpenDetail(s, rng, opt = BOT_DEFAULTS) {
  const side = s.turn;
  const view = publicView(s, side);
  const first = [null].concat(openLegalActions(view));
  if (first.length === 1) return { action: null, values: [] };
  const K = opt.openSamples;
  const totals = new Map(first.map(a => [a, 0]));
  for (let k = 0; k < K; k++) {
    const w = sampleWorld(view, side, rng);
    const best = new Map(first.map(a => [a, -Infinity]));
    const actsLeft = 2 - w.p[side].actions;
    // leaf values grouped by first action of this turn
    const consider = (t, a) => { const v = replyValue(t, side); if (v > best.get(a)) best.set(a, v); };
    consider(w, null);
    for (const a of first) {
      if (a === null) continue;
      const t = _playInPlace(clone(w), a);
      consider(t, a);
      if (t.winner !== null || actsLeft < 2) continue;
      for (const b of openLegalActions(t)) consider(_playInPlace(clone(t), b), a);
    }
    for (const a of first) totals.set(a, totals.get(a) + best.get(a) / K);
  }
  let pick = null, bv = -Infinity;
  for (const a of first) { const v = totals.get(a); if (v > bv + 1e-9) { bv = v; pick = a; } }
  return { action: pick, values: first.map(a => ({ action: a, value: totals.get(a) })) };
}
export function botOpenAction(s, rng, opt) { return botOpenDetail(s, rng, opt).action; }
