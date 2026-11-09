# Written with AI assistance (Claude Code). See AI_USE.md.
"""Per-cell confidence (PROMPT.md 4.10). Label: MODELED.

Confidence (0 to 1) is a weighted mean of three scores: the DEM source class (HiRISE stereo
scores highest), nearness to ground imagery (exp(-distance / scale)), and the absence of model
flags. Curiosity's localizations stand in for the camera positions of its ground images; the
PLACES image table (view_metadata.csv) would be the better source and is still to check.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from ariadne.fetch.coverage import HIRISE, NODATA, OTHER


def distance_to_points(shape, transform, xs, ys) -> np.ndarray:
    """Distance (m) from each cell to the nearest of the given map points inside the grid."""
    h, w = shape
    inv = ~transform
    cols = np.floor(inv.a * np.asarray(xs) + inv.b * np.asarray(ys) + inv.c).astype(int)
    rows = np.floor(inv.d * np.asarray(xs) + inv.e * np.asarray(ys) + inv.f).astype(int)
    ok = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)
    seeds = np.ones((h, w), dtype=bool)
    seeds[rows[ok], cols[ok]] = False
    if seeds.all():
        return np.full((h, w), np.inf, dtype=np.float32)
    return (ndimage.distance_transform_edt(seeds) * transform.a).astype(np.float32)


def confidence(
    source_class, image_distance_m, flags, source_score: dict, scale_m: float, weights: dict
):
    src = np.select(
        [source_class == HIRISE, source_class == OTHER],
        [source_score["hirise"], source_score["other"]],
        default=source_score["nodata"],
    ).astype(np.float64)
    img = np.exp(-np.asarray(image_distance_m, dtype=np.float64) / scale_m)
    flg = 1.0 - np.clip(np.asarray(flags, dtype=np.float64) / 2.0, 0.0, 1.0)
    wsum = weights["source"] + weights["imagery"] + weights["flags"]
    conf = (weights["source"] * src + weights["imagery"] * img + weights["flags"] * flg) / wsum
    conf = np.where(source_class == NODATA, 0.0, conf)
    return np.clip(conf, 0.0, 1.0).astype(np.float32)
