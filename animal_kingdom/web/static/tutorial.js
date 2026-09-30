// The tutorial's coach: one short lesson at a time, each at the moment it matters, in a real game against a gentle
// opponent (web/tutorial.py deals the cards and plays it). Written for a player who has never seen the game or its
// rules (a bright ten-year-old): every thing is named, pointed at, before a lesson uses its name, one idea a line.
//   1. The opening: before any card, the coach names what is on screen, one thing per step, each closed with Next.
//   2. The first two turns are forced: a lesson with `only` lets just that step be taken (one card, one crossroad, or
//      the deck), so the first four moves build the first food region.
//   3. Free play: lessons appear the first time their situation comes up: the moves a turn, the claimed region,
//      covering, Roar, the open den.
// Every line is one of two kinds: it tells (a Next step: nothing else can be clicked until it is read) or it asks for one
// thing (and only that thing, or the obvious next click, is open). A line never informs while leaving the player to
// guess what to do. A lesson shows until Next, its situation passing, or the player acting past it (`untilAct`).
//
// Each lesson stands beside what it talks about: `at` names it (a card in hand, the hand, a crossroad, a region's
// stone, the deck, End turn, a den, a food gem, the opponent's cards, the middle of the board), directly or from
// the moment's facts. It points at what the sentence is about: the card for a card's power; for a choice of places, it
// stands beside the whole group of rings (`rings`), which pulse, since one notch can't point at several.

// Lessons read plain facts of the game view (the player is always seat A here). `c` is:
//   { G, mine, theirs, choosing, sel, round, at(cr), units, hand(id), acts, places, rightmost(id), roar(id),
//     home (the first food region's corners), homeHeld, homeOpen (its corners a placement can take now) }

const owner = (G, cr) => { const st = G.board[cr]; return st && st.length ? st[st.length - 1].owner : null; };
// The first food region is one of the two +10 regions by the player's den, whichever the first animals started (the
// lower on a tie); its corners are 'c,r' for c in 1-2 and r in its two rows.
const HOME = [['1,1', '2,1', '1,2', '2,2'], ['1,2', '2,2', '1,3', '2,3']];
const opening = c => c.mine && c.round === 1 && c.units === 0;   // the first turn, before the first animal is placed
const talk = { next: true, only: {} };
// A card's power is explained with the card shown large, as if hovered (`read`), its text beside the coach's line; the move
// that uses it is a separate, short step, so the large card never covers the circles.
const explain = (id, card, when, text) => ({ id, when, ...talk, read: card, at: { read: card }, text });   // an opening step: read, then Next; nothing else can be clicked meanwhile

// Lines both lessons share: a Roar asking for a target, and the safety net for a hand with nothing to place.
const TARGET = { id: 'target', when: c => c.choosing, untilAct: true, at: { prompt: true },
    text: 'This Roar needs a target. Click one of the circled crossroads, or click Skip.' };
const EMPTY = { id: 'empty', again: true, when: c => c.mine && c.round >= 3 && !c.offered.length,   // nothing to place: never a silent turn
  at: c => c.canDraw ? { deck: true } : { endturn: true },
  text: c => c.canDraw ? 'Nothing you can place right now. Click your deck to draw 2 new ones.' : 'Nothing to do this turn. Click End turn.' };

export const LESSONS = [
  // --- the opening: what is on screen ---
  { id: 'welcome', when: opening, ...talk, at: { middle: true },
    text: 'Welcome to the savanna! You lead the blue animals. Your opponent leads the red ones.' },
  { id: 'yourden', when: opening, ...talk, at: { den: 'A' },
    text: 'This rock is your den, your home. Your animals start next to it.' },
  { id: 'theirden', when: opening, ...talk, at: { den: 'B' },
    text: 'This is your opponent\'s den. Put any of your animals on it and you win!' },
  { id: 'foodcount', when: opening, ...talk, at: { gem: 'A' },
    text: 'The second way to win is food. This counts your food: gather 100 and you win.' },
  { id: 'oppfood', when: opening, ...talk, at: { gem: 'B' },
    text: 'And this counts your opponent\'s food. Don\'t let it reach 100 first!' },
  { id: 'cards', when: opening, ...talk, at: { hand: true },
    text: 'These are your animal cards. The number on a card is the animal\'s strength.' },

  // --- forced: the first two turns ---
  { id: 'lion', when: c => opening(c) && c.sel !== 'lion',
    text: 'Let\'s place your first animal. Click the Lion.',
    only: { card: 'lion' }, at: { card: 'lion' } },
  { id: 'lion2', when: c => opening(c) && c.sel === 'lion',
    text: 'Animals stand on crossroads, the sandy circles. Your first animal goes next to your den: click one of the circled crossroads.',
    only: { card: 'lion' }, at: { rings: true } },
  { id: 'buffalo', when: c => c.mine && c.round === 1 && c.units === 1,
    text: 'Now the Buffalo. Animals can only stand next to your den or next to your other animals. Click one of the circles.',
    only: c => ({ card: 'cape_buffalo', picked: true, crs: c.empty('cape_buffalo') }), at: { rings: true } },
  { id: 'watch', when: c => c.theirs && c.round === 1, at: { oppcards: true },
    text: 'Now it\'s your opponent\'s turn. Watch where the red animals go.' },
  { id: 'patch', when: c => c.mine && c.round === 2 && c.hand('dire_wolf'), ...talk, at: c => ({ stone: c.home[0] }),
    text: 'This is a region. Put animals on all four crossroads around it, and you get 10 food every turn.' },
  { id: 'wolf', when: c => c.mine && c.round === 2 && c.hand('dire_wolf'),
    text: 'Place the Wolf on one of the circles around the +10 region.',
    only: c => ({ card: 'dire_wolf', picked: true, crs: c.homeOpen.length ? c.homeOpen : undefined }),
    at: { rings: true } },
  { id: 'draw', when: c => c.mine && c.round === 2 && !c.hand('dire_wolf') && c.acts > 0,
    text: 'You\'re out of cards! Click your deck to draw 2 new ones.',
    only: { deck: true }, at: { deck: true } },

  // --- free play: each the first time it comes up ---
  { id: 'actions', when: c => c.mine && c.round === 3, ...talk, at: { endturn: true },
    text: 'Each turn you get two moves: place an animal or draw cards. The dots show how many moves are left.' },
  // the first patch is finished by hand, any card, only its last corner (shown only when a card can reach it: never a dead end)
  { id: 'corner', when: c => c.mine && c.round >= 3 && !c.homeHeld && c.homeOpen.length > 0,
    only: c => ({ crs: c.homeOpen }), at: c => ({ cr: c.homeOpen[0] }),
    text: 'Finish the region! Place an animal on the last crossroad around the +10.' },
  { id: 'food', when: c => c.homeHeld, ...talk, at: c => ({ stone: c.home[0] }),
    text: 'The +10 region is yours! You get 10 food at the end of every turn. Watch the fruit fill your den.' },
  // covering, by hand: the second move of turn 3, onto the Pup the opponent always leaves beside the patch
  { id: 'cover', when: c => c.mine && c.round >= 3 && c.homeHeld && c.coverable.length > 0, done: c => c.covered,
    only: c => ({ card: c.coverWith, picked: true, crs: c.coverable }), at: c => ({ cr: c.coverable[0] }),
    text: 'A stronger animal can stand on top of a weaker enemy and take its crossroad. 7 beats 1, but 7 can\'t beat 7. Cover the circled animal!' },
  // Roar, by hand: the Lynx (turn 4), whose Roar always works beside the Lion
  explain('roarinfo', 'lynx', c => c.mine && c.hand('lynx') && c.empty('lynx').length > 0,
    'The Lynx has a Roar: a power that happens the moment you place it. Its Roar draws a card if you have another Cat, like your Lion.'),
  { id: 'roar', when: c => c.mine && c.hand('lynx') && c.empty('lynx').length > 0, done: c => c.roared,
    only: c => ({ card: 'lynx', picked: true, crs: c.empty('lynx') }), at: { rings: true },
    text: 'Place the Lynx on a circle.' },
  { id: 'roared', when: c => c.roared, ...talk, at: { hand: true },
    text: 'Your Lynx roared and drew you a card! Point at any card to read what it does.' },
  { id: 'free', when: c => c.mine && (c.roared || c.round >= 6), ...talk, at: { middle: true },
    text: 'Now make your way to your opponent\'s den. Each move, the circles show how to get closer.' },
  TARGET,
  // lesson 1 ends on the den win it teaches: after the Roar every move is forced toward the den, then onto it
  { id: 'den', when: c => c.mine && c.places.some(t => t[0] === 'hq'), only: { hq: true }, at: { den: 'B' },
    text: 'Your opponent\'s den is open! Pick any animal and put it on the den to win.' },
  { id: 'march', again: true, when: c => c.mine && (c.roared || c.round >= 6) && c.forward.length > 0,
    only: c => ({ crs: c.forward }), at: { rings: true },
    text: 'Head for your opponent\'s den! Pick an animal, then click one of the circles.' },
  EMPTY,
];

// Lesson 2: the deeper mechanics, won on food (the opponent walls its den with 7s). Scripted like lesson 1: every move is
// a step in a fixed order on fixed crossroads (connection was taught in lesson 1; here the fixed board is what makes the
// Eagle's ambush and the Black Mamba's rescue always possible). Only the Eagle, teaching Flight, rings every empty crossroad.
// Then each move is guided to the best spots for finishing a region, until 100 food.
const one = (card, cr) => ({ card, picked: true, crs: [cr] });
export const LESSONS_2 = [
  { id: 'intro2', when: c => c.mine && c.round === 1 && c.units === 0, ...talk, at: { middle: true },
    text: 'Lesson 2! Many animals have special powers. Let\'s meet some of them.' },
  { id: 'lion', when: c => c.mine && c.hand('lion') && !c.placed('lion'), only: one('lion', '1,2'), at: { rings: true },
    text: 'Place your Lion on the circle.' },
  explain('glow', 'lynx', c => c.mine && c.ready('lynx'),
    'See the Lynx glowing? A glowing card\'s Roar will work right now: it draws a card if you have another Cat, and your Lion is one.'),
  { id: 'lynx', when: c => c.mine && c.hand('lynx'), only: one('lynx', '2,2'), at: { rings: true },
    text: 'Place the Lynx on the circle.' },
  { id: 'wall', when: c => c.theirs && c.round === 1, at: { den: 'B' },
    text: 'Your opponent is building a wall of strong animals in front of its den.' },
  explain('eagleinfo', 'eagle', c => c.mine && c.hand('eagle') && !c.placed('eagle'),
    'Your Lynx drew an Eagle. The Eagle has Flight: it can land on any empty crossroad, even far from your animals.'),
  { id: 'eagle', when: c => c.mine && c.hand('eagle') && !c.placed('eagle'),
    only: c => ({ card: 'eagle', picked: true, crs: c.empty('eagle').filter(cr => !['2,1', '3,1', '3,2'].includes(cr)) }), at: { rings: true },
    text: 'Place the Eagle on any circle.' },
  { id: 'buffalo2', when: c => c.mine && c.round === 2 && c.placed('eagle') && c.hand('cape_buffalo'), only: one('cape_buffalo', '2,1'), at: { rings: true },
    text: 'Now place the Buffalo on the circle.' },
  { id: 'draw2', when: c => c.mine && c.round >= 3 && !c.hand('squirrel') && !c.placed('squirrel'), only: { deck: true }, at: { deck: true },
    text: 'Your hand is empty. Click your deck to draw 2 cards.' },
  explain('squirrelinfo', 'squirrel', c => c.mine && c.hand('squirrel') && !c.placed('squirrel'), 'The Squirrel\'s Roar gives you 10 food.'),
  { id: 'squirrel', when: c => c.mine && c.hand('squirrel') && !c.placed('squirrel'), only: one('squirrel', '3,2'), at: { rings: true },
    text: 'Place the Squirrel on the circle.' },
  { id: 'foodroar', when: c => c.placed('squirrel'), ...talk, at: { gem: 'A' },
    text: 'Your food went up by 10! Roars like this are another way to gather food, besides regions.' },
  { id: 'covered', when: c => c.squirrelCovered, ...talk, at: c => ({ cr: c.squirrelAt }),
    text: 'Your opponent has an Eagle too! It flew over and covered your Squirrel. Your Squirrel isn\'t gone. It waits underneath.' },
  explain('mambainfo', 'black_mamba', c => c.mine && c.squirrelCovered && c.hand('black_mamba') && c.nextToFlier.length > 0,
    'The Black Mamba\'s Roar removes an enemy next to it with strength 5 or less, like that Eagle.'),
  { id: 'mamba', when: c => c.mine && c.squirrelCovered && c.hand('black_mamba') && c.nextToFlier.length > 0,
    only: c => ({ card: 'black_mamba', picked: true, crs: c.nextToFlier }), at: { rings: true },
    text: 'Place the Black Mamba on the circle, next to the Eagle.' },
  TARGET,
  { id: 'uncovered', when: c => c.squirrelBack, ...talk, at: c => ({ cr: c.squirrelAt }),
    text: 'The Eagle is gone, and your Squirrel is back on top! When the top animal leaves, the one below comes back.' },
  { id: 'goal2', when: c => c.mine && c.wall, ...talk, at: { den: 'B' },
    text: 'Your opponent\'s den is guarded by three 7s, and a 7 can\'t beat a 7. So this time, you\'ll win by gathering 100 food.' },
  { id: 'draw3', when: c => c.mine && c.placed('black_mamba') && !c.hand('tiger') && !c.placed('tiger') && c.canDraw, only: { deck: true }, at: { deck: true },
    text: 'Click your deck to draw 2 more cards.' },
  explain('apexinfo', 'tiger', c => c.mine && c.hand('tiger') && c.prey.length > 0,
    'The Tiger is an Apex Predator: it must land on top of an animal, and it eats it. An eaten animal is gone for good.'),
  { id: 'apex', when: c => c.mine && c.hand('tiger') && c.prey.length > 0,
    only: c => ({ card: 'tiger', picked: true, crs: c.prey }), at: { rings: true },
    text: 'Place the Tiger on a circled animal to eat it.' },
  { id: 'free2', when: c => c.mine && (c.placed('tiger') || c.round >= 8), ...talk, at: { middle: true },
    text: 'Now gather 100 food. Each move, the circles show the best spots for finishing a region.' },
  { id: 'feed', again: true, when: c => c.mine && (c.placed('tiger') || c.round >= 8) && c.feed.length > 0,
    only: c => ({ crs: c.feed }), at: { rings: true },
    text: 'Pick an animal, then click one of the circles.' },
  EMPTY,
];
// Lesson 2 holds each teaching card back until its own step: it can't be placed before its line explains it.
const HOLD = ['lynx', 'squirrel', 'black_mamba', 'eagle', 'tiger'];
export const lessonOf = V => V.seats.B.bot === 'tutorial2' ? 2 : 1;
// The cards not to offer now: in lesson 2, a teaching card never yet placed, unless its step is the one showing.
export function held(V, L) {
  if (lessonOf(V) !== 2) return [];
  const placed = id => V.game.history.some(m => m.seat === V.you && m.kind === 'place' && m.card === id);
  return HOLD.filter(id => !placed(id) && !(L && L.only && L.only.card === id) && !(id === 'tiger' && V.game.round >= 8));
}
const ADJ = cr => { const [x, y] = cr.split(',').map(Number); return [[x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]].filter(([a, b]) => a >= 1 && a <= 5 && b >= 1 && b <= 3).map(([a, b]) => `${a},${b}`); };

// The facts the lessons read, from the view and the client's selection.
export function context(V, sel, cards) {
  const G = V.game, places = Object.values((G.legal && G.legal.place) || {}).flat();   // no legal moves off your turn
  const c = {
    G, sel, places, round: G.round, acts: G.actionsLeft,
    mine: V.phase === 'playing' && G.current === V.you && G.toAct === V.you && !G.pending,
    theirs: V.phase === 'playing' && G.current !== V.you,
    choosing: V.phase === 'playing' && G.toAct === V.you && !!G.pending && G.pending.kind !== 'mulligan',
    at: cr => owner(G, cr) === V.you,
    canDraw: !!(G.legal && G.legal.draw),
    // enemy crossroads a card can cover now; whether you have covered, and whether the Lynx has roared
    coverable: [...new Set(places.filter(t => t[0] === 'cr' && owner(G, t[1]) && owner(G, t[1]) !== V.you).map(t => t[1]))],
    coverWith: (Object.entries((G.legal && G.legal.place) || {}).find(([, ts]) => ts.some(t => t[0] === 'cr' && owner(G, t[1]) && owner(G, t[1]) !== V.you)) || [])[0],   // a card that can cover now
    covered: G.history.some(m => m.seat === V.you && m.fx.some(f => f.k === 'cover')),
    roared: G.history.some(m => m.seat === V.you && m.kind === 'place' && m.card === 'lynx'),
    units: Object.keys(G.board).filter(cr => owner(G, cr) === V.you).length,
    hand: id => G.hand.some(h => h.id === id),
    // the empty crossroads a card can go to now (placing onto your own animal is legal, but only noise while learning)
    empty: id => ((G.legal && G.legal.place && G.legal.place[id]) || []).filter(t => t[0] === 'cr' && !owner(G, t[1])).map(t => t[1]),
    // the rightmost of them (the coach stands beside it, clear of the others)
    rightmost: id => c.empty(id).sort((a, b) => b[0] - a[0])[0],
    roar: id => /(^|\. )Roar:/.test((cards[id] || {}).text || ''),
    ready: id => G.hand.some(h => h.id === id && h.ready),   // the card glows: its Roar's condition holds now
    placed: id => G.history.some(m => m.seat === V.you && m.kind === 'place' && m.card === id),
  };
  // the moves the tutorial offers: never onto your own animal, never a teaching card before its step (lesson 2)
  const hold = V.seats && V.seats.B && V.seats.B.bot === 'tutorial2' ? HOLD.filter(id => !c.placed(id)) : [];
  c.offered = Object.entries((G.legal && G.legal.place) || {}).filter(([id]) => !hold.includes(id)).flatMap(([, ts]) => ts)
    .filter(t => !(t[0] === 'cr' && owner(G, t[1]) === V.you));
  // the crossroads that get closest to the opponent's den (the furthest column a move can reach; covering a weak enemy counts)
  const crs = c.offered.filter(t => t[0] === 'cr').map(t => t[1]), far = Math.max(0, ...crs.map(cr => +cr[0]));
  c.forward = [...new Set(crs.filter(cr => +cr[0] === far))];
  // lesson 2's stack: the Squirrel under the opponent's Eagle, then back on top once the Eagle is removed
  const under = Object.entries(G.board).find(([, st]) => st.length > 1 && st[st.length - 1].owner !== V.you && st.slice(0, -1).some(u => u.owner === V.you && u.id === 'squirrel'));
  const top = Object.entries(G.board).find(([, st]) => st.length && st[st.length - 1].owner === V.you && st[st.length - 1].id === 'squirrel');
  const wasCovered = G.history.some(m => m.seat !== V.you && m.fx.some(f => f.k === 'cover' && f.card === 'squirrel'));
  Object.assign(c, { squirrelCovered: !!under, squirrelBack: !under && wasCovered && !!top, squirrelAt: (under || top || [])[0] });
  c.nextToFlier = under ? c.empty('black_mamba').filter(cr => ADJ(under[0]).includes(cr)) : [];
  c.wall = ['5,1', '5,2', '5,3'].every(cr => owner(G, cr) && owner(G, cr) !== V.you);   // lesson 2's wall before the den
  // the best spots for food: the open corners of the region, not yet yours and free of enemies, where you hold the most
  const regions = [1, 2, 3, 4].flatMap(x => [1, 2].map(y => [`${x},${y}`, `${x + 1},${y}`, `${x},${y + 1}`, `${x + 1},${y + 1}`]));
  const open = new Set(crs.filter(cr => !owner(G, cr)));
  const cand = regions.filter(r => !r.every(cr => owner(G, cr) === V.you) && !r.some(cr => owner(G, cr) && owner(G, cr) !== V.you) && r.some(cr => open.has(cr)))
    .map(r => [r.filter(cr => owner(G, cr) === V.you).length, r]).sort((a, b) => b[0] - a[0]);
  c.feed = cand.length ? cand.filter(([n]) => n === cand[0][0]).flatMap(([, r]) => r.filter(cr => open.has(cr))).filter((x, i, a) => a.indexOf(x) === i) : [...open];
  // the enemies the Tiger may land on and eat
  c.prey = ((G.legal && G.legal.place && G.legal.place.tiger) || []).filter(t => t[0] === 'cr' && owner(G, t[1]) && owner(G, t[1]) !== V.you).map(t => t[1]);
  const mineAt = cr => owner(G, cr) === V.you, count = h => h.filter(mineAt).length;
  const home = count(HOME[1]) > count(HOME[0]) ? HOME[1] : HOME[0];
  const legal = new Set(Object.values((G.legal && G.legal.place) || {}).flat().filter(t => t[0] === 'cr').map(t => t[1]));
  return Object.assign(c, { home, homeHeld: HOME.some(h => h.every(mineAt)), homeOpen: home.filter(cr => !mineAt(cr) && legal.has(cr)) });
}

// The lesson to show now, or null. `seen` holds finished lessons; `shown` when each untilAct lesson first showed
// (the count of the player's moves then): it is finished once the player has acted since.
export function current(V, sel, cards, tut) {
  const c = context(V, sel, cards), n = V.game.history.filter(m => m.seat === V.you).length;   // the player's own moves
  for (const L of lessonOf(V) === 2 ? LESSONS_2 : LESSONS) {
    const now = f => typeof f === 'function' ? f(c) : f;   // a lesson's target, gate and words can depend on the moment
    if (L.again) { if (L.when(c)) return { ...L, at: now(L.at), text: now(L.text), only: now(L.only) }; continue; }   // a safety net: shown whenever it applies, never used up
    if (tut.seen.has(L.id)) continue;
    if (L.untilAct && tut.shown[L.id] !== undefined && n > tut.shown[L.id]) { tut.seen.add(L.id); continue; }
    if (L.done && L.done(c)) { tut.seen.add(L.id); continue; }
    if (!L.when(c)) continue;
    if (L.untilAct && tut.shown[L.id] === undefined) tut.shown[L.id] = n;
    return { ...L, at: now(L.at), only: now(L.only) };
  }
  return null;
}

// Narrow a decision to what the lesson lets happen: only its card and crossroads, only the deck, never End turn. A
// `picked` card is already chosen, so its rings show as the lesson speaks (only the first card is picked by hand).
export function gate(d, only) {
  const places = {};
  const fits = t => only.hq ? t[0] === 'hq' : !only.crs || (t[0] === 'cr' && only.crs.includes(t[1]));
  for (const [id, ts] of Object.entries(d.places)) if (only.card ? id === only.card : only.crs || only.hq) {   // its card, or any card to its crossroads
    const ok = ts.filter(fits); if (ok.length) places[id] = ok; }
  d.places = places;
  d.noDraw = !only.deck;
  d.noPass = true;
  return d;
}
