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
// `token`: the piece is held instead of the card (Martin, 2026-11-13: does the card turning into the token as it is picked
// up read better than a card over a ghost of the piece? ?held=token), centred on the pointer, popping out of the card.
export const HELD_TOKEN = new URLSearchParams(globalThis.location?.search || '').get('held') === 'token';
export function carry(from, html, token = false) {
  drop();
  const stage = document.getElementById('stage'), k = stage.getBoundingClientRect().width / stage.offsetWidth;
  const r = from.getBoundingClientRect(), w = token ? 134 : from.offsetWidth, h = token ? 134 : from.offsetHeight;
  const el = document.createElement('div'); el.className = 'flight carry';
  const fc = document.createElement('div'); fc.className = 'fcard';
  fc.style.cssText = `width:${w}px;height:${h}px;left:${-w / 2}px;top:${-h / 2}px`;
  fc.innerHTML = html; el.appendChild(fc); document.body.appendChild(el);
  const card = fc.firstElementChild;
  if (token) { el.classList.add('token'); card.animate([{ transform: 'scale(.55)', filter: 'brightness(1.8)' }, { transform: 'scale(1.08)', filter: 'brightness(1.15)', offset: .6 }, { transform: 'none', filter: 'none' }], { duration: 200, easing: 'cubic-bezier(.3,.7,.4,1)' }); }
  else { card.style.cssText += `;--w:${w}px;width:${w}px;height:${h}px;`; fitNames(fc); }
  C = { el, fc, w, h, k, token, x: r.left + r.width / 2, y: r.top + (token ? r.height * .35 : r.height / 2), s: token ? k * .8 : r.width / w, rx: 0, ry: 0, rz: 0, t: performance.now() };
  fc.style.transform = pose(C);
  const me = C;
  const tick = now => {
    if (C !== me) return;
    const dt = Math.min(50, now - me.t) || 16; me.t = now;
    // where it hangs: its painting on the pointer (Martin, 2026-11-13: a card hung above the pointer sat over the next
    // crossroad, "a disconnect between where my cursor is and where the card is"), so what it covers is where it goes
    const ts = me.token ? k : HELD * CARD_END * k / w, tx = px, ty = py - LIFT * k + (me.token ? 0 : PIC_UP * HELD * CARD_END * k);
    const f = 1 - Math.exp(-dt / 26), x = me.x + (tx - me.x) * f, y = me.y + (ty - me.y) * f;
    const vx = (x - me.x) / dt, vy = (y - me.y) / dt;   // px per ms
    me.x = x; me.y = y; me.s += (ts - me.s) * (1 - Math.exp(-dt / 40));
    const g = 1 - Math.exp(-dt / 60);   // the tilt eases toward what the speed asks, so it rocks rather than snaps
    me.ry += (clamp(vx * 14, 26) - me.ry) * g; me.rx += ((me.token ? 0 : REST_X) + clamp(-vy * 14, 26) - me.rx) * g; me.rz += (clamp(vx * 4, 8) - me.rz) * g;
    fc.style.transform = pose(me);
    me.raf = requestAnimationFrame(tick);
  };
  me.raf = requestAnimationFrame(tick);
}

export const carrying = () => !!C;

// Its pose now, and it lets go of it (fly() takes the card on from here, in the same frame); null when nothing is held.
export function release() {
  if (!C) return null;
  const { x, y, s, rx, ry, rz, w, h, token } = C; cancelAnimationFrame(C.raf); C.el.remove(); C = null;
  return { x, y, s, rx, ry, rz, w, h, token };
}

// Put it back: it flies to `to` (the card's place in the hand, a .card element) and `done` runs when it is there.
export function drop(to = null, done = null) {
  if (!C) { if (done) done(); return; }
  const c = C; C = null; cancelAnimationFrame(c.raf);
  if (!to) { c.el.remove(); if (done) done(); return; }
  const r = to.getBoundingClientRect(), end = { ...c, x: r.left + r.width / 2, y: r.top + r.height / 2, s: r.width / c.w, rx: 0, ry: 0, rz: 0 };
  c.fc.animate([{ transform: pose(c) }, { transform: pose(end) }], { duration: 220 / (window.AK_SPEED || 1), easing: 'cubic-bezier(.3,.7,.4,1)', fill: 'forwards' })
    .finished.then(() => { c.el.remove(); if (done) done(); }, () => { c.el.remove(); if (done) done(); });
}
