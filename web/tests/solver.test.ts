// Written with AI assistance (Claude Code). See AI_USE.md.
// Test D11: the browser solver against OR-Tools on the boxwork benchmark scenarios.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { greedyInsert, type Instance, routeTotals, solve } from "../src/core/plan/solver";

const root = resolve(__dirname, "..", "..");
const bench = JSON.parse(readFileSync(resolve(__dirname, "fixtures/boxwork-bench.json"), "utf8"));

const inf = (m: (number | null)[][]) => m.map((row) => row.map((v) => (v === null ? Infinity : v)));

function instanceFor(s: { nodes: number[]; eva_max_min: number; consumables_budget: number }): Instance {
  const pick = (m: number[][]) => s.nodes.map((a) => s.nodes.map((b) => m[a][b]));
  const minutes = inf(bench.minutes);
  const consumables = inf(bench.consumables);
  const cost = inf(bench.cost);
  return {
    value: s.nodes.map((n) => bench.values[n]),
    minutes: pick(minutes),
    consumables: pick(consumables),
    cost: pick(cost),
    serviceMin: s.nodes.map((n) => bench.service_min[n] ?? Infinity),
    serviceCons: s.nodes.map((n) => bench.service_consumables_min[n] ?? Infinity),
    evaMax: s.eva_max_min,
    consBudget: s.consumables_budget,
  };
}

function bruteForce(inst: Instance): number {
  const n = inst.value.length;
  let best = 0;
  const rec = (route: number[], used: Set<number>) => {
    const t = routeTotals(inst, [...route, 0]);
    if (!t.feasible) return;
    best = Math.max(best, t.value);
    for (let k = 1; k < n; k++) if (!used.has(k)) rec([...route, k], new Set([...used, k]));
  };
  rec([0], new Set([0]));
  return best;
}

describe("browser station solver", () => {
  it("finds the optimum on small instances", () => {
    for (let seed = 0; seed < 5; seed++) {
      const s = bench.scenarios[seed];
      const nodes = s.nodes.slice(0, 7);
      const inst = instanceFor({ ...s, nodes });
      const got = solve(inst, { seed: 1 }).totals.value;
      expect(got).toBeCloseTo(bruteForce(inst), 9);
    }
  });

  it("greedy insertion alone stays feasible", () => {
    const inst = instanceFor(bench.scenarios[0]);
    expect(routeTotals(inst, greedyInsert(inst)).feasible).toBe(true);
  });

  it("reaches at least 95% of the OR-Tools value on the benchmark, every plan feasible", () => {
    expect(bench.scenarios.length).toBeGreaterThanOrEqual(50);
    const rows = bench.scenarios.map((s: any, k: number) => {
      const inst = instanceFor(s);
      const t0 = performance.now();
      const { route, totals } = solve(inst, { seed: 1 });
      const ms = performance.now() - t0;
      expect(totals.feasible).toBe(true);
      expect(route[0]).toBe(0);
      expect(route[route.length - 1]).toBe(0);
      const ref = s.ortools_value;
      const ratio = ref > 0 ? totals.value / ref : totals.value >= 0 ? 1 : 0;
      return { scenario: k, stations_offered: s.nodes.length - 1, ortools_value: ref,
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
  }, 120_000);
});
