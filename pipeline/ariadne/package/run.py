# Written with AI assistance (Claude Code). See AI_USE.md.
"""`ariadne package`: write web/public/sites/<site>/ for the Habitat Planner.

Everything the browser loads is written here from the derived layers, the plans and the photo
source: a manifest with each layer's provenance, overlays as PNG, vectors as GeoJSON, the plans
with their timelines, terrain chunks for the 3D rehearsal, and Navcam billboards.
"""

from __future__ import annotations

import json
import math
import shutil
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ariadne import __version__ as PIPELINE_VERSION
from ariadne.config import load_derive_config, setting
from ariadne.derive.io import read_raster
from ariadne.fetch import places
from ariadne.guardrails import repo_root
from ariadne.models import msl_time
from ariadne.package import layers as L
from ariadne.package import photos as P
from ariadne.package import png
from ariadne.package import timeline as T

ORTHO_DATE = "2022-12-01 (USGS orthophoto mosaic v3)"
DEM_DATE = "2022-11-09 (USGS DEM mosaic v3)"
# Okabe-Ito colors, readable with common colour-vision deficiencies; legends carry text too.
GO, CAUTION, NOGO = [0, 158, 115, 70], [230, 159, 0, 150], [213, 94, 0, 210]
USER_AGENT = "ariadne-pipeline (NASA Space Apps 2026 entry)"


def block(a, k, how="mean"):
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    b = a[:h, :w].reshape(h // k, k, w // k, k)
    return b.max(axis=(1, 3)) if how == "max" else np.nanmean(b, axis=(1, 3))


def hillshade(z, res):
    from ariadne.derive.ridge_labels import hillshade as hs

    return hs(np.nan_to_num(z, nan=float(np.nanmean(z))), res)


def gray(a, lo_q=2, hi_q=98):
    v = a[np.isfinite(a) & (a > 0)]
    lo, hi = np.percentile(v, [lo_q, hi_q])
    scaled = np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1) * 255
    return np.nan_to_num(scaled, nan=0.0).astype(np.uint8)


def _class_legend(names):
    return [
        {"value": 0, "color": GO, "label": f"go ({names[0]})"},
        {"value": 1, "color": CAUTION, "label": f"caution ({names[1]})"},
        {"value": 2, "color": NOGO, "label": f"no-go ({names[2]})"},
    ]


def raster_layers(site_dir: Path, out: Path, cfg, derived_date: str, log) -> tuple[list, dict]:
    d = site_dir / "derived"
    (out / "layers").mkdir(parents=True, exist_ok=True)
    dem, t, _ = read_raster(site_dir / "dem.tif")
    ortho, ot, _ = read_raster(site_dir / "ortho.tif", as_float=False)
    k = int(round(1.0 / abs(ot.a)))  # 25 cm -> 1 m blocks
    o1 = block(np.where(ortho > 0, ortho, np.nan).astype(np.float32), k)
    t1 = type(ot)(ot.a * k, 0, ot.c, 0, ot.e * k, ot.f)
    png.write_png(out / "layers" / "imagery.png", gray(o1))
    b1 = L.bounds(t1, o1.shape)
    # a 2 m overview loads first; the browser swaps in the 1 m image once the map is up
    o2 = block(o1, 2)
    png.write_png(out / "layers" / "imagery_2m.png", gray(o2))
    b_over = L.bounds(t1, (o2.shape[0] * 2, o2.shape[1] * 2))
    t2 = type(t)(t.a * 2, 0, t.c, 0, t.e * 2, t.f)
    z2 = block(dem, 2)
    png.write_png(out / "layers" / "hillshade.png", hillshade(z2, 2.0))
    b2 = L.bounds(t2, z2.shape)
    wslope = setting(cfg, "walkability", "walker_slope_deg")
    rslope = setting(cfg, "walkability", "rover_slope_deg")
    entries = [
        {"id": "imagery", "title": "HiRISE imagery", "file": "layers/imagery_2m.png",
         "file_detail": "layers/imagery.png", "bounds_detail_m": b1, "bounds_m": b_over,
         "resolution_m": 1.0, "sources": ["usgs-gale-ortho-25cm"],
         "date": ORTHO_DATE, "label": "MEASURED", "legend": None, "group": "base",
         "description": "USGS 25 cm orthophoto mosaic from HiRISE, averaged to 1 m.",
         "default_visible": True, "opacity": 1.0},
        {"id": "hillshade", "title": "Shaded relief", "file": "layers/hillshade.png",
         "bounds_m": b2, "resolution_m": 2.0, "sources": ["usgs-gale-dem-1m"], "date": DEM_DATE,
         "label": "DERIVED", "legend": None, "group": "base",
         "description": "Shaded relief of the 1 m DEM averaged to 2 m (light from the northwest).",
         "default_visible": False, "opacity": 0.6},
    ]  # fmt: skip
    for who, slopes, title in (("walker", wslope, "Walkability, suited walker"),
                               ("rover", rslope, "Walkability, rover")):  # fmt: skip
        cls, ct, _ = read_raster(d / f"walk_class_{who}.tif", as_float=False)
        c2 = block(np.where(cls == 255, 0, cls).astype(np.int16), 2, "max")
        c2[block((cls == 255).astype(np.int16), 2, "max") > 0] = 255
        legend = _class_legend([f"slope up to {slopes[0]}°", f"{slopes[0]} to {slopes[1]}°",
                                f"above {slopes[1]}° or other hazard"])  # fmt: skip
        png.write_png(out / "layers" / f"walk_{who}.png", L.colorize_classes(c2, legend))
        entries.append(
            {"id": f"walk_{who}", "title": title, "file": f"layers/walk_{who}.png",
             "bounds_m": b2, "resolution_m": 2.0,
             "sources": ["usgs-gale-dem-1m", "usgs-gale-ortho-25cm", "trek-themis-night-ir"],
             "date": derived_date, "label": "MODELED", "legend": legend, "group": "safety",
             "description": "Go, caution or no-go from slope at the traveller's footprint "
             "scale, roughness, dark objects, the sand proxy and drop-offs (PLACEHOLDER "
             "thresholds; the worst cell of each 2 m block is shown).",
             "default_visible": who == "walker", "opacity": 0.7}
        )  # fmt: skip
    oc, _, _ = read_raster(d / "overcautious_walker.tif", as_float=False)
    hatched = L.hatch(oc == 1, spacing=4, color=[240, 228, 66, 255], width=2)
    png.write_png(out / "layers" / "overcautious_walker.png", hatched)
    entries.append(
        {"id": "overcautious_walker", "title": "Map may be over-cautious here",
         "file": "layers/overcautious_walker.png", "bounds_m": L.bounds(t, oc.shape),
         "resolution_m": 1.0, "sources": ["usgs-gale-dem-1m", "ode-hirise-footprints"],
         "date": derived_date, "label": "MODELED",
         "legend": [{"color": [240, 228, 66, 255], "label": "hatched: no-go by slope in a DEM "
                     "seam or low-confidence zone, check by eye"}],
         "group": "safety", "pattern": "hatch",
         "description": "The rover check can only measure false alarms, and they cluster at "
         "DEM seams. The planner still avoids these cells; the crew should check them by eye.",
         "default_visible": True, "opacity": 1.0}
    )  # fmt: skip
    for lid, fname, title, vmin, vmax, stops, unit, label, desc in (
        ("shielding", "shielding.tif", "Shielding index S", 0.8, 1.0,
         [[8, 48, 107], [66, 146, 198], [247, 251, 255]], "S (1 = open sky)", "MODELED",
         "Zenith-weighted open-sky fraction, calibrated on one RAD measurement (Murray Buttes). "
         "Lower is better shielded."),
        ("confidence", "confidence.tif", "Confidence", 0.4, 1.0,
         [[84, 39, 143], [158, 154, 200], [242, 240, 247]], "0 to 1", "MODELED",
         "From the DEM source, distance to Curiosity's positions and model flags (seams, crop "
         "edge). PLACEHOLDER weights."),
    ):  # fmt: skip
        a, at, _ = read_raster(d / fname)
        a2 = block(a, 2)
        png.write_png(out / "layers" / f"{lid}.png", L.colorize_ramp(a2, vmin, vmax, stops, 200))
        entries.append(
            {"id": lid, "title": title, "file": f"layers/{lid}.png", "bounds_m": b2,
             "resolution_m": 2.0, "sources": ["usgs-gale-dem-1m", "mola-dem-463m"],
             "date": derived_date, "label": label, "group": "science" if lid == "shielding"
             else "uncertainty",
             "ramp": {"min": vmin, "max": vmax, "stops": stops, "unit": unit},
             "legend": [{"color": stops[0] + [200], "label": f"{vmin} {unit}"},
                        {"color": stops[-1] + [200], "label": f"{vmax} {unit}"}],
             "description": desc, "default_visible": False, "opacity": 0.7}
        )  # fmt: skip
    rd, _, _ = read_raster(d / "ridges.tif", as_float=False)
    rleg = [{"value": 1, "color": [204, 121, 167, 170], "label": "ridge"},
            {"value": 2, "color": [86, 180, 233, 150], "label": "hollow"}]  # fmt: skip
    r2 = block(rd.astype(np.int16), 2, "max")
    png.write_png(out / "layers" / "ridges.png", L.colorize_classes(r2, rleg))
    entries.append(
        {"id": "ridges", "title": "Boxwork ridges and hollows", "file": "layers/ridges.png",
         "bounds_m": b2, "resolution_m": 2.0, "sources": ["usgs-gale-dem-1m"],
         "date": derived_date, "label": "MODELED", "legend": rleg, "group": "science",
         "description": "From TPI and local relief, PLACEHOLDER thresholds until the team's "
         "labels tune them.", "default_visible": False, "opacity": 0.7}
    )  # fmt: skip
    plan_dir = site_dir / "plan"
    if (plan_dir / "shelter_minutes.tif").exists():
        sm, st, _ = read_raster(plan_dir / "shelter_minutes.tif")
        stops = [[0, 109, 44], [161, 217, 155], [255, 255, 204]]
        png.write_png(out / "layers" / "shelter_minutes.png",
                      L.colorize_ramp(sm, 0.0, 20.0, stops, 190))  # fmt: skip
        entries.append(
            {"id": "shelter_minutes", "title": "Minutes to shelter", "file":
             "layers/shelter_minutes.png", "bounds_m": L.bounds(st, sm.shape),
             "resolution_m": float(abs(st.a)), "sources": ["usgs-gale-dem-1m"],
             "date": derived_date, "label": "MODELED", "group": "safety",
             "ramp": {"min": 0, "max": 20, "stops": stops, "unit": "minutes"},
             "legend": [{"color": stops[0] + [190], "label": "0 minutes"},
                        {"color": stops[-1] + [190], "label": "20 minutes or more"}],
             "description": "Walking time on the walker model (PLACEHOLDER suit settings) to "
             "the nearest terrain shelter (S at most 0.95) or the rover.",
             "default_visible": False, "opacity": 0.7}
        )  # fmt: skip
    log(f"  {len(entries)} raster layers written")
    return entries, {"site_transform": t, "dem": dem}


def vector_layers(site_dir: Path, out: Path, derived_date: str) -> list:
    (out / "vectors").mkdir(parents=True, exist_ok=True)
    d = site_dir / "derived"
    items = [
        ("fractures", d / "fractures.geojson", "Fractures", "MODELED", ["usgs-gale-ortho-25cm"],
         "Dark central lines on ridges, 10 m or longer (line filter on the 25 cm image)."),
        ("seams", d / "seams.geojson", "Candidate DEM seams", "DERIVED",
         ["ode-hirise-footprints"], "Edges of the USGS stereo-pair footprints; positions "
         "uncertain by about 30 m."),
        ("rover_path", site_dir / "rover_path.geojson", "Curiosity's path", "MEASURED",
         ["msl-places"], "Curiosity's localizations in the site window (PLACES)."),
        ("drill_sites", site_dir / "drill_sites.geojson", "Drill holes", "MEASURED",
         ["msl-places", "curiosity-blog-4563"], "Curiosity's position while drilling."),
    ]  # fmt: skip
    entries = []
    for lid, src, title, label, sources, desc in items:
        if not src.exists():
            continue
        gj = json.loads(src.read_text(encoding="utf-8"))
        (out / "vectors" / f"{lid}.geojson").write_text(json.dumps(gj, separators=(",", ":")),
                                                        encoding="utf-8", newline="\n")  # fmt: skip
        entries.append({"id": lid, "title": title, "file": f"vectors/{lid}.geojson",
                        "kind": "vector", "resolution_m": None, "sources": sources,
                        "date": derived_date, "label": label, "legend": None, "group": "context",
                        "description": desc, "default_visible": lid in ("rover_path",),
                        "opacity": 1.0})  # fmt: skip
    return entries


def plans_with_timelines(root: Path, site: str, site_dir: Path, out: Path, ref_sol: int, log):
    (out / "plans").mkdir(parents=True, exist_ok=True)
    view, vt, _ = read_raster(site_dir / "derived" / "viewshed_staging.tif", as_float=False)

    def in_sight(xy):
        r = int((xy[1] - vt.f) / vt.e)
        c = int((xy[0] - vt.c) / vt.a)
        return 0 <= r < view.shape[0] and 0 <= c < view.shape[1] and bool(view[r, c])

    entries = []
    for f in sorted((root / "docs" / "plan").glob(f"{site}-*.json")):
        plan = json.loads(f.read_text(encoding="utf-8"))
        sx, sy = plan["legs"][0]["path_xy_m"][0] if plan["legs"] else plan["margins"][0]["xy_m"]
        lon = math.degrees(sx / places.MARS_RADIUS_M)
        lat = math.degrees(sy / places.MARS_RADIUS_M)
        start = T.ltst_start(msl_time.sol_start_utc(ref_sol), 9.0, lon, lat)
        sun = T.sun_elevation(start, [m["t_min"] for m in plan["margins"]], lon, lat)
        plan["timeline"] = T.build(plan, in_sight, sun)
        plan["scenario"]["start_utc"] = start.replace(microsecond=0).isoformat()
        plan["scenario"]["start_note"] = (
            f"PLACEHOLDER: sol {ref_sol} at 09:00 local true solar time, for the sun track"
        )
        preset = plan["scenario"]["preset"]
        (out / "plans" / f"{preset}.json").write_text(json.dumps(plan, separators=(",", ":")),
                                                      encoding="utf-8", newline="\n")  # fmt: skip
        entries.append({"preset": preset, "file": f"plans/{preset}.json",
                        "title": {"safest": "Safest", "balanced": "Balanced",
                                  "most_science": "Most science"}[preset],
                        "totals": plan["totals"]})  # fmt: skip
    log(f"  {len(entries)} plans with timelines")
    return entries


def terrain(site_dir: Path, out: Path, ctx: dict, log) -> dict:
    """Heightmap chunks (2 m and 8 m) and a 1 m texture over the planning window."""
    win_path = site_dir / "plan" / "c_home.tif"
    _, wt, _ = read_raster(win_path)
    with __import__("rasterio").open(win_path) as src:
        wshape = src.shape
    t, dem = ctx["site_transform"], ctx["dem"]
    r0 = int(round((wt.f - t.f) / t.e))
    c0 = int(round((wt.c - t.c) / t.a))
    k = int(round(abs(wt.a) / abs(t.a)))
    z = dem[r0 : r0 + wshape[0] * k, c0 : c0 + wshape[1] * k]
    z2 = block(z, k)
    (out / "terrain").mkdir(parents=True, exist_ok=True)
    chunks = []
    for ch in L.terrain_chunks(z2, chunk=128, coarse=4):
        a, b = ch["rows_cols"][:2]
        name = f"terrain/z_{a}_{b}"
        # raw little-endian uint16 (browsers read PNGs back as 8-bit, which would lose height)
        (out / f"{name}_fine.bin").write_bytes(ch["fine"].astype("<u2").tobytes())
        (out / f"{name}_coarse.bin").write_bytes(ch["coarse"].astype("<u2").tobytes())
        files = {"fine": f"{name}_fine.bin", "coarse": f"{name}_coarse.bin"}
        shapes = {"fine": list(ch["fine"].shape), "coarse": list(ch["coarse"].shape)}
        chunks.append({"rows_cols": ch["rows_cols"], "files": files, "shapes": shapes})
    ortho, ot, _ = read_raster(site_dir / "ortho.tif", as_float=False)
    kk = int(round(1.0 / abs(ot.a)))
    orr = int(round((wt.f - ot.f) / ot.e))
    occ = int(round((wt.c - ot.c) / ot.a))
    span = int(round(wshape[0] * abs(wt.a) / abs(ot.a)))
    tex = ortho[orr : orr + span, occ : occ + span].astype(np.float32)
    tex = block(np.where(tex > 0, tex, np.nan), kk)
    png.write_png(out / "terrain" / "texture.png", gray(tex))
    log(f"  terrain: {len(chunks)} chunks, texture {tex.shape[1]} x {tex.shape[0]}")
    return {
        "bounds_m": L.bounds(wt, wshape),
        "resolution_m": float(abs(wt.a)),
        "coarse_factor": 4,
        "chunk_cells": 128,
        "z0": float(np.nanmin(z2)),
        "scale": 0.01,
        "texture": "terrain/texture.png",
        "texture_resolution_m": 1.0,
        "chunks": chunks,
        "label": "DERIVED",
        "sources": ["usgs-gale-dem-1m", "usgs-gale-ortho-25cm"],
    }


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def raw_items_for_sol(cache: Path, sol: int) -> list:
    path = cache / f"sol_{sol:05d}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    items, page = [], 0
    while True:
        url = (f"{P.API}?order=sol%20desc&per_page=100&page={page}"
               f"&condition_1=msl:mission&condition_2={sol}:sol:in")  # fmt: skip
        d = _get_json(url)
        items += d.get("items", [])
        if not d.get("more") or page > 20:
            break
        page += 1
        time.sleep(0.3)
    cache.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items), encoding="utf-8", newline="\n")
    return items


def billboards(
    root: Path,
    site_dir: Path,
    out: Path,
    plans: list,
    log,
    per_transect: int = 2,
    max_photos: int = 16,
    max_m: float = 800.0,
    max_angle: float = 20.0,
    drives_per_transect: int = 4,
) -> list:
    """Navcam frames taken from Curiosity's path that look toward a planned transect (within
    max_m and max_angle), up to per_transect each, placed at their capture points."""
    import pandas as pd

    cols = ["frame", "site", "drive", "easting", "northing", "yaw", "sol"]
    raw = pd.read_csv(
        root / "data" / "sources" / "msl-places" / "localized_interp.csv", usecols=cols
    )
    raw = raw[raw.frame == "ROVER"]
    locs = {(int(r.site), int(r.drive)): {"easting": r.easting, "northing": r.northing,
                                          "yaw": r.yaw} for r in raw.itertuples()}  # fmt: skip
    transects: dict = {}
    for p in plans:
        plan = json.loads((out / p["file"]).read_text(encoding="utf-8"))
        for s in plan["stations"]:
            transects.setdefault(s["transect_source_id"], []).append(s["xy_m"])
    # the sols of the few drives nearest each transect (photos look out from Curiosity's path)
    e, n = raw.easting.to_numpy(), raw.northing.to_numpy()
    sols = set()
    for xys in transects.values():
        x, y = np.mean(np.array(xys), axis=0)
        d = np.hypot(e - x, n - y)
        order = np.argsort(d)
        seen = set()
        for k in order:
            if d[k] > max_m:
                break
            key = (int(raw.site.iloc[k]), int(raw.drive.iloc[k]))
            if key not in seen:
                seen.add(key)
                sols.add(int(raw.sol.iloc[k]))
            if len(seen) >= drives_per_transect:
                break
    sols = sorted(sols)
    cache = root / "data" / "sources" / "raw-images"
    cands = []
    for sol in sols:
        for it in raw_items_for_sol(cache, sol):
            if it.get("instrument") not in ("NAV_LEFT_B", "NAV_RIGHT_B"):
                continue
            if (it.get("extended") or {}).get("sample_type") != "full":
                continue
            ph = P.place(it, locs)
            if ph is not None and -20.0 <= ph["view_elevation_deg"] <= 5.0:
                cands.append(ph)
    log(f"  photos: {len(cands)} placed Navcam frames from {len(sols)} sols")
    chosen, used = [], set()
    for tid, xys in transects.items():
        scored = []
        for ph in cands:
            if ph["imageid"][4:13] in used:  # one frame per stereo pair (same clock time)
                continue
            hits = [xy for xy in xys if P.looks_at(ph, xy, max_m, max_angle)]
            if hits:
                d = min(math.hypot(xy[0] - ph["xy_m"][0], xy[1] - ph["xy_m"][1]) for xy in hits)
                scored.append((-len(hits), d, ph["instrument"] != "NAV_LEFT_B", ph))
        scored.sort(key=lambda s: s[:3])
        for *_, ph in scored[:per_transect]:
            ph["transect_source_id"] = tid
            chosen.append(ph)
            used.add(ph["imageid"][4:13])
    chosen = chosen[:max_photos]
    (out / "photos").mkdir(parents=True, exist_ok=True)
    photo_cache = site_dir / "photos"
    photo_cache.mkdir(parents=True, exist_ok=True)
    for ph in chosen:
        local = photo_cache / f"{ph['imageid']}.jpg"
        if not local.exists():
            req = urllib.request.Request(ph["url"], headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                local.write_bytes(r.read())
            time.sleep(0.3)
        shutil.copyfile(local, out / "photos" / local.name)
        ph["file"] = f"photos/{local.name}"
        ph["label"] = "MEASURED"
        # show only the upper part: the lower part of most Navcam frames shows the rover deck,
        # and no hardware markings or emblems are shown as graphics (CLAUDE.md rule 5)
        ph["show_top_fraction"] = 0.55
    log(f"  photos: {len(chosen)} billboards for {len(transects)} planned transects")
    return chosen


def package_site(site: str = "boxwork", log=print) -> dict:
    t0 = time.time()
    root = repo_root()
    site_dir = root / "data" / "sites" / site
    out = root / "web" / "public" / "sites" / site
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_derive_config()
    summary = json.loads((site_dir / "derived" / "summary.json").read_text(encoding="utf-8"))
    derived_date = summary["computed_utc"][:10]
    import yaml

    site_raw = yaml.safe_load((root / "config" / "sites" / f"{site}.yaml").read_text("utf-8"))
    ref_sol = int(site_raw["reference_sol"]["value"])
    log(f"Packaging {site} into {out.relative_to(root)}")
    rasters, ctx = raster_layers(site_dir, out, cfg, derived_date, log)
    for r in rasters:
        r["kind"] = "raster"
    vectors = vector_layers(site_dir, out, derived_date)
    plans = plans_with_timelines(root, site, site_dir, out, ref_sol, log)
    ter = terrain(site_dir, out, ctx, log)
    pics = billboards(root, site_dir, out, plans, log)
    t = ctx["site_transform"]
    manifest = {
        "site": site,
        "title": site_raw.get("title", site),
        "pipeline_version": PIPELINE_VERSION,
        "packaged_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "crs": "Equirectangular metres on the 3,396,190 m Mars sphere (east, north)",
        "bounds_m": L.bounds(t, ctx["dem"].shape),
        "staging_xy_m": summary["shelters"]["staging_xy"],
        "staging_label": "PLACEHOLDER",
        "layers": rasters + vectors,
        "plans": plans,
        "terrain": ter,
        "photos": pics,
        "eye_height_m": {"value": 1.7, "label": "PLACEHOLDER", "source": "PROMPT.md section 6"},
        "walker_model": "MODELED with PLACEHOLDER suit settings; EXTRAPOLATED to Mars gravity",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8",
                                       newline="\n")  # fmt: skip
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    log(f"  package written: {size / 2**20:.1f} MB ({time.time() - t0:.0f} s)")
    return manifest
