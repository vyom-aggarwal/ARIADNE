# Written with AI assistance (Claude Code). See AI_USE.md.
"""Where the merged DEM comes from HiRISE stereo, from the stereo-pair footprints.

The USGS product page lists the 12 HiRISE stereo pairs used in the merged DEM and says that
elsewhere the DEM falls back to CTX, then HRSC, then MOLA. It publishes no per-pixel source
map, so this module builds one: a pair gives stereo coverage where its two images overlap.
Areas outside every pair are "CTX, HRSC or MOLA"; the metadata does not let us tell those
apart. Label: DERIVED. Footprint vertices from ODE are rounded (0.001 deg of longitude, about
59 m), so mask edges are uncertain by roughly 30 m.
"""

from __future__ import annotations

import numpy as np
from affine import Affine
from rasterio.features import rasterize
from shapely import wkt
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform as shp_transform
from shapely.ops import unary_union

from ariadne.fetch.places import MARS_RADIUS_M

NODATA, HIRISE, OTHER = 0, 1, 2
CLASS_NAMES = {HIRISE: "hirise_stereo", OTHER: "ctx_hrsc_or_mola"}

# From https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m (fetched at
# kickoff). The page writes every ID with _1755; the archive uses _1750 for some, so pairs are
# matched on the first two parts of the observation ID.
USGS_STEREO_PAIRS: dict[str, tuple[str, str]] = {
    "West Gap": ("ESP_024234", "ESP_024300"),
    "West": ("PSP_009650", "PSP_009716"),
    "Center": ("PSP_010573", "PSP_010639"),
    "G2": ("PSP_009505", "PSP_009571"),
    "East": ("ESP_011417", "ESP_011562"),
    "West of Center": ("ESP_018854", "ESP_018920"),
    "Center Gap": ("ESP_023957", "ESP_024023"),
    "East Gap": ("ESP_024102", "ESP_025368"),
    "Traverse": ("PSP_009149", "PSP_009294"),
    "T2": ("ESP_012551", "ESP_012841"),
    "T1": ("PSP_001488", "PSP_001752"),
    "T3": ("ESP_019698", "ESP_019988"),
}


def obs_key(observation_id: str) -> str:
    """'PSP_009149_1750' -> 'PSP_009149'."""
    return "_".join(observation_id.split("_")[:2])


def lonlat_geom_to_eqc(geom: BaseGeometry) -> BaseGeometry:
    """Equirectangular projection on the sphere is linear in lon/lat, so edges stay straight."""
    k = MARS_RADIUS_M * np.pi / 180.0
    return shp_transform(lambda x, y, z=None: (np.asarray(x) * k, np.asarray(y) * k), geom)


def observation_footprints(products: list[dict]) -> dict[str, BaseGeometry]:
    """Footprint per observation in meters, from RED products when present (they span the full
    image width; COLOR products cover only the central strip)."""
    by_obs: dict[str, dict[str, list[BaseGeometry]]] = {}
    for p in products:
        geom_text = p.get("Footprint_C0_geometry")
        obs = p.get("Observation_id")
        if not geom_text or not obs:
            continue
        kind = "RED" if "_RED" in (p.get("LabelURL") or "").upper() else "OTHER"
        by_obs.setdefault(obs_key(obs), {}).setdefault(kind, []).append(wkt.loads(geom_text))
    out = {}
    for key, kinds in by_obs.items():
        geoms = kinds.get("RED") or kinds["OTHER"]
        out[key] = lonlat_geom_to_eqc(unary_union(geoms))
    return out


def pair_footprints(
    obs_fps: dict[str, BaseGeometry], pairs: dict[str, tuple[str, str]] = USGS_STEREO_PAIRS
) -> dict[str, BaseGeometry]:
    """Stereo coverage per pair: the overlap of its two images (pairs missing an image drop out)."""
    out = {}
    for name, (a, b) in pairs.items():
        if a in obs_fps and b in obs_fps:
            inter = obs_fps[a].intersection(obs_fps[b])
            if not inter.is_empty:
                out[name] = inter
    return out


def source_class_mask(
    shape: tuple[int, int], transform: Affine, stereo: list[BaseGeometry], valid: np.ndarray
) -> np.ndarray:
    """uint8 mask on the DEM grid: 1 = HiRISE stereo, 2 = CTX/HRSC/MOLA, 0 = DEM nodata."""
    shapes = [(g, 1) for g in stereo if not g.is_empty]
    hirise = (
        rasterize(shapes, out_shape=shape, transform=transform, fill=0, dtype="uint8")
        if shapes
        else np.zeros(shape, "uint8")
    )
    mask = np.where(hirise == 1, HIRISE, OTHER).astype("uint8")
    mask[~valid] = NODATA
    return mask


def coverage_summary(
    mask: np.ndarray, transform: Affine, east: np.ndarray, north: np.ndarray
) -> dict:
    """Shares of the box (valid cells) and of the rover's points in each source class."""
    valid = mask != NODATA
    n_valid = int(valid.sum())
    box = {name: 100.0 * int((mask == code).sum()) / n_valid for code, name in CLASS_NAMES.items()}
    inv = ~transform
    cols, rows = inv * (np.asarray(east), np.asarray(north))
    cols, rows = np.floor(cols).astype(int), np.floor(rows).astype(int)
    inside = (rows >= 0) & (rows < mask.shape[0]) & (cols >= 0) & (cols < mask.shape[1])
    vals = mask[rows[inside], cols[inside]]
    vals = vals[vals != NODATA]
    path = {
        name: (100.0 * int((vals == code).sum()) / len(vals) if len(vals) else 0.0)
        for code, name in CLASS_NAMES.items()
    }
    return {
        "box_percent": box,
        "valid_cells": n_valid,
        "nodata_cells": int((~valid).sum()),
        "path_percent": path,
        "path_points": int(len(vals)),
    }


def geometry_share(geom: BaseGeometry, bounds: tuple[float, float, float, float]) -> float:
    """Percent of a rectangle covered by a geometry."""
    rect = Polygon.from_bounds(*bounds)
    return 100.0 * geom.intersection(rect).area / rect.area
