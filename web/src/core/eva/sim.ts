// Written with AI assistance (Claude Code). See AI_USE.md.
/**
 * The EVA simulated from a plan (PROMPT.md section 6: "simulated from the plan in the demo").
 * Pure functions of plan time t (minutes since the walk starts):
 * - EV1 follows the plan's margin samples (at most 5 m apart), standing at each station for its
 *   visit;
 * - EV2, the buddy, stands at the station's overwatch point during a visit and walks 15 s behind
 *   EV1 on legs (PLACEHOLDER);
 * - the rover follows its relay schedule, on a straight line between parking places while it
 *   drives (its drive path is not stored);
 * - the margin, consumables left, walking minutes to the rover, the storm response and the
 *   over-cautious marking come from the plan's own samples.
 * Everything here is simulated from MODELED plans; nothing is live telemetry.
 */
import type { Plan, Station } from "../../planner/types";
import { type StormSample, stormAt } from "../plan/storm";

export type XY = [number, number];

export const BUDDY_LAG_MIN = 0.25; // PLACEHOLDER: EV2 walks 15 s behind EV1 on legs

interface TrackPoint {
  t: number;
  xy: XY;
}

const tracks = new WeakMap<Plan, TrackPoint[]>();

/** Time-ordered positions: each station sample becomes an arrival and a departure point. */
export function track(plan: Plan): TrackPoint[] {
  const cached = tracks.get(plan);
  if (cached) return cached;
  const out: TrackPoint[] = [];
  for (const m of plan.margins) {
    if (m.station !== null && m.station !== undefined) {
      const st = plan.stations[m.station];
      const svc = st?.service_min ?? 0;
      const xy = (st?.xy_m ?? m.xy_m) as XY;
      out.push({ t: m.t_min - svc, xy });
      out.push({ t: m.t_min, xy });
    } else {
      out.push({ t: m.t_min, xy: m.xy_m as XY });
    }
  }
  tracks.set(plan, out);
  return out;
}

export function endTime(plan: Plan): number {
  const tr = track(plan);
  return tr.length ? tr[tr.length - 1].t : 0;
}

/** Index of the last element with key <= t (0 if t is before the first). */
function lastAtOrBefore<T>(arr: T[], key: (x: T) => number, t: number): number {
  let lo = 0;
  let hi = arr.length - 1;
  if (hi < 0 || t <= key(arr[0])) return 0;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (key(arr[mid]) <= t) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

export function lerp(a: XY, b: XY, f: number): XY {
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
}

export function positionAt(plan: Plan, t: number): XY {
  const tr = track(plan);
  if (tr.length === 0) return [0, 0];
  if (t <= tr[0].t) return tr[0].xy;
  if (t >= tr[tr.length - 1].t) return tr[tr.length - 1].xy;
  const i = lastAtOrBefore(tr, (p) => p.t, t);
  const a = tr[i];
  const b = tr[Math.min(i + 1, tr.length - 1)];
  const span = b.t - a.t;
  return span > 0 ? lerp(a.xy, b.xy, (t - a.t) / span) : b.xy;
}

/** Direction of travel in degrees clockwise from north (site metres: x east, y north). */
export function headingAt(plan: Plan, t: number): number {
  const a = positionAt(plan, t);
  for (const dt of [0.2, 0.5, 1, 2, 5]) {
    const b = positionAt(plan, t + dt);
    if (distanceM(a, b) > 0.5) return bearingDeg(a, b);
  }
  const p = positionAt(plan, t - 0.5);
  return distanceM(p, a) > 0.5 ? bearingDeg(p, a) : 0;
}

export function bearingDeg(from: XY, to: XY): number {
  const deg = (Math.atan2(to[0] - from[0], to[1] - from[1]) * 180) / Math.PI;
  return (deg + 360) % 360;
}

export function distanceM(a: XY, b: XY): number {
  return Math.hypot(b[0] - a[0], b[1] - a[1]);
}

/** Relative bearing in -180..180 (positive: to the right of the heading). */
export function relativeBearing(bearing: number, heading: number): number {
  return ((bearing - heading + 540) % 360) - 180;
}

export interface Block {
  index: number;
  station: Station;
  start: number;
  end: number;
}

export function blocks(plan: Plan): Block[] {
  return plan.timeline.stations.map((b, index) => ({
    index,
    station: plan.stations[index],
    start: b.start_min,
    end: b.end_min,
  }));
}

/** The station being worked at t, or the next one; null once every station is done. */
export function nextStation(plan: Plan, t: number): { block: Block; atStation: boolean } | null {
  for (const b of blocks(plan)) {
    if (b.end > t) return { block: b, atStation: b.start <= t };
  }
  return null;
}

export function buddyAt(plan: Plan, t: number): XY {
  const ns = nextStation(plan, t);
  if (ns?.atStation && ns.block.station.overwatch_xy_m) return ns.block.station.overwatch_xy_m;
  return positionAt(plan, Math.max(0, t - BUDDY_LAG_MIN));
}

function relayXY(plan: Plan, index: number): XY {
  return plan.rover?.relays[index]?.xy_m ?? plan.rover?.relays[0]?.xy_m ?? [0, 0];
}

/** Where the rover is at t, and whether it is driving. */
export function roverAt(plan: Plan, t: number): { xy: XY; moving: boolean; relay: number } {
  const rover = plan.rover;
  if (!rover) return { xy: [0, 0], moving: false, relay: 0 };
  const bl = blocks(plan);
  let cur = 0;
  for (const mv of rover.moves) {
    // a move before transect k happens during the first leg (k = 1) or the last station of
    // transect k - 1
    const start = mv.before_transect === 1 ? 0 : (bl[3 * (mv.before_transect - 1) - 1]?.start ?? 0);
    const end = start + mv.drive_min;
    if (t < start) return { xy: relayXY(plan, cur), moving: false, relay: cur };
    if (t < end) {
      const f = mv.drive_min > 0 ? (t - start) / mv.drive_min : 1;
      return { xy: lerp(relayXY(plan, mv.from_relay), relayXY(plan, mv.to_relay), f), moving: true,
        relay: mv.to_relay };
    }
    cur = mv.to_relay;
  }
  return { xy: relayXY(plan, cur), moving: false, relay: cur };
}

function marginIndex(plan: Plan, t: number): number {
  return lastAtOrBefore(plan.margins, (m) => m.t_min, t);
}

/** Thread margin above the reserve, in minutes, interpolated along the timeline. */
export function marginAt(plan: Plan, t: number): number {
  const m = plan.timeline.margin;
  if (m.length === 0) return 0;
  const i = lastAtOrBefore(m, (x) => x.t_min, t);
  const a = m[i];
  const b = m[Math.min(i + 1, m.length - 1)];
  if (t <= a.t_min || b.t_min <= a.t_min) return a.margin_min;
  return a.margin_min + ((b.margin_min - a.margin_min) * (t - a.t_min)) / (b.t_min - a.t_min);
}

export function consumablesLeftAt(plan: Plan, t: number): number {
  return plan.margins[marginIndex(plan, t)]?.c_left ?? 0;
}

export function minutesToRoverAt(plan: Plan, t: number): number | null {
  return plan.margins[marginIndex(plan, t)]?.minutes_to_rover ?? null;
}

/** The over-cautious marking in force at t: the plan's listed sample at the margin sample at or
 * before t, if that sample is listed. */
export function overcautiousAt(plan: Plan, t: number) {
  const list = plan.overcautious?.samples ?? [];
  if (list.length === 0) return null;
  const m = plan.margins[marginIndex(plan, t)];
  return list.find((x) => Math.abs(x.t_min - m.t_min) < 1e-6) ?? null;
}

/** EV1's positions up to t, about every `everyM` metres. */
export function breadcrumbs(plan: Plan, t: number, everyM = 25): XY[] {
  const out: XY[] = [];
  for (const p of track(plan)) {
    if (p.t > t) break;
    if (out.length === 0 || distanceM(out[out.length - 1], p.xy) >= everyM) out.push(p.xy);
  }
  return out;
}

export interface EvaSnapshot {
  t: number;
  ev1: XY;
  heading: number;
  ev2: XY;
  rover: { xy: XY; moving: boolean; relay: number };
  next: { block: Block; atStation: boolean } | null;
  marginMin: number;
  consumablesLeft: number;
  minutesToRover: number | null;
  storm: StormSample | null;
  overcautious: ReturnType<typeof overcautiousAt>;
}

export function snapshot(plan: Plan, t: number): EvaSnapshot {
  return {
    t,
    ev1: positionAt(plan, t),
    heading: headingAt(plan, t),
    ev2: buddyAt(plan, t),
    rover: roverAt(plan, t),
    next: nextStation(plan, t),
    marginMin: marginAt(plan, t),
    consumablesLeft: consumablesLeftAt(plan, t),
    minutesToRover: minutesToRoverAt(plan, t),
    storm: stormAt(plan.storm, t),
    overcautious: overcautiousAt(plan, t),
  };
}
