// The bot of a match played in the browser (local/match.js), thinking in its own thread so the screen never waits on it.
// One bot a game, kept across its moves as the server keeps it (its plans and random streams carry over). Messages in:
// {t: 'init', module (the compiled wasm), doc (/api/local/engine), spec, evaluator, cand (the candidate network's artifact, for a spec with cand=), seed}; {t: 'choose', id, state (the
// position as the engine serialises it)}. Out: {t: 'ready'}; {t: 'chose', id, action, ms}; {t: 'error', id, error}.
import init, { Engine, Bot } from '../wasm/ak_engine.js';

let engine = null, bot = null;

onmessage = async ({ data: m }) => {
  try {
    if (m.t === 'init') {
      await init({ module_or_path: m.module });
      engine = new Engine(JSON.stringify(m.doc.cards), JSON.stringify(m.doc.maps), JSON.stringify(m.doc.config), m.doc.map_id);
      bot = new Bot(m.spec, m.seed, m.evaluator || '', m.cand || undefined);
      postMessage({ t: 'ready' });
    } else if (m.t === 'choose') {
      const t0 = performance.now();
      const st = engine.fromJson(m.state);
      const action = bot.choose(st);
      st.free();
      postMessage({ t: 'chose', id: m.id, action: JSON.parse(action), ms: performance.now() - t0 });
    }
  } catch (e) {
    postMessage({ t: 'error', id: m.id, error: String(e && e.message || e) });
  }
};
