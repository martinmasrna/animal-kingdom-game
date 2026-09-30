// The tutorial's coach: one short lesson at a time, each at the moment it matters, in a real game against a gentle
// opponent (web/tutorial.py deals the cards and plays it). Written for a player who has never seen the game or its
// rules (a bright ten-year-old): every thing is named, pointed at, before a lesson uses its name, one idea a line.
//   1. The opening: before any card, the coach names what is on screen, one thing per step, each closed with Next.
//   2. The first two turns are forced: a lesson with `only` lets just that step be taken (one card, one crossroad, or
//      the deck), so the first four moves build the first food region.
//   3. Free play: lessons appear the first time their situation comes up: the moves a turn, the claimed region,
//      covering, Roar, the open den.
// A lesson shows until its situation passes, the player acts past it (`untilAct`) or clicks Next, then never again.
//
// Each lesson stands beside what it talks about: `at` names it (a card in hand, the hand, a crossroad, a region's
// stone, the deck, End turn, a den, your food gem, the opponent's cards, the middle of the board), directly or from
// the moment's facts (beside the rightmost of a picked card's rings).

// Lessons read plain facts of the game view (the player is always seat A here). `c` is:
//   { G, mine, theirs, choosing, sel, round, at(cr), units, hand(id), acts, places, rightmost(id), roar(id),
//     home (the first food region's corners), homeHeld, homeOpen (its corners a placement can take now) }

const owner = (G, cr) => { const st = G.board[cr]; return st && st.length ? st[st.length - 1].owner : null; };
// The first food region is one of the two +10 regions by the player's den, whichever the first animals started (the
// lower on a tie); its corners are 'c,r' for c in 1-2 and r in its two rows.
const HOME = [['1,1', '2,1', '1,2', '2,2'], ['1,2', '2,2', '1,3', '2,3']];
const opening = c => c.mine && c.round === 1 && c.units === 0;   // the first turn, before the first animal is placed
const talk = { next: true, only: {} };   // an opening step: read, then Next; nothing else can be clicked meanwhile

export const LESSONS = [
  // --- the opening: what is on screen ---
  { id: 'welcome', when: opening, ...talk, at: { middle: true },
    text: 'Welcome to the savanna! You lead the blue animals. Your opponent leads the red ones.' },
  { id: 'yourden', when: opening, ...talk, at: { den: 'A' },
    text: 'This rock is your den, your home. Your animals start next to it.' },
  { id: 'theirden', when: opening, ...talk, at: { den: 'B' },
    text: 'This is your opponent\'s den. Put any of your animals on it and you win!' },
  { id: 'foodcount', when: opening, ...talk, at: { gem: 'A' },
    text: 'This counts your food. Gather 100 food and you win too.' },
  { id: 'cards', when: opening, ...talk, at: { hand: true },
    text: 'These are your animal cards. The number on a card is the animal\'s strength.' },

  // --- forced: the first two turns ---
  { id: 'lion', when: c => opening(c) && c.sel !== 'lion',
    text: 'Let\'s place your first animal. Click the Lion.',
    only: { card: 'lion' }, at: { card: 'lion' } },
  { id: 'lion2', when: c => opening(c) && c.sel === 'lion',
    text: 'Animals stand on crossroads, the sandy circles. Your first animal goes next to your den: click one of the circled crossroads.',
    only: { card: 'lion' }, at: { cr: '1,2' } },
  { id: 'buffalo', when: c => c.mine && c.round === 1 && c.units === 1,
    text: 'Now the Buffalo. Animals can only stand next to your den or next to your other animals. Click one of the circles.',
    only: c => ({ card: 'cape_buffalo', picked: true, crs: c.empty('cape_buffalo') }), at: c => ({ cr: c.rightmost('cape_buffalo') }) },
  { id: 'watch', when: c => c.theirs && c.round === 1, at: { oppcards: true },
    text: 'Now it\'s your opponent\'s turn. Watch where the red animals go.' },
  { id: 'wolf', when: c => c.mine && c.round === 2 && c.hand('dire_wolf'),
    text: 'A stone with a number gives food. Stand on all four crossroads around it and you get that food every turn. Place the Wolf on a circled crossroad around the +10 stone.',
    only: c => ({ card: 'dire_wolf', picked: true, crs: c.homeOpen.length ? c.homeOpen : undefined }),
    at: c => ({ cr: c.homeOpen.length ? c.homeOpen.slice().sort((a, b) => b[0] - a[0])[0] : c.rightmost('dire_wolf') }) },
  { id: 'draw', when: c => c.mine && c.round === 2 && !c.hand('dire_wolf') && c.acts > 0,
    text: 'You\'re out of cards! Click your deck to draw 2 new ones.',
    only: { deck: true }, at: { deck: true } },

  // --- free play: each the first time it comes up ---
  { id: 'actions', when: c => c.mine && c.round === 3, untilAct: true, at: { endturn: true },
    text: 'Each turn you get two moves: place an animal or draw cards. The dots show how many moves are left.' },
  { id: 'corner', when: c => c.mine && c.round === 3 && !c.homeHeld && c.homeOpen.length > 0, done: c => c.homeHeld || c.round > 3,
    at: c => ({ cr: c.homeOpen[0] }), text: 'Now you choose! Place an animal on the last crossroad around the +10 stone.' },
  { id: 'food', when: c => c.homeHeld, untilAct: true, at: c => ({ stone: c.home[0] }),
    text: 'The +10 stone is yours! You get 10 food at the end of every turn. Watch the fruit fill your den.' },
  { id: 'cover', when: c => c.mine && c.places.some(t => t[0] === 'cr' && owner(c.G, t[1]) === 'B'), untilAct: true,
    at: c => ({ cr: c.places.find(t => t[0] === 'cr' && owner(c.G, t[1]) === 'B')[1] }),
    text: 'A stronger animal can stand on top of a weaker enemy and take its crossroad. 7 beats 1, but 7 can\'t beat 7.' },
  { id: 'roar', when: c => c.mine && c.G.hand.some(h => c.roar(h.id)), untilAct: true,
    at: c => ({ card: c.G.hand.find(h => c.roar(h.id)).id }),
    text: 'Some animals have a special power. Point at a card to read it. A Roar happens as soon as you place the animal.' },
  { id: 'target', when: c => c.choosing, untilAct: true, at: { prompt: true },
    text: 'This Roar needs a target. Click one of the circled crossroads, or click Skip.' },
  { id: 'den', when: c => c.mine && c.places.some(t => t[0] === 'hq'), at: { den: 'B' },
    text: 'Your opponent\'s den is open! Put any animal on it to win.' },
];

// The facts the lessons read, from the view and the client's selection.
export function context(V, sel, cards) {
  const G = V.game, places = Object.values((G.legal && G.legal.place) || {}).flat();   // no legal moves off your turn
  const c = {
    G, sel, places, round: G.round, acts: G.actionsLeft,
    mine: V.phase === 'playing' && G.current === V.you && G.toAct === V.you && !G.pending,
    theirs: V.phase === 'playing' && G.current !== V.you,
    choosing: V.phase === 'playing' && G.toAct === V.you && !!G.pending && G.pending.kind !== 'mulligan',
    at: cr => owner(G, cr) === V.you,
    units: Object.keys(G.board).filter(cr => owner(G, cr) === V.you).length,
    hand: id => G.hand.some(h => h.id === id),
    // the rightmost crossroad a card can go to now (the coach stands beside it, clear of the others)
    // the empty crossroads a card can go to now (placing onto your own animal is legal, but only noise while learning)
    empty: id => ((G.legal && G.legal.place && G.legal.place[id]) || []).filter(t => t[0] === 'cr' && !owner(G, t[1])).map(t => t[1]),
    // the rightmost of them (the coach stands beside it, clear of the others)
    rightmost: id => c.empty(id).sort((a, b) => b[0] - a[0])[0],
    roar: id => /(^|\. )Roar:/.test((cards[id] || {}).text || ''),
  };
  const mineAt = cr => owner(G, cr) === V.you, count = h => h.filter(mineAt).length;
  const home = count(HOME[1]) > count(HOME[0]) ? HOME[1] : HOME[0];
  const legal = new Set(Object.values((G.legal && G.legal.place) || {}).flat().filter(t => t[0] === 'cr').map(t => t[1]));
  return Object.assign(c, { home, homeHeld: HOME.some(h => h.every(mineAt)), homeOpen: home.filter(cr => !mineAt(cr) && legal.has(cr)) });
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
    const now = f => typeof f === 'function' ? f(c) : f;   // a lesson's target and gate can depend on the moment
    return { ...L, at: now(L.at), only: now(L.only) };
  }
  return null;
}

// Narrow a decision to what the lesson lets happen: only its card and crossroads, only the deck, never End turn. A
// `picked` card is already chosen, so its rings show as the lesson speaks (only the first card is picked by hand).
export function gate(d, only) {
  const places = {};
  if (only.card && d.places[only.card]) places[only.card] = d.places[only.card].filter(t => !only.crs || (t[0] === 'cr' && only.crs.includes(t[1])));
  d.places = places;
  d.noDraw = !only.deck;
  d.noPass = true;
  return d;
}
