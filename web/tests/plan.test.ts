// Written with AI assistance (Claude Code). See AI_USE.md.
// Test D9: every committed plan.json validates against config/schemas/plan.schema.json.
import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import Ajv2020 from "ajv/dist/2020";
import { describe, expect, it } from "vitest";

const root = resolve(__dirname, "..", "..");
const schema = JSON.parse(readFileSync(resolve(root, "config/schemas/plan.schema.json"), "utf8"));
const planDir = resolve(root, "docs/plan");
const plans = readdirSync(planDir).filter((f) => f.endsWith(".json"));

describe("plan.json", () => {
  it("there are plans for the three presets", () => {
    for (const p of ["safest", "balanced", "most_science"])
      expect(plans.some((f) => f.endsWith(`-${p}.json`))).toBe(true);
  });

  it.each(plans)("%s validates against the schema", (file) => {
    const ajv = new Ajv2020({ allErrors: true, strict: false });
    const validate = ajv.compile(schema);
    const plan = JSON.parse(readFileSync(resolve(planDir, file), "utf8"));
    const ok = validate(plan);
    expect(validate.errors ?? []).toEqual([]);
    expect(ok).toBe(true);
  });

  it("a broken plan is rejected", () => {
    const ajv = new Ajv2020({ strict: false });
    const validate = ajv.compile(schema);
    expect(validate({ site: "boxwork" })).toBe(false);
  });
});
