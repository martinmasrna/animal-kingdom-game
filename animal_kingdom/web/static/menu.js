// The menus' shared controls (their look is menu.css): the screen's own dropdown, never the browser's menu.

// A slab showing the current choice; its list opens under it. opts: [[value, label], ...].
export const dd = (key, cur, opts) => { const c = opts.find(([v]) => v === cur) || opts[0];
  return `<div class="dd" data-dd="${key}"><button class="sel">${c[1]}</button><div class="ddm">${opts.map(([v, l]) => `<div class="ddo${v === cur ? ' on' : ''}" data-k="${key}" data-v="${v}">${l}</div>`).join('')}</div></div>`; };

// Every dropdown under root: its button opens it (closing any other), a row calls pick(key, value).
export function wireDd(root, pick) {
  root.querySelectorAll('.dd').forEach(d => {
    d.querySelector('.sel').onclick = ev => { ev.stopPropagation(); const was = d.classList.contains('open'); closeAll(); d.classList.toggle('open', !was);
      // The list hangs under its slab, or over it when the window has no room below.
      d.classList.remove('up'); if (!was && d.querySelector('.ddm').getBoundingClientRect().bottom > innerHeight - 8) d.classList.add('up'); };
    d.querySelectorAll('.ddo').forEach(o => o.onclick = () => pick(d.dataset.dd, o.dataset.v));
  });
}
const closeAll = () => { const open = document.querySelectorAll('.dd.open'); open.forEach(d => d.classList.remove('open', 'up')); return open.length; };
// A click elsewhere closes an open dropdown; so does Escape, which then goes no further (the screen's own Escape waits for the next press).
addEventListener('click', closeAll);
addEventListener('keydown', e => { if (e.key === 'Escape' && closeAll()) e.stopImmediatePropagation(); }, true);

// Touch has no hover or right-click: pressing and holding does what they do (read a card large); the tap that ends the
// hold does nothing else. fn(el) starts the reading, done(el) ends it (for a reading shown only while held).
export function onHold(el, fn, done) {
  let t = null, held = false;
  el.addEventListener('touchstart', () => { held = false; clearTimeout(t); t = setTimeout(() => { held = true; fn(el); }, 420); }, { passive: true });
  const end = e => { clearTimeout(t); if (held) { if (e.cancelable) e.preventDefault(); if (done) done(el); } };   // no click follows a hold
  el.addEventListener('touchend', end); el.addEventListener('touchcancel', end); el.addEventListener('touchmove', () => clearTimeout(t), { passive: true });
  el.addEventListener('click', e => { if (held) { held = false; e.stopImmediatePropagation(); e.preventDefault(); } }, true);
  el.addEventListener('contextmenu', e => e.preventDefault());
}
