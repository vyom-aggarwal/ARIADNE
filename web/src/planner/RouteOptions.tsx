// Written with AI assistance (Claude Code). See AI_USE.md.
// The three route options as cards side by side (PROMPT.md section 6), key numbers large in mono,
// every number with its label, and the price-of-safety line as a highlighted strip.
import { CircleAlert, CircleCheck } from "lucide-react";
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

export const ROWS: { name: string; unit: string; value: (t: Totals) => string; big?: boolean }[] = [
  { name: "Science value", unit: "sum of station scores", value: (t) => t.science_value.toFixed(2), big: true },
  { name: "Stations (transects)", unit: "", value: (t) => `${t.stations} (${t.transects})` },
  { name: "Duration", unit: "min", value: (t) => t.minutes.toFixed(0) },
  { name: "Distance", unit: "m", value: (t) => Math.round(t.distance_m).toLocaleString("en-US") },
  { name: "Consumables used", unit: "min at nominal rate", value: (t) => t.consumables_min.toFixed(0) },
  { name: "Least margin above reserve", unit: "min", value: (t) => t.min_thread_margin_min.toFixed(1) },
  { name: "Worst walk to the rover", unit: "min", value: (t) => t.worst_minutes_to_shelter.toFixed(1) },
  { name: "Relative dose", unit: "open-sky minutes", value: (t) => t.relative_dose_min.toFixed(0) },
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
    <section className="route-options" aria-label="Route options">
      <div className="route-cards">
        {presets.map((p) => {
          const plan = plans[p];
          const failed = Object.entries(plan.checks).filter(([, v]) => v !== "pass").map(([k]) => k);
          return (
            <article key={p} className={`route-card${p === selected ? " selected" : ""}`} aria-label={`${PRESET_TITLES[p]} route`}
              data-preset={p}>
              <button type="button" aria-pressed={p === selected} aria-label={`Show ${PRESET_TITLES[p]} on the map`}
                onClick={() => onSelect(p)} className="preset-button">
                {PRESET_TITLES[p]}
              </button>
              <dl>
                {ROWS.map((row) => (
                  <div key={row.name} data-row={row.name}>
                    <dt>
                      {row.name}
                      {row.unit && <span className="visually-hidden"> ({row.unit})</span>}
                    </dt>
                    <dd className={row.big ? "big" : undefined} title={row.unit || undefined}>
                      {row.value(plan.totals)} <LabelBadge label={plan.totals.label} source={SOURCE} />
                    </dd>
                  </div>
                ))}
                <div data-row="Rover moves">
                  <dt>Rover moves (where the walk ends)</dt>
                  <dd>
                    {plan.rover ? `${plan.rover.moves.length} (${plan.rover.ends_at})` : "0"}{" "}
                    <LabelBadge label="MODELED" source={ROVER_SOURCE} />
                  </dd>
                </div>
                <div data-row="Checks">
                  <dt>Checks</dt>
                  <dd>
                    {failed.length === 0 ? (
                      <span className="checks-ok"><CircleCheck size={13} aria-hidden="true" /> All five pass</span>
                    ) : (
                      <span className="checks-ok" style={{ color: "var(--danger)" }}>
                        <CircleAlert size={13} aria-hidden="true" /> {failed.join(", ")}
                      </span>
                    )}{" "}
                    <LabelBadge label="MODELED" source="Thread, buddy, shelter, comms and rover checks" />
                  </dd>
                </div>
              </dl>
            </article>
          );
        })}
      </div>
      {price && (
        <p className="price-of-safety" data-testid="price-of-safety">
          <strong>Price of safety:</strong> Safest gives up <span className="num">{price.valueGivenUp.toFixed(2)}</span> of
          science value (<span className="num">{(100 * price.shareGivenUp).toFixed(0)}%</span> of Most science
          {price.transectsGivenUp > 0
            ? `, ${price.transectsGivenUp} transect${price.transectsGivenUp === 1 ? "" : "s"}`
            : ""}
          ) and gains <span className="num">{price.marginGained.toFixed(1)}</span> min of least margin above its reserve.{" "}
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
