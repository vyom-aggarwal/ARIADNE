# Written with AI assistance (Claude Code). See AI_USE.md.
"""Reading crops and writing derived layers with provenance."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio

from ariadne.fetch import raster
from ariadne.labels import Label
from ariadne.provenance import Provenance, provenance_tag, write_provenance

DERIVED_URL = "https://github.com/vyom-aggarwal/ARIADNE"


def read_raster(path: Path, as_float: bool = True):
    with rasterio.open(path) as d:
        a = d.read() if d.count > 1 else d.read(1)
        if as_float:
            a = a.astype(np.float64)
            if d.nodata is not None:
                a[a == d.nodata] = np.nan
        return a, d.transform, d.crs


def write_layer(
    path: Path,
    data: np.ndarray,
    transform,
    crs,
    nodata,
    *,
    product_id: str,
    label: Label,
    notes: str,
    resolution_m: float,
    inputs: list[str],
    settings: dict | None = None,
    compress: str | None = None,
) -> Path:
    """Write a derived raster as a COG with a provenance sidecar and tag."""
    prov = Provenance.new(
        source_id=f"ariadne-{path.stem}",
        url=DERIVED_URL,
        product_id=product_id,
        resolution_m=resolution_m,
        acquisition_date=None,
        label=label,
        notes=notes,
        extra={"inputs": inputs, "settings": settings or {}},
    )
    crop = raster.Crop(np.asarray(data), transform, crs, nodata, None, None, "derived")
    raster.write_cog(path, crop, tags=provenance_tag(prov), compress=compress)
    write_provenance(path, prov)
    return path


def write_geojson(
    path: Path,
    collection: dict,
    *,
    product_id: str,
    label: Label,
    notes: str,
    inputs: list[str],
    settings: dict | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection), encoding="utf-8", newline="\n")
    write_provenance(
        path,
        Provenance.new(
            source_id=f"ariadne-{path.stem}",
            url=DERIVED_URL,
            product_id=product_id,
            resolution_m=None,
            acquisition_date=None,
            label=label,
            notes=notes,
            extra={"inputs": inputs, "settings": settings or {}},
        ),
    )
    return path


CRS_NOTE = "equirectangular metres, Mars sphere 3,396,190 m (as the DEM)"


def feature_collection(name: str, features: list[dict]) -> dict:
    return {
        "type": "FeatureCollection",
        "name": name,
        "ariadne_crs": CRS_NOTE,
        "features": features,
    }
