// The card in your hand's grip (Martin, 2026-11-13: play as Hearthstone does, drag and drop, or click to pick up and click
// to place): picked up, the full card leaves the hand and hangs over the pointer, a little above it so the crossroad under
// the pointer stays in sight, where flight.js turns it into the piece. It follows with a short lag and tilts in 3D with its
// speed, leaning the way it is carried, as a held card does in Hearthstone. Placed, it hands its pose to fly() in the same
// frame; let go, it goes back to its place in the hand.
import { fitNames } from './card.js';
import { LIFT, CARD_END, PIC_UP } from './flight.js';

const HELD = 1;                   // held, its size over its place (Hearthstone shrinks a lifted card to about its minion's size)
const REST_X = 9;                 // and tipped back a little, even still, so it reads as a card in the hand's grip, not a tile
let C = null;                     // { el, fc, w, h, k, x, y, s, rx, ry, rz, raf, t }
let px = innerWidth / 2, py = innerHeight / 2;   // the pointer, always known
addEventListener('pointermove', e => { px = e.clientX; py = e.clientY; }, { passive: true, capture: true });

const clamp = (v, m) => Math.max(-m, Math.min(m, v));
const pose = c => `translate(${c.x}px,${c.y}px) perspective(${900 * c.k}px) rotateX(${c.rx}deg) rotateY(${c.ry}deg) rotateZ(${c.rz}deg) scale(${c.s})`;

// Pick up the hand's card `from` (its .card element), shown as `html` (the full card).
// `geo`: another card form's measures (fly()'s), so its piece hangs on the pointer.
export function carry(from, html, geo = null) {
  drop();
  const stage = document.getElementById('stage'), k = stage.getBoundingClientRect().width / stage.offsetWidth;
  const r = from.getBoundingClientRect(), w = from.offsetWidth, h = from.offsetHeight;
  const el = document.createElement('div'); el.className = 'flight carry';
  const fc = document.createElement('div'); fc.className = 'fcard';
  fc.style.cssText = `width:${w}px;height:${h}px;left:${-w / 2}px;top:${-h / 2}px`;
  fc.innerHTML = html; el.appendChild(fc); document.body.appendChild(el);
  const card = fc.firstElementChild; card.style.cssText += `;--w:${w}px;width:${w}px;height:${h}px;`;
  fitNames(fc);
  C = { geo, el, fc, w, h, k, x: r.left + r.width / 2, y: r.top + r.height / 2, s: r.width / w, rx: 0, ry: 0, rz: 0, t: performance.now(), over: null };
  document.documentElement.classList.add('carrying');
  fc.style.transform = pose(C);
  const me = C;
  const tick = now => {
    if (C !== me) return;
    const dt = Math.min(50, now - me.t) || 16; me.t = now;
    // where it hangs: its painting on the pointer (Martin, 2026-11-13: a card hung above the pointer sat over the next
    // crossroad, "a disconnect between where my cursor is and where the card is"), so what it covers is where it goes
    const end = me.geo ? me.geo.end : CARD_END, up = me.geo ? me.geo.up : PIC_UP, o = me.over;
    // over a tile it may take (carryOver), the card has become its creature standing there: settled on the tile, upright
    const ts = o ? o.s : HELD * end * k / w, tx = o ? o.x : px, ty = o ? o.y : py - LIFT * k + up * HELD * end * k;
    const f = 1 - Math.exp(-dt / 26), x = me.x + (tx - me.x) * f, y = me.y + (ty - me.y) * f;
    const vx = (x - me.x) / dt, vy = (y - me.y) / dt;   // px per ms
    me.x = x; me.y = y; me.s += (ts - me.s) * (1 - Math.exp(-dt / 40));
    const g = 1 - Math.exp(-dt / 60);   // the tilt eases toward what the speed asks, so it rocks rather than snaps
    if (o) { me.rx -= me.rx * g; me.ry -= me.ry * g; me.rz -= me.rz * g; }
    else { me.ry += (clamp(vx * 14, 26) - me.ry) * g; me.rx += (REST_X + clamp(-vy * 14, 26) - me.rx) * g; me.rz += (clamp(vx * 4, 8) - me.rz) * g; }
    fc.style.transform = pose(me);
    me.raf = requestAnimationFrame(tick);
  };
  me.raf = requestAnimationFrame(tick);
}

export const carrying = () => !!C;

// The square board's held card over a tile it may take becomes the creature standing on it: `fig` is where the board's own
// standing figure would be (its screen rect), and the card goes to the pose that puts its creature there while everything
// else on it fades (mana.css .flight.over); null turns it back into the card on the pointer. The card's creature is
// --a wide for its 1.02 card widths of height, its centre .04 widths above the card's.
export function carryOver(fig) {
  if (!C) return;
  C.over = fig ? { s: fig.height / (1.02 * C.w), x: fig.left + fig.width / 2, y: fig.top + fig.height / 2 + .04 * fig.height / 1.02 } : null;
  C.el.classList.toggle('over', !!fig);
}

// Its pose now, and it lets go of it (fly() takes the card on from here, in the same frame); null when nothing is held.
export function release() {
  if (!C) return null;
  const { x, y, s, rx, ry, rz, w, h, over } = C; cancelAnimationFrame(C.raf); C.el.remove(); C = null; document.documentElement.classList.remove('carrying');
  return { x, y, s, rx, ry, rz, w, h, over: !!over };
}

// Put it back: it flies to `to` (the card's place in the hand, a .card element) and `done` runs when it is there.
export function drop(to = null, done = null) {
  if (!C) { if (done) done(); return; }
  const c = C; C = null; cancelAnimationFrame(c.raf); document.documentElement.classList.remove('carrying'); c.el.classList.remove('over');
  if (!to) { c.el.remove(); if (done) done(); return; }
  const r = to.getBoundingClientRect(), end = { ...c, x: r.left + r.width / 2, y: r.top + r.height / 2, s: r.width / c.w, rx: 0, ry: 0, rz: 0 };
  c.fc.animate([{ transform: pose(c) }, { transform: pose(end) }], { duration: 220 / (window.AK_SPEED || 1), easing: 'cubic-bezier(.3,.7,.4,1)', fill: 'forwards' })
    .finished.then(() => { c.el.remove(); if (done) done(); }, () => { c.el.remove(); if (done) done(); });
}
