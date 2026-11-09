# Written with AI assistance (Claude Code). See AI_USE.md.
"""Boxwork ridges, hollows and dark central fractures (PROMPT.md 4.4). Label: MODELED.

Ridges and hollows come from the topographic position index at 10 m and local relief on the
1 m DEM (both sites lie fully on HiRISE stereo, so the DEM route applies). Fractures are dark
lines found by a multi-scale Sato line filter on the 25 cm orthophoto, kept inside the ridge
mask, thinned to one-pixel skeletons at 0.5 m, and kept when 10 m or longer. Each fracture is
written as a line ordered along its main axis, which suits the mostly straight boxwork
fractures but simplifies curved or branching ones.
"""

from __future__ import annotations

import numpy as np
from affine import Affine
from scipy import ndimage
from skimage.filters import sato
from skimage.morphology import skeletonize

OTHER, RIDGE, HOLLOW = 0, 1, 2


def ridge_hollow(tpi10, relief, tpi_ridge: float, tpi_hollow: float, relief_min: float):
    t = np.asarray(tpi10, dtype=np.float64)
    r = np.asarray(relief, dtype=np.float64)
    out = np.full(t.shape, OTHER, dtype=np.uint8)
    out[(t > tpi_ridge) & (r >= relief_min)] = RIDGE
    out[t < tpi_hollow] = HOLLOW
    return out


def stretch_limits(img: np.ndarray, step: int = 4) -> tuple[float, float]:
    """2nd and 98th percentiles of the valid pixels (min and max if those coincide)."""
    v = img[::step, ::step]
    v = v[v > 0]
    if v.size == 0:
        return 0.0, 1.0
    lo, hi = (float(x) for x in np.percentile(v, [2, 98]))
    if hi - lo < 1.0:
        lo, hi = float(v.min()), float(v.max())
    return lo, max(hi, lo + 1.0)


def normalise(img: np.ndarray, limits: tuple[float, float]) -> np.ndarray:
    """Scale an 8-bit image to 0 to 1 between fixed limits (0 = no data becomes NaN)."""
    lo, hi = limits
    out = np.clip((img.astype(np.float32) - lo) / (hi - lo), 0, 1)
    out[img == 0] = np.nan
    return out


def fracture_mask(
    img: np.ndarray,
    ridge_on_img: np.ndarray,
    sigmas,
    threshold: float,
    tile: int = 2048,
    pad: int = 16,
) -> np.ndarray:
    """Dark-line pixels (bool, image grid) inside the ridge mask, computed tile by tile."""
    h, w = img.shape
    out = np.zeros((h, w), dtype=bool)
    limits = stretch_limits(img)  # one stretch for the whole image, so tiles agree
    for r0 in range(0, h, tile):
        for c0 in range(0, w, tile):
            r1, c1 = min(h, r0 + tile), min(w, c0 + tile)
            ra, ca = max(0, r0 - pad), max(0, c0 - pad)
            rb, cb = min(h, r1 + pad), min(w, c1 + pad)
            ridge = ridge_on_img[ra:rb, ca:cb]
            if not ridge.any():
                continue
            sub = normalise(img[ra:rb, ca:cb], limits)
            sub = np.where(np.isnan(sub), np.nanmedian(sub) if np.isfinite(sub).any() else 0.5, sub)
            resp = sato(sub, sigmas=list(sigmas), black_ridges=True)
            hit = (resp > threshold) & ridge
            out[r0:r1, c0:c1] = hit[r0 - ra : r0 - ra + (r1 - r0), c0 - ca : c0 - ca + (c1 - c0)]
    return out


def skeleton_lines(mask: np.ndarray, transform: Affine, min_length_m: float):
    """Skeletonize a line mask; return GeoJSON-style line features 10 m or longer and the skeleton.

    Length is the skeleton's path length (diagonal steps count sqrt 2).
    """
    sk = skeletonize(mask)
    lab, n = ndimage.label(sk, structure=np.ones((3, 3)))
    res = transform.a
    feats = []
    if n == 0:
        return feats, sk
    # path length per component: count orthogonal and diagonal neighbour links once each
    rows, cols = np.nonzero(sk)
    ids = lab[rows, cols]
    order = np.argsort(ids)
    rows, cols, ids = rows[order], cols[order], ids[order]
    bounds = np.searchsorted(ids, np.arange(1, n + 2))
    for comp in range(n):
        a, b = bounds[comp], bounds[comp + 1]
        if b - a < 2:
            continue
        rr, cc = rows[a:b].astype(float), cols[a:b].astype(float)
        pts = np.stack([cc, rr], axis=1)
        centre = pts.mean(axis=0)
        u, s, vt = np.linalg.svd(pts - centre, full_matrices=False)
        proj = (pts - centre) @ vt[0]
        o = np.argsort(proj)
        ordered = pts[o]
        steps = np.hypot(*np.diff(ordered, axis=0).T)
        length = float(np.sum(np.minimum(steps, np.sqrt(2.0)))) * res
        if length < min_length_m:
            continue
        xs = transform.c + (ordered[:, 0] + 0.5) * transform.a
        ys = transform.f + (ordered[:, 1] + 0.5) * transform.e
        keep = np.unique(np.linspace(0, len(xs) - 1, min(len(xs), 200)).astype(int))
        feats.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [round(float(x), 2), round(float(y), 2)]
                        for x, y in zip(xs[keep], ys[keep], strict=True)
                    ],
                },
                "properties": {"length_m": round(length, 1), "label": "MODELED"},
            }
        )
    return feats, sk
