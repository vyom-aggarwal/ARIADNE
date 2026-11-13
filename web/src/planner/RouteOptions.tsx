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
  { name: "Worst walk to the rover", unit: "min", value: (t) => t.worst_minutes_to_shelter.toFixed(1) },
  { name: "Relative dose", unit: "open-sky minutes", value: (t) => t.relative_dose_min.toFixed(0) },
  { name: "Stations (transects)", unit: "", value: (t) => `${t.stations} (${t.transects})` },
  { name: "Science value", unit: "sum of station scores", value: (t) => t.science_value.toFixed(2) },
];
const ROVER_SOURCE =
  "The rover is a mobile comms relay and the shelter: it parks at a relay site for each transect " +
  "and moves during the last station of a transect or the first leg; the walk ends where the " +
  "rover is (PLACEHOLDER rover settings).";

export interface PriceOfSafety {
  valueGivenUp: number;
  shareGivenUp: number;
  transectsGivenUp: number;
  marginGained: number;
  sameTransects: boolean;
}

/** What Safest gives up in science value, and gains in least thread margin, against Most science. */
export function priceOfSafety(plans: Record<string, Plan>): PriceOfSafety | null {
  const a = plans.safest;
  const b = plans.most_science;
  if (!a || !b) return null;
  const ids = (p: Plan) => new Set(p.stations.map((s) => s.transect_source_id ?? s.transect));
  const ta = ids(a);
  const tb = ids(b);
  const same = ta.size === tb.size && [...ta].every((x) => tb.has(x));
  const given = b.totals.science_value - a.totals.science_value;
  return {
    valueGivenUp: given,
    shareGivenUp: b.totals.science_value > 0 ? given / b.totals.science_value : 0,
    transectsGivenUp: b.totals.transects - a.totals.transects,
    marginGained: a.totals.min_thread_margin_min - b.totals.min_thread_margin_min,
    sameTransects: same,
  };
}

export default function RouteOptions({ plans, selected, onSelect }: Props) {
  const presets = ORDER.filter((p) => plans[p]);
  const price = priceOfSafety(plans);
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
            <th scope="row">
              Rover moves<span className="unit"> (where the walk ends)</span>
            </th>
            {presets.map((p) => (
              <td key={p}>
                {plans[p].rover ? `${plans[p].rover!.moves.length} (${plans[p].rover!.ends_at})` : "0"}{" "}
                <LabelBadge label="MODELED" source={ROVER_SOURCE} />
              </td>
            ))}
          </tr>
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
      {price && (
        <p className="price-of-safety" data-testid="price-of-safety">
          <strong>Price of safety:</strong> Safest gives up {price.valueGivenUp.toFixed(2)} of science
          value ({(100 * price.shareGivenUp).toFixed(0)}% of Most science
          {price.transectsGivenUp > 0
            ? `, ${price.transectsGivenUp} transect${price.transectsGivenUp === 1 ? "" : "s"}`
            : ""}
          ) and gains {price.marginGained.toFixed(1)} min of least margin above its reserve.{" "}
          {price.sameTransects
            ? "The two visit the same transects; they differ in paths and margins only."
            : "The two visit different transects."}{" "}
          <LabelBadge label="MODELED" source={`${SOURCE} Most science minus Safest, from the plans above.`} />
        </p>
      )}
      <p className="note">
        Reserve and walking limits to the rover differ by preset (Safest: 45 min reserve, the rover
        within 10 min on foot; the others 30 and 20). The rover is the shelter: terrain blocks a few
        percent of the dose at most. All settings are PLACEHOLDER; the walker model is EXTRAPOLATED
        to Mars gravity.
      </p>
    </section>
  );
}
