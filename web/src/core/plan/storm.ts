// Written with AI assistance (Claude Code). See AI_USE.md.
/**
 * Storm mode (PROMPT.md 5.11). The pipeline runs Dijkstra on walking time from every shelter
 * (terrain shelters and the rover) on the reversed graph and stores, for each cell, the move
 * toward the earliest arrival, ties going to the lower shielding index S. Here we follow those
 * pointers from the walker's cell. The dose avoided is MODELED; its inputs stay PLACEHOLDER until
 * Phase 6 brings replay data.
 */

/** The 16 moves, in the pipeline's order (pipeline/ariadne/plan/graph.py OFFSETS). */
export const OFFSETS: ReadonlyArray<readonly [number, number]> = [
  [0, 1], [1, 0], [0, -1], [-1, 0],
  [1, 1], [1, -1], [-1, 1], [-1, -1],
  [1, 2], [2, 1], [-1, 2], [-2, 1], [1, -2], [2, -1], [-1, -2], [-2, -1],
];

export interface StormField {
  width: number;
  height: number;
  /** Index into OFFSETS of the move that brought the search here; -1 at shelters. */
  pointer: ArrayLike<number>;
  /** Walking minutes to the shelter reached. */
  minutes: ArrayLike<number>;
}

/** Cells from `start` to the shelter its pointers lead to. The pointer of a cell names the move
 * from the next cell into it, so the next cell is the cell minus that move. */
export function followPointers(field: StormField, start: [number, number]): [number, number][] {
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

export interface DoseAvoided {
  withoutShelter: number;
  withShelter: number;
  avoided: number;
  label: "MODELED";
  inputs: "PLACEHOLDER" | "MEASURED";
}

/** Dose over an event lasting durationMin minutes: staying in the open at the walker's spot
 * (S here) against walking walkMin minutes to the shelter (S here on the way, a simplification)
 * and sheltering for the rest (S of the shelter). eventDoseOpen is the event's dose under an
 * open sky over the whole event. */
export function doseAvoided(
  eventDoseOpen: number,
  durationMin: number,
  walkMin: number,
  sHere: number,
  sShelter: number,
  inputs: "PLACEHOLDER" | "MEASURED" = "PLACEHOLDER",
): DoseAvoided {
  const rate = eventDoseOpen / durationMin;
  const walk = Math.min(walkMin, durationMin);
  const withoutShelter = rate * durationMin * sHere;
  const withShelter = rate * (walk * sHere + (durationMin - walk) * sShelter);
  return { withoutShelter, withShelter, avoided: withoutShelter - withShelter, label: "MODELED", inputs };
}
