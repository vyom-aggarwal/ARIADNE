# Written with AI assistance (Claude Code). See AI_USE.md.
"""Human-readable outputs of a fetch: the coverage report, the fetch log and a quicklook image."""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.features import rasterize
from shapely.geometry import LineString

from ariadne import PIPELINE_VERSION
from ariadne.fetch.places import MARS_RADIUS_M

CYAN = (0, 230, 255)
DARK = (10, 10, 10)
WHITE = (255, 255, 255)


def _deg(m: float) -> float:
    return math.degrees(m / MARS_RADIUS_M)


def hillshade(dem: np.ndarray, cell_m: float, azimuth=315.0, altitude=45.0) -> np.ndarray:
    gy, gx = np.gradient(dem.astype("float64"), cell_m)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = math.radians(azimuth), math.radians(altitude)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(shade, 0, 1)


def quicklook(
    out_png: Path, dem_path: Path, ortho_path: Path | None, east, north, anchor=None, max_px=1200
) -> Path:
    """RGB overview: orthophoto blended with DEM hillshade, rover path in cyan with a dark edge."""
    with rasterio.open(dem_path) as src:
        f = max(1, math.ceil(max(src.width, src.height) / max_px))
        h, w = math.ceil(src.height / f), math.ceil(src.width / f)
        dem = src.read(1, out_shape=(h, w), resampling=Resampling.average, masked=True).filled(
            np.nan
        )
        t = src.transform * Affine.scale(src.width / w, src.height / h)
    shade = hillshade(np.nan_to_num(dem, nan=np.nanmean(dem)), abs(t.a))
    gray = shade
    if ortho_path is not None and Path(ortho_path).exists():
        with rasterio.open(ortho_path) as src:
            img = (
                src.read(1, out_shape=(h, w), resampling=Resampling.average).astype("float64")
                / 255.0
            )
        gray = 0.65 * img + 0.35 * shade
    rgb = np.repeat((np.clip(gray, 0, 1) * 255).astype("uint8")[None], 3, axis=0)
    line = LineString(list(zip(east, north, strict=True)))
    edge = rasterize(
        [(line.buffer(abs(t.a) * 1.5), 1)], out_shape=(h, w), transform=t, all_touched=True
    )
    core = rasterize([(line, 1)], out_shape=(h, w), transform=t, all_touched=True)
    for band in range(3):
        rgb[band][edge == 1] = DARK[band]
        rgb[band][core == 1] = CYAN[band]
    if anchor:
        c, r = ~t * (anchor["easting"], anchor["northing"])
        r, c = int(r), int(c)
        rgb[:, max(0, r - 5) : r + 6, max(0, c - 5) : c + 6] = np.array(DARK)[:, None, None]
        rgb[:, max(0, r - 3) : r + 4, max(0, c - 3) : c + 4] = np.array(WHITE)[:, None, None]
    out_png = Path(out_png)
    with rasterio.open(
        out_png, "w", driver="PNG", width=w, height=h, count=3, dtype="uint8"
    ) as dst:
        dst.write(rgb)
    return out_png


def _fmt(x: float, nd=1) -> str:
    return f"{x:,.{nd}f}".replace("-", "−")


def coverage_markdown(summary: dict) -> str:
    """docs/coverage/<site>.md from a fetch summary."""
    s = summary
    box = s["box"]
    left, bottom, right, top = box["bounds"]
    cov = s["coverage"]
    geo = s["georeference"]
    lines = [
        f"# Coverage and georeferencing: {s['title']}",
        "",
        f"Written by `ariadne fetch --site {s['site']}` (pipeline {PIPELINE_VERSION}) on "
        f"{s['processed_utc']}. Do not edit by hand; rerun the fetch instead.",
        "",
        "## Site box",
        "",
        "| Item | Value | Label |",
        "| --- | --- | --- |",
        f"| Selection | {box['method'].replace('_', ' ')}, sols {box['first_sol']} to {box['last_sol']} "
        f"({s['utc_window'][0]} to {s['utc_window'][1]} UTC) | DERIVED from PLACES |",
        f"| Rover localizations in the window | {box['rover_count']:,} | MEASURED (PLACES) |",
        f"| Buffer | {box['buffer_m']:,.0f} m | {box['buffer_label']} |",
        f"| Box, easting | {_fmt(left)} to {_fmt(right)} m ({_fmt(right - left, 0)} m) | DERIVED |",
        f"| Box, northing | {_fmt(bottom)} to {_fmt(top)} m ({_fmt(top - bottom, 0)} m) | DERIVED |",
        f"| Box, longitude (east) | {_deg(left):.5f} to {_deg(right):.5f}° | DERIVED |",
        f"| Box, latitude (planetocentric) | {_deg(bottom):.5f} to {_deg(top):.5f}° | DERIVED |",
    ]
    if box.get("anchor"):
        a = box["anchor"]
        lines.append(
            f"| Parking position | site {a['site']}, drive {a['drive']}, held from sol {a['arrived_sol']} "
            f"to sol {a['left_sol']}; E {_fmt(a['easting'], 3)} m, N {_fmt(a['northing'], 3)} m, "
            f"elevation {_fmt(a['elevation'], 2)} m | MEASURED (PLACES) |"
        )
    lines += [
        "",
        "## Products",
        "",
        "| File | Source | Pixels | Pixel size | Read method | Time | Label |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for p in s["products"]:
        if p.get("skipped"):
            lines.append(f"| {p['file']} | `{p['source_id']}` | not made: {p['skipped']} | | | | |")
            continue
        lines.append(
            f"| {p['file']} | `{p['source_id']}` | {p['width']:,} × {p['height']:,} | {p['resolution_m']} m | "
            f"{p['method']} | {p['seconds']:.0f} s | {p['label']} |"
        )
    lines += [
        "",
        "## Where the elevation comes from",
        "",
        "The USGS product lists 12 HiRISE stereo pairs and falls back to CTX, then HRSC, then MOLA "
        "elsewhere. A pair counts as HiRISE stereo where its two images overlap (footprints from the "
        "PDS Orbital Data Explorer). Label: DERIVED. Footprint vertices are rounded to 0.001° of "
        "longitude (about 59 m), so class edges are uncertain by roughly 30 m.",
        "",
        "| DEM source | Share of the site box | Share of Curiosity's localizations in the box |",
        "| --- | --- | --- |",
        f"| HiRISE stereo | {cov['box_percent']['hirise_stereo']:.1f}% | {cov['path_percent']['hirise_stereo']:.1f}% |",
        f"| CTX, HRSC or MOLA | {cov['box_percent']['ctx_hrsc_or_mola']:.1f}% | "
        f"{cov['path_percent']['ctx_hrsc_or_mola']:.1f}% |",
        "",
        f"Localizations checked: {cov['path_points']:,}. DEM nodata cells in the box: {cov['nodata_cells']:,}.",
        "",
        "| USGS stereo pair | Share of the site box |",
        "| --- | --- |",
    ]
    for name, pct in sorted(s["pairs"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {name} | {pct:.1f}% |")
    if s["missing_pairs"]:
        lines.append("")
        lines.append(
            "Pairs with no stereo overlap inside the box: " + ", ".join(s["missing_pairs"]) + "."
        )
    lines += ["", "| Public HiRISE DTM | Share of the site box |", "| --- | --- |"]
    for name, pct in sorted(s["dtms"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {name} | {pct:.1f}% |")
    lines += ["", f"**Gap-fill decision:** {s['gap_fill']}", ""]
    lines += [
        "## Georeferencing check (acceptance test B8)",
        "",
        "The DEM crop is sampled at every PLACES localization inside the box (all sols) and compared "
        "with the PLACES elevation; the comparison is repeated for horizontal shifts of up to "
        f"±{geo['search']['max_shift_m']} m to find the best fit.",
        "",
        "| Measure | Value | Target |",
        "| --- | --- | --- |",
        f"| Localizations compared | {geo['points']:,} ({geo['points_outside_or_nodata']} outside or on nodata) | |",
        f"| Median of DEM − PLACES elevation | {_fmt(geo['median_dem_minus_places_m'], 2)} m | within "
        f"±{geo['thresholds']['max_median_offset_m']} m |",
        f"| Median absolute deviation | {geo['mad_m']:.2f} m | |",
        f"| 90th percentile of absolute deviation | {geo['p90_abs_deviation_m']:.2f} m | |",
        f"| Best-fit shift (east, north) | {geo['best_shift_east_north_m'][0]:+.0f} m, "
        f"{geo['best_shift_east_north_m'][1]:+.0f} m | within ±{geo['thresholds']['max_best_shift_m']} m |",
        f"| Median absolute deviation at best shift | {geo['mad_at_best_shift_m']:.2f} m | |",
        f"| Crop bounds agree (DEM and orthophoto) | {s['bounds_check']} | within one DEM pixel |",
        f"| **Result** | **{'PASS' if geo['passed'] else 'FAIL'}** | |",
        "",
        f"Quicklook for a visual check (orthophoto, hillshade and the rover path in cyan): "
        f"`data/sites/{s['site']}/quicklook.png` (not committed).",
        "",
    ]
    return "\n".join(lines)


def update_fetch_log(sources_log: Path, site: str, rows: list[dict]) -> None:
    """Rewrite this site's block inside the marked fetch-log section of SOURCES_LOG.md."""
    text = sources_log.read_text(encoding="utf-8")
    start, end = "<!-- fetch-log:start -->", "<!-- fetch-log:end -->"
    if start not in text:
        text = text.rstrip("\n") + (
            "\n\n## Fetch log\n\nWritten by `make fetch`; one block per site, replaced on each run. "
            "Raw files stay in `data/` (gitignored).\n\n" + start + "\n" + end + "\n"
        )
    head, rest = text.split(start, 1)
    body, tail = rest.split(end, 1)
    blocks = dict(re.findall(r"<!-- site:(\S+) -->\n(.*?)<!-- /site -->\n", body, flags=re.S))
    table = [
        f"### {site}",
        "",
        "| Product | Source | Bounds (E, N; m) | Size | Method | Processed (UTC) | Pipeline |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        table.append(
            f"| {r['file']} | `{r['source_id']}` | {r['bounds']} | {r['size']} | {r['method']} | "
            f"{r['processed']} | {r['pipeline']} |"
        )
    blocks[site] = "\n".join(table) + "\n\n"
    new_body = "\n" + "".join(
        f"<!-- site:{k} -->\n{v}<!-- /site -->\n" for k, v in sorted(blocks.items())
    )
    sources_log.write_text(head + start + new_body + end + tail, encoding="utf-8", newline="\n")
