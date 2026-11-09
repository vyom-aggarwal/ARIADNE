# Written with AI assistance (Claude Code). See AI_USE.md.
"""Overlays and terrain for the web app: class colors, ramps, hatching, heightmap chunks."""

from __future__ import annotations

import numpy as np
from affine import Affine


def bounds(t: Affine, shape) -> list[float]:
    """[west, south, east, north] of a north-up raster's outer corners, in site metres."""
    h, w = shape
    return [float(t.c), float(t.f + t.e * h), float(t.c + t.a * w), float(t.f)]


def colorize_classes(arr: np.ndarray, legend: list[dict]) -> np.ndarray:
    """RGBA from class values; values not in the legend (and no data) are transparent."""
    a = np.asarray(arr)
    out = np.zeros(a.shape + (4,), dtype=np.uint8)
    for e in legend:
        out[a == e["value"]] = e["color"]
    return out


def colorize_ramp(arr: np.ndarray, vmin: float, vmax: float, stops, alpha: int = 255):
    """RGBA from a linear ramp through `stops` (RGB lists) between vmin and vmax; NaN is clear."""
    a = np.asarray(arr, dtype=np.float64)
    f = np.clip((a - vmin) / (vmax - vmin), 0.0, 1.0)
    s = np.asarray(stops, dtype=np.float64)
    pos = np.nan_to_num(f) * (len(s) - 1)
    i0 = np.clip(np.floor(pos).astype(int), 0, len(s) - 2)
    frac = (pos - i0)[..., None]
    rgb = s[i0] * (1 - frac) + s[i0 + 1] * frac
    out = np.zeros(a.shape + (4,), dtype=np.uint8)
    out[..., :3] = np.rint(rgb).astype(np.uint8)
    out[..., 3] = np.where(np.isfinite(a), alpha, 0)
    return out


def hatch(mask: np.ndarray, spacing: int, color, width: int = 1) -> np.ndarray:
    """Diagonal stripes over the masked cells, so a pattern, not only a color, marks them."""
    m = np.asarray(mask, dtype=bool)
    rr, cc = np.indices(m.shape)
    stripe = ((rr - cc) % spacing) < width
    out = np.zeros(m.shape + (4,), dtype=np.uint8)
    out[m & stripe] = color
    return out


def encode_height(z: np.ndarray, z0: float, scale: float) -> np.ndarray:
    return np.clip(np.rint((np.asarray(z) - z0) / scale), 0, 65535).astype(np.uint16)


def decode_height(code: np.ndarray, z0: float, scale: float) -> np.ndarray:
    return np.asarray(code, dtype=np.float64) * scale + z0


def terrain_chunks(z: np.ndarray, chunk: int = 128, coarse: int = 4, scale: float = 0.01):
    """Split a height grid into square chunks, each with a fine heightmap and a coarse one (the
    mean of `coarse` x `coarse` blocks), both 16-bit with a shared offset and 1 cm steps."""
    z = np.asarray(z, dtype=np.float64)
    zmin = float(np.nanmin(z))
    filled = np.where(np.isfinite(z), z, zmin)
    out = []
    h, w = z.shape
    for r0 in range(0, h, chunk):
        for c0 in range(0, w, chunk):
            r1, c1 = min(h, r0 + chunk), min(w, c0 + chunk)
            fine = filled[r0:r1, c0:c1]
            hh = max(coarse, (fine.shape[0] // coarse) * coarse)
            ww = max(coarse, (fine.shape[1] // coarse) * coarse)
            pad = np.pad(fine, ((0, max(0, hh - fine.shape[0])), (0, max(0, ww - fine.shape[1]))),
                         mode="edge")[:hh, :ww]  # fmt: skip
            blocks = pad.reshape(hh // coarse, coarse, ww // coarse, coarse)
            out.append(
                {
                    "rows_cols": [r0, c0, r1, c1],
                    "z0": zmin,
                    "scale": scale,
                    "fine": encode_height(fine, zmin, scale),
                    "coarse": encode_height(blocks.mean(axis=(1, 3)), zmin, scale),
                }
            )
    return out
