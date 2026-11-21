// Food in motion (Martin, 2026-11-21: "nice little animations ... the food can be represented by little orange glowing
// dots for now"), as the old game flew its fruit: one dot per food, leaving 35 ms apart and taking 0.7 s on a low arc, the
// den's count ticking up as each lands. Food gained flies into its side's den from where it came: a region's income from
// the dots of the regions held, a card's food from the animals whose doing it is, a leader's from the leader on the rail.
// Food a raid destroys bursts out of the den and fades. The dots live in a layer over the whole screen, placed from where
// each thing is drawn (the board is tilted; the leaders are off it), so they need no geometry of their own.

export const FLY = 0.7, GAP = 0.035;   // seconds: one dot's flight, and between two leaving (timeline.js foodDur matches)

const centre = el => { const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2, h: r.height }; };
let layer = null;
const host = () => { if (!layer || !layer.isConnected) { layer = document.createElement('div'); layer.id = 'foodfx'; document.body.appendChild(layer); } return layer; };
const dot = (x, y, size) => { const d = document.createElement('i'); d.className = 'fdot fly';
  d.style.cssText = `left:${x - size / 2}px;top:${y - size / 2}px;width:${size}px;height:${size}px`; host().appendChild(d); return d; };

// The den's count shows `from` and steps one food at a time towards `to` as `times` (ms from now) come due.
function tick(den, from, to, times) {
  const b = den && den.querySelector('b'); if (!b) return;
  b.textContent = from;
  const dir = Math.sign(to - from);
  times.forEach((t, i) => setTimeout(() => { if (!b.isConnected) return; b.textContent = from + dir * (i + 1);
    den.classList.remove('fpulse'); void den.offsetWidth; den.classList.add('fpulse'); }, t));
  setTimeout(() => { if (b.isConnected) b.textContent = to; }, (times[times.length - 1] || 0) + 30);
}

// `step`: the timeline's food step ({ player, n, income, from }) or raid step ({ den, n }), sides already the viewer's
// (A at the bottom). `before`: the den's count before it. `sources(side)`: where a gain comes from, as elements with a share each.
export function playFood(step, before, sources) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || !step.n) return;
  const side = step.side, den = document.querySelector(`#board .mden.${side}`); if (!den) return;
  const to = centre(den.querySelector('.fdot') || den), size = Math.max(10, to.h * .8);   // into the den's own food dot, about its size
  if (step.kind === 'raid') {   // destroyed: the den jolts and flashes as it is hit, and the food bursts out, fading
    den.classList.remove('hit'); void den.offsetWidth; den.classList.add('hit');
    const times = [];
    for (let i = 0; i < step.n; i++) {
      const a = (i / step.n) * Math.PI * 2 + Math.random() * .6, r = to.h * (3 + Math.random() * 2.5), delay = i * GAP * 1000;
      const d = dot(to.x, to.y, size);
      d.animate([{ transform: 'translate(0,0) scale(1)', opacity: 1 }, { transform: `translate(${Math.cos(a) * r}px,${Math.sin(a) * r * .7}px) scale(.4)`, opacity: 0 }],
        { duration: 600, delay, easing: 'cubic-bezier(.2,.7,.4,1)', fill: 'both' }).finished.then(() => d.remove());
      times.push(delay);
    }
    tick(den, before, before - step.n, times);
    return;
  }
  const from = sources(side);
  if (!from.length) from.push({ el: den, n: step.n });
  const times = [];
  let k = 0;
  for (const s of from) {
    const p = centre(s.el);
    for (let j = 0; j < s.n; j++, k++) {
      const delay = k * GAP * 1000, dx = to.x - p.x + (k % 3 - 1) * size * .6, dy = to.y - p.y, lift = -Math.min(120, Math.hypot(dx, dy) * .35);
      const d = dot(p.x, p.y, size);
      d.animate([{ transform: 'translate(0,0) scale(.6)', opacity: 0 },
                 { transform: `translate(${dx * .5}px,${dy * .5 + lift}px) scale(1.1)`, opacity: 1, offset: .5 },
                 { transform: `translate(${dx}px,${dy}px) scale(.8)`, opacity: 1 }],
        { duration: FLY * 1000, delay, easing: 'cubic-bezier(.45,.05,.55,.95)', fill: 'both' }).finished.then(() => d.remove());
      times.push(delay + FLY * 1000);
    }
  }
  tick(den, before, before + step.n, times);
}
