// Written with AI assistance (Claude Code). See AI_USE.md.
/**
 * What the Visor HUD shows (PROMPT.md section 6), as data, so the rules can be tested in every
 * state: at most four elements at once, in four fixed slots in the periphery; white and cyan
 * only, each element with its own shape.
 *
 *  top-left       caution and warning: the highest-priority alert, with a count of the others
 *  top-centre     next station: heading and distance (in storm mode: the arrow to the refuge)
 *  bottom-left    thread: a small map with the line home, the margin, breadcrumbs and pins
 *  bottom-right   buddy: bearing, distance and suit status
 */
import type { Plan } from "../planner/types";
import { refugeName } from "../core/plan/storm";
import {
  bearingDeg,
  breadcrumbs,
  distanceM,
  type EvaSnapshot,
  relativeBearing,
  type XY,
} from "../core/eva/sim";
import type { HudColor } from "./colors";

export type Slot = "top-left" | "top-centre" | "bottom-left" | "bottom-right";
export type Shape =
  | "chevron"
  | "double-chevron"
  | "ring"
  | "polyline"
  | "diamond"
  | "octagon"
  | "triangle"
  | "hatched-square"
  | "circle";

export type AlertId = "storm" | "low-margin" | "rover-far" | "overcautious";

export interface Alert {
  id: AlertId;
  level: "warning" | "caution" | "advisory";
  text: string;
  shape: Shape;
}

export interface HudElement {
  kind: "next" | "storm" | "thread" | "buddy" | "alert";
  slot: Slot;
  shape: Shape;
  color: HudColor;
  text: string;
  /** Arrow direction relative to the direction of travel, degrees (positive: right). */
  arrowDeg?: number;
  homePath?: XY[];
  crumbs?: XY[];
  pins?: XY[];
  ev1?: XY;
  more?: number;
}

export const LOW_MARGIN_MIN = 15; // PLACEHOLDER: caution when the thread margin falls below this
export const ROVER_FAR_FRACTION = 0.9; // PLACEHOLDER: caution at 90% of the walking limit
export const STEER_AHEAD_M = 15; // the storm arrow points this far along the path to the refuge

export const ALERT_SHAPES: Record<AlertId, Shape> = {
  storm: "octagon",
  "low-margin": "triangle",
  "rover-far": "circle",
  overcautious: "hatched-square",
};

const PRIORITY: AlertId[] = ["storm", "low-margin", "rover-far", "overcautious"];

export function alertsFor(plan: Plan, snap: EvaSnapshot, stormOn: boolean): Alert[] {
  const out: Alert[] = [];
  if (stormOn) {
    const s = snap.storm;
    out.push({
      id: "storm",
      level: "warning",
      shape: ALERT_SHAPES.storm,
      text: s
        ? s.choice === "stay"
          ? "Solar storm: stay put, the lowest modeled dose is here"
          : `Solar storm: go to ${refugeName(s.choice)}, ${s.walk_min.toFixed(0)} min`
        : "Solar storm: go to the rover",
    });
  }
  if (snap.marginMin < LOW_MARGIN_MIN) {
    out.push({ id: "low-margin", level: "caution", shape: ALERT_SHAPES["low-margin"],
      text: `Thread margin ${snap.marginMin.toFixed(0)} min: head home` });
  }
  const limit = plan.scenario.shelter_max_min;
  if (snap.minutesToRover !== null && snap.minutesToRover > ROVER_FAR_FRACTION * limit) {
    out.push({ id: "rover-far", level: "caution", shape: ALERT_SHAPES["rover-far"],
      text: `Rover ${snap.minutesToRover.toFixed(0)} min away on foot (limit ${limit})` });
  }
  if (snap.overcautious) {
    out.push({ id: "overcautious", level: "advisory", shape: ALERT_SHAPES.overcautious,
      text: "Map may be over-cautious here, check by eye" });
  }
  return out.sort((a, b) => PRIORITY.indexOf(a.id) - PRIORITY.indexOf(b.id));
}

function capital(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function arrow(rel: number): string {
  if (Math.abs(rel) < 15) return "ahead";
  if (Math.abs(rel) > 150) return "behind";
  return rel > 0 ? `right ${Math.round(rel)}°` : `left ${Math.round(-rel)}°`;
}

/** The point the storm arrow aims at: STEER_AHEAD_M along the refuge path from where it passes
 * closest to EV1 (the refuge itself when nearer). */
export function steerPoint(path: XY[], from: XY): XY | null {
  if (path.length === 0) return null;
  let k = 0;
  for (let i = 1; i < path.length; i++) if (distanceM(path[i], from) < distanceM(path[k], from)) k = i;
  for (let i = k; i < path.length; i++) if (distanceM(path[i], from) >= STEER_AHEAD_M) return path[i];
  return path[path.length - 1];
}

export function hudElements(
  plan: Plan,
  snap: EvaSnapshot,
  eva: { storm: boolean; pins: { xy: XY }[] },
): HudElement[] {
  const els: HudElement[] = [];
  const alerts = alertsFor(plan, snap, eva.storm);
  if (alerts.length) {
    const top = alerts[0];
    els.push({ kind: "alert", slot: "top-left", shape: top.shape,
      color: top.level === "advisory" ? "cyan" : "white", text: top.text, more: alerts.length - 1 });
  }
  if (eva.storm && snap.storm) {
    const target = steerPoint(snap.storm.path_xy_m, snap.ev1);
    const rel = target ? relativeBearing(bearingDeg(snap.ev1, target), snap.heading) : 0;
    els.push({
      kind: "storm",
      slot: "top-centre",
      shape: "double-chevron",
      color: "white",
      arrowDeg: target ? rel : undefined,
      text:
        snap.storm.choice === "stay"
          ? "Stay put"
          : `${capital(refugeName(snap.storm.choice))} ${arrow(rel)} · avoids ${snap.storm.dose_avoided.toFixed(0)} open-sky min`,
    });
  } else if (snap.next) {
    const st = snap.next.block.station;
    const d = distanceM(snap.ev1, st.xy_m);
    const rel = relativeBearing(bearingDeg(snap.ev1, st.xy_m), snap.heading);
    els.push(
      snap.next.atStation
        ? { kind: "next", slot: "top-centre", shape: "ring", color: "white",
            text: `At ${st.id} (${st.role}) · ${Math.max(0, snap.next.block.end - snap.t).toFixed(0)} min left` }
        : { kind: "next", slot: "top-centre", shape: "chevron", color: "white", arrowDeg: rel,
            text: `${st.id} ${st.role} · ${Math.round(d)} m ${arrow(rel)}` },
    );
  } else {
    const d = distanceM(snap.ev1, snap.rover.xy);
    const rel = relativeBearing(bearingDeg(snap.ev1, snap.rover.xy), snap.heading);
    els.push({ kind: "next", slot: "top-centre", shape: "chevron", color: "white", arrowDeg: rel,
      text: `Home: rover · ${Math.round(d)} m ${arrow(rel)}` });
  }
  const home = snap.storm?.home_path_xy_m ?? [];
  els.push({
    kind: "thread",
    slot: "bottom-left",
    shape: "polyline",
    color: "cyan",
    text: `Margin ${snap.marginMin.toFixed(0)} min${snap.minutesToRover !== null ? ` · rover ${snap.minutesToRover.toFixed(0)} min` : ""}`,
    homePath: [snap.ev1, ...home],
    crumbs: breadcrumbs(plan, snap.t),
    pins: eva.pins.map((p) => p.xy),
    ev1: snap.ev1,
  });
  const bd = distanceM(snap.ev1, snap.ev2);
  const brel = relativeBearing(bearingDeg(snap.ev1, snap.ev2), snap.heading);
  els.push({
    kind: "buddy",
    slot: "bottom-right",
    shape: "diamond",
    color: "cyan",
    arrowDeg: brel,
    text: `EV2 ${Math.round(bd)} m ${bd < 1 ? "" : arrow(brel)} · suit ${snap.consumablesLeft.toFixed(0)} min left`,
  });
  return els;
}
