// Written with AI assistance (Claude Code). See AI_USE.md.
/**
 * Browser station solver (PROMPT.md 5.8): pick and order stations to maximise science value
 * within the EVA time limit and the consumables budget. Node 0 is the staging point, where the
 * route starts and ends. Greedy value-per-minute insertion builds a first route; 2-opt and
 * Or-opt shorten it; insertion fills the time freed; simulated annealing (seeded) escapes local
 * optima. Benchmarked against the OR-Tools reference plans (test D11).
 *
 * Optional: `group` gives each node a group id (-1 for none) and at most one node of a group is
 * visited (one relay per transect); `end` is the node the route ends at (default 0, the start),
 * so a walk can end wherever the rover is.
 */

export interface Instance {
  value: number[];
  minutes: number[][];
  consumables: number[][];
  cost: number[][];
  serviceMin: number[];
  serviceCons: number[];
  evaMax: number;
  consBudget: number;
  group?: number[];
  end?: number;
}

export interface Totals {
  value: number;
  minutes: number;
  consumables: number;
  cost: number;
  feasible: boolean;
}

export interface SolveOptions {
  seed?: number;
  iterations?: number;
  /** Independent annealing runs (different seeds); the best is kept. */
  restarts?: number;
}

const EPS = 1e-9;

export function routeTotals(inst: Instance, route: number[]): Totals {
  let minutes = 0;
  let consumables = 0;
  let cost = 0;
  let value = 0;
  for (let k = 0; k + 1 < route.length; k++) {
    const a = route[k];
    const b = route[k + 1];
    minutes += inst.minutes[a][b];
    consumables += inst.consumables[a][b];
    cost += inst.cost[a][b];
  }
  for (let k = 1; k + 1 < route.length; k++) {
    const n = route[k];
    minutes += inst.serviceMin[n];
    consumables += inst.serviceCons[n];
    value += inst.value[n];
  }
  const feasible =
    Number.isFinite(minutes) &&
    Number.isFinite(consumables) &&
    minutes <= inst.evaMax + EPS &&
    consumables <= inst.consBudget + EPS;
  return { value, minutes, consumables, cost, feasible };
}

/** A small seeded generator (mulberry32), so runs are reproducible. */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function better(a: Totals, b: Totals): boolean {
  if (a.value > b.value + EPS) return true;
  if (a.value < b.value - EPS) return false;
  return a.minutes < b.minutes - EPS;
}

/** Best place to insert node n: the position with the smallest added minutes that stays
 * feasible, or null. */
function bestInsertion(inst: Instance, route: number[], base: Totals, n: number) {
  let best: { pos: number; dMin: number } | null = null;
  for (let k = 0; k + 1 < route.length; k++) {
    const a = route[k];
    const b = route[k + 1];
    const dMin = inst.minutes[a][n] + inst.minutes[n][b] - inst.minutes[a][b] + inst.serviceMin[n];
    const dCons =
      inst.consumables[a][n] + inst.consumables[n][b] - inst.consumables[a][b] + inst.serviceCons[n];
    if (!Number.isFinite(dMin) || !Number.isFinite(dCons)) continue;
    if (base.minutes + dMin > inst.evaMax + EPS) continue;
    if (base.consumables + dCons > inst.consBudget + EPS) continue;
    if (best === null || dMin < best.dMin) best = { pos: k + 1, dMin };
  }
  return best;
}

const endOf = (inst: Instance) => inst.end ?? 0;

/** Nodes that may still join a route: not the start or end, not in it, and not in a group the
 * route already visits. */
function open(inst: Instance, route: number[]): number[] {
  const inRoute = new Set(route);
  const groups = new Set(
    route.map((n) => inst.group?.[n] ?? -1).filter((g) => g >= 0),
  );
  const out: number[] = [];
  for (let n = 1; n < inst.value.length; n++) {
    if (n === endOf(inst) || inRoute.has(n)) continue;
    const g = inst.group?.[n] ?? -1;
    if (g >= 0 && groups.has(g)) continue;
    out.push(n);
  }
  return out;
}

/** Repeatedly insert the station with the highest value per added minute. */
export function greedyInsert(inst: Instance, start?: number[]): number[] {
  const route = start ? [...start] : [0, endOf(inst)];
  for (;;) {
    const base = routeTotals(inst, route);
    let pick: { n: number; pos: number; ratio: number } | null = null;
    for (const n of open(inst, route)) {
      const ins = bestInsertion(inst, route, base, n);
      if (!ins) continue;
      const ratio = inst.value[n] / Math.max(ins.dMin, 1e-6);
      if (pick === null || ratio > pick.ratio) pick = { n, pos: ins.pos, ratio };
    }
    if (!pick) return route;
    route.splice(pick.pos, 0, pick.n);
  }
}

/** 2-opt: reverse inner segments while that shortens the route (and keeps it feasible). */
export function twoOpt(inst: Instance, route: number[]): number[] {
  let r = [...route];
  let cur = routeTotals(inst, r);
  let improved = true;
  while (improved) {
    improved = false;
    for (let i = 1; i < r.length - 2; i++) {
      for (let j = i + 1; j < r.length - 1; j++) {
        const cand = [...r.slice(0, i), ...r.slice(i, j + 1).reverse(), ...r.slice(j + 1)];
        const t = routeTotals(inst, cand);
        if (t.feasible && t.minutes < cur.minutes - EPS) {
          r = cand;
          cur = t;
          improved = true;
        }
      }
    }
  }
  return r;
}

/** Or-opt: move runs of 1 to 3 stations elsewhere while that shortens the route. */
export function orOpt(inst: Instance, route: number[]): number[] {
  let r = [...route];
  let cur = routeTotals(inst, r);
  let improved = true;
  while (improved) {
    improved = false;
    for (let len = 1; len <= 3; len++) {
      for (let i = 1; i + len < r.length; i++) {
        const seg = r.slice(i, i + len);
        const rest = [...r.slice(0, i), ...r.slice(i + len)];
        for (let p = 1; p < rest.length; p++) {
          if (p === i) continue;
          const cand = [...rest.slice(0, p), ...seg, ...rest.slice(p)];
          const t = routeTotals(inst, cand);
          if (t.feasible && t.minutes < cur.minutes - EPS) {
            r = cand;
            cur = t;
            improved = true;
            break;
          }
        }
        if (improved) break;
      }
      if (improved) break;
    }
  }
  return r;
}

function polish(inst: Instance, route: number[]): number[] {
  let r = route;
  for (let pass = 0; pass < 3; pass++) {
    const before = routeTotals(inst, r);
    r = greedyInsert(inst, orOpt(inst, twoOpt(inst, r)));
    if (!better(routeTotals(inst, r), before)) break;
  }
  return r;
}

/** Greedy, 2-opt, Or-opt, then simulated annealing over remove, insert, swap and reverse moves,
 * restarted with different seeds; the best route is kept. */
export function solve(inst: Instance, opts: SolveOptions = {}): { route: number[]; totals: Totals } {
  const restarts = Math.max(1, opts.restarts ?? 8);
  let best: { route: number[]; totals: Totals } | null = null;
  for (let k = 0; k < restarts; k++) {
    const run = solveOnce(inst, (opts.seed ?? 1) + 7919 * k, opts.iterations ?? 4000);
    if (best === null || better(run.totals, best.totals)) best = run;
  }
  return best!;
}

function solveOnce(inst: Instance, seed: number, iterations: number) {
  const rand = rng(seed);
  const iters = iterations;
  let cur = polish(inst, greedyInsert(inst));
  let curT = routeTotals(inst, cur);
  let best = cur;
  let bestT = curT;
  const vmax = Math.max(1e-6, ...inst.value);
  let temp = 0.3 * vmax;
  const cool = Math.pow(1e-3, 1 / Math.max(1, iters));
  for (let it = 0; it < iters; it++, temp *= cool) {
    const cand = [...cur];
    const move = rand();
    const inner = cand.length - 2;
    if (move < 0.25 && inner > 0) {
      cand.splice(1 + Math.floor(rand() * inner), 1); // remove a station
    } else if (move < 0.85) {
      // insert an unvisited station at its cheapest feasible place, after removing one visited
      // station for a swap (60% of these moves) when the route has any
      if (move >= 0.45 && inner > 0) cand.splice(1 + Math.floor(rand() * inner), 1);
      const out = open(inst, cand);
      if (out.length === 0) continue;
      const node = out[Math.floor(rand() * out.length)];
      const ins = bestInsertion(inst, cand, routeTotals(inst, cand), node);
      if (!ins) continue;
      cand.splice(ins.pos, 0, node);
    } else if (inner > 1) {
      const i = 1 + Math.floor(rand() * inner);
      const j = 1 + Math.floor(rand() * inner);
      const [a, b] = i < j ? [i, j] : [j, i];
      const mid = cand.slice(a, b + 1).reverse();
      cand.splice(a, mid.length, ...mid);
    } else continue;
    const t = routeTotals(inst, cand);
    if (!t.feasible) continue;
    const route = cand;
    const delta = t.value - curT.value - 1e-4 * (t.minutes - curT.minutes) / Math.max(1, inst.evaMax);
    if (delta >= 0 || rand() < Math.exp(delta / Math.max(temp, 1e-12))) {
      cur = route;
      curT = t;
      if (better(curT, bestT)) {
        best = cur;
        bestT = curT;
      }
    }
  }
  best = polish(inst, best);
  return { route: best, totals: routeTotals(inst, best) };
}
