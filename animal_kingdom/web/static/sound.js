// The game's sounds (Kenney CC0 packs: casino-audio, impact-sounds, rpg-audio; picked and levelled in the design sandbox's
// screen/sound/). One short mp3 per variant in kit2/snd/; a sound with several variants picks one at random so repeats
// don't drill. The volume (0..1, 0 is off) lives in localStorage ('ak:vol'), set in Settings. Browsers allow audio only after a click, which every match
// starts with (Play), so nothing needs unlocking.
const SND = {
  land: ['land_1', 'land_2', 'land_3'],          // a piece lands on a clearing
  cover: ['cover_1', 'cover_2'],                 // a piece lands on top of another
  remove: ['remove_1', 'remove_2'],              // a piece is removed
  fruit: ['fruit_1', 'fruit_2', 'fruit_3', 'fruit_4'],   // fruit drops into a pit
  draw: ['draw_1', 'draw_2', 'draw_3', 'draw_4'],        // a card slides into your hand
  oppdraw: ['oppdraw_1', 'oppdraw_2'],           // a card slides into the opponent's hand
  reveal: ['reveal_1'],                          // the opponent's card is shown
  pick: ['pick_1', 'pick_2'],                    // you pick up a card in your hand
  endturn: ['endturn_1'],                        // you end your turn
  yourturn: ['yourturn_1'],                      // your turn begins
  versus: ['versus_1'],                          // the match's versus moment
};
const VOL = { fruit: .55, oppdraw: .5, pick: .5, draw: .8 };
const cache = {};
const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch { return null; } };
export const volume = () => { const v = store('ak:vol'); return v === null ? (store('ak:mute') === '1' ? 0 : .8) : Math.max(0, Math.min(1, +v)); };
export const setVolume = v => store('ak:vol', String(Math.max(0, Math.min(1, v))));
export const muted = () => volume() === 0;

// play('land') now; play('land', 0.4) in 0.4 s
export function play(name, delay = 0) {
  if (muted() || !SND[name] || (document.hidden && name !== 'yourturn')) return;   // a background tab hears only its turn
  const go = () => {
    const v = SND[name][Math.floor(Math.random() * SND[name].length)];
    const a = (cache[v] = cache[v] || new Audio(`/static/kit2/snd/${v}.mp3`)).cloneNode();
    a.volume = (VOL[name] ?? 1) * volume(); a.play().catch(() => {});
  };
  delay > 0 ? setTimeout(go, delay * 1000) : go();
}
// warm the cache so the first sounds of a match aren't late
export const preload = () => Object.values(SND).flat().forEach(v => { if (!cache[v]) { cache[v] = new Audio(`/static/kit2/snd/${v}.mp3`); cache[v].preload = 'auto'; } });

// After a render that animated: one sound per thing that moved, timed to its CSS animation (delay, then arrival).
const secs = t => t.split(',').map(x => parseFloat(x) * (x.includes('ms') ? .001 : 1))[0] || 0;
const timing = el => { const s = getComputedStyle(el); return [secs(s.animationDelay), secs(s.animationDuration)]; };
export function soundsFor(root) {
  if (muted()) return;
  root.querySelectorAll('#board .cr.land').forEach(el => { const [d, t] = timing(el); play(el.classList.contains('cover') ? 'cover' : 'land', d + t * .75); });
  root.querySelectorAll('#board .leave.removed').forEach(el => { const [d] = timing(el); play('remove', d); });
  const fruit = [...root.querySelectorAll('#board .flyfruit')].map(el => { const [d, t] = timing(el); return d + t; }).sort((a, b) => a - b);
  fruit.filter((t, i) => i === 0 || t - fruit[i - 1] > .07).slice(0, 8).forEach(t => play('fruit', t));   // a patter, not a roar
  root.querySelectorAll('#hand .hc.drawn').forEach(el => play('draw', timing(el)[0]));
  root.querySelectorAll('#opphand .oc.drawn').forEach(el => play('oppdraw', timing(el)[0]));
}
