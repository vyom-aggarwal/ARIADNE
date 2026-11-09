// Written with AI assistance (Claude Code). See AI_USE.md.
// Test D12 (storm mode): following the pipeline's pointers to the earliest shelter.
import { describe, expect, it } from "vitest";
import { doseAvoided, followPointers, OFFSETS, type StormField } from "../src/core/plan/storm";

// A 1 x 7 corridor with shelters at both ends; pointers lead each cell to the nearer end.
function corridor(): StormField {
  const west = OFFSETS.findIndex(([r, c]) => r === 0 && c === -1); // move west into a cell
  const east = OFFSETS.findIndex(([r, c]) => r === 0 && c === 1);
  // a cell reached by moving east came from the west, so its pointer leads back west
  const pointer = [-1, east, east, east, west, west, -1];
  return { width: 7, height: 1, pointer, minutes: [0, 1, 2, 3, 2, 1, 0] };
}

describe("storm mode", () => {
  it("follows the pointers to the shelter they lead to", () => {
    const f = corridor();
    expect(followPointers(f, [0, 2])).toEqual([[0, 2], [0, 1], [0, 0]]);
    expect(followPointers(f, [0, 4])).toEqual([[0, 4], [0, 5], [0, 6]]);
    expect(followPointers(f, [0, 6])).toEqual([[0, 6]]);
  });

  it("uses the same 16 moves as the pipeline", () => {
    expect(OFFSETS).toHaveLength(16);
    expect(OFFSETS[8]).toEqual([1, 2]);
  });

  it("labels the dose avoided as modeled, counting the walk to shelter", () => {
    const d = doseAvoided(1000, 60, 6, 1.0, 0.5);
    expect(d.withoutShelter).toBeCloseTo(1000);
    expect(d.withShelter).toBeCloseTo(100 + 450);
    expect(d.avoided).toBeCloseTo(450);
    expect(d.label).toBe("MODELED");
    expect(d.inputs).toBe("PLACEHOLDER");
  });
});
