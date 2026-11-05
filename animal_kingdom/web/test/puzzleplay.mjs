// Plays a line of engine actions on the game screen by clicks, the way a player would: a card then its crossroad or the
// den, an animal then where it roams, a choice's crossroad, card or Skip, End turn. Shared by the puzzle tests.
const SKIP = '__skip__';

// Until it is the player's move and nothing is playing out.
export async function waitMine(page, timeout = 20000) {
  await page.waitForFunction(() => { const s = window.__ak && window.__ak(); return s && s.V && s.V.phase === 'playing' && s.d && s.d.mine && !s.PB.busy; }, { timeout });
}

const dcr = (you, cr) => { if (you === 'A') return cr; const [c, r] = cr.split(','); return `${6 - c},${r}`; };

// After a card is picked, the pointer leaves the hand and any card shown large on hover closes first: on the bottom row
// of the board (lane 3, beside the hand) the enlarged card would otherwise take the click meant for the crossroad.
async function clearPointer(page) {
  await page.mouse.move(8, 8);
  await page.waitForFunction(() => { return ['pop', 'stackpop'].every(id => { const p = document.getElementById(id); return !p || getComputedStyle(p).display === 'none'; }); }, { timeout: 2000 }).catch(() => {});
}

async function clickTarget(page, you, target) {
  await clearPointer(page);
  if (target[0] === 'hq') await page.click(`#board [data-hq="B"]`);
  else await page.click(`#board .cr[data-cr="${dcr(you, target[1])}"]`);
}

const state = page => page.evaluate(() => { const s = window.__ak(), G = s.V.game; return JSON.stringify({ phase: s.V.phase, toAct: G && G.toAct,
  pending: G && G.pending && { kind: G.pending.kind, options: G.pending.options.map(o => [o.kind, o.v, o.cr]) }, sel: s.ui.sel, busy: s.PB.busy,
  log: (document.querySelector('#clog') || {}).textContent?.slice(-300) }); });

// Clicks one action; the caller waits for the next decision.
export async function clickAction(page, a) {
  const { V, d } = await page.evaluate(() => { const s = window.__ak(); return JSON.parse(JSON.stringify({ V: s.V, d: { cardOpts: s.d.cardOpts, otherOpts: s.d.otherOpts } })); });
  const you = V.you;
  if (a.kind === 'place') {
    const sel = a.iid != null ? `#hand .hc[data-iid="${a.iid}"]` : `#hand .hc[data-id="${a.card_id}"].can`;
    await page.click(sel);
    await clickTarget(page, you, a.target);
  } else if (a.kind === 'roam') {
    await page.click(`#board .cr[data-cr="${dcr(you, a.from)}"]`);
    await clickTarget(page, you, a.target);
  } else if (a.kind === 'pass') {
    await page.click('#tbtn');
  } else if (a.kind === 'choice') {
    if (a.choice === SKIP) return page.click('#skip');
    const opts = V.game.pending.options, o = opts.find(o => o.v === a.choice);
    if (!o) throw new Error(`no option ${JSON.stringify(a.choice)} among ${JSON.stringify(opts)}`);
    const ci = d.cardOpts.findIndex(c => c.v === a.choice), xi = d.otherOpts.findIndex(c => c.v === a.choice);
    await clearPointer(page);
    if (o.kind === 'cr') await page.click(`#board .cr[data-cr="${dcr(you, o.cr || o.v)}"]`);
    else if (o.kind === 'hq') await page.click(`#board [data-hq="B"]`);
    else if (ci >= 0) await page.click(`#opts [data-o="${ci}"]`);
    else if (xi >= 0) await page.click(`#choicebar [data-x="${xi}"]`);
    else throw new Error(`cannot click option ${JSON.stringify(o)}`);
  } else throw new Error(`unknown action ${a.kind}`);
}

// Plays the solver's actions in `line` (the defender's, marked "by": "B", are the server's to play: waited for, not clicked).
export async function playLine(page, line, { timeout = 20000 } = {}) {
  for (const [i, a] of line.entries()) {
    if (a.by === 'B') continue;
    const where = `step ${i} ${JSON.stringify(a)}`;
    try { await waitMine(page, timeout); } catch (e) { throw new Error(`${where}: never the player's move: ${await state(page)}`); }
    const before = await page.evaluate(() => window.__ak().V.version);
    await clickAction(page, a);
    try { await page.waitForFunction(v => { const s = window.__ak(); return s.V.version !== v; }, { timeout }, before); }
    catch (e) { throw new Error(`${where}: the click sent nothing: ${await state(page)}`); }
  }
}
