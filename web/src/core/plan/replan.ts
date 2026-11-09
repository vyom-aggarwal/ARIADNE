// Written with AI assistance (Claude Code). See AI_USE.md.
/**
 * Re-planning during the walk (PROMPT.md 5.10) and the leg-level constraint check.
 *
 * Triggers: pace drifting more than the threshold (PLACEHOLDER 15%) from plan, a margin crossing
 * its threshold, or an alert. The rest of the route is projected at the observed pace (minutes
 * and consumables of the remaining legs and station work scale with it); while any check fails,
 * the remaining station with the lowest value per minute is dropped. The thread is checked at
 * every node: consumables left minus the consumables of the leg straight home from that node must
 * stay at or above the reserve. The pipeline's plan.json margins check it every 5 m.
 */

import { type Instance, routeTotals } from "./solver";

export interface Limits {
  reserveMin: number;
  consumablesTotal: number;
  paceDriftTrigger: number;
}

export interface WalkState {
  /** Index in the route of the last node reached (0 = still at staging). */
  doneIndex: number;
  /** Minutes elapsed since the start. */
  elapsedMin: number;
  /** Consumables used so far (minutes at the nominal rate). */
  consumablesUsed: number;
  alert?: boolean;
}

export interface NodeCheck {
  node: number;
  tMin: number;
  cLeft: number;
  cHome: number;
}

export interface Check {
  thread: "pass" | "fail";
  time: "pass" | "fail";
  minMargin: number;
  endMinutes: number;
  nodes: NodeCheck[];
}

/** Planned minutes and consumables up to and including the node at route index k. */
function plannedTo(inst: Instance, route: number[], k: number) {
  let t = 0;
  let c = 0;
  for (let i = 0; i < k; i++) {
    t += inst.minutes[route[i]][route[i + 1]];
    c += inst.consumables[route[i]][route[i + 1]];
    if (i + 1 < route.length - 1) {
      t += inst.serviceMin[route[i + 1]];
      c += inst.serviceCons[route[i + 1]];
    }
  }
  return { t, c };
}

/** Check the rest of a route from the current state, at a pace factor (1 = as planned). */
export function checkFrom(
  inst: Instance,
  route: number[],
  state: WalkState,
  pace: number,
  limits: Limits,
): Check {
  let t = state.elapsedMin;
  let used = state.consumablesUsed;
  let minMargin = Infinity;
  const nodes: NodeCheck[] = [];
  const at = (k: number) => {
    const node = route[k];
    const cLeft = limits.consumablesTotal - used;
    const cHome = node === 0 ? 0 : inst.consumables[node][0];
    minMargin = Math.min(minMargin, cLeft - cHome - limits.reserveMin);
    nodes.push({ node, tMin: t, cLeft, cHome });
  };
  at(state.doneIndex);
  for (let k = state.doneIndex; k + 1 < route.length; k++) {
    const a = route[k];
    const b = route[k + 1];
    t += pace * inst.minutes[a][b];
    used += pace * inst.consumables[a][b];
    if (k + 1 < route.length - 1) {
      t += pace * inst.serviceMin[b];
      used += pace * inst.serviceCons[b];
    }
    at(k + 1);
  }
  return {
    thread: minMargin >= -1e-9 ? "pass" : "fail",
    time: t <= inst.evaMax + 1e-9 ? "pass" : "fail",
    minMargin,
    endMinutes: t,
    nodes,
  };
}

export interface ReplanResult {
  triggered: boolean;
  reasons: string[];
  paceDrift: number;
  route: number[];
  removed: number[];
  before: Check;
  after: Check;
}

/** Re-plan if a trigger fires: drop the lowest value-per-minute stations until every check
 * passes, and report what changed. */
export function replan(
  inst: Instance,
  route: number[],
  state: WalkState,
  limits: Limits,
): ReplanResult {
  const planned = plannedTo(inst, route, state.doneIndex);
  const paceDrift = planned.t > 0 ? state.elapsedMin / planned.t - 1 : 0;
  const pace = Math.max(1, 1 + paceDrift); // only slow-downs lengthen the rest
  const before = checkFrom(inst, route, state, pace, limits);
  const reasons: string[] = [];
  if (Math.abs(paceDrift) > limits.paceDriftTrigger)
    reasons.push(`pace is ${(100 * paceDrift).toFixed(0)}% off plan`);
  if (before.thread === "fail") reasons.push("the thread margin would fall below the reserve");
  if (before.time === "fail") reasons.push("the walk would run past the EVA limit");
  if (state.alert) reasons.push("alert");
  let r = [...route];
  const removed: number[] = [];
  let after = before;
  if (reasons.length > 0) {
    while (after.thread === "fail" || after.time === "fail") {
      let pick = -1;
      let worst = Infinity;
      for (let k = state.doneIndex + 1; k < r.length - 1; k++) {
        const a = r[k - 1];
        const n = r[k];
        const b = r[k + 1];
        const saved =
          inst.minutes[a][n] + inst.minutes[n][b] - inst.minutes[a][b] + inst.serviceMin[n];
        const perMin = inst.value[n] / Math.max(saved, 1e-6);
        if (perMin < worst) {
          worst = perMin;
          pick = k;
        }
      }
      if (pick < 0) break; // nothing left to drop: head home
      removed.push(r[pick]);
      r = [...r.slice(0, pick), ...r.slice(pick + 1)];
      after = checkFrom(inst, r, state, pace, limits);
    }
  }
  return { triggered: reasons.length > 0, reasons, paceDrift, route: r, removed, before, after };
}

export { routeTotals };
