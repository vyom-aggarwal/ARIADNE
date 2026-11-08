// Written with AI assistance (Claude Code). See AI_USE.md.
// Unit tests for the npm license check used by acceptance test A8.
import { describe, expect, it } from "vitest";
// @ts-expect-error: plain JavaScript module without type declarations
import { checkLockfile, licenseAllowed } from "../scripts/check-licenses.mjs";

describe("licenseAllowed", () => {
  it.each(["MIT", "Apache-2.0", "(MIT OR Apache-2.0)", "BSD-3-Clause AND MIT", "MPL-2.0"])(
    "accepts %s",
    (expr) => expect(licenseAllowed(expr)).toBe(true),
  );

  it.each(["GPL-3.0-only AND MIT", "CC-BY-NC-4.0", "UNLICENSED", "", undefined])(
    "rejects %s",
    (expr) => expect(licenseAllowed(expr)).toBe(false),
  );

  it("accepts an OR choice when one side is allowed", () => {
    expect(licenseAllowed("(GPL-2.0-only OR MIT)")).toBe(true);
  });
});

describe("checkLockfile", () => {
  it("reports packages with missing or disallowed licenses", () => {
    const lock = {
      packages: {
        "": { name: "ariadne-web" },
        "node_modules/good": { version: "1.0.0", license: "MIT" },
        "node_modules/bad": { version: "2.0.0", license: "SSPL-1.0" },
        "node_modules/none": { version: "3.0.0" },
      },
    };
    expect(checkLockfile(lock)).toEqual(["bad@2.0.0: SSPL-1.0", "none@3.0.0: no license field"]);
  });
});
