// Card art: /static/art/<id>.jpg (placeholder paintings from the design sandbox, cards/).
// CROP places a card's round board portrait: centre x, centre y, diameter, as fractions of the art's width, height, width.
export const CROP = {
  lion: [.64, .28, .62], lynx: [.52, .30, .62], house_cat: [.58, .36, .62], tiger: [.6, .5, .66], cougar: [.72, .36, .6],
  black_bear: [.34, .24, .66], caracal: [.42, .26, .6], rhinoceros: [.52, .38, .74], elephant: [.64, .3, .74],
  grizzly_bear: [.56, .4, .7], polar_bear: [.48, .36, .66], oxpecker: [.58, .3, .5], cape_buffalo: [.5, .33, .66],
  methuselah: [.56, .38, .8], jaguar: [.66, .42, .55], andean_condor: [.5, .28, .95],
  bat: [.45, .3, .7], black_panther: [.66, .42, .5], borealis: [.62, .3, .66], bulwark: [.52, .37, .7],
  chameleon: [.68, .3, .55], cheetah: [.7, .42, .6], falcon: [.66, .5, .6], gale: [.62, .38, .75], gray_wolf: [.65, .3, .6],
  hippopotamus: [.45, .25, .8], hornet: [.58, .42, .8], jerboa: [.65, .32, .65], king_theron: [.55, .3, .62],
  lemming: [.65, .36, .7], mouse: [.5, .33, .55], pestis: [.6, .38, .8], prince_leo: [.66, .29, .5],
  princess_lea: [.4, .3, .65], queen_adira: [.55, .3, .62], rat: [.68, .48, .62], serval: [.58, .3, .8],
  sirocco: [.45, .52, .75], skunk: [.42, .45, .75], sloth: [.42, .36, .6], snow_leopard: [.55, .34, .8],
  squirrel: [.62, .4, .7], verminus: [.6, .38, .8], worker_ant: [.55, .38, .75],
  eagle: [.56, .42, .62], owl: [.57, .25, .55], raven: [.64, .44, .7], goliath: [.55, .5, .62], rattlesnake: [.52, .36, .55],
  viper: [.65, .38, .6], stoop: [.55, .45, .7], magpie: [.6, .38, .75], black_mamba: [.52, .42, .75], taipan: [.45, .4, .8],
  queen_bee: [.55, .42, .75], guard_hornet: [.58, .42, .8], soldier_ant: [.55, .38, .75], worker_wasp: [.6, .38, .75], worker_bee: [.52, .42, .8],
  nurse_bee: [.55, .45, .8], nurse_bumblebee: [.5, .45, .8], termite_king: [.55, .5, .8], termite_queen: [.45, .45, .85],
  cairn: [.72, .44, .55], chipmunk: [.6, .45, .8], gopher: [.52, .38, .8], groundhog: [.55, .36, .65], hamster: [.52, .42, .72], hedgehog: [.5, .45, .8], muskrat: [.65, .42, .7],
  armadillo: [.72, .38, .6], chinchilla: [.68, .38, .7], flying_squirrel: [.62, .5, .7], porcupine: [.35, .48, .62], fathom: [.5, .42, .8],
  greywhisker: [.5, .33, .65], rat_king: [.52, .35, .8], scrooge: [.62, .45, .62],
  queen_honoria: [.55, .3, .7], queen_marabunta: [.6, .45, .75], vesper: [.6, .42, .72], falstaff: [.5, .38, .85],
  eon: [.6, .33, .7], ember: [.55, .3, .75], aurum: [.5, .45, .96], omen: [.5, .42, .75], anaconda: [.49, .6, .62], egg_eater: [.66, .4, .6], snake_egg: [.55, .46, .62], bird_egg: [.52, .42, .82],
  dire_wolf: [.65, .3, .6], dingo: [.7, .27, .6], fox: [.55, .45, .8], african_wild_dog: [.7, .3, .55], dog: [.66, .3, .6],
  pup: [.55, .36, .72], outrider: [.62, .36, .75], red_wolf: [.62, .3, .65], hyena: [.5, .38, .6], bush_dog: [.64, .33, .6],
  lobo: [.6, .25, .62], raksha: [.64, .33, .6], clarion: [.6, .22, .7], alpha: [.56, .36, .8], poppy: [.55, .36, .72], rusty: [.45, .36, .72],
};
// STRIP places the art in a thin strip (the Collection's deck tile and deck list): the point (x, y as fractions of the art)
// that lands on the strip's focus, and a zoom over the strip's own width.
export const STRIP = {
  prince_leo: [.7, .28, 1], princess_lea: [.4, .29, 1.5], king_theron: [.62, .22, 1], queen_adira: [.57, .17, 1.2], jaguar: [.7, .36, 1], serval: [.47, .22, 1.5],
  snow_leopard: [.66, .38, 1], black_panther: [.7, .43, 1], lion: [.73, .28, 1], lynx: [.52, .24, 1.3], caracal: [.47, .28, 1.5], tiger: [.82, .54, 1],
  cougar: [.73, .38, 1.1], house_cat: [.43, .37, 1.5], eon: [.62, .29, 1], goliath: [.6, .47, 1.2], ember: [.75, .17, 1.5], aurum: [.6, .2, 1.3], anaconda: [.5, .55, 1.2], egg_eater: [.7, .36, 1.3], snake_egg: [.58, .45, 1.3], bird_egg: [.6, .33, 1.2],
  rattlesnake: [.53, .35, 1.3], omen: [.6, .28, 1.7], stoop: [.58, .47, 1.8], eagle: [.63, .43, 1.8], owl: [.6, .24, 1.2], taipan: [.6, .3, 1],
  viper: [.63, .35, 1], magpie: [.73, .34, 1.7], black_mamba: [.58, .3, 1], raven: [.77, .47, 1.7], queen_marabunta: [.8, .53, 1.7], vesper: [.66, .47, 1.1],
  queen_honoria: [.78, .25, 1.8], falstaff: [.72, .42, 1], nurse_bee: [.6, .4, 1.3], nurse_bumblebee: [.65, .4, 1.1], termite_king: [.73, .47, 1], termite_queen: [.45, .37, 1],
  queen_bee: [.65, .42, 1.3], guard_hornet: [.43, .4, 1], soldier_ant: [.55, .34, 1.3], worker_ant: [.52, .32, 1], worker_wasp: [.62, .4, 1.1], worker_bee: [.6, .42, 1.2],
  methuselah: [.62, .33, 1], borealis: [.83, .17, 1], bulwark: [.62, .31, 1], cairn: [.8, .38, 1], polar_bear: [.52, .32, 1.3], rhinoceros: [.68, .42, 1],
  hippopotamus: [.55, .15, 1], andean_condor: [.57, .35, 1.8], elephant: [.68, .28, 1], grizzly_bear: [.72, .3, 1], oxpecker: [.7, .18, 1.8], black_bear: [.38, .28, 1.5],
  sloth: [.57, .43, 1.3], cape_buffalo: [.6, .34, 1], fathom: [.48, .33, 1], greywhisker: [.5, .29, 1], rat_king: [.52, .17, 1.2], scrooge: [.73, .4, 1.2],
  flying_squirrel: [.65, .42, 1.1], porcupine: [.23, .5, 1.5], chinchilla: [.75, .4, 1], armadillo: [.83, .42, 1.3], squirrel: [.62, .31, 1.1], chipmunk: [.8, .47, 1.3],
  hedgehog: [.47, .47, 1], hamster: [.52, .38, 1], muskrat: [.8, .46, 1.4], groundhog: [.58, .3, 1], gopher: [.62, .37, 1], verminus: [.7, .22, 1],
  pestis: [.66, .48, 1], sirocco: [.47, .62, 1.5], gale: [.7, .36, 1.7], jerboa: [.73, .38, 1.3], hornet: [.5, .45, 1], chameleon: [.73, .3, 1],
  skunk: [.53, .52, 1.7], lemming: [.82, .38, 1.4], cheetah: [.87, .4, 1.3], rat: [.8, .48, 1], falcon: [.8, .6, 1.7], bat: [.53, .44, 1.3],
  mouse: [.47, .33, 1], lobo: [.64, .23, 1.1], raksha: [.63, .38, 1.1], clarion: [.63, .16, 1.1], bush_dog: [.63, .25, 1.1], red_wolf: [.6, .25, 1.2],
  gray_wolf: [.73, .31, 1], fox: [.7, .56, 1.3], african_wild_dog: [.68, .33, 1], dingo: [.73, .25, 1.1], dog: [.67, .34, 1], alpha: [.6, .19, 1.2],
  hyena: [.5, .38, 1.4], outrider: [.77, .31, 1.3], dire_wolf: [.73, .29, 1], pup: [.57, .27, 1.2], poppy: [.5, .32, 1], rusty: [.5, .32, 1],
};
// FULL places the painting in the full card's window, which shows 61% of its height between the name bar and the rules panel:
// the height, as a fraction of the art, the window centres on (its top edge is that minus .305). Set by hand: the whole animal
// where it fits, otherwise its head near the top with a little room and the legs cut. A card without an entry centres on its
// board portrait (CROP), which Martin preferred for a few (Eagle, Ember, Hippopotamus, ...).
export const FULL = {
  african_wild_dog: .425, alpha: .355, anaconda: .485, andean_condor: .335, armadillo: .435, aurum: .415, bat: .305,
  bird_egg: .445, black_bear: .445, black_mamba: .445, black_panther: .455, borealis: .365, bulwark: .345, bush_dog: .475,
  cairn: .455, cape_buffalo: .445, caracal: .345, chameleon: .455, cheetah: .415, chinchilla: .365, chipmunk: .405,
  clarion: .355, cougar: .455, dingo: .375, dire_wolf: .385, dog: .435, egg_eater: .485, elephant: .365, eon: .375,
  falcon: .385, falstaff: .385, fathom: .405, flying_squirrel: .385, fox: .405, gale: .375, goliath: .345, gopher: .475,
  gray_wolf: .475, greywhisker: .415, grizzly_bear: .425, groundhog: .385, guard_hornet: .465, hamster: .455, hedgehog: .435,
  hornet: .425, house_cat: .435, hyena: .475, jaguar: .455, king_theron: .305, lemming: .445, lion: .355, lobo: .385,
  lynx: .395, magpie: .375, methuselah: .405, mouse: .455, muskrat: .485, nurse_bumblebee: .445, omen: .465, outrider: .365,
  owl: .385, pestis: .405, poppy: .355, porcupine: .435, prince_leo: .365, princess_lea: .395, pup: .365, queen_adira: .375,
  queen_bee: .425, queen_marabunta: .455, raksha: .425, rat: .475, rat_king: .365, rattlesnake: .555, raven: .405,
  red_wolf: .445, rhinoceros: .395, rusty: .345, scrooge: .485, serval: .385, sirocco: .415, skunk: .395, sloth: .405,
  snake_egg: .445, snow_leopard: .385, soldier_ant: .465, squirrel: .455, taipan: .405, termite_king: .485,
  termite_queen: .455, tiger: .505, verminus: .345, vesper: .425, viper: .415, worker_ant: .465, worker_bee: .355,
  worker_wasp: .375,
};
export const hasArt = id => id in CROP;
export const artUrl = id => `/static/art/${id}.jpg`;
// A strip W x H px with its focus at ax of its width: the art zoomed, shifted as close to the focus as its edges allow.
export const stripArt = (id, W, H, ax) => {
  if (!STRIP[id]) return `background-image:url(${artUrl(id)})`;
  const [x, y, z] = STRIP[id], w = W * z, h = w * 1.5, fit = (v, lo) => Math.min(0, Math.max(lo, v));
  return `background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${fit(ax * W - x * w, W - w)}px ${fit(H / 2 - y * h, H - h)}px`;
};
