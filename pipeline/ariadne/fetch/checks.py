# Written with AI assistance (Claude Code). See AI_USE.md.
"""Georeferencing checks: does Curiosity's recorded path sit on the right terrain? (B8)

The DEM crop is sampled (bilinear) at each PLACES localization and compared with the PLACES
elevation. If the crop were shifted, the residuals would spread out, so the same comparison
is repeated for horizontal shifts of up to +-10 m and the shift with the tightest residuals is
reported. Pass thresholds are team targets (docs/PROGRESS.md, Phase 1).
"""

from __future__ import annotations

import numpy as np
from affine import Affine
from scipy.ndimage import map_coordinates

MAX_MEDIAN_OFFSET_M = 2.0
MAX_BEST_SHIFT_M = 2.0


def sample_bilinear(dem: np.ndarray, transform: Affine, east, north, nodata) -> np.ndarray:
    """DEM values at points (meters), NaN where outside or touching nodata."""
    inv = ~transform
    cols, rows = inv * (np.asarray(east, float), np.asarray(north, float))
    # map_coordinates indexes pixel centers, which sit at (col + 0.5, row + 0.5) in grid units.
    coords = np.vstack([rows - 0.5, cols - 0.5])
    arr = dem.astype("float64")
    bad = ~np.isfinite(arr) if nodata is None else (arr == nodata) | ~np.isfinite(arr)
    arr = np.where(bad, np.nan, arr)
    vals = map_coordinates(arr, coords, order=1, mode="constant", cval=np.nan)
    return vals


def _robust_spread(res: np.ndarray) -> float:
    r = res[np.isfinite(res)]
    return float(np.median(np.abs(r - np.median(r)))) if len(r) else float("nan")


def georeference_check(
    dem, transform, nodata, east, north, elevation, max_shift_m=10, step_m=1.0
) -> dict:
    east, north, elevation = (np.asarray(a, float) for a in (east, north, elevation))
    res0 = sample_bilinear(dem, transform, east, north, nodata) - elevation
    ok = np.isfinite(res0)
    r = res0[ok]
    shifts = np.arange(-max_shift_m, max_shift_m + step_m / 2, step_m)
    grid = np.full((len(shifts), len(shifts)), np.nan)
    for i, dy in enumerate(shifts):
        for j, dx in enumerate(shifts):
            res = sample_bilinear(dem, transform, east + dx, north + dy, nodata) - elevation
            grid[i, j] = _robust_spread(res)
    i, j = np.unravel_index(np.nanargmin(grid), grid.shape)
    best = (float(shifts[j]), float(shifts[i]))
    median = float(np.median(r)) if len(r) else float("nan")
    passed = (
        len(r) > 0
        and abs(median) <= MAX_MEDIAN_OFFSET_M
        and abs(best[0]) <= MAX_BEST_SHIFT_M
        and abs(best[1]) <= MAX_BEST_SHIFT_M
    )
    return {
        "points": int(len(r)),
        "points_outside_or_nodata": int((~ok).sum()),
        "median_dem_minus_places_m": median,
        "mad_m": _robust_spread(res0),
        "p90_abs_deviation_m": float(np.percentile(np.abs(r - median), 90))
        if len(r)
        else float("nan"),
        "best_shift_east_north_m": best,
        "mad_at_best_shift_m": float(grid[i, j]),
        "search": {"max_shift_m": max_shift_m, "step_m": step_m},
        "thresholds": {
            "max_median_offset_m": MAX_MEDIAN_OFFSET_M,
            "max_best_shift_m": MAX_BEST_SHIFT_M,
        },
        "passed": bool(passed),
    }
