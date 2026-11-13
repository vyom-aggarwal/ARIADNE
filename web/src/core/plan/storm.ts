// Written with AI assistance (Claude Code). See AI_USE.md.
/**
 * Storm mode (PROMPT.md 5.11; team decision of 2026-11-10): on a solar-particle alert the crew
 * goes to the refuge with the lowest modeled dose over the event, counting the exposed walk
 * there, not to the earliest arrival. Refuges are the rover where it is parked (shielding S a
 * labeled PLACEHOLDER), the nearest terrain shielding zone (its own S) and staying put.
 *
 * Doses are relative, in open-sky minutes (one minute under an open sky at S = 1 counts 1). The
 * pipeline (pipeline/ariadne/plan/storm.py) precomputes a response every few minutes along each
 * plan; this module reads them and holds the same dose rule, so both agree. Every dose is
 * MODELED; the event length stays PLACEHOLDER until Phase 6 replays May 2024.
 */

/** The 16 moves, in the pipeline's order (pipeline/ariadne/plan/graph.py OFFSETS). */
export const OFFSETS: ReadonlyArray<readonly [number, number]> = [
  [0, 1], [1, 0], [0, -1], [-1, 0],
  [1, 1], [1, -1], [-1, 1], [-1, -1],
  [1, 2], [2, 1], [-1, 2], [-2, 1], [1, -2], [2, -1], [-1, -2], [-2, -1],
];

export interface PointerField {
  width: number;
  height: number;
  /** Index into OFFSETS of the move that brought the search here; -1 at the refuge. */
  pointer: ArrayLike<number>;
}

/** Cells from `start` to the refuge its pointers lead to. The pointer of a cell names the move
 * from the next cell into it, so the next cell is the cell minus that move. */
export function followPointers(field: PointerField, start: [number, number]): [number, number][] {
  const out: [number, number][] = [start];
  let [r, c] = start;
  for (let guard = 0; guard < field.width * field.height; guard++) {
    const p = field.pointer[r * field.width + c];
    if (p < 0) return out;
    const [dr, dc] = OFFSETS[p];
    r -= dr;
    c -= dc;
    out.push([r, c]);
  }
  throw new Error("storm pointers loop");
}

/** Relative dose over an event of `durationMin`: the exposed walk (walkDose, the sum of S x dt
 * along it), then the rest of the event at the refuge's S; a walk longer than the event is cut
 * at the event's end. */
export function eventDose(walkMin: number, walkDose: number, sDest: number, durationMin: number): number {
  if (walkMin <= durationMin) return walkDose + (durationMin - walkMin) * sDest;
  return walkMin > 0 ? (walkDose * durationMin) / walkMin : 0;
}

export interface RefugeOption {
  name: "stay" | "rover" | "terrain";
  walkMin: number;
  walkDose: number;
  sDest: number;
}

/** The option with the lowest event dose; ties go to the shorter walk. Unreachable options
 * (infinite or missing walk) are skipped. */
export function chooseRefuge(options: RefugeOption[], durationMin: number): RefugeOption & { dose: number } {
  const scored = options
    .filter((o) => Number.isFinite(o.walkMin))
    .map((o) => ({ ...o, dose: eventDose(o.walkMin, o.walkDose, o.sDest, durationMin) }));
  scored.sort((a, b) => a.dose - b.dose || a.walkMin - b.walkMin);
  return scored[0];
}

export interface StormSample {
  t_min: number;
  xy_m: [number, number];
  rover_relay: number;
  rover_moving: boolean;
  choice: "stay" | "rover" | "terrain";
  walk_min: number;
  s_dest: number;
  dose: number;
  dose_staying: number;
  dose_avoided: number;
  path_xy_m: [number, number][];
  /** The line home: the fastest walk to where the rover parks next (the abort route). */
  home_relay?: number;
  home_walk_min?: number;
  home_path_xy_m?: [number, number][];
}

export interface PlanStorm {
  label: "MODELED";
  event_duration_min: number;
  rover_s: number;
  placeholders: string[];
  note: string;
  samples: StormSample[];
}

/** The storm response in force at plan time tMin: the latest precomputed sample at or before
 * it (the first sample before the plan starts), or null when the plan has none. */
export function stormAt(storm: PlanStorm | null | undefined, tMin: number): StormSample | null {
  const s = storm?.samples ?? [];
  if (s.length === 0) return null;
  let lo = 0;
  let hi = s.length - 1;
  if (tMin <= s[0].t_min) return s[0];
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (s[mid].t_min <= tMin) lo = mid;
    else hi = mid - 1;
  }
  return s[lo];
}

/** Plain-English name of a refuge choice, for the HUD, tablet and card. */
export function refugeName(choice: StormSample["choice"]): string {
  return choice === "rover" ? "the rover" : choice === "terrain" ? "terrain shielding" : "stay put";
}
