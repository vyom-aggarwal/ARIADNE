// Written with AI assistance (Claude Code). See AI_USE.md.
// Test D11: the browser solver against the time-limited OR-Tools reference on the boxwork
// relay scenarios: (transect, relay) nodes, at most one per transect, ending at the rover.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { greedyInsert, type Instance, routeTotals, solve } from "../src/core/plan/solver";

const root = resolve(__dirname, "..", "..");
const bench = JSON.parse(readFileSync(resolve(__dirname, "fixtures/boxwork-bench.json"), "utf8"));

const inf = (m: (number | null)[][]) => m.map((row) => row.map((v) => (v === null ? Infinity : v)));
const minutes = inf(bench.minutes);
const consumables = inf(bench.consumables);
const cost = inf(bench.cost);

function instanceFor(s: { nodes: number[]; eva_max_min: number; consumables_budget: number }): Instance {
  const pick = (m: number[][]) => s.nodes.map((a) => s.nodes.map((b) => m[a][b]));
  return {
    value: s.nodes.map((n) => bench.values[n]),
    minutes: pick(minutes),
    consumables: pick(consumables),
    cost: pick(cost),
    serviceMin: s.nodes.map((n) => bench.service_min[n]),
    serviceCons: s.nodes.map((n) => bench.service_consumables_min[n]),
    evaMax: s.eva_max_min,
    consBudget: s.consumables_budget,
    group: s.nodes.map((n) => bench.group[n]),
    end: s.nodes.indexOf(bench.end_node),
  };
}

function bruteForce(inst: Instance): number {
  const end = inst.end ?? 0;
  let best = 0;
  const rec = (route: number[]) => {
    const t = routeTotals(inst, [...route, end]);
    if (!t.feasible) return;
    best = Math.max(best, t.value);
    const groups = new Set(route.map((n) => inst.group?.[n] ?? -1).filter((g) => g >= 0));
    for (let k = 1; k < inst.value.length; k++) {
      if (k === end || route.includes(k)) continue;
      const g = inst.group?.[k] ?? -1;
      if (g >= 0 && groups.has(g)) continue;
      rec([...route, k]);
    }
  };
  rec([0]);
  return best;
}

describe("browser station solver", () => {
  it("finds the optimum on small instances, at most one node per group, ending at the end node", () => {
    for (let k = 0; k < 5; k++) {
      const s = bench.scenarios[k];
      const nodes = [...s.nodes.slice(0, 7), bench.end_node];
      const inst = instanceFor({ ...s, nodes });
      const { route, totals } = solve(inst, { seed: 1 });
      expect(route[route.length - 1]).toBe(inst.end);
      const groups = route.slice(1, -1).map((n) => inst.group![n]);
      expect(new Set(groups).size).toBe(groups.length);
      expect(totals.value).toBeCloseTo(bruteForce(inst), 9);
    }
  });

  it("greedy insertion alone stays feasible", () => {
    const inst = instanceFor(bench.scenarios[0]);
    expect(routeTotals(inst, greedyInsert(inst)).feasible).toBe(true);
  });

  it("reaches at least 95% of the time-limited OR-Tools value on average, every plan feasible", () => {
    expect(bench.scenarios.length).toBeGreaterThanOrEqual(50);
    const rows = bench.scenarios.map((s: any, k: number) => {
      const inst = instanceFor(s);
      const t0 = performance.now();
      const { route, totals } = solve(inst, { seed: 1 });
      const ms = performance.now() - t0;
      expect(totals.feasible).toBe(true);
      expect(route[0]).toBe(0);
      expect(route[route.length - 1]).toBe(inst.end);
      const ref = s.ortools_value;
      const ratio = ref > 0 ? totals.value / ref : 1;
      return { scenario: k, nodes_offered: s.nodes.length - 2, ortools_value: ref,
        browser_value: Number(totals.value.toFixed(6)), ratio: Number(ratio.toFixed(4)),
        browser_ms: Number(ms.toFixed(1)) };
    });
    const mean = rows.reduce((a: number, r: any) => a + r.ratio, 0) / rows.length;
    const min = Math.min(...rows.map((r: any) => r.ratio));
    if (process.env.BENCH_OUT) {
      const out = resolve(root, process.env.BENCH_OUT);
      mkdirSync(dirname(out), { recursive: true });
      writeFileSync(out, JSON.stringify({ scenarios: rows.length, mean_ratio: Number(mean.toFixed(4)),
        min_ratio: min, target: 0.95,
        reference: `OR-Tools guided local search, ${bench.ortools_time_limit_s} s per scenario: ` +
          "a time-limited reference, not a proven optimum",
        pipeline_version: bench.pipeline_version, rows }, null, 1) + "\n");
    }
    expect(mean).toBeGreaterThanOrEqual(0.95);
  }, 180_000);
});
