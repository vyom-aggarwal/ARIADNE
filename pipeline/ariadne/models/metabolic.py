# Written with AI assistance (Claude Code). See AI_USE.md.
"""Suited walker model: pace and metabolic rate on a slope (PROMPT.md 5.2).

NASA/TP-2010-216125 (Norcross et al. 2010) gives the FORM of its predictive model, equation (1)
on p. 70, MR = b0 + b1 (V x G) + b2 L_shank + b3 L_shoulder + b4 P_suit + b5 M_suit, but states
on p. 79 that "equation coefficients were not reported at this time". It cannot be transcribed.
What it does give is the tested range used here for the EXTRAPOLATED flags: speeds 0.56 to
0.97 m/s and grades 0 to 30% (p. 70), gravity 0.12 to 0.32 g and suit pressure 6.9 to 44.8 kPa
(Table 7, p. 71). Mars (0.38 g) is outside it, so every Mars walk is flagged.

The slope dependence therefore comes from Minetti et al. 2002 (J Appl Physiol 93:1039, p. 1041):
the metabolic cost of walking per kg and metre, Cw(i), a 5th-order polynomial in the gradient
i (rise over run) fitted between -0.45 and +0.45 on Earth, unsuited, on a treadmill. A
PLACEHOLDER factor (config/suits.json) stands for Mars gravity and the suit, which no verified
source quantifies here. Pace: the walker goes at the PLACEHOLDER top speed unless that would
need more than the PLACEHOLDER power ceiling, then at the speed the ceiling allows.

Label: MODELED (Minetti's curve) with PLACEHOLDER suit, gravity and pace settings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Minetti et al. 2002, p. 1041: Cw(i) = 280.5 i^5 - 58.7 i^4 - 76.8 i^3 + 51.9 i^2 + 19.6 i + 2.5
# (J kg^-1 m^-1, R^2 = 0.999), highest power first.
MINETTI_CW = (280.5, -58.7, -76.8, 51.9, 19.6, 2.5)
MINETTI_RANGE = (-0.45, 0.45)
# NASA/TP-2010-216125 tested ranges (pp. 70 and 71).
NASA_SPEED_M_S = (0.56, 0.97)
NASA_GRADE = (0.0, 0.30)
NASA_GRAVITY_G = (0.12, 0.32)
NASA_PRESSURE_KPA = (6.9, 44.8)
EARTH_G = 9.80665


@dataclass(frozen=True)
class Suit:
    body_mass_kg: float
    suit_gravity_factor: float
    max_speed_m_s: float
    power_ceiling_w_kg: float
    station_rate_ratio: float
    suit_pressure_kpa: float
    gravity_m_s2: float

    @property
    def gravity_g(self) -> float:
        return self.gravity_m_s2 / EARTH_G


def load_suit(profile: str = "default", path: Path | None = None) -> Suit:
    from ariadne.config import config_dir

    p = path or config_dir() / "suits.json"
    d = json.loads(Path(p).read_text(encoding="utf-8"))[profile]
    return Suit(**{k: float(d[k]["value"]) for k in Suit.__dataclass_fields__})


def cost_of_transport(i):
    """Minetti's Cw (J/kg/m) at gradient i, evaluated with i clamped to the fitted range."""
    x = np.clip(np.asarray(i, dtype=np.float64), *MINETTI_RANGE)
    return np.polyval(MINETTI_CW, x)


def speed(i, suit: Suit):
    """Walking pace (m/s): the top speed, or what the power ceiling allows if that is lower."""
    cw = suit.suit_gravity_factor * cost_of_transport(i)
    return np.minimum(suit.max_speed_m_s, suit.power_ceiling_w_kg / cw)


def metabolic_rate(i, v, suit: Suit):
    """Metabolic power per kg of body mass (W/kg) while walking at speed v on gradient i."""
    return suit.suit_gravity_factor * cost_of_transport(i) * np.asarray(v, dtype=np.float64)


def nominal_rate(suit: Suit) -> float:
    """The nominal rate consumables are counted in: level walking at the top speed."""
    return float(metabolic_rate(0.0, suit.max_speed_m_s, suit))


def rate_ratio(i, suit: Suit):
    """Metabolic rate at the model pace on gradient i, relative to the nominal rate."""
    return metabolic_rate(i, speed(i, suit), suit) / nominal_rate(suit)


def extrapolation_flags(i: float, v: float, suit: Suit) -> list[str]:
    """Reasons a setting lies outside the tested ranges (empty if none)."""
    out = []
    g = suit.gravity_g
    if not NASA_GRAVITY_G[0] <= g <= NASA_GRAVITY_G[1]:
        out.append(f"gravity {g:.2f} g is outside the 0.12 to 0.32 g tested in NASA/TP-2010-216125")
    if not NASA_PRESSURE_KPA[0] <= suit.suit_pressure_kpa <= NASA_PRESSURE_KPA[1]:
        out.append("suit pressure is outside the 6.9 to 44.8 kPa tested")
    if not NASA_GRADE[0] <= i <= NASA_GRADE[1]:
        out.append(f"grade {100 * i:.0f}% is outside the 0 to 30% tested")
    if not NASA_SPEED_M_S[0] <= v <= NASA_SPEED_M_S[1]:
        out.append(f"speed {v:.2f} m/s is outside the 0.56 to 0.97 m/s tested")
    if not MINETTI_RANGE[0] <= i <= MINETTI_RANGE[1]:
        out.append("gradient is outside Minetti et al.'s -0.45 to +0.45")
    return out
