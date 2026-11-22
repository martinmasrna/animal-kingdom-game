// The board: one painted plate (kit2/plate_wide.webp, drawn under the stage by the game screen: ground, trails, clearings, blank stones and both dens), with the pieces,
// payouts and food drawn onto it from painted sprites. Draws in viewer space on the STAGE: the viewer is always 'A'
// (blue, den on the left), the opponent 'B' (red). What changed since the last view comes from turn.js; this file only
// draws it. Layout and look: the design sandbox's screen/plan.md and screen/kit/.
import { CROP, hasArt, artUrl } from './art.js';
import { flightEnd, inFlight } from './flight.js';
import { heldRegions, boardChanges } from './turn.js';
import { TW, TH, WINDOW, hasFigure, figure, numeral, tokenBase, armorShell } from './token.js';
import { FIGS } from './hex/figs.js';
const FIG_DIMS = id => FIGS[id] || [400, 420];

export const STAGE = { w: 1512, h: 800 };
// A window taller than wide (a phone held upright) gets its own board: a painting made upright (kit2/plate_port.webp,
// your den at the bottom, you attack upward) on a tall stage, with its own measured places for everything (PORT_AT);
// nothing is turned. setView picks the layout; every place below reads it.
export const LAND = { w: 1512, h: 800 }, PORT = { w: 720, h: 1440 };
export const VIEW = { port: false };
export function setView(port) { Object.assign(STAGE, port ? PORT : LAND); VIEW.port = port; }
const key = (c, r) => `${c},${r}`;
const kit = f => `/static/kit2/${f}`;
const team = side => (side === 'A' ? 'a' : side === 'W' ? 'n' : 'b');   // n: the neutral paint of a Wild animal

// Where things are painted on the plate (measured in plate pixels, 1672 wide), converted to stage pixels.
const PX = x => x / 1.10582, PY = y => y / 1.10582 - 25;
const CLEARINGS = [[282.3, 225.4], [558.4, 224.0], [831.6, 223.5], [1112.7, 222.8], [1382.6, 223.7],
  [288.2, 401.2], [559.6, 398.5], [834.1, 399.7], [1110.5, 396.6], [1384.7, 399.6],
  [288.1, 568.2], [557.0, 576.0], [835.9, 575.8], [1111.0, 572.9], [1379.8, 576.2]];
// Upright (stage px on the 720x1440 stage, measured on plate_port; the design sandbox's screen/kit/plate/port/): the
// clearings three across (row r left to right) and five up (column c from your den), each den's ridge across the top or
// bottom with its ten pits filling left to right toward the crown boulder at its right end, the cave mouth mid-ridge.
const PORT_AT = { cols: [150, 352, 550], rows: [1037, 853, 660, 469, 271],
  pits: { A: { x: [172, 544], y: 1208 }, B: { x: [172, 544], y: 98 } },
  crown: { A: [600, 1208], B: [600, 98] }, mouth: { A: [386, 1177], B: [356, 124] } };
// The hex board (Martin's diamond, 2026-11-16; data/maps.json map_hex): pointy-top tokens touching in rows 1-2-3-4-3-2-1
// from the top, your den the bottom tip and your opponent's the top tip on every device (Martin, 2026-11-17: "bottom to
// top 100%"), the 14 between them the crossroads. The map names a crossroad "column,row", column 1..5 from your den and
// row 1..n across it: column c is the c-th row of tokens up from your den's tip, its row 1 on the left. This is the map's
// own geometry turned a quarter (its flat-top hexagons become pointy-top ones), so neighbours on the map are neighbours
// here. A region is the corner three of them share. Drawn on a ground without trails (kit2/plate_hex.webp).
// w: a token's width on the stage (static/token.js draws it at any size), x: the board's middle, top: the top tip's top.
// The mana ruleset's board (map_hex19, the prototype of 2026-11-20): the same tokens in rows of 3, 4, 5, 4, 3, each player's
// row of 3 their base, no dens; "row,col" with row 1 your base at the bottom. HEX.mana draws it plainly (game.css .mana):
// no ground painting, no dens, a dot on each region's shared corner instead of the stone, the leaders on the screen's rail.
const HEX = { cols: [3, 4, 5, 4, 3], last: 5, dy: .75 };   // the board: rows of 3, 4, 5, 4, 3 tiles
// any other map (the 4x4 test board, AK_MAP=map_sq16): its rows as the map lists them; rows all as long are a square grid
const setRows = M => { if (!M || !M.crossroads) return; const n = {};
  for (const cr of M.crossroads) { const r = +cr.split(',')[0]; n[r] = (n[r] || 0) + 1; }
  HEX.last = Math.max(...Object.keys(n).map(Number)); HEX.cols = Array.from({ length: HEX.last }, (_, i) => n[i + 1] || 0);
  HEX.dy = HEX.cols.every(k => k === HEX.cols[0]) ? 1 : .75; };
// landscape: the board the stage's full height under the opponent's hand (to y 66), right of the middle so your hand has
// the ground beside its foot (app.js PL); upright: between the dens' ridges. The mana board stands in the middle column,
// as tall as the stage allows between the opponent's hand and yours.
const hexGeo = () => { const g = ({ w: 120, x: STAGE.w / 2, top: 41 }); g.h = g.w * TH / TW; return g; };
export const tokenWidth = () => hexGeo().w;
const hexAt = (c, r) => { const g = hexGeo(), n = HEX.cols[c - 1];
  return [g.x + (r - 1 - (n - 1) / 2) * g.w, g.top + g.h / 2 + (HEX.last - c) * HEX.dy * g.h]; };
const at = (c, r) => { return hexAt(c, r);
  if (VIEW.port) return [PORT_AT.cols[r - 1], PORT_AT.rows[c - 1]];
  const [x, y] = CLEARINGS[(r - 1) * 5 + c - 1]; return [PX(x), PY(y)]; };
// A crossroad's centre on the stage, for anything that travels to it.
// The mana board lies tilted on the screen, seen at an angle (Martin, 2026-11-20: on a short desktop window the tilt gives
// the height back), its animals standing up out of their tokens. The board's drawing stays flat (at); the browser tilts
// #board about the board's middle, and project() says where a flat board point lands on the stage, for anything drawn
// outside the board (a card flying to its crossroad). TILT.deg is the board's lean away from you (90 minus the camera's
// elevation); STAND, how tall a standing animal is, in token widths.
export const TILT = { deg: 40, persp: 1400 }, STAND = .66;
const tiltOrigin = () => { const g = hexGeo(); return [g.x, g.top + g.h / 2 + (HEX.last - 1) / 2 * HEX.dy * g.h]; };
export function project(x, y) {
  if ((!TILT.deg)) return [x, y];
  const [ox, oy] = tiltOrigin(), t = TILT.deg * Math.PI / 180, dy = y - oy, k = TILT.persp / (TILT.persp - dy * Math.sin(t));
  return [ox + (x - ox) * k, oy + dy * Math.cos(t) * k];
}
export const crossroadAt = cr => project(...at(...cr.split(',').map(Number)));

// Numbers are painted digits: chalk on a boss (strength, payouts), bold numerals in the den's gem. Every count animates
// through all digits, so they load up front (a digit fetched mid-count shows as a gap).
const digits = (dir, n) => String(n).split('').map(d => `<img src="${kit(`${dir}/${d === '+' ? 'p' : d}.webp`)}" alt="${d}" draggable="false">`).join('');
// A timer's words: its badge's tip on the board, under the card when a stack is read.
export const resolvesIn = n => `Resolves in ${n} turn${n > 1 ? 's' : ''}`;
export const chalk = n => `<span class="chalk">${digits('chalk', n)}</span>`;
export const gemDigits = n => `<span class="gemnum">${digits('gemnum', n)}</span>`;
if (typeof Image !== 'undefined') for (let d = 0; d < 10; d++) { new Image().src = kit(`gemnum/${d}.webp`); new Image().src = kit(`chalk/${d}.webp`); }
// The end's beat (ui.beat: { kind: 'fall' | 'lit', side, ago }): a den taken falls apart, a full den lights up from the bottom.
// Its pieces are timed from the beat's start (ago ms ago), so a redraw carries them on. BEAT_MS: how long it plays.
export const BEAT_MS = 2000;
const BEAT_ANIMS = new Set(['pitfall', 'gemfall', 'pitlit', 'gemflare', 'bflash', 'bdust', 'bdark', 'bglow', 'bwave']);
const reducedMotion = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;

const put = (cls, x, y, html = '', attrs = '', style = '') => `<div class="abs ${cls}" style="left:${x}px;top:${y}px;${style}" ${attrs}>${html}</div>`;

// A den: its food as a ball of light (mana.css .mden). Its area grows with the food, so the diameter goes with the square
// root, from DEN_D[0] token widths at 0 to DEN_D[1] at the 30 that wins; it floats over its spot, DEN_AT token heights past
// the middle of its base row (yours further: nearer the camera, it would cover your base row). The count and next turn's
// income are the board's numerals (static/hex/num, set as token.js numeral sets numbers over 20), inked on the light.
const DEN_D = [.3, .75], DEN_AT = { A: 1.3, B: .7 };
// k: how much the tilt's perspective scales the den's spot (project()); the ball is drawn 1/k as large there, so equal food
// shows as equal balls on the screen, near or far.
const denD = (n, k = 1) => tokenWidth() * (DEN_D[0] + (DEN_D[1] - DEN_D[0]) * Math.sqrt(Math.min(Math.max(n, 0), 30) / 30)) / k;
const denK = y => { if (!TILT.deg) return 1; const [, oy] = tiltOrigin(); return TILT.persp / (TILT.persp - (y - oy) * Math.sin(TILT.deg * Math.PI / 180)); };
const denSize = (n, k) => { const D = denD(n, k); return `--d:${D.toFixed(1)}px;--lift:${(D / 2 + 6).toFixed(1)}px`; };
const inkNum = n => { n = Math.max(0, Math.round(n)); const m = f => `--m:url(/static/hex/num/${f}.svg)`;
  return n <= 20 ? `<i style="${m(n)}"></i>` : String(n).slice(-2).split('').map((f, i) => `<i style="${m(f)};left:${i ? 17.5 : -17.5}%;right:${i ? -17.5 : 17.5}%;scale:.96"></i>`).join(''); };
const denCount = n => `<b class="dnum">${inkNum(n)}</b>`;
const denBall = (n, inc) => `<div class="up"><i class="pool"></i><i class="shade"></i><div class="float"><i class="halo"></i><i class="core"></i><i class="spec"></i>`
  + denCount(n) + (inc > 0 ? `<em class="dinc"><svg viewBox="-0.3 -0.6 0.6 1.2"><path d="M-0.21 0H0.21M0 -0.21V0.21"/></svg><span>${inkNum(Math.min(inc, 20))}</span></em>` : '') + `</div></div>`;
// A den's count stepping as food lands or leaves (foodfx.js): the number and the ball's size follow it.
export function setDenFood(den, n) {
  const b = den.querySelector('.dnum'); if (b) b.innerHTML = inkNum(n);
  const D = denD(n, +den.dataset.k || 1); den.style.setProperty('--d', `${D.toFixed(1)}px`); den.style.setProperty('--lift', `${(D / 2 + 6).toFixed(1)}px`);
  den.classList.toggle('none', n <= 0);
}

// A round crop of the card art, D stage pixels across, in a box `box` pixels across (a larger box shows more of the
// painting around the same crop, at the same zoom: the hexagonal portrait of an animal with Armor).
// It never runs past the painting's edge: the crop slides inward first, and zooms in only when the painting is narrower
// than the box (many crops already span its full width). The box's visible height is a flat-topped hexagon's (0.866).
export function portrait(id, D, box = D) {
  if (!hasArt(id)) return '';
  const [x, y, d] = CROP[id], w = Math.max(D / d, box), h = w * 1.5, hy = box * 0.433, fit = box !== D;   // round crops stay exactly as set
  const cx = fit ? Math.min(Math.max(x * w, box / 2), w - box / 2) : x * w, cy = fit ? Math.min(Math.max(y * h, hy), h - hy) : y * h;
  return `background-image:url(${artUrl(id)});background-size:${w}px ${h}px;background-position:${box / 2 - cx}px ${box / 2 - cy}px`;
}

// A unit: portrait under its team rim, strength on the boss, buried units peeking out behind, timer, and its board keywords painted on.
function unit(u, under, cards, fire = false) {
  return hexUnit(u, under, cards, fire);
  // Board keywords, as the view states them (match.py): printed or lent alike. Stealth whenever the enemy can't choose it (an
  // adjacent Armadillo gives it); Spikes only until they've removed a coverer, after that it's an ordinary animal; Armor
  // when it can't be removed (a neighbour's Capybara too), Poison when a neighbour's legendary Jellyfish lends it; an inked
  // animal (the Octopus) wears none.
  const c = cards[u.id], kws = u.inked ? [] : [u.armor && 'Armor', u.hidden && 'Stealth', u.spikes && 'Spikes', u.poison && 'Poison'].filter(Boolean);
  // the animals underneath peek out behind, down and right: each a solid disc under its team rim, a step darker (at this
  // offset a portrait showed only as a sliver, which read as a gap)
  const peek = under.slice(0, 3).map((b, i) => `<div class="buried ${b.owner} seen" style="transform:translate(${22 + i * 7}px,${20 + i * 6}px) scale(.82);z-index:${-i - 1}">`
    + `<div class="fill"></div><img class="rimimg" src="${kit(`rim_${team(b.owner)}.webp`)}" alt="" draggable="false"></div>`).join('');
  // Board keywords are painted onto the piece, each on its own layer so all four stack (design sandbox screen/keywords/):
  // Armor turns the piece into a hexagon shell scute (rim and portrait), Spikes stand out as acacia thorns behind the rim, Stealth veils the
  // portrait in mist, Poison takes the portrait over with toxic green vapour (after Hearthstone's Enrage). The card on hover says what each one does.
  const has = k => kws.includes(k);
  // Poison's two layers sandwich Stealth's mist: the green tint colours the animal under the mist, the fumes (thickest at
  // the edge) ring it from above, so an animal with both shows both.
  // The mist drifts left to right and the vapour rises, slowly, each piece on its own phase (from its iid) so the board never moves in unison;
  // the phase runs on the clock, so a redraw (every view redraws the board) carries the drift on instead of restarting it.
  const hx = has('Armor') ? ' hexp' : '', ph = (i, dur) => `animation-delay:${(-((Date.now() / 1000 + (u.iid * 7919 + i * 433) % 997) % dur)).toFixed(2)}s`;
  const img = (f, cls = '', st = '') => `<img class="${cls}" src="${kit(f)}" alt="" draggable="false"${st ? ` style="${st}"` : ''}>`;
  const venom = k => !has('Poison') ? '' : k === 'tint' ? img('kwl_vapour_tint.webp', `kwl venom tint${hx}`)
    : `<div class="kwl venom fumes${hx}">${img('kwl_vapour_fumes.webp', 'base')}<div class="vmask"><div class="flow v1" style="${ph(2, 14)}"></div></div></div>`;
  return peek + (has('Spikes') ? `<img class="kwl thorns" src="${kit(has('Armor') ? 'kwl_thorns_hex.webp' : 'kwl_thorns.webp')}" alt="" draggable="false">` : '') +
    `<div class="ring${has('Armor') ? ' hexp' : ''}${hasArt(u.id) ? '' : ' noart'}${u.inked ? ' inked" data-tip="Inked: no keywords or effects' : ''}" style="${portrait(u.id, 98, has('Armor') ? 124 : 98)}">${hasArt(u.id) ? '' : `<span>${c.name}</span>`}</div>` +
    venom('tint') + (has('Stealth') ? `<div class="kwl mist${hx}"><div class="flow m2" style="${ph(1, 70)}"></div><div class="flow m1" style="${ph(0, 25)}"></div></div>` : '') + venom('fumes') +
    `<img class="rimimg${has('Armor') ? ' hex' : ''}" src="${kit(has('Armor') ? `kwl_hexb_${team(u.owner)}.webp` : `rim_${team(u.owner)}.webp`)}" alt="" draggable="false">` +
    `<div class="boss num">${chalk(Math.max(0, u.str))}</div>` +
    (u.timer ? `<div class="timer" data-tip="${resolvesIn(u.timer)}">${chalk(u.timer)}</div>` : '') +
    (u.guarded ? '<div class="gname">Can\'t be covered</div>' : '') +   // Yuki's leader (a plain plaque until it has a painted mark)
    '';
}

// A unit on the hex board: the token (static/token.js) in its owner's frame, the animals under it peeking out behind, down
// and right, as the same token a shade darker; its board keywords as on the round piece, fitted to the token: Armor its
// stone shell over the frame, Spikes the thorns on its rim, just past its edge, Stealth's mist and Poison's vapour in the window; the trigger
// mark on the rim's upper right, a timer on its upper left.
const TK_TIMER = 'left:13.1%;top:31.6%';
// The token alone, `w` stage px wide, for anything drawn off the board as the piece (the mana ruleset's card: mana.js).
export const tokenHTML = (u, cards, w) => hexUnit(u, [], cards, false, w);
function hexUnit(u, under, cards, fire = false, tw = null) {
  const c = cards[u.id], kws = u.inked ? [] : [u.armor && 'Armor', u.hidden && 'Stealth', u.spikes && 'Spikes', u.poison && 'Poison'].filter(Boolean);
  const has = k => kws.includes(k), g = tw ? { w: tw } : hexGeo();
  const ph = (i, dur) => `animation-delay:${(-((Date.now() / 1000 + (u.iid * 7919 + i * 433) % 997) % dur)).toFixed(2)}s`;
  const img = (src, cls = '', st = '') => `<img class="${cls}" src="${src}" alt="" draggable="false"${st ? ` style="${st}"` : ''}>`;
  const peek = under.slice(0, 3).map((b, i) => `<div class="buried ${b.owner} seen tkpeek" style="transform:translate(${4 + i * 3}%,${3.5 + i * 2.5}%)">${img(tokenBase(b.owner), b.owner === 'W' ? 'wild' : '')}</div>`).reverse().join('');   // the deepest first, under the others
  // a card with no stand-in figure (a token, a reserve card) shows its painting's crop in the window
  const stand = !tw && TILT.deg && hasFigure(u.id);   // the board's piece in the mana ruleset: the animal stands
  const win = stand ? '' : hasFigure(u.id) ? figure(u.id) : (() => { const D = g.w * 380 / TW;
    return `<div class="tkwin"><div class="ring${hasArt(u.id) ? '' : ' noart'}" style="left:${(80 / TW * 100).toFixed(2)}%;top:${(92.6 / TH * 100).toFixed(2)}%;width:${D}px;height:${D}px;${portrait(u.id, D)}">${hasArt(u.id) ? '' : `<span>${c.name}</span>`}</div></div>`; })();
  const venom = k => !has('Poison') ? '' : k === 'tint' ? `<div class="kwl venom tint tkw">${img(kit('kwl_vapour_tint.webp'))}</div>`
    : `<div class="kwl venom fumes tkw">${img(kit('kwl_vapour_fumes.webp'), 'base')}<div class="vmask"><div class="flow v1" style="${ph(2, 14)}"></div></div></div>`;
  return peek + img(tokenBase(u.owner), `tkbase${u.owner === 'W' ? ' wild' : ''}`) +
    (has('Spikes') ? img(kit('kwl_thorns.webp'), 'kwl thorns') : '') +
    (has('Armor') ? img(armorShell(u.owner), 'rimimg hex tkarmor') : '') +
    `<div class="tkanimal${u.inked ? ' inked" data-tip="Inked: no keywords or effects' : ''}">${win}</div>` +
    venom('tint') + (has('Stealth') ? `<div class="kwl mist tkw"><div class="flow m2" style="${ph(1, 70)}"></div><div class="flow m1" style="${ph(0, 25)}"></div></div>` : '') + venom('fumes') +
    (u.str == null ? '' : numeral(u.str)) +
    // a legendary of the mana prototype: a painted gold gem on the top tip (Martin, 2026-11-20, a placeholder mark)
    (c && c.rarity === 'legendary' ? img('/static/hex/gem.webp', 'tkgem', 'position:absolute;left:40%;top:-4%;width:20%;z-index:4;pointer-events:none') : '') +
    (stand ? (([fw, fh]) => `<img class="mstand" src="/static/hex/fig/${u.id}.webp" alt="" draggable="false" style="height:${STAND * g.w}px;width:${STAND * g.w * fw / fh}px">`)(FIG_DIMS(u.id)) : '') +
    (u.timer ? `<div class="timer" style="${TK_TIMER}" data-tip="${resolvesIn(u.timer)}">${chalk(u.timer)}</div>` : '') +
    (u.guarded ? '<div class="gname">Can\'t be covered</div>' : '');
}

// `g` is a viewer-space game { board, food, income, winFood }. `ui`: { rings: [cr] legal targets, hqRing (the enemy den can
// be taken), preview: {cr, id, str} (the selected card under the pointer), anim: the previous view's { board, food, income,
// fx, fromStones } when this view follows one (so what changed animates; static/timeline.js plays one step per view), else null }.
// Where the board stands on the stage, for what is placed around it (app.js drawRail): each base row's left and right
// edges and its middle's height, and the board's right edge, all as the tilted board shows them.
export const RAIL = { A: null, B: null, right: 0 };
export function renderBoard(el, M, g, cards, ui) {
  setRows(M);
  { const G = hexGeo(); RAIL.right = Math.max(...M.crossroads.map(cr => { const [x, y] = at(...cr.split(',').map(Number)); return project(x + G.w / 2, y)[0]; })); }
  const bases = { A: new Set((ui.bases || {}).A || []), B: new Set((ui.bases || {}).B || []) };   // the mana board's bases, viewer space
  const A = ui.anim, rings = new Set(ui.rings || []), roamable = new Set(ui.roamable || []), fire = new Set(ui.fire || []);   // fire: the animals whose own effect this step is   // your animals that can roam now
  // the tutorial shows a region: its four crossroads and its stone glow (not rings: rings mean a click acts there)
  const shown = new Set([...(ui.region || []), ...(ui.acting || [])]), shownAt = ui.region && ui.region[0].split(',').map(Number);
  const { landed, covered, leaving } = boardChanges(A && A.board, g.board, (A && A.fx) || []);
  const strength = (A && A.strength) || new Map();   // the stored changes this step made (a grant, a poison), iid to up or down
  const held = heldRegions(M.regions, g.board);
  // the animals a card's food flies from, or eaten food flies to (Hungry): [{ x, y, food }] on `side`
  const flowAt = (side, kind) => A && A.flow && A.flow.kind === kind && A.flow.side === side
    ? A.flow.at.map(f => { const [x, y] = at(...f.cr.split(',').map(Number)); return { x, y, food: f.n }; }) : [];
  // what a stone pays: its holder's yield (the legendary Wildebeest and Boar move it), the printed food while no one holds it
  const pays = (reg, h) => (h && g.regionFood && g.regionFood[h.owner] || {})[reg.id] ?? reg.food;
  const stoneAt = reg => { if (reg.corners) {   // the corner three hexagons share: the centre of their three centres
      const ps = reg.corners.map(cr => at(...cr.split(',').map(Number))); return [ps.reduce((a, p) => a + p[0], 0) / ps.length, ps.reduce((a, p) => a + p[1], 0) / ps.length]; }
    const [c, r] = reg.c, [x1, y1] = at(c, r), [x2, y2] = at(c + 1, r + 1); return [(x1 + x2) / 2, (y1 + y2) / 2]; };
  let s = '';   // the painted ground is the game screen's (kit2/plate_wide.webp, under the stage), wider than any window
  { const g = hexGeo(); el.style.setProperty('--tw', `${g.w}px`); el.style.setProperty('--th', `${g.h}px`); el.style.setProperty('--tkwin', WINDOW); }
  { const [ox, oy] = tiltOrigin();   // the tilt: the board turns about its middle; what stands on it turns back upright
    el.style.transformOrigin = `${ox}px ${oy}px`; el.style.transform = TILT.deg ? `perspective(${TILT.persp}px) rotateX(${TILT.deg}deg)` : '';
    el.style.setProperty('--tilt', `${TILT.deg}deg`); }

  // Payout stones: the plate's stone with a small boss on it holding the payout, in the holder's colour when held.
  for (const reg of M.regions) {
    const [x, y] = stoneAt(reg), h = held.find(r => r.id === reg.id);
    { s += put(`rdot${h ? ' ' + h.owner : ''}`, x, y); continue; }   // the mana board: a dot, coloured while one side holds all three
    s += put(`stone pboss ${h ? h.owner : ''}${reg.c.every((v, i) => shownAt && v === shownAt[i]) ? ' shown' : ''}`, x, y, chalk('+' + pays(reg, h)));
  }

  // the mana board's dens (Martin, 2026-11-22, design/screen/den/props "light"): each side's food is a ball of light floating
  // past its base row, the one thing a raid takes and the only way to win; the enemy's is a target (data-hq) while an
  // animal could raid it. Its spot is on the board, the ball stands upright over it, as the animals do.
  for (const side of ['A', 'B']) {
    const ps = [...bases[side]].map(cr => at(...cr.split(',').map(Number)));
    if (!ps.length) continue;
    const G = hexGeo(), x = (Math.min(...ps.map(p => p[0])) + Math.max(...ps.map(p => p[0]))) / 2;
    { const l = project(Math.min(...ps.map(p => p[0])) - G.w / 2, ps[0][1]), r = project(Math.max(...ps.map(p => p[0])) + G.w / 2, ps[0][1]);
      RAIL[side] = { l: l[0], r: r[0], y: l[1] }; }
    const y = ps[0][1] + (side === 'A' ? DEN_AT.A : -DEN_AT.B) * G.h;
    // the trails: from each base tile's far tip into the ball, so the way in reads (Martin, 2026-11-22), in the ball's own
    // light (mana.css .mtrails). Each runs to the ball's centre, which floats its lift above the spot (a height on the screen
    // is 1/cos(tilt) as long on the board's plane), and the ball, standing in front, covers its end: they meet its rim
    // whatever its size, arriving along the line from its centre
    const d = side === 'A' ? 1 : -1, D = denD(g.food[side], denK(y)), ey = y - (D / 2 + 6) / Math.cos(TILT.deg * Math.PI / 180);
    s += `<svg class="mtrails">${ps.map(([px, py]) => { const ty = py + d * G.h / 2;
      return `<path d="M ${px} ${ty} C ${px} ${ty + (ey - ty) * .45}, ${x + (px - x) * .35} ${ey + (ty - ey) * .35}, ${x} ${ey}"/>`; }).join('')}</svg>`;
    s += put(`mden ${side}${g.food[side] > 0 ? '' : ' none'}${side === 'B' && ui.hqRing ? ' tgt' : ''}`, x, y, denBall(g.food[side], (g.income || {})[side] ?? 0), `data-hq="${side}" data-k="${denK(y).toFixed(4)}"`, denSize(g.food[side], denK(y)));
  }
  // the hex board's tips: each den's own tile, where it is entered (its mouth; the gem and the pits stay on the ridge)
  
  // the hex board's pieces top row first, so a head that rises over its rim lies over the row above, as pieces on a table
  const CRS = (M.crossroads) ? M.crossroads.map(cr => cr.split(',').map(Number)).sort((a, b) => b[0] - a[0] || a[1] - b[1]) : Array.from({ length: M.cols * M.rows }, (_, i) => [i % M.cols + 1, Math.floor(i / M.cols) + 1]);
  for (const [c, r] of CRS) {
    // an animal that roamed into the den stands only in its mouth, not also where it came from
    const cr = key(c, r), st = (g.board[cr] || []), [x, y] = at(c, r);
    const cls = (bases.A.has(cr) ? ' base A' : bases.B.has(cr) ? ' base B' : '') + (rings.has(cr) ? ' tgt' : '') + (roamable.has(cr) ? (ui.roamFrom === cr ? ' roamsel' : ' roamable') : '') + (shown.has(cr) ? ' shown' : '') + (landed.has(cr) ? ' land' : '') + (covered.has(cr) ? ' cover' : '');
    const pv = ui.preview && ui.preview.cr === cr ? ui.preview : null;
    if (pv) { s += put(`cr unit A ghost${cls}`, x, y, unit({ id: pv.id, owner: 'A', str: pv.str }, st.slice().reverse(), cards), `data-cr="${cr}"`); continue; }
    if (!st.length) { s += put(`cr clear${cls}`, x, y, '', `data-cr="${cr}"`); continue; }
    const u = st[st.length - 1], chg = strength.get(u.iid);
    // the animal that removed a unit lunges at it (a buried one surfacing under its victim rises where it is)
    let strike = '';
    if (ui.strike && ui.strike.from === cr) { const [tx, ty] = at(...ui.strike.to.split(',').map(Number)), dx = tx - x, dy = ty - y, n = Math.hypot(dx, dy) || 1;
      strike = `--sx:${(dx / n * 26).toFixed(1)}px;--sy:${(dy / n * 26).toFixed(1)}px`; }
    // a card flying here from a hand (flight.js): until it touches down the crossroad shows what it had; then the piece lands
    // in its place (--fd: when it touched down, from this step's start; negative once that is past, so it never replays)
    const was = inFlight(cr);
    if (was) {
      s += was.length ? put(`cr unit ${was[was.length - 1].owner}`, x, y, unit(was[was.length - 1], was.slice(0, -1).reverse(), cards), `data-cr="${cr}" data-card="${was[was.length - 1].id}"`)
        : put('cr clear', x, y, '', `data-cr="${cr}"`);
      continue; }
    const fe = flightEnd(cr), flown = fe ? `--fd:${Math.round(fe - (Date.now() - (ui.ago || 0)))}ms` : '';
    s += put(`cr unit ${u.owner}${cls}${flown ? ' flown' : ''}${chg ? ' strchg ' + chg : ''}${strike ? ' strike' : ''}`, x, y, unit(u, st.slice(0, -1).reverse(), cards, fire.has(cr)), `data-cr="${cr}" data-card="${u.id}"`, [strike, flown].filter(Boolean).join(';'));
  }

  // Removed units drain, sink and leave dust; returned ones lift and fly to their owner's side of the screen.
  for (const { cr, unit: u, how } of leaving) {
    // toward its owner's hand
    const [x, y] = at(...cr.split(',').map(Number)), hx = STAGE.w / 2 - x, hy = (u.owner === 'A' ? STAGE.h - 100 : -40) - y;
    s += `<div class="abs leave ${how} unit ${u.owner}" style="left:${x}px;top:${y}px;--hx:${hx}px;--hy:${hy}px">${unit(u, [], cards)}</div>`;
  }

  // a region's income flies from its stone; a card's food comes from no stone
  const stonesOf = side => A && A.fromStones === false ? flowAt(side, 'food') : held.filter(r => r.owner === side).map(r => { const [x, y] = stoneAt(r); return { x, y, food: pays(r, r) }; });
     // the mana board has no dens: its food is on the screen's rail
  
  // The unit that took a den stands in its mouth: the game's last move, drawn where it won.
  el.innerHTML = s;

  // A redraw of the same moment (ui.ago ms after it began) carries every CSS animation on from where it is, never from the start.
  const ago = ui.ago || 0;
  if (ago > 0) for (const a of el.getAnimations({ subtree: true })) if (!BEAT_ANIMS.has(a.animationName)) a.currentTime = ago;   // the end's beat keeps its own clock
  // The gem counts up to its new total as the fruit arrive (with reduced motion, the new total simply shows).
  if (!reducedMotion()) el.querySelectorAll('.dcount.tick').forEach(gem => {
    const from = +gem.dataset.from, to = +gem.dataset.to, t0 = performance.now() - ago + +gem.dataset.lag, dur = +gem.dataset.dur;
    const step = t => { const n = Math.round(from + (to - from) * Math.min(1, Math.max(0, (t - t0) / dur)));
      gem.innerHTML = gemDigits(n); if (n !== to && gem.isConnected) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  });
}

// The leaders prototype: each player's leader beside their den, a portrait under the team rim, a size up from an animal's
// (yours at the foot of your den, your opponent's at the head of theirs, as Hearthstone's two heroes). What it says is its
// state, never a hint: Queen Adira's number on the boss with her progress to the next as pips, Xanthe as the stage she has
// reached (its own painting), a power that can't be used now greyed, one you can press now ringed as an animal you can act
// with is. Where it stands on the stage: LEADER_AT.
export const LEADER_AT = { A: [178, 650], B: [1110, 78] }, LEADER_PORT = { A: [70, 1300], B: [650, 140] };
export const leaderAt = side => VIEW.port ? LEADER_PORT[side] : RAIL[side] ? [RAIL[side].l - 24 - 42, RAIL[side].y] : LEADER_AT[side];   // where app.js drawRail stands it

