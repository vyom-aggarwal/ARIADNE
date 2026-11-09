# Written with AI assistance (Claude Code). See AI_USE.md.
"""docs/derived/<site>.md: what `ariadne derive` made and what it found, in plain English."""

from __future__ import annotations


def _h(hours) -> str:
    if hours is None:
        return "never"
    h = int(hours)
    m = int(round((hours - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    return f"{h:02d}:{m:02d}"


def _n(x, fmt="{:.2f}") -> str:
    return "n/a" if x is None else fmt.format(x).replace("-", "−")


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _calibration_section(cal: dict) -> list[str]:
    r, sky, ref, m = cal["result"], cal["sky_check"], cal["reference"], cal["model"]
    lo, hi = r["n_range_for_uncertainty"]
    lines = [
        "## Shielding calibration (Murray Buttes)",
        "",
        f"Reference: {ref['source']}. Parked beside Butte M12 on sols {ref['parked_sols'][0]} to "
        f"{ref['parked_sols'][1]}, RAD measured {ref['measured_reduction'] * 100:.1f}% ± "
        f"{ref['uncertainty'] * 100:.1f}% less dose than the expected dose fitted on sols "
        f"{ref['baseline_sols'][0][0]} to {ref['baseline_sols'][0][1]} and {ref['baseline_sols'][1][0]} to "
        f"{ref['baseline_sols'][1][1]}. So n is fitted to S(parking) f(parking) / mean over baseline sols of "
        "S f, with each baseline sol represented by the positions Curiosity held at its start and end.",
        "",
        "| Quantity | Value |",
        "| --- | --- |",
        f"| Fitted n (target ratio {ref['target_ratio']:.3f}) | **{_n(r['n'], '{:.2f}')}** |",
        f"| n range for 3.8% ± 0.4% | {_n(lo, '{:.2f}')} to {_n(hi, '{:.2f}')} |",
        f"| n for the rounded 4% (ratio 0.96) | {_n(r['n_for_headline_ratio'], '{:.2f}')} |",
        f"| Model ratio at n = 0 (isotropic sky) and n = 10 | {_n(r['ratio_at_n0'], '{:.3f}')} and {_n(r['ratio_at_n10'], '{:.3f}')} |",
        f"| S at the parking spot, mean S over the baseline (at the fitted n) | {_n(r['s_parking_at_n'], '{:.3f}')}, {_n(r['s_baseline_mean_at_n'], '{:.3f}')} |",
        f"| Observer height | {m['observer_height_m']:g} m above the ground (PLACEHOLDER) |",
        f"| MOLA tied to the 1 m DEM by | {_n(m['mola_tie_offset_m'], '{:+.1f}')} m (median difference) |",
        f"| Pressure term spread over the baseline | {m['pressure_factor_spread_over_baseline']:.4f} (negligible) |",
        "",
        f'Result: **{"PASS" if r["passed"] else "NO FIT"}**. Label: "calibrated on one RAD measurement". '
        + (r["note"] or ""),
        "",
        "### Horizon check against the paper's sky mask",
        "",
        "The paper's horizon mask comes from rover images, localization and MSL elevation models; ours comes "
        "from the 1 m DEM and MOLA. This is a comparison, not a gate.",
        "",
        "| Quantity | This model | Ehresmann et al. 2021 |",
        "| --- | --- | --- |",
        f"| Blocked share of the sky | {_pct(sky['blocked_fraction_model'])} | {_pct(sky['blocked_fraction_paper'])} |",
        f"| Mean blocking angle | {sky['mean_blocking_angle_model_deg']:.1f}° | {sky['mean_blocking_angle_paper_deg']:.0f}° |",
        f"| Butte half (azimuth 240° to 60°), mean angle | {sky['butte_half_mean_angle_model_deg']:.1f}° | {sky['butte_half_mean_angle_paper_deg']:.0f}° |",
        f"| Other half, mean angle | {sky['other_half_mean_angle_model_deg']:.1f}° | {sky['other_half_mean_angle_paper_deg']:.0f}° |",
        f"| Largest angle | {sky['max_angle_model_deg']:.1f}° | about {sky['max_angle_paper_deg']:.0f}° |",
        f"| Blocked share with near-field horizons only | {_pct(sky['blocked_fraction_near_only'])} | |",
        f"| Blocked share, mean over the baseline positions | {_pct(sky['blocked_fraction_baseline_mean'])} | |",
        "",
        "### Sensitivity",
        "",
        "| Case | n |",
        "| --- | --- |",
    ]
    lines += [f"| {s['case']} | {_n(s['n'], '{:.2f}')} |" for s in cal["sensitivity"]]
    lines += ["", "Caveats: " + " ".join(cal["caveats"]) + " " + cal["neutral_note"], ""]
    lines += [f"Other published estimate: {ref['other_estimate']}", ""]
    return lines


def derived_markdown(summary: dict, calibration: dict | None) -> str:
    s = summary
    hz = s["horizons"]
    lines = [
        f"# Derived layers: {s['site']}",
        "",
        f"Written by `ariadne derive --site {s['site']}` (pipeline {s['pipeline_version']}, "
        f"{s['computed_utc'][:10]}). Do not edit by hand. The layers themselves are in "
        f"`data/sites/{s['site']}/derived/` (not committed); each has a provenance record.",
        "",
        f"Grid: {s['grid']['width']:,} × {s['grid']['height']:,} cells of {s['grid']['resolution_m']:g} m.",
        "",
    ]
    if calibration is not None:
        lines += _calibration_section(calibration)
    lines += [
        "## Horizons and shielding",
        "",
        f"Shielding uses n = {hz['n']:.2f} from the Murray Buttes calibration. Horizons combine the 1 m DEM out "
        "to 2 km with MOLA out to 100 km, both with the planet's curvature subtracted. "
        f"MOLA sits {_n(hz['mola_tie_offset_m'], '{:.1f}')} m below the 1 m DEM here (median), and is raised by that much. "
        f"The far field sets the horizon in {_pct(hz['far_field_sets_horizon_share'])} of all cell and azimuth pairs.",
        "",
        "| Layer | 5th percentile | Median | 95th percentile | Minimum |",
        "| --- | --- | --- | --- | --- |",
        f"| S, near and far field | {hz['s']['p05']:.4f} | {hz['s']['median']:.4f} | {hz['s']['p95']:.4f} | {hz['s']['min']:.4f} |",
        f"| S, near field only | {hz['s_near_only']['p05']:.4f} | {hz['s_near_only']['median']:.4f} | {hz['s_near_only']['p95']:.4f} | {hz['s_near_only']['min']:.4f} |",
        f"| Blocked share of the sky | {_pct(hz['sky_blocked']['p05'])} | {_pct(hz['sky_blocked']['median'])} | {_pct(hz['sky_blocked']['p95'])} | max {_pct(hz['sky_blocked']['max'])} |",
        "",
    ]
    if s["named_points"]:
        lines += ["| Point | S | Blocked sky |", "| --- | --- | --- |"]
        lines += [
            f"| {p['name']} | {p['s']:.4f} | {_pct(p['blocked'])} |" for p in s["named_points"]
        ]
        lines.append("")
    lines += [
        "## How far-field horizons shift sunrise and sunset",
        "",
        'Times are local true solar time at the site centre; the sun\'s centre is used. "Far field" is the '
        'change from adding MOLA beyond 2 km to the 1 m DEM horizons; "all terrain" is the change from a flat, '
        f"open horizon. Statistics cover every {s['sun']['sample_step_px']}th cell in each direction.",
        "",
        "| Date | Ls | Flat-horizon sunrise and sunset | Far field delays sunrise (median, 90th percentile, max) | Far field advances sunset (median, 90th percentile, max) | All terrain delays sunrise (median) | All terrain advances sunset (median) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for d in s["sun"]["dates"]:
        fr, fs = d["far_delays_sunrise_min"], d["far_advances_sunset_min"]
        tr, ts = d["terrain_delays_sunrise_min"], d["terrain_advances_sunset_min"]

        def trio(x):
            return "n/a" if x is None else f"{x['median']:.1f}, {x['p90']:.1f}, {x['max']:.1f} min"

        lines.append(
            f"| {d['date']} ({d['utc_day']}) | {d['ls']:.0f}° | {_h(d['sunrise_ltst_flat'])} and {_h(d['sunset_ltst_flat'])} | "
            f"{trio(fr)} | {trio(fs)} | {'n/a' if tr is None else f'{tr["median"]:.1f} min'} | "
            f"{'n/a' if ts is None else f'{ts["median"]:.1f} min'} |"
        )
    lines.append("")
    if s["named_points"]:
        lines += [
            "At named points (sunrise and sunset; near field only, then with the far field):",
            "",
            "| Date | Point | Sunrise | Sunset | Far field delays sunrise | Far field advances sunset |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for d in s["sun"]["dates"]:
            for p in d["points"]:
                lines.append(
                    f"| {d['date']} | {p['name']} | {_h(p['sunrise_ltst_near'])} → {_h(p['sunrise_ltst'])} | "
                    f"{_h(p['sunset_ltst_near'])} → {_h(p['sunset_ltst'])} | {_n(p['far_delays_sunrise_min'], '{:.1f}')} min | "
                    f"{_n(p['far_advances_sunset_min'], '{:.1f}')} min |"
                )
        lines.append("")
    w, r, sh, sci, un = s["walkability"], s["ridges"], s["shelters"], s["science"], s["uncertainty"]
    lines += ["## Other layers", "", "| Layer | Summary |", "| --- | --- |"]
    if w:
        ww, wr = w["walker_class_share"], w["rover_class_share"]
        lines.append(
            f"| Walkability, walker (MODELED) | go {_pct(ww['go'])}, caution {_pct(ww['caution'])}, no-go {_pct(ww['no-go'])} |"
        )
        lines.append(
            f"| Walkability, rover (MODELED) | go {_pct(wr['go'])}, caution {_pct(wr['caution'])}, no-go {_pct(wr['no-go'])} |"
        )
        lines.append(
            f"| Sand proxy | uses THEMIS night IR: {'yes' if w['sand_proxy_uses_themis'] else 'no (no THEMIS input for this site)'}; drop-off cells {_pct(w['dropoff_share'])} |"
        )
    if r:
        lines.append(
            f"| Ridges and hollows (MODELED, PLACEHOLDER thresholds) | ridges {_pct(r['ridge_share'])}, hollows {_pct(r['hollow_share'])} of the site |"
        )
        lines.append(
            f"| Fractures | {r['fractures']} lines of 10 m or more, {r['fracture_length_km']} km in all, median {_n(r['fracture_median_length_m'], '{:.0f}')} m |"
        )
    if sh:
        m = sh["minutes_to_shelter"]
        lines.append(
            f"| Terrain shelters (S ≤ 0.95, PLACEHOLDER) | {sh['shelter_area_m2']:,} m² ({_pct(sh['shelter_share'])} of the site) |"
        )
        if m:
            lines.append(
                f"| Minutes to shelter or the staging point (PLACEHOLDER pace) | median {m['median']:.1f}, 95th percentile {m['p95']:.1f}, max {m['max']:.1f} |"
            )
    if s["line_of_sight"]:
        lines.append(
            f"| Line of sight from the staging antenna | {_pct(s['line_of_sight']['visible_share_of_site'])} of the site (line of sight only, no radio model) |"
        )
    if sci:
        sc = sci["score"]
        lines.append(
            f"| Science transects | {sci['transects']} transects ({sci['on_fractures']} on mapped fractures); station scores median {sc['median']:.2f} (5th to 95th percentile {sc['p05']:.2f} to {sc['p95']:.2f}); {sci['prior_targets']} prior targets; missing term: spectral |"
        )
    if un:
        c = un["confidence"]
        lines.append(
            f"| Confidence | median {c['median']:.2f}; {_pct(un['share_below_0_5'])} of cells below 0.5 |"
        )
    if s.get("light"):
        lt = s["light"]
        lines.append(
            f"| Light, sol {lt['reference_sol']} | sunrise median {_h(lt['sunrise_ltst']['median'])}, sunset median {_h(lt['sunset_ltst']['median'])}; insolation median {lt['insolation_ratio']['median']:.2f} of flat open ground |"
        )
    lines.append("")
    if s["drill_sites"]:
        lines += [
            "## Drill sites",
            "",
            "| Hole | Sol (blog) | PLACES site, drive | Held sols | Easting, northing (m) |",
            "| --- | --- | --- | --- | --- |",
        ]
        for d in s["drill_sites"]:
            lines.append(
                f"| {d['name']} | {d['sol']} | {d['site']}, {d['drive']} | {d['held_from_sol']} to {d['held_until_sol']} | {d['easting']:,.1f}, {d['northing']:,.1f} |"
            )
        lines.append("")
    lines += [
        "## Not done here",
        "",
        "- Relative ground temperature is implemented and tested, but needs the REMS archive, which Phase 6 reads.",
        "- The spectral term of the science score needs CRISM summary parameters, not read yet; its weight is set aside.",
        "- Ridge thresholds are PLACEHOLDER until a hand-labeled sample exists, so the ridge map has no precision or recall yet.",
        "- Minutes-to-shelter uses a PLACEHOLDER pace until Phase 3 brings the NASA/TP-2010-216125 walking model.",
        "",
    ]
    return "\n".join(lines)
