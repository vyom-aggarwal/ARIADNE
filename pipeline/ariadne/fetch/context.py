# Written with AI assistance (Claude Code). See AI_USE.md.
"""Context inputs for the derived layers: Trek map tiles, ChemCam targets and drill sites.

Trek's default028mm tile matrix is geographic: level z has 2^(z+1) x 2^z tiles of 256 px over
360 x 180 degrees, starting at (-180, 90). Equirectangular metres on the Mars sphere are linear
in longitude and latitude (x = R lon, y = R lat), so a tile mosaic maps to the analysis grid with
a plain affine transform and no resampling.
"""

from __future__ import annotations

import io
import math
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from rasterio.errors import NotGeoreferencedWarning

from ariadne.fetch.http import download
from ariadne.fetch.places import MARS_RADIUS_M

TILE_PX = 256


def trek_tile_size_deg(level: int) -> float:
    return 360.0 / (2 ** (level + 1))


def trek_tiles_for_bounds(bounds_eqc, level: int) -> tuple[list[tuple[int, int]], Affine]:
    """Tiles (row, col) covering an equirectangular box, and the mosaic's eqc transform."""
    left, bottom, right, top = bounds_eqc
    deg = math.degrees
    lon0, lon1 = deg(left / MARS_RADIUS_M), deg(right / MARS_RADIUS_M)
    lat0, lat1 = deg(bottom / MARS_RADIUS_M), deg(top / MARS_RADIUS_M)
    size = trek_tile_size_deg(level)
    c0, c1 = int(math.floor((lon0 + 180.0) / size)), int(math.floor((lon1 + 180.0) / size))
    r0, r1 = int(math.floor((90.0 - lat1) / size)), int(math.floor((90.0 - lat0) / size))
    tiles = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
    px_deg = size / TILE_PX
    px_m = math.radians(px_deg) * MARS_RADIUS_M
    x0 = math.radians(c0 * size - 180.0) * MARS_RADIUS_M
    y0 = math.radians(90.0 - r0 * size) * MARS_RADIUS_M
    return tiles, Affine(px_m, 0.0, x0, 0.0, -px_m, y0)


def fetch_trek_mosaic(url_template: str, level: int, bounds_eqc, cache_dir: Path):
    """Download (or reuse) the tiles over a box; return (gray uint8 with 0 = no data, transform)."""
    tiles, transform = trek_tiles_for_bounds(bounds_eqc, level)
    rows = sorted({r for r, _ in tiles})
    cols = sorted({c for _, c in tiles})
    mosaic = np.zeros((len(rows) * TILE_PX, len(cols) * TILE_PX), dtype=np.uint8)
    for r, c in tiles:
        path = cache_dir / str(level) / str(r) / f"{c}.png"
        if not path.exists():
            download(url_template.format(z=level, y=r, x=c), path)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", NotGeoreferencedWarning)  # tiles carry no georeference
            with rasterio.open(io.BytesIO(path.read_bytes())) as ds:
                arr = ds.read()
        gray = arr[0]
        if arr.shape[0] in (2, 4):  # alpha band: transparent pixels are outside the mosaic
            gray = np.where(arr[-1] > 0, np.maximum(gray, 1), 0)
        i, j = rows.index(r), cols.index(c)
        mosaic[i * TILE_PX : (i + 1) * TILE_PX, j * TILE_PX : (j + 1) * TILE_PX] = gray
    return mosaic, transform


SCLK_RE = re.compile(r"^C[A-Z]\d_(\d{9})")


def sclk_from_chemcam_file(name: str) -> int | None:
    m = SCLK_RE.match(name.strip())
    return int(m.group(1)) if m else None


def read_chemcam_moc(path: Path) -> pd.DataFrame:
    """Target name, SCLK and distance (m) from a ChemCam MOC table (header row starts 'File')."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("File,"))
    df = pd.read_csv(io.StringIO("\n".join(lines[start:])), dtype=str)
    out = pd.DataFrame(
        {
            "file": df["File"],
            "target": df["Target"].str.strip(),
            "distance_m": pd.to_numeric(df["Distance (m)"], errors="coerce"),
        }
    )
    out["sclk"] = out["file"].map(sclk_from_chemcam_file)
    return out.dropna(subset=["sclk"]).astype({"sclk": "int64"})


def position_at_sclk(rover: pd.DataFrame, sclk: np.ndarray) -> pd.DataFrame:
    """The localization in effect at each SCLK (the latest one at or before it)."""
    r = rover.sort_values("sclk").reset_index(drop=True)
    idx = np.searchsorted(r["sclk"].to_numpy(), np.asarray(sclk), side="right") - 1
    idx = np.clip(idx, 0, len(r) - 1)
    return r.iloc[idx].reset_index(drop=True)


def chemcam_targets(tables: list[Path], rover: pd.DataFrame) -> pd.DataFrame:
    """One row per ChemCam target: name, first SCLK, sol and the rover position then."""
    df = pd.concat([read_chemcam_moc(p) for p in tables], ignore_index=True)
    first = (
        df.sort_values("sclk")
        .groupby("target", as_index=False)
        .agg(sclk=("sclk", "first"), distance_m=("distance_m", "median"), shots=("file", "size"))
    )
    pos = position_at_sclk(rover, first["sclk"].to_numpy())
    first["sol"] = pos["sol"].to_numpy()
    first["easting"] = pos["easting"].to_numpy()
    first["northing"] = pos["northing"].to_numpy()
    return first


def held_localization(rover: pd.DataFrame, sol: int) -> pd.Series:
    """The localization Curiosity held on a sol: the last one with sol at or before it."""
    r = rover.sort_values("sclk")
    held = r[r["sol"] <= sol]
    if held.empty:
        raise ValueError(f"no localization at or before sol {sol}")
    return held.iloc[-1]


def drill_site_positions(drill_sites: list[dict], rover: pd.DataFrame) -> list[dict]:
    out = []
    for d in drill_sites:
        loc = held_localization(rover, int(d["sol"]))
        later = rover[rover["sclk"] > loc["sclk"]]
        out.append(
            {
                **d,
                "site": int(loc["site"]),
                "drive": int(loc["drive"]),
                "held_from_sol": int(loc["sol"]),
                "held_until_sol": int(later.iloc[0]["sol"]) - 1 if not later.empty else None,
                "easting": float(loc["easting"]),
                "northing": float(loc["northing"]),
                "elevation": float(loc["elevation"]),
            }
        )
    return out


def sol_positions(rover: pd.DataFrame, sol: int) -> list[pd.Series]:
    """Positions at the start and end of a sol (the same row when the rover did not drive)."""
    r = rover.sort_values("sclk")
    before = r[r["sol"] < sol]
    upto = r[r["sol"] <= sol]
    if upto.empty:
        raise ValueError(f"no localization at or before sol {sol}")
    start = before.iloc[-1] if not before.empty else upto.iloc[0]
    return [start, upto.iloc[-1]]
