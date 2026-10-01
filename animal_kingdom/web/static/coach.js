// The tutorial on the game screen (the lessons themselves are tutorial.js, plain data): whether a match is a lesson, the
// lesson for this moment, how it narrows what may be done, the hand's hints, the fruit it holds back until Next, the coach
// piece it draws, and a lesson's end. The game screen calls these at named points and knows nothing else about lessons
// (Martin, 2026-10-01: the tutorial kept separate from ordinary games). bindCoach hands over what it reads from the screen.
import { crossroadAt, denMouthAt, gemAt, STAGE, VIEW } from './board.js';
import { current, gate, held, lessonOf } from './tutorial.js';

let C;   // { V(), ui, CARDS(), send, drawGame, tapWords, PL, store, startTutorial, firstMatch }
export function bindCoach(ctx) { C = ctx; }

// A lesson is a match against the tutorial's bot.
export const isLesson = V => !!(V && V.seats && V.seats.B && /^tutorial/.test(V.seats.B.bot || ''));
export { lessonOf };

// Its lessons seen, per match (a new tutorial starts them over).
function tutState() { const V = C.V(), ui = C.ui; if (!ui.tut || ui.tut.id !== V.id) ui.tut = { id: V.id, seen: new Set(), shown: {} }; return ui.tut; }

// The lesson for this moment: only once the steps have played (the coach speaks on a settled view).
export function lessonNow() {
  const V = C.V();
  return isLesson(V) && V.phase === 'playing' && !C.ui.step ? current(V, C.ui.sel, C.CARDS(), tutState()) : null;
}

// What a lesson lets be done. A choice: only the target it teaches. A move: a forced step only its card and places; teaching
// cards wait for their step; placing onto your own animal is legal but never taught, so not offered (unless the lesson
// rings it: the Mamba's rescue).
export function narrowChoice(d) {
  if (d.lesson && d.lesson.only && d.lesson.only.crs) d.crChoice = Object.fromEntries(Object.entries(d.crChoice).filter(([cr]) => d.lesson.only.crs.includes(cr)));
}
export function narrowPlaces(d) {
  const V = C.V();
  if (d.lesson && d.lesson.only) gate(d, d.lesson.only);
  if (!isLesson(V)) return;
  d.places = Object.fromEntries(Object.entries(d.places).filter(([id]) => !held(V, d.lesson).includes(id))
    .map(([id, ts]) => [id, ts.filter(t => !(t[0] === 'cr' && (V.game.board[t[1]] || []).slice(-1).some(u => u.owner === V.you)) || (d.lesson && d.lesson.only && (d.lesson.only.crs || []).includes(t[1])))]).filter(([, ts]) => ts.length));
}

// The hand while a lesson runs: a step naming a card lights only its leftmost copy (two lit copies leave "click the
// Buffalo" ambiguous); the card it asks for hints; while the coach talks the cards stay lit; the card it explains shows large.
export function handLights(d, hand) {
  const L = d.lesson, one = L && L.only && L.only.card ? hand.find(x => x.id === L.only.card) : null;
  return { one, hint: can => !!(can && L && L.only && !C.ui.sel), talking: !!(L && L.next), shown: id => !!(L && L.read === id && !C.ui.step) };
}

// The "region is yours" line: the fruit waits for its Next. The board keeps the food it had, and the animation that would
// have played is kept for the Next click (drawCoach) to play. Returns the animation and game to draw.
export function holdFood(d, A, g) {
  const ui = C.ui;
  if (!(d.lesson && d.lesson.holdFood)) return [A, g];
  if (A && A.food && A.food.A !== g.food.A) ui.heldFood = A;
  if (ui.heldFood) { g = { ...g, food: { ...g.food, A: ui.heldFood.food.A } }; A = A && { ...A, food: { ...A.food, A: ui.heldFood.food.A } }; }
  return [A, g];
}

// The region a lesson shows (its crossroads and stone glow), with the coach.
export const shownRegion = d => d.lesson && d.lesson.at && d.lesson.at.region && !C.ui.step ? d.lesson.at.region : null;

// A lesson's end: lesson 1 leads on to lesson 2, lesson 2 to a real match; a loss offers the same lesson again.
export function lessonEnd(ov, { res, how, won }) {
  const V = C.V(), lesson = lessonOf(V);
  if (won) C.store(lesson === 1 ? 'ak:lesson' : 'ak:learned', '1');
  const next = !won ? '' : lesson === 1 ? '<div class="next">One more lesson to go.</div>' : '<div class="next">You\'re ready! Now play a real match with the Cats deck.</div>';
  const go = !won ? `<a class="slab" href="#/">Menu</a><button class="play" id="again">Try again</button>`   // no See the board in a lesson
    : lesson === 1 ? `<button class="play" id="nextlesson">Next lesson</button>` : `<button class="play" id="firstmatch">Play a match</button>`;
  ov.innerHTML = `<div class="endbox"><div class="res ${res[0]}">${res[1]}</div><div class="how">${how}.</div>${next}<div class="btns">${go}</div></div>`;
  if (!won) document.getElementById('again').onclick = () => C.startTutorial(lesson);
  if (won && lesson === 1) document.getElementById('nextlesson').onclick = () => C.startTutorial(2);
  if (won && lesson === 2) document.getElementById('firstmatch').onclick = C.firstMatch;
}

// The tutorial's Next also answers Enter and Space.
addEventListener('keydown', e => {
  const next = document.getElementById('coachnext');
  if (next && (e.key === 'Enter' || e.key === ' ') && document.activeElement.tagName !== 'TEXTAREA') { e.preventDefault(); next.click(); }
});

// The tutorial's coach: a granite piece standing beside what the lesson talks about, its notch pointing at it: above a
// card in the hand, the deck or End turn, beside a crossroad (on the side with more room), a region's stone or a den.
let COACH_W = 300;   // 400 upright (game.css .port .coach)
// While a line waits for Next, the tutorial's opponent waits too: its moves would run over the line (told to the server once per change).
let botHeld = false;
const holdBot = on => {
  if (!on && (C.ui.animUntil || 0) > Date.now()) {   // what Next set off (the fruit) plays out before the opponent moves on
    clearTimeout(holdBot.t); holdBot.t = setTimeout(() => holdBot(false), C.ui.animUntil - Date.now() + 20); return; }
  if (on) clearTimeout(holdBot.t);
  if (on !== botHeld && isLesson(C.V())) { botHeld = on; C.send({ t: 'hold', on }); } };
export function drawCoach(el, L, rings = []) {
  el.className = 'abs coach';
  if (!L) { if (!C.ui.step) holdBot(false); el.innerHTML = ''; document.getElementById('board').classList.remove('pulse'); return; }
  const a = L.at || {}, card = a.card && document.querySelector(`#hand .hc[data-id="${a.card}"]`);
  let x, y, side;
  // the edge pieces sit at the window's edges (fitStage's --above/--side, stage px): anchors on them move with them
  const st = getComputedStyle(document.getElementById('stage')), up = parseFloat(st.getPropertyValue('--above')) || 0, out = parseFloat(st.getPropertyValue('--side')) || 0;
  const read = a.read && document.querySelector(`#hand .hc[data-id="${a.read}"]`);
  const P = C.PL(), port = VIEW.port, H = P.hand + up; COACH_W = port ? 400 : 300;
  // upright, the stage is too narrow for a line beside a thing: the coach stands above it or below it, its notch pointing
  const vert = (x, y, r) => y > STAGE.h / 2 ? [x, y - r, 'above'] : [x, y + r, 'below'];
  if (read) { const cx = parseFloat(read.style.left) + 71.5;   // beside the large card (2.1x: 300 wide, so 150 + a 24 gap from its middle)
    [x, y, side] = port ? [cx, H - 243, 'above']   // upright, over it (it grows 2.1x from its foot)
      : cx - 174 - COACH_W >= 16 ? [cx - 96, 568 + up, 'left'] : [cx + 96, 568 + up, 'right']; }
  else if (card) [x, y, side] = [parseFloat(card.style.left) + 71.5, (card.classList.contains('sel') ? H - 18 : H), 'above'];   // a picked card stands 18px higher
  else if (a.deck) [x, y, side] = port ? [P.deck[0] - 50 + out, 0, 'cleft'] : [P.deck[0] + out, P.deck[1] + up, 'above'];   // upright, left of the corner: the deck and End turn stand together
  else if (a.prompt) { const pb = document.getElementById('choicebar');   // under the card's question (upright it stands top left, and wraps)
    [x, y, side] = port ? [16 + pb.offsetWidth / 2, pb.offsetTop + pb.offsetHeight - 14 - up, 'below'] : [STAGE.w / 2, 100 - up, 'below']; }
  else if (a.endturn) [x, y, side] = port ? [P.end[0] - 55 + out, 0, 'cleft'] : [P.end[0] + out, P.end[1] + up, 'above'];
  else if (a.cr) { [x, y] = crossroadAt(a.cr); if (port) [x, y, side] = vert(x, y, 52); else side = x > STAGE.w / 2 ? 'left' : 'right'; }
  else if (a.den) { [x, y] = denMouthAt(a.den); if (port) [x, y, side] = vert(x, y, 40); else side = a.den === 'B' ? 'left' : 'right'; }
  else if (a.rings && !rings.length) [x, y, side] = [P.handC, H, 'above'];   // no card picked yet: the circles come with one, so point at the hand
  else if (a.rings) {   // beside the group of rings, clear of all of them, with no notch (the rings pulse instead)
    const rs = rings.map(crossroadAt);   // this frame's rings, before the board redraws
    const xs = rs.map(r => r[0]), ys = rs.map(r => r[1]), cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    const right = Math.max(...xs) + 78;
    const left = Math.min(...xs) - 78 - COACH_W;
    if (port) [x, y, side] = Math.min(...ys) > 420 ? [STAGE.w / 2, Math.min(...ys) - 62, 'gabove']   // over the group, or under it
      : Math.max(...ys) < 880 ? [STAGE.w / 2, Math.max(...ys) + 62, 'gbelow'] : [STAGE.w / 2, H, 'above'];
    else [x, y, side] = right + COACH_W < STAGE.w - 16 ? [right, cy, 'group'] : left >= 16 ? [left, cy, 'group']
      : [STAGE.w / 2, H, 'above'];   // circles across the whole board (Flight): above the hand, pointing at the picked card
  }
  else if (a.gem) { const g = gemAt(a.gem); [x, y, side] = port ? vert(g[0], g[1], 44) : a.gem === 'A' ? [150, 122, 'right'] : [STAGE.w - 150, 122, 'left']; }   // a den's food gem, on its crown
  else if (a.hand) [x, y, side] = [P.handC, H, 'above'];
  else if (a.oppcards) [x, y, side] = port ? [STAGE.w / 2, 72, 'below'] : [STAGE.w / 2 + 170, 72, 'below'];   // beside the opponent's card backs, clear of their revealed card
  else if (a.middle) [x, y, side] = port ? [STAGE.w / 2, 650, 'mid'] : [STAGE.w / 2, 250, 'mid'];
  else if (a.region) {   // to the right of the region, which glows (drawBoard), clear of all of it
    const ps = a.region.map(crossroadAt), ys = ps.map(p => p[1]);
    if (port) [x, y, side] = Math.min(...ys) > 420 ? [STAGE.w / 2, Math.min(...ys) - 62, 'gabove'] : [STAGE.w / 2, Math.max(...ys) + 62, 'gbelow'];
    else [x, y, side] = [Math.max(...ps.map(p => p[0])) + 2, (Math.min(...ys) + Math.max(...ys)) / 2, 'right']; }
  else if (a.stone) { const [c, r] = a.stone.split(',').map(Number), [x1, y1] = crossroadAt(`${c},${r}`), [x2, y2] = crossroadAt(`${c + 1},${r + 1}`);
    [x, y, side] = port ? vert((x1 + x2) / 2, (y1 + y2) / 2, 34) : [(x1 + x2) / 2 - 20, (y1 + y2) / 2, 'right']; }   // a region's payout stone, in the open ground between crossroads
  else [x, y, side] = [STAGE.w / 2, H, 'above'];
  const clampX = v => Math.max(16, Math.min(STAGE.w - 16 - COACH_W, v));
  const pos = side === 'above' ? `left:${clampX(x - COACH_W / 2)}px;bottom:${STAGE.h - y + 14}px;--nx:${x - clampX(x - COACH_W / 2)}px`
    : side === 'below' ? `left:${clampX(x - COACH_W / 2)}px;top:${y + 14}px;--nx:${x - clampX(x - COACH_W / 2)}px`
    : side === 'mid' ? `left:${x - COACH_W / 2}px;top:${y}px`
    : side === 'group' ? `left:${x}px;top:${y}px`
    : side === 'cleft' ? `left:${x - 24 - COACH_W}px;bottom:${16 - up}px`   // upright, along the bottom edge left of the deck and End turn
    : side === 'gabove' ? `left:${x - COACH_W / 2}px;bottom:${STAGE.h - y}px` : side === 'gbelow' ? `left:${x - COACH_W / 2}px;top:${y}px`
    : side === 'right' ? `left:${x + 78}px;top:${y}px` : `left:${x - 78 - COACH_W}px;top:${y}px`;
  document.getElementById('board').classList.toggle('pulse', !!a.rings);
  holdBot(!!L.next);
  el.className = `abs coach on ${side}${L.next ? ' talk' : ''}`; el.style.cssText = pos;
  el.style.setProperty('--up', `${up}px`);   // a risen coach clears the lifted card, which moved with the hand
  el.dataset.iid = side === 'above' && y >= P.hand - 18 + up ? (card ? card.dataset.iid : 'any') : '';   // over the hand: a hovered card lifts it   // hovering that card lifts the coach above it (wireCoachHover)
  // the words follow what is on screen: one circle is "the circle" (enemy, animal), several are "one of"; with one card lit,
  // "one of your animals" names it
  let text = rings.length === 1 ? L.text.replace('one of the circles', 'the circle').replace('Click one.', 'Click it.')
      .replace('one of the circled enemies', 'the circled enemy').replace('one of the circled animals', 'the circled animal')
    : L.text.replace(/\bthe circle\b(?! next)/, 'one of the circles');
  const lit = [...document.querySelectorAll('#hand .hc.can')];
  if (lit.length === 1 && !rings.length) text = text.replace(/Click (any|one) of your animals\./, `Click the ${C.CARDS()[lit[0].dataset.id].name}.`);
  el.innerHTML = `<p>${C.tapWords(text)}</p>` + (L.next ? '<button class="slab" id="coachnext">Next</button>' : '');
  // an opening step closes on Next (or Enter/Space), and the next one shows
  if (L.next) el.querySelector('#coachnext').onclick = e => { e.stopPropagation(); tutState().seen.add(L.id);
    const ui = C.ui; if (ui.heldFood) { ui.anim = ui.heldFood; ui.heldFood = null; ui.animUntil = Date.now() + 1800 / (window.AK_SPEED || 1); }   // the held fruit flies now, uninterrupted
    C.drawGame(); };
}
