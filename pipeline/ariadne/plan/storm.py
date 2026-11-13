# Written with AI assistance (Claude Code). See AI_USE.md.
"""Storm mode: the refuge with the lowest modeled dose over the event (team decision,
2026-11-10), not the earliest arrival.

Doses are relative, in open-sky minutes: one minute under an open sky at S = 1 counts 1. For a
refuge reached by the fastest walk, the dose over an event of D minutes is the exposed walk
(the sum of S x dt along the path) plus the rest of the event at the refuge's S; a walk longer
than the event is cut at the event's end. The options are the rover where it is parked (S a
labeled PLACEHOLDER), the nearest terrain shielding zone (the Phase 2 zones, S <= 0.95, at their
own S), and staying put. Label: MODELED.
"""

from __future__ import annotations

import numpy as np

from ariadne.plan import graph as g

TIME_ONLY = {"time": 1.0, "metabolic": 0.0, "hazard": 0.0, "dose": 0.0, "uncertainty": 0.0}


def event_dose(walk_min: float, walk_dose: float, s_dest: float, duration: float) -> float:
    if walk_min <= duration:
        return float(walk_dose + (duration - walk_min) * s_dest)
    return float(walk_dose * duration / walk_min) if walk_min > 0 else 0.0


def choose(options: list[dict], duration: float) -> dict:
    """The option with the lowest event dose; ties go to the shorter walk."""
    scored = [
        dict(o, dose=event_dose(o["walk_min"], o["walk_dose"], o["s_dest"], duration))
        for o in options
        if o["walk_min"] == o["walk_min"] and o["walk_min"] < float("inf")
    ]
    return min(scored, key=lambda o: (o["dose"], o["walk_min"]))


def refuge_fields(gr: g.Grid, suit, rover_cell, rover_s: float, terrain_cells, terrain_s) -> dict:
    """Fastest-walk fields to the rover and to the shielding zones (reversed graph); each field
    accumulates the walk's dose (S x dt) and, for terrain, the S of the zone cell reached."""
    out = {"rover": g.dijkstra(gr, suit, TIME_ONLY, [tuple(rover_cell)], reverse=True,
                               tie_break=[rover_s])}  # fmt: skip
    if terrain_cells:
        out["terrain"] = g.dijkstra(gr, suit, TIME_ONLY, [tuple(c) for c in terrain_cells],
                                    reverse=True, tie_break=list(terrain_s))  # fmt: skip
    return out


def simplify(path: list, tol: float = 1.0) -> list:
    """Ramer-Douglas-Peucker on grid cells (tolerance in cells), for display only; walk times
    and doses come from the full path."""
    if len(path) < 3:
        return list(path)
    a, b = np.array(path[0], float), np.array(path[-1], float)
    pts = np.array(path, float)
    d = b - a
    n = float(np.hypot(*d))
    if n == 0:
        dist = np.hypot(*(pts - a).T)
    else:
        dist = np.abs(d[0] * (pts[:, 1] - a[1]) - d[1] * (pts[:, 0] - a[0])) / n
    i = int(np.argmax(dist))
    if dist[i] <= tol:
        return [path[0], path[-1]]
    return simplify(path[: i + 1], tol)[:-1] + simplify(path[i:], tol)


def track(gr: g.Grid, margins: list, leg_relay: list, moving: dict, walk_f: list, terrain_f,
          rover_s: float, duration: float, every_min: float, to_xy) -> list:  # fmt: skip
    """Storm responses along a plan, one every `every_min` minutes: from the margin sample at or
    after each mark, the refuge with the lowest event dose. While the rover drives (during the
    first leg, or during the station visit before it changes relay) the response is worked out
    for both of its parking places and the higher dose is kept. Each sample also carries the line
    home: the fastest walk to where the rover parks next."""
    out, mark = [], 0.0
    for x in margins:
        if x["t_min"] + 1e-9 < mark:
            continue
        mark = x["t_min"] + every_min
        r, c = x["xy_cell"]
        cell = (int(round(r)), int(round(c)))
        leg = min(int(x["leg"]), len(leg_relay) - 1)
        relays = [leg_relay[leg]]
        if leg == 0 and x["station"] is None and moving.get("first"):
            relays = [0, leg_relay[0]]
        if x["station"] is not None and x["station"] in moving.get("visits", ()):
            relays = [leg_relay[leg], leg_relay[leg + 1]]
        best = None
        for rl in relays:
            fields = {"rover": walk_f[rl]}
            if terrain_f is not None:
                fields["terrain"] = terrain_f
            resp = response(gr, fields, cell, rover_s, duration)
            resp["relay"] = rl
            if best is None or resp["dose"] > best["dose"]:
                best = resp
        out.append(
            {
                "t_min": x["t_min"],
                "xy_m": to_xy(*cell),
                "rover_relay": best["relay"],
                "rover_moving": len(relays) > 1,
                "choice": best["choice"],
                "walk_min": best["walk_min"],
                "s_dest": best["s_dest"],
                "dose": best["dose"],
                "dose_staying": best["dose_staying"],
                "dose_avoided": best["dose_avoided"],
                "path_xy_m": [to_xy(*p) for p in simplify(best["path"])],
                # the line home: the fastest walk to where the rover parks next (also the
                # abort route on the printed card)
                "home_relay": relays[-1],
                "home_walk_min": round(float(walk_f[relays[-1]].time[cell]), 2),
                "home_path_xy_m": [
                    to_xy(*p) for p in simplify(g.follow_pointers(walk_f[relays[-1]], cell))
                ],
            }
        )
    return out


def response(gr: g.Grid, fields: dict, cell, rover_s: float, duration: float) -> dict:
    """The storm response from one cell: the chosen refuge, its path, and the doses."""
    r, c = cell
    s_here = float(gr.dose[r, c])
    options = [{"name": "stay", "walk_min": 0.0, "walk_dose": 0.0, "s_dest": s_here}]
    for name, f in fields.items():
        options.append(
            {
                "name": name,
                "walk_min": float(f.time[r, c]),
                "walk_dose": float(f.dose[r, c]),
                "s_dest": rover_s if name == "rover" else float(f.tie[r, c]),
            }
        )
    best = choose(options, duration)
    if best["name"] == "stay":
        path = [tuple(cell)]
    else:
        path = g.follow_pointers(fields[best["name"]], cell)
    staying = event_dose(0.0, 0.0, s_here, duration)
    return {
        "choice": best["name"],
        "walk_min": round(best["walk_min"], 2),
        "s_dest": round(best["s_dest"], 3),
        "dose": round(best["dose"], 2),
        "dose_staying": round(staying, 2),
        "dose_avoided": round(staying - best["dose"], 2),
        "path": path,
        "options": [
            {k: (round(v, 3) if isinstance(v, float) else v) for k, v in o.items()} for o in options
        ],
    }
