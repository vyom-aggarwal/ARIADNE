# Written with AI assistance (Claude Code). See AI_USE.md.
"""Site stages after the horizons: light, walkability, ridges, shelters, line of sight, science,
uncertainty. Each takes the shared context dict built by run.derive_site and adds to it."""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from affine import Affine
from scipy import ndimage
from scipy.spatial import cKDTree

from ariadne.config import config_dir, setting
from ariadne.derive import horizons as hz
from ariadne.derive import light, los, ridges, science, seams, shelters, terrain, uncertainty
from ariadne.derive import walkability as wk
from ariadne.derive.io import feature_collection, read_raster, write_geojson, write_layer
from ariadne.fetch import places
from ariadne.labels import Label
from ariadne.models import msl_time

STRIP = 4096  # 25 cm rows per strip (1,024 m)


def _xy_to_rc(t: Affine, x: float, y: float) -> tuple[int, int]:
    return int(math.floor((y - t.f) / t.e)), int(math.floor((x - t.c) / t.a))


def _rc_to_xy(t: Affine, r: float, c: float) -> tuple[float, float]:
    return t.c + (c + 0.5) * t.a, t.f + (r + 0.5) * t.e


def _ltst_from_seconds(track: light.SunTrack, seconds: np.ndarray) -> np.ndarray:
    step = (track.times[1] - track.times[0]).total_seconds()
    lt = np.unwrap(track.ltst * 15.0, period=360.0) / 15.0
    k = np.asarray(seconds, dtype=np.float64) / step
    out = np.interp(k, np.arange(lt.size), lt) % 24.0
    return np.where(np.isnan(seconds), np.nan, out).astype(np.float32)


def stage_light(ctx, log):
    cfg, t, crs, out = ctx["cfg"], ctx["t"], ctx["crs"], ctx["out"]
    ref_sol = int(ctx["site_cfg_raw"].get("reference_sol", {}).get("value"))
    day = msl_time.sol_start_utc(ref_sol)
    lon, lat = ctx["centre_lonlat"]
    track = light.local_noon_track(day, lon, lat, float(setting(cfg, "light", "time_step_s")))
    rise, sset, insol = light.sun_grid(
        ctx["codes"], ctx["qmin"], ctx["qstep"], hz.NODATA_CODE, track, ctx["slope"], ctx["aspect"]
    )
    rise_l, set_l = _ltst_from_seconds(track, rise), _ltst_from_seconds(track, sset)
    common = dict(resolution_m=ctx["res"], inputs=["horizons.tif", "slope.tif", "aspect.tif"])
    note = (
        f"Sol {ref_sol} ({track.times[0].date()} to {track.times[-1].date()} UTC); sun centre; "
        "Mars24."
    )
    write_layer(
        out / "sunrise_ltst.tif",
        rise_l,
        t,
        crs,
        None,
        product_id="Sunrise, local true solar time (hours)",
        label=Label.MODELED,
        notes=note,
        **common,
    )
    write_layer(
        out / "sunset_ltst.tif",
        set_l,
        t,
        crs,
        None,
        product_id="Sunset, local true solar time (hours)",
        label=Label.MODELED,
        notes=note,
        **common,
    )
    write_layer(
        out / "insolation.tif",
        insol,
        t,
        crs,
        None,
        product_id="Daily insolation relative to flat open ground",
        label=Label.MODELED,
        notes=note + " Direct sunlight only; no scattered light.",
        **common,
    )
    ctx["light"] = {
        "reference_sol": ref_sol,
        "track_start_utc": track.times[0].isoformat(),
        "sunrise_ltst": _stats(rise_l),
        "sunset_ltst": _stats(set_l),
        "insolation_ratio": _stats(insol),
    }
    ctx["minutes_to_shelter"] = None
    log("  light: sunrise, sunset and insolation written")


def _image_layers(ortho: np.ndarray, background_px: int, ratio: float, window_blocks: int):
    """1 m image measures on the orthophoto's own grid, computed in strips."""
    k = 4
    h4 = (ortho.shape[0] // k) * k
    w4 = (ortho.shape[1] // k) * k
    img = ortho[:h4, :w4]
    means, stds = [], []
    for r0 in range(0, h4, STRIP):
        m, s = wk.image_block_stats(img[r0 : r0 + STRIP], k)
        means.append(m)
        stds.append(s)
    mean1, std1 = np.vstack(means), np.vstack(stds)
    filled = np.where(np.isnan(mean1), np.nanmedian(mean1), mean1)
    bg = ndimage.median_filter(filled, size=background_px, mode="nearest")
    dark_parts, jxx, jyy, jxy = [], [], [], []
    for r0 in range(0, h4, STRIP):
        strip = img[r0 : r0 + STRIP]
        b = wk.block_view(strip, k).astype(np.float32)
        bgs = bg[r0 // k : r0 // k + b.shape[0]]
        dark = (b > 0) & (b < ratio * bgs[:, None, :, None])
        valid = (b > 0).sum(axis=(1, 3))
        with np.errstate(invalid="ignore", divide="ignore"):
            dark_parts.append(
                np.where(valid > 0, dark.sum(axis=(1, 3)) / valid, np.nan).astype(np.float32)
            )
        # structure tensor on a 2 x 2 averaged strip, with a small overlap for the gradient
        lo, hi = max(0, r0 - 8), min(h4, r0 + STRIP + 8)
        half = wk.block_view(img[lo:hi], 2).astype(np.float32).mean(axis=(1, 3))
        gy, gx = np.gradient(half)
        top = (r0 - lo) // 2
        n_half = strip.shape[0] // 2
        gx, gy = gx[top : top + n_half], gy[top : top + n_half]
        jxx.append(wk.block_view(gx * gx, 2).mean(axis=(1, 3)))
        jyy.append(wk.block_view(gy * gy, 2).mean(axis=(1, 3)))
        jxy.append(wk.block_view(gx * gy, 2).mean(axis=(1, 3)))
    jxx, jyy, jxy = (
        ndimage.uniform_filter(np.vstack(a), window_blocks, mode="nearest") for a in (jxx, jyy, jxy)
    )
    with np.errstate(invalid="ignore", divide="ignore"):
        coh = np.nan_to_num(np.sqrt((jxx - jyy) ** 2 + 4 * jxy**2) / (jxx + jyy), nan=0.0)
    texture = np.sqrt(
        ndimage.uniform_filter(np.nan_to_num(std1, nan=0.0) ** 2, window_blocks, mode="nearest")
    )
    dark5 = ndimage.uniform_filter(
        np.nan_to_num(np.vstack(dark_parts), nan=0.0), window_blocks, mode="nearest"
    )
    return {
        "texture": texture.astype(np.float32),
        "coherence": coh.astype(np.float32),
        "dark": dark5.astype(np.float32),
    }


def texture_rank(site_dir, shape, t, crs, cfg) -> np.ndarray:
    """Image texture (RMS of 1 m block standard deviations over the dark-object window) as a
    percentile rank within the site, on the DEM grid. The walkability and ridge stages and the
    ridge tuning all use this one definition."""
    ortho, ot, _ = read_raster(site_dir / "ortho.tif", as_float=False)
    ot1 = Affine(ot.a * 4, 0, ot.c, 0, ot.e * 4, ot.f)
    lay = _image_layers(
        ortho,
        int(round(float(setting(cfg, "walkability", "dark_background_m")) / 1.0)),
        float(setting(cfg, "walkability", "dark_ratio")),
        int(round(float(setting(cfg, "walkability", "dark_window_m")))),
    )
    return wk.percentile_rank(wk.to_grid(lay["texture"], ot1, shape, t, crs))


def stage_walkability(ctx, log):
    cfg, t, crs, out, dem, res = (
        ctx["cfg"],
        ctx["t"],
        ctx["crs"],
        ctx["out"],
        ctx["dem"],
        ctx["res"],
    )
    site_dir = ctx["site_dir"]
    ortho, ot, _ = read_raster(site_dir / "ortho.tif", as_float=False)
    ot1 = Affine(ot.a * 4, 0, ot.c, 0, ot.e * 4, ot.f)
    lay = _image_layers(
        ortho,
        int(round(float(setting(cfg, "walkability", "dark_background_m")) / 1.0)),
        float(setting(cfg, "walkability", "dark_ratio")),
        int(round(float(setting(cfg, "walkability", "dark_window_m")))),
    )
    ctx["ortho"], ctx["ortho_t"] = ortho, ot
    grid = {k: wk.to_grid(v, ot1, dem.shape, t, crs) for k, v in lay.items()}
    ctx["texture_rank"] = wk.percentile_rank(grid["texture"])
    smooth_rank = 1.0 - ctx["texture_rank"]
    coh_rank = wk.percentile_rank(grid["coherence"])
    night_rank = None
    themis_path = site_dir / "themis_night_ir.tif"
    if themis_path.exists():
        th, tt, _ = read_raster(themis_path)
        night_rank = wk.percentile_rank(wk.to_grid(th, tt, dem.shape, t, crs))
    sand = wk.sand_proxy(smooth_rank, coh_rank, night_rank)
    conv = terrain.convexity(dem, res)
    relief = terrain.local_relief(dem, res, float(setting(cfg, "terrain", "relief_radius_m")))
    drop = wk.dropoffs(
        conv,
        relief,
        float(setting(cfg, "walkability", "dropoff_curvature_per_m")),
        float(setting(cfg, "walkability", "dropoff_relief_m")),
    )
    weights = setting(cfg, "walkability", "cost_weights")
    dark_c = float(setting(cfg, "walkability", "dark_density_caution"))
    # Slope at each traveller's footprint scale (fixed 2026-11-09, docs/PROGRESS.md): a plane
    # fit over a disc no smaller than the DEM's effective resolution.
    scales = wk.slope_scales(cfg)
    slope_w, _ = terrain.footprint_slope(dem, res, scales["walker_m"])
    slope_r, _ = terrain.footprint_slope(dem, res, scales["rover_m"])

    def walker(slope):
        return wk.walkability(
            slope,
            ctx["rough"],
            grid["dark"],
            sand,
            drop,
            tuple(setting(cfg, "walkability", "walker_slope_deg")),
            tuple(setting(cfg, "walkability", "walker_roughness_m")),
            dark_c,
            None,
            wk.CAUTION,
            weights,
        )

    def rover(slope):
        return wk.walkability(
            slope,
            ctx["rough"],
            grid["dark"],
            sand,
            drop,
            tuple(setting(cfg, "walkability", "rover_slope_deg")),
            tuple(setting(cfg, "walkability", "rover_roughness_m")),
            dark_c,
            float(setting(cfg, "walkability", "sand_caution")),
            wk.NOGO,
            weights,
        )

    cls_w, cost_w = walker(slope_w)
    cls_r, cost_r = rover(slope_r)
    # Kept for comparison, not used downstream: the Phase 2 first-run method (Horn slope of the
    # 1 m DEM) and the coarse end of the DEM resolution range.
    cls_r_horn, _ = rover(ctx["slope"])
    cls_r_coarse, _ = rover(terrain.footprint_slope(dem, res, scales["rover_coarse_m"])[0])
    cls_w_coarse, _ = walker(terrain.footprint_slope(dem, res, scales["walker_coarse_m"])[0])
    nan = np.isnan(dem)
    for a in (cls_w, cls_r, cls_r_horn, cls_r_coarse, cls_w_coarse):
        a[nan] = 255
    common = dict(
        resolution_m=res, settings={k: setting(cfg, "walkability", k) for k in cfg["walkability"]}
    )
    inputs = ["dem.tif", "ortho.tif"] + (["themis_night_ir.tif"] if night_rank is not None else [])
    cls_note = (
        "0 = go, 1 = caution, 2 = no-go, 255 = no data. PLACEHOLDER thresholds in "
        "config/derive.yaml."
    )
    write_layer(
        out / "walk_class_walker.tif",
        cls_w,
        t,
        crs,
        255,
        product_id="Walkability class, suited walker",
        label=Label.MODELED,
        notes=cls_note,
        inputs=inputs,
        **common,
    )
    write_layer(
        out / "walk_cost_walker.tif",
        cost_w,
        t,
        crs,
        None,
        product_id="Walking cost multiplier (NaN = no-go)",
        label=Label.MODELED,
        notes="1 on easy ground; relative, not metabolic.",
        inputs=inputs,
        **common,
    )
    write_layer(
        out / "walk_class_rover.tif",
        cls_r,
        t,
        crs,
        255,
        product_id="Walkability class, rover",
        label=Label.MODELED,
        notes=cls_note,
        inputs=inputs,
        **common,
    )
    for fname, arr, pid, note in (
        (
            "slope_walker.tif",
            slope_w,
            f"Slope at the walker's scale ({scales['walker_m']:.2f} m disc), degrees",
            "Least-squares plane over a disc the size of the DEM's effective resolution.",
        ),
        (
            "slope_rover.tif",
            slope_r,
            f"Slope at the rover's footprint ({scales['rover_m']:.2f} m disc), degrees",
            "Least-squares plane over a disc of Curiosity's length (NASA: 10 ft).",
        ),
    ):
        write_layer(
            out / fname,
            arr,
            t,
            crs,
            None,
            product_id=pid,
            label=Label.DERIVED,
            notes=note,
            inputs=["dem.tif"],
            resolution_m=res,
            settings=scales,
        )
    for fname, arr, pid, note in (
        (
            "walk_class_rover_horn1m.tif",
            cls_r_horn,
            "Walkability class, rover, Phase 2 first-run method (1 m Horn slope)",
            "Kept for comparison with the frozen first result; not used downstream.",
        ),
        (
            "walk_class_rover_coarse.tif",
            cls_r_coarse,
            "Walkability class, rover, slope at the coarse DEM resolution "
            f"({scales['rover_coarse_m']:.1f} m disc)",
            "Sensitivity case (20 image pixels); not used downstream.",
        ),
    ):
        write_layer(
            out / fname,
            arr,
            t,
            crs,
            255,
            product_id=pid,
            label=Label.MODELED,
            notes=cls_note + " " + note,
            inputs=inputs,
            **common,
        )
    write_layer(
        out / "sand_proxy.tif",
        sand,
        t,
        crs,
        None,
        product_id="Sand proxy, 0 to 1, relative within the site",
        label=Label.MODELED,
        notes="Mean of smooth-texture rank, ripple-direction rank"
        + (" and inverse THEMIS night-IR rank." if night_rank is not None else "."),
        inputs=inputs,
        resolution_m=res,
    )
    write_layer(
        out / "dark_density.tif",
        grid["dark"],
        t,
        crs,
        None,
        product_id="Share of 25 cm pixels much darker than their surroundings (5 m window)",
        label=Label.MODELED,
        notes="A proxy for rocks and pits; mosaic seams move the reference.",
        inputs=["ortho.tif"],
        resolution_m=res,
    )
    write_layer(
        out / "dropoffs.tif",
        drop.astype(np.uint8),
        t,
        crs,
        None,
        product_id="Ridge-edge drop-offs (1 = yes)",
        label=Label.MODELED,
        notes="Convex edges with at least 1 m of local relief.",
        inputs=["dem.tif"],
        resolution_m=res,
    )
    ctx.update(cls_w=cls_w, cost_w=cost_w, cls_r=cls_r, sand=sand, relief=relief)
    ctx["walkability"] = {
        "slope_scales_m": {k: round(v, 3) for k, v in scales.items()},
        "walker_class_share": _shares(cls_w),
        "rover_class_share": _shares(cls_r),
        "rover_class_share_horn_1m": _shares(cls_r_horn),
        "rover_class_share_coarse": _shares(cls_r_coarse),
        "walker_class_share_coarse": _shares(cls_w_coarse),
        "sand_proxy_uses_themis": night_rank is not None,
        "dropoff_share": round(float(np.mean(drop)), 4),
    }
    log("  walkability written")


def stage_ridges(ctx, log):
    cfg, t, crs, out, res = ctx["cfg"], ctx["t"], ctx["crs"], ctx["out"], ctx["res"]
    from ariadne.derive.ridge_run import smoothed

    sigma = float(setting(cfg, "ridges", "smooth_sigma_m"))
    radius = float(setting(cfg, "ridges", "tpi_radius_m"))
    tpi10 = terrain.tpi(smoothed(ctx["dem"], res, sigma), res, radius)
    relief = terrain.local_relief(
        ctx["dem"], res, float(setting(cfg, "terrain", "relief_radius_m"))
    )
    cls = ridges.ridge_hollow(
        tpi10,
        relief,
        float(setting(cfg, "ridges", "tpi_ridge_m")),
        float(setting(cfg, "ridges", "tpi_hollow_m")),
        float(setting(cfg, "ridges", "ridge_relief_m")),
    )
    tex_min = setting(cfg, "ridges", "texture_min_rank")
    if tex_min is not None and "texture_rank" in ctx:
        cls[(cls == ridges.RIDGE) & ~(ctx["texture_rank"] >= float(tex_min))] = ridges.OTHER
    ortho, ot = ctx["ortho"], ctx["ortho_t"]
    h4, w4 = (ortho.shape[0] // 4) * 4, (ortho.shape[1] // 4) * 4
    ortho = ortho[:h4, :w4]
    xs = ot.c + (np.arange(w4) + 0.5) * ot.a
    ys = ot.f + (np.arange(h4) + 0.5) * ot.e
    cols = np.clip(np.floor((xs - t.c) / t.a).astype(int), 0, cls.shape[1] - 1)
    rows = np.clip(np.floor((ys - t.f) / t.e).astype(int), 0, cls.shape[0] - 1)
    ridge_on_img = (cls == ridges.RIDGE)[rows[:, None], cols[None, :]]
    mask = ridges.fracture_mask(
        ortho,
        ridge_on_img,
        setting(cfg, "ridges", "fracture_sigmas_px"),
        float(setting(cfg, "ridges", "fracture_threshold")),
    )
    del ridge_on_img
    half = wk.block_view(mask, 2).any(axis=(1, 3))
    ht = Affine(ot.a * 2, 0, ot.c, 0, ot.e * 2, ot.f)
    feats, _ = ridges.skeleton_lines(
        half, ht, float(setting(cfg, "ridges", "fracture_min_length_m"))
    )
    # fracture cells on the DEM grid, from the kept lines only
    frac_1m = np.zeros(cls.shape, dtype=bool)
    for f in feats:
        for x, y in f["geometry"]["coordinates"]:
            r, c = _xy_to_rc(t, x, y)
            if 0 <= r < cls.shape[0] and 0 <= c < cls.shape[1]:
                frac_1m[r, c] = True
    write_layer(
        out / "ridges.tif",
        cls,
        t,
        crs,
        None,
        product_id="Boxwork ridges (1) and hollows (2)",
        label=Label.MODELED,
        notes="TPI at 10 m and local relief; PLACEHOLDER thresholds, not yet tuned on a "
        "hand-labeled sample.",
        resolution_m=res,
        inputs=["dem.tif"],
        settings={k: setting(cfg, "ridges", k) for k in cfg["ridges"]},
    )
    write_geojson(
        out / "fractures.geojson",
        feature_collection(f"{ctx['site']}_fractures", feats),
        product_id="Dark central fractures on ridges (lines 10 m or longer)",
        label=Label.MODELED,
        notes="Sato line filter on the 25 cm orthophoto inside the ridge mask; lines ordered along "
        "their main axis.",
        inputs=["ortho.tif", "ridges.tif"],
    )
    ctx.update(ridge_cls=cls, frac_1m=frac_1m)
    lengths = [f["properties"]["length_m"] for f in feats]
    ctx["ridges"] = {
        "ridge_share": round(float(np.mean(cls == ridges.RIDGE)), 4),
        "hollow_share": round(float(np.mean(cls == ridges.HOLLOW)), 4),
        "fractures": len(feats),
        "fracture_length_km": round(sum(lengths) / 1000, 2),
        "fracture_median_length_m": round(float(np.median(lengths)), 1) if lengths else None,
    }
    log(f"  ridges and {len(feats)} fractures written")


def _staging_xy(ctx) -> tuple[float, float]:
    st = ctx["site_cfg"].staging
    if st.get("drill_site"):
        for d in ctx.get("drills", []):
            if d["name"] == st["drill_site"]:
                return d["easting"], d["northing"]
    if st.get("parking"):
        p = ctx["calibration"]["parking"]
        return p["easting"], p["northing"]
    h, w = ctx["dem"].shape
    return _rc_to_xy(ctx["t"], h / 2, w / 2)


def stage_shelters_los(ctx, log):
    cfg, t, crs, out, res = ctx["cfg"], ctx["t"], ctx["crs"], ctx["out"], ctx["res"]
    zones = shelters.shelter_zones(
        ctx["s"],
        ctx["cls_w"],
        float(setting(cfg, "shielding", "shelter_max_s")),
        float(setting(cfg, "shielding", "shelter_min_area_m2")),
        res,
    )
    sx, sy = _staging_xy(ctx)
    srow, scol = _xy_to_rc(t, sx, sy)
    mins = shelters.minutes_to_shelter(
        ctx["cost_w"],
        zones,
        res,
        float(setting(cfg, "shelters", "walking_speed_m_s")),
        extra_sources=[(srow, scol)],
    )
    vis = los.viewshed(
        ctx["dem"],
        res,
        (srow, scol),
        float(setting(cfg, "line_of_sight", "antenna_height_m")),
        float(setting(cfg, "line_of_sight", "helmet_height_m")),
        float(setting(cfg, "line_of_sight", "max_range_m")),
    )
    write_layer(
        out / "shelters.tif",
        zones.astype(np.uint8),
        t,
        crs,
        None,
        product_id="Terrain shelter cells (1 = shelter)",
        label=Label.MODELED,
        notes="S at or below the PLACEHOLDER threshold, walkable, in zones of at least 4 m2.",
        resolution_m=res,
        inputs=["shielding.tif", "walk_class_walker.tif"],
    )
    write_layer(
        out / "minutes_to_shelter.tif",
        mins,
        t,
        crs,
        None,
        product_id="Walking minutes to the nearest shelter or the staging point",
        label=Label.MODELED,
        notes="PLACEHOLDER pace until Phase 3's suited-walking model.",
        resolution_m=res,
        inputs=["shelters.tif", "walk_cost_walker.tif"],
    )
    write_layer(
        out / "viewshed_staging.tif",
        vis.astype(np.uint8),
        t,
        crs,
        None,
        product_id="Line of sight from the staging antenna (3 m) to a helmet (1.8 m)",
        label=Label.MODELED,
        notes="Line of sight only; radio propagation is not modeled. PLACEHOLDER staging point and "
        "heights.",
        resolution_m=res,
        inputs=["dem.tif"],
    )
    ctx["minutes_to_shelter"] = mins
    walkable = ctx["cls_w"] != wk.NOGO
    within = np.isfinite(mins) & walkable
    ctx["shelters"] = {
        "shelter_share": round(float(np.mean(zones)), 4),
        "shelter_area_m2": round(float(zones.sum() * res * res)),
        "minutes_to_shelter": _stats(mins[within]) if within.any() else None,
        "staging_xy": [round(sx, 2), round(sy, 2)],
    }
    ctx["line_of_sight"] = {"visible_share_of_site": round(float(np.mean(vis)), 4)}
    log("  shelters, minutes-to-shelter and line of sight written")


def stage_science(ctx, log):
    if not ctx.get("drills"):
        return
    t, out, res = ctx["t"], ctx["out"], ctx["res"]
    sci = json.loads((config_dir() / "science.json").read_text(encoding="utf-8"))

    def v(k):
        return sci[k]["value"]

    trs = science.transects(
        ctx["ridge_cls"],
        ctx["dem"],
        ctx["cls_w"],
        ctx["frac_1m"],
        res,
        float(v("transect_spacing_m")),
        float(v("min_crest_length_m")),
        tuple(v("wall_distance_m")),
        tuple(v("hollow_distance_m")),
        float(v("fracture_snap_m")),
    )
    prior = []
    tpath = ctx["site_dir"] / "chemcam_targets.csv"
    if tpath.exists():
        df = pd.read_csv(tpath)
        prior += list(zip(df.easting, df.northing, strict=True))
    prior += [(d["easting"], d["northing"]) for d in ctx["drills"]]
    tree = cKDTree(np.array(prior)) if prior else None
    feats, scores = [], []
    for i, tr in enumerate(trs):
        stations = [
            ("crest", tr["crest"][0], tr["crest"][1], tr["crest"][2]),
            ("wall", tr["wall"][0], tr["wall"][1], "wall"),
            ("hollow", tr["hollow"][0], tr["hollow"][1], "hollow"),
        ]
        coords = []
        for kind, r, c, role in stations:
            x, y = _rc_to_xy(t, r, c)
            coords.append([round(x, 2), round(y, 2)])
            d = float(tree.query([x, y])[0]) if tree is not None else None
            mins = (
                ctx["minutes_to_shelter"][r, c] if ctx["minutes_to_shelter"] is not None else None
            )
            terms = {
                "role": float(v("role_values")[role]),
                "novelty": science.novelty(d, float(v("novelty_scale_m")))
                if d is not None
                else None,
                "spectral": None,
                "access": science.access(
                    float(mins) if mins is not None else None, float(v("access_scale_min"))
                ),
            }
            sc, missing = science.score(terms, v("weights"))
            scores.append(sc)
            feats.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": coords[-1]},
                    "properties": {
                        "transect": i,
                        "station": kind,
                        "role": role,
                        "score": round(sc, 3),
                        "terms": {
                            k: (None if x is None else round(x, 3)) for k, x in terms.items()
                        },
                        "missing": missing,
                        "distance_to_prior_m": None if d is None else round(d, 1),
                        "elevation_m": round(float(ctx["dem"][r, c]), 2),
                        "label": "MODELED",
                    },
                }
            )
        feats.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "transect": i,
                    "relief_m": round(tr["relief_m"], 2),
                    "label": "MODELED",
                },
            }
        )
    write_geojson(
        out / "transects.geojson",
        feature_collection(f"{ctx['site']}_transects", feats),
        product_id="Three-station science transects with scores",
        label=Label.MODELED,
        notes="Spectral context is not read yet, so its weight is set aside and listed as missing.",
        inputs=[
            "ridges.tif",
            "fractures.geojson",
            "walk_class_walker.tif",
            "chemcam_targets.csv",
            "drill_sites.geojson",
        ],
        settings={k: sci[k]["value"] for k in sci if not k.startswith("_")},
    )
    ctx["science"] = {
        "transects": len(trs),
        "on_fractures": sum(1 for tr in trs if tr["crest"][2] == "fracture"),
        "score": _stats(np.array(scores)) if scores else None,
        "prior_targets": len(prior),
        "missing_terms": ["spectral"],
    }
    log(f"  {len(trs)} transects written")


def stage_uncertainty(ctx, log):
    cfg, t, crs, out, res = ctx["cfg"], ctx["t"], ctx["crs"], ctx["out"], ctx["res"]
    src, _, _ = read_raster(ctx["site_dir"] / "source_class.tif", as_float=False)
    rover = places.load_rover_positions(
        ctx["root"] / "data" / "sources" / "msl-places" / "localized_interp.csv"
    )
    dist = uncertainty.distance_to_points(
        src.shape, t, rover.easting.to_numpy(), rover.northing.to_numpy()
    )
    h, w = src.shape
    rr, cc = np.mgrid[0:h, 0:w]
    edge = np.minimum.reduce([rr, cc, h - 1 - rr, w - 1 - cc]) * res
    # Candidate DEM mosaic seams: edges of the USGS stereo-pair footprints inside the crop.
    from shapely.geometry import box, mapping

    from ariadne.fetch import coverage

    ode_path = ctx["root"] / "data" / "sources" / "ode" / f"{ctx['site']}_hirise_rdrv11.json"
    pairs = coverage.pair_footprints(
        coverage.observation_footprints(json.loads(ode_path.read_text(encoding="utf-8")))
    )
    extent = box(t.c, t.f + t.e * h, t.c + t.a * w, t.f)
    lines = seams.seam_lines(list(pairs.values()), extent)
    seam_d = seams.seam_distance(src.shape, t, lines)
    seam_m = float(setting(cfg, "uncertainty", "seam_zone_m"))
    zone = seam_d <= seam_m
    flags = seams.model_flags(src, edge, 1000.0, zone)
    write_layer(
        out / "seam_distance.tif",
        np.where(np.isfinite(seam_d), seam_d, np.nan).astype(np.float32),
        t,
        crs,
        None,
        product_id="Distance to the nearest candidate DEM mosaic seam, m",
        label=Label.DERIVED,
        notes="Seams are the edges of the USGS stereo-pair footprints inside the crop (ODE "
        "footprints, uncertain by about 30 m); which pair wins in an overlap is not documented.",
        resolution_m=res,
        inputs=["ode-hirise-footprints", "dem.tif"],
        settings={"seam_zone_m": seam_m, "pairs": sorted(pairs)},
    )
    feats = []
    for name, fp in sorted(pairs.items()):
        part = seams.seam_lines([fp], extent)
        if not part.is_empty:
            feats.append(
                {
                    "type": "Feature",
                    "properties": {"pair": name, "length_m": round(part.length, 1)},
                    "geometry": mapping(part),
                }
            )
    write_geojson(
        out / "seams.geojson",
        feature_collection("dem_seams", feats),
        product_id="Candidate DEM mosaic seams (stereo-pair footprint edges)",
        label=Label.DERIVED,
        notes="Edges of each USGS stereo pair's footprint inside the crop. Positions uncertain "
        "by about 30 m. CCD seams inside one HiRISE image are not mapped.",
        inputs=["ode-hirise-footprints"],
    )
    conf = uncertainty.confidence(
        src,
        dist,
        flags,
        setting(cfg, "uncertainty", "source_score"),
        float(setting(cfg, "uncertainty", "image_distance_scale_m")),
        setting(cfg, "uncertainty", "weights"),
    )
    write_layer(
        out / "confidence.tif",
        conf,
        t,
        crs,
        None,
        product_id="Confidence, 0 to 1",
        label=Label.MODELED,
        notes="DEM source class, distance to Curiosity's localizations (standing in for image "
        "positions) "
        "and flags (DEM not HiRISE; within 1 km of the crop edge, where near-field horizons are "
        f"cut short; within {seam_m:.0f} m of a candidate DEM mosaic seam).",
        resolution_m=res,
        inputs=["source_class.tif", "localized_interp.csv", "seam_distance.tif"],
        settings={k: setting(cfg, "uncertainty", k) for k in cfg["uncertainty"]},
    )
    ctx["uncertainty"] = {
        "confidence": _stats(conf),
        "share_below_0_5": round(float(np.mean(conf < 0.5)), 4),
        "seams": {
            "pairs_with_edges_in_crop": [f["properties"]["pair"] for f in feats],
            "length_m": round(float(lines.length), 1),
            "zone_m": seam_m,
            "zone_share_of_site": round(float(np.mean(zone)), 4),
        },
    }
    log("  confidence written")


def stage_flags(ctx, log):
    """Where the map may be over-cautious: no-go by slope in a seam or low-confidence zone. Reads
    the saved slope, seam-distance and confidence layers, so it can run on its own."""
    cfg, out = ctx["cfg"], ctx["out"]
    conf, t, crs = read_raster(out / "confidence.tif")
    seam_d, _, _ = read_raster(out / "seam_distance.tif")
    zone = np.nan_to_num(seam_d, nan=np.inf) <= float(setting(cfg, "uncertainty", "seam_zone_m"))
    low = float(setting(cfg, "uncertainty", "low_confidence"))
    summary = {"low_confidence": low}
    for who, nogo_key in (("walker", "walker_slope_deg"), ("rover", "rover_slope_deg")):
        slope, _, _ = read_raster(out / f"slope_{who}.tif")
        nogo = float(setting(cfg, "walkability", nogo_key)[1])
        flag = seams.overcautious(slope, nogo, zone, conf, low)
        write_layer(
            out / f"overcautious_{who}.tif",
            flag,
            t,
            crs,
            255,
            product_id=f"Map may be over-cautious here ({who}): no-go by slope in a seam or "
            "low-confidence zone, check by eye",
            label=Label.MODELED,
            notes="1 = no-go by slope (above the PLACEHOLDER limit) within the seam zone or where "
            "confidence is below the PLACEHOLDER low-confidence level. The rover check can only "
            "measure false alarms, and they cluster at seams.",
            resolution_m=float(t.a),
            inputs=[f"slope_{who}.tif", "seam_distance.tif", "confidence.tif"],
            settings={
                "nogo_deg": nogo,
                "seam_zone_m": float(setting(cfg, "uncertainty", "seam_zone_m")),
                "low_confidence": low,
            },
        )
        valid = flag != 255
        nogo_cells = int(((slope > nogo) & valid).sum())
        summary[who] = {
            "flagged_share_of_site": round(float((flag == 1).sum()) / max(1, int(valid.sum())), 4),
            "flagged_share_of_slope_no_go": round(float((flag == 1).sum()) / max(1, nogo_cells), 4),
        }
    ctx["flags"] = summary
    log("  over-cautious flags written")


def _stats(a) -> dict | None:
    v = np.asarray(a, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    return {
        "min": round(float(v.min()), 4),
        "p05": round(float(np.percentile(v, 5)), 4),
        "median": round(float(np.median(v)), 4),
        "p95": round(float(np.percentile(v, 95)), 4),
        "max": round(float(v.max()), 4),
    }


def _shares(cls) -> dict:
    valid = cls != 255
    n = max(1, int(valid.sum()))
    return {
        name: round(float(((cls == k) & valid).sum()) / n, 4)
        for k, name in ((0, "go"), (1, "caution"), (2, "no-go"))
    }
