// Card art: /static/art/<id>.jpg (placeholder paintings from the design sandbox, cards/).
// CROP places a card's round board portrait: centre x, centre y, diameter, as fractions of the art's width, height, width.
export const CROP = {
  prince_leo: [.66, .29, .5], princess_lea: [.42, .3, .45], king_theron: [.6, .25, .55], queen_adira: [.55, .2, .42], jaguar: [.66, .38, .45], serval: [.5, .24, .42],
  snow_leopard: [.56, .31, .45], black_panther: [.66, .42, .5], lion: [.7, .3, .55], lynx: [.52, .26, .42], caracal: [.5, .26, .42], tiger: [.72, .52, .5],
  cougar: [.7, .38, .42], house_cat: [.45, .38, .42], eon: [.62, .3, .6], goliath: [.6, .45, .45], ember: [.62, .25, .6], aurum: [.55, .28, .55],
  rattlesnake: [.58, .38, .5], omen: [.55, .34, .5], stoop: [.52, .45, .6], eagle: [.55, .42, .6], owl: [.58, .27, .45], taipan: [.55, .35, .8],
  viper: [.62, .37, .5], magpie: [.62, .35, .6], black_mamba: [.57, .37, .62], raven: [.62, .4, .55], queen_marabunta: [.5, .45, .9], vesper: [.6, .48, .6],
  queen_honoria: [.62, .28, .55], falstaff: [.6, .4, .7], nurse_bee: [.52, .45, .75], nurse_bumblebee: [.6, .45, .7], termite_king: [.6, .47, .75], termite_queen: [.45, .42, .85],
  queen_bee: [.5, .42, .75], guard_hornet: [.45, .42, .6], soldier_ant: [.58, .38, .65], worker_ant: [.52, .55, .6], worker_wasp: [.5, .37, .75], worker_bee: [.5, .4, .8],
  methuselah: [.65, .35, .7], borealis: [.76, .24, .45], bulwark: [.57, .35, .6], cairn: [.64, .38, .7], polar_bear: [.52, .34, .5], rhinoceros: [.65, .4, .6],
  hippopotamus: [.5, .26, .65], andean_condor: [.5, .33, .9], elephant: [.68, .33, .65], grizzly_bear: [.68, .35, .55], oxpecker: [.58, .28, .45], black_bear: [.4, .32, .5],
  sloth: [.55, .42, .45], cape_buffalo: [.6, .33, .75], fathom: [.5, .36, .8], greywhisker: [.38, .32, .5], rat_king: [.55, .21, .45], scrooge: [.53, .27, .45],
  flying_squirrel: [.6, .42, .5], porcupine: [.35, .45, .62], chinchilla: [.72, .37, .45], armadillo: [.68, .4, .6], squirrel: [.58, .3, .55], chipmunk: [.55, .3, .5],
  hedgehog: [.5, .47, .62], hamster: [.52, .33, .55], muskrat: [.5, .45, .6], groundhog: [.52, .25, .42], gopher: [.58, .38, .6], verminus: [.6, .25, .5],
  pestis: [.55, .31, .5], sirocco: [.47, .5, .7], gale: [.62, .37, .5], jerboa: [.72, .34, .5], hornet: [.32, .23, .5], chameleon: [.66, .34, .55],
  skunk: [.42, .4, .8], lemming: [.62, .42, .6], cheetah: [.73, .4, .5], rat: [.58, .28, .45], falcon: [.7, .52, .5], bat: [.55, .4, .6],
  mouse: [.55, .26, .45], lobo: [.6, .25, .5], raksha: [.6, .36, .5], clarion: [.6, .22, .6], bush_dog: [.6, .29, .5], red_wolf: [.58, .27, .45],
  gray_wolf: [.72, .3, .45], fox: [.64, .5, .55], african_wild_dog: [.67, .3, .5], dingo: [.7, .28, .45], dog: [.65, .33, .5], alpha: [.6, .28, .6],
  hyena: [.46, .38, .5], outrider: [.7, .34, .45], dire_wolf: [.73, .28, .45], pup: [.57, .3, .55], poppy: [.5, .3, .6], rusty: [.5, .3, .6],
  aquila: [.5, .33, .7], yuka: [.58, .35, .75],
};
// STRIP places the art in a thin strip (the Collection's deck tile and deck list): the point (x, y as fractions of the art)
// that lands on the strip's focus, and a zoom over the strip's own width.
export const STRIP = {
  prince_leo: [.7, .28, 1], princess_lea: [.4, .29, 1.5], king_theron: [.62, .22, 1], queen_adira: [.57, .17, 1.2], jaguar: [.7, .36, 1], serval: [.52, .23, 1.3],
  snow_leopard: [.55, .32, 1.3], black_panther: [.7, .43, 1], lion: [.73, .28, 1], lynx: [.52, .24, 1.3], caracal: [.47, .28, 1.5], tiger: [.82, .54, 1],
  cougar: [.73, .38, 1.1], house_cat: [.43, .37, 1.5], eon: [.62, .29, 1], goliath: [.6, .47, 1.2], ember: [.75, .17, 1.5], aurum: [.6, .2, 1.3],
  rattlesnake: [.53, .35, 1.3], omen: [.6, .28, 1.7], stoop: [.58, .47, 1.8], eagle: [.63, .43, 1.8], owl: [.6, .24, 1.2], taipan: [.6, .3, 1],
  viper: [.63, .35, 1], magpie: [.73, .34, 1.7], black_mamba: [.58, .3, 1], raven: [.77, .47, 1.7], queen_marabunta: [.8, .53, 1.7], vesper: [.66, .47, 1.1],
  queen_honoria: [.78, .25, 1.8], falstaff: [.72, .42, 1], nurse_bee: [.6, .4, 1.3], nurse_bumblebee: [.65, .4, 1.1], termite_king: [.73, .47, 1], termite_queen: [.45, .37, 1],
  queen_bee: [.65, .42, 1.3], guard_hornet: [.43, .4, 1], soldier_ant: [.55, .34, 1.3], worker_ant: [.6, .56, 1.7], worker_wasp: [.62, .4, 1.1], worker_bee: [.6, .42, 1.2],
  methuselah: [.62, .33, 1], borealis: [.83, .17, 1], bulwark: [.62, .31, 1], cairn: [.8, .38, 1], polar_bear: [.52, .32, 1.3], rhinoceros: [.68, .42, 1],
  hippopotamus: [.55, .15, 1], andean_condor: [.57, .35, 1.8], elephant: [.68, .28, 1], grizzly_bear: [.72, .3, 1], oxpecker: [.7, .18, 1.8], black_bear: [.38, .28, 1.5],
  sloth: [.57, .43, 1.3], cape_buffalo: [.6, .34, 1], fathom: [.48, .33, 1], greywhisker: [.36, .29, 1.5], rat_king: [.55, .16, 1.3], scrooge: [.55, .24, 1.3],
  flying_squirrel: [.65, .42, 1.1], porcupine: [.23, .5, 1.5], chinchilla: [.75, .4, 1], armadillo: [.83, .42, 1.3], squirrel: [.62, .31, 1.1], chipmunk: [.58, .27, 1.2],
  hedgehog: [.47, .47, 1], hamster: [.52, .29, 1.3], muskrat: [.57, .45, 1.2], groundhog: [.53, .21, 1.3], gopher: [.6, .36, 1.2], verminus: [.62, .22, 1.1],
  pestis: [.57, .31, 1.2], sirocco: [.47, .62, 1.5], gale: [.7, .36, 1.7], jerboa: [.73, .38, 1.3], hornet: [.4, .22, 1.5], chameleon: [.73, .3, 1],
  skunk: [.53, .52, 1.7], lemming: [.68, .44, 1], cheetah: [.87, .4, 1.3], rat: [.6, .27, 1.2], falcon: [.8, .6, 1.7], bat: [.53, .44, 1.3],
  mouse: [.57, .21, 1.3], lobo: [.64, .23, 1.1], raksha: [.63, .38, 1.1], clarion: [.63, .16, 1.1], bush_dog: [.63, .25, 1.1], red_wolf: [.6, .25, 1.2],
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
