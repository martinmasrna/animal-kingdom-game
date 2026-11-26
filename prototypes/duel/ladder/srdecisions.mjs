// node srdecisions.mjs <game> [n]: for the rollout expert's decisions with a real choice,
// how often does it differ from the greedy rule, and from the plan?
import { variants } from './games/variants.js';
import { makeRng } from './bots.js';
const g = variants[process.argv[2]], n = +(process.argv[3] || 10);
const E = g.bots.roll; let real = 0, total = 0, diffRule = 0, diffPlan = 0; const byPhase = {};
for (let i = 0; i < n; i++) {
  const rng = makeRng(500 + i); let s = g.init(rng);
  while (g.winner(s) === null && s.ply < 120) {
    const ms = g.moves(s); const m = E(g, s, rng); total++;
    if (ms.length > 1) {
      real++; const r = g.bots.rule(g, s), p = g.bots.plan(g, s);
      if (m !== r) diffRule++; if (m !== p) diffPlan++;
      byPhase[s.phase] = byPhase[s.phase] || [0, 0]; byPhase[s.phase][0]++; if (m !== r) byPhase[s.phase][1]++;
    }
    s = g.play(s, m);
  }
}
console.log(`${process.argv[2]}: decisions ${total}, with a real choice ${(100 * real / total).toFixed(0)}%; of those the expert differs from the greedy rule ${(100 * diffRule / real).toFixed(0)}%, from the plan ${(100 * diffPlan / real).toFixed(0)}%`);
console.log('by phase (choices, differs from rule):', JSON.stringify(byPhase));
