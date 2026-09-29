// Card art: /static/art/<id>.jpg (placeholder paintings from the design sandbox, cards/).
// CROP places a card's round board portrait: centre x, centre y, diameter, as fractions of the art's width, height, width.
export const CROP = {
  lion: [.64, .28, .62], lynx: [.52, .30, .62], house_cat: [.58, .36, .62], tiger: [.6, .5, .66], cougar: [.72, .36, .6],
  black_bear: [.34, .24, .66], caracal: [.42, .26, .6], rhinoceros: [.52, .38, .74], elephant: [.64, .3, .74],
  grizzly_bear: [.56, .4, .7], polar_bear: [.48, .36, .66], oxpecker: [.58, .3, .5], cape_buffalo: [.5, .33, .66],
  methuselah: [.56, .38, .8], jaguar: [.66, .42, .55], andean_condor: [.5, .28, .95], aquila: [.5, .33, .7],
  bat: [.45, .3, .7], black_panther: [.55, .33, .6], borealis: [.62, .3, .66], bulwark: [.52, .37, .7],
  chameleon: [.68, .3, .55], cheetah: [.7, .42, .6], falcon: [.66, .5, .6], gale: [.62, .38, .75], gray_wolf: [.65, .3, .6],
  hippopotamus: [.45, .25, .8], hornet: [.5, .3, .7], jerboa: [.65, .32, .65], king_theron: [.55, .3, .62],
  lemming: [.52, .45, .62], mouse: [.55, .28, .55], pestis: [.55, .3, .6], prince_leo: [.45, .28, .65],
  princess_lea: [.4, .3, .65], queen_adira: [.55, .3, .62], rat: [.58, .32, .62], serval: [.4, .2, .6],
  sirocco: [.45, .52, .75], skunk: [.42, .45, .75], sloth: [.42, .36, .6], snow_leopard: [.5, .28, .66],
  squirrel: [.62, .4, .7], verminus: [.6, .28, .65], worker_ant: [.52, .42, .8],
  eagle: [.56, .42, .62], owl: [.57, .25, .55], raven: [.64, .44, .7], goliath: [.55, .5, .62], rattlesnake: [.52, .36, .55],
  viper: [.65, .38, .6], stoop: [.55, .45, .7], magpie: [.6, .38, .75], black_mamba: [.52, .42, .75], taipan: [.45, .4, .8],
  queen_bee: [.55, .42, .75], guard_hornet: [.45, .4, .72], soldier_ant: [.55, .38, .75], worker_wasp: [.6, .38, .75], worker_bee: [.52, .42, .8],
  nurse_bee: [.55, .45, .8], nurse_bumblebee: [.5, .45, .8], termite_king: [.55, .5, .8], termite_queen: [.45, .45, .85],
  yuka: [.58, .35, .75], cairn: [.72, .44, .55], chipmunk: [.6, .35, .7], gopher: [.55, .42, .75], groundhog: [.48, .3, .6], hamster: [.52, .38, .7], hedgehog: [.5, .45, .8], muskrat: [.55, .45, .8],
  armadillo: [.72, .38, .6], chinchilla: [.68, .38, .7], flying_squirrel: [.62, .5, .7], porcupine: [.35, .48, .62], fathom: [.5, .42, .8],
  greywhisker: [.45, .35, .7], rat_king: [.52, .25, .6], scrooge: [.52, .3, .62],
  queen_honoria: [.55, .3, .7], queen_marabunta: [.6, .45, .75], vesper: [.6, .42, .72], falstaff: [.5, .38, .85],
  eon: [.6, .33, .7], ember: [.55, .3, .75], aurum: [.52, .3, .8], omen: [.5, .42, .75],
  dire_wolf: [.65, .3, .6], dingo: [.7, .27, .6], fox: [.55, .45, .8], african_wild_dog: [.7, .3, .55], dog: [.66, .3, .6],
  pup: [.55, .36, .72], outrider: [.62, .36, .75], red_wolf: [.62, .3, .65], hyena: [.5, .38, .6], bush_dog: [.64, .33, .6],
  lobo: [.6, .25, .62], raksha: [.64, .33, .6], clarion: [.6, .22, .7], alpha: [.56, .36, .8], poppy: [.55, .36, .72], rusty: [.45, .36, .72],
};
export const hasArt = id => id in CROP;
export const artUrl = id => `/static/art/${id}.jpg`;
