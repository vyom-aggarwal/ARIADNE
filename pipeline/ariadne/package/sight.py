# Written with AI assistance (Claude Code). See AI_USE.md.
"""Line of sight from the rover, wherever it is parked, to each sample of a plan (for the
timeline's comm-shadow segments). Line of sight only; radio is not modeled.

`line_of_sight` mirrors ariadne.derive.los.line_of_sight (the same sampling, bilinear heights
and curvature bulge) in plain NumPy, so the package step does not load numba; a test checks the
two agree. Each sample is checked from the relay the rover is parked at for its leg; at a
station where the rover changes relay, from both, as the plan's comms check does.
"""

from __future__ import annotations

import math

import numpy as np

R_MARS = 3_396_190.0  # m, as ariadne.derive.horizons.R_MARS


def bilinear(z: np.ndarray, rr: np.ndarray, cc: np.ndarray) -> np.ndarray:
    """ariadne.derive.horizons._bilinear, vectorized: NaN outside the grid."""
    h, w = z.shape
    rr = np.asarray(rr, dtype=np.float64)
    cc = np.asarray(cc, dtype=np.float64)
    out = np.full(rr.shape, np.nan)
    ok = (rr >= 0.0) & (cc >= 0.0) & (rr <= h - 1) & (cc <= w - 1)
    r, c = rr[ok], cc[ok]
    i0 = np.floor(r).astype(np.int64)
    j0 = np.floor(c).astype(np.int64)
    i1 = np.minimum(i0 + 1, h - 1)
    j1 = np.minimum(j0 + 1, w - 1)
    fy, fx = r - i0, c - j0
    top = z[i0, j0] * (1.0 - fx) + z[i0, j1] * fx
    bot = z[i1, j0] * (1.0 - fx) + z[i1, j1] * fx
    out[ok] = top * (1.0 - fy) + bot * fy
    return out


def line_of_sight(dem, transform, a_xy, b_xy, ha: float, hb: float, step_m=None) -> bool:
    """True if the line from a (ha above ground) to b (hb above ground) clears the terrain."""
    res = transform.a
    step = step_m or res / 2
    inv = ~transform

    def rc(x, y):
        col = inv.a * x + inv.b * y + inv.c
        row = inv.d * x + inv.e * y + inv.f
        return row - 0.5, col - 0.5

    z = np.asarray(dem, dtype=np.float64)
    ra, ca = rc(*a_xy)
    rb, cb = rc(*b_xy)
    za = float(bilinear(z, np.array([ra]), np.array([ca]))[0]) + ha
    zb = float(bilinear(z, np.array([rb]), np.array([cb]))[0]) + hb
    total = math.hypot(b_xy[0] - a_xy[0], b_xy[1] - a_xy[1])
    n = max(2, int(total / step))
    f = np.arange(1, n) / n
    d = f * total
    line = za + (zb - za) * f
    bulge = d * (total - d) / (2.0 * R_MARS)
    zt = bilinear(z, ra + (rb - ra) * f, ca + (cb - ca) * f)
    blocked = ~np.isnan(zt) & (zt + bulge > line)
    return not bool(blocked.any())


def relays_per_sample(plan: dict) -> list[list[str]]:
    """For each margin sample, the relay ids the rover must be seen from: the relay of the
    station its leg ends at (the rover's last relay for the walk home), and at a station where
    the rover then moves, the next relay as well."""
    st = plan["stations"]
    end = plan["rover"]["ends_at"]

    def relay_of(k):
        return st[k]["relay"] if k < len(st) else end

    out = []
    for m in plan["margins"]:
        k = int(m.get("leg", 0))
        ids = [relay_of(k)]
        if m.get("station") is not None and k + 1 <= len(st) and relay_of(k + 1) != ids[0]:
            ids.append(relay_of(k + 1))
        out.append(ids)
    return out


def samples_in_sight(plan: dict, dem, transform, antenna_m: float, helmet_m: float) -> list[bool]:
    relay_xy = {r["id"]: r["xy_m"] for r in plan["rover"]["relays"]}
    out = []
    for m, ids in zip(plan["margins"], relays_per_sample(plan), strict=True):
        out.append(
            all(
                line_of_sight(dem, transform, relay_xy[i], m["xy_m"], antenna_m, helmet_m)
                for i in ids
            )
        )
    return out
