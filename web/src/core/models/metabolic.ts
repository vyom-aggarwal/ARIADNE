// Written with AI assistance (Claude Code). See AI_USE.md.
/**
 * Suited walker model, the TypeScript twin of pipeline/ariadne/models/metabolic.py.
 *
 * NASA/TP-2010-216125 publishes the form of its predictive model (eq. 1, p. 70) but no
 * coefficients (p. 79), so it cannot be transcribed. The slope dependence is Minetti et al. 2002
 * (J Appl Physiol 93:1039, p. 1041): cost of walking per kg and metre, a 5th-order polynomial in
 * gradient i, fitted from -0.45 to +0.45 on Earth, unsuited. Suit, gravity and pace settings are
 * PLACEHOLDER (config/suits.json). NASA/TP-2010-216125's tested ranges (pp. 70 and 71) set the
 * EXTRAPOLATED flags; Mars's 0.38 g is outside them. Both twins meet
 * config/models/metabolic_fixture.json.
 */

/** Minetti et al. 2002, p. 1041, highest power first (J kg^-1 m^-1). */
export const MINETTI_CW = [280.5, -58.7, -76.8, 51.9, 19.6, 2.5] as const;
export const MINETTI_RANGE: [number, number] = [-0.45, 0.45];
export const NASA_SPEED_M_S: [number, number] = [0.56, 0.97];
export const NASA_GRADE: [number, number] = [0.0, 0.3];
export const NASA_GRAVITY_G: [number, number] = [0.12, 0.32];
export const NASA_PRESSURE_KPA: [number, number] = [6.9, 44.8];
export const EARTH_G = 9.80665;

export interface Suit {
  body_mass_kg: number;
  suit_gravity_factor: number;
  max_speed_m_s: number;
  power_ceiling_w_kg: number;
  station_rate_ratio: number;
  suit_pressure_kpa: number;
  gravity_m_s2: number;
}

/** Reads a profile from config/suits.json ({key: {value, label, ...}}). */
export function suitFromConfig(profile: Record<string, { value: number }>): Suit {
  const v = (k: keyof Suit) => Number(profile[k].value);
  return {
    body_mass_kg: v("body_mass_kg"),
    suit_gravity_factor: v("suit_gravity_factor"),
    max_speed_m_s: v("max_speed_m_s"),
    power_ceiling_w_kg: v("power_ceiling_w_kg"),
    station_rate_ratio: v("station_rate_ratio"),
    suit_pressure_kpa: v("suit_pressure_kpa"),
    gravity_m_s2: v("gravity_m_s2"),
  };
}

/** Minetti's Cw (J/kg/m) at gradient i, with i clamped to the fitted range. */
export function costOfTransport(i: number): number {
  const x = Math.min(Math.max(i, MINETTI_RANGE[0]), MINETTI_RANGE[1]);
  let y = 0;
  for (const c of MINETTI_CW) y = y * x + c;
  return y;
}

/** Walking pace (m/s): the top speed, or what the power ceiling allows if lower. */
export function speed(i: number, suit: Suit): number {
  const cw = suit.suit_gravity_factor * costOfTransport(i);
  return Math.min(suit.max_speed_m_s, suit.power_ceiling_w_kg / cw);
}

/** Metabolic power per kg of body mass (W/kg) at speed v on gradient i. */
export function metabolicRate(i: number, v: number, suit: Suit): number {
  return suit.suit_gravity_factor * costOfTransport(i) * v;
}

/** The nominal rate consumables are counted in: level walking at the top speed. */
export function nominalRate(suit: Suit): number {
  return metabolicRate(0, suit.max_speed_m_s, suit);
}

/** Metabolic rate at the model pace on gradient i, relative to the nominal rate. */
export function rateRatio(i: number, suit: Suit): number {
  return metabolicRate(i, speed(i, suit), suit) / nominalRate(suit);
}

/** Reasons a setting lies outside the tested ranges (empty if none). */
export function extrapolationFlags(i: number, v: number, suit: Suit): string[] {
  const out: string[] = [];
  const g = suit.gravity_m_s2 / EARTH_G;
  if (g < NASA_GRAVITY_G[0] || g > NASA_GRAVITY_G[1])
    out.push(`gravity ${g.toFixed(2)} g is outside the 0.12 to 0.32 g tested in NASA/TP-2010-216125`);
  if (suit.suit_pressure_kpa < NASA_PRESSURE_KPA[0] || suit.suit_pressure_kpa > NASA_PRESSURE_KPA[1])
    out.push("suit pressure is outside the 6.9 to 44.8 kPa tested");
  if (i < NASA_GRADE[0] || i > NASA_GRADE[1])
    out.push(`grade ${(100 * i).toFixed(0)}% is outside the 0 to 30% tested`);
  if (v < NASA_SPEED_M_S[0] || v > NASA_SPEED_M_S[1])
    out.push(`speed ${v.toFixed(2)} m/s is outside the 0.56 to 0.97 m/s tested`);
  if (i < MINETTI_RANGE[0] || i > MINETTI_RANGE[1])
    out.push("gradient is outside Minetti et al.'s -0.45 to +0.45");
  return out;
}
