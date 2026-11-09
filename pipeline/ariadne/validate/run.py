# Written with AI assistance (Claude Code). See AI_USE.md.
"""Write validation.json (repo root) from the derived outputs and the time models.

Each check records its reference, the team's target (set before the run), the result and a
status: "pass", "fail", "reported" (a comparison with no gate) or "not run" (with the reason and
the phase that adds it). Targets are team targets, not published standards.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import rasterio

from ariadne import PIPELINE_VERSION
from ariadne.guardrails import repo_root
from ariadne.models import mars24, msl_time

# GISS Mars24 worked examples (https://www.giss.nasa.gov/tools/mars24/help/algorithm.html),
# the same values as pipeline/tests/test_mars24.py.
MARS24_EXAMPLES = [
    {
        "name": "2000-01-06 00:00 UTC at 0 N, 0 W",
        "utc": datetime(2000, 1, 6, tzinfo=UTC),
        "lon_east": 0.0,
        "lat": 0.0,
        "expect": {
            "ls": 277.18758,
            "eot_deg": -5.18774,
            "mst_hours": 23.99425,
            "ltst_hours": 23.64840,
            "subsolar_lon_west": 174.72600,
            "declination": -25.22825,
            "zenith": 154.26182,
            "azimuth": 191.03905,
        },
    },
    {
        "name": "Spirit landing, 2004-01-03 13:46:31 UTC at 14.640 S, 184.702 W",
        "utc": datetime(2004, 1, 3, 13, 46, 31, tzinfo=UTC),
        "lon_east": 360.0 - 184.702,
        "lat": -14.640,
        "expect": {
            "ls": 327.32416,
            "eot_deg": -12.77553,
            "mst_hours": 13.16537,
            "ltst_hours": 0.00025,
            "subsolar_lon_west": 4.70500,
            "declination": -13.42065,
            "zenith": 151.93895,
            "azimuth": 179.99383,
        },
    },
]
CAPTION_SOLS = [
    (4190, date(2024, 5, 20)),
    (4220, date(2024, 6, 19)),
    (4636, date(2025, 8, 21)),
    (4650, date(2025, 9, 5)),
    (4677, date(2025, 10, 2)),
]


def mars24_check() -> dict:
    worst_deg, worst_h, rows = 0.0, 0.0, []
    for ex in MARS24_EXAMPLES:
        r = mars24.solar_state(ex["utc"], ex["lon_east"], ex["lat"])
        for k, want in ex["expect"].items():
            got = getattr(r, k)
            diff = abs(got - want)
            if k.endswith("hours"):
                worst_h = max(worst_h, diff)
            else:
                worst_deg = max(worst_deg, diff)
            rows.append(
                {"example": ex["name"], "value": k, "printed": want, "computed": round(got, 6)}
            )
    passed = worst_deg <= 1e-3 and worst_h <= 1e-4
    return {
        "id": "mars24",
        "title": "Mars24 sun position and solar time",
        "reference": "GISS Mars24 algorithm page, two worked examples",
        "target": "Every printed value matched to 0.001 degrees (0.0001 h) or better, most to all "
        "five printed decimals",
        "result": {
            "largest_difference_deg": round(worst_deg, 6),
            "largest_difference_hours": round(worst_h, 6),
            "values": rows,
        },
        "status": "pass" if passed else "fail",
        "label": "MODELED",
        "note": "In the Spirit example the printed declination and LTST differ from the printed "
        "formulas by "
        "more than rounding of the printed inputs explains; the page does not say why. All gaps "
        "are under one "
        "arcsecond.",
    }


def sol_check() -> dict:
    rows, ok = [], True
    for sol, day in CAPTION_SOLS:
        start = msl_time.sol_start_utc(sol)
        diff = abs((start.date() - day).days)
        ok &= diff <= 1
        rows.append(
            {
                "sol": sol,
                "caption_date": day.isoformat(),
                "sol_start_utc": start.isoformat(),
                "days_off": diff,
            }
        )
    return {
        "id": "sols",
        "title": "MSL sol to date",
        "reference": "Dates in NASA image captions (PROMPT.md section 3)",
        "target": "Within one day",
        "result": {"fixtures": rows},
        "status": "pass" if ok else "fail",
        "label": "MODELED",
    }


ROVER_TARGET = 0.95
FIRST_RUN = Path("docs") / "validation" / "rover-walkability-first-run.json"


def _sample(path: Path, rows, cols):
    with rasterio.open(path) as d:
        return d.read(1)[rows, cols]


def _rover_path_points(root: Path, site: str):
    """Curiosity's localizations used for a site's rover check, and a description of them."""
    from ariadne.fetch import places

    site_dir = root / "data" / "sites" / site
    rover = places.load_rover_positions(
        root / "data" / "sources" / "msl-places" / "localized_interp.csv"
    )
    if site == "boxwork":
        box = json.loads((site_dir / "fetch_summary.json").read_text(encoding="utf-8"))["box"]
        pts = places.in_sols(rover, box["first_sol"], box["last_sol"])
        return pts, f"PLACES localizations, sols {box['first_sol']} to {box['last_sol']}"
    with rasterio.open(site_dir / "dem.tif") as d:
        b = d.bounds
    inside = rover.easting.between(b.left, b.right) & rover.northing.between(b.bottom, b.top)
    pts = rover[inside]
    return pts, (
        f"PLACES localizations inside the {site} box, sols {int(pts.sol.min())} to "
        f"{int(pts.sol.max())}"
    )


def _class_result(cls_vals, seam_zone) -> dict:
    from ariadne.derive import seams

    share = {
        name: round(float(np.mean(cls_vals == k)), 4)
        for k, name in ((0, "go"), (1, "caution"), (2, "no-go"))
    }
    nogo = cls_vals == 2
    out = {
        "points": int(cls_vals.size),
        "share": share,
        "go_or_caution": round(share["go"] + share["caution"], 4),
        "no_go_count": int(nogo.sum()),
    }
    if seam_zone is not None:
        out["seams"] = seams.zone_statistics(seam_zone, nogo)
    return out


def _site_rover_results(root: Path, site: str) -> dict | None:
    """Rover classes on Curiosity's path at one site: the footprint method (the result), the
    Phase 2 first-run method and the coarse-resolution case, with the tilt and seam checks."""
    d = root / "data" / "sites" / site / "derived"
    if not (d / "walk_class_rover.tif").exists() or not (d / "slope_rover.tif").exists():
        return None
    pts, ref = _rover_path_points(root, site)
    with rasterio.open(d / "walk_class_rover.tif") as src:
        t, shape = src.transform, src.shape
    rows = np.floor((pts.northing.to_numpy() - t.f) / t.e).astype(int)
    cols = np.floor((pts.easting.to_numpy() - t.c) / t.a).astype(int)
    ok = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
    rows, cols, pts = rows[ok], cols[ok], pts[ok]
    zone = None
    if (d / "seam_distance.tif").exists():
        from ariadne.config import load_derive_config, setting

        zone_m = float(setting(load_derive_config(), "uncertainty", "seam_zone_m"))
        zone = _sample(d / "seam_distance.tif", rows, cols) <= zone_m
    new = _sample(d / "walk_class_rover.tif", rows, cols)
    result = _class_result(new, zone)
    nogo = pts[new == 2]
    result["no_go_points"] = [
        {
            "sol": int(r.sol),
            "site": int(r.site),
            "drive": int(r.drive),
            "easting": round(float(r.easting), 2),
            "northing": round(float(r.northing), 2),
        }
        for r in nogo.itertuples()
    ][:200]
    # Curiosity's own tilt from PLACES roll and pitch (MEASURED) against the slopes under it.
    import pandas as pd

    raw = pd.read_csv(
        root / "data" / "sources" / "msl-places" / "localized_interp.csv",
        usecols=["frame", "site", "drive", "roll", "pitch"],
    )
    raw = raw[raw.frame == "ROVER"].drop_duplicates(["site", "drive"])
    keyed = pts[["site", "drive"]].merge(raw, on=["site", "drive"], how="left")
    tilt = np.degrees(np.arccos(np.cos(np.radians(keyed.roll)) * np.cos(np.radians(keyed.pitch))))
    tilt = tilt.to_numpy()
    slope_fp = _sample(d / "slope_rover.tif", rows, cols)
    slope_horn = _sample(d / "slope.tif", rows, cols)

    def pct(a):
        a = a[np.isfinite(a)]
        return [round(float(x), 1) for x in np.percentile(a, [50, 90, 99])]

    def over20(a):
        a = a[np.isfinite(a)]
        return round(float(np.mean(a > 20)), 4)

    both = np.isfinite(tilt) & np.isfinite(slope_fp) & np.isfinite(slope_horn)
    result["tilt_check"] = {
        "rover_tilt_deg_p50_p90_p99": pct(tilt),
        "rover_tilt_share_over_20_deg": over20(tilt),
        "footprint_slope_deg_p50_p90_p99": pct(slope_fp),
        "footprint_slope_share_over_20_deg": over20(slope_fp),
        "horn_1m_slope_deg_p50_p90_p99": pct(slope_horn),
        "horn_1m_slope_share_over_20_deg": over20(slope_horn),
        "correlation_tilt_footprint": round(
            float(np.corrcoef(tilt[both], slope_fp[both])[0, 1]), 3
        ),
        "correlation_tilt_horn_1m": round(
            float(np.corrcoef(tilt[both], slope_horn[both])[0, 1]), 3
        ),
        "note": "Rover tilt is arccos(cos roll x cos pitch) from PLACES (MEASURED), matched by "
        "site and drive. It is a check, not a target: the rover's suspension and its choice of "
        "route both shape it.",
    }
    horn = _class_result(_sample(d / "walk_class_rover_horn1m.tif", rows, cols), zone)
    coarse = _class_result(_sample(d / "walk_class_rover_coarse.tif", rows, cols), None)
    return {"reference": ref, "result": result, "horn": horn, "coarse": coarse}


def rover_walkability_check(root: Path) -> list[dict]:
    """The boxwork rover check (re-run with footprint slope, first result kept) and the Murray
    Buttes held-out check."""
    from ariadne.config import load_derive_config
    from ariadne.derive.walkability import slope_scales

    scales = {k: round(v, 3) for k, v in slope_scales(load_derive_config()).items()}
    method = (
        f"Rover slope at its footprint: least-squares plane over a {scales['rover_m']} m disc "
        f"(Curiosity's length, no finer than the DEM's effective resolution of "
        f"{scales['r_eff_m']} m). Fixed on 2026-11-09 before the re-run (docs/PROGRESS.md)."
    )
    target = "At least 95% classed go or caution; every no-go cell listed as a possible false alarm"
    note = (
        "Rover thresholds are PLACEHOLDER (config/derive.yaml). This check can only measure false "
        "alarms (no-go where Curiosity actually drove), the cautious direction; it cannot measure "
        "missed hazards. A no-go point on the path is a likely false alarm, or ground the rover "
        "crossed with care."
    )
    diagnosis = (
        "The boxwork misses its target while Murray Buttes, held out, passes. The boxwork ridges "
        "are 1 to 2 m high and a few metres wide, at the DEM's effective resolution (about 2.5 m) "
        "and the rover's footprint, so slope there mixes real relief with what the DEM cannot "
        "resolve and with its errors; candidate DEM seams add false alarms (no-go rate 62% within "
        "30 m of a seam against 18% elsewhere). No more re-runs (team decision, 2026-11-09). The "
        "planner stays conservative, and the surfaces mark slope no-go cells in seam or "
        "low-confidence zones as 'map may be over-cautious here, check by eye'."
    )
    out = []
    box = _site_rover_results(root, "boxwork")
    frozen_path = root / FIRST_RUN
    frozen = json.loads(frozen_path.read_text(encoding="utf-8")) if frozen_path.exists() else None
    if box is None:
        out.append(
            _not_run("rover-walkability", "Rover walkability", "derive the boxwork site first", 2)
        )
    else:
        r = box["result"]
        entry = {
            "id": "rover-walkability",
            "title": "Rover walkability on Curiosity's boxwork path",
            "site": "boxwork",
            "reference": f"{box['reference']} ({r['points']} points)",
            "target": target,
            "method": method,
            "slope_scales_m": scales,
            "result": r,
            "status": "pass" if r["go_or_caution"] >= ROVER_TARGET else "fail",
            "first_run_reproduced": box["horn"],
            "sensitivity": {
                "coarse_resolution": dict(
                    box["coarse"],
                    disc_m=scales["rover_coarse_m"],
                    note="DEM effective resolution at the coarse end (20 image pixels); not "
                    "the result.",
                )
            },
            "label": "MODELED",
            "note": note,
            "diagnosis": diagnosis,
        }
        if frozen is not None:
            first = frozen["check"]
            entry["first_run"] = {
                "status": first["status"],
                "method": frozen["method"],
                "frozen_from": frozen["frozen_from"],
                "result": first["result"],
            }
        out.append(entry)
    mb = _site_rover_results(root, "murray-buttes")
    if mb is None:
        out.append(
            _not_run(
                "rover-walkability-held-out",
                "Rover walkability on Curiosity's Murray Buttes traverse (held out)",
                "derive the murray-buttes site first",
                2,
            )
        )
    else:
        r = mb["result"]
        out.append(
            {
                "id": "rover-walkability-held-out",
                "title": "Rover walkability on Curiosity's Murray Buttes traverse (held out)",
                "site": "murray-buttes",
                "reference": f"{mb['reference']} ({r['points']} points)",
                "target": target,
                "method": method + " This site played no part in choosing the method.",
                "result": r,
                "status": "pass" if r["go_or_caution"] >= ROVER_TARGET else "fail",
                "comparison_horn_1m": mb["horn"],
                "sensitivity": {
                    "coarse_resolution": dict(mb["coarse"], disc_m=scales["rover_coarse_m"])
                },
                "label": "MODELED",
                "note": note,
                "diagnosis": diagnosis,
            }
        )
    return out


def ridge_spot_check(root: Path) -> dict | None:
    """Ridge class and TPI at the drill holes whose setting the blog states (not a validation)."""
    d = root / "data" / "sites" / "boxwork"
    if not (d / "derived" / "ridges.tif").exists() or not (d / "drill_sites.geojson").exists():
        return None
    drills = json.loads((d / "drill_sites.geojson").read_text(encoding="utf-8"))["features"]
    with (
        rasterio.open(d / "derived" / "ridges.tif") as r,
        rasterio.open(d / "derived" / "tpi10.tif") as tp,
    ):
        cls, tpi, t = r.read(1), tp.read(1), r.transform
    out = []
    names = {0: "other", 1: "ridge", 2: "hollow"}
    for f in drills:
        x, y = f["geometry"]["coordinates"]
        row, col = int((y - t.f) / t.e), int((x - t.c) / t.a)
        out.append(
            {
                "hole": f["properties"]["name"],
                "setting_from_blog": f["properties"]["setting"],
                "class": names[int(cls[row, col])],
                "tpi10_m": round(float(tpi[row, col]), 2),
            }
        )
    return {
        "note": "Curiosity's position while drilling is within the arm's reach of each hole, so "
        "this spot-checks two settings (ridgetop and hollow); it does not measure precision or "
        "recall.",
        "holes": out,
    }


def _not_run(cid: str, title: str, reason: str, phase: int) -> dict:
    return {"id": cid, "title": title, "status": "not run", "reason": reason, "phase": phase}


# Minetti et al. 2002, Table 2 (p. 1042): gradient, mean minimum Cw, SD (J/kg/m).
MINETTI_TABLE_2 = [
    (-0.45, 3.46, 0.95), (-0.40, 3.23, 0.59), (-0.35, 2.65, 0.68), (-0.30, 2.18, 0.67),
    (-0.20, 1.30, 0.48), (-0.10, 0.81, 0.37), (0.00, 1.64, 0.50), (0.10, 4.68, 0.34),
    (0.20, 8.07, 0.57), (0.30, 11.29, 1.14), (0.35, 12.72, 0.76), (0.40, 14.75, 0.61),
    (0.45, 17.33, 1.11),
]  # fmt: skip


def walker_model_check() -> dict:
    from ariadne.models import metabolic as mb

    suit = mb.load_suit()
    rows = []
    for i, mean, sd in MINETTI_TABLE_2:
        model = float(mb.cost_of_transport(i))
        rows.append(
            {"gradient": i, "measured": mean, "sd": sd, "model": round(model, 3),
             "within_one_sd": abs(model - mean) <= sd}
        )  # fmt: skip
    return {
        "id": "walker-model",
        "title": "Walker model",
        "reference": "NASA/TP-2010-216125 (Norcross et al. 2010) and Minetti et al. 2002, "
        "J Appl Physiol 93:1039, Table 2",
        "target": "Matches transcribed values; extrapolation flagged",
        "status": "reported",
        "result": {
            "nasa_tp_2010_216125": "Cannot be transcribed: the report gives the form of its "
            "predictive equation (eq. 1, p. 70) but not its coefficients (p. 79). Its tested "
            "ranges set the EXTRAPOLATED flag.",
            "stand_in": "Minetti et al. 2002 cost of walking against gradient (Earth, unsuited), "
            "with PLACEHOLDER suit, gravity and pace settings (config/suits.json)",
            "minetti_within_one_sd": f"{sum(r['within_one_sd'] for r in rows)} of {len(rows)}",
            "minetti_rows": rows,
            "mars_walks_flagged_extrapolated": bool(mb.extrapolation_flags(0.1, 0.8, suit)),
            "flags_at_mars_gravity": mb.extrapolation_flags(0.1, 0.8, suit),
        },
        "label": "MODELED",
        "note": "The level value is the one mismatch (model 2.5 against 1.64 +/- 0.50 J/kg/m); "
        "the fitted polynomial also used Margaria's data.",
    }


def thread_check(root: Path) -> dict:
    path = root / "data" / "sites" / "boxwork" / "plan" / "summary.json"
    if not path.exists():
        return _not_run("thread", "Thread in 1,000 random scenarios", "run `make plan` first", 3)
    s = json.loads(path.read_text(encoding="utf-8"))
    th = s["thread"]
    return {
        "id": "thread",
        "title": "Thread in random scenarios on the boxwork",
        "reference": "C_left(x) - C_home(x) >= C_reserve at every sample (at most 5 m apart) of "
        f"{th['scenarios']} random plans (seed {th['seed']})",
        "target": "Holds in all of at least 1,000 random scenarios",
        "status": "pass" if th["held"] == th["scenarios"] and th["scenarios"] >= 1000 else "fail",
        "result": th,
        "plans": s["plans"],
        "label": "MODELED",
        "note": "Plans use PLACEHOLDER consumables, reserve and suit settings; the check measures "
        "the margin along each plan's actual legs.",
    }


def station_solver_check(root: Path) -> dict:
    path = root / "docs" / "validation" / "station-solver.json"
    if not path.exists():
        return _not_run(
            "station-solver",
            "Browser station solver against OR-Tools",
            "run the web benchmark (`make plan` writes docs/validation/station-solver.json)",
            3,
        )
    b = json.loads(path.read_text(encoding="utf-8"))
    return {
        "id": "station-solver",
        "title": "Browser station solver against OR-Tools",
        "reference": f"Time-limited OR-Tools reference plans on {b['scenarios']} random boxwork "
        "scenarios",
        "target": "At least 95% of the reference science value on average; worst case reported",
        "status": "pass" if b["mean_ratio"] >= b["target"] else "fail",
        "result": {k: b[k] for k in ("scenarios", "mean_ratio", "min_ratio", "target")},
        "label": "MODELED",
        "note": "OR-Tools runs a guided local search with a time limit per scenario, so it is a "
        "time-limited reference, not a proven optimum; the browser solver can and sometimes does "
        f"find more value. Mean ratio {b['mean_ratio']:.3f}, worst case {b['min_ratio']:.3f}; "
        "per-scenario rows in docs/validation/station-solver.json.",
    }


def build_validation(root: Path | None = None) -> dict:
    root = root or repo_root()
    cal_path = root / "data" / "calibration" / "shielding.json"
    checks = []
    if cal_path.exists():
        cal = json.loads(cal_path.read_text(encoding="utf-8"))
        cal["status"] = "pass" if cal["result"]["passed"] else "fail"
        cal["value_label"] = "MODELED"  # n and S are model values; the RAD figures are MEASURED
        cal["sky_check"]["status"] = "reported"
        cal["target"] = (
            "Some n in 0 to 10 reproduces S(parking) / S(baseline) = 0.962 (3.8%), within the "
            "paper's 0.4%; blocked sky and the neutral drop reported separately"
        )
        cal.pop("horizon_parking_near_deg", None)
        checks.append(cal)
    else:
        checks.append(
            _not_run(
                "shielding-murray-buttes",
                "Shielding index calibrated at Murray Buttes",
                "run `make derive SITE=murray-buttes` first",
                2,
            )
        )
    checks.extend(rover_walkability_check(root))
    checks.append(mars24_check())
    checks.append(sol_check())
    ridge = _not_run(
        "ridge-map",
        "Ridge map against a hand-labeled sample",
        "no hand-labeled sample of ridges at known image positions yet; thresholds are PLACEHOLDER",
        2,
    )
    tuned = root / "docs" / "validation" / "ridge-map.json"
    if tuned.exists():
        rm = json.loads(tuned.read_text(encoding="utf-8"))
        ridge = {
            "id": "ridge-map",
            "title": "Ridge map against a hand-labeled sample",
            "reference": f"{rm['test_points']} hand labels in the test half (sample "
            f"{rm['sample_id']}); tuned on {rm['tuning_points']} others",
            "target": "Precision and recall reported (no pass mark)",
            "status": "reported",
            "result": rm["test"],
            "placeholder_thresholds_on_the_same_test_half": rm["test_with_placeholder_thresholds"],
            "tuned": rm["tuned"],
            "method": rm["method"],
            "label": "MODELED",
        }
    spot = ridge_spot_check(root)
    if spot is not None:
        ridge["spot_check"] = spot
    checks.append(ridge)
    checks.append(walker_model_check())
    checks.append(thread_check(root))
    checks.append(
        _not_run(
            "ground-temperature",
            "Ground temperature against REMS",
            "Phase 6 reads the REMS archive",
            6,
        )
    )
    checks.append(
        _not_run(
            "light-time",
            "Light time against JPL Horizons",
            "Phase 6 builds the light-time table",
            6,
        )
    )
    checks.append(station_solver_check(root))
    checks.append(
        _not_run("labels", "Every number in the app labeled", "Phase 7 runs the label audit", 7)
    )
    return {
        "title": "ARIADNE validation",
        "pipeline_version": PIPELINE_VERSION,
        "generated_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "note": "Targets are team targets, set before each run, not published standards.",
        "checks": checks,
    }


def write_validation(root: Path | None = None, log=print) -> dict:
    root = root or repo_root()
    v = build_validation(root)
    (root / "validation.json").write_text(
        json.dumps(v, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    for c in v["checks"]:
        log(f"  {c['id']}: {c['status']}")
    return v
