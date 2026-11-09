# Written with AI assistance (Claude Code). See AI_USE.md.
"""`ariadne derive --site <name>`: build the derived layers for a site from its fetched crops."""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from ariadne import PIPELINE_VERSION
from ariadne.config import load_derive_config, load_site_config, setting
from ariadne.derive import calibrate as calib
from ariadne.derive import horizons as hz
from ariadne.derive import light, terrain
from ariadne.derive import shielding as sh
from ariadne.derive.io import read_raster, write_layer
from ariadne.fetch import places
from ariadne.guardrails import repo_root
from ariadne.labels import Label
from ariadne.models import msl_time

CALIBRATION_SITE = "murray-buttes"
SAMPLE_STEP = 25  # every 25th cell in each direction feeds the report statistics


def calibration_path(root: Path) -> Path:
    return root / "data" / "calibration" / "shielding.json"


def _site_paths(name: str):
    root = repo_root()
    site_dir = root / "data" / "sites" / name
    if not (site_dir / "dem.tif").exists():
        raise FileNotFoundError(f"no crops for {name}: run `make fetch SITE={name}` first")
    out = site_dir / "derived"
    out.mkdir(parents=True, exist_ok=True)
    return root, site_dir, out


def load_or_run_calibration(root: Path, log) -> dict:
    path = calibration_path(root)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    site_dir = root / "data" / "sites" / CALIBRATION_SITE
    if not (site_dir / "regional_dem.tif").exists():
        raise FileNotFoundError(
            "the shielding calibration needs the Murray Buttes crops: run "
            "`make fetch SITE=murray-buttes` first"
        )
    log("  calibrating the shielding exponent at Murray Buttes")
    result = calib.calibrate(
        site_dir, root / "data" / "sources" / "msl-places" / "localized_interp.csv"
    )
    result["pipeline_version"] = PIPELINE_VERSION
    result["computed_utc"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


def compute_horizons(dem, t, regional, regional_t, cfg, n_shield: float, log):
    """All azimuth bands: quantized combined horizons plus S maps and report samples."""
    n_az = int(setting(cfg, "horizons", "azimuths"))
    az = hz.azimuths(n_az)
    obs = float(setting(cfg, "horizons", "observer_height_m"))
    near_max = float(setting(cfg, "horizons", "near_max_m"))
    qmin = float(setting(cfg, "horizons", "quant_min_deg"))
    qstep = float(setting(cfg, "horizons", "quant_step_deg"))
    dist = hz.near_distances(
        near_max,
        t.a,
        float(setting(cfg, "horizons", "near_fine_until_m")),
        float(setting(cfg, "horizons", "near_growth")),
    )
    t0 = time.time()
    ff = hz.far_field(
        dem,
        t,
        regional,
        regional_t,
        az,
        near_max,
        float(setting(cfg, "horizons", "far_max_m")),
        float(setting(cfg, "horizons", "far_grid_m")),
        float(setting(cfg, "horizons", "far_min_step_m")),
        float(setting(cfg, "horizons", "far_growth")),
        obs,
    )
    log(
        f"  far field: {ff.tmax.shape[0]} x {ff.tmax.shape[1]} coarse nodes in "
        f"{time.time() - t0:.0f} s"
    )
    h, w = dem.shape
    codes = np.empty((n_az, h, w), dtype=np.uint8)
    s_acc = np.zeros((h, w))
    s_near_acc = np.zeros((h, w))
    blocked_acc = np.zeros((h, w))
    far_wins = np.zeros((h, w), dtype=np.uint8)
    ys, xs = np.mgrid[SAMPLE_STEP // 2 : h : SAMPLE_STEP, SAMPLE_STEP // 2 : w : SAMPLE_STEP]
    sample_near = np.empty((ys.size, n_az), dtype=np.float32)
    sample_comb = np.empty((ys.size, n_az), dtype=np.float32)
    t0 = time.time()
    for k, a in enumerate(az):
        near = hz.near_field_band(dem, t.a, a, dist, obs)
        far = hz.far_field_band(ff, k, dem, t, obs)
        comb = np.fmax(near, far)
        codes[k] = hz.quantize(comb, qmin, qstep)
        pos = np.sin(np.radians(np.clip(comb.astype(np.float64), 0.0, 90.0)))
        s_acc += 1.0 - pos ** (n_shield + 1.0)
        blocked_acc += pos
        posn = np.sin(np.radians(np.clip(near.astype(np.float64), 0.0, 90.0)))
        s_near_acc += 1.0 - posn ** (n_shield + 1.0)
        far_wins += (far > near).astype(np.uint8)
        sample_near[:, k] = near[ys.ravel(), xs.ravel()]
        sample_comb[:, k] = comb[ys.ravel(), xs.ravel()]
        if k % 12 == 11:
            log(f"  horizons: {k + 1}/{n_az} azimuths, {time.time() - t0:.0f} s")
    nanmask = np.isnan(dem)
    s_map = (s_acc / n_az).astype(np.float32)
    s_map[nanmask] = np.nan
    s_near = (s_near_acc / n_az).astype(np.float32)
    s_near[nanmask] = np.nan
    blocked = (blocked_acc / n_az).astype(np.float32)
    blocked[nanmask] = np.nan
    return {
        "codes": codes,
        "s": s_map,
        "s_near": s_near,
        "blocked": blocked,
        "far_share": (far_wins / n_az).astype(np.float32),
        "samples": {
            "rows": ys.ravel(),
            "cols": xs.ravel(),
            "near": sample_near,
            "comb": sample_comb,
        },
        "tie_offset_m": ff.tie_offset_m,
        "qmin": qmin,
        "qstep": qstep,
        "az": az,
    }


def mars_year_dates(after: datetime) -> list[tuple[str, datetime]]:
    """UTC days nearest to Ls 0, 90, 180 and 270 of the first Mars year starting after `after`."""
    day = after
    prev = msl_time.solar_longitude(day)
    found = []
    targets = [0.0, 90.0, 180.0, 270.0]
    while len(found) < 4 and (day - after).days < 800:
        day += timedelta(days=1)
        ls = msl_time.solar_longitude(day)
        tgt = targets[len(found)]
        crossed = (prev < tgt <= ls) if tgt > 0 else (prev > 300 and ls < 60)
        if crossed and (tgt == 0 or found):
            found.append((f"Ls {tgt:g}", day.replace(hour=0, minute=0, second=0)))
        prev = ls
    return found


def _clock(track: light.SunTrack, seconds: float | None) -> float | None:
    if seconds is None or (isinstance(seconds, float) and math.isnan(seconds)):
        return None
    k = seconds / ((track.times[1] - track.times[0]).total_seconds())
    return float(
        np.interp(k, np.arange(track.ltst.size), np.unwrap(track.ltst * 15.0, period=360.0) / 15.0)
        % 24.0
    )


def sun_shift_report(samples, named, centre_lonlat, dates, step_s, log) -> dict:
    """Sunrise and sunset with no terrain, near-field only and near + far, per date."""
    lon, lat = centre_lonlat
    out = []
    flat = np.zeros(samples["near"].shape[1])
    for label, day in dates:
        track = light.local_noon_track(day, lon, lat, step_s)
        rise_f, set_f = light.sunrise_sunset_point(flat, track)
        shifts_rise, shifts_set, total_rise, total_set, never = [], [], [], [], 0
        for i in range(samples["near"].shape[0]):
            rn, sn = light.sunrise_sunset_point(samples["near"][i].astype(np.float64), track)
            rc, sc = light.sunrise_sunset_point(samples["comb"][i].astype(np.float64), track)
            if rn is None or rc is None:
                never += 1
                continue
            shifts_rise.append((rc - rn) / 60.0)
            shifts_set.append((sn - sc) / 60.0)
            total_rise.append((rc - rise_f) / 60.0)
            total_set.append((set_f - sc) / 60.0)
        pts = []
        for p in named:
            rn, sn = light.sunrise_sunset_point(np.asarray(p["near"], dtype=np.float64), track)
            rc, sc = light.sunrise_sunset_point(np.asarray(p["comb"], dtype=np.float64), track)
            pts.append(
                {
                    "name": p["name"],
                    "sunrise_ltst_flat": _clock(track, rise_f),
                    "sunrise_ltst_near": _clock(track, rn),
                    "sunrise_ltst": _clock(track, rc),
                    "sunset_ltst_flat": _clock(track, set_f),
                    "sunset_ltst_near": _clock(track, sn),
                    "sunset_ltst": _clock(track, sc),
                    "far_delays_sunrise_min": None
                    if rn is None or rc is None
                    else round((rc - rn) / 60, 1),
                    "far_advances_sunset_min": None
                    if sn is None or sc is None
                    else round((sn - sc) / 60, 1),
                }
            )

        def stats(v):
            v = np.asarray(v)
            if v.size == 0:
                return None
            return {
                "median": round(float(np.median(v)), 1),
                "p90": round(float(np.percentile(v, 90)), 1),
                "max": round(float(v.max()), 1),
                "share_over_1_min": round(float(np.mean(v > 1.0)), 3),
            }

        out.append(
            {
                "date": label,
                "utc_day": day.date().isoformat(),
                "ls": round(msl_time.solar_longitude(day), 1),
                "sunrise_ltst_flat": _clock(track, rise_f),
                "sunset_ltst_flat": _clock(track, set_f),
                "far_delays_sunrise_min": stats(shifts_rise),
                "far_advances_sunset_min": stats(shifts_set),
                "terrain_delays_sunrise_min": stats(total_rise),
                "terrain_advances_sunset_min": stats(total_set),
                "cells_never_lit": never,
                "cells": int(samples["near"].shape[0]),
                "points": pts,
            }
        )
        log(
            f"  {label} ({day.date()}): far field delays sunrise by a median "
            f"{out[-1]['far_delays_sunrise_min']['median'] if shifts_rise else 'n/a'} min"
        )
    return {"dates": out, "sample_step_px": SAMPLE_STEP}


def _load_cached_horizons(out: Path, n_shield: float, cfg) -> dict | None:
    """Reuse the horizon pass if its outputs exist for the same n and horizon settings."""
    cache = out / "horizon_cache.npz"
    needed = [out / "horizons.tif", out / "shielding.tif", out / "sky_blocked.tif", cache]
    if not all(p.exists() for p in needed):
        return None
    z = np.load(cache, allow_pickle=False)
    settings = json.dumps({k: setting(cfg, "horizons", k) for k in cfg["horizons"]}, sort_keys=True)
    if (
        str(z["settings"]) != settings
        or abs(float(z["n"]) - n_shield) > 1e-9
        or str(z["version"]) != PIPELINE_VERSION
    ):
        return None
    codes, _, _ = read_raster(out / "horizons.tif", as_float=False)
    s, _, _ = read_raster(out / "shielding.tif")
    blocked, _, _ = read_raster(out / "sky_blocked.tif")
    return {
        "codes": codes,
        "s": s.astype(np.float32),
        "s_near": z["s_near"],
        "blocked": blocked.astype(np.float32),
        "far_share": z["far_share"],
        "samples": {"rows": z["rows"], "cols": z["cols"], "near": z["near"], "comb": z["comb"]},
        "tie_offset_m": float(z["tie"]),
        "qmin": float(setting(cfg, "horizons", "quant_min_deg")),
        "qstep": float(setting(cfg, "horizons", "quant_step_deg")),
        "az": hz.azimuths(int(setting(cfg, "horizons", "azimuths"))),
    }


def _save_horizon_cache(out: Path, hres: dict, n_shield: float, cfg) -> None:
    s = hres["samples"]
    np.savez_compressed(
        out / "horizon_cache.npz",
        s_near=hres["s_near"],
        far_share=hres["far_share"],
        rows=s["rows"],
        cols=s["cols"],
        near=s["near"],
        comb=s["comb"],
        tie=hres["tie_offset_m"],
        n=n_shield,
        version=PIPELINE_VERSION,
        settings=json.dumps(
            {k: setting(cfg, "horizons", k) for k in cfg["horizons"]}, sort_keys=True
        ),
    )


def _named_points(ctx) -> list[dict]:
    """Points reported by name: drill sites at the boxwork, the parking spot at Murray Buttes."""
    pts = [
        {"name": d["name"], "x": d["easting"], "y": d["northing"]} for d in ctx.get("drills", [])
    ]
    if ctx["site"] == CALIBRATION_SITE:
        p = ctx["calibration"]["parking"]
        pts.append(
            {"name": "Parking spot (site 57, drive 2798)", "x": p["easting"], "y": p["northing"]}
        )
    if not pts:
        return []
    regional, regional_t, _ = read_raster(ctx["site_dir"] / "regional_dem.tif")
    xs = np.array([p["x"] for p in pts])
    ys = np.array([p["y"] for p in pts])
    near, _, comb = calib.point_horizons(
        ctx["dem"],
        ctx["t"],
        regional,
        regional_t,
        ctx["tie_offset_m"],
        xs,
        ys,
        ctx["cfg"],
        float(setting(ctx["cfg"], "horizons", "observer_height_m")),
    )
    for i, p in enumerate(pts):
        p["near"] = near[i].tolist()
        p["comb"] = comb[i].tolist()
        p["s"] = round(float(sh.open_sky_fraction(comb[i], ctx["n"])), 4)
        p["blocked"] = round(float(sh.blocked_fraction(comb[i])), 4)
    return pts


def derive_site(name: str, force: bool = False, log: Callable[[str], None] = print) -> dict:
    from ariadne.derive import stages
    from ariadne.fetch import context

    root, site_dir, out = _site_paths(name)
    cfg = load_derive_config()
    site_cfg = load_site_config(name)
    import yaml

    site_raw = yaml.safe_load(
        (root / "config" / "sites" / f"{name}.yaml").read_text(encoding="utf-8")
    )
    t_start = time.time()
    log(f"Deriving layers for {name}")

    cal = load_or_run_calibration(root, log)
    n_shield = cal["result"]["n"]
    if n_shield is None:
        raise RuntimeError(
            "the shielding calibration found no n; see data/calibration/shielding.json"
        )

    dem, t, crs = read_raster(site_dir / "dem.tif")
    res = float(t.a)
    regional, regional_t, _ = read_raster(site_dir / "regional_dem.tif")
    common = dict(resolution_m=res, inputs=["dem.tif"])

    # 1. Terrain basics
    slope, aspect = terrain.slope_aspect(dem, res)
    rough = terrain.roughness(dem, res, float(setting(cfg, "terrain", "roughness_window_m")))
    write_layer(
        out / "slope.tif",
        slope,
        t,
        crs,
        None,
        product_id="Slope (Horn), degrees",
        label=Label.DERIVED,
        notes="Horn (1981) slope of the 1 m DEM.",
        **common,
    )
    write_layer(
        out / "aspect.tif",
        aspect,
        t,
        crs,
        None,
        product_id="Aspect, degrees clockwise from north (downhill)",
        label=Label.DERIVED,
        notes="NaN on flat ground.",
        **common,
    )
    write_layer(
        out / "roughness.tif",
        rough,
        t,
        crs,
        None,
        product_id="Roughness, m",
        label=Label.DERIVED,
        notes="Standard deviation about the best-fit plane in a 5 m window.",
        **common,
    )
    for r_m in setting(cfg, "terrain", "tpi_radii_m"):
        write_layer(
            out / f"tpi{int(r_m)}.tif",
            terrain.tpi(dem, res, float(r_m)),
            t,
            crs,
            None,
            product_id=f"Topographic position index at {r_m} m, m",
            label=Label.DERIVED,
            notes="Elevation minus the mean within the disc.",
            **common,
        )
    log(f"  terrain basics written ({time.time() - t_start:.0f} s)")

    # 2. Horizons, with the shielding index accumulated on the way (cached between runs)
    hres = None if force else _load_cached_horizons(out, n_shield, cfg)
    if hres is not None:
        log("  horizons: reusing the cached pass (same n and settings)")
    else:
        hres = compute_horizons(dem, t, regional, regional_t, cfg, n_shield, log)
        qmin, qstep = hres["qmin"], hres["qstep"]
        hz_settings = {k: setting(cfg, "horizons", k) for k in cfg["horizons"]}
        write_layer(
            out / "horizons.tif",
            hres["codes"],
            t,
            crs,
            hz.NODATA_CODE,
            product_id="Horizon angles, 72 azimuths (band 1 = north, clockwise every 5 degrees)",
            label=Label.DERIVED,
            notes=f"uint8 code: angle = code x {qstep} + {qmin} degrees, 255 = no data. Near field "
            "on "
            "the 1 m DEM to 2 km, far field on MOLA to 100 km, curvature included.",
            resolution_m=res,
            inputs=["dem.tif", "regional_dem.tif"],
            settings=hz_settings,
        )
        write_layer(
            out / "shielding.tif",
            hres["s"],
            t,
            crs,
            None,
            product_id="Shielding index S (open-sky fraction weighted by cos^n, n = "
            f"{n_shield:.3f})",
            label=Label.MODELED,
            notes="Calibrated on one RAD measurement (Murray Buttes, Ehresmann et al. 2021).",
            resolution_m=res,
            inputs=["horizons"],
            settings={"n": n_shield},
        )
        write_layer(
            out / "sky_blocked.tif",
            hres["blocked"],
            t,
            crs,
            None,
            product_id="Blocked share of the sky (solid angle below the horizon)",
            label=Label.DERIVED,
            notes="The n = 0 case of S: mean of sin(h) over azimuths.",
            resolution_m=res,
            inputs=["horizons"],
        )
        _save_horizon_cache(out, hres, n_shield, cfg)
    log(f"  horizons and shielding ready ({time.time() - t_start:.0f} s)")

    rover = places.load_rover_positions(
        root / "data" / "sources" / "msl-places" / "localized_interp.csv"
    )
    drills = (
        context.drill_site_positions(site_cfg.drill_sites, rover) if site_cfg.drill_sites else []
    )
    ctx = {
        "site": name,
        "root": root,
        "site_dir": site_dir,
        "out": out,
        "cfg": cfg,
        "site_cfg": site_cfg,
        "site_cfg_raw": site_raw,
        "dem": dem,
        "t": t,
        "crs": crs,
        "res": res,
        "slope": slope,
        "aspect": aspect,
        "rough": rough,
        "codes": hres["codes"],
        "qmin": hres["qmin"],
        "qstep": hres["qstep"],
        "s": hres["s"],
        "n": n_shield,
        "calibration": cal,
        "drills": drills,
        "tie_offset_m": hres["tie_offset_m"],
        "centre_lonlat": centre_lonlat(t, dem.shape),
    }

    # 3. Light, then the sunrise and sunset report with and without the far field
    stages.stage_light(ctx, log)
    named = _named_points(ctx)
    ref_day = msl_time.sol_start_utc(int(site_raw["reference_sol"]["value"]))
    dates = mars_year_dates(ref_day - timedelta(days=690))
    dates.append(
        (
            f"sol {site_raw['reference_sol']['value']} (reference)",
            ref_day.replace(hour=0, minute=0, second=0, microsecond=0),
        )
    )
    sun = sun_shift_report(
        hres["samples"],
        named,
        ctx["centre_lonlat"],
        dates,
        float(setting(cfg, "light", "time_step_s")),
        log,
    )

    # 4 to 8. Walkability, ridges, shelters and line of sight, science, uncertainty
    stages.stage_walkability(ctx, log)
    stages.stage_ridges(ctx, log)
    stages.stage_shelters_los(ctx, log)
    stages.stage_science(ctx, log)
    stages.stage_uncertainty(ctx, log)

    summary = {
        "site": name,
        "pipeline_version": PIPELINE_VERSION,
        "computed_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "grid": {"width": int(dem.shape[1]), "height": int(dem.shape[0]), "resolution_m": res},
        "horizons": {
            "n": n_shield,
            "mola_tie_offset_m": round(hres["tie_offset_m"], 2),
            "far_field_sets_horizon_share": round(float(np.nanmean(hres["far_share"])), 3),
            "s": _stats(hres["s"]),
            "s_near_only": _stats(hres["s_near"]),
            "sky_blocked": _stats(hres["blocked"]),
        },
        "named_points": [{k: v for k, v in p.items() if k not in ("near", "comb")} for p in named],
        "sun": sun,
        "light": ctx.get("light"),
        "walkability": ctx.get("walkability"),
        "ridges": ctx.get("ridges"),
        "shelters": ctx.get("shelters"),
        "line_of_sight": ctx.get("line_of_sight"),
        "science": ctx.get("science"),
        "uncertainty": ctx.get("uncertainty"),
        "drill_sites": drills,
        "seconds": round(time.time() - t_start),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    from ariadne.derive.report import derived_markdown

    report = root / "docs" / "derived" / f"{name}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        derived_markdown(summary, cal if name == CALIBRATION_SITE else None), encoding="utf-8"
    )
    log(f"  report: {report.relative_to(root)} ({summary['seconds']} s in all)")
    return summary


def _stats(a) -> dict:
    v = np.asarray(a, dtype=np.float64)
    v = v[np.isfinite(v)]
    return {
        "min": round(float(v.min()), 4),
        "p05": round(float(np.percentile(v, 5)), 4),
        "median": round(float(np.median(v)), 4),
        "p95": round(float(np.percentile(v, 95)), 4),
        "max": round(float(v.max()), 4),
    }


def centre_lonlat(t, shape) -> tuple[float, float]:
    h, w = shape
    x = t.c + t.a * w / 2
    y = t.f + t.e * h / 2
    return math.degrees(x / places.MARS_RADIUS_M), math.degrees(y / places.MARS_RADIUS_M)
