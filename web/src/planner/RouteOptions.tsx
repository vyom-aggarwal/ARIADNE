// Written with AI assistance (Claude Code). See AI_USE.md.
// The three route options side by side (PROMPT.md section 6), every number labeled.
import LabelBadge from "./LabelBadge";
import { type Plan, PRESET_TITLES, type Totals } from "./types";

interface Props {
  plans: Record<string, Plan>;
  selected: string;
  onSelect: (preset: string) => void;
}

const ORDER = ["safest", "balanced", "most_science"];
const SOURCE =
  "Modeled by ariadne plan: walker model (Minetti et al. 2002 with PLACEHOLDER suit settings), " +
  "PLACEHOLDER presets and scenario (config/presets.json).";

const ROWS: { name: string; unit: string; value: (t: Totals) => string }[] = [
  { name: "Duration", unit: "min", value: (t) => t.minutes.toFixed(0) },
  { name: "Distance", unit: "m", value: (t) => Math.round(t.distance_m).toLocaleString("en-US") },
  { name: "Consumables used", unit: "min at nominal rate", value: (t) => t.consumables_min.toFixed(0) },
  { name: "Least margin above reserve", unit: "min", value: (t) => t.min_thread_margin_min.toFixed(1) },
  { name: "Worst time to shelter", unit: "min", value: (t) => t.worst_minutes_to_shelter.toFixed(1) },
  { name: "Relative dose", unit: "open-sky minutes", value: (t) => t.relative_dose_min.toFixed(0) },
  { name: "Stations (transects)", unit: "", value: (t) => `${t.stations} (${t.transects})` },
  { name: "Science value", unit: "sum of station scores", value: (t) => t.science_value.toFixed(2) },
];

export default function RouteOptions({ plans, selected, onSelect }: Props) {
  const presets = ORDER.filter((p) => plans[p]);
  return (
    <section className="panel route-options" aria-labelledby="routes-heading">
      <h2 id="routes-heading">Route options</h2>
      <table aria-label="Route options">
        <thead>
          <tr>
            <td />
            {presets.map((p) => (
              <th key={p} scope="col">
                <button
                  type="button"
                  aria-pressed={p === selected}
                  aria-label={`Show ${PRESET_TITLES[p]} on the map`}
                  onClick={() => onSelect(p)}
                  className="preset-button"
                >
                  {PRESET_TITLES[p]}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.name}>
              <th scope="row">
                {row.name}
                {row.unit && <span className="unit"> ({row.unit})</span>}
              </th>
              {presets.map((p) => (
                <td key={p}>
                  {row.value(plans[p].totals)} <LabelBadge label={plans[p].totals.label} source={SOURCE} />
                </td>
              ))}
            </tr>
          ))}
          <tr>
            <th scope="row">Checks</th>
            {presets.map((p) => (
              <td key={p}>
                {Object.values(plans[p].checks).every((c) => c === "pass")
                  ? "All five pass"
                  : Object.entries(plans[p].checks)
                      .filter(([, v]) => v !== "pass")
                      .map(([k]) => k)
                      .join(", ")}{" "}
                <LabelBadge label="MODELED" source="Thread, buddy, shelter, comms and rover checks" />
              </td>
            ))}
          </tr>
        </tbody>
      </table>
      <p className="note">
        Reserve and shelter limits differ by preset (Safest: 45 min reserve, shelter within 10 min).
        All settings are PLACEHOLDER; the walker model is EXTRAPOLATED to Mars gravity.
      </p>
    </section>
  );
}
