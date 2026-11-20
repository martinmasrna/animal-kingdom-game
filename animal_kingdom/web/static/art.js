// Card art: /static/art/<id>.webp (placeholder paintings from the design sandbox, cards/; web/art_webp.sh makes the WebP from the JPEG).
// CROP places a card's round board portrait: centre x, centre y, diameter, as fractions of the art's width, height, width.
export const CROP = {
  wisp_10: [.5, .5, .95],
  wisp_9: [.5, .5, .95],
  wisp_8: [.5, .5, .95],
  wisp_7: [.5, .5, .95],
  wisp_6: [.5, .5, .95],
  wisp_5: [.5, .5, .95],
  wisp_4: [.5, .5, .95],
  wisp_3: [.5, .5, .95],
  wisp_2: [.5, .5, .95],
  wisp_1: [.5, .5, .95],
  
};
// STRIP places the art in a thin strip (the Collection's deck tile and deck list): the point (x, y as fractions of the art)
// that lands on the strip's focus, and a zoom over the strip's own width.
export const STRIP = {
  
  
};
// FULL places the painting in the full card's window, which shows 61% of its height between the name bar and the rules panel:
// the height, as a fraction of the art, the window centres on (its top edge is that minus .305). Set by hand: the whole animal
// where it fits, otherwise its head near the top with a little room and the legs cut. A card without an entry centres on its
// board portrait (CROP), which Martin preferred for a few (Eagle, Ember, Hippopotamus, ...).
export const FULL = {
  
  
};
export const hasArt = id => id in CROP;
export const artUrl = id => `/static/art/${id}.webp`;
// A long grid's art loads as its cards near view in `scroller` (data-art, from cardHTML's `lazy`), not all hundred at once.
let seen;
export const lazyArt = scroller => {
  seen?.disconnect();
  seen = new IntersectionObserver((es, o) => es.forEach(e => { if (!e.isIntersecting) return;
    e.target.style.backgroundImage = `url(${e.target.dataset.art})`; o.unobserve(e.target); }), { root: scroller, rootMargin: '600px 0px' });
  scroller.querySelectorAll('[data-art]').forEach(el => seen.observe(el));
};
// A strip's crop is sized from its box, so it is fitted again whenever the box changes (a phone's wider rows, a panel
// opening, a rotation): a crop sized for another width tiles across the strip. A strip leaving the page measures 0 and is let go.
let sized;
export const fitStrips = root => root.querySelectorAll('[data-strip]').forEach(el => (sized ||= new ResizeObserver(es => es.forEach(({ target: el }) => {
  const { offsetWidth: W, offsetHeight: H } = el; if (!W) { if (!el.isConnected) sized.unobserve(el); return; }
  for (const d of stripArt(el.dataset.strip, W, H, +el.dataset.ax).split(';')) { const i = d.indexOf(':'); if (i > 0) el.style.setProperty(d.slice(0, i), d.slice(i + 1)); }
}))).observe(el));
export const stripArt = (id, W, H, ax) => {
  if (!hasArt(id)) return '';                    // not painted yet: the strip shows its plain ground
  if (!STRIP[id]) return `background-image:url(${artUrl(id)})`;
  const [x, y, z] = STRIP[id], w = W * z, h = w * 1.5, fit = (v, lo) => Math.min(0, Math.max(lo, v));
  return `background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${fit(ax * W - x * w, W - w)}px ${fit(H / 2 - y * h, H - h)}px`;
};
