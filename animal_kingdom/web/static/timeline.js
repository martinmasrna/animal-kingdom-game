// The animation timeline (plain data, no DOM; test/timeline.test.mjs checks it). A view from the server carries the game's
// events, in the order they happened (engine state.events: placed, covered, removed, bounced, drawn, food, turns). Between
// the view on screen and a new one, `plan` turns the events the screen hasn't shown into steps: one view per step, the
// board exactly as it stood after that step, ending with the new view itself. The screen plays the steps in order, each
// for its declared length (DUR), so nothing waits on a guess: "Your turn" is a step after the opponent's last card has
// landed and eaten, an egg hatching at your turn's start is a step after it, and a choice or the result shows only once
// the last step is done.

// How long each step holds the screen, in seconds: the one place these lengths live (the board's animations fit inside).
// The animal whose effect removed or moved a unit (the engine stamps each event with its cause card): the one on the
// board nearest the victim, often right under it (spines) or beside it (Hippopotamus, Grizzly Bear). It answers in the
// removal's beat, so a player sees what did it (Martin, 2026-10-02). The engine names the very unit when it knows it
// (`causeIid`: of two Servals, the one that roared); only an event without it falls back to the nearest of that card.
// None when the cause isn't on the board.
function culprit(board, cause, cr, causeIid) {
  if (!cause || !cr) return null;
  if (causeIid != null) { for (const [at, st] of Object.entries(board)) if (st.some(u => u.iid === causeIid)) return at; return null; }
  const [c0, r0] = cr.split(',').map(Number);
  let best = null, bd = Infinity;
  for (const [at, st] of Object.entries(board)) {
    if (!st.some(u => u.id === cause)) continue;
    const [c, r] = at.split(',').map(Number), d = Math.abs(c - c0) + Math.abs(r - r0);
    if (d < bd) { bd = d; best = at; }
  }
  return best;
}

export const DUR = { leader: 1.1, discard: 0.5, reveal: 0.95, land: 0.5, remove: 0.85, draw: 0.5, yourturn: 1.5, raid: 0.9 };
// Food in flight: one fruit per food, 0.035 s apart, each flying 0.7 s, then the count settles.
export const foodDur = n => Math.min(2.4, 0.7 + 0.035 * Math.max(0, n - 1) + 0.3);

const clone = x => JSON.parse(JSON.stringify(x));
const lastSeq = v => { const ev = v && v.game && v.game.events; return ev && ev.length ? ev[ev.length - 1].seq : 0; };

// The events in `next` that `prev` hadn't shown, or null when they can't be told apart (another game, a different seat,
// or events from before the oldest one kept): then the new view simply replaces the old.
export function newEvents(prev, next) {
  if (!prev || !next || !prev.game || !next.game || prev.you !== next.you || prev.id !== next.id) return null;
  // A rematch starts its own events: nothing of the last game plays. The view that ends a game also adds a
  // result, but its last move still plays in full before the end shows (Martin, 2026-10-02: a food win was announced as
  // the card landed, before its fruit had flown).
  if ((prev.rematches || 0) !== (next.rematches || 0) && next.phase === 'playing') return null;
  const ev = next.game.events || [], seen = lastSeq(prev);
  if (!ev.length || (ev[0].seq > seen + 1 && seen > 0)) return null;
  return ev.filter(e => e.seq > seen);
}

// The steps from `prev` to `next`: [{ view, step: { kind, dur, ... } }], the last being `next` itself (step null).
export function plan(prev, next, cards = {}) {
  const fresh = newEvents(prev, next);
  if (!fresh || !fresh.length) return [{ view: next, step: null }];
  const you = next.you, them = you === 'A' ? 'B' : 'A';
  const g0 = prev.game, gN = next.game;
  const s = { board: clone(g0.board), food: { ...g0.food }, handCount: { ...g0.handCount }, hand: clone(g0.hand), current: g0.current };
  const finalCard = iid => gN.hand.find(x => x.iid === iid);
  const finalUnit = iid => { for (const st of Object.values(gN.board)) for (const u of st) if (u.iid === iid) return u; return null; };
  const view = () => {
    const v = clone(next);
    Object.assign(v.game, { board: clone(s.board), food: { ...s.food }, handCount: { ...s.handCount }, hand: clone(s.hand),
      current: s.current, toAct: null, pending: null, legal: null, result: null, decision: 'playing_out', history: g0.history,
      events: g0.events ? [...g0.events] : [] });
    v.phase = 'playing';
    return v;
  };
  // a step's src: the crossroads of the animals whose doing it is (the engine's cause_iid), where they stand as it plays; the
  // board brightens their trigger marks (board.js)
  let cur = null;
  const out = [], push = step => { if (!step.src) { const cr = cur && at(cur.cause_iid); if (cr) step.src = [cr]; } out.push({ view: view(), step }); };
  const take = (cr, iid) => { const st = s.board[cr] || [], i = st.findIndex(u => u.iid === iid); if (i < 0) return null;
    const [u] = st.splice(i, 1); if (!st.length) delete s.board[cr]; return u; };
  // food in a row by one player flies together into the den, from the stones or from the animals whose doing it is.
  // `from`: [{ cr, n }], the animals' tiles.
  let food = null;
  const at = iid => { if (iid == null) return null; for (const [cr, st] of Object.entries(s.board)) if (st.some(u => u.iid === iid)) return cr; return null; };
  const flow = (kind, e) => {
    if (!(food && food.kind === kind && food.player === e.player && !!food.income === !!e.income)) {
      flushFood(); food = { kind, player: e.player, n: 0, income: !!e.income, from: [] };
    }
    food.n += e.n;
    const cr = at(e.cause_iid), f = cr && food.from.find(x => x.cr === cr);
    if (f) f.n += e.n; else if (cr) food.from.push({ cr, n: e.n });
  };
  const flushFood = () => { if (food) { push({ ...food, src: food.kind === 'food' ? food.from.map(f => f.cr) : [], dur: foodDur(food.n) }); food = null; } };
  for (let i = 0; i < fresh.length; i++) {
    const e = fresh[i]; cur = e;
    if (e.e !== 'food') flushFood();
    switch (e.e) {
      case 'place': {
        // a card they played is shown large first; units an effect puts down (a Sardine's swarm) are its doing, not plays,
        // unless the engine asks for the card to be shown (`reveal`: Vesper, out of their hand or deck onto your animal)
        if (e.player === them && ((e.from_hand && !e.cause) || e.reveal)) push({ kind: 'reveal', dur: DUR.reveal, card: e.card, cr: e.cr, player: e.player });
        const put = p => { const u = finalUnit(p.iid) || { iid: p.iid, id: p.card, owner: p.player, str: (cards[p.card] || {}).str };
          const st = (s.board[p.cr] = s.board[p.cr] || []);
          if (p.at != null) st.splice(p.at, 0, u); else st.push(u);   // a Cockroach comes back at its old height
          if (p.from_hand) {   // from a hand (an effect putting a unit down from the deck leaves the hand alone)
            s.handCount[p.player] = Math.max(0, s.handCount[p.player] - 1);
            if (p.player === you) s.hand = s.hand.filter(h => h.iid !== p.iid);
          } };
        put(e);
        // what one effect puts down lands together, in one beat: a swarm, not a string of separate plays (Martin, 2026-10-02)
        while (e.cause && fresh[i + 1] && fresh[i + 1].e === 'place' && fresh[i + 1].cause === e.cause && fresh[i + 1].cause_iid === e.cause_iid) put(fresh[++i]);
        push({ kind: 'land', dur: DUR.land, cr: e.cr, card: e.card, player: e.player });
        break;
      }
      case 'leader_power':   // a leader's power used: its card shown, shrinking into its place by the den
        push({ kind: 'leader', dur: DUR.leader, card: e.card, player: e.player });
        break;
      case 'remove':
        if (e.cr) {
          take(e.cr, e.iid);
          // removals by one card that several of its animals did go together, in one beat; one animal's keep a beat each
          const gone = x => x && x.cr && x.e === 'remove';
          let j = i;
          while (gone(e) && e.cause && gone(fresh[j + 1]) && fresh[j + 1].cause === e.cause) j++;
          const many = new Set(fresh.slice(i, j + 1).map(r => r.cause_iid)).size > 1;
          const kind = 'remove';
          if (many) for (; i < j; i++) take(fresh[i + 1].cr, fresh[i + 1].iid);
          push({ kind, dur: DUR[kind], cr: e.cr, card: e.card, owner: e.owner, by: many ? null : culprit(s.board, e.cause, e.cr, e.cause_iid) });
        }
        else if (e.zone === 'hand') {   // discarded from a hand
          s.handCount[e.owner] = Math.max(0, s.handCount[e.owner] - 1);
          if (e.owner === you) s.hand = s.hand.filter(h => h.iid !== e.iid);
          push({ kind: 'discard', dur: DUR.discard, card: e.card, owner: e.owner });
        }
        break;
      case 'food':
        flow('food', e); s.food[e.player] += e.n;
        break;
      case 'raid':   // the food a raid destroys leaves the den in a step of its own (foodfx.js)
        if (e.n) { s.food[e.den] -= e.n; push({ kind: 'raid', dur: DUR.raid, den: e.den, n: e.n, player: e.player }); }
        break;
      case 'draw': {
        const n = e.cards ? e.cards.length : e.n;
        s.handCount[e.player] += n;
        if (e.player === you && e.cards) for (const [iid, card] of e.cards) s.hand.push(finalCard(iid) || { iid, id: card, str: (cards[card] || {}).str });
        push({ kind: 'draw', dur: DUR.draw, player: e.player, n });
        break;
      }
      case 'turn_start':
        s.current = e.player;
        if (e.player === you) push({ kind: 'yourturn', dur: DUR.yourturn });
        break;
      // cover (the land step shows it), turn_end, mulligan (its own screen) need no step of their own
    }
  }
  flushFood();
  out.push({ view: next, step: null });
  return out;
}
