// The menus' shared controls (their look is menu.css): the screen's own dropdown, never the browser's menu.

// A slab showing the current choice; its list opens under it. opts: [[value, label], ...].
export const dd = (key, cur, opts) => { const c = opts.find(([v]) => v === cur) || opts[0];
  return `<div class="dd" data-dd="${key}"><button class="sel">${c[1]}</button><div class="ddm">${opts.map(([v, l]) => `<div class="ddo${v === cur ? ' on' : ''}" data-k="${key}" data-v="${v}">${l}</div>`).join('')}</div></div>`; };

// Every dropdown under root: its button opens it (closing any other), a row calls pick(key, value).
// The button is as wide as its widest choice, measured in the list's own type, so the open list fits under it and the
// button keeps its width whichever choice it shows (Martin, 2026-10-26: 'Every rarity' was cut off under 'Rare').
const ruler = document.createElement('canvas').getContext('2d');
function fitChoices(d) {
  const sel = d.querySelector('.sel'), o = d.querySelector('.ddo'); if (!o) return;
  const so = getComputedStyle(sel), oo = getComputedStyle(o); ruler.font = oo.font;
  const widest = Math.max(...[...d.querySelectorAll('.ddo')].map(e => ruler.measureText(e.textContent).width));
  const need = Math.ceil(widest + parseFloat(oo.paddingLeft) + parseFloat(oo.paddingRight) + parseFloat(so.paddingRight) - parseFloat(oo.paddingRight));
  if (sel.offsetWidth < need) sel.style.minWidth = need + 'px';
}
export function wireDd(root, pick) {
  root.querySelectorAll('.dd').forEach(d => {
    fitChoices(d);
    d.querySelector('.sel').onclick = ev => { ev.stopPropagation(); const was = d.classList.contains('open'); closeAll(); d.classList.toggle('open', !was);
      // The list hangs under its slab, or over it when the window has more room above; a list taller than the room
      // (the bot decks, nineteen of them since 2026-10-20) scrolls inside it instead of running off the screen.
      d.classList.remove('up'); const m = d.querySelector('.ddm'); m.style.maxHeight = '';
      if (!was) { const r = d.getBoundingClientRect(), below = innerHeight - r.bottom - 8, above = r.top - 8, up = m.scrollHeight > below && above > below;
        d.classList.toggle('up', up); if (m.scrollHeight > (up ? above : below)) m.style.maxHeight = Math.max(120, up ? above : below) + 'px'; } };
    d.querySelectorAll('.ddo').forEach(o => o.onclick = () => pick(d.dataset.dd, o.dataset.v));
  });
}
const closeAll = () => { const open = document.querySelectorAll('.dd.open'); open.forEach(d => d.classList.remove('open', 'up')); return open.length; };
// A click elsewhere closes an open dropdown; so does Escape, which then goes no further (the screen's own Escape waits for the next press).
addEventListener('click', closeAll);
addEventListener('keydown', e => { if (e.key === 'Escape' && closeAll()) e.stopImmediatePropagation(); }, true);

// Touch has no hover or right-click: pressing and holding does what they do (read a card large); the tap that ends the
// hold does nothing else. fn(el) starts the reading, done(el) ends it (for a reading shown only while held).
// A held finger always wobbles a little: only a real move (a scroll, a drag) cancels a hold.
// A finger holds through touch events (a pointer's would be cancelled by the first wobble in a scrolling list); a pen sends no
// touch events (a Surface; feedback 2026-10-01), so it holds through pointer events. A mouse keeps hover and right-click.
export const moved = (e, x0, y0) => { const p = e.touches ? e.touches[0] : e; return Math.hypot(p.clientX - x0, p.clientY - y0) > 10; };
export function holdEvents(el, start, cancel, end) {
  let x0 = 0, y0 = 0;
  el.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; start(e); }, { passive: true });
  el.addEventListener('touchmove', e => { if (moved(e, x0, y0)) cancel(); }, { passive: true });
  el.addEventListener('touchend', end); el.addEventListener('touchcancel', end);
  el.addEventListener('pointerdown', e => { if (e.pointerType === 'pen') { x0 = e.clientX; y0 = e.clientY; start(e); } });
  el.addEventListener('pointermove', e => { if (e.pointerType === 'pen' && moved(e, x0, y0)) cancel(); });
  el.addEventListener('pointerup', e => { if (e.pointerType === 'pen') end(e); }); el.addEventListener('pointercancel', e => { if (e.pointerType === 'pen') end(e); });
}
export function onHold(el, fn, done) {
  let t = null, held = false;
  holdEvents(el, () => { held = false; clearTimeout(t); t = setTimeout(() => { held = true; fn(el); }, 420); }, () => clearTimeout(t),
    e => { clearTimeout(t); if (held) { if (e && e.cancelable) e.preventDefault(); if (done) done(el); } });   // no click follows a hold
  el.addEventListener('click', e => { if (held) { held = false; e.stopImmediatePropagation(); e.preventDefault(); } }, true);
  el.addEventListener('contextmenu', e => e.preventDefault());
}
