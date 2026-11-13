// Written with AI assistance (Claude Code). See AI_USE.md.
// One state store for the surfaces (PROMPT.md section 6: "Five surfaces share one state store"):
// the chosen route, simulated mission time, play and speed, the manual storm alert, dropped pins
// and the last spoken response. The HUD, the Cuff Tablet and the card all read it.
import { useSyncExternalStore } from "react";
import type { XY } from "./sim";

export interface Pin {
  xy: XY;
  t: number;
  label: string;
}

export interface EvaState {
  preset: string;
  t: number;
  playing: boolean;
  /** Simulated minutes per real second. */
  speed: number;
  /** Manual storm alert (PLACEHOLDER until Phase 6 replays May 2024). */
  storm: boolean;
  pins: Pin[];
  said: string;
}

const initial: EvaState = { preset: "balanced", t: 0, playing: false, speed: 1, storm: false, pins: [], said: "" };
let state: EvaState = initial;
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

export function getEva(): EvaState {
  return state;
}

export function setEva(change: Partial<EvaState> | ((s: EvaState) => Partial<EvaState>)) {
  const c = typeof change === "function" ? change(state) : change;
  state = { ...state, ...c };
  emit();
}

export function resetEva() {
  state = initial;
  emit();
}

export function subscribeEva(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useEva(): EvaState {
  return useSyncExternalStore(subscribeEva, getEva, getEva);
}

/** Advance the clock while playing (simulated minutes = real seconds x speed), stopping at the
 * end of the walk. Returns a stop function. */
export function runClock(endMin: () => number): () => void {
  let last = performance.now();
  let frame = 0;
  const tick = (now: number) => {
    const dt = Math.min(0.25, (now - last) / 1000);
    last = now;
    const s = state;
    if (s.playing) {
      const t = Math.min(endMin(), s.t + dt * s.speed);
      setEva({ t, playing: t < endMin() });
    }
    frame = requestAnimationFrame(tick);
  };
  frame = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(frame);
}
