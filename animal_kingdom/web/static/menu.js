// The menus' shared controls (their look is menu.css): the screen's own dropdown, never the browser's menu.

// A slab showing the current choice; its list opens under it. opts: [[value, label], ...].
export const dd = (key, cur, opts) => { const c = opts.find(([v]) => v === cur) || opts[0];
  return `<div class="dd" data-dd="${key}"><button class="sel">${c[1]}</button><div class="ddm">${opts.map(([v, l]) => `<div class="ddo${v === cur ? ' on' : ''}" data-k="${key}" data-v="${v}">${l}</div>`).join('')}</div></div>`; };

// Every dropdown under root: its button opens it (closing any other), a row calls pick(key, value).
export function wireDd(root, pick) {
  root.querySelectorAll('.dd').forEach(d => {
    d.querySelector('.sel').onclick = ev => { ev.stopPropagation(); const was = d.classList.contains('open'); closeAll(); d.classList.toggle('open', !was); };
    d.querySelectorAll('.ddo').forEach(o => o.onclick = () => pick(d.dataset.dd, o.dataset.v));
  });
}
const closeAll = () => { const open = document.querySelectorAll('.dd.open'); open.forEach(d => d.classList.remove('open')); return open.length; };
// A click elsewhere closes an open dropdown; so does Escape, which then goes no further (the screen's own Escape waits for the next press).
addEventListener('click', closeAll);
addEventListener('keydown', e => { if (e.key === 'Escape' && closeAll()) e.stopImmediatePropagation(); }, true);
