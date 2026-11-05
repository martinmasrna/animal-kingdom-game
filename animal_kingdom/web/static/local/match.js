// A practice match against a bot played in the browser (?local=1): the engine runs here as WebAssembly (static/wasm,
// engine_rs/wasm.sh), the bot thinks in a Web Worker (worker.js), and the game screen is fed the views the server would
// have sent: the engine's part from the wasm (engine_rs/src/view.rs, held equal to the server's by
// tools/engine_rs/wasm_oracle.mjs), the match's part (seats, history, numbered events) built here the way web/match.py
// builds it. When the game ends, its log goes to the server (/api/local/match), which replays and saves it as any match;
// a log that can't be sent now waits in localStorage and goes with the next one.
import init, { Engine, Bot, sourceHash } from '../wasm/ak_engine.js';

const EVENTS_KEPT = 200;                                   // match.py EVENTS_KEPT
const BOT_PAUSE = { open: 0.6, move: 0.4, choice: 0.3 };   // server.py: the bot's beat once its last move has been watched
const BOT_WAIT_MAX = 6.0;                                  // server.py: at most this long for the screen to play it out
const BOT_THINK_MAX = 20;                                  // server.py: then the Easy bot's move is played for it
const OUTBOX = 'ak:local:outbox';
const other = p => (p === 'A' ? 'B' : 'A');
const sleep = ms => new Promise(r => setTimeout(r, ms));

let loaded = null;   // {module, doc, engine}: the wasm compiled once a page, the engine doc fetched once
let broken = false;  // the engine panicked (a RuntimeError out of the wasm): this page plays its next matches on the server

// The wasm and what it plays with, or null when this browser can't play locally (no wasm, or a build older or newer
// than the server's engine: the source hashes differ). `api` is the client's fetch.
export async function prepare(api) {
  if (broken) return null;
  if (loaded) return loaded;
  try {
    const [wasm, doc] = await Promise.all([
      fetch(new URL('../wasm/ak_engine_bg.wasm', import.meta.url)).then(r => r.arrayBuffer()).then(b => WebAssembly.compile(b)),
      api('/api/local/engine').then(r => r.json()),
    ]);
    await init({ module_or_path: wasm });
    if (!doc.source_hash || doc.source_hash !== sourceHash()) {
      console.warn('local play off: the browser engine', sourceHash(), 'is not the server\'s', doc.source_hash);
      return null;
    }
    const engine = new Engine(JSON.stringify(doc.cards), JSON.stringify(doc.maps), JSON.stringify(doc.config), doc.map_id);
    loaded = { module: wasm, doc, engine };
    return loaded;
  } catch (e) {
    console.warn('local play off:', e);
    return null;
  }
}

// What a move did, read from the engine's events (match.py _effects).
function effects(events, move) {
  const fx = [];
  for (const e of events) {
    if (e.e === 'cover' && e.owner !== move.seat) fx.push({ k: 'cover', card: e.card, owner: e.owner });
    else if (e.e === 'place' && e.reveal) fx.push({ k: 'placed', card: e.card, owner: e.player });
    else if (e.e === 'remove' && e.cr) fx.push({ k: 'remove', card: e.card, owner: e.owner });
    else if (e.e === 'bounce') fx.push({ k: 'bounce', card: e.card, owner: e.owner });
    else if (e.e === 'to_deck') fx.push({ k: 'to_deck', card: e.card, owner: e.owner });
    else if (e.e === 'draw') fx.push({ k: 'draw', seat: e.player, n: e.cards.length });
    else if (e.e === 'food' && !e.income) fx.push({ k: 'food', seat: e.player, n: e.n });
  }
  const merged = [];
  for (const f of fx) {
    const last = merged[merged.length - 1];
    if (last && (f.k === 'draw' || f.k === 'food') && last.k === f.k && last.seat === f.seat) merged[merged.length - 1] = { ...last, n: last.n + f.n };
    else merged.push(f);
  }
  return merged;
}

// An event as `viewer` may see it (match.py public_event).
function publicEvent(e, viewer) {
  const drop = k => Object.fromEntries(Object.entries(e).filter(([x]) => x !== k));
  if (e.e === 'draw' && e.player !== viewer) return { ...drop('cards'), n: e.cards.length };
  if (e.e === 'to_hand' && e.player !== viewer && !e.public) return drop('card');
  if (e.e === 'leave_hand' && e.owner !== viewer) return drop('card');
  return e;
}

const counts = list => { const c = {}; for (const x of list) c[x] = (c[x] || 0) + 1; return c; };

export class LocalMatch {
  // setup: /api/local/setup's answer; body: what was sent for it (the deck and the bot, sent again with the log);
  // onView(view): the client's socket handler; opts.toast for a word to the player.
  constructor(lib, setup, body, onView, opts = {}) {
    Object.assign(this, { lib, setup, body, onView, toast: opts.toast || (() => {}), api: opts.api || fetch });
    this.live = false;        // views go to the screen once it shows the match (show)
    this.id = 'local';
    this.results = [];
    this.lastGame = null;
    this.rematches = 0;
    this.version = 0;
    this.played = 0;          // the last event the screen has played out ('played')
    this.thinkMs = [];        // the bot's time per move in its worker, for the numbers (knowledge/wasm/STATUS.md)
    this.wallMs = [];         // and from its turn to its move on the board, the screen's waits and the beat included
    this.closed = false;
    this.flush();             // a log left from an earlier visit goes first
    this.start();
  }

  // ------------------------------------------------------------- games (match.py _start_game)
  start() {
    let first = '';
    if (this.results.length || this.lastGame) {
      const last = this.results.length ? this.results[this.results.length - 1] : this.lastGame;
      first = last.winner ? other(last.winner) : last.first;
    }
    this.seed = Math.floor(Math.random() * (1 << 30));
    if (this.state) this.state.free();
    this.state = this.lib.engine.newGame(JSON.stringify(this.setup.lists.A), JSON.stringify(this.setup.lists.B), this.seed, first, false);
    this.actions = []; this.times = []; this.t0 = performance.now();
    this.history = []; this.events = []; this.seq = 0;
    this.phase = 'playing';
    this.startWorker(this.seed + 1);    // match.py: the bot of seat i is seeded seed + i
    this.takeEvents();
    this.version++;
    this.push();
  }

  startWorker(seed) {
    if (this.worker) this.worker.terminate();
    this.botSeed = seed;
    this.worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });
    this.waiting = new Map();
    this.ready = new Promise(res => {
      this.worker.onmessage = ({ data: m }) => {
        if (m.t === 'ready') return res();
        const w = this.waiting.get(m.id); if (!w) return;
        this.waiting.delete(m.id);
        if (m.t === 'chose') { this.thinkMs.push(m.ms); w.resolve(m.action); } else w.reject(new Error(m.error));
      };
    });
    this.worker.postMessage({ t: 'init', module: this.lib.module, doc: this.lib.doc, spec: this.setup.spec, evaluator: this.setup.evaluator, seed });
    this.asked = 0;
  }

  takeEvents() {
    const evs = JSON.parse(this.state.takeEvents());
    for (const e of evs) e.seq = ++this.seq;
    this.events = this.events.concat(evs).slice(-EVENTS_KEPT);
    return evs;
  }

  toAct() { return this.phase === 'playing' ? this.state.playerToAct() : null; }

  // ------------------------------------------------------------- moves (match.py act)
  act(s, action) {
    if (this.phase !== 'playing') throw new Error('no game in progress');
    const st = this.state;
    const a = JSON.parse(st.canonical(JSON.stringify(action)));
    if (st.playerToAct() !== s && st.earlyMulligan(s)) {      // both mulligan at once
      st.applyLogged(JSON.stringify({ ...a, by: s }));
      this.takeEvents();
      this.log({ ...a, by: s });
      this.version++;
      return;
    }
    if (st.playerToAct() !== s) throw new Error('not your decision');
    const pending = JSON.parse(st.pending());
    const startsMove = (pending === null && a.kind !== 'pass') || a.kind === 'place';
    const round = Math.floor(st.turnCounter / 2) + 1;
    let roamer = null;
    if (a.kind === 'roam') { const stack = JSON.parse(st.toJson()).board[a.from] || []; roamer = stack.length ? stack[stack.length - 1].card_id : null; }
    st.applyAction(JSON.stringify(a), true);
    const fresh = this.takeEvents();
    this.log(a);
    if (startsMove) {
      const placed = a.kind === 'place', roamed = a.kind === 'roam';
      this.history.push({ round, seat: s, kind: placed ? 'place' : roamed ? 'roam' : 'draw', card: placed ? a.card_id : roamer,
        target: placed || roamed ? a.target : null, fx: [], events: [] });
    }
    if (this.history.length) {
      const m = this.history[this.history.length - 1];
      m.events.push(...fresh);
      m.fx = effects(m.events, m);
    }
    this.checkEnd();
    this.version++;
  }

  log(a) { this.actions.push(a); this.times.push(Math.round((performance.now() - this.t0) / 100) / 10); }

  checkEnd(result) {
    result = result || JSON.parse(this.state.isTerminal());
    if (!result) return;
    this.state.setResult(result.winner || '', result.reason);
    this.results.push({ winner: result.winner, reason: result.reason, turns: Math.floor(this.state.turnCounter / 2) + 1,
      first: this.state.firstPlayer });
    this.phase = 'match_over';             // one game a match (match.py GAMES_TO_WIN)
    this.send({ concede: result.reason === 'concede' });
  }

  // ------------------------------------------------------------- the client's messages (server.py socket)
  handle(msg) {
    try {
      if (msg.t === 'act') this.act('A', msg.action);
      else if (msg.t === 'played') { this.played = Math.max(this.played, +msg.seq || 0); return; }
      else if (msg.t === 'concede') {
        if (this.phase !== 'playing') throw new Error('no game to concede');
        this.checkEnd({ winner: 'B', reason: 'concede' });
        this.version++;
      } else if (msg.t === 'rematch') {
        if (this.phase !== 'match_over') throw new Error('the match is still on');
        this.lastGame = this.results[this.results.length - 1];
        this.results = []; this.rematches++;
        this.start();
        return;
      } else if (msg.t === 'ready' || msg.t === 'hold' || msg.t === 'next') return;
      else throw new Error(`unknown message ${msg.t}`);
    } catch (e) {
      if (e instanceof WebAssembly.RuntimeError) return this.panicked(e);
      this.toast(e.message);
    }
    this.push();
  }

  panicked(e) {   // the module is gone with its state: the game can't go on here (the console has the panic's message)
    console.error('local engine stopped:', e);
    broken = true; loaded = null;
    this.toast('This game stopped on an engine error. The next one plays on the server.');
    this.close();
  }

  // ------------------------------------------------------------- views (match.py view, _game_view)
  view() {
    const s = 'A', S = { A: 0, B: 0 };
    for (const r of this.results) if (r.winner) S[r.winner]++;
    const g = JSON.parse(this.state.view(s));
    g.clock = { on: false };
    g.history = this.history.map(({ round, seat, kind, card, target, fx }) => ({ round, seat, kind, card, target, fx }));
    g.events = this.events.filter(e => !(e.e === 'mulligan' && e.player !== s)).map(e => publicEvent(e, s));
    return { id: this.id, you: s, phase: this.phase, version: this.version, takeover: false, seats: this.setup.seats,
      results: this.results.map(({ winner, reason, turns }) => ({ winner, reason, turns })), score: S,
      lists: { A: counts(this.setup.lists.A), B: counts(this.setup.lists.B) }, game: g, ranked: false, local: true };
  }

  show() { this.live = true; this.push(); }

  push() {
    if (this.closed || !this.live) return;
    this.onView(this.view());
    this.kickBot();
  }

  // ------------------------------------------------------------- the bot (server.py _run_bot)
  kickBot() {
    const s = this.toAct();
    if (!s || s === 'A' || this.thinking) return;
    this.thinking = this.runBot().finally(() => { this.thinking = null; if (!this.closed) this.kickBot(); });
  }

  async runBot() {
    const s = this.toAct();
    if (!s || s === 'A') return;
    const st = this.state, version = this.version;
    const pending = JSON.parse(st.pending()), opening = !pending && JSON.parse(st.toJson()).actions_taken_this_turn === 0;
    const id = ++this.asked;
    // the bot thinks while the screen plays its last move out, then keeps the server's beat
    const choice = new Promise((resolve, reject) => { this.waiting.set(id, { resolve, reject }); });
    this.ready.then(() => this.worker.postMessage({ t: 'choose', id, state: st.toJson() }));
    const t0 = performance.now();
    while (performance.now() - t0 < BOT_WAIT_MAX * 1000 && this.played < this.seq && !this.closed) await sleep(50);
    await sleep(1000 * BOT_PAUSE[pending ? 'choice' : opening ? 'open' : 'move'] * (window.AK_BOT_PAUSE ?? 1));
    let action;
    try {
      action = await Promise.race([choice, sleep(BOT_THINK_MAX * 1000).then(() => { throw new Error('timeout'); })]);
    } catch (e) {
      console.warn('local bot:', e.message, '- playing the Easy bot\'s move');
      if (e.message === 'timeout') this.startWorker(this.botSeed);   // a bot still thinking is stopped
      action = this.fallback();
    }
    if (this.closed || this.version !== version || this.toAct() !== s) return;   // the position moved under it
    try {
      try { this.act(s, action); } catch (e) {
        if (e instanceof WebAssembly.RuntimeError) throw e;
        console.error('local bot move refused:', e);
        this.act(s, this.fallback());
      }
    } catch (e) { return this.panicked(e); }
    this.wallMs.push(performance.now() - t0);
    this.push();
  }

  fallback() {   // match.py fallback_move: the greedy bot's move, else the first legal one
    try { const b = new Bot('greedy', this.seed, ''); const a = JSON.parse(b.choose(this.state)); b.free(); return a; }
    catch { return JSON.parse(this.state.legalActions())[0]; }
  }

  // ------------------------------------------------------------- the log to the server
  send({ concede }) {
    const rec = { ...this.body, seed: this.seed, first: this.state.firstPlayer, actions: this.actions, times: this.times,
      concede: !!concede, key: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}` };
    const box = this.outbox(); box.push(rec); this.saveOutbox(box);
    this.flush();
  }

  outbox() { try { return JSON.parse(localStorage.getItem(OUTBOX) || '[]'); } catch { return []; } }
  saveOutbox(box) { try { localStorage.setItem(OUTBOX, JSON.stringify(box.slice(-20))); } catch { /* no storage: sent once or lost */ } }

  async flush() {
    if (this.flushing) return this.flushing;
    this.flushing = (async () => {
      for (const rec of this.outbox()) {
        let r;
        try { r = await this.api('/api/local/match', { method: 'POST', body: JSON.stringify(rec) }); }
        catch { return; }                                   // offline: it waits for the next match
        if (!r.ok && r.status < 500) console.error('local match refused by the server:', await r.text());
        if (r.ok || r.status < 500) this.saveOutbox(this.outbox().filter(x => x.key !== rec.key));   // a refused log is dropped, never resent forever
        if (r.ok) this.lastSaved = (await r.json()).id;
      }
    })().finally(() => { this.flushing = null; });
    return this.flushing;
  }

  close() {
    this.closed = true;
    if (this.worker) this.worker.terminate();
    if (this.state) { this.state.free(); this.state = null; }
  }
}
