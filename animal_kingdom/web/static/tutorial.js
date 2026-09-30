// The tutorial's coach: one short lesson at a time, each at the moment it matters, in a real game against a gentle
// opponent (web/tutorial.py deals the cards and plays it). The first two turns are forced: a lesson with `only` lets
// just that step be taken (one card, one crossroad, or the deck), so the first four actions build the first food
// region. After that the player plays freely and lessons appear when their situation first comes up: covering, Roar,
// the open den. A lesson shows until its situation passes or the player acts past it, then never again.
//
// Lessons read plain facts of the game view (the player is always seat A here). `c` is:
//   { G, mine, sel, round, placed(id), at(cr), hand(id), acts, places, heldR1 }

const R1 = ['1,1', '1,2', '2,1', '2,2'];   // the +10 region by the player's den the first turns build
const owner = (G, cr) => { const st = G.board[cr]; return st && st.length ? st[st.length - 1].owner : null; };

export const LESSONS = [
  // --- forced: the first two turns ---
  { id: 'lion', when: c => c.mine && c.round === 1 && !c.at('1,2') && c.sel !== 'lion',
    text: 'Win by putting any animal on their den, far right, or by gathering 100 food first. Click the Lion to start.',
    only: { card: 'lion' } },
  { id: 'lion2', when: c => c.mine && c.round === 1 && !c.at('1,2') && c.sel === 'lion',
    text: 'Now click the circled crossroad beside your den.',
    only: { card: 'lion', cr: '1,2' } },
  { id: 'buffalo', when: c => c.mine && c.round === 1 && c.at('1,2') && !c.at('2,2'),
    text: 'You get two actions each turn. Place the Buffalo next to the Lion: every animal must connect back to your den.',
    only: { card: 'cape_buffalo', cr: '2,2' } },
  { id: 'wolf', when: c => c.mine && c.round === 2 && !c.at('1,1'),
    text: 'Hold all four crossroads around a stone and its food is yours every turn. Place the Wolf on the third corner.',
    only: { card: 'dire_wolf', cr: '1,1' }, focus: { region: '1,1' } },
  { id: 'draw', when: c => c.mine && c.round === 2 && c.at('1,1') && c.acts > 0,
    text: 'Out of animals? Your deck draws 2 cards for one action. Click it.',
    only: { deck: true } },

  // --- free play: each the first time it comes up ---
  { id: 'corner', when: c => c.mine && c.round === 3 && !c.heldR1 && !c.at('2,1'),
    text: 'The rest is up to you. Take the last corner to claim the +10.', done: c => c.heldR1 || c.round > 3,
    focus: { region: '1,1' } },
  { id: 'food', when: c => c.heldR1, text: 'It\'s yours: +10 food at the end of each of your turns. The fruit in your den counts it.',
    untilAct: true },
  { id: 'cover', when: c => c.mine && c.places.some(t => t[0] === 'cr' && owner(c.G, t[1]) === 'B'),
    text: 'A stronger animal can go on top of a weaker enemy and take its crossroad. Equal strength isn\'t enough.',
    untilAct: true },
  { id: 'roar', when: c => c.mine && c.G.hand.some(h => c.roar(h.id)),
    text: 'Hover a card to read it. A Roar happens the moment the animal is placed.', untilAct: true },
  { id: 'den', when: c => c.mine && c.places.some(t => t[0] === 'hq'),
    text: 'Their den is open: place any animal on it to win.', focus: { den: 'B' } },
];

// The facts the lessons read, from the view and the client's selection.
export function context(V, sel, cards) {
  const G = V.game, places = Object.values((G.legal && G.legal.place) || {}).flat();   // no legal moves off your turn
  return {
    G, sel, places, round: G.round, acts: G.actionsLeft,
    mine: V.phase === 'playing' && G.current === V.you && G.toAct === V.you && !G.pending,
    at: cr => owner(G, cr) === V.you,
    heldR1: R1.every(cr => owner(G, cr) === V.you),
    roar: id => /(^|\. )Roar:/.test((cards[id] || {}).text || ''),
  };
}

// The lesson to show now, or null. `seen` holds finished lessons; `shown` when each untilAct lesson first showed
// (the count of the player's moves then): it is finished once the player has acted since.
export function current(V, sel, cards, tut) {
  const c = context(V, sel, cards), n = V.game.history.filter(m => m.seat === V.you).length;   // the player's own moves
  for (const L of LESSONS) {
    if (tut.seen.has(L.id)) continue;
    if (L.untilAct && tut.shown[L.id] !== undefined && n > tut.shown[L.id]) { tut.seen.add(L.id); continue; }
    if (L.done && L.done(c)) { tut.seen.add(L.id); continue; }
    if (!L.when(c)) continue;
    if (L.untilAct && tut.shown[L.id] === undefined) tut.shown[L.id] = n;
    return L;
  }
  return null;
}

// Narrow a decision to what the lesson lets happen: only its card and crossroad, only the deck, never End turn.
export function gate(d, only) {
  const places = {};
  if (only.card && d.places[only.card]) places[only.card] = d.places[only.card].filter(t => !only.cr || (t[0] === 'cr' && t[1] === only.cr));
  d.places = places;
  d.noDraw = !only.deck;
  d.noPass = true;
  return d;
}
