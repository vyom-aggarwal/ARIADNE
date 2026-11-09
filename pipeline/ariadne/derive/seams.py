# Written with AI assistance (Claude Code). See AI_USE.md.
"""Candidate DEM mosaic seams from the USGS stereo-pair footprints. Label: DERIVED.

The merged Gale DEM switches source where one HiRISE stereo pair's DTM gives way to another (or
to CTX, HRSC or MOLA). The mosaic does not record which pair wins in an overlap, so every edge
of a pair's footprint inside the DEM is a candidate seam. Kirk et al. 2021 report that the
individual Gale HiRISE DTMs were mosaicked without rigorous registration, leaving vertical
discontinuities. The footprints come from ODE and are uncertain by about 30 m.
"""

from __future__ import annotations

import numpy as np
from affine import Affine
from rasterio.features import rasterize
from scipy import ndimage, stats
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def seam_lines(footprints: list[BaseGeometry], extent: Polygon) -> BaseGeometry:
    """Edges of the footprints that lie inside the DEM extent (the crop edge is not a seam)."""
    edges = [g.boundary for g in footprints if not g.is_empty]
    if not edges:
        return Polygon().boundary
    inside = unary_union(edges).intersection(extent)
    return inside.difference(extent.exterior.buffer(1e-6))


def seam_distance(shape: tuple[int, int], transform: Affine, lines: BaseGeometry) -> np.ndarray:
    """Distance (m) from each cell centre to the nearest cell a seam line touches."""
    if lines.is_empty:
        return np.full(shape, np.inf, dtype=np.float32)
    hit = rasterize(
        [(lines, 1)], out_shape=shape, transform=transform, fill=0, all_touched=True, dtype="uint8"
    )
    if not hit.any():
        return np.full(shape, np.inf, dtype=np.float32)
    return (ndimage.distance_transform_edt(hit == 0) * abs(transform.a)).astype(np.float32)


def model_flags(source_class, edge_distance_m, edge_min_m: float, seam_zone) -> np.ndarray:
    """Number of model flags per cell: DEM not HiRISE stereo, near-field horizon cut short by
    the crop edge, and inside a candidate seam zone."""
    return (
        (np.asarray(source_class) != 1).astype(np.uint8)
        + (np.asarray(edge_distance_m) < edge_min_m).astype(np.uint8)
        + np.asarray(seam_zone, dtype=bool).astype(np.uint8)
    )


def zone_statistics(in_zone, nogo) -> dict:
    """How no-go points split between the seam zone and the rest, with Fisher's exact test."""
    z = np.asarray(in_zone, dtype=bool)
    n = np.asarray(nogo, dtype=bool)
    a, b = int((z & n).sum()), int((z & ~n).sum())
    c, d = int((~z & n).sum()), int((~z & ~n).sum())
    odds, p = stats.fisher_exact([[a, b], [c, d]])
    total = a + b + c + d

    def ratio(x, y):
        return round(x / y, 4) if y else None

    return {
        "points": total,
        "points_in_zone": a + b,
        "share_of_points_in_zone": ratio(a + b, total),
        "no_go_total": a + c,
        "no_go_in_zone": a,
        "share_of_no_go_in_zone": ratio(a, a + c),
        "no_go_rate_in_zone": ratio(a, a + b),
        "no_go_rate_outside": ratio(c, c + d),
        "odds_ratio": round(float(odds), 3) if np.isfinite(odds) else None,
        "fisher_p": float(f"{p:.4g}"),
    }


def overcautious(slope_deg, nogo_deg: float, seam_zone, confidence, low_confidence: float):
    """Where the map may be over-cautious: cells that are no-go by slope and lie in a candidate
    seam zone or a low-confidence zone. 1 = flag, 0 = not, 255 = no slope. The rover check can
    only measure false alarms (no-go where Curiosity drove), and those cluster at seams, so the
    surfaces ask the crew to check these cells by eye rather than treat them as walls."""
    s = np.asarray(slope_deg, dtype=np.float64)
    nogo = s > nogo_deg
    doubt = np.asarray(seam_zone, dtype=bool) | (np.asarray(confidence) < low_confidence)
    out = (nogo & doubt).astype(np.uint8)
    out[~np.isfinite(s)] = 255
    return out
