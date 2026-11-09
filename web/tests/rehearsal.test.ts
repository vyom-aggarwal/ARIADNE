// Written with AI assistance (Claude Code). See AI_USE.md.
// Test E9: 3D rehearsal geometry (level of detail, billboard facing, eye height).
import { describe, expect, it } from "vitest";
import {
  billboardPose,
  eyePosition,
  groundHeight,
  lodLevel,
  pointAlong,
  toLocal,
} from "../src/rehearsal/geometry";

describe("rehearsal geometry", () => {
  it("uses the fine chunks near the camera and the coarse ones far away", () => {
    expect(lodLevel(100, 300)).toBe("fine");
    expect(lodLevel(500, 300)).toBe("coarse");
  });

  it("maps site metres to scene coordinates (x east, z south, y up)", () => {
    const origin: [number, number] = [1000, 2000];
    expect(toLocal([1010, 2030], origin)).toEqual([10, -30]);
  });

  it("places a billboard ahead along the view direction, facing back toward the camera", () => {
    for (const az of [0, 90, 200]) {
      const p = billboardPose([0, 0], az, 20);
      const a = (az * Math.PI) / 180;
      expect(p.x).toBeCloseTo(20 * Math.sin(a));
      expect(p.z).toBeCloseTo(-20 * Math.cos(a));
      // the plane's normal (sin r, 0, cos r) points from the billboard back to the camera
      const nx = Math.sin(p.rotationY);
      const nz = Math.cos(p.rotationY);
      expect(nx * -p.x + nz * -p.z).toBeGreaterThan(19.99);
    }
  });

  it("keeps the walker's eye 1.7 m above the terrain", () => {
    // 3 x 3 height posts 2 m apart (x east from `west`, scene z south from `north`), rising
    // 0.1 m per metre eastward
    const grid = { heights: [0, 0.2, 0.4, 0, 0.2, 0.4, 0, 0.2, 0.4], cols: 3, rows: 3, cell: 2,
      west: 0, north: 0 };
    expect(groundHeight(grid, 1, 1)).toBeCloseTo(0.1);
    expect(eyePosition(grid, 3, 2, 1.7).y).toBeCloseTo(0.3 + 1.7);
  });

  it("walks a route at a given distance along it", () => {
    const route: [number, number][] = [[0, 0], [10, 0], [10, 10]];
    expect(pointAlong(route, 15)).toEqual([10, 5]);
    expect(pointAlong(route, 100)).toEqual([10, 10]);
  });
});
