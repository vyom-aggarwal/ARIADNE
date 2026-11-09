# Written with AI assistance (Claude Code). See AI_USE.md.
"""docs/plan/<site>.md: the reference plans, the thread run and the assumptions behind them."""

from __future__ import annotations


def plan_markdown(s: dict) -> str:
    sc = s["scenario"]
    th = s["thread"]
    shelter = ", ".join(
        f"{100 * v:.1f}% within {float(k):.0f} min"
        for k, v in s["within_shelter_limit_share"].items()
    )
    lines = [
        f"# Route plans: {s['site']}",
        "",
        f"Written by `ariadne plan` (pipeline {s['pipeline_version']}, {s['computed_utc']}). "
        "Every plan is MODELED and rests on PLACEHOLDER settings (config/presets.json, "
        "config/suits.json); the walker model is EXTRAPOLATED to Mars gravity.",
        "",
        "## Setting",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Staging point (rover), PLACEHOLDER | E {s['staging_xy_m'][0]:,.1f} m, N {s['staging_xy_m'][1]:,.1f} m |",
        f"| Planning grid | {s['grid']['resolution_m']:.0f} m cells, {s['grid']['shape'][1]} × {s['grid']['shape'][0]} |",
        f"| Walkable for the walker | {100 * s['walkable_share']:.1f}% of the grid; of that, {shelter} of shelter |",
        f"| In line of sight of the rover antenna | {100 * s['comms_share']:.1f}% of the grid |",
        f"| Candidate transects | {s['candidate_transects']} whole fracture (or crest), wall and hollow transects: all three points walkable, in line of sight, with an overwatch point within {sc['buddy_max_m']:.0f} m, within {sc['max_station_distance_m']:.0f} m |",
        f"| Scenario (PLACEHOLDER) | EVA up to {sc['eva_max_min']:.0f} min (6 h); {sc['consumables_total_min']:.0f} min of consumables (6 h plus the 30 min reserve); {sc['service_min']:.0f} min per station, so 45 min per transect plus its internal walk |",
        f"| Staging point passable for the rover | {'yes' if s['rover_ok'] else 'no'} (rover class go or caution there; the rover's drive to it is not planned) |",
        "",
        "## Presets (all PLACEHOLDER)",
        "",
        "| Preset | Reserve (min) | Shelter limit (min) | Caution (hazard) weight | Uncertainty weight | Objective | Usable transects |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, p in s["presets"].items():
        lines.append(
            f"| {name} | {p['limits']['reserve_min']:.0f} | {p['limits']['shelter_max_min']:.0f} | "
            f"{p['weights']['hazard']:g} | {p['weights']['uncertainty']:g} | "
            f"{'complete transects, then value' if p['objective'] == 'transects' else 'science value'} | "
            f"{s['usable_transects'][name]} |"
        )
    lines += [
        "",
        "## Reference plans (OR-Tools)",
        "",
        "Each plan visits whole transects only: every visited transect's fracture (or crest), wall and hollow stations, in that order.",
        "",
        "| Preset | Transects | Stations | Science value | Minutes | Consumables (min) | Distance (m) | Least thread margin (min) | Worst minutes to shelter | Longest comm shadow (min) | Checks |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, p in s["plans"].items():
        checks = ", ".join(f"{k} {v}" for k, v in p["checks"].items())
        lines.append(
            f"| {name} | {p['transects']} | {p['stations']} | {p['science_value']:.2f} | {p['minutes']:.0f} | "
            f"{p['consumables_min']:.0f} | {p['distance_m']:,.0f} | {p['min_thread_margin_min']:.1f} | "
            f"{p['worst_minutes_to_shelter']:.1f} | {p['longest_comm_shadow_min']:.1f} | {checks} |"
        )
    lines += [
        "",
        "## Thread over random scenarios",
        "",
        f"{th['held']} of {th['scenarios']} random scenarios kept the thread at every sample (random transect subsets, EVA limits of 120 to 420 min and consumables of 150 to 450 min, Balanced limits; seed {th['seed']}). The least margin above the reserve was {th['worst_margin_min']:.2f} min; plans visited {th['mean_transects_visited']:.1f} transects on average.",
        "",
        "## Assumptions",
        "",
        "- Walker model: Minetti et al. 2002 cost of walking against gradient (Earth, unsuited) with a PLACEHOLDER suit and gravity factor of 1.0, a PLACEHOLDER top speed of 1.0 m/s and a PLACEHOLDER power ceiling. NASA/TP-2010-216125 publishes no coefficients for its model, so it is used only for the tested ranges behind the EXTRAPOLATED flag.",
        "- Hazard (the caution penalty) is the Phase 2 walker cost multiplier less 1; relative dose is the shielding index S; uncertainty is 1 − confidence. A transect's value is the sum of its three Phase 2 station scores (spectral term missing).",
        "- The planner stays conservative: slope no-go cells are never entered, even where the map may be over-cautious (seam or low-confidence zones); the surfaces mark those cells for the crew to check by eye.",
        "- Comms is line of sight only from a 3 m antenna on the rover at the staging point; no radio model and no relays.",
        "- The buddy rule is met by an overwatch point found for every station; the partner's own walk to it is not timed.",
        "- The rover stays at the staging point; pickups elsewhere are not planned yet.",
        "",
    ]
    return "\n".join(lines)
