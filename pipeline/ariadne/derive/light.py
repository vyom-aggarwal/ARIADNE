# Written with AI assistance (Claude Code). See AI_USE.md.
"""Light and relative ground temperature (PROMPT.md 4.8).

The sun's azimuth (clockwise from north) and elevation come from the Mars24 functions. A cell is
in shadow when the sun's elevation is below its horizon at the sun's azimuth (horizons are
interpolated between azimuths). Sunrise and sunset use the sun's centre. The sun track is
computed once per site: across a 4 km site the sun's position changes by under 0.07 degrees.

Relative ground temperature keeps the timing of a REMS daily curve and scales its swing about
the daily mean by the cell's daily insolation ratio and a thermal-inertia factor. It is MODELED
and RELATIVE: it says which ground runs warmer or colder, not by how many kelvin.
"""

from __future__ import annotations

import math

import numpy as np
from numba import njit, prange

from ariadne.models.sun import (  # noqa: F401  (re-exported: light.sun_track and friends)
    MARS_FLATTENING,
    SunTrack,
    band_lookup,
    local_noon_track,
    planetographic_latitude,
    sun_track,
)


def in_shadow(h_bands: np.ndarray, sun_az: float, sun_el: float) -> np.ndarray:
    """True where the sun (centre) is at or below the horizon; h_bands has azimuths last."""
    from ariadne.derive.horizons import horizon_at_azimuth

    return sun_el <= horizon_at_azimuth(h_bands, sun_az)


def incidence_cos(slope_deg, aspect_deg, sun_az, sun_el):
    """Cosine of the sun's incidence angle on a slope (aspect = direction it faces)."""
    s = np.radians(np.asarray(slope_deg, dtype=np.float64))
    asp = np.radians(np.nan_to_num(np.asarray(aspect_deg, dtype=np.float64), nan=0.0))
    e = math.radians(sun_el)
    a = math.radians(sun_az)
    return np.cos(s) * math.sin(e) + np.sin(s) * math.cos(e) * np.cos(a - asp)


def _crossing(t0, t1, d0, d1):
    """Linear interpolation of the time where d goes through zero between two samples."""
    if d1 == d0:
        return t1
    return t0 + (t1 - t0) * (d0 / (d0 - d1))


def sunrise_sunset_point(h_az: np.ndarray, track: SunTrack) -> tuple[float | None, float | None]:
    """Sunrise and sunset (seconds from the track start) for one horizon profile."""
    i0, i1, f = track.lookup(h_az.size)
    h = h_az[i0] * (1 - f) + h_az[i1] * f
    d = track.elevation - h
    t = track.seconds
    lit = d > 0
    if not lit.any():
        return None, None
    k_first = int(np.argmax(lit))
    k_last = int(len(lit) - 1 - np.argmax(lit[::-1]))
    rise = (
        t[0] if k_first == 0 else _crossing(t[k_first - 1], t[k_first], d[k_first - 1], d[k_first])
    )
    sset = (
        t[-1]
        if k_last == len(t) - 1
        else _crossing(t[k_last], t[k_last + 1], d[k_last], d[k_last + 1])
    )
    return float(rise), float(sset)


@njit(parallel=True, cache=True)
def _sun_grid(codes, qmin, qstep, nodata_code, el, i0, i1, f, t, slope, aspect, sin_el_sum, sun_az):
    """Per cell: sunrise and sunset (s from track start, NaN if never lit) and relative insolation.

    codes: (n_az, rows, cols) uint8 quantized horizons.
    """
    n_az, h, w = codes.shape
    n_t = el.size
    rise = np.full((h, w), np.nan, dtype=np.float32)
    sset = np.full((h, w), np.nan, dtype=np.float32)
    insol = np.full((h, w), np.nan, dtype=np.float32)
    for r in prange(h):
        for c in range(w):
            if codes[0, r, c] == nodata_code:
                continue
            prev_d = -1e9
            first = -1.0
            last = -1.0
            acc = 0.0
            s = math.radians(slope[r, c])
            asp = aspect[r, c]
            asp = 0.0 if math.isnan(asp) else math.radians(asp)
            for k in range(n_t):
                hz0 = codes[i0[k], r, c] * qstep + qmin
                hz1 = codes[i1[k], r, c] * qstep + qmin
                hk = hz0 * (1.0 - f[k]) + hz1 * f[k]
                d = el[k] - hk
                if d > 0.0:
                    if first < 0.0:
                        first = (
                            t[0]
                            if k == 0
                            else t[k - 1] + (t[k] - t[k - 1]) * (prev_d / (prev_d - d))
                        )
                    e = math.radians(el[k])
                    a = math.radians(sun_az[k])
                    ci = math.cos(s) * math.sin(e) + math.sin(s) * math.cos(e) * math.cos(a - asp)
                    if ci > 0.0:
                        acc += ci
                elif prev_d > 0.0 and k > 0:
                    last = t[k - 1] + (t[k] - t[k - 1]) * (prev_d / (prev_d - d))
                prev_d = d
            if first >= 0.0:
                rise[r, c] = first
                sset[r, c] = last if last >= 0.0 else t[n_t - 1]
            insol[r, c] = acc / sin_el_sum if sin_el_sum > 0 else np.nan
    return rise, sset, insol


def sun_grid(codes, qmin, qstep, nodata_code, track: SunTrack, slope, aspect):
    """Sunrise, sunset (seconds from track start) and daily insolation relative to flat open ground.

    The relative insolation is the sum over the track of max(cos incidence, 0) while lit, over
    the same sum for flat ground with no horizon (sum of max(sin elevation, 0)).
    """
    i0, i1, f = track.lookup(codes.shape[0])
    t = track.seconds
    sin_sum = float(np.sum(np.clip(np.sin(np.radians(track.elevation)), 0, None)))
    return _sun_grid(
        codes,
        float(qmin),
        float(qstep),
        int(nodata_code),
        track.elevation.astype(np.float64),
        i0,
        i1,
        f.astype(np.float64),
        t,
        np.asarray(slope, dtype=np.float32),
        np.asarray(aspect, dtype=np.float32),
        sin_sum,
        track.azimuth.astype(np.float64),
    )


def relative_ground_temperature(
    rems_curve_k: np.ndarray,
    insolation_ratio: float | np.ndarray,
    inertia_factor: float | np.ndarray,
) -> np.ndarray:
    """Scale a REMS daily ground-temperature curve's swing about its mean, keeping its timing.

    T(t) = mean + (T_REMS(t) - mean) * insolation_ratio * inertia_factor. Returns (..., time).
    """
    curve = np.asarray(rems_curve_k, dtype=np.float64)
    mean = curve.mean()
    k = np.asarray(insolation_ratio, dtype=np.float64) * np.asarray(
        inertia_factor, dtype=np.float64
    )
    return mean + (curve - mean) * np.asarray(k)[..., None]
