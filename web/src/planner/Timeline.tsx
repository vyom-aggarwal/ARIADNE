// Written with AI assistance (Claude Code). See AI_USE.md.
// Timeline of the selected plan: margin above the reserve, station blocks, sun elevation and
// comm-shadow segments, with a text summary for screen readers.
import LabelBadge from "./LabelBadge";
import type { Plan } from "./types";

const W = 760;
const H = 190;
const PAD = { l: 48, r: 48, t: 14, b: 40 };

export default function Timeline({ plan }: { plan: Plan }) {
  const tl = plan.timeline;
  const tMax = Math.max(plan.scenario.eva_max_min, ...tl.margin.map((m) => m.t_min), 1);
  const mMax = Math.max(...tl.margin.map((m) => m.margin_min), 1);
  const x = (t: number) => PAD.l + (t / tMax) * (W - PAD.l - PAD.r);
  const yM = (m: number) => PAD.t + (1 - Math.max(m, 0) / mMax) * (H - PAD.t - PAD.b);
  const sun = tl.sun_elevation_deg ?? [];
  const yS = (d: number) => PAD.t + (1 - (d + 10) / 100) * (H - PAD.t - PAD.b);
  const least = Math.min(...tl.margin.map((m) => m.margin_min));
  const blockY = H - PAD.b + 6;
  const summary =
    `Timeline: ${tl.stations.length} station visits over ${tMax.toFixed(0)} minutes; ` +
    `least margin above the reserve ${least.toFixed(0)} minutes; ` +
    `${tl.comm_shadows.length} comm shadows`;
  return (
    <section className="panel timeline" aria-labelledby="timeline-heading">
      <h2 id="timeline-heading">
        Timeline <LabelBadge label="MODELED" source="ariadne plan and Mars24 (sun elevation)" />
      </h2>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={summary} className="timeline-svg">
        <defs>
          <pattern id="shadow-hatch" width="6" height="6" patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)">
            <rect width="3" height="6" className="shadow-fill" />
          </pattern>
        </defs>
        {tl.comm_shadows.map((s, i) => (
          <rect key={`shadow-${i}`} data-shadow={i} x={x(s.start_min)} y={PAD.t}
            width={Math.max(1, x(s.end_min) - x(s.start_min))} height={H - PAD.t - PAD.b}
            fill="url(#shadow-hatch)" />
        ))}
        <line x1={PAD.l} x2={W - PAD.r} y1={H - PAD.b} y2={H - PAD.b} className="axis" />
        <line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={H - PAD.b} className="axis" />
        <polyline data-series="margin" className="margin-line" fill="none"
          points={tl.margin.map((m) => `${x(m.t_min)},${yM(m.margin_min)}`).join(" ")} />
        {sun.length > 0 && (
          <polyline data-series="sun" className="sun-line" fill="none"
            points={sun.map((s) => `${x(s.t_min)},${yS(s.deg)}`).join(" ")} />
        )}
        {tl.stations.map((s) => (
          <rect key={s.id} data-station={s.id} x={x(s.start_min)} y={blockY}
            width={Math.max(1, x(s.end_min) - x(s.start_min))} height={10} className="station-block">
            <title>{`${s.id}: ${s.start_min.toFixed(0)} to ${s.end_min.toFixed(0)} min`}</title>
          </rect>
        ))}
        <text x={PAD.l - 6} y={PAD.t + 10} textAnchor="end" className="tick">{mMax.toFixed(0)}</text>
        <text x={PAD.l - 6} y={H - PAD.b} textAnchor="end" className="tick">0</text>
        <text x={W - PAD.r + 6} y={yS(90)} className="tick">90°</text>
        <text x={W - PAD.r + 6} y={yS(0)} className="tick">0°</text>
        <text x={x(tMax)} y={H - 6} textAnchor="end" className="tick">{tMax.toFixed(0)} min</text>
        <text x={PAD.l} y={H - 6} className="tick">0 min</text>
      </svg>
      <ul className="timeline-key">
        <li><span className="key key-margin" aria-hidden="true" /> Margin above the reserve (solid line, left axis, minutes)</li>
        <li><span className="key key-sun" aria-hidden="true" /> Sun elevation (dashed line, right axis)</li>
        <li><span className="key key-station" aria-hidden="true" /> Station work (blocks along the bottom)</li>
        <li><span className="key key-shadow" aria-hidden="true" /> Out of the rover's line of sight (hatched)</li>
      </ul>
      <p className="visually-hidden">{summary}.</p>
      <p className="note">
        Least margin {least.toFixed(0)} min <LabelBadge label="MODELED" />. Start time{" "}
        {plan.scenario.start_utc ?? "not set"} <LabelBadge label="PLACEHOLDER" source={plan.scenario.start_note} />.
      </p>
    </section>
  );
}
