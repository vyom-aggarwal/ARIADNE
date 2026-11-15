// Written with AI assistance (Claude Code). See AI_USE.md.
// Earth-Mars one-way light time for the mission bar, interpolated in the bundled JPL Horizons
// table (config/snapshots/horizons_light_time.json, written by `ariadne timemachine`). DERIVED.
import table from "../../../config/snapshots/horizons_light_time.json";

interface Row {
  utc: string;
  light_time_min: number;
}

const rows: { t: number; lt: number }[] = (table.table as Row[])
  .map((r) => ({ t: Date.parse(r.utc), lt: r.light_time_min }))
  .sort((a, b) => a.t - b.t);

/** One-way light time in minutes at `when`, or null outside the table. */
export function lightTimeAt(when: Date): number | null {
  const t = when.getTime();
  for (let i = 1; i < rows.length; i++) {
    const a = rows[i - 1];
    const b = rows[i];
    if (a.t <= t && t <= b.t && b.t - a.t <= 3 * 86400e3) {
      return a.lt + ((b.lt - a.lt) * (t - a.t)) / (b.t - a.t);
    }
  }
  return null;
}

export const LIGHT_TIME_SOURCE = "JPL Horizons API, Earth-Mars one-way light time, interpolated (config/snapshots)";

/** Sol and local solar time for the scenario clock: the plan's PLACEHOLDER start ("sol N at
 * HH:MM local true solar time") advanced by mission time at the mean solar rate. */
export function solClock(startNote: string | undefined, missionMin: number): { sol: number; hhmm: string } | null {
  const m = /sol (\d+) at (\d{1,2}):(\d{2})/.exec(startNote ?? "");
  if (!m) return null;
  const hours = Number(m[2]) + Number(m[3]) / 60 + missionMin / 60 / 1.0274912517;
  const sol = Number(m[1]) + Math.floor(hours / 24);
  const h = hours % 24;
  const hh = Math.floor(h);
  const mm = Math.floor((h - hh) * 60);
  return { sol, hhmm: `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}` };
}
