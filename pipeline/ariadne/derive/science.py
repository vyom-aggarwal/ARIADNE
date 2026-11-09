# Written with AI assistance (Claude Code). See AI_USE.md.
"""Science value: three-station transects across boxwork ridges (PROMPT.md 4.9). Label: MODELED.

Along each ridge crest of at least the minimum length, every `spacing` metres: a crest station
(moved onto a mapped fracture if one lies within `fracture_snap`), a wall station 1 to 2 m down
the flank, and a hollow station 3 to 10 m away on the same side, all on walkable ground. Each
station's score is the weighted mean of hypothesis role, novelty, spectral context and access,
over the terms that are available; a missing term is reported, never filled in.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage
from skimage.morphology import skeletonize

from ariadne.derive.ridges import HOLLOW, RIDGE
from ariadne.derive.walkability import NOGO


def score(terms: dict[str, float | None], weights: dict[str, float]) -> tuple[float, list[str]]:
    """Weighted mean of the available terms (each 0 to 1) and the list of missing ones."""
    used = {k: v for k, v in terms.items() if v is not None}
    missing = [k for k, v in terms.items() if v is None]
    wsum = sum(weights[k] for k in used)
    if wsum == 0:
        return float("nan"), missing
    return sum(weights[k] * used[k] for k in used) / wsum, missing


def novelty(distance_m: float, scale_m: float) -> float:
    return float(min(1.0, max(0.0, distance_m / scale_m)))


def access(minutes: float | None, scale_min: float) -> float | None:
    if minutes is None or not math.isfinite(minutes):
        return None
    return float(1.0 - min(1.0, max(0.0, minutes / scale_min)))


def crest_segments(ridge_class: np.ndarray, res: float, min_length_m: float):
    """Skeleton crest lines of ridge areas, as lists of (row, col) ordered along each crest."""
    sk = skeletonize(ridge_class == RIDGE)
    lab, n = ndimage.label(sk, structure=np.ones((3, 3)))
    segs = []
    rows, cols = np.nonzero(sk)
    ids = lab[rows, cols]
    order = np.argsort(ids, kind="stable")
    rows, cols, ids = rows[order], cols[order], ids[order]
    bounds = np.searchsorted(ids, np.arange(1, n + 2))
    for i in range(n):
        a, b = bounds[i], bounds[i + 1]
        if b - a < 2:
            continue
        pts = np.stack([rows[a:b], cols[a:b]], axis=1).astype(float)
        c = pts.mean(axis=0)
        _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
        o = np.argsort((pts - c) @ vt[0])
        ordered = pts[o]
        length = (
            float(np.sum(np.minimum(np.hypot(*np.diff(ordered, axis=0).T), math.sqrt(2)))) * res
        )
        if length >= min_length_m:
            segs.append({"points": ordered.astype(int), "length_m": length})
    return segs


def _local_normal(points: np.ndarray, k: int, half: int) -> np.ndarray:
    lo, hi = max(0, k - half), min(len(points), k + half + 1)
    p = points[lo:hi].astype(float)
    if len(p) < 2:
        return np.array([1.0, 0.0])
    _, _, vt = np.linalg.svd(p - p.mean(axis=0), full_matrices=False)
    d = vt[0]
    return np.array([-d[1], d[0]])  # perpendicular, in (row, col)


def transects(
    ridge_class,
    dem,
    walk_class,
    fracture_1m,
    res: float,
    spacing_m: float,
    min_length_m: float,
    wall_range: tuple[float, float],
    hollow_range: tuple[float, float],
    snap_m: float,
):
    """Transect triples as dicts of (row, col) stations with their roles."""
    h, w = dem.shape
    out = []
    frac_rc = np.argwhere(fracture_1m) if fracture_1m is not None else np.empty((0, 2))
    tree = None
    if len(frac_rc):
        from scipy.spatial import cKDTree

        tree = cKDTree(frac_rc)

    def ok(r, c):
        return 0 <= r < h and 0 <= c < w and walk_class[r, c] != NOGO and np.isfinite(dem[r, c])

    step = max(1, int(round(spacing_m / res)))
    for seg_id, seg in enumerate(crest_segments(ridge_class, res, min_length_m)):
        pts = seg["points"]
        for k in range(step // 2, len(pts), step):
            r0, c0 = int(pts[k][0]), int(pts[k][1])
            if not ok(r0, c0):
                continue
            role = "crest"
            if tree is not None:
                d, j = tree.query([r0, c0])
                if d * res <= snap_m:
                    rr, cc = int(frac_rc[j][0]), int(frac_rc[j][1])
                    if ok(rr, cc):
                        r0, c0, role = rr, cc, "fracture"
            nrm = _local_normal(pts, k, max(2, int(5 / res)))
            best = None
            for side in (1.0, -1.0):
                wall = None
                for dist in np.arange(wall_range[0], wall_range[1] + 1e-9, res):
                    r = int(round(r0 + side * nrm[0] * dist / res))
                    c = int(round(c0 + side * nrm[1] * dist / res))
                    if ok(r, c) and dem[r, c] < dem[r0, c0]:
                        wall = (r, c, float(dist))
                        break
                if wall is None:
                    continue
                hollow = None
                for dist in np.arange(hollow_range[0], hollow_range[1] + 1e-9, res):
                    r = int(round(r0 + side * nrm[0] * dist / res))
                    c = int(round(c0 + side * nrm[1] * dist / res))
                    if ok(r, c) and ridge_class[r, c] == HOLLOW:
                        hollow = (r, c, float(dist))
                        break
                if hollow is None:
                    continue
                drop = float(dem[r0, c0] - dem[hollow[0], hollow[1]])
                if best is None or drop > best[2]:
                    best = (wall, hollow, drop)
            if best is None:
                continue
            wall, hollow, drop = best
            out.append(
                {
                    "segment": seg_id,
                    "crest": (r0, c0, role),
                    "wall": wall,
                    "hollow": hollow,
                    "relief_m": drop,
                }
            )
    return out
