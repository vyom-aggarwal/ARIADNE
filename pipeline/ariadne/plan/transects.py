# Written with AI assistance (Claude Code). See AI_USE.md.
"""Transects as routing nodes.

The science value of a boxwork transect is in comparing its fracture (or crest), wall and hollow
stations, so the planner visits a transect whole or not at all. A node is one transect: the walk
enters at the fracture or crest point, works it, walks to the wall point, works it, walks to the
hollow point and works it, then leaves. Its service time is the three station visits plus that
internal walk; legs between nodes run from one node's hollow point to the next node's first point.
"""

from __future__ import annotations

import numpy as np

FIRST = ("fracture", "crest")
ORDER = ("wall", "hollow")


def order_transect(points):
    """Points [(role, cell, score), ...] in walking order (fracture or crest, wall, hollow), as
    (roles, cells, scores); None if a role is missing."""
    first = [p for p in points if p[0] in FIRST]
    rest = [[p for p in points if p[0] == r] for r in ORDER]
    if not first or not all(rest):
        return None
    chosen = [first[0], rest[0][0], rest[1][0]]
    return [p[0] for p in chosen], [p[1] for p in chosen], [p[2] for p in chosen]


def node_service(internal: list[dict], service_min: float, station_rate_ratio: float) -> dict:
    """Minutes and consumables a node takes: three station visits and the internal walk."""
    minutes = 3 * service_min + sum(m["minutes"] for m in internal)
    cons = 3 * service_min * station_rate_ratio + sum(m["consumables"] for m in internal)
    return {"minutes": float(minutes), "consumables": float(cons)}


def expand_route(route, nodes, leg_paths, internal_paths):
    """Turn a node route [0, a, b, ..., 0] into legs and stations for the constraint check:
    leg k ends at station k, and the last leg ends at the staging point."""
    legs, stations, info = [], [], []
    for a, b in zip(route[:-1], route[1:], strict=True):
        if a == b:
            continue
        legs.append(leg_paths[(a, b)])
        if b == 0:
            continue
        nd = nodes[b - 1]
        for k, (cell, role) in enumerate(zip(nd["points"], nd["roles"], strict=True)):
            if k > 0:
                legs.append(internal_paths[b][k - 1])
            stations.append(cell)
            info.append({"transect": nd["transect"], "role": role, "node": b})
    return legs, stations, info


def objective_values(values, mode: str) -> np.ndarray:
    """Per-node prize for the solver. 'value': the transect's science value. 'transects': one
    per complete transect, plus a tie-break below 1/1000 that prefers higher value, so more
    transects always win."""
    v = np.asarray(values, dtype=np.float64)
    if mode == "value":
        return v
    if mode == "transects":
        return 1.0 + 1e-3 * v / max(float(v.max()), 1e-9)
    raise ValueError(mode)
