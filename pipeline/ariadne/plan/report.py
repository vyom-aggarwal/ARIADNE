# Written with AI assistance (Claude Code). See AI_USE.md.
"""docs/plan/<site>.md: the reference plans, the thread run and the assumptions behind them."""

from __future__ import annotations


def plan_markdown(s: dict) -> str:
    sc = s["scenario"]
    th = s["thread"]
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
        f"| Walkable for the walker | {100 * s['walkable_share']:.1f}% of the grid; {100 * s['within_shelter_limit_share']:.1f}% of that is within {sc['shelter_max_min']:.0f} min of shelter |",
        f"| In line of sight of the rover antenna | {100 * s['comms_share']:.1f}% of the grid |",
        f"| Candidate stations | {s['candidates']} (walkable, in line of sight, with an overwatch point within {sc['buddy_max_m']:.0f} m, within {sc['max_station_distance_m']:.0f} m) |",
        f"| Scenario (PLACEHOLDER) | EVA up to {sc['eva_max_min']:.0f} min; {sc['consumables_total_min']:.0f} min of consumables; reserve {sc['reserve_min']:.0f} min; {sc['service_min']:.0f} min per station |",
        f"| Staging point passable for the rover | {'yes' if s['rover_ok'] else 'no'} (rover class go or caution there; the rover's drive to it is not planned) |",
        "",
        "## Reference plans (OR-Tools)",
        "",
        "| Preset | Stations | Science value | Minutes | Consumables (min) | Distance (m) | Least thread margin (min) | Worst minutes to shelter | Longest comm shadow (min) | Checks |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, p in s["plans"].items():
        checks = ", ".join(f"{k} {v}" for k, v in p["checks"].items())
        lines.append(
            f"| {name} | {p['stations']} | {p['science_value']:.2f} | {p['minutes']:.0f} | "
            f"{p['consumables_min']:.0f} | {p['distance_m']:,.0f} | {p['min_thread_margin_min']:.1f} | "
            f"{p['worst_minutes_to_shelter']:.1f} | {p['longest_comm_shadow_min']:.1f} | {checks} |"
        )
    binding = all(p["minutes"] >= sc["eva_max_min"] - 10 for p in s["plans"].values())
    if binding:
        lines += [
            "",
            f"With these PLACEHOLDER settings the {sc['eva_max_min']:.0f}-minute EVA limit binds before the consumables do, and every preset's value weight is high enough that each takes nearly every station it can fit. So the three presets pick almost the same stations and differ mainly in the paths between them. The preset weights are PLACEHOLDER and are for the team to set.",
        ]
    lines += [
        "",
        "## Thread over random scenarios",
        "",
        f"{th['held']} of {th['scenarios']} random scenarios kept the thread at every sample (random station subsets, EVA limits of 90 to 300 min and consumables of 120 to 360 min; seed {th['seed']}). The least margin above the reserve was {th['worst_margin_min']:.2f} min; plans visited {th['mean_stations_visited']:.1f} stations on average.",
        "",
        "## Assumptions",
        "",
        "- Walker model: Minetti et al. 2002 cost of walking against gradient (Earth, unsuited) with a PLACEHOLDER suit and gravity factor of 1.0, a PLACEHOLDER top speed of 1.0 m/s and a PLACEHOLDER power ceiling. NASA/TP-2010-216125 publishes no coefficients for its model, so it is used only for the tested ranges behind the EXTRAPOLATED flag.",
        "- Hazard is the Phase 2 walker cost multiplier less 1; relative dose is the shielding index S; uncertainty is 1 − confidence. Station value is the Phase 2 station score (spectral term missing).",
        "- Comms is line of sight only from a 3 m antenna on the rover at the staging point; no radio model and no relays.",
        "- The buddy rule is met by an overwatch point found for every candidate station; the partner's own walk to it is not timed.",
        "- The rover stays at the staging point; pickups elsewhere are not planned yet.",
        "",
    ]
    return "\n".join(lines)
