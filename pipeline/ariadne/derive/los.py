# Written with AI assistance (Claude Code). See AI_USE.md.
"""Line of sight (PROMPT.md 4.7): line of sight only; radio propagation is not modeled.

`viewshed` casts one ray from the observer to every cell on the edge of a square of the given
range (one ray per edge cell, so every cell lies within half a pixel of some ray), keeps the
steepest terrain angle met so far along each ray, and marks a cell visible when a target
`target_height` above it is at or above that angle. `line_of_sight` tests one pair of points.
Both subtract the curvature drop d^2 / (2 R).
"""

from __future__ import annotations

import math

import numpy as np
from numba import njit

from ariadne.derive.horizons import R_MARS, _bilinear


@njit(cache=True)
def _cast(z, vis, r0, c0, z0, tgt_h, er, ec, res):
    h, w = z.shape
    dr = er - r0
    dc = ec - c0
    n = max(abs(dr), abs(dc))
    best = -1e30
    for s in range(1, n + 1):
        rr = r0 + dr * s / n
        cc = c0 + dc * s / n
        i = int(round(rr))
        j = int(round(cc))
        if i < 0 or j < 0 or i >= h or j >= w:
            break
        zt = z[i, j]
        if math.isnan(zt):
            continue
        d = math.hypot(rr - r0, cc - c0) * res
        curv = d * d / (2.0 * 3_396_190.0)
        if (zt + tgt_h - curv - z0) / d >= best:
            vis[i, j] = 1
        g = (zt - curv - z0) / d
        if g > best:
            best = g


@njit(cache=True)
def _viewshed(z, r0, c0, obs_h, tgt_h, rng_px, res):
    h, w = z.shape
    vis = np.zeros((h, w), dtype=np.uint8)
    z0 = z[r0, c0] + obs_h
    vis[r0, c0] = 1
    for k in range(-rng_px, rng_px + 1):
        _cast(z, vis, r0, c0, z0, tgt_h, r0 - rng_px, c0 + k, res)
        _cast(z, vis, r0, c0, z0, tgt_h, r0 + rng_px, c0 + k, res)
        _cast(z, vis, r0, c0, z0, tgt_h, r0 + k, c0 - rng_px, res)
        _cast(z, vis, r0, c0, z0, tgt_h, r0 + k, c0 + rng_px, res)
    return vis


def viewshed(
    dem, res: float, observer_rc, observer_height: float, target_height: float, max_range_m: float
):
    """Cells (bool) from which a target `target_height` up is visible to the observer, in range."""
    rng = int(max_range_m / res)
    z = np.ascontiguousarray(dem, dtype=np.float64)
    vis = _viewshed(
        z,
        int(observer_rc[0]),
        int(observer_rc[1]),
        float(observer_height),
        float(target_height),
        rng,
        float(res),
    )
    return vis.astype(bool)


def line_of_sight(
    dem, transform, a_xy, b_xy, ha: float, hb: float, step_m: float | None = None
) -> bool:
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
    za = _bilinear(z, ra, ca) + ha
    zb = _bilinear(z, rb, cb) + hb
    total = math.hypot(b_xy[0] - a_xy[0], b_xy[1] - a_xy[1])
    n = max(2, int(total / step))
    for k in range(1, n):
        f = k / n
        d = f * total
        line = za + (zb - za) * f
        # curvature: the chord between the two points bulges above the sphere by d (L - d) / 2R
        bulge = d * (total - d) / (2.0 * R_MARS)
        zt = _bilinear(z, ra + (rb - ra) * f, ca + (cb - ca) * f)
        if not math.isnan(zt) and zt + bulge > line:
            return False
    return True
