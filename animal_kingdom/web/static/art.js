// Card art: /static/art/<id>.webp (placeholder paintings from the design sandbox, cards/; web/art_webp.sh makes the WebP from the JPEG).
// CROP places a card's round board portrait: centre x, centre y, diameter, as fractions of the art's width, height, width.
export const CROP = {
  zebra: [.62, .33, .7],
  dart_frog: [.5, .4, .8],
  anteater: [.65, .5, .66],
  macaw: [.66, .3, .62],
  capybara: [.62, .45, .7],
  tarsier: [.57, .33, .6],
  meerkat: [.56, .24, .6],
  leopard: [.62, .3, .7],
  baboon: [.6, .42, .8],
  giraffe: [.62, .22, .55],
  tortoise: [.55, .45, .75],
  wildebeest: [.6, .5, .65],
  gazelle: [.64, .37, .7],
  dung_beetle: [.48, .55, .75],
  lion: [.7, .36, .55], lynx: [.52, .30, .62], house_cat: [.58, .36, .62], tiger: [.6, .5, .66], cougar: [.72, .36, .6],
  black_bear: [.34, .24, .66], caracal: [.42, .26, .6], rhinoceros: [.52, .38, .74], elephant: [.57, .27, .74],
  grizzly_bear: [.56, .4, .7], polar_bear: [.48, .36, .66], oxpecker: [.55, .35, .6], vulture: [.62, .45, .7], cape_buffalo: [.5, .4, .7],
  methuselah: [.56, .38, .8], jaguar: [.66, .42, .55], andean_condor: [.55, .36, .88],
  bat: [.45, .3, .7], black_panther: [.66, .42, .5], borealis: [.62, .3, .66], bulwark: [.5, .45, .9],
  chameleon: [.55, .4, .8], cheetah: [.7, .42, .6], falcon: [.66, .5, .6], gale: [.56, .45, .9], gray_wolf: [.72, .52, .6],
  hippopotamus: [.62, .3, .72], hornet: [.58, .42, .8], jerboa: [.65, .32, .65], king_theron: [.6, .3, .62],
  lemming: [.65, .36, .7], mouse: [.5, .33, .55], pestis: [.6, .38, .8], prince_leo: [.64, .33, .66],
  princess_lea: [.42, .36, .66], queen_adira: [.6, .29, .62], rat: [.68, .48, .62], serval: [.64, .6, .7],
  sirocco: [.45, .52, .75], skunk: [.42, .45, .75], sloth: [.45, .4, .75], snow_leopard: [.55, .34, .8],
  squirrel: [.62, .4, .7], verminus: [.6, .38, .8], worker_ant: [.55, .38, .75],
  eagle: [.56, .42, .62], owl: [.57, .25, .55], raven: [.64, .44, .7], goliath: [.62, .56, .62], rattlesnake: [.52, .36, .55],
  viper: [.65, .38, .6], stoop: [.55, .45, .7], magpie: [.6, .38, .75], black_mamba: [.52, .42, .75], taipan: [.45, .4, .8],
  queen_bee: [.55, .42, .75], guard_hornet: [.58, .42, .8], soldier_ant: [.55, .38, .75], worker_wasp: [.6, .38, .75], worker_bee: [.52, .42, .8],
  nurse_bee: [.6, .5, .8], nurse_bumblebee: [.5, .45, .8], termite_king: [.55, .5, .8], crocodile: [.68, .45, .62], honey_badger: [.6, .48, .8], termite_queen: [.45, .45, .85], naked_mole_rat: [.66, .5, .6],
  cairn: [.66, .44, .66], chipmunk: [.6, .45, .8], gopher: [.52, .38, .8], groundhog: [.55, .36, .65], hamster: [.52, .42, .72], hedgehog: [.5, .45, .8], muskrat: [.56, .42, .86],
  armadillo: [.72, .38, .6], chinchilla: [.68, .38, .7], flying_squirrel: [.62, .5, .7], porcupine: [.35, .48, .62], fathom: [.5, .42, .8],
  greywhisker: [.5, .33, .65], rat_king: [.52, .35, .8], scrooge: [.62, .45, .62],
  queen_honoria: [.6, .38, .7], queen_marabunta: [.6, .45, .75], vesper: [.6, .42, .72], falstaff: [.52, .37, .95],
  eon: [.6, .33, .7], ember: [.55, .3, .75], aurum: [.52, .5, .85], omen: [.58, .44, .82], anaconda: [.49, .6, .62], egg_eater: [.68, .27, .6], snake_egg: [.55, .46, .62], bird_egg: [.52, .42, .82],
  dire_wolf: [.55, .33, .62], dingo: [.7, .27, .6], fox: [.62, .42, .7], african_wild_dog: [.5, .4, .6], dog: [.66, .3, .6],
  pup: [.55, .36, .72], outrider: [.62, .36, .75], red_wolf: [.66, .36, .66], hyena: [.62, .45, .6], bush_dog: [.64, .33, .6],
  lobo: [.55, .42, .75], raksha: [.64, .33, .6], clarion: [.6, .22, .7], alpha: [.56, .36, .8], poppy: [.55, .36, .72], rusty: [.45, .36, .72],
};
// STRIP places the art in a thin strip (the Collection's deck tile and deck list): the point (x, y as fractions of the art)
// that lands on the strip's focus, and a zoom over the strip's own width.
export const STRIP = {
  zebra: [.72, .26, 1],
  dart_frog: [.55, .38, 1],
  anteater: [.7, .48, 1],
  macaw: [.7, .28, 1],
  capybara: [.66, .43, 1],
  tarsier: [.62, .3, 1],
  meerkat: [.62, .14, 1.2],
  leopard: [.7, .28, 1],
  baboon: [.7, .3, 1],
  giraffe: [.72, .12, 1.3],
  tortoise: [.6, .45, 1],
  wildebeest: [.75, .55, 1.1],
  gazelle: [.78, .4, 1.2],
  dung_beetle: [.4, .5, 1.2],
  prince_leo: [.72, .3, 1.2], princess_lea: [.34, .34, 1.2], king_theron: [.6, .28, 1], queen_adira: [.62, .22, 1.2], jaguar: [.7, .36, 1], serval: [.66, .48, 1.3],
  snow_leopard: [.66, .38, 1], black_panther: [.7, .43, 1], lion: [.72, .36, 1.2], lynx: [.52, .24, 1.3], caracal: [.47, .28, 1.5], tiger: [.82, .54, 1],
  cougar: [.73, .38, 1.1], house_cat: [.43, .37, 1.5], eon: [.62, .29, 1], goliath: [.62, .55, 1.2], ember: [.75, .17, 1.5], aurum: [.6, .45, 1.2], anaconda: [.5, .55, 1.2], egg_eater: [.72, .26, 1.3], snake_egg: [.58, .45, 1.3], bird_egg: [.6, .33, 1.2],
  rattlesnake: [.53, .35, 1.3], omen: [.72, .3, 1.7], stoop: [.58, .47, 1.8], eagle: [.63, .43, 1.8], owl: [.6, .24, 1.2], taipan: [.6, .3, 1],
  viper: [.63, .35, 1], magpie: [.73, .34, 1.7], black_mamba: [.58, .3, 1], raven: [.77, .47, 1.7], queen_marabunta: [.8, .53, 1.7], vesper: [.66, .47, 1.1],
  queen_honoria: [.62, .32, 1.2], falstaff: [.6, .33, 1.1], nurse_bee: [.58, .45, 1.2], nurse_bumblebee: [.65, .4, 1.1], termite_king: [.73, .47, 1], crocodile: [.75, .45, 1], honey_badger: [.72, .42, 1], termite_queen: [.45, .37, 1], naked_mole_rat: [.76, .48, 1],
  queen_bee: [.65, .42, 1.3], guard_hornet: [.43, .4, 1], soldier_ant: [.55, .34, 1.3], worker_ant: [.52, .32, 1], worker_wasp: [.62, .4, 1.1], worker_bee: [.6, .42, 1.2],
  methuselah: [.62, .33, 1], borealis: [.83, .17, 1], bulwark: [.6, .33, 1.1], cairn: [.7, .42, 1.1], polar_bear: [.52, .32, 1.3], rhinoceros: [.68, .42, 1],
  hippopotamus: [.62, .24, 1], andean_condor: [.6, .25, 1.6], elephant: [.57, .26, 1], grizzly_bear: [.72, .3, 1], oxpecker: [.62, .25, 1.3], vulture: [.72, .5, 1.2], black_bear: [.38, .28, 1.5],
  sloth: [.5, .38, 1.2], cape_buffalo: [.52, .38, 1], fathom: [.48, .33, 1], greywhisker: [.5, .29, 1], rat_king: [.52, .17, 1.2], scrooge: [.73, .4, 1.2],
  flying_squirrel: [.65, .42, 1.1], porcupine: [.23, .5, 1.5], chinchilla: [.75, .4, 1], armadillo: [.83, .42, 1.3], squirrel: [.62, .31, 1.1], chipmunk: [.8, .47, 1.3],
  hedgehog: [.47, .47, 1], hamster: [.52, .38, 1], muskrat: [.4, .38, 1.3], groundhog: [.58, .3, 1], gopher: [.62, .37, 1], verminus: [.7, .22, 1],
  pestis: [.66, .48, 1], sirocco: [.47, .62, 1.5], gale: [.72, .56, 1.7], jerboa: [.73, .38, 1.3], hornet: [.5, .45, 1], chameleon: [.62, .28, 1.3],
  skunk: [.53, .52, 1.7], lemming: [.82, .38, 1.4], cheetah: [.87, .4, 1.3], rat: [.8, .48, 1], falcon: [.8, .6, 1.7], bat: [.53, .44, 1.3],
  mouse: [.47, .33, 1], lobo: [.55, .38, 1.2], raksha: [.63, .38, 1.1], clarion: [.63, .16, 1.1], bush_dog: [.63, .25, 1.1], red_wolf: [.7, .32, 1.4],
  gray_wolf: [.8, .5, 1], fox: [.7, .4, 1.3], african_wild_dog: [.55, .3, 1.2], dingo: [.73, .25, 1.1], dog: [.67, .34, 1], alpha: [.6, .19, 1.2],
  hyena: [.72, .45, 1.2], outrider: [.77, .31, 1.3], dire_wolf: [.56, .36, 1.3], pup: [.57, .27, 1.2], poppy: [.5, .32, 1], rusty: [.5, .32, 1],
};
// FULL places the painting in the full card's window, which shows 61% of its height between the name bar and the rules panel:
// the height, as a fraction of the art, the window centres on (its top edge is that minus .305). Set by hand: the whole animal
// where it fits, otherwise its head near the top with a little room and the legs cut. A card without an entry centres on its
// board portrait (CROP), which Martin preferred for a few (Eagle, Ember, Hippopotamus, ...).
export const FULL = {
  zebra: .35,
  dart_frog: .4,
  anteater: .45,
  macaw: .3,
  capybara: .45,
  tarsier: .33,
  meerkat: .25,
  leopard: .3,
  baboon: .45,
  giraffe: .42,
  tortoise: .45,
  wildebeest: .45,
  gazelle: .5,
  oxpecker: .4, vulture: .5,
  dung_beetle: .5,
  african_wild_dog: .45, alpha: .355, anaconda: .485, andean_condor: .335, armadillo: .435, aurum: .5, bat: .305,
  bird_egg: .445, black_bear: .445, black_mamba: .445, black_panther: .455, borealis: .365, bulwark: .45, bush_dog: .475,
  cairn: .42, cape_buffalo: .4, caracal: .345, chameleon: .38, cheetah: .415, chinchilla: .365, chipmunk: .405,
  clarion: .355, cougar: .455, dingo: .375, dire_wolf: .385, dog: .435, egg_eater: .42, elephant: .365, eon: .375,
  falcon: .385, falstaff: .36, fathom: .405, flying_squirrel: .385, fox: .45, gale: .46, goliath: .45, gopher: .475,
  gray_wolf: .5, greywhisker: .415, grizzly_bear: .425, groundhog: .385, guard_hornet: .465, hamster: .455, hedgehog: .435,
  hornet: .425, house_cat: .435, hyena: .45, jaguar: .455, king_theron: .305, lemming: .445, lion: .45, lobo: .45,
  lynx: .395, magpie: .375, methuselah: .405, mouse: .455, muskrat: .48, nurse_bumblebee: .445, omen: .48, outrider: .365,
  owl: .385, pestis: .405, poppy: .355, porcupine: .435, prince_leo: .365, princess_lea: .395, pup: .365, queen_adira: .375,
  queen_bee: .425, queen_marabunta: .455, raksha: .425, rat: .475, rat_king: .365, rattlesnake: .555, raven: .405,
  red_wolf: .445, rhinoceros: .395, rusty: .345, scrooge: .485, serval: .5, sirocco: .415, skunk: .395, sloth: .4,
  snake_egg: .445, snow_leopard: .385, soldier_ant: .465, squirrel: .455, taipan: .405, termite_king: .485, crocodile: .45, honey_badger: .5,
  termite_queen: .455, naked_mole_rat: .5, tiger: .505, verminus: .345, vesper: .425, viper: .415, worker_ant: .465, worker_bee: .355,
  worker_wasp: .375,
};
// Cards painted as another card: the tutorial's copies of the cards it was written with (the live cards changed since).
const ALIAS = { tutorial_cape_buffalo: 'cape_buffalo', tutorial_dire_wolf: 'dire_wolf', tutorial_lynx: 'lynx', tutorial_chipmunk: 'chipmunk' };
for (const [id, art] of Object.entries(ALIAS)) for (const T of [CROP, STRIP, FULL]) if (art in T) T[id] = T[art];
// Cards whose painting shows an animal the card no longer is (the workbench changed its species): unpainted until
// repainted, so they never wear another animal's art. Scrooge was painted a hamster (now a chipmunk), Gale an albatross
// (now a falcon).
for (const id of ['scrooge', 'gale']) for (const T of [CROP, STRIP, FULL]) delete T[id];
export const hasArt = id => id in CROP;
export const artUrl = id => `/static/art/${ALIAS[id] || id}.webp`;
// A long grid's art loads as its cards near view in `scroller` (data-art, from cardHTML's `lazy`), not all hundred at once.
let seen;
export const lazyArt = scroller => {
  seen?.disconnect();
  seen = new IntersectionObserver((es, o) => es.forEach(e => { if (!e.isIntersecting) return;
    e.target.style.backgroundImage = `url(${e.target.dataset.art})`; o.unobserve(e.target); }), { root: scroller, rootMargin: '600px 0px' });
  scroller.querySelectorAll('[data-art]').forEach(el => seen.observe(el));
};
export const fitStrips = root => root.querySelectorAll('[data-strip]').forEach(el => {
  const { offsetWidth: W, offsetHeight: H } = el; if (!W) return;
  el.style.cssText += ';' + stripArt(el.dataset.strip, W, H, +el.dataset.ax);
});
export const stripArt = (id, W, H, ax) => {
  if (!hasArt(id)) return '';                    // not painted yet: the strip shows its plain ground
  if (!STRIP[id]) return `background-image:url(${artUrl(id)})`;
  const [x, y, z] = STRIP[id], w = W * z, h = w * 1.5, fit = (v, lo) => Math.min(0, Math.max(lo, v));
  return `background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${fit(ax * W - x * w, W - w)}px ${fit(H / 2 - y * h, H - h)}px`;
};
