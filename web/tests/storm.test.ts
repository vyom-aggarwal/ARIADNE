// Written with AI assistance (Claude Code). See AI_USE.md.
// Test E12 (storm mode by lowest modeled dose, team decision of 2026-11-10).
import { describe, expect, it } from "vitest";
import {
  chooseRefuge,
  eventDose,
  followPointers,
  OFFSETS,
  type PlanStorm,
  type PointerField,
  stormAt,
} from "../src/core/plan/storm";

// A 1 x 7 corridor with refuges at both ends; pointers lead each cell to the nearer end.
function corridor(): PointerField {
  const west = OFFSETS.findIndex(([r, c]) => r === 0 && c === -1); // move west into a cell
  const east = OFFSETS.findIndex(([r, c]) => r === 0 && c === 1);
  // a cell reached by moving east came from the west, so its pointer leads back west
  return { width: 7, height: 1, pointer: [-1, east, east, east, west, west, -1] };
}

describe("storm mode", () => {
  it("follows the pointers to the refuge they lead to", () => {
    const f = corridor();
    expect(followPointers(f, [0, 2])).toEqual([[0, 2], [0, 1], [0, 0]]);
    expect(followPointers(f, [0, 4])).toEqual([[0, 4], [0, 5], [0, 6]]);
    expect(followPointers(f, [0, 6])).toEqual([[0, 6]]);
  });

  it("uses the same 16 moves as the pipeline", () => {
    expect(OFFSETS).toHaveLength(16);
    expect(OFFSETS[8]).toEqual([1, 2]);
  });

  it("counts the exposed walk, then the rest of the event at the refuge (as the pipeline does)", () => {
    expect(eventDose(10, 10, 0.5, 120)).toBeCloseTo(10 + 110 * 0.5);
    expect(eventDose(240, 200, 0.5, 120)).toBeCloseTo(100); // cut at the event's end
    expect(eventDose(0, 0, 0.9, 120)).toBeCloseTo(108); // staying put
  });

  it("chooses the lowest dose, not the earliest arrival", () => {
    const options = [
      { name: "stay" as const, walkMin: 0, walkDose: 0, sDest: 1.0 },
      { name: "terrain" as const, walkMin: 2, walkDose: 2, sDest: 0.9 },
      { name: "rover" as const, walkMin: 15, walkDose: 15, sDest: 0.5 },
    ];
    expect(chooseRefuge(options, 120).name).toBe("rover");
    expect(chooseRefuge(options, 10).name).toBe("terrain");
    const far = [options[0], { ...options[2], walkMin: 300, walkDose: 300 }];
    expect(chooseRefuge(far, 120).name).toBe("stay");
    const unreachable = [options[0], { ...options[2], walkMin: Infinity }];
    expect(chooseRefuge(unreachable, 120).name).toBe("stay");
  });

  it("reads the precomputed response in force at a plan time", () => {
    const sample = (t: number) => ({
      t_min: t, xy_m: [0, 0] as [number, number], rover_relay: 0, rover_moving: false,
      choice: "rover" as const, walk_min: 1, s_dest: 0.5, dose: 60, dose_staying: 120,
      dose_avoided: 60, path_xy_m: [],
    });
    const storm: PlanStorm = {
      label: "MODELED", event_duration_min: 120, rover_s: 0.5, placeholders: [], note: "",
      samples: [sample(0), sample(5), sample(10)],
    };
    expect(stormAt(storm, -1)?.t_min).toBe(0);
    expect(stormAt(storm, 4.9)?.t_min).toBe(0);
    expect(stormAt(storm, 5)?.t_min).toBe(5);
    expect(stormAt(storm, 99)?.t_min).toBe(10);
    expect(stormAt(null, 3)).toBeNull();
  });
});
