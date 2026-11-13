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
export const LIFT = 160;              // stage pixels above its crossroad the card stops, turns, and the piece falls from (game.css landf)
const POP_MS = 90;                    // the pop out of the hand
export const CARD_END = 130;                 // the card's width over its place, in stage pixels: its painting about the piece's size
export const PIC_UP = 2.55 / 20;             // the card's painting's centre above the card's centre, in card widths (app.css .card)
// The burst that hides the cut, painted (kit2/burst_<name>.webp): it swells over the card in the flight's last moment, the
// card becomes the piece under it, and it thins away as the piece drops. `?burst=` picks one while they are compared.
const BURST = new URLSearchParams(globalThis.location?.search || '').get('burst') || 'poof';
const BURST_IN = 150, BURST_OUT = 380, BURST_W = 300;   // ms from the card's stop to the burst's peak (the cut), ms to thin away; width in stage px
let cur = null;                       // the flight in the air: { cr, el, arrived, onArrive, before, anim }
let last = null;                      // the latest flight's { cr, end }, kept after its layer goes: the landing it handed to runs on

const quadOut = t => 1 - (1 - t) * (1 - t);
const clamp = (v, m) => Math.max(-m, Math.min(m, v));

// Fly from the card `from` (a .card element on screen) to the crossroad element `target`. `html`: the card to fly, in full
// (cardHTML), else `from` itself; `id`: its card; `cr`: the crossroad's key, which the board asks about (inFlight, flightEnd);
// `before`: the units there before the play, shown until the cut; `onArrive(covered)`: redraws the board. Returns false
// when it can't fly (no art, reduced motion), and the play looks as it always did.
// Off on live (Martin, 2026-11-12: live plays without it while he compares); on staging and localhost.
export const FLIGHT = globalThis.location?.hostname !== 'animal-kingdom.fly.dev';

// `start`: the pose of a card held in the pointer's grip (carry.js release()), which it flies on from, without the pop out of
// the hand: a held card is already over its crossroad, so its flight is the short settle into place.
export function fly(from, target, id, cr, before, onArrive, html = null, start = null) {
  if (!FLIGHT || (!from && !start) || !target || !hasArt(id) || matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
  const stage = document.getElementById('stage'), k = stage.getBoundingClientRect().width / stage.offsetWidth;
  const C = start ? null : from.getBoundingClientRect(), t = target.getBoundingClientRect();
  const w = start ? start.w : from.offsetWidth, h = start ? start.h : from.offsetHeight;   // the card's own size (the full card has the same outline)
  const x0 = start ? start.x : C.left + C.width / 2, y0 = start ? start.y : C.top + C.height / 2, s0 = start ? start.s : C.width / w, s1 = CARD_END * k / w;
  const x1 = t.left + t.width / 2, y1 = t.top + t.height / 2 - LIFT * k + PIC_UP * CARD_END * k;   // its painting over the piece's

  done();
  const el = document.createElement('div'); el.className = 'flight';
  const fc = document.createElement('div'); fc.className = 'fcard';
  fc.style.cssText = `width:${w}px;height:${h}px;left:${-w / 2}px;top:${-h / 2}px`;
  if (html) fc.innerHTML = html; else fc.appendChild(from.cloneNode(true));
  const card = fc.firstElementChild; card.style.cssText += `;--w:${w}px;width:${w}px;height:${h}px;`;
  el.appendChild(fc); document.body.appendChild(el);
  if (html) fitNames(fc);

  // The path: a quadratic curve bending off the straight line (it swings out, then comes in) and a little up (it is thrown,
  // not slid), sampled densely in time with the measured ease-out. The card tilts in 3D with its speed: it banks toward
  // where it is going, its leading edge dipping, and rocks just past level as it stops.
  const dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy) || 1, side = dx >= 0 ? 1 : -1;
  const cx = x0 + dx * .45 + (-dy / len) * side * Math.min(80, len * .18) * k, cy = y0 + dy * .45 - 30 * k;
  const at = u => [(1 - u) * (1 - u) * x0 + 2 * (1 - u) * u * cx + u * u * x1, (1 - u) * (1 - u) * y0 + 2 * (1 - u) * u * cy + u * u * y1];
  const pose = (x, y, s, rx, ry, rz) => ({ transform: `translate(${x}px,${y}px) perspective(${900 * k}px) rotateX(${rx}deg) rotateY(${ry}deg) rotateZ(${rz}deg) scale(${s})` });
  const speed = window.AK_SPEED || 1;
  let dur, frames;
  if (start) {   // held: it settles from where the grip left it, its tilt easing out as it stops (a little longer the farther)
    dur = Math.min(FLY_MS, 150 + len / k * .35) / speed;
    frames = [{ ...pose(x0, y0, s0, start.rx, start.ry, start.rz), offset: 0, easing: 'cubic-bezier(.25,.7,.35,1)' },
      { ...pose(x1 + (x0 - x1) * .04, y1 + (y0 - y1) * .04, s1, -start.rx * .15, -start.ry * .15, 0), offset: .8, easing: 'ease-in-out' },
      { ...pose(x1, y1, s1, 0, 0, 0), offset: 1 }];
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
  const me = cur = { cr, el, arrived: false, onArrive, before: before || [] };
  const cutAt = dur + (BURST !== 'none' ? BURST_IN / speed : 0);   // the card stops, the burst swells over it, then the cut
  last = { cr, end: Date.now() + cutAt };
  me.anim = fc.animate(frames, { duration: dur, fill: 'forwards' });
  if (BURST !== 'none') {
    burst(x1, y1 - PIC_UP * CARD_END * k * .5, BURST_W * k, dur, speed);
    // the card is drawn into the burst as it swells: it pulls in toward its painting, so no frame or text is left to vanish
    card.style.transformOrigin = `50% ${h / 2 - PIC_UP * w}px`;
    card.animate([{ transform: 'scale(1)' }, { transform: 'scale(.62)' }],
      { duration: BURST_IN / speed, delay: dur, easing: 'cubic-bezier(.5,0,.9,.6)', fill: 'forwards' });
  }
  // the cut: the piece in the card's place in the same frame (board.js, game.css .flown); a view still on its way keeps the
  // card there until it comes
  me.anim.finished.then(() => setTimeout(() => {
    if (cur !== me) return; me.arrived = true; last.end = Date.now(); if (me.onArrive) me.onArrive(me.before.length > 0);
  }, cutAt - dur), () => {});
  me.giveUp = setTimeout(() => { if (cur === me) done(); }, dur + 4000);   // a play the server refused: the card lets go
  return true;
}

// The painted burst over the card's last place: in, peaking at the cut, then out while the piece drops under it. Its own
// element, so the flight layer going at the cut doesn't take it.
function burst(x, y, w, dur, speed) {
  const b = document.createElement('div'); b.className = 'fburst';
  b.style.cssText = `width:${w}px;height:${w}px;left:${x - w / 2}px;top:${y - w / 2}px;background-image:url(/static/kit2/burst_${BURST}.webp)`;
  document.body.appendChild(b);
  const tin = BURST_IN / speed, tout = BURST_OUT / speed, rot = (Math.random() * 2 - 1) * 40;
  b.animate([
    { transform: `rotate(${rot}deg) scale(.35)`, opacity: 0, offset: 0, easing: 'cubic-bezier(.3,.7,.4,1)' },
    { transform: `rotate(${rot + 6}deg) scale(1)`, opacity: 1, offset: tin / (tin + tout), easing: 'cubic-bezier(.2,.6,.3,1)' },
    { transform: `rotate(${rot + 14}deg) scale(1.35)`, opacity: 0, offset: 1 },
  ], { duration: tin + tout, delay: dur, fill: 'both' }).finished.then(() => b.remove(), () => b.remove());
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
