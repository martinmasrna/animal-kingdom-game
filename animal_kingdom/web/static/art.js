// Card art: /static/art/<id>.jpg (placeholder paintings from the design sandbox, cards/).
// CROP places a card's round board portrait: centre x, centre y, diameter, as fractions of the art's width, height, width.
export const CROP = {
  lion: [.64, .28, .62], lynx: [.52, .30, .62], house_cat: [.58, .36, .62], tiger: [.6, .5, .66], cougar: [.72, .36, .6],
  black_bear: [.34, .24, .66], caracal: [.42, .26, .6], rhinoceros: [.52, .38, .74], elephant: [.64, .3, .74],
  grizzly_bear: [.56, .4, .7], polar_bear: [.48, .36, .66], oxpecker: [.58, .3, .5], cape_buffalo: [.5, .33, .66],
  methuselah: [.56, .38, .8], jaguar: [.66, .42, .55], andean_condor: [.5, .28, .95], aquila: [.5, .33, .7],
  bat: [.45, .3, .7], black_panther: [.55, .33, .6], borealis: [.62, .3, .66], bulwark: [.52, .37, .7],
  chameleon: [.74, .37, .55], cheetah: [.75, .3, .6], falcon: [.4, .47, .6], gale: [.55, .33, .8], gray_wolf: [.65, .3, .6],
  hippopotamus: [.45, .25, .8], hornet: [.5, .3, .7], jerboa: [.65, .32, .65], king_theron: [.55, .3, .62],
  lemming: [.72, .52, .6], mouse: [.55, .28, .55], pestis: [.45, .24, .55], prince_leo: [.45, .28, .65],
  princess_lea: [.4, .3, .65], queen_adira: [.55, .3, .62], rat: [.35, .37, .6], serval: [.4, .2, .6],
  sirocco: [.45, .3, .65], skunk: [.35, .4, .7], sloth: [.42, .36, .6], snow_leopard: [.5, .28, .66],
  squirrel: [.5, .3, .66], verminus: [.6, .2, .6], worker_ant: [.45, .6, .9],
  eagle: [.56, .42, .62], owl: [.57, .25, .55], raven: [.64, .44, .7], goliath: [.55, .5, .62], rattlesnake: [.52, .36, .55],
  viper: [.65, .38, .6], stoop: [.55, .45, .7], magpie: [.6, .38, .75], black_mamba: [.52, .42, .75], taipan: [.45, .4, .8],
  eon: [.6, .33, .7], ember: [.55, .3, .75], aurum: [.52, .3, .8], omen: [.5, .42, .75],
  dire_wolf: [.65, .3, .6], dingo: [.7, .27, .6], fox: [.55, .45, .8], african_wild_dog: [.7, .3, .55], dog: [.66, .3, .6],
  pup: [.55, .36, .72], outrider: [.62, .36, .75], red_wolf: [.62, .3, .65], hyena: [.5, .38, .6], bush_dog: [.64, .33, .6],
  lobo: [.55, .28, .62], raksha: [.6, .33, .6], clarion: [.52, .3, .65], alpha: [.56, .35, .75],
};
export const hasArt = id => id in CROP;
export const artUrl = id => `/static/art/${id}.jpg`;
