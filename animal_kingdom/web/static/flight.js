// A card played flies to its crossroad and lands there as the piece (Martin, 2026-11-12: a played card "just disappears from
// your hand and then the token appears on the board, out of thin air"). One object the eye can follow, as Hearthstone plays a
// minion (its frames at 60 fps, design sandbox screen/play-flight/hs-ref/): the full card, text and all, pops out of the hand
// (or the opponent's card leaves the centre) and flies over its place, a physical thing tilting in 3D as it goes; over its
// place it is cut, in one frame, to the piece, centred where the card's painting was; the piece hangs a beat, then drops onto
// the crossroad (game.css @keyframes landf).
//
// The travel is Hearthstone's measured curve: a short lift, then a strong ease-out (40% of the way in the first quarter of
// the time, 95% by three quarters) on a curved path. It runs on the browser's compositor (Web Animations, transform only) on
// its own layer over the page, so no redraw of the board or the hand can stall or cut it. Until the cut the crossroad shows
// what it showed before (board.js); at the cut the board is redrawn (`onArrive`) with the piece landing, and the layer goes
// in that frame.
import { hasArt } from './art.js';
import { fitNames } from './card.js';

export const FLY_MS = 520;
export const LIFT = 0;                // stage pixels above its crossroad the card stops and turns: none, it turns right over it and the piece falls toward the board (game.css landf)
const POP_MS = 90;                    // the pop out of the hand
export const CARD_END = 130; const CARD_W = CARD_END;                 // the card's width over its place, in stage pixels: its painting about the piece's size
export const PIC_UP = 2.55 / 20; const PIC_C = PIC_UP;             // the card's painting's centre above the card's centre, in card widths (app.css .card)
// The turn, as Hearthstone turns a minion (its 60 fps frames, design sandbox screen/play-flight/hs-ref/): at rest over its
// crossroad the card turns to light, a painted plate of sunlight in its shape (kit2/glow_plate.webp) brightening over it;
// under the light the card becomes the piece; the light thins and draws in to the portrait, which settles onto the board
// (game.css landf). Light, not a cover laid on top: the card itself is what glows.
const GLOW_IN = 90, GLOW_HOLD = 90, GLOW_OUT = 260;   // ms: the card lights up, stays lit (the cut at its middle), the light goes
// Impact (Martin, 2026-11-13, the best of the card-play study's prototypes, design sandbox screen/play-flight/study/): over its
// crossroad the card rears up toward the eye, then is thrown down, shrinking as it falls away to the piece's size, and on the
// frame it hits it is the piece, squashed by the hit, inside a flash of painted light and a ring of dust, the board jolting,
// with the landing's sound. `?turn=glow` keeps the earlier turn (the card turned to light over its place) to compare.
export const TURN = new URLSearchParams(globalThis.location?.search || '').get('turn') === 'glow' ? 'glow' : 'impact';
if (globalThis.document) document.documentElement.dataset.turn = TURN;
const REAR_MS = 120, THROW_MS = 180;  // the card rears up toward the eye, then is thrown down onto its place
const REAR_C = 152, HIT_C = 128;      // its width reared up, and as it hits (the piece's rim is 134), in stage pixels
export const HIT_DELAY = TURN === 'impact' ? 0 : .41;   // s from the cut to the piece's impact (game.css landf / landi)
let cur = null;                       // the flight in the air: { cr, el, arrived, onArrive, before, anim }
let last = null;                      // the latest flight's { cr, end }, kept after its layer goes: the landing it handed to runs on

const quadOut = t => 1 - (1 - t) * (1 - t);
const clamp = (v, m) => Math.max(-m, Math.min(m, v));

// The card's own layer over the page, for a flight: `html` (the card in full) or a copy of `from`, at the card's size.
function layer(from, html, w, h) {
  const el = document.createElement('div'); el.className = 'flight';
  const fc = document.createElement('div'); fc.className = 'fcard';
  fc.style.cssText = `width:${w}px;height:${h}px;left:${-w / 2}px;top:${-h / 2}px`;
  if (html) fc.innerHTML = html; else fc.appendChild(from.cloneNode(true));
  const card = fc.firstElementChild; card.style.cssText += `;--w:${w}px;width:${w}px;height:${h}px;`;
  el.appendChild(fc); document.body.appendChild(el);
  if (html) fitNames(fc);
  return { el, fc, card };
}
const poser = k => (x, y, s, rx, ry, rz) => ({ transform: `translate(${x}px,${y}px) perspective(${900 * k}px) rotateX(${rx}deg) rotateY(${ry}deg) rotateZ(${rz}deg) scale(${s})` });

// The way there, from (x0, y0) at scale s0 to (x1, y1) at s1 (screen pixels; k the stage's scale): the throw out of the hand,
// or, for a card held in the grip (`start`), the short settle from where the grip left it. Its keyframes and length, every
// card that leaves the hand (fly() to a crossroad, dive() into a den) taking the same path.
function travel(card, k, x0, y0, s0, x1, y1, s1, start) {
  // The path: a quadratic curve bending off the straight line (it swings out, then comes in) and a little up (it is thrown,
  // not slid), sampled densely in time with the measured ease-out. The card tilts in 3D with its speed: it banks toward
  // where it is going, its leading edge dipping, and rocks just past level as it stops.
  const dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy) || 1, side = dx >= 0 ? 1 : -1;
  const cx = x0 + dx * .45 + (-dy / len) * side * Math.min(80, len * .18) * k, cy = y0 + dy * .45 - 30 * k;
  const at = u => [(1 - u) * (1 - u) * x0 + 2 * (1 - u) * u * cx + u * u * x1, (1 - u) * (1 - u) * y0 + 2 * (1 - u) * u * cy + u * u * y1];
  const pose = poser(k), speed = window.AK_SPEED || 1;
  let dur, frames;
  if (start) {   // held: it settles from where the grip left it, its tilt easing out as it stops (a little longer the farther)
    // (Impact: no settle of its own when it is already there, the rear-up starts at once; a still beat reads as a pause)
    dur = (TURN === 'impact' ? Math.min(FLY_MS, 30 + len / k * .45) : Math.min(FLY_MS, 150 + len / k * .35)) / speed;
    // its shadow draws in under it as it comes down from the grip's height (game.css .flight.carry)
    const sh = (o, x, y, b, a) => `drop-shadow(0 0 1px rgba(30,18,6,${o})) drop-shadow(${x}px ${y}px ${b}px rgba(20,12,4,${a}))`;
    frames = [{ ...pose(x0, y0, s0, start.rx, start.ry, start.rz), offset: 0, easing: 'cubic-bezier(.25,.7,.35,1)' },
      { ...pose(x1 + (x0 - x1) * .04, y1 + (y0 - y1) * .04, s1, -start.rx * .15, -start.ry * .15, 0), offset: .8, easing: 'ease-in-out' },
      { ...pose(x1, y1, s1, 0, 0, 0), offset: 1 }];
    card.animate([{ filter: sh(.8, 30, 46, 14, .85) }, { filter: sh(.4, 4, 10, 8, .4) }], { duration: dur * .8, easing: 'cubic-bezier(.25,.7,.35,1)', fill: 'forwards' });
  } else {
    dur = FLY_MS / speed; const pop = POP_MS / FLY_MS;
    frames = [{ ...pose(x0, y0, s0, 0, 0, 0), offset: 0, easing: 'cubic-bezier(.2,.6,.4,1)' },
      { ...pose(x0, y0 - 18 * k, s0 * 1.08, 14, 0, 0), offset: pop }];   // the pop: it lifts and tips back
    const N = 16;
    let [px, py] = [x0, y0 - 18 * k];
    for (let i = 1; i <= N; i++) {
      const f = i / N, q = quadOut(f), [x, y] = at(q), vx = (x - px) / (len / N), vy = (y - py) / (len / N), fade = 1 - f;
      const rx = i === N ? 0 : i === N - 1 ? -3 : clamp(-vy * 16, 22) * fade + 14 * (1 - Math.min(1, f * 3));   // nose toward its way
      const ry = i === N ? 0 : i === N - 1 ? 2 * side : clamp(vx * 18, 24) * fade;
      const rz = i === N ? 0 : clamp(vx * 7, 8) * fade;
      frames.push({ ...pose(x, y - 18 * k * (1 - q), s0 * 1.08 + (s1 - s0 * 1.08) * q, rx, ry, rz), offset: pop + (1 - pop) * f });
      px = x; py = y;
    }
  }
  return { dur, frames };
}

// Fly from the card `from` (a .card element on screen) to the crossroad element `target`. `html`: the card to fly, in full
// (cardHTML), else `from` itself; `id`: its card; `cr`: the crossroad's key, which the board asks about (inFlight, flightEnd);
// `before`: the units there before the play, shown until the cut; `onArrive(covered)`: redraws the board. Returns false
// when it can't fly (no art, reduced motion), and the play looks as it always did.
// Off on live (Martin, 2026-11-12: live plays without it while he compares); on staging and localhost.
export const FLIGHT = globalThis.location?.hostname !== 'animal-kingdom.fly.dev';

// `start`: the pose of a card held in the pointer's grip (carry.js release()), which it flies on from, without the pop out of
// the hand: a held card is already over its crossroad, so its flight is the short settle into place.
// `geo`: another card form's measures (the mana ruleset's card, mana.js: the piece over a plaque), { end: its width over its
// place, up: its piece's centre above its own centre in card widths, rear, hit: its widths reared up and as it hits }.
export function fly(from, target, id, cr, before, onArrive, html = null, start = null, geo = null) {
  if (!FLIGHT || (!from && !start) || !target || !hasArt(id) || matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
  const CARD_END = geo ? geo.end : CARD_W, PIC_UP = geo ? geo.up : PIC_C, REAR_W = geo ? geo.rear : REAR_C, HIT_W = geo ? geo.hit : HIT_C;
  const stage = document.getElementById('stage'), k = stage.getBoundingClientRect().width / stage.offsetWidth;
  const C = start ? null : from.getBoundingClientRect(), t = target.getBoundingClientRect();
  const w = start ? start.w : from.offsetWidth, h = start ? start.h : from.offsetHeight;   // the card's own size (the full card has the same outline)
  const x0 = start ? start.x : C.left + C.width / 2, y0 = start ? start.y : C.top + C.height / 2, s0 = start ? start.s : C.width / w, s1 = CARD_END * k / w;
  const x1 = t.left + t.width / 2, y1 = t.top + t.height / 2 - LIFT * k + PIC_UP * CARD_END * k;   // its painting over the piece's

  done();
  const { el, fc, card } = layer(from, html, w, h);
  const pose = poser(k), speed = window.AK_SPEED || 1;
  let { dur, frames } = travel(card, k, x0, y0, s0, x1, y1, s1, start);
  const me = cur = { cr, el, arrived: false, onArrive, before: before || [] };
  const cx0 = t.left + t.width / 2, cy0 = t.top + t.height / 2;
  let cutAt;
  if (TURN === 'impact') {
    // rear up and throw down, after the travel: the travel's keyframes shrink into the first part of one longer animation
    const T = dur + (REAR_MS + THROW_MS) / speed, sr = REAR_W * k / w, sh = HIT_W * k / w;
    frames.forEach(f => { f.offset *= dur / T; });
    frames[frames.length - 1].easing = 'cubic-bezier(.3,.6,.4,1)';
    frames.push({ ...pose(cx0, cy0 + PIC_UP * REAR_W * k - 10 * k, sr, 8, 0, 0), offset: (dur + REAR_MS / speed) / T, easing: 'cubic-bezier(.5,0,.85,.4)' });
    frames.push({ ...pose(cx0, cy0 + PIC_UP * HIT_W * k, sh, 0, 0, 0), offset: 1 });
    const sha = (x, y, b, a) => `drop-shadow(0 0 1px rgba(30,18,6,.5)) drop-shadow(${x}px ${y}px ${b}px rgba(20,12,4,${a}))`;
    card.animate([{ filter: sha(4, 10, 8, .4), offset: 0 }, { filter: sha(4, 10, 8, .4), offset: dur / T, easing: 'ease-out' },
      { filter: sha(22, 34, 14, .5), offset: (dur + REAR_MS / speed) / T, easing: 'cubic-bezier(.5,0,.85,.4)' },
      { filter: sha(1, 2, 2, .6), offset: 1 }], { duration: T, fill: 'forwards' });
    dur = T; cutAt = T;
  } else cutAt = dur + (GLOW_IN + GLOW_HOLD / 2) / speed;   // the card stops, lights up, and turns under the light
  last = { cr, end: Date.now() + cutAt };
  me.anim = fc.animate(frames, { duration: dur, fill: 'forwards' });
  if (TURN === 'glow') glow(x1, y1, w * s1, h * s1, PIC_UP * w * s1, dur, speed);
  else me.anim.finished.then(() => { if (cur === me) hit(cx0, cy0, k); }, () => {});
  // the cut: the piece in the card's place in the same frame (board.js, game.css .flown); a view still on its way keeps the
  // card there until it comes
  me.anim.finished.then(() => setTimeout(() => {
    if (cur !== me) return; me.arrived = true; last.end = Date.now(); if (me.onArrive) me.onArrive(me.before.length > 0);
  }, cutAt - dur), () => {});
  me.giveUp = setTimeout(() => { if (cur === me) done(); }, dur + 4000);   // a play the server refused: the card lets go
  return true;
}

// The hit: a flash of painted light added over the place (plus-lighter: it brightens what is under it), and the board jolts.
function hit(x, y, k) {
  const f = document.createElement('div'); f.className = 'fflash';
  const d = 300 * k; f.style.cssText = `width:${d}px;height:${d}px;left:${x - d / 2}px;top:${y - d / 2}px`;
  document.body.appendChild(f);
  f.animate([{ opacity: .55, transform: 'scale(.9)' }, { opacity: 0, transform: 'scale(1.25)' }], { duration: 240, easing: 'cubic-bezier(.2,.6,.4,1)', fill: 'both' })
    .finished.then(() => f.remove(), () => f.remove());
  const b = document.getElementById('board');
  if (b) b.animate([0, 1, 2, 3, 4, 5, 6].map(i => { const d = 5 * (1 - i / 6); return { transform: `translate(${Math.sin(i * 2.6) * d}px,${Math.cos(i * 2.1) * d * .7}px)` }; }), { duration: 220, easing: 'linear' });
}

// The light over the card at rest (centred at x, y, cw x ch on screen; its painting `up` above that): it brightens over the
// card, holds while the card becomes the piece beneath it, then thins and draws in to the portrait. Its own element, so the
// flight layer going at the cut doesn't take it.
const PLATE = { w: 1.32, h: 1.21 };   // the painted plate's size over the card's outline (its halo around it; design sandbox key.py)
function glow(x, y, cw, ch, up, dur, speed) {
  const g = document.createElement('div'); g.className = 'fglow';
  const pw = cw * PLATE.w, ph = ch * PLATE.h;
  g.style.cssText = `width:${pw}px;height:${ph}px;left:${x - pw / 2}px;top:${y - ph / 2}px;transform-origin:50% ${ph / 2 - up}px`;
  document.body.appendChild(g);
  const a = GLOW_IN / speed, b = GLOW_HOLD / speed, c = GLOW_OUT / speed, T = a + b + c;
  g.animate([
    { opacity: 0, transform: 'scale(.98)', offset: 0, easing: 'cubic-bezier(.3,.6,.5,1)' },
    { opacity: 1, transform: 'scale(1.02)', offset: a / T },
    { opacity: 1, transform: 'scale(1)', offset: (a + b) / T, easing: 'cubic-bezier(.4,0,.7,.6)' },
    { opacity: 0, transform: 'scale(.62)', offset: 1 },
  ], { duration: T, delay: dur, fill: 'both' }).finished.then(() => g.remove(), () => g.remove());
}

// A card is still on its way to `cr`: the units the crossroad shows meanwhile (what it had), else null.
export function inFlight(cr) { return cur && cur.cr === cr && !cur.arrived ? cur.before : null; }
// When the card flying to `cr` was cut to the piece (Date.now() ms), for the board's landing there; null when none came lately.
export function flightEnd(cr) {
  return last && last.cr === cr && Date.now() - last.end < 3000 ? last.end : null;
}
// The board drew the piece the flight brought, landing: the layer goes in this frame.
export function landed(cr) { if (cur && cur.cr === cr && cur.arrived) done(); }
export function flying() { return cur ? cur.cr : null; }
function done() { if (!cur) return; clearTimeout(cur.giveUp); cur.el.remove(); cur = null; }

// A raid from the hand: the card takes the same way out of the hand (or on from the grip, `start`) to the den's ball
// `target` (its .core), arriving at the ball's size, and goes into it; the food it destroys then leaves the den
// (foodfx.js, in the view's own steps). Returns false when it can't fly (reduced motion), as fly() does.
export function dive(from, target, html = null, start = null) {
  if (!FLIGHT || (!from && !start) || !target || matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
  const stage = document.getElementById('stage'), k = stage.getBoundingClientRect().width / stage.offsetWidth;
  const C = start ? null : from.getBoundingClientRect(), t = target.getBoundingClientRect();
  const w = start ? start.w : from.offsetWidth, h = start ? start.h : from.offsetHeight;
  const x0 = start ? start.x : C.left + C.width / 2, y0 = start ? start.y : C.top + C.height / 2, s0 = start ? start.s : C.width / w;
  const x1 = t.left + t.width / 2, y1 = t.top + t.height / 2, s1 = t.width / w;
  const { el, fc, card } = layer(from, html, w, h);
  const { dur, frames } = travel(card, k, x0, y0, s0, x1, y1, s1, start);
  const into = DIVE_MS / (window.AK_SPEED || 1), T = dur + into;
  frames.forEach(f => { f.offset *= dur / T; });
  frames.push({ ...poser(k)(x1, y1, s1 * .2, 0, 0, 0), offset: 1 });   // into the light
  fc.animate(frames, { duration: T, fill: 'forwards' });
  el.animate([{ opacity: 1, offset: 0 }, { opacity: 1, offset: dur / T, easing: 'ease-in' }, { opacity: 0, offset: 1 }], { duration: T, fill: 'forwards' })
    .finished.then(() => el.remove(), () => el.remove());
  return true;
}
const DIVE_MS = 160;   // from the ball's size into it
