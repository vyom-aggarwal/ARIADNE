# Written with AI assistance (Claude Code). See AI_USE.md.
"""Radiation shielding index (PROMPT.md 4.5) and its calibration at Murray Buttes.

S(n) is the open-sky fraction weighted by cos^n of the zenith angle:

    S = mean over azimuths of (1 - sin^(n+1)(max(h, 0)))

because integrating cos^n(theta) sin(theta) over the open zenith angles 0 to 90 - h gives
(1 - sin^(n+1) h) / (n + 1), and the open hemisphere gives 1 / (n + 1). n = 0 is an isotropic
sky, for which 1 - S is the blocked solid-angle fraction, mean(sin h).

Relative dose is D ~ D_RAD * S * f(p), with f(p) = 1 + kappa (p - p_ref) / D_ref and pressure
from elevation, p = p_ref exp(-(z - z_ref) / H).

The calibration follows Ehresmann et al. (2021): RAD's dose on the parked sols is compared with
an expected dose fitted on baseline sols, so n is fitted to the ratio
S(parking) f(parking) / mean over baseline sols of S f, not to S against an open sky.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def open_sky_fraction(h_deg: np.ndarray, n: float) -> np.ndarray:
    """S for horizons with azimuths on the last axis."""
    s = np.sin(np.radians(np.clip(np.asarray(h_deg, dtype=np.float64), 0.0, 90.0)))
    return np.mean(1.0 - s ** (n + 1.0), axis=-1)


def blocked_fraction(h_deg: np.ndarray) -> np.ndarray:
    """Share of the hemisphere's solid angle below the horizon (the n = 0 case)."""
    return 1.0 - open_sky_fraction(h_deg, 0.0)


def mean_blocking_angle(h_deg: np.ndarray) -> np.ndarray:
    """Mean of max(h, 0) over azimuths, in degrees (the paper's 'average blocking angle')."""
    return np.mean(np.clip(np.asarray(h_deg, dtype=np.float64), 0.0, 90.0), axis=-1)


def pressure_from_elevation(z, z_ref: float, p_ref: float, scale_height: float):
    return p_ref * np.exp(-(np.asarray(z, dtype=np.float64) - z_ref) / scale_height)


def pressure_factor(
    z, z_ref: float, p_ref: float, kappa: float, dose_ref: float, scale_height: float
):
    """f(p) = 1 + kappa (p - p_ref) / D_ref; 1 at the reference elevation."""
    p = pressure_from_elevation(z, z_ref, p_ref, scale_height)
    return 1.0 + kappa * (p - p_ref) / dose_ref


def column_to_pressure(column_g_cm2: float, gravity: float) -> float:
    """Vertical column mass (g/cm^2) to surface pressure (Pa): p = sigma g."""
    return column_g_cm2 * 10.0 * gravity


@dataclass
class Calibration:
    """Result of fitting n to a measured dose ratio."""

    target_ratio: float
    n: float | None
    n_low: float | None  # n giving the target's lower ratio bound (more reduction)
    n_high: float | None  # n giving the upper ratio bound (less reduction)
    n_grid: np.ndarray = field(repr=False)
    ratio_grid: np.ndarray = field(repr=False)
    crossings: int = 0
    note: str = ""

    def ratio_at(self, n: float) -> float:
        return float(np.interp(n, self.n_grid, self.ratio_grid))


def dose_ratio(
    n: float,
    h_park: np.ndarray,
    f_park: float,
    h_baseline_sols: list[np.ndarray],
    f_baseline_sols: list[np.ndarray],
) -> float:
    """S f at the parking spot over the mean, across sols, of each sol's mean S f."""
    s_park = float(open_sky_fraction(h_park, n)) * f_park
    per_sol = [
        float(np.mean(open_sky_fraction(h, n) * f))
        for h, f in zip(h_baseline_sols, f_baseline_sols, strict=True)
    ]
    return s_park / float(np.mean(per_sol))


def _crossings(n_grid: np.ndarray, ratio: np.ndarray, target: float) -> list[float]:
    diff = ratio - target
    out = []
    for i in range(len(n_grid) - 1):
        a, b = diff[i], diff[i + 1]
        if a == 0:
            out.append(float(n_grid[i]))
        elif a * b < 0:
            out.append(float(n_grid[i] - a * (n_grid[i + 1] - n_grid[i]) / (b - a)))
    if diff[-1] == 0:
        out.append(float(n_grid[-1]))
    return out


def calibrate_n(
    h_park: np.ndarray,
    f_park: float,
    h_baseline_sols: list[np.ndarray],
    f_baseline_sols: list[np.ndarray],
    target_ratio: float,
    ratio_bounds: tuple[float, float] | None = None,
    n_range: tuple[float, float] = (0.0, 10.0),
    n_step: float = 0.001,
) -> Calibration:
    """Find n in `n_range` where the modeled dose ratio equals `target_ratio`.

    Evaluates the ratio on a fine grid and reports every crossing; `n` is None (with a note) when
    no n in the range fits. `ratio_bounds` = (lower, upper) ratios give the matching n range.
    """
    n_grid = np.arange(n_range[0], n_range[1] + n_step / 2, n_step)
    ratio = np.array(
        [dose_ratio(n, h_park, f_park, h_baseline_sols, f_baseline_sols) for n in n_grid]
    )
    hits = _crossings(n_grid, ratio, target_ratio)
    note = ""
    if not hits:
        lo, hi = float(ratio.min()), float(ratio.max())
        note = (
            f"No n in {n_range[0]:g} to {n_range[1]:g} gives a ratio of {target_ratio:.4f}; "
            f"the model's ratio ranges from {lo:.4f} to {hi:.4f}."
        )
    elif len(hits) > 1:
        note = f"{len(hits)} values of n give the target ratio; the smallest is reported."

    def first(target):
        h = _crossings(n_grid, ratio, target)
        return h[0] if h else None

    n_low = n_high = None
    if ratio_bounds is not None:
        n_low, n_high = first(ratio_bounds[0]), first(ratio_bounds[1])
    return Calibration(
        target_ratio=target_ratio,
        n=hits[0] if hits else None,
        n_low=n_low,
        n_high=n_high,
        n_grid=n_grid,
        ratio_grid=ratio,
        crossings=len(hits),
        note=note,
    )


def shielding_map(h_bands_iter, n: float, n_az: int) -> np.ndarray:
    """S on a grid from an iterable of per-azimuth horizon bands (degrees)."""
    acc = None
    for band in h_bands_iter:
        s = np.sin(np.radians(np.clip(band.astype(np.float64), 0.0, 90.0)))
        term = 1.0 - s ** (n + 1.0)
        acc = term if acc is None else acc + term
    return (acc / n_az).astype(np.float32)
