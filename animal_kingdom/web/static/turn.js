// What the board shows and what changed since the last view, as plain data (no DOM): the board renderer draws from
// these, and test/turn.test.mjs checks them. Everything is in viewer space; a board is { "col,row": [unit, ...] } with the
// top unit last, a unit { iid, id, owner, str, timer }.

const key = (c, r) => `${c},${r}`;
const top = (board, cr) => (board[cr] || []).slice(-1)[0];


// The regions a player holds: every corner's top unit is theirs.
export function heldRegions(regions, board) {
  return regions.flatMap(reg => {
    const [c, r] = reg.c, owners = (reg.corners || [key(c, r), key(c + 1, r), key(c, r + 1), key(c + 1, r + 1)]).map(cr => (top(board, cr) || {}).owner);
    return owners.every(o => o && o === owners[0]) ? [{ ...reg, owner: owners[0] }] : [];
  });
}

// What happened on the board between two views. `fx` are the effects of the moves in between (a move's fx, with owners
// in viewer space). Returns:
//   landed    crossroads whose top unit is new (a piece arrived there);
//   covered   the subset where the new piece covered one that is still under it;
//   leaving   top units gone from the board: [{ cr, unit, how: 'removed' | 'bounce' }];
export function boardChanges(before, after, fx = []) {
  const landed = new Set(), covered = new Set();
  if (!before) return { landed, covered, leaving: [] };
  for (const cr of Object.keys(after)) {
    const now = top(after, cr), was = top(before, cr);
    // a new top that was already in the stack was uncovered (its coverer left), not landed
    const uncovered = now && (before[cr] || []).some(u => u.iid === now.iid);
    if (now && (!was || was.iid !== now.iid) && !uncovered) { landed.add(cr); if (was) covered.add(cr); }
  }
  const onBoard = new Set(Object.values(after).flat().map(u => u.iid));
  const bounced = new Set(fx.filter(f => f.k === 'bounce').map(f => f.card + f.owner));
  const leaving = Object.entries(before).flatMap(([cr, st]) => {
    const u = st[st.length - 1];
    return u && u.iid !== undefined && !onBoard.has(u.iid) ? [{ cr, unit: u, how: bounced.has(u.id + u.owner) ? 'bounce' : 'removed' }] : [];
  });
  return { landed, covered, leaving };   // strength changes are events (the timeline's strength step), not a diff
}


