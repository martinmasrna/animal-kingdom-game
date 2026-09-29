// What the board shows and what changed since the last view, as plain data (no DOM): the board renderer draws from
// these, and test/turn.test.mjs checks them. Everything is in viewer space; a board is { "col,row": [unit, ...] } with the
// top unit last, a unit { iid, id, owner, str, timer }.

const key = (c, r) => `${c},${r}`;
const top = (board, cr) => (board[cr] || []).slice(-1)[0];

// Each den's ten pits, bottom first: how many ripe fruit (food stored) and ghost fruit (next turn's income) each holds.
// One fruit is one food, so a pit holds winFood / 10.
export function pitStates(food, income, winFood, pits = 10) {
  const per = winFood / pits, ripe = Math.min(food, winFood), ghost = Math.max(0, Math.min(income, winFood - ripe));
  return Array.from({ length: pits }, (_, i) => {
    const r = Math.max(0, Math.min(per, ripe - i * per)), t = Math.max(0, Math.min(per, ripe + ghost - i * per));
    return { ripe: r, ghost: t - r };
  });
}

// The regions a player holds: every corner's top unit is theirs.
export function heldRegions(regions, board) {
  return regions.flatMap(reg => {
    const [c, r] = reg.c, owners = [key(c, r), key(c + 1, r), key(c, r + 1), key(c + 1, r + 1)].map(cr => (top(board, cr) || {}).owner);
    return owners.every(o => o && o === owners[0]) ? [{ ...reg, owner: owners[0] }] : [];
  });
}

// What happened on the board between two views. `fx` are the effects of the moves in between (a move's fx, with owners
// in viewer space). Returns:
//   landed    crossroads whose top unit is new (a piece arrived there);
//   covered   the subset where the new piece covered one that is still under it;
//   leaving   top units gone from the board: [{ cr, unit, how: 'removed' | 'bounce' }];
//   strength  units still on the board whose strength changed: Map iid -> 'up' | 'down'.
export function boardChanges(before, after, fx = []) {
  const landed = new Set(), covered = new Set(), strength = new Map();
  if (!before) return { landed, covered, leaving: [], strength };
  for (const cr of Object.keys(after)) {
    const now = top(after, cr), was = top(before, cr);
    if (now && (!was || was.iid !== now.iid)) { landed.add(cr); if (was) covered.add(cr); }
  }
  const onBoard = new Set(Object.values(after).flat().map(u => u.iid));
  const bounced = new Set(fx.filter(f => f.k === 'bounce').map(f => f.card + f.owner));
  const leaving = Object.entries(before).flatMap(([cr, st]) => {
    const u = st[st.length - 1];
    return u && u.iid !== undefined && !onBoard.has(u.iid) ? [{ cr, unit: u, how: bounced.has(u.id + u.owner) ? 'bounce' : 'removed' }] : [];
  });
  const was = new Map(Object.values(before).flat().map(u => [u.iid, u.str]));
  for (const u of Object.values(after).flat()) if (was.has(u.iid) && was.get(u.iid) !== u.str) strength.set(u.iid, u.str > was.get(u.iid) ? 'up' : 'down');
  return { landed, covered, leaving, strength };
}

// Income in flight: one fruit per food gained, flown from the player's held stones (each sends as many as it pays) to the
// pit it fills, in the order the pits fill. Returns [{ from: stone index, pit, delay }]; empty when food came from
// anything but held regions (no stone to fly from) or nothing was gained.
export function incomeFlights(foodBefore, foodAfter, winFood, stones, { gap = 0.035, pits = 10 } = {}) {
  const per = winFood / pits, n = Math.min(foodAfter, winFood) - foodBefore;
  if (n <= 0 || !stones.length) return [];
  const sources = stones.flatMap((s, i) => Array(s.food).fill(i));
  return Array.from({ length: n }, (_, j) => ({ from: sources[j % sources.length], pit: Math.min(pits - 1, Math.floor((foodBefore + j) / per)), delay: j * gap }));
}
