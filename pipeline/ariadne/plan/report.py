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
        f"| Walkable for the walker | {100 * s['walkable_share']:.1f}% of the grid; of that, {shelter} walk of a place the rover can park |",
        f"| In line of sight of the rover antenna | {100 * s['comms_share']:.1f}% of the grid from the staging point; {100 * s['comms_share_with_relays']:.1f}% from the staging point or a relay site |",
        f"| Candidate transects | {s['candidate_transects']} whole fracture (or crest), wall and hollow transects: all three points walkable and in line of sight of the rover at some relay site, each with an overwatch point within {sc['buddy_max_m']:.0f} m, within {sc['max_station_distance_m']:.0f} m |",
        f"| Scenario (PLACEHOLDER) | EVA up to {sc['eva_max_min']:.0f} min (6 h); {sc['consumables_total_min']:.0f} min of consumables (6 h plus the 30 min reserve); {sc['service_min']:.0f} min per station, so 45 min per transect plus its internal walk |",
        f"| Staging point passable for the rover | {'yes' if s['rover_ok'] else 'no'} (rover class go or caution there; the rover's drive to it is not planned) |",
        "",
        "## Presets (all PLACEHOLDER)",
        "",
        "| Preset | Reserve (min) | Walking limit to the rover (min) | Caution (hazard) weight | Uncertainty weight | Objective | Usable transects |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, p in s["presets"].items():
        lines.append(
            f"| {name} | {p['limits']['reserve_min']:.0f} | {p['limits']['shelter_max_min']:.0f} | "
            f"{p['weights']['hazard']:g} | {p['weights']['uncertainty']:g} | "
            f"{'complete transects, then value' if p['objective'] == 'transects' else 'science value'} | "
            f"{s['usable_transects'][name]} |"
        )
    rl = s["relays"]
    lines += [
        "",
        "## Rover as a mobile comms relay (PLACEHOLDER rover settings)",
        "",
        f"From {rl['candidates']} rover-reachable candidate sites ({rl['rover']['relay_spacing_m']:.0f} m grid within {rl['rover']['relay_max_distance_m']:.0f} m of the staging point), greedy coverage chose {len(rl['sites']) - 1} relay sites. Of the {rl['pool']} highest-value whole transects within reach, {rl['pool_seen_from_staging']} are in full sight of the rover at the staging point and {rl['pool_seen_with_relays']} with the relay sites. The rover drives at {rl['rover']['speed_go_m_s']:g} m/s on rover-go ground and {rl['rover']['speed_caution_m_s']:g} m/s on caution ground; it moves only during the last station of a transect (within the 15-minute visit, with that station in sight along the whole drive) or during the first leg, and the walk ends where the rover is.",
        "",
        "| Relay | Easting, northing (m) | Drive from staging (min) |",
        "| --- | --- | --- |",
    ]
    for i, (xy, d) in enumerate(zip(rl["sites"], rl["drive_from_staging_min"], strict=True)):
        lines.append(
            f"| {'STAGING' if i == 0 else f'RELAY{i}'} | {xy[0]:,.1f}, {xy[1]:,.1f} | {d:.1f} |"
        )
    lines += [
        "",
        "| Preset | Usable transects: staging only, with relay | Planned transects: staging only, with relay | Science value: staging only, with relay |",
        "| --- | --- | --- | --- |",
    ]
    for name, c in s["comparison"].items():
        lines.append(
            f"| {name} | {c['usable_transects_staging_only']}, {c['usable_transects_with_relay']} | "
            f"{c['transects_staging_only']}, {c['transects_with_relay']} | "
            f"{c['value_staging_only']:.2f}, {c['value_with_relay']:.2f} |"
        )
    lines += [
        "",
        "## Reference plans (OR-Tools)",
        "",
        "Each plan visits whole transects only: every visited transect's fracture (or crest), wall and hollow stations, in that order.",
        "",
        "| Preset | Transects | Stations | Science value | Minutes | Consumables (min) | Distance (m) | Least thread margin (min) | Worst walking minutes to the rover | Longest comm shadow (min) | Rover moves, ends at | Checks |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, p in s["plans"].items():
        checks = ", ".join(f"{k} {v}" for k, v in p["checks"].items())
        lines.append(
            f"| {name} | {p['transects']} | {p['stations']} | {p['science_value']:.2f} | {p['minutes']:.0f} | "
            f"{p['consumables_min']:.0f} | {p['distance_m']:,.0f} | {p['min_thread_margin_min']:.1f} | "
            f"{p['worst_minutes_to_shelter']:.1f} | {p['longest_comm_shadow_min']:.1f} | "
            f"{p['rover_moves']}, {p['ends_at']} | {checks} |"
        )
    ps = s.get("price_of_safety")
    if ps:
        lines += [
            "",
            "## Price of safety (Safest against Most science)",
            "",
            f"Safest gives up {ps['value_given_up']:.2f} of science value "
            f"({ps['value_given_up_share']:.1%} of Most science's {ps['value_most_science']:.2f}) "
            f"and {ps['transects_given_up']} transect(s), and gains {ps['margin_gained_min']:.1f} "
            "min of least thread margin above its reserve "
            f"({ps['margin_safest_min']:.1f} against {ps['margin_most_science_min']:.1f}); its "
            f"reserve is {ps['reserve_safest_min']:.0f} min against "
            f"{ps['reserve_most_science_min']:.0f}, and its worst walk to the rover "
            f"{ps['worst_to_rover_safest_min']:.1f} min against "
            f"{ps['worst_to_rover_most_science_min']:.1f}. All MODELED, on PLACEHOLDER presets.",
            "",
            f"Do the presets separate? {ps['separation']}",
        ]
    st = s.get("storm")
    if st:
        lines += [
            "",
            "## Storm mode along the plans (MODELED, PLACEHOLDER event)",
            "",
            f"At least every {sc['storm_sample_every_min']:.0f} minutes of walking along each "
            "plan (and once per station visit, where the crew stands still), the refuge with "
            f"the lowest modeled dose over a {sc['storm_event_duration_min']:.0f}-minute event "
            "(PLACEHOLDER until Phase 6 replays May 2024), counting the exposed walk there: the "
            f"rover (S {s['relays']['rover']['shelter_s']:g}, PLACEHOLDER), the nearest terrain "
            "shielding zone at its own S, or staying put. Doses are relative, in open-sky minutes. "
            "Over an event this long the rover wins wherever it can be reached: terrain shields a "
            "few percent, so it wins only for events of a few minutes.",
            "",
            "| Preset | Samples | Rover chosen | Terrain chosen | Stay chosen | Longest walk to the refuge (min) | Mean dose avoided (open-sky min) |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for name, x in st.items():
            lines.append(
                f"| {name} | {x['samples']} | {x['choices'].get('rover', 0)} | "
                f"{x['choices'].get('terrain', 0)} | {x['choices'].get('stay', 0)} | "
                f"{x['longest_walk_min']:.1f} | {x['mean_dose_avoided']:.1f} |"
            )
    lines += [
        "",
        "## Thread over random scenarios",
        "",
        f"{th['held']} of {th['scenarios']} random scenarios kept the thread at every sample (random transect subsets, EVA limits of 120 to 420 min and consumables of 150 to 450 min, Balanced limits; seed {th['seed']}). The least margin above the reserve was {th['worst_margin_min']:.2f} min; plans visited {th['mean_transects_visited']:.1f} transects and moved the rover {th['mean_rover_moves']:.1f} times on average; C_home follows the rover.",
        "",
        "## Assumptions",
        "",
        "- Walker model: Minetti et al. 2002 cost of walking against gradient (Earth, unsuited) with a PLACEHOLDER suit and gravity factor of 1.0, a PLACEHOLDER top speed of 1.0 m/s and a PLACEHOLDER power ceiling. NASA/TP-2010-216125 publishes no coefficients for its model, so it is used only for the tested ranges behind the EXTRAPOLATED flag.",
        "- Hazard (the caution penalty) is the Phase 2 walker cost multiplier less 1; relative dose is the shielding index S; uncertainty is 1 − confidence. A transect's value is the sum of its three Phase 2 station scores (spectral term missing).",
        "- The planner stays conservative: slope no-go cells are never entered, even where the map may be over-cautious (seam or low-confidence zones); the surfaces mark those cells for the crew to check by eye.",
        "- Comms is line of sight only from a 3 m antenna on the rover at the relay site it is parked at; no radio model. While the rover drives during the first leg, contact is assumed from its destination.",
        "- The buddy rule is met by an overwatch point found for every station; the partner's own walk to it is not timed.",
        "- The thread's C_home is the consumables to walk to the rover's current relay site; during a move, the larger of the two sites' values at that station.",
        "- Shelter is the rover (team decision, 2026-11-10): the shelter limit is walking minutes to the rover wherever it is. Parked, that is the walk to its relay site; driving during a station visit, the walk from the station to the farthest point of its drive; driving during the first leg, the walk to where it is at that moment (positions every half minute of the drive, the larger of the two around each moment). Terrain shielding zones block a few percent of the dose at most and are not shelter.",
        "",
    ]
    return "\n".join(lines)
