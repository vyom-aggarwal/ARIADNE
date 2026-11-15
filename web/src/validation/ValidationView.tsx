// Written with AI assistance (Claude Code). See AI_USE.md.
// The Validation tab (PROMPT.md section 7): renders validation.json, written by `make validate`,
// with the site-level notes first. Status is shown in words and by a shape, never by color alone.
import { CircleCheck, CircleDashed, CircleDot, CircleX, ExternalLink, type LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { REPO_URL } from "../links";
import { SiteNotes } from "../planner/AssumptionsPanel";
import type { Validation, ValidationCheck } from "../planner/types";

const STATUS: Record<string, { Icon: LucideIcon; text: string; cls: string }> = {
  pass: { Icon: CircleCheck, text: "Pass", cls: "status-pass" },
  fail: { Icon: CircleX, text: "Fail", cls: "status-fail" },
  reported: { Icon: CircleDot, text: "Reported", cls: "status-reported" },
  "not run": { Icon: CircleDashed, text: "Not run", cls: "status-not-run" },
};

/** Where the evidence for a check lives in the repository. */
const EVIDENCE: Record<string, string> = {
  "shielding-murray-buttes": "docs/derived/murray-buttes.md",
  "rover-walkability": "docs/PROGRESS.md",
  "rover-walkability-held-out": "docs/PROGRESS.md",
  thread: "docs/plan/boxwork.md",
  "station-solver": "docs/validation/station-solver.json",
  "light-time": "config/snapshots/horizons_light_time.json",
  mars24: "pipeline/tests/test_mars24.py",
  sols: "pipeline/tests/test_msl_time.py",
  "walker-model": "docs/PROGRESS.md",
};

/** A few plain facts from a check's result: top-level numbers and short strings only. */
export function resultFacts(result: unknown, max = 6): [string, string][] {
  if (!result || typeof result !== "object") return [];
  const out: [string, string][] = [];
  for (const [k, v] of Object.entries(result as Record<string, unknown>)) {
    if (out.length >= max) break;
    if (typeof v === "number") out.push([k.replace(/_/g, " "), Number.isInteger(v) ? v.toLocaleString("en-US") : v.toPrecision(4)]);
    else if (typeof v === "string" && v.trim() && v.length <= 80) out.push([k.replace(/_/g, " "), v]);
    else if (typeof v === "boolean") out.push([k.replace(/_/g, " "), v ? "yes" : "no"]);
  }
  return out;
}

function Check({ c }: { c: ValidationCheck }) {
  const s = STATUS[c.status] ?? { Icon: CircleDot, text: c.status, cls: "status-reported" };
  const facts = resultFacts(c.result);
  const evidence = EVIDENCE[c.id] ?? "validation.json";
  return (
    <li className={`check check-${c.status.replace(/\s+/g, "-")}`}>
      <p className="check-head">
        <strong>{c.title}</strong>
        <span className={`status-chip ${s.cls}`}>
          <s.Icon size={12} aria-hidden="true" />
          <span className="check-status">{s.text}</span>
        </span>
      </p>
      {c.label && <p className="unit">Label: {c.label}</p>}
      {c.target && <p className="note">What it tests: {c.target}</p>}
      {c.reason && <p className="note">{c.reason}{c.phase ? ` (Phase ${c.phase})` : ""}</p>}
      {facts.length > 0 && (
        <dl className="check-facts">
          {facts.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
      )}
      {c.note && <p className="note">{c.note}</p>}
      <p className="evidence">
        <a href={`${REPO_URL}/blob/main/${evidence}`}>
          Evidence: {evidence} <ExternalLink size={11} aria-hidden="true" />
        </a>
      </p>
    </li>
  );
}

export default function ValidationView({ site = "boxwork" }: { site?: string }) {
  const [v, setV] = useState<Validation | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let alive = true;
    fetch(`${import.meta.env.BASE_URL}sites/${site}/validation.json`)
      .then((r) => r.json())
      .then((j: Validation) => alive && setV(j))
      .catch(() => alive && setError(true));
    return () => {
      alive = false;
    };
  }, [site]);
  return (
    <section className="validation page" aria-labelledby="validation-heading">
      <h2 id="validation-heading" className="page-title">
        Validation
      </h2>
      {error && <p role="alert">validation.json could not be loaded.</p>}
      {!v && !error && <p role="status">Loading the validation results…</p>}
      {v && (
        <>
          <p className="note">
            {v.note} Pipeline {v.pipeline_version}, written {v.generated_utc}.
          </p>
          <h3>Site notes</h3>
          <SiteNotes notes={(v.site_notes ?? []).filter((n) => n.site === site)} />
          <h3>Checks</h3>
          <ul className="checks">
            {v.checks.map((c) => (
              <Check key={c.id} c={c} />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
