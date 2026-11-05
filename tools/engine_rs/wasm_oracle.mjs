// The wasm oracle: logged human games replayed through the browser build (static/wasm, engine_rs/wasm.sh) and the Python
// engine side by side (wasm_trace.py streams the Python side), the serialised position, the legal actions and both seats'
// game views compared after every action, as oracle.py compares the Python module. The browser build is right when every
// game agrees.
//
//     node tools/engine_rs/wasm_oracle.mjs [--limit 100] [--stop]
//
// Needs the venv (.venv/bin/python) and a built static/wasm; no network, no server.
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { createInterface } from "node:readline";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const WASM = join(ROOT, "animal_kingdom/web/static/wasm");
const args = process.argv.slice(2);
const limit = args.includes("--limit") ? Number(args[args.indexOf("--limit") + 1]) : 100;
const stop = args.includes("--stop");

const ak = await import(join(WASM, "ak_engine.js"));
ak.initSync({ module: readFileSync(join(WASM, "ak_engine_bg.wasm")) });
const CARDS = readFileSync(join(ROOT, "animal_kingdom/data/cards.json"), "utf8");
const MAPS = readFileSync(join(ROOT, "animal_kingdom/data/maps.json"), "utf8");
const engines = new Map();
function engineFor(config, mapId) {
  const key = JSON.stringify(config) + mapId;
  if (!engines.has(key)) engines.set(key, new ak.Engine(CARDS, MAPS, JSON.stringify(config), mapId));
  return engines.get(key);
}

// Where two JSON values differ: the first few paths with both sides. Numbers compare by value (Python writes 1.0, Rust 1).
function diff(a, b, path = "", out = []) {
  if (out.length >= 8) return out;
  if (a && b && typeof a === "object" && typeof b === "object" && Array.isArray(a) === Array.isArray(b)) {
    if (Array.isArray(a)) {
      if (a.length !== b.length) out.push(`${path}[len] py=${a.length} wasm=${b.length}`);
      for (let i = 0; i < Math.min(a.length, b.length); i++) diff(a[i], b[i], `${path}[${i}]`, out);
    } else {
      for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) {
        if (!(k in a) || !(k in b)) out.push(`${path}.${k} py=${JSON.stringify(a[k])} wasm=${JSON.stringify(b[k])}`.slice(0, 300));
        else diff(a[k], b[k], `${path}.${k}`, out);
      }
    }
  } else if (a !== b) out.push(`${path} py=${JSON.stringify(a)} wasm=${JSON.stringify(b)}`.slice(0, 300));
  return out;
}

const py = spawn(join(ROOT, ".venv/bin/python"), [join(ROOT, "tools/engine_rs/wasm_trace.py"), "--limit", String(limit)],
  { stdio: ["ignore", "pipe", "inherit"] });
const counts = { ok: 0, fail: 0, skip: 0 };
let game = null, rs = null, failed = false, steps = 0, actions = 0;
const t0 = Date.now();

function finish() {
  if (game && !failed) counts.ok++;
}

for await (const line of createInterface({ input: py.stdout, crlfDelay: Infinity })) {
  const d = JSON.parse(line);
  if (d.skipped !== undefined) { counts.skip++; continue; }
  if (d.game) {
    finish();
    game = d.game; failed = false;
    rs = engineFor(game.config, game.map_id).newGame(JSON.stringify(game.lists[0]), JSON.stringify(game.lists[1]),
      game.seed, game.first_player, false);
    continue;
  }
  if (failed) continue;
  steps++;
  try {
    if (d.do === "skip") rs.applyAction(JSON.stringify({ kind: "choice", choice: "__skip__" }), true);
    else if (d.do !== null) { rs.applyLogged(JSON.stringify(d.do)); actions++; }
  } catch (e) {
    failed = true;
  }
  rs.takeEvents();
  const problems = failed ? [`wasm refused ${JSON.stringify(d.do)}`] : [
    ...diff(d.state, JSON.parse(rs.toJson()), "state"),
    ...diff(d.legal, JSON.parse(rs.legalActions()), "legal"),
    ...diff(d.views.A, JSON.parse(rs.view("A")), "view.A"),
    ...diff(d.views.B, JSON.parse(rs.view("B")), "view.B"),
  ];
  if (problems.length) {
    failed = true;
    counts.fail++;
    console.log(`fail ${game.match_id} game ${game.game_no} at ${d.label}:\n  ${problems.slice(0, 8).join("\n  ")}`);
    if (stop) { py.kill(); break; }
  }
}
finish();
console.log(`=== ${JSON.stringify(counts)}: ${steps} positions, ${actions} logged actions, in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
process.exitCode = counts.fail ? 1 : 0;
