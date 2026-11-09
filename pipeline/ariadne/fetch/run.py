# Written with AI assistance (Claude Code). See AI_USE.md.
"""`ariadne fetch --site <name>`: crop every source to the site box, with provenance and checks."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import rasterio
from shapely import wkt

from ariadne import PIPELINE_VERSION
from ariadne.config import Source, load_site_config, load_sources
from ariadne.fetch import coverage, ode, places, raster, report
from ariadne.fetch.checks import georeference_check
from ariadne.fetch.http import download
from ariadne.fetch.sites import site_box
from ariadne.guardrails import repo_root
from ariadne.labels import Label
from ariadne.provenance import (
    TAG,
    Provenance,
    provenance_tag,
    read_provenance,
    sidecar_path,
    write_provenance,
)

GAP_FILL_PATH_MIN = 99.0  # percent of Curiosity's localizations on HiRISE stereo (team rule)
GAP_FILL_BOX_MIN = 90.0  # percent of the site box on HiRISE stereo (team rule)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _inside(inner, outer) -> bool:
    return (
        inner[0] >= outer[0]
        and inner[1] >= outer[1]
        and inner[2] <= outer[2]
        and inner[3] <= outer[3]
    )


def _fetch_places(src: Source, data: Path, force: bool, log) -> Path:
    path = data / "sources" / src.id / src.output
    if path.exists() and sidecar_path(path).exists() and not force:
        log(f"  PLACES table cached: {path.relative_to(data.parent)}")
        return path
    log(f"  downloading {src.url}")
    info = download(src.url, path)
    write_provenance(
        path,
        Provenance.new(
            source_id=src.id,
            url=src.url,
            product_id=src.product_id,
            resolution_m=None,
            acquisition_date=None,
            label=src.label,
            notes=src.notes,
            extra=info,
        ),
    )
    return path


def _crop_source(src: Source, bounds, out: Path, force: bool, log) -> dict:
    if out.exists() and sidecar_path(out).exists() and not force:
        prov = read_provenance(out)
        if prov.url == src.url and prov.extra.get("requested_bounds") == [float(b) for b in bounds]:
            with rasterio.open(out) as ds:
                complete = TAG in ds.tags()
            if complete:
                log(f"  {out.name}: cached")
                with rasterio.open(out) as ds:
                    return {
                        "width": ds.width,
                        "height": ds.height,
                        "method": prov.extra["method"],
                        "seconds": prov.extra["seconds"],
                        "bounds": list(ds.bounds),
                        "prov": prov,
                    }
    fast = raster.is_uncompressed_strip_tiff(src.url)
    log(f"  {out.name}: reading {src.id} ({'range requests' if fast else 'GDAL row bands'})")
    t0 = time.time()
    crop = raster.read_crop(src.url, bounds, workers=64 if fast else 16)
    seconds = time.time() - t0  # reading time; writing the COG follows
    h, w = crop.data.shape[-2:]
    prov = Provenance.new(
        source_id=src.id,
        url=src.url,
        product_id=src.product_id,
        resolution_m=src.resolution_m,
        acquisition_date=src.acquisition_date,
        label=src.label,
        notes=src.notes,
        extra={
            "requested_bounds": [float(b) for b in bounds],
            "bounds": [float(b) for b in crop.bounds],
            "source_window": [int(crop.window.col_off), int(crop.window.row_off), w, h],
            "method": crop.method,
            "seconds": round(seconds, 1),
            "credit": src.credit,
            "license": src.license,
        },
    )
    # A COG cannot be re-tagged in place without breaking its layout: tag it while writing.
    raster.write_cog(out, crop, tags=provenance_tag(prov))
    write_provenance(out, prov)
    log(f"  {out.name}: {w:,} x {h:,} px in {seconds:.0f} s")
    return {
        "width": w,
        "height": h,
        "method": crop.method,
        "seconds": round(seconds, 1),
        "bounds": [float(b) for b in crop.bounds],
        "prov": prov,
    }


def _ode(bounds, site: str, data: Path, product_type: str, force: bool, log) -> list[dict]:
    path = data / "sources" / "ode" / f"{site}_hirise_{product_type.lower()}.json"
    if path.exists() and sidecar_path(path).exists() and not force:
        return json.loads(path.read_text(encoding="utf-8"))
    products, query = ode.query_products(bounds, product_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(products, indent=1), encoding="utf-8")
    write_provenance(
        path,
        Provenance.new(
            source_id="ode-hirise-footprints",
            url=ode.ODE_URL,
            product_id=f"HiRISE {product_type}",
            resolution_m=None,
            acquisition_date=None,
            label=Label.MEASURED,
            notes="Footprint metadata for products touching the site box.",
            extra=query,
        ),
    )
    log(f"  ODE: {len(products)} HiRISE {product_type} products touch the box")
    return products


def _gap_fill_text(cov: dict, dtms: dict) -> str:
    path, box = cov["path_percent"]["hirise_stereo"], cov["box_percent"]["hirise_stereo"]
    rule = f"team rule: at least {GAP_FILL_PATH_MIN:.0f}% and {GAP_FILL_BOX_MIN:.0f}%"
    shares = f"{path:.1f}% of Curiosity's localizations and {box:.1f}% of the box"
    if path >= GAP_FILL_PATH_MIN and box >= GAP_FILL_BOX_MIN:
        return (
            f"not needed. {shares} lie on HiRISE stereo ({rule}). Cells outside HiRISE "
            "stereo get a lower confidence in the Phase 2 uncertainty layer."
        )
    best = max(dtms.items(), key=lambda kv: kv[1]) if dtms else None
    hint = f" The public DTM {best[0]} covers {best[1]:.1f}% of the box." if best else ""
    return (
        f"needed. Only {shares} lie on HiRISE stereo ({rule}).{hint} "
        "Recorded as an open issue in docs/PROGRESS.md."
    )


def fetch_site(name: str, force: bool = False, log: Callable[[str], None] = print) -> dict:
    root = repo_root()
    data = root / "data"
    cfg = load_site_config(name)
    sources = load_sources()
    site_dir = data / "sites" / name
    site_dir.mkdir(parents=True, exist_ok=True)
    log(f"Fetching site {name}")

    places_csv = _fetch_places(sources["msl-places"], data, force, log)
    rover = places.load_rover_positions(places_csv)
    box = site_box(cfg, rover)
    log(
        f"  box: sols {box.first_sol} to {box.last_sol}, {box.rover_count} localizations, "
        f"bounds {[round(b, 1) for b in box.bounds]}"
    )

    window_rover = places.in_sols(rover, box.first_sol, box.last_sol)
    path_file = site_dir / "rover_path.geojson"
    path_file.write_text(
        json.dumps(places.rover_path_geojson(window_rover, name)), encoding="utf-8"
    )
    ps = sources["msl-places"]
    write_provenance(
        path_file,
        Provenance.new(
            source_id=ps.id,
            url=ps.url,
            product_id=ps.product_id,
            resolution_m=None,
            acquisition_date=f"sols {box.first_sol} to {box.last_sol}",
            label=Label.MEASURED,
            notes="Curiosity's ROVER-frame localizations in the site's sol window.",
        ),
    )

    products, rows = [], []
    for sid in cfg.sources + cfg.optional_sources:
        src = sources[sid]
        with rasterio.Env(**raster.GDAL_ENV), rasterio.open(raster.gdal_path(src.url)) as ds:
            src_bounds = tuple(ds.bounds)
        if not _inside(box.bounds, src_bounds):
            if sid in cfg.optional_sources:
                products.append(
                    {
                        "file": src.output,
                        "source_id": sid,
                        "skipped": "the source does not cover the whole site box",
                    }
                )
                log(f"  {src.output}: skipped (source does not cover the box)")
                continue
            raise ValueError(f"{sid} does not cover the {name} site box")
        out = site_dir / src.output
        r = _crop_source(src, box.bounds, out, force, log)
        prov = r.pop("prov")
        products.append(
            {
                "file": src.output,
                "source_id": sid,
                "resolution_m": src.resolution_m,
                "label": str(src.label),
                **r,
            }
        )
        b = r["bounds"]
        rows.append(
            {
                "file": src.output,
                "source_id": sid,
                "bounds": f"{b[0]:,.2f} to {b[2]:,.2f}; {b[1]:,.2f} to {b[3]:,.2f}",
                "size": f"{r['width']:,} × {r['height']:,} px",
                "method": r["method"],
                "processed": prov.processing_date,
                "pipeline": prov.pipeline_version,
            }
        )

    dem_path = site_dir / sources["usgs-gale-dem-1m"].output
    with rasterio.open(dem_path) as d:
        dem, t, nod, crs, dem_bounds = d.read(1), d.transform, d.nodata, d.crs, tuple(d.bounds)

    rdr = _ode(dem_bounds, name, data, "RDRV11", force, log)
    dtm = _ode(dem_bounds, name, data, "DTM", force, log)
    pairs = coverage.pair_footprints(coverage.observation_footprints(rdr))
    mask = coverage.source_class_mask(dem.shape, t, list(pairs.values()), dem != nod)
    mask_crop = raster.Crop(mask, t, crs, coverage.NODATA, dem_bounds, None, "derived")
    mask_prov = Provenance.new(
        source_id="ariadne-dem-source-class",
        url=ode.ODE_URL,
        product_id="DEM source class from USGS stereo-pair footprints",
        resolution_m=1.0,
        acquisition_date=None,
        label=Label.DERIVED,
        notes="1 = HiRISE stereo (overlap of a USGS pair's two images), 2 = CTX, HRSC or MOLA, "
        "0 = DEM nodata. Edges uncertain by about 30 m (rounded ODE footprints).",
        extra={"pairs": sorted(pairs)},
    )
    mask_path = raster.write_cog(
        site_dir / "source_class.tif", mask_crop, tags=provenance_tag(mask_prov)
    )
    write_provenance(mask_path, mask_prov)
    rows.append(
        {
            "file": "source_class.tif",
            "source_id": "ariadne-dem-source-class",
            "bounds": "DEM grid",
            "size": f"{mask.shape[1]:,} × {mask.shape[0]:,} px",
            "method": "derived",
            "processed": _now(),
            "pipeline": PIPELINE_VERSION,
        }
    )

    left, bottom, right, top = dem_bounds
    in_box = rover[
        (rover["easting"] >= left)
        & (rover["easting"] <= right)
        & (rover["northing"] >= bottom)
        & (rover["northing"] <= top)
    ]
    cov = coverage.coverage_summary(
        mask, t, in_box["easting"].to_numpy(), in_box["northing"].to_numpy()
    )
    pair_share = {k: coverage.geometry_share(g, dem_bounds) for k, g in pairs.items()}
    pair_share = {k: v for k, v in pair_share.items() if v > 0}
    missing = sorted(set(coverage.USGS_STEREO_PAIRS) - set(pair_share))
    dtm_share = {}
    for p in dtm:
        stem = Path(p.get("LabelURL", "unknown")).stem
        geom = coverage.lonlat_geom_to_eqc(wkt.loads(p["Footprint_C0_geometry"]))
        dtm_share[stem] = coverage.geometry_share(geom, dem_bounds)

    geo = georeference_check(
        dem,
        t,
        nod,
        in_box["easting"].to_numpy(),
        in_box["northing"].to_numpy(),
        in_box["elevation"].to_numpy(),
    )
    ortho = [
        p for p in products if p["source_id"] == "usgs-gale-ortho-25cm" and not p.get("skipped")
    ]
    if ortho:
        diff = max(abs(a - b) for a, b in zip(ortho[0]["bounds"], dem_bounds, strict=True))
        bounds_check = (
            f"{'yes' if diff <= abs(t.a) else 'NO'} (largest edge difference {diff:.2f} m)"
        )
    else:
        bounds_check = "no orthophoto"

    anchor = box.anchor
    report.quicklook(
        site_dir / "quicklook.png",
        dem_path,
        site_dir / sources["usgs-gale-ortho-25cm"].output if ortho else None,
        in_box["easting"].to_numpy(),
        in_box["northing"].to_numpy(),
        anchor,
    )

    summary = {
        "site": name,
        "title": cfg.title,
        "processed_utc": _now(),
        "pipeline_version": PIPELINE_VERSION,
        "utc_window": [str(cfg.selection.utc_start), str(cfg.selection.utc_end)],
        "box": box.to_dict(),
        "products": products,
        "coverage": cov,
        "pairs": pair_share,
        "missing_pairs": missing,
        "dtms": dtm_share,
        "gap_fill": _gap_fill_text(cov, dtm_share),
        "georeference": geo,
        "bounds_check": bounds_check,
    }
    (site_dir / "fetch_summary.json").write_text(
        json.dumps(summary, indent=2, default=float), encoding="utf-8"
    )
    cov_md = root / "docs" / "coverage" / f"{name}.md"
    cov_md.parent.mkdir(parents=True, exist_ok=True)
    cov_md.write_text(report.coverage_markdown(summary), encoding="utf-8", newline="\n")
    report.update_fetch_log(root / "docs" / "SOURCES_LOG.md", name, rows)
    log(
        f"  HiRISE stereo: {cov['box_percent']['hirise_stereo']:.1f}% of box, "
        f"{cov['path_percent']['hirise_stereo']:.1f}% of {cov['path_points']} localizations"
    )
    log(
        f"  georeferencing: median DEM - PLACES {geo['median_dem_minus_places_m']:+.2f} m, "
        f"best shift {geo['best_shift_east_north_m']}, {'PASS' if geo['passed'] else 'FAIL'}"
    )
    log(f"  report: {cov_md.relative_to(root)}")
    return summary


def fetch_summary_ok(summary: dict) -> bool:
    return bool(summary["georeference"]["passed"]) and np.isfinite(
        summary["georeference"]["median_dem_minus_places_m"]
    )
