// Card art: /static/art/<id>.jpg (placeholder paintings from the design sandbox, cards/).
// CROP places a card's round board portrait: centre x, centre y, diameter, as fractions of the art's width, height, width.
export const CROP = {
  lion: [.64, .28, .62], lynx: [.52, .30, .62], house_cat: [.58, .36, .62], tiger: [.6, .5, .66], cougar: [.72, .36, .6],
  black_bear: [.34, .24, .66], caracal: [.42, .26, .6], rhinoceros: [.52, .38, .74], elephant: [.64, .3, .74],
  grizzly_bear: [.56, .4, .7], polar_bear: [.48, .36, .66], oxpecker: [.58, .3, .5], cape_buffalo: [.5, .33, .66],
  methuselah: [.56, .38, .8], jaguar: [.66, .42, .55], andean_condor: [.5, .28, .95], aquila: [.5, .33, .7],
  bat: [.45, .3, .7], black_panther: [.66, .42, .5], borealis: [.62, .3, .66], bulwark: [.52, .37, .7],
  chameleon: [.68, .3, .55], cheetah: [.7, .42, .6], falcon: [.66, .5, .6], gale: [.62, .38, .75], gray_wolf: [.65, .3, .6],
  hippopotamus: [.45, .25, .8], hornet: [.58, .42, .8], jerboa: [.65, .32, .65], king_theron: [.55, .3, .62],
  lemming: [.52, .45, .62], mouse: [.5, .33, .55], pestis: [.6, .38, .8], prince_leo: [.66, .29, .5],
  princess_lea: [.4, .3, .65], queen_adira: [.55, .3, .62], rat: [.68, .48, .62], serval: [.58, .3, .8],
  sirocco: [.45, .52, .75], skunk: [.42, .45, .75], sloth: [.42, .36, .6], snow_leopard: [.55, .34, .8],
  squirrel: [.62, .4, .7], verminus: [.6, .28, .65], worker_ant: [.55, .38, .75],
  eagle: [.56, .42, .62], owl: [.57, .25, .55], raven: [.64, .44, .7], goliath: [.55, .5, .62], rattlesnake: [.52, .36, .55],
  viper: [.65, .38, .6], stoop: [.55, .45, .7], magpie: [.6, .38, .75], black_mamba: [.52, .42, .75], taipan: [.45, .4, .8],
  queen_bee: [.55, .42, .75], guard_hornet: [.58, .42, .8], soldier_ant: [.55, .38, .75], worker_wasp: [.6, .38, .75], worker_bee: [.52, .42, .8],
  nurse_bee: [.55, .45, .8], nurse_bumblebee: [.5, .45, .8], termite_king: [.55, .5, .8], termite_queen: [.45, .45, .85],
  yuka: [.58, .35, .75], cairn: [.72, .44, .55], chipmunk: [.6, .35, .7], gopher: [.55, .42, .75], groundhog: [.48, .3, .6], hamster: [.52, .38, .7], hedgehog: [.5, .45, .8], muskrat: [.55, .45, .8],
  armadillo: [.72, .38, .6], chinchilla: [.68, .38, .7], flying_squirrel: [.62, .5, .7], porcupine: [.35, .48, .62], fathom: [.5, .42, .8],
  greywhisker: [.5, .33, .65], rat_king: [.52, .25, .6], scrooge: [.52, .3, .62],
  queen_honoria: [.55, .3, .7], queen_marabunta: [.6, .45, .75], vesper: [.6, .42, .72], falstaff: [.5, .38, .85],
  eon: [.6, .33, .7], ember: [.55, .3, .75], aurum: [.52, .3, .8], omen: [.5, .42, .75],
  dire_wolf: [.65, .3, .6], dingo: [.7, .27, .6], fox: [.55, .45, .8], african_wild_dog: [.7, .3, .55], dog: [.66, .3, .6],
  pup: [.55, .36, .72], outrider: [.62, .36, .75], red_wolf: [.62, .3, .65], hyena: [.5, .38, .6], bush_dog: [.64, .33, .6],
  lobo: [.6, .25, .62], raksha: [.64, .33, .6], clarion: [.6, .22, .7], alpha: [.56, .36, .8], poppy: [.55, .36, .72], rusty: [.45, .36, .72],
};
// STRIP places the art in a thin strip (the Collection's deck tile and deck list): the point (x, y as fractions of the art)
// that lands on the strip's focus, and a zoom over the strip's own width.
export const STRIP = {
  prince_leo: [.7, .28, 1], princess_lea: [.4, .29, 1.5], king_theron: [.62, .22, 1], queen_adira: [.57, .17, 1.2], jaguar: [.7, .36, 1], serval: [.47, .22, 1.5],
  snow_leopard: [.66, .38, 1], black_panther: [.7, .43, 1], lion: [.73, .28, 1], lynx: [.52, .24, 1.3], caracal: [.47, .28, 1.5], tiger: [.82, .54, 1],
  cougar: [.73, .38, 1.1], house_cat: [.43, .37, 1.5], eon: [.62, .29, 1], goliath: [.6, .47, 1.2], ember: [.75, .17, 1.5], aurum: [.6, .2, 1.3],
  rattlesnake: [.53, .35, 1.3], omen: [.6, .28, 1.7], stoop: [.58, .47, 1.8], eagle: [.63, .43, 1.8], owl: [.6, .24, 1.2], taipan: [.6, .3, 1],
  viper: [.63, .35, 1], magpie: [.73, .34, 1.7], black_mamba: [.58, .3, 1], raven: [.77, .47, 1.7], queen_marabunta: [.8, .53, 1.7], vesper: [.66, .47, 1.1],
  queen_honoria: [.78, .25, 1.8], falstaff: [.72, .42, 1], nurse_bee: [.6, .4, 1.3], nurse_bumblebee: [.65, .4, 1.1], termite_king: [.73, .47, 1], termite_queen: [.45, .37, 1],
  queen_bee: [.65, .42, 1.3], guard_hornet: [.43, .4, 1], soldier_ant: [.55, .34, 1.3], worker_ant: [.52, .32, 1], worker_wasp: [.62, .4, 1.1], worker_bee: [.6, .42, 1.2],
  methuselah: [.62, .33, 1], borealis: [.83, .17, 1], bulwark: [.62, .31, 1], cairn: [.8, .38, 1], polar_bear: [.52, .32, 1.3], rhinoceros: [.68, .42, 1],
  hippopotamus: [.55, .15, 1], andean_condor: [.57, .35, 1.8], elephant: [.68, .28, 1], grizzly_bear: [.72, .3, 1], oxpecker: [.7, .18, 1.8], black_bear: [.38, .28, 1.5],
  sloth: [.57, .43, 1.3], cape_buffalo: [.6, .34, 1], fathom: [.48, .33, 1], greywhisker: [.5, .29, 1], rat_king: [.55, .16, 1.3], scrooge: [.55, .24, 1.3],
  flying_squirrel: [.65, .42, 1.1], porcupine: [.23, .5, 1.5], chinchilla: [.75, .4, 1], armadillo: [.83, .42, 1.3], squirrel: [.62, .31, 1.1], chipmunk: [.58, .27, 1.2],
  hedgehog: [.47, .47, 1], hamster: [.52, .29, 1.3], muskrat: [.57, .45, 1.2], groundhog: [.53, .21, 1.3], gopher: [.6, .36, 1.2], verminus: [.62, .22, 1.1],
  pestis: [.66, .48, 1], sirocco: [.47, .62, 1.5], gale: [.7, .36, 1.7], jerboa: [.73, .38, 1.3], hornet: [.5, .45, 1], chameleon: [.73, .3, 1],
  skunk: [.53, .52, 1.7], lemming: [.68, .44, 1], cheetah: [.87, .4, 1.3], rat: [.8, .48, 1], falcon: [.8, .6, 1.7], bat: [.53, .44, 1.3],
  mouse: [.47, .33, 1], lobo: [.64, .23, 1.1], raksha: [.63, .38, 1.1], clarion: [.63, .16, 1.1], bush_dog: [.63, .25, 1.1], red_wolf: [.6, .25, 1.2],
  gray_wolf: [.73, .31, 1], fox: [.7, .56, 1.3], african_wild_dog: [.68, .33, 1], dingo: [.73, .25, 1.1], dog: [.67, .34, 1], alpha: [.6, .19, 1.2],
  hyena: [.5, .38, 1.4], outrider: [.77, .31, 1.3], dire_wolf: [.73, .29, 1], pup: [.57, .27, 1.2], poppy: [.5, .32, 1], rusty: [.5, .32, 1],
};
export const hasArt = id => id in CROP;
export const artUrl = id => `/static/art/${id}.jpg`;
// A strip W x H px with its focus at ax of its width: the art zoomed, shifted as close to the focus as its edges allow.
export const stripArt = (id, W, H, ax) => {
  if (!STRIP[id]) return `background-image:url(${artUrl(id)})`;
  const [x, y, z] = STRIP[id], w = W * z, h = w * 1.5, fit = (v, lo) => Math.min(0, Math.max(lo, v));
  return `background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${fit(ax * W - x * w, W - w)}px ${fit(H / 2 - y * h, H - h)}px`;
};
