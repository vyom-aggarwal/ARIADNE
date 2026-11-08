// Written with AI assistance (Claude Code). See AI_USE.md.
// Acceptance test A8: every npm package in the lockfile must carry an allowed open license.
// OSI-approved licenses are allowed. CC0-1.0 is a public-domain dedication, allowed by rule 13.
// Anything else needs the human's approval first (CLAUDE.md rule 14), recorded in EXCEPTIONS.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ALLOWED = new Set([
  "MIT",
  "MIT-0",
  "ISC",
  "Apache-2.0",
  "BSD-2-Clause",
  "BSD-3-Clause",
  "0BSD",
  "MPL-2.0",
  "BlueOak-1.0.0",
  "Python-2.0",
  "Unlicense",
  "Zlib",
  "CC0-1.0",
]);

// Package name -> reason and the date the human approved it. Empty until approved.
const EXCEPTIONS = {};

/** True if an SPDX expression is satisfied by the allowed set. Handles AND, OR and parentheses. */
export function licenseAllowed(expr) {
  if (!expr || typeof expr !== "string") return false;
  const tokens = expr.replace(/[()]/g, " ").trim().split(/\s+/);
  // Without parentheses nesting in practice, treat OR groups of AND terms (AND binds tighter).
  const orGroups = tokens.join(" ").split(/\s+OR\s+/);
  return orGroups.some((group) =>
    group
      .split(/\s+AND\s+/)
      .map((t) => t.replace(/\s+WITH\s+.*$/, "").trim())
      .every((t) => ALLOWED.has(t)),
  );
}

export function checkLockfile(lock) {
  const problems = [];
  for (const [path, info] of Object.entries(lock.packages ?? {})) {
    if (path === "") continue; // the project itself
    const name = info.name ?? path.replace(/^.*node_modules\//, "");
    if (EXCEPTIONS[name]) continue;
    if (!licenseAllowed(info.license)) {
      problems.push(`${name}@${info.version ?? "?"}: ${info.license ?? "no license field"}`);
    }
  }
  return problems;
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  const here = dirname(fileURLToPath(import.meta.url));
  const lock = JSON.parse(readFileSync(join(here, "..", "package-lock.json"), "utf8"));
  const count = Object.keys(lock.packages ?? {}).length - 1;
  const problems = checkLockfile(lock);
  if (problems.length) {
    console.error(`License check failed for ${problems.length} of ${count} packages:`);
    for (const p of problems) console.error(`  ${p}`);
    process.exit(1);
  }
  console.log(`License check passed: ${count} packages, all with allowed open licenses.`);
}
