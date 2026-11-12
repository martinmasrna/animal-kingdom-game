// A card played flies to its crossroad and lands there as the piece (Martin, 2026-11-12: a played card "just disappears from
// your hand and then the token appears on the board, out of thin air"). One object the eye can follow: the card pops out of
// the hand (or the opponent's card leaves the centre), flies on a curve, leaning into it, slowing as it comes in, and drops
// onto the crossroad; at the impact it is the piece, and the dust hides the change.
//
// The motion is Hearthstone's, measured from its footage at 60 fps (design sandbox screen/play-flight/hs-ref/): a short lift,
// then a strong ease-out (40% of the way in the first quarter of the time, 95% by three quarters) on a curved path.
// It runs on the browser's compositor (Web Animations, transform only) on its own layer over the page, so no redraw of the
// board or the hand can stall or cut it. Until it lands the crossroad shows what it showed before (board.js); at the impact
// the board is redrawn (`onArrive`) with the piece landing, and the layer goes in that frame.
import { hasArt } from './art.js';

export const FLY_MS = 560;
const LIFT_MS = 90, DROP_MS = 110;    // the pop out of the hand, and the fall onto the ground at the end
const CARD_END = 104;                 // the card's width as it touches down, in stage pixels (the piece's rim is 134 across)
let cur = null;                       // the flight in the air: { cr, el, arrived, onArrive, anim }
let last = null;                      // the latest flight's { cr, end }, kept after its layer goes: the landing it handed to runs on

const quadOut = t => 1 - (1 - t) * (1 - t);

// Fly `card` (a .card element) to the crossroad element `target`. `id`: the card; `cr`: the crossroad's key, which the board
// asks about (inFlight, flightEnd); `before`: the units there before the play, shown until the card lands; `onArrive`:
// redraws the board. Returns false when it can't fly (no art, reduced motion),
// and the play looks as it always did.
export function fly(card, target, id, owner, cr, before, onArrive) {
  if (!card || !target || !hasArt(id) || matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
  const stage = document.getElementById('stage'), k = stage.getBoundingClientRect().width / stage.offsetWidth;
  const C = card.getBoundingClientRect(), t = target.getBoundingClientRect();
  const w = card.offsetWidth, h = card.offsetHeight, kc = C.width / w;   // the card's own size, and its scale on screen
  const x0 = C.left + C.width / 2, y0 = C.top + C.height / 2, x1 = t.left + t.width / 2, y1 = t.top + t.height / 2;
  const s0 = kc, s1 = CARD_END * k / w;

  done();
  const el = document.createElement('div'); el.className = 'flight';
  const fc = document.createElement('div'); fc.className = 'fcard';
  const clone = card.cloneNode(true);
  clone.style.cssText += `;--w:${w}px;width:${w}px;height:${h}px;`;
  fc.style.cssText = `width:${w}px;height:${h}px;left:${-w / 2}px;top:${-h / 2}px`;
  fc.appendChild(clone); el.appendChild(fc); document.body.appendChild(el);

  // The path: a quadratic curve whose bend sits off the straight line, to the side the card starts on (it swings out, then
  // comes in), and a little up (it is thrown, not slid). Sampled densely in time with the measured ease-out.
  const dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy) || 1, side = dx >= 0 ? 1 : -1;
  const cx = x0 + dx * .45 + (-dy / len) * side * Math.min(80, len * .18) * k, cy = y0 + dy * .45 - 30 * k;
  const at = u => [(1 - u) * (1 - u) * x0 + 2 * (1 - u) * u * cx + u * u * x1, (1 - u) * (1 - u) * y0 + 2 * (1 - u) * u * cy + u * u * y1];
  const pose = (x, y, s, r) => ({ transform: `translate(${x}px,${y}px) rotate(${r}deg) scale(${s})` });
  const speed = window.AK_SPEED || 1, dur = FLY_MS / speed, lift = LIFT_MS / FLY_MS, drop = DROP_MS / FLY_MS;
  const frames = [{ ...pose(x0, y0, s0, 0), offset: 0, easing: 'cubic-bezier(.2,.6,.4,1)' },
    { ...pose(x0, y0 - 16 * k, s0 * 1.06, 0), offset: lift }];   // the pop out of the hand
  const N = 14, travel = 1 - lift - drop, sHigh = s1 * 1.22;   // it flies a little large (high), then drops to its size
  let px = x0;
  for (let i = 1; i <= N; i++) {
    const q = quadOut(i / N), [x, y] = at(q);
    const vx = (x - px) / (len / N);                                     // leaning into the turn, upright as it slows
    const r = i === N ? 0 : Math.max(-9, Math.min(9, vx * 10 * (1 - i / N)));
    frames.push({ ...pose(x, y - 16 * k * (1 - q), s0 * 1.06 + (sHigh - s0 * 1.06) * q, r), offset: lift + travel * i / N });
    px = x;
  }
  frames[frames.length - 1].easing = 'cubic-bezier(.55,0,1,.6)';   // the fall accelerates into the ground
  frames.push({ ...pose(x1, y1, s1, 0), offset: 1 });
  const me = cur = { cr, el, arrived: false, onArrive, before: before || [] };
  last = { cr, end: Date.now() + dur };
  me.anim = fc.animate(frames, { duration: dur, fill: 'forwards' });
  // the impact: the piece lands in the card's place in the same frame (board.js, game.css .flown)
  me.anim.finished.then(() => { if (cur !== me) return; me.arrived = true; last.end = Date.now(); if (me.onArrive) me.onArrive(me.before.length > 0); }, () => {});   // a view still on its way: the card waits on the ground
  me.giveUp = setTimeout(() => { if (cur === me) done(); }, dur + 4000);   // a play the server refused: the card lets go
  return true;
}

// A card is still on its way to `cr`: the units the crossroad shows meanwhile (what it had), else null.
export function inFlight(cr) { return cur && cur.cr === cr && !cur.arrived ? cur.before : null; }
// When the flight to `cr` touched down (Date.now() ms), for the board's landing there; null when none came lately.
export function flightEnd(cr) {
  return last && last.cr === cr && Date.now() - last.end < 3000 ? last.end : null;
}
// The board drew the piece the flight brought, landing: the layer goes in this frame.
export function landed(cr) { if (cur && cur.cr === cr && cur.arrived) done(); }
export function flying() { return cur ? cur.cr : null; }
function done() { if (!cur) return; clearTimeout(cur.giveUp); cur.el.remove(); cur = null; }
