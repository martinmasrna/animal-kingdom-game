// Toy 6: the stamina duel, both choosing at once.
// Two fighters on a line, health and stamina. Each round both pick one action in secret,
// then reveal. Everything happens at the same moment: steps settle first, then blows land.
//   Step forward / Step back: 1 stamina. Two steps into the same tile: neither moves.
//   Strike: 3 stamina, 3 damage if adjacent after the steps. Stopped by a guard.
//   Guard: 2 stamina, stops the other's strike this round.
//   Rest: free; you recover double this round.
// At the end of every round both recover REGEN stamina (Rest: twice that), never above the cap.
// Pure from the outside: resolve() returns a new state.

export const R = { recovery: false, grab: false, grabCost: 2, grabDmg: 3, lunge: false, lungeCost: 4, len: 5, hp: 20, stamina: 10, cap: 10, regen: 2, strike: 3, strikeCost: 3, guardCost: 2, stepCost: 1, roundLimit: 60 };
export function setRules(o) { Object.assign(R, o); }

export const ACTIONS_BASE = ['F', 'B', 'S', 'G', 'Z']; // forward, back, strike, guard, rest; L = lunge (step in and strike)
export const actions = () => ACTIONS_BASE.concat(R.lunge ? ['L'] : [], R.grab ? ['T'] : []);
export const COST = (a) => ({ F: R.stepCost, B: R.stepCost, S: R.strikeCost, G: R.guardCost, Z: 0, L: R.lungeCost, T: R.grabCost })[a];

export function newMatch() {
  return { pos: [0, R.len - 1], hp: [R.hp, R.hp], st: [R.stamina, R.stamina], off: [0, 0], round: 1, winner: null };
}
export function legal(s, side) { return actions().filter(a => COST(a) <= s.st[side] && !(s.off && s.off[side] && !['F', 'B', 'Z'].includes(a))); }

export function resolve(s, acts, ev) {
  const t = { pos: s.pos.slice(), hp: s.hp.slice(), st: s.st.slice(), off: [0, 0], round: s.round + 1, winner: null };
  const e = (x) => { ev && ev.push(x); if (R.recovery && ['miss', 'blocked', 'grabfail', 'grabclash'].includes(x.t)) t.off[x.side] = 1; };
  for (const i of [0, 1]) t.st[i] -= COST(acts[i]);
  // steps: player 0 faces right (+1), player 1 faces left (-1)
  const dir = [1, -1];
  const want = [0, 1].map(i => (acts[i] === 'F' || acts[i] === 'L') ? t.pos[i] + dir[i] : acts[i] === 'B' ? t.pos[i] - dir[i] : t.pos[i]);
  for (const i of [0, 1]) if (want[i] < 0 || want[i] >= R.len) { want[i] = t.pos[i]; if (acts[i] === 'B') e({ t: 'wall', side: i }); }
  if (want[0] === want[1]) { e({ t: 'clash' }); want[0] = t.pos[0]; want[1] = t.pos[1]; } // both into one tile: neither moves
  else if (want[0] > want[1]) { want[0] = t.pos[0]; want[1] = t.pos[1]; }                 // can't pass through
  else {
    // a step into the tile the other is standing on (and not leaving) is stopped
    if (want[0] === t.pos[1] && want[1] === t.pos[1]) want[0] = t.pos[0];
    if (want[1] === t.pos[0] && want[0] === t.pos[0]) want[1] = t.pos[1];
  }
  for (const i of [0, 1]) if (want[i] !== t.pos[i]) { e({ t: 'step', side: i, from: t.pos[i], to: want[i] }); t.pos[i] = want[i]; }
  // blows
  const adj = t.pos[1] - t.pos[0] === 1;
  for (const i of [0, 1]) if (acts[i] === 'S' || acts[i] === 'L') {
    const o = 1 - i;
    if (!adj) e({ t: 'miss', side: i });
    else if (acts[o] === 'G') e({ t: 'blocked', side: i });
    else { t.hp[o] -= R.strike; e({ t: 'hit', side: i, dmg: R.strike }); }
  }
  // grabs: work only when adjacent; a strike beats a grab (the grabber is hit and the grab fails); two grabs cancel
  for (const i of [0, 1]) if (acts[i] === 'T') {
    const o = 1 - i;
    if (!adj) e({ t: 'miss', side: i });
    else if (acts[o] === 'S' || acts[o] === 'L') e({ t: 'grabfail', side: i });
    else if (acts[o] === 'T') e({ t: 'grabclash', side: i });
    else { t.hp[o] -= R.grabDmg; e({ t: 'grab', side: i, dmg: R.grabDmg }); }
  }
  for (const i of [0, 1]) if (acts[i] === 'G' && acts[1 - i] !== 'S') e({ t: 'idleguard', side: i });
  // recovery
  for (const i of [0, 1]) t.st[i] = Math.min(R.cap, t.st[i] + (acts[i] === 'Z' ? 2 * R.regen : R.regen));
  const a = t.hp[0] <= 0, b = t.hp[1] <= 0;
  if (a || b) t.winner = a && b ? 'draw' : a ? 1 : 0;
  else if (t.round > R.roundLimit) t.winner = R.timeDecides ? (t.hp[0] === t.hp[1] ? 'draw' : t.hp[0] > t.hp[1] ? 0 : 1) : 'draw';
  if (t.winner !== null) e({ t: 'end', winner: t.winner });
  return t;
}
