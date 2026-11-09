# Written with AI assistance (Claude Code). See AI_USE.md.
"""Terrain basics (PROMPT.md 4.1): slope, aspect, roughness, topographic position, relief.

Arrays are north-up rasters with square pixels of `res` metres: row index grows southward,
column index grows eastward. NaN marks missing elevation and propagates.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage, signal


def slope_aspect(dem: np.ndarray, res: float) -> tuple[np.ndarray, np.ndarray]:
    """Horn (1981) slope and aspect in degrees.

    Aspect is the compass direction the slope faces (downhill), clockwise from north; it is NaN
    where the ground is flat. Edge cells use replicated neighbours.
    """
    z = np.pad(np.asarray(dem, dtype=np.float64), 1, mode="edge")
    a, b, c = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
    d, f = z[1:-1, :-2], z[1:-1, 2:]
    g, h, i = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]
    dz_east = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * res)
    dz_north = ((a + 2 * b + c) - (g + 2 * h + i)) / (8 * res)
    grad = np.hypot(dz_east, dz_north)
    slope = np.degrees(np.arctan(grad))
    aspect = np.degrees(np.arctan2(-dz_east, -dz_north)) % 360.0
    aspect = np.where(grad > 1e-12, aspect, np.nan)
    return slope.astype(np.float32), aspect.astype(np.float32)


def _window_px(window_m: float, res: float) -> int:
    w = int(round(window_m / res))
    return w if w % 2 == 1 else w + 1


def roughness(dem: np.ndarray, res: float, window_m: float = 5.0) -> np.ndarray:
    """Standard deviation of elevation about the best-fit plane in a square window.

    A plane (tilted or flat) gives zero. Computed with box sums: in centred window coordinates,
    the plane fit's x and y terms are orthogonal to the mean, so the residual variance is
    mean(z^2) - mean(z)^2 - (sum x z)^2 / (N sum x^2) - (sum y z)^2 / (N sum y^2).
    """
    w = _window_px(window_m, res)
    k = w // 2
    z = np.asarray(dem, dtype=np.float64)
    z = z - np.nanmean(z)  # keep the sums small for precision
    n = float(w * w)
    offs = np.arange(-k, k + 1, dtype=np.float64)
    sum_x2 = w * float((offs**2).sum())
    ones = np.ones((w, w))
    xk = np.tile(offs, (w, 1))  # column offset (east)
    yk = xk.T  # row offset
    mode = "nearest"
    s_z = ndimage.correlate(z, ones, mode=mode)
    s_zz = ndimage.correlate(z * z, ones, mode=mode)
    s_xz = ndimage.correlate(z, xk, mode=mode)
    s_yz = ndimage.correlate(z, yk, mode=mode)
    var = s_zz / n - (s_z / n) ** 2 - (s_xz**2) / (n * sum_x2) - (s_yz**2) / (n * sum_x2)
    return np.sqrt(np.clip(var, 0.0, None)).astype(np.float32)


def disc_kernel(radius_px: int, exclude_centre: bool = True) -> np.ndarray:
    r = radius_px
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    k = ((xx**2 + yy**2) <= r * r).astype(np.float64)
    if exclude_centre:
        k[r, r] = 0.0
    return k / k.sum()


def tpi(dem: np.ndarray, res: float, radius_m: float) -> np.ndarray:
    """Topographic position index: elevation minus the mean within a disc of `radius_m`.

    Edges are padded by reflection. Positive on crests, negative in hollows, zero on planes
    (away from the edge).
    """
    r = max(1, int(round(radius_m / res)))
    z = np.asarray(dem, dtype=np.float64)
    offset = np.nanmean(z)
    zp = np.pad(z - offset, r, mode="reflect")
    mean = signal.oaconvolve(zp, disc_kernel(r), mode="valid")
    return ((z - offset) - mean).astype(np.float32)


def local_relief(dem: np.ndarray, res: float, radius_m: float) -> np.ndarray:
    """Maximum minus minimum elevation in a square window of half-width `radius_m`."""
    size = 2 * max(1, int(round(radius_m / res))) + 1
    z = np.asarray(dem, dtype=np.float64)
    return (
        ndimage.maximum_filter(z, size=size, mode="nearest")
        - ndimage.minimum_filter(z, size=size, mode="nearest")
    ).astype(np.float32)


def convexity(dem: np.ndarray, res: float) -> np.ndarray:
    """Negative Laplacian of elevation (1/m): positive on convex edges and crests."""
    z = np.asarray(dem, dtype=np.float64)
    return (-ndimage.laplace(z, mode="nearest") / (res * res)).astype(np.float32)
