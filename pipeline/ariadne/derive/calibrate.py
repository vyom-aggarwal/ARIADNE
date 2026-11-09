# Written with AI assistance (Claude Code). See AI_USE.md.
"""Calibrate the shielding exponent n at Murray Buttes against RAD (PROMPT.md 4.5).

Ehresmann et al. (2021, JGR Planets 126, e2021JE006851) measured 3.8% +/- 0.4% less dose on
sols 1456 to 1467, parked beside Butte M12, than an expected dose fitted on sols 1440 to 1455 and
1468 to 1480. So the model ratio is

    S(parking) f(parking) / mean over baseline sols of [mean of S f at that sol's positions]

where a sol's positions are those held at its start and end (PLACES gives no drive times).
Horizons combine the 1 m DEM (near field) and MOLA (far field) at each exact point.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from ariadne.config import load_derive_config, setting
from ariadne.derive import horizons as hz
from ariadne.derive import shielding as sh
from ariadne.fetch import context, places


def point_horizons(
    dem,
    dem_t,
    regional,
    regional_t,
    tie: float,
    xs,
    ys,
    cfg,
    observer_height: float,
    far: bool = True,
):
    """Horizon angles (points x azimuths) at exact points: near field, far field and combined."""
    az = hz.azimuths(int(setting(cfg, "horizons", "azimuths")))
    near_max = float(setting(cfg, "horizons", "near_max_m"))
    dist = hz.near_distances(
        near_max,
        dem_t.a,
        float(setting(cfg, "horizons", "near_fine_until_m")),
        float(setting(cfg, "horizons", "near_growth")),
    )
    near = hz.horizons_at_points(dem, dem_t, xs, ys, az, dist, observer_height)
    if not far:
        return near, None, near
    h, w = dem.shape
    bounds = (dem_t.c, dem_t.f + dem_t.e * h, dem_t.c + dem_t.a * w, dem_t.f)
    reach = np.minimum(near_max, hz.distance_to_box_edge(xs, ys, az, bounds))
    z0 = hz.sample_bilinear(dem, dem_t, xs, ys) + observer_height
    fdist = hz.far_distances(
        0.0,
        float(setting(cfg, "horizons", "far_max_m")),
        float(setting(cfg, "horizons", "far_min_step_m")),
        float(setting(cfg, "horizons", "far_growth")),
    )
    tmax, _ = hz.profile_max_at_points(
        np.asarray(regional, dtype=np.float64) + tie, regional_t, xs, ys, z0, az, fdist, reach
    )
    farh = np.degrees(np.arctan(tmax))
    return near, farh, np.maximum(near, farh)


def calibration_points(rover, cfg) -> dict:
    """Parking spot and the baseline sols' start and end positions from PLACES."""
    park_cfg = cfg["calibration"]["parking"]
    park = rover[(rover.site == park_cfg["site"]) & (rover.drive == park_cfg["drive"])]
    if park.empty:
        raise ValueError("parking localization not found in PLACES")
    park = park.iloc[0]
    sols = []
    for lo, hi in setting(cfg, "calibration", "baseline_sols"):
        for sol in range(int(lo), int(hi) + 1):
            start, end = context.sol_positions(rover, sol)
            sols.append(
                {
                    "sol": sol,
                    "positions": [
                        (float(p.easting), float(p.northing), int(p.site), int(p.drive))
                        for p in (start, end)
                    ],
                }
            )
    return {"parking": park, "sols": sols}


def _evaluate(dem, dem_t, regional, regional_t, tie, pts, cfg, obs_h, far, f_kwargs):
    park = pts["parking"]
    xs = [float(park.easting)]
    ys = [float(park.northing)]
    index = []
    for s in pts["sols"]:
        idx = []
        for x, y, _, _ in s["positions"]:
            idx.append(len(xs))
            xs.append(x)
            ys.append(y)
        index.append(idx)
    xs, ys = np.array(xs), np.array(ys)
    near, farh, h = point_horizons(dem, dem_t, regional, regional_t, tie, xs, ys, cfg, obs_h, far)
    z = hz.sample_bilinear(dem, dem_t, xs, ys)
    f = sh.pressure_factor(z, **f_kwargs)
    h_base = [h[i] for i in index]
    f_base = [f[i] for i in index]
    return {"h": h, "near": near, "far": farh, "z": z, "f": f, "h_base": h_base, "f_base": f_base}


def calibrate(site_dir: Path, places_csv: Path, cfg: dict | None = None) -> dict:
    cfg = cfg or load_derive_config()
    with rasterio.open(site_dir / "dem.tif") as d:
        dem = d.read(1).astype(np.float64)
        dem[dem == d.nodata] = np.nan
        dem_t = d.transform
    with rasterio.open(site_dir / "regional_dem.tif") as d:
        regional = d.read(1).astype(np.float64)
        regional[regional == d.nodata] = np.nan
        regional_t = d.transform
    tie = hz.tie_offset(dem, dem_t, regional, regional_t)
    rover = places.load_rover_positions(places_csv)
    pts = calibration_points(rover, cfg)

    reduction = float(setting(cfg, "calibration", "reduction"))
    unc = float(setting(cfg, "calibration", "reduction_uncertainty"))
    target = 1.0 - reduction
    bounds = (1.0 - reduction - unc, 1.0 - reduction + unc)
    headline = float(setting(cfg, "calibration", "headline_ratio"))
    n_range = tuple(setting(cfg, "shielding", "n_search"))
    obs_main = float(setting(cfg, "horizons", "observer_height_m"))

    park = pts["parking"]
    z_park = float(hz.sample_bilinear(dem, dem_t, [park.easting], [park.northing])[0])
    p_ref = sh.column_to_pressure(
        float(setting(cfg, "shielding", "murray_column_g_cm2")),
        float(setting(cfg, "shielding", "gravity_m_s2")),
    )
    f_kwargs = dict(
        z_ref=z_park,
        p_ref=p_ref,
        kappa=float(setting(cfg, "shielding", "kappa_ugy_per_day_per_pa")),
        dose_ref=float(setting(cfg, "shielding", "dose_ref_ugy_per_day")),
        scale_height=float(setting(cfg, "shielding", "scale_height_m")),
    )

    def run(obs_h, far=True):
        ev = _evaluate(dem, dem_t, regional, regional_t, tie, pts, cfg, obs_h, far, f_kwargs)
        cal = sh.calibrate_n(
            ev["h"][0], float(ev["f"][0]), ev["h_base"], ev["f_base"], target, bounds, n_range
        )
        cal_headline = sh.calibrate_n(
            ev["h"][0], float(ev["f"][0]), ev["h_base"], ev["f_base"], headline, None, n_range
        )
        return ev, cal, cal_headline

    ev, cal, cal_h = run(obs_main)
    az = hz.azimuths(ev["h"].shape[1])
    h_park = ev["h"][0]
    butte_half = (az >= 240.0) | (az < 60.0)
    base_all = np.vstack(ev["h_base"])
    sens = []
    for obs_h in setting(cfg, "calibration", "observer_heights_m"):
        if float(obs_h) == obs_main:
            continue
        _, c, _ = run(float(obs_h))
        sens.append({"case": f"observer {obs_h:g} m above the ground", "n": c.n, "note": c.note})
    ev_near, c_near, _ = run(obs_main, far=False)
    sens.append({"case": "near-field horizons only (no MOLA)", "n": c_near.n, "note": c_near.note})

    def r4(x):
        return None if x is None else round(float(x), 4)

    f_spread = float(np.max(np.concatenate(ev["f_base"])) - np.min(np.concatenate(ev["f_base"])))
    return {
        "id": "shielding-murray-buttes",
        "title": "Shielding index calibrated at Murray Buttes",
        "label": "calibrated on one RAD measurement",
        "reference": {
            "measured_reduction": reduction,
            "uncertainty": unc,
            "target_ratio": target,
            "headline_ratio": headline,
            "parked_sols": setting(cfg, "calibration", "parked_sols"),
            "baseline_sols": setting(cfg, "calibration", "baseline_sols"),
            "blocked_sky_fraction": float(setting(cfg, "calibration", "blocked_sky_fraction")),
            "neutral_reduction": 0.075,
            "source": "Ehresmann et al. 2021, JGR Planets 126, e2021JE006851",
            "other_estimate": "Guo et al. 2021 (Astron. Astrophys. Rev. 29:8, section 5.4) find "
            "5% +/- 1% with a different baseline (the same phase of the four previous solar "
            "rotations); not fitted here.",
        },
        "parking": {
            "site": int(park.site),
            "drive": int(park.drive),
            "easting": float(park.easting),
            "northing": float(park.northing),
            "dem_elevation_m": round(z_park, 2),
        },
        "baseline_positions": [
            {
                "sol": s["sol"],
                "positions": [
                    [round(x, 2), round(y, 2), si, dr] for x, y, si, dr in s["positions"]
                ],
            }
            for s in pts["sols"]
        ],
        "model": {
            "observer_height_m": obs_main,
            "azimuths": int(len(az)),
            "near_max_m": float(setting(cfg, "horizons", "near_max_m")),
            "far_max_m": float(setting(cfg, "horizons", "far_max_m")),
            "mola_tie_offset_m": round(tie, 2),
            "pressure_ref_pa": round(p_ref, 1),
            "pressure_factor_spread_over_baseline": round(f_spread, 6),
        },
        "result": {
            "n": r4(cal.n),
            "n_range_for_uncertainty": [r4(cal.n_low), r4(cal.n_high)],
            "n_for_headline_ratio": r4(cal_h.n),
            "crossings": cal.crossings,
            "note": cal.note,
            "ratio_at_n": r4(cal.ratio_at(cal.n)) if cal.n is not None else None,
            "ratio_at_n0": r4(cal.ratio_grid[0]),
            "ratio_at_n10": r4(cal.ratio_grid[-1]),
            "s_parking_at_n": r4(sh.open_sky_fraction(h_park, cal.n))
            if cal.n is not None
            else None,
            "s_baseline_mean_at_n": r4(
                np.mean([np.mean(sh.open_sky_fraction(h, cal.n)) for h in ev["h_base"]])
            )
            if cal.n is not None
            else None,
            "passed": cal.n is not None,
        },
        "sky_check": {
            "blocked_fraction_model": r4(sh.blocked_fraction(h_park)),
            "blocked_fraction_paper": float(setting(cfg, "calibration", "blocked_sky_fraction")),
            "mean_blocking_angle_model_deg": round(float(sh.mean_blocking_angle(h_park)), 2),
            "mean_blocking_angle_paper_deg": 11.0,
            "butte_half_mean_angle_model_deg": round(
                float(np.mean(np.clip(h_park[butte_half], 0, 90))), 2
            ),
            "butte_half_mean_angle_paper_deg": 16.0,
            "other_half_mean_angle_model_deg": round(
                float(np.mean(np.clip(h_park[~butte_half], 0, 90))), 2
            ),
            "other_half_mean_angle_paper_deg": 6.0,
            "max_angle_model_deg": round(float(np.max(h_park)), 2),
            "max_angle_paper_deg": 30.0,
            "blocked_fraction_near_only": r4(sh.blocked_fraction(ev_near["h"][0])),
            "blocked_fraction_baseline_mean": r4(float(np.mean(sh.blocked_fraction(base_all)))),
            "note": "The paper's horizon mask comes from rover images, localization and MSL "
            "elevation models (Calef, JPL), so this is a comparison, not a pass or fail.",
        },
        "horizon_parking_deg": [round(float(x), 2) for x in h_park],
        "horizon_parking_near_deg": [round(float(x), 2) for x in ev["near"][0]],
        "sensitivity": sens,
        "neutral_note": "The model has no neutral-particle term, so the measured 7.5% drop in "
        "neutral particles is reported, not predicted.",
        "caveats": [
            "The butte also sends back some albedo radiation, which the paper could not separate "
            "and this model leaves out.",
            "RAD's dose is omnidirectional; the model treats the whole dose as arriving from the "
            "sky above the horizon.",
            "One measurement fixes one number (n); it does not validate the model elsewhere.",
        ],
    }
