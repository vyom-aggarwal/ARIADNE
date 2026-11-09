# Written with AI assistance (Claude Code). See AI_USE.md.
"""Horizon angles in many azimuths (PROMPT.md 4.2), near field plus far field.

Azimuth is clockwise from north: 0 = north, 90 = east. Angles are degrees above the
astronomical horizon, measured from `observer_height` above the ground. Both fields subtract
the planet's curvature, d^2 / (2 R), from the height of each sample; refraction is ignored
(Mars's atmosphere is about 1% of Earth's).

Near field: rays on the 1 m DEM, 1 m steps out to `fine_until`, then steps growing by a fixed
factor, out to `near_max` or until the ray leaves the crop. Samples are bilinear.

Far field: rays on a coarse regional DEM (MOLA) from where the near field stops to `far_max`,
traced from a coarse grid of observers. For each observer and azimuth we keep the profile
maximum T = max (z_t - curvature - z_obs) / d and the distance d* where it occurs; a fine cell
then takes tan h = T + (z_obs_coarse - z_obs_fine) / d*, interpolated from the coarse grid,
which corrects to first order for its own elevation.

Stored horizons are uint8: code = round((h - quant_min) / quant_step), 255 = no data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from affine import Affine
from numba import njit, prange
from scipy import ndimage

R_MARS = 3_396_190.0
NODATA_CODE = 255


def apply_transform(transform: Affine, x, y) -> tuple[np.ndarray, np.ndarray]:
    """(x, y) through an affine transform, elementwise (affine deprecates `*` on tuples)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    return (
        transform.a * x + transform.b * y + transform.c,
        transform.d * x + transform.e * y + transform.f,
    )


def azimuths(n: int) -> np.ndarray:
    return np.arange(n, dtype=np.float64) * (360.0 / n)


def near_distances(max_dist: float, res: float, fine_until: float, growth: float) -> np.ndarray:
    """Sample distances (metres): every pixel out to `fine_until`, then growing geometrically."""
    d = list(np.arange(1, int(round(fine_until / res)) + 1) * res)
    if not d:
        d = [res]
    while d[-1] * growth < max_dist:
        d.append(max(d[-1] * growth, d[-1] + res))
    if d[-1] < max_dist:
        d.append(max_dist)
    return np.array([x for x in d if x <= max_dist + 1e-9], dtype=np.float64)


def far_distances(start: float, max_dist: float, min_step: float, growth: float) -> np.ndarray:
    """Far-field sample distances from 0 to `max_dist`; each observer uses those past its start."""
    d = [min_step]
    while d[-1] < max_dist:
        d.append(d[-1] + max(min_step, d[-1] * (growth - 1.0)))
    out = np.array(d, dtype=np.float64)
    return out[out >= start] if start > 0 else out


@njit(cache=True)
def _bilinear(z, rr, cc):
    h, w = z.shape
    if rr < 0.0 or cc < 0.0 or rr > h - 1 or cc > w - 1:
        return np.nan
    i0 = int(math.floor(rr))
    j0 = int(math.floor(cc))
    i1 = min(i0 + 1, h - 1)
    j1 = min(j0 + 1, w - 1)
    fy = rr - i0
    fx = cc - j0
    top = z[i0, j0] * (1.0 - fx) + z[i0, j1] * fx
    bot = z[i1, j0] * (1.0 - fx) + z[i1, j1] * fx
    return top * (1.0 - fy) + bot * fy


@njit(parallel=True, cache=True)
def _near_band_tan(z, dr, dc, dist, curv, obs_h):
    """Max tangent of the elevation angle along one azimuth for every cell (-inf if no sample)."""
    h, w = z.shape
    out = np.full((h, w), -np.inf)
    k_n = dist.size
    for r in prange(h):
        best = np.full(w, -np.inf)
        for k in range(k_n):
            rr = r + dr[k]
            if rr < 0.0 or rr > h - 1:
                continue
            i0 = int(math.floor(rr))
            i1 = min(i0 + 1, h - 1)
            fy = rr - i0
            jo = int(math.floor(dc[k]))
            fx = dc[k] - jo
            # valid columns: 0 <= c + dc <= w - 1
            c_lo = max(0, -jo)
            c_hi = min(w - 1, w - 1 - jo)
            if fx > 0.0:
                c_hi = min(c_hi, w - 2 - jo)
            d = dist[k]
            cv = curv[k]
            for c in range(c_lo, c_hi + 1):
                j0 = c + jo
                j1 = j0 + 1 if fx > 0.0 else j0
                top = z[i0, j0] * (1.0 - fx) + z[i0, j1] * fx
                bot = z[i1, j0] * (1.0 - fx) + z[i1, j1] * fx
                zz = top * (1.0 - fy) + bot * fy
                t = (zz - cv - (z[r, c] + obs_h)) / d
                if t > best[c]:
                    best[c] = t
        for c in range(w):
            out[r, c] = best[c]
    return out


def ray_offsets(az_deg: float, dist: np.ndarray, res: float) -> tuple[np.ndarray, np.ndarray]:
    a = math.radians(az_deg)
    return -dist * math.cos(a) / res, dist * math.sin(a) / res


def near_field_band(
    dem: np.ndarray,
    res: float,
    az_deg: float,
    dist: np.ndarray,
    observer_height: float,
) -> np.ndarray:
    """Near-field horizon angle (degrees) along one azimuth for every cell.

    Cells whose ray leaves the crop at once get -90; NaN elevations give NaN.
    """
    z = np.ascontiguousarray(dem, dtype=np.float64)
    dr, dc = ray_offsets(az_deg, dist, res)
    curv = dist**2 / (2.0 * R_MARS)
    tan = _near_band_tan(z, dr, dc, dist, curv, float(observer_height))
    h = np.degrees(np.arctan(tan))
    h[np.isnan(z)] = np.nan
    return h.astype(np.float32)


@njit(parallel=True, cache=True)
def _profile_max_points(z, rows0, cols0, zobs, dr_unit, dc_unit, dist, start, res):
    """For points (fractional pixel coords) and azimuth unit offsets, max tan and its distance."""
    n_pts = rows0.size
    n_az = dr_unit.size
    tmax = np.full((n_pts, n_az), -np.inf)
    dstar = np.full((n_pts, n_az), np.nan)
    for p in prange(n_pts):
        for a in range(n_az):
            s = start[p, a]
            for k in range(dist.size):
                d = dist[k]
                if d < s:
                    continue
                zz = _bilinear(z, rows0[p] + dr_unit[a] * d / res, cols0[p] + dc_unit[a] * d / res)
                if np.isnan(zz):
                    continue
                t = (zz - d * d / (2.0 * 3_396_190.0) - zobs[p]) / d
                if t > tmax[p, a]:
                    tmax[p, a] = t
                    dstar[p, a] = d
    return tmax, dstar


def profile_max_at_points(
    dem: np.ndarray,
    transform: Affine,
    xs: np.ndarray,
    ys: np.ndarray,
    zobs: np.ndarray,
    az_deg: np.ndarray,
    dist: np.ndarray,
    start: np.ndarray | float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Profile maximum tangent T and its distance d* for observers at map coordinates.

    `dem` must be north-up with square pixels; `zobs` already includes the observer height.
    `start` (scalar or points x azimuths) skips samples nearer than that distance.
    """
    res = transform.a
    if not math.isclose(-transform.e, res, rel_tol=1e-9):
        raise ValueError("profile_max_at_points needs square, north-up pixels")
    inv = ~transform
    cols, rows = apply_transform(inv, xs, ys)
    # pixel-centre coordinates: the centre of pixel (0, 0) is at (0.5, 0.5) in GDAL terms
    rows = np.asarray(rows) - 0.5
    cols = np.asarray(cols) - 0.5
    a = np.radians(np.asarray(az_deg, dtype=np.float64))
    start_arr = np.broadcast_to(np.asarray(start, dtype=np.float64), (rows.size, a.size)).copy()
    return _profile_max_points(
        np.ascontiguousarray(dem, dtype=np.float64),
        rows.ravel(),
        cols.ravel(),
        np.asarray(zobs, dtype=np.float64).ravel(),
        -np.cos(a),
        np.sin(a),
        np.asarray(dist, dtype=np.float64),
        start_arr,
        float(res),
    )


def horizons_at_points(
    dem: np.ndarray,
    transform: Affine,
    xs: np.ndarray,
    ys: np.ndarray,
    az_deg: np.ndarray,
    dist: np.ndarray,
    observer_height: float,
) -> np.ndarray:
    """Near-field horizon angles (degrees) at map points, shape (points, azimuths)."""
    z0 = sample_bilinear(dem, transform, xs, ys) + observer_height
    tmax, _ = profile_max_at_points(dem, transform, xs, ys, z0, az_deg, dist)
    return np.degrees(np.arctan(tmax))


def sample_bilinear(dem: np.ndarray, transform: Affine, xs, ys) -> np.ndarray:
    inv = ~transform
    cols, rows = apply_transform(inv, xs, ys)
    coords = np.vstack([np.ravel(rows) - 0.5, np.ravel(cols) - 0.5])
    return ndimage.map_coordinates(
        np.asarray(dem, dtype=np.float64), coords, order=1, mode="nearest"
    ).reshape(np.shape(xs))


def distance_to_box_edge(
    xs: np.ndarray, ys: np.ndarray, az_deg: np.ndarray, bounds: tuple[float, float, float, float]
) -> np.ndarray:
    """Distance from each point to the edge of `bounds` along each azimuth, (points, azimuths)."""
    left, bottom, right, top = bounds
    a = np.radians(np.asarray(az_deg, dtype=np.float64))
    sx, sy = np.sin(a)[None, :], np.cos(a)[None, :]
    x = np.asarray(xs, dtype=np.float64).ravel()[:, None]
    y = np.asarray(ys, dtype=np.float64).ravel()[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        tx = np.where(sx > 0, (right - x) / sx, np.where(sx < 0, (left - x) / sx, np.inf))
        ty = np.where(sy > 0, (top - y) / sy, np.where(sy < 0, (bottom - y) / sy, np.inf))
    return np.clip(np.minimum(tx, ty), 0.0, None)


@dataclass
class FarField:
    """Far-field profile maxima on a coarse grid (rows x cols x azimuths)."""

    tmax: np.ndarray
    dstar: np.ndarray
    zobs: np.ndarray  # observer elevation (with observer height) at each coarse node
    transform: Affine  # node (i, j) is at (c + j * spacing, f - i * spacing), clipped to the crop
    az_deg: np.ndarray
    tie_offset_m: float
    coreg: Coregistration | None = None


def coarse_grid(bounds: tuple[float, float, float, float], spacing: float) -> Affine:
    left, _, _, top = bounds
    return Affine(spacing, 0.0, left, 0.0, -spacing, top)


def coarse_shape(bounds: tuple[float, float, float, float], spacing: float) -> tuple[int, int]:
    left, bottom, right, top = bounds
    return (
        max(2, int(math.ceil((top - bottom) / spacing)) + 1),
        max(2, int(math.ceil((right - left) / spacing)) + 1),
    )


def tie_offset(fine_dem, fine_transform, coarse_dem, coarse_transform, step: int = 25) -> float:
    """Median of (fine - coarse) elevation over a subsample of the fine grid."""
    fine = np.asarray(fine_dem, dtype=np.float64)[::step, ::step]
    rows, cols = np.mgrid[0 : fine_dem.shape[0] : step, 0 : fine_dem.shape[1] : step]
    xs, ys = apply_transform(fine_transform, cols + 0.5, rows + 0.5)
    coarse = sample_bilinear(coarse_dem, coarse_transform, xs, ys)
    diff = fine - coarse
    return float(np.nanmedian(diff[np.isfinite(diff)]))


@dataclass
class Coregistration:
    """How to place the coarse DEM on the fine one: sample it at (x + dx, y + dy) and add dz."""

    dx: float
    dy: float
    dz: float
    mad_vertical_only: float  # median absolute deviation with dz alone (no shift)
    mad: float  # after the shift


def shifted(transform: Affine, dx: float, dy: float) -> Affine:
    """A transform under which sampling at (x, y) reads the original grid at (x + dx, y + dy)."""
    return Affine(
        transform.a, transform.b, transform.c - dx, transform.d, transform.e, transform.f - dy
    )


def coregister(
    fine_dem, fine_transform, coarse_dem, coarse_transform, search_m: float = 800.0, step: int = 25
) -> Coregistration:
    """Find the horizontal shift and vertical offset that best place a coarse DEM on a fine one.

    The fine DEM is first smoothed to the coarse pixel size, then the shift that minimises the
    median absolute deviation of (fine - coarse) is found on a 100 m grid and refined on a 10 m
    grid; dz is the median difference at that shift.
    """
    fine = np.asarray(fine_dem, dtype=np.float64)
    size = max(1, int(round(abs(coarse_transform.a) / fine_transform.a)))
    filled = np.where(np.isnan(fine), np.nanmean(fine), fine)
    smooth = ndimage.uniform_filter(filled, size, mode="nearest")[::step, ::step]
    rows, cols = np.mgrid[0 : fine.shape[0] : step, 0 : fine.shape[1] : step]
    xs, ys = apply_transform(fine_transform, cols + 0.5, rows + 0.5)
    ok = np.isfinite(fine[::step, ::step])
    coarse = np.asarray(coarse_dem, dtype=np.float64)

    def score(dx, dy):
        d = smooth - sample_bilinear(coarse, coarse_transform, xs + dx, ys + dy)
        d = d[ok & np.isfinite(d)]
        med = float(np.median(d))
        return float(np.median(np.abs(d - med))), med

    mad0, _ = score(0.0, 0.0)
    best = (mad0, 0.0, 0.0)
    for grid, span, centre in ((100.0, search_m, (0.0, 0.0)), (10.0, 100.0, None)):
        cx, cy = centre if centre is not None else (best[1], best[2])
        for dx in np.arange(cx - span, cx + span + 1e-9, grid):
            for dy in np.arange(cy - span, cy + span + 1e-9, grid):
                m, _ = score(dx, dy)
                if m < best[0]:
                    best = (m, float(dx), float(dy))
    mad, dz = score(best[1], best[2])
    return Coregistration(dx=best[1], dy=best[2], dz=dz, mad_vertical_only=mad0, mad=mad)


def far_field(
    fine_dem: np.ndarray,
    fine_transform: Affine,
    regional_dem: np.ndarray,
    regional_transform: Affine,
    az_deg: np.ndarray,
    near_max: float,
    far_max: float,
    grid_m: float,
    min_step: float,
    growth: float,
    observer_height: float,
) -> FarField:
    """Trace far-field rays from a coarse grid of observers covering the fine crop."""
    h, w = fine_dem.shape
    bounds = (
        fine_transform.c,
        fine_transform.f + fine_transform.e * h,
        fine_transform.c + fine_transform.a * w,
        fine_transform.f,
    )
    co = coregister(fine_dem, fine_transform, regional_dem, regional_transform)
    offset = co.dz
    reg = np.asarray(regional_dem, dtype=np.float64) + offset
    regional_transform = shifted(regional_transform, co.dx, co.dy)
    ct = coarse_grid(bounds, grid_m)
    ny, nx = coarse_shape(bounds, grid_m)
    jj, ii = np.meshgrid(np.arange(nx), np.arange(ny))
    xs = np.clip(ct.c + jj * grid_m, bounds[0], bounds[2])
    ys = np.clip(ct.f - ii * grid_m, bounds[1], bounds[3])
    zobs = sample_bilinear(fine_dem, fine_transform, xs, ys) + observer_height
    reach = np.minimum(near_max, distance_to_box_edge(xs, ys, az_deg, bounds))
    start = np.clip(reach - grid_m, 0.0, None)
    dist = far_distances(0.0, far_max, min_step, growth)
    tmax, dstar = profile_max_at_points(
        reg, regional_transform, xs.ravel(), ys.ravel(), zobs.ravel(), az_deg, dist, start
    )
    n_az = len(az_deg)
    return FarField(
        tmax=tmax.reshape(ny, nx, n_az),
        dstar=dstar.reshape(ny, nx, n_az),
        zobs=zobs,
        transform=ct,
        az_deg=np.asarray(az_deg, dtype=np.float64),
        tie_offset_m=offset,
        coreg=co,
    )


def far_field_band(
    ff: FarField,
    a_index: int,
    fine_dem: np.ndarray,
    fine_transform: Affine,
    observer_height: float,
) -> np.ndarray:
    """Far-field horizon (degrees) for one azimuth on the fine grid; -90 where no sample."""
    h, w = fine_dem.shape
    sx = fine_transform.a / ff.transform.a
    sy = fine_transform.e / ff.transform.e
    # coarse index coordinates of fine pixel centres
    cc = ((fine_transform.c - ff.transform.c) / ff.transform.a) + (np.arange(w) + 0.5) * sx
    rr = ((fine_transform.f - ff.transform.f) / ff.transform.e) + (np.arange(h) + 0.5) * sy
    grid_r, grid_c = np.meshgrid(rr, cc, indexing="ij")
    t = ff.tmax[:, :, a_index]
    valid = np.isfinite(t)
    t_filled = np.where(valid, t, 0.0)
    d_filled = np.where(valid, ff.dstar[:, :, a_index], 1.0)
    coords = np.stack([grid_r, grid_c])

    def interp(arr):
        return ndimage.map_coordinates(arr, coords, order=1, mode="nearest")

    t_i = interp(t_filled)
    d_i = interp(d_filled)
    zref_i = interp(ff.zobs)
    v_i = interp(valid.astype(np.float64))
    z0 = np.asarray(fine_dem, dtype=np.float64) + observer_height
    tan = t_i + (zref_i - z0) / np.maximum(d_i, 1.0)
    out = np.degrees(np.arctan(tan))
    out[v_i < 0.5] = -90.0
    out[np.isnan(z0)] = np.nan
    return out.astype(np.float32)


def quantize(h_deg: np.ndarray, qmin: float, qstep: float) -> np.ndarray:
    code = np.round((np.asarray(h_deg, dtype=np.float64) - qmin) / qstep)
    code = np.clip(code, 0, NODATA_CODE - 1)
    code = np.where(np.isnan(h_deg), NODATA_CODE, code)
    return code.astype(np.uint8)


def dequantize(code: np.ndarray, qmin: float, qstep: float) -> np.ndarray:
    h = code.astype(np.float32) * np.float32(qstep) + np.float32(qmin)
    return np.where(code == NODATA_CODE, np.float32(np.nan), h)


def horizon_at_azimuth(h_bands: np.ndarray, az_query: float | np.ndarray) -> np.ndarray:
    """Linear interpolation of horizons (..., n_az) at an azimuth, wrapping at 360."""
    n = h_bands.shape[-1]
    step = 360.0 / n
    pos = (np.asarray(az_query, dtype=np.float64) % 360.0) / step
    i0 = np.floor(pos).astype(int) % n
    i1 = (i0 + 1) % n
    f = pos - np.floor(pos)
    h0 = np.take_along_axis(h_bands, np.broadcast_to(i0, h_bands.shape[:-1])[..., None], -1)[..., 0]
    h1 = np.take_along_axis(h_bands, np.broadcast_to(i1, h_bands.shape[:-1])[..., None], -1)[..., 0]
    return h0 * (1.0 - f) + h1 * f
