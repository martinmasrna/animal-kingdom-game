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

export const DUR = { strength: 0.6, to_hand: 0.5, leave_hand: 0.4, steal: 0.7, discard: 0.5, reveal: 0.95, land: 0.5, remove: 0.85, bounce: 0.85, to_deck: 0.85, draw: 0.5, pay: 0.4, capture: 0.6, yourturn: 1.5 };
// Food in flight: one fruit per food, 0.035 s apart, each flying 0.7 s, then the count settles.
export const foodDur = n => Math.min(2.4, 0.7 + 0.035 * Math.max(0, n - 1) + 0.3);

const clone = x => JSON.parse(JSON.stringify(x));
const lastSeq = v => { const ev = v && v.game && v.game.events; return ev && ev.length ? ev[ev.length - 1].seq : 0; };

// The events in `next` that `prev` hadn't shown, or null when they can't be told apart (another game, a different seat,
// or events from before the oldest one kept): then the new view simply replaces the old.
export function newEvents(prev, next) {
  if (!prev || !next || !prev.game || !next.game || prev.you !== next.you || prev.id !== next.id) return null;
  // A new game in a series starts its own events: nothing of the last one plays. The view that ends a game also adds a
  // result, but its last move still plays in full before the end shows (Martin, 2026-10-02: a food win was announced as
  // the card landed, before its fruit had flown).
  if ((prev.results || []).length !== (next.results || []).length && next.phase === 'playing') return null;
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
  const finalUnit = iid => { for (const st of Object.values(gN.board)) for (const u of st) if (u.iid === iid) return u; return null; };
  const finalCard = iid => gN.hand.find(h => h.iid === iid);
  const view = () => {
    const v = clone(next);
    Object.assign(v.game, { board: clone(s.board), food: { ...s.food }, handCount: { ...s.handCount }, hand: clone(s.hand),
      current: s.current, toAct: null, pending: null, legal: null, result: null, decision: 'playing_out', history: g0.history,
      events: g0.events ? [...g0.events] : [] });
    v.phase = 'playing';
    return v;
  };
  const out = [], push = step => out.push({ view: view(), step });
  const take = (cr, iid) => { const st = s.board[cr] || [], i = st.findIndex(u => u.iid === iid); if (i < 0) return null;
    const [u] = st.splice(i, 1); if (!st.length) delete s.board[cr]; return u; };
  let food = null;   // food gains in a row by one player fly together
  const landed = new Set();   // units put down in these steps: they already show their final strength
  const flushFood = () => { if (food) { push({ kind: 'food', dur: foodDur(food.n), ...food }); food = null; } };
  const toHand = e => { s.handCount[e.player] += 1;
    if (e.player === you) s.hand.push(finalCard(e.iid) || { iid: e.iid, id: e.card, str: (cards[e.card] || {}).str }); };
  for (let i = 0; i < fresh.length; i++) {
    const e = fresh[i];
    if (e.e !== 'food') flushFood();
    switch (e.e) {
      case 'place': {
        // a card they played is shown large first; units an effect puts down (a Lemming's swarm) are its doing, not plays
        if (e.player === them && e.from_hand && !e.cause) push({ kind: 'reveal', dur: DUR.reveal, card: e.card, cr: e.cr, player: e.player });
        const put = p => { const u = finalUnit(p.iid) || { iid: p.iid, id: p.card, owner: p.player, str: (cards[p.card] || {}).str };
          landed.add(p.iid);
          (s.board[p.cr] = s.board[p.cr] || []).push(u);
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
      case 'remove': case 'bounce': case 'to_deck':
        if (e.cr) {
          take(e.cr, e.iid);
          if (e.e === 'bounce' && fresh[i + 1] && fresh[i + 1].e === 'to_hand') toHand(fresh[++i]);   // it flies back into the hand
          push({ kind: e.e, dur: DUR[e.e], cr: e.cr, card: e.card, owner: e.owner, by: culprit(s.board, e.cause, e.cr, e.cause_iid) });
        }
        else if (e.zone === 'hand') {   // discarded from a hand
          s.handCount[e.owner] = Math.max(0, s.handCount[e.owner] - 1);
          if (e.owner === you) s.hand = s.hand.filter(h => h.iid !== e.iid);
          push({ kind: 'discard', dur: DUR.discard, card: e.card, owner: e.owner });
        }
        break;
      case 'food':
        if (food && food.player === e.player && !!food.income === !!e.income) food.n += e.n;
        else { flushFood(); food = { player: e.player, n: e.n, income: !!e.income }; }
        s.food[e.player] += e.n;
        break;
      case 'pay':
        s.food[e.player] -= e.n; push({ kind: 'pay', dur: DUR.pay, player: e.player, n: e.n });
        break;
      case 'draw': {
        const n = e.cards ? e.cards.length : e.n;
        s.handCount[e.player] += n;
        if (e.player === you && e.cards) for (const [iid, card] of e.cards) s.hand.push(finalCard(iid) || { iid, id: card, str: (cards[card] || {}).str });
        push({ kind: 'draw', dur: DUR.draw, player: e.player, n });
        break;
      }
      case 'to_hand':
        toHand(e); push({ kind: 'to_hand', dur: DUR.to_hand, player: e.player });
        break;
      case 'leave_hand':
        s.handCount[e.owner] = Math.max(0, s.handCount[e.owner] - 1);
        if (e.owner === you) s.hand = s.hand.filter(h => h.iid !== e.iid);
        push({ kind: 'leave_hand', dur: DUR.leave_hand, owner: e.owner });
        break;
      case 'steal':
        s.handCount[e.victim] = Math.max(0, s.handCount[e.victim] - 1); s.handCount[e.player] += 1;
        if (e.victim === you) s.hand = s.hand.filter(h => h.iid !== e.iid);
        if (e.player === you) s.hand.push(finalCard(e.new) || { iid: e.new, id: e.card, str: (cards[e.card] || {}).str });
        push({ kind: 'steal', dur: DUR.steal, player: e.player, card: e.card });
        break;
      case 'strength': {   // a stored change (a Roar's grant, Rattlesnake's growth, Viper's poison): auras are not events
        const ch = { iid: e.iid, card: e.card, owner: e.owner, n: e.n }, last = out[out.length - 1];
        // the number changes as it flashes, and stays changed through the steps after (a unit already on the board)
        const hit = u => (e.iid ? u.iid === e.iid : u.id === e.card && u.owner === e.owner) && !landed.has(u.iid);
        for (const st of Object.values(s.board)) for (const u of st) if (hit(u)) u.str += e.n;
        if (last && last.step && last.step.kind === 'strength')   // shown with the change before it: in that step's board too
          for (const st of Object.values(last.view.game.board)) for (const u of st) if (hit(u)) u.str += e.n;
        if (last && last.step && last.step.kind === 'strength') last.step.changes.push(ch);   // several in a row show together
        else push({ kind: 'strength', dur: DUR.strength, changes: [ch] });
        break;
      }
      case 'turn_start':
        s.current = e.player;
        if (e.player === you) push({ kind: 'yourturn', dur: DUR.yourturn });
        break;
      case 'capture':
        s.handCount[e.player] = Math.max(0, s.handCount[e.player] - 1);
        if (e.player === you) s.hand = s.hand.filter(h => h.iid !== e.iid);
        push({ kind: 'capture', dur: DUR.capture, card: e.card, player: e.player, den: e.den });
        break;
      // cover (the land step shows it), turn_end, mulligan (its own screen) need no step of their own
    }
  }
  flushFood();
  out.push({ view: next, step: null });
  return out;
}
