# Written with AI assistance (Claude Code). See AI_USE.md.
"""Walkability for the suited walker and the rover (PROMPT.md 4.3). Label: MODELED.

Classes: 0 = go, 1 = caution, 2 = no-go. A cell takes the worst class of its factors. The cost
multiplier is 1 on easy ground and grows with each factor; it is NaN where the class is no-go.

Image-based factors are computed from the 25 cm orthophoto on its own 1 m grid (4 x 4 pixel
blocks) and then resampled onto the DEM grid, because the two grids are offset by a fraction of
a metre. All image measures are relative within the site.
"""

from __future__ import annotations

import numpy as np
from affine import Affine
from rasterio.warp import Resampling, reproject
from scipy import ndimage

GO, CAUTION, NOGO = 0, 1, 2


def classify(values: np.ndarray, breaks: tuple[float, float]) -> np.ndarray:
    """0 up to breaks[0], 1 up to breaks[1], 2 above; missing values are no-go."""
    v = np.asarray(values, dtype=np.float64)
    out = np.where(v <= breaks[0], GO, np.where(v <= breaks[1], CAUTION, NOGO))
    return np.where(np.isnan(v), NOGO, out).astype(np.uint8)


def percentile_rank(values: np.ndarray) -> np.ndarray:
    """Each value's rank among the finite values, scaled to 0 to 1 (NaN stays NaN)."""
    v = np.asarray(values, dtype=np.float64)
    ok = np.isfinite(v)
    out = np.full(v.shape, np.nan)
    if ok.sum() == 0:
        return out
    srt = np.sort(v[ok])
    out[ok] = np.searchsorted(srt, v[ok], side="right") / srt.size
    return out


def block_view(img: np.ndarray, k: int) -> np.ndarray:
    h, w = (img.shape[0] // k) * k, (img.shape[1] // k) * k
    return img[:h, :w].reshape(h // k, k, w // k, k)


def image_block_stats(img: np.ndarray, k: int):
    """Mean and standard deviation of each k x k block (nodata 0 ignored), as float32."""
    b = block_view(img, k).astype(np.float32)
    valid = b > 0
    n = valid.sum(axis=(1, 3))
    s = np.where(valid, b, 0).sum(axis=(1, 3))
    s2 = np.where(valid, b * b, 0).sum(axis=(1, 3))
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(n > 0, s / n, np.nan)
        var = np.where(n > 1, s2 / n - mean**2, np.nan)
    return mean.astype(np.float32), np.sqrt(np.clip(var, 0, None)).astype(np.float32)


def dark_fraction(img: np.ndarray, k: int, background_px: int, ratio: float) -> np.ndarray:
    """Share of pixels in each k x k block darker than `ratio` x the local median brightness.

    The local median is a median filter of the block means over `background_px` blocks, so a
    brightness step at a mosaic seam shifts the reference with it instead of flagging the dark
    side as rocks.
    """
    mean, _ = image_block_stats(img, k)
    filled = np.where(np.isnan(mean), np.nanmedian(mean), mean)
    bg = ndimage.median_filter(filled, size=background_px, mode="nearest")
    b = block_view(img, k).astype(np.float32)
    dark = (b > 0) & (b < ratio * bg[:, None, :, None])
    valid = (b > 0).sum(axis=(1, 3))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(valid > 0, dark.sum(axis=(1, 3)) / valid, np.nan).astype(np.float32)


def orientation_coherence(img: np.ndarray, k: int, window_blocks: int) -> np.ndarray:
    """Structure-tensor coherence (0 = no preferred direction, 1 = perfectly oriented texture).

    Gradients are taken on a 2 x 2 averaged image; the tensor is averaged over k/2 x k/2 blocks
    and then over a square window of `window_blocks` blocks. Ripples score high.
    """
    half = block_view(img, 2).astype(np.float32).mean(axis=(1, 3))
    gy, gx = np.gradient(half)
    m = k // 2
    jxx = block_view(gx * gx, m).mean(axis=(1, 3))
    jyy = block_view(gy * gy, m).mean(axis=(1, 3))
    jxy = block_view(gx * gy, m).mean(axis=(1, 3))
    jxx, jyy, jxy = (
        ndimage.uniform_filter(a, window_blocks, mode="nearest") for a in (jxx, jyy, jxy)
    )
    with np.errstate(invalid="ignore", divide="ignore"):
        coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy**2) / (jxx + jyy)
    return np.nan_to_num(coh, nan=0.0).astype(np.float32)


def to_grid(
    src: np.ndarray, src_t: Affine, dst_shape, dst_t: Affine, crs, method=Resampling.bilinear
):
    out = np.full(dst_shape, np.nan, dtype=np.float32)
    reproject(
        source=np.asarray(src, dtype=np.float32),
        destination=out,
        src_transform=src_t,
        src_crs=crs,
        dst_transform=dst_t,
        dst_crs=crs,
        src_nodata=np.nan,
        dst_nodata=np.nan,
        resampling=method,
    )
    return out


def sand_proxy(smooth_rank, coherence_rank, night_ir_rank) -> np.ndarray:
    """Mean of the available scores (each 0 to 1): smooth texture, ripple directionality, and
    low night-IR brightness (cool at night = low thermal inertia = loose material)."""
    parts = [
        np.asarray(p, dtype=np.float64) for p in (smooth_rank, coherence_rank) if p is not None
    ]
    if night_ir_rank is not None:
        parts.append(1.0 - np.asarray(night_ir_rank, dtype=np.float64))
    stack = np.stack(parts)
    return np.nanmean(stack, axis=0).astype(np.float32)


def dropoffs(convexity: np.ndarray, relief: np.ndarray, curvature_min: float, relief_min: float):
    """Convex edges with at least `relief_min` of local relief (ridge-edge drop-offs)."""
    return (np.asarray(convexity) > curvature_min) & (np.asarray(relief) >= relief_min)


def slope_scales(cfg: dict) -> dict:
    """Disc diameters (m) for each traveller's slope: the larger of its footprint and the DEM's
    effective resolution r_eff (image pixels x pixel size), plus the coarse-resolution case."""

    def v(key):
        return float(cfg["walkability"][key]["value"])

    px = v("dem_image_pixel_m")
    r_eff = v("dem_resolution_pixels") * px
    r_coarse = v("dem_resolution_pixels_coarse") * px
    rover, walker = v("rover_footprint_m"), v("walker_footprint_m")
    return {
        "r_eff_m": r_eff,
        "rover_m": max(rover, r_eff),
        "walker_m": max(walker, r_eff),
        "r_eff_coarse_m": r_coarse,
        "rover_coarse_m": max(rover, r_coarse),
        "walker_coarse_m": max(walker, r_coarse),
    }


def walkability(
    slope,
    roughness,
    dark,
    sand,
    dropoff,
    slope_breaks,
    rough_breaks,
    dark_caution: float,
    sand_caution: float | None,
    dropoff_class: int,
    weights: dict,
):
    """Class (uint8) and cost multiplier (float32, NaN for no-go) for one traveller."""
    cls = np.maximum(classify(slope, slope_breaks), classify(roughness, rough_breaks))
    d = np.nan_to_num(np.asarray(dark, dtype=np.float64), nan=0.0)
    cls = np.maximum(cls, np.where(d > dark_caution, CAUTION, GO).astype(np.uint8))
    s = np.nan_to_num(np.asarray(sand, dtype=np.float64), nan=0.0)
    if sand_caution is not None:
        cls = np.maximum(cls, np.where(s > sand_caution, CAUTION, GO).astype(np.uint8))
    cls = np.maximum(cls, np.where(dropoff, dropoff_class, GO).astype(np.uint8))
    sl = np.nan_to_num(np.asarray(slope, dtype=np.float64), nan=90.0)
    ro = np.nan_to_num(np.asarray(roughness, dtype=np.float64), nan=10.0)
    cost = (
        1.0
        + weights["slope"] * (sl / slope_breaks[0]) ** 2
        + weights["roughness"] * (ro / rough_breaks[0])
        + weights["dark"] * (d / dark_caution)
        + weights["sand"] * s
        + weights["dropoff"] * np.asarray(dropoff, dtype=np.float64)
    )
    cost = np.where(cls == NOGO, np.nan, cost)
    return cls.astype(np.uint8), cost.astype(np.float32)
