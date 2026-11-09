// Written with AI assistance (Claude Code). See AI_USE.md.
/**
 * Planner Web Worker: runs the station solver and re-planning off the main thread, so the
 * interface never freezes. Messages: {kind: "solve", instance, seed?} and
 * {kind: "replan", instance, route, state, limits}.
 */

import { type Limits, replan, type WalkState } from "../core/plan/replan";
import { type Instance, solve } from "../core/plan/solver";

export type PlannerRequest =
  | { kind: "solve"; instance: Instance; seed?: number; iterations?: number }
  | { kind: "replan"; instance: Instance; route: number[]; state: WalkState; limits: Limits };

export function handle(req: PlannerRequest) {
  if (req.kind === "solve") return solve(req.instance, { seed: req.seed, iterations: req.iterations });
  return replan(req.instance, req.route, req.state, req.limits);
}

// In a worker, answer each message; in tests this module is imported for `handle` only.
const scope = globalThis as unknown as {
  postMessage?: (m: unknown) => void;
  onmessage?: ((e: MessageEvent<PlannerRequest>) => void) | null;
  WorkerGlobalScope?: unknown;
};
if (typeof scope.WorkerGlobalScope !== "undefined" && scope.postMessage) {
  scope.onmessage = (e) => scope.postMessage?.(handle(e.data));
}
