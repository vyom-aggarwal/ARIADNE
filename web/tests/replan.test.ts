// Written with AI assistance (Claude Code). See AI_USE.md.
// Test D12: re-planning on pace drift, dropping the lowest value per minute first, with a diff.
import { describe, expect, it } from "vitest";
import { checkFrom, replan } from "../src/core/plan/replan";
import type { Instance } from "../src/core/plan/solver";

// Staging (0) and four stations on a line, 10 walking minutes apart; station 2 is worth little.
function line(): Instance {
  const pos = [0, 10, 20, 30, 40];
  const minutes = pos.map((a) => pos.map((b) => Math.abs(a - b)));
  return {
    value: [0, 0.9, 0.1, 0.8, 0.7],
    minutes,
    consumables: minutes.map((row) => row.map((v) => 1.2 * v)),
    cost: minutes,
    serviceMin: [0, 15, 15, 15, 15],
    serviceCons: [0, 9, 9, 9, 9],
    evaMax: 160,
    consBudget: 200,
  };
}
const limits = { reserveMin: 30, consumablesTotal: 200, paceDriftTrigger: 0.15 };
const route = [0, 1, 2, 3, 4, 0];

describe("re-planning", () => {
  it("does nothing while the walk is on pace", () => {
    const inst = line();
    const r = replan(inst, route, { doneIndex: 1, elapsedMin: 25, consumablesUsed: 21 }, limits);
    expect(r.triggered).toBe(false);
    expect(r.route).toEqual(route);
  });

  it("triggers on more than 15% drift and drops the lowest value per minute first", () => {
    const inst = line();
    // reached station 1 after 40 min instead of 25 (60% slow)
    const r = replan(inst, route, { doneIndex: 1, elapsedMin: 40, consumablesUsed: 34 }, limits);
    expect(r.triggered).toBe(true);
    expect(r.reasons[0]).toContain("60% off plan");
    expect(r.before.time === "fail" || r.before.thread === "fail").toBe(true);
    expect(r.removed[0]).toBe(2);
    expect(r.after.time).toBe("pass");
    expect(r.after.thread).toBe("pass");
    expect(r.route[0]).toBe(0);
    expect(r.route[r.route.length - 1]).toBe(0);
    expect(r.route).not.toContain(2);
  });

  it("an alert triggers a re-check even on pace", () => {
    const inst = line();
    const r = replan(inst, route, { doneIndex: 0, elapsedMin: 0, consumablesUsed: 0, alert: true }, limits);
    expect(r.triggered).toBe(true);
    expect(r.reasons).toContain("alert");
  });

  it("the thread check uses the leg home from every node", () => {
    const inst = line();
    const c = checkFrom(inst, route, { doneIndex: 0, elapsedMin: 0, consumablesUsed: 0 }, 1, limits);
    const atFar = c.nodes.find((n) => n.node === 4)!;
    expect(atFar.cHome).toBeCloseTo(48);
    expect(c.minMargin).toBeCloseTo(Math.min(...c.nodes.map((n) => n.cLeft - n.cHome - 30)));
  });
});
