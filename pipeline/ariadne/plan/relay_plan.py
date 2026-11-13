# Written with AI assistance (Claude Code). See AI_USE.md.
"""Planning with the rover as a mobile comms relay.

Nodes are (transect, relay) pairs. Legs run from one transect's exit to the next transect's
entry, or from the last transect's exit to the relay where the rover ends the EVA. The comms and
shelter checks of a leg use the relay the rover is parked at during it; the rover changes relay
only during the last station of a transect (relay.switch_feasible) or during the first leg, and
the thread ends at the rover's last relay. See docs/PROGRESS.md (rover relay plan).

Shelter is the rover (team decision, 2026-11-10): the shelter value at a point is the walking
time from it to the rover. While the rover is parked that is the walk to its relay; while it
drives during a station visit, the walk from the station to the farthest point of its drive
(switch_shelter); while it drives during the first leg, the walk to where it is at that moment,
from rover positions sampled every half minute of the drive (moving_rover_fields).
"""

from __future__ import annotations

import numpy as np
from affine import Affine

from ariadne.derive import los
from ariadne.plan import constraints as cs
from ariadne.plan import graph as g
from ariadne.plan import relay, select
from ariadne.plan import transects as tr

TIME_ONLY = {"time": 1.0, "metabolic": 0.0, "hazard": 0.0, "dose": 0.0, "uncertainty": 0.0}
CONSUMABLES = {"time": 0.0, "metabolic": 1.0, "hazard": 0.0, "dose": 0.0, "uncertainty": 0.0}


def _xy(rc, res):
    return ((rc[1] + 0.5) * res, -(rc[0] + 0.5) * res)


def choose_relays(gr, staging, rover_cls, pool, rover: dict, log) -> dict:
    """The staging point plus up to rover['relay_sites'] relay sites (greedy coverage)."""
    res = gr.res
    speeds = {0: rover["speed_go_m_s"], 1: rover["speed_caution_m_s"]}
    rt0 = relay.rover_times(rover_cls, res, speeds, staging)
    reach = np.isfinite(rt0.minutes) & gr.passable
    spacing = max(1, int(round(rover["relay_spacing_m"] / res)))
    sites = relay.candidate_sites(reach, staging, spacing, rover["relay_max_distance_m"] / res)
    ant, rng = float(rover["antenna_height_m"]), float(rover["viewshed_range_m"])

    def view(rc):
        return los.viewshed(gr.z, res, rc, ant, 1.8, rng)

    v0 = view(staging)
    values = {i: nd["value"] for i, nd in enumerate(pool)}
    base = {i for i, nd in enumerate(pool) if relay.sees_transect(v0, nd["points"])}
    views, sees = [], []
    for rc in sites:
        v = view(rc)
        views.append(v)
        sees.append({i for i, nd in enumerate(pool) if relay.sees_transect(v, nd["points"])})
    picked = relay.greedy_relays(sees, values, int(rover["relay_sites"]), base)
    cells = [tuple(staging)] + [sites[i] for i in picked]
    vs = [v0] + [views[i] for i in picked]
    covered = set(base).union(*[sees[i] for i in picked]) if picked else set(base)
    times = [rt0] + [relay.rover_times(rover_cls, res, speeds, c) for c in cells[1:]]
    log(f"  relays: {len(cells) - 1} sites chosen from {len(sites)}; pool transects in sight "
        f"{len(base)} from staging, {len(covered)} with the relays")  # fmt: skip
    return {
        "cells": cells,
        "views": vs,
        "times": times,
        "candidates": len(sites),
        "pool_seen_from_staging": len(base),
        "pool_seen_with_relays": len(covered),
        "pool": len(pool),
        "drive_from_staging_min": [float(rt0.minutes[c]) for c in cells],
    }


def path_samples(gr, suit, w, pts):
    s = cs.route_samples(gr, suit, w, [pts], [], 0.0, 0.0)
    rc = np.array([cs._cell(gr, x["r"], x["c"]) for x in s])
    return rc[:, 0], rc[:, 1], np.array([x["t"] for x in s])


def longest_shadow(visible: np.ndarray, t: np.ndarray) -> float:
    longest, start = 0.0, None
    for v, tt in zip(visible, t, strict=True):
        if not v:
            start = tt if start is None else start
            longest = max(longest, tt - start)
        else:
            start = None
    return float(longest)


def leg_extras_by_relay(gr, suit, w, paths, shape, views, shelters, first_leg=None) -> dict:
    """Longest comm shadow and worst walking minutes to the rover of every leg, per relay. Legs
    from the staging point (source 0) to a node served from another relay are walked while the
    rover drives there, so their shelter follows the moving rover (`first_leg`)."""
    R = len(views)
    shadow = np.zeros((R,) + shape)
    shelter = np.zeros((R,) + shape)
    for key, pts in paths.items():
        rr, cc, t = path_samples(gr, suit, w, pts)
        for r in range(R):
            shadow[(r, *key)] = longest_shadow(views[r][rr, cc], t)
            if key[0] == 0 and r > 0 and first_leg is not None and r in first_leg:
                shelter[(r, *key)] = float(moving_shelter(rr, cc, t, first_leg[r]).max())
            else:
                shelter[(r, *key)] = float(shelters[r][rr, cc].max())
    return {"shadow": shadow, "shelter": shelter}


def internals_by_relay(gr, suit, w, nodes, views, shelters) -> list:
    """Each node's two internal walks, with their longest shadow and worst shelter per relay."""
    out = []
    for nd in nodes:
        a, b, c = nd["points"]
        legs = []
        for p, q in ((a, b), (b, c)):
            path = g.astar(gr, suit, w, p, q) if gr.passable[p] and gr.passable[q] else None
            if path is None:
                legs = None
                break
            pts = g.smooth(gr, suit, w, path.path)
            if len(pts) < 2:
                pts = [p, q]
            rr, cc, t = path_samples(gr, suit, w, pts)
            legs.append(
                {
                    "path": pts,
                    "metrics": g.polyline_metrics(gr, suit, w, pts),
                    "shadow": [longest_shadow(v[rr, cc], t) for v in views],
                    "shelter": [float(s[rr, cc].max()) for s in shelters],
                }
            )
        out.append(legs)
    return out


def switches(gr, nodes, rel: dict, service_min: float, antenna: float) -> np.ndarray:
    """ok[t, ra, rb]: the rover may move from relay ra to rb while the crew works the last
    station of transect t (0-based)."""
    R = len(rel["cells"])
    T = len(nodes)
    ok = np.zeros((T, R, R), dtype=bool)
    tr_ = Affine(gr.res, 0, 0, 0, -gr.res, 0)
    for ra in range(R):
        for rb in range(R):
            if ra == rb:
                ok[:, ra, rb] = True
                continue
            drive = float(rel["times"][ra].minutes[rel["cells"][rb]])
            path = relay.drive_path(rel["times"][ra], rel["cells"][rb])[::5] + [rel["cells"][rb]]
            for t, nd in enumerate(nodes):
                st = nd["points"][-1]

                def sight(rover_rc, station_rc):
                    return los.line_of_sight(gr.z, tr_, _xy(rover_rc, gr.res),
                                             _xy(station_rc, gr.res), antenna, 1.8)  # fmt: skip

                ok[t, ra, rb] = relay.switch_feasible(drive, service_min, path, st, sight)
    return ok


def relay_fields(gr, suit, cells, views, walk, rover_ok):
    """Per relay: C_home to it on the preset's grid, walking minutes to it (`walk`, computed on
    every walkable cell, since in an emergency the crew may cross any of them) and comms."""
    out = []
    for rc, v, wk in zip(cells, views, walk, strict=True):
        home = g.dijkstra(gr, suit, CONSUMABLES, [rc], reverse=True).consumables
        out.append(cs.Fields(gr, home, wk, v, rover_ok))
    return out


def walk_fields(gr, suit, cells, rover_s: float) -> list:
    """Walking-time fields to each relay (reversed graph, every walkable cell); each Field's
    dose accumulates S x dt along the walk, for storm mode."""
    return [g.dijkstra(gr, suit, TIME_ONLY, [tuple(c)], reverse=True, tie_break=[rover_s])
            for c in cells]  # fmt: skip


def rover_track(rel: dict, r: int, step_min: float) -> list[tuple[float, tuple[int, int]]]:
    """(minutes since the start, cell) of the rover driving from the staging point to relay r,
    every `step_min` minutes of the drive, ending at the relay."""
    path = relay.drive_path(rel["times"][0], rel["cells"][r])
    if not path:
        return []
    mins = rel["times"][0].minutes
    out, nxt = [], 0.0
    for c in path:
        tt = float(mins[c])
        if tt >= nxt - 1e-9:
            out.append((tt, c))
            nxt = tt + step_min
    if out[-1][1] != tuple(rel["cells"][r]):
        out.append((float(mins[rel["cells"][r]]), tuple(rel["cells"][r])))
    return out


def moving_rover_fields(gr, suit, rel: dict, walks: list, step_min: float = 0.5) -> dict:
    """For each relay r the rover may drive to during the first leg: the sample times of its
    drive and the walking-minute field to the rover at each sample."""
    out = {}
    for r in range(1, len(rel["cells"])):
        track = rover_track(rel, r, step_min)
        if not track:
            continue
        fields = []
        for k, (_tt, c) in enumerate(track):
            if k == 0:
                fields.append(walks[0])
            elif k == len(track) - 1:
                fields.append(walks[r])
            else:
                f = g.dijkstra(gr, suit, TIME_ONLY, [c], reverse=True)
                fields.append(f.time.astype(np.float32))
        out[r] = (np.array([x[0] for x in track]), fields)
    return out


def moving_shelter(rr, cc, t, mv) -> np.ndarray:
    """Walking minutes to the rover at each sample (rr, cc, t) of a first leg during which the
    rover drives: the larger of the two rover samples around time t (half a minute apart), then
    the relay's field once the rover has arrived."""
    return np.array([cs.rover_walk_at(mv, (r, c), tt) for r, c, tt in zip(rr, cc, t, strict=True)])


def switch_shelter(gr, suit, nodes, rel: dict) -> np.ndarray:
    """sh[t, ra, rb]: the longest walk from transect t's last station to any point of the
    rover's drive from relay ra to rb (the rover drives while the crew works that station)."""
    R = len(rel["cells"])
    sh = np.zeros((len(nodes), R, R))
    paths = {(ra, rb): relay.drive_path(rel["times"][ra], rel["cells"][rb])
             for ra in range(R) for rb in range(R) if ra != rb}  # fmt: skip
    for t, nd in enumerate(nodes):
        f = g.dijkstra(gr, suit, TIME_ONLY, [nd["points"][-1]]).time
        for (ra, rb), path in paths.items():
            sh[t, ra, rb] = max(float(f[c]) for c in path) if path else np.inf
    return sh


def pairs_for(nodes, views) -> list[tuple[int, int]]:
    """(transect index, relay index) pairs, 1-based transects, where the relay sees all three."""
    return [
        (t + 1, r)
        for t, nd in enumerate(nodes)
        for r, v in enumerate(views)
        if relay.sees_transect(v, nd["points"])
    ]


def build_problem(m, nodes, pairs, rel, ok_switch, sc, lim, suit, lam, objective, eva=None,
                  cons_total=None):  # fmt: skip
    """The routing problem: node 0 = start (staging), 1..P = pairs, P + 1 = END (the walk ends
    at the rover's relay)."""
    T = len(nodes)
    P = len(pairs)
    n = P + 2
    END = P + 1
    INF = np.inf
    mins = np.full((n, n), INF)
    cons = np.full((n, n), INF)
    cost = np.full((n, n), INF)
    shadow_max, shelter_max = lim["comm_shadow_max_min"], lim["shelter_max_min"]

    def leg_ok(s, tgt, r):
        return (
            np.isfinite(m["minutes"][s, tgt])
            and m["shadow"][r, s, tgt] <= shadow_max
            and m["shelter"][r, s, tgt] <= shelter_max
        )

    def put(a, b, s, tgt):
        mins[a, b], cons[a, b], cost[a, b] = (
            m["minutes"][s, tgt],
            m["consumables"][s, tgt],
            m["cost"][s, tgt],
        )

    drive0 = rel["drive_from_staging_min"]
    for b, (tb, rb) in enumerate(pairs, start=1):
        if leg_ok(0, tb - 1, rb) and drive0[rb] <= m["minutes"][0, tb - 1] + 1e-9:
            put(0, b, 0, tb - 1)
    for a, (ta, ra) in enumerate(pairs, start=1):
        for b, (tb, rb) in enumerate(pairs, start=1):
            if ta == tb:
                continue
            if leg_ok(ta, tb - 1, rb) and ok_switch[ta - 1, ra, rb]:
                put(a, b, ta, tb - 1)
        if leg_ok(ta, T + ra, ra):
            put(a, END, ta, T + ra)
    mins[0, END] = cons[0, END] = cost[0, END] = 0.0
    np.fill_diagonal(mins, 0.0)
    np.fill_diagonal(cons, 0.0)
    np.fill_diagonal(cost, 0.0)
    svc = [tr.node_service([lg["metrics"] for lg in m["internal"][t - 1]], sc["service_min"],
                           suit.station_rate_ratio) for t, _ in pairs]  # fmt: skip
    values = np.array([nodes[t - 1]["value"] for t, _ in pairs]) if pairs else np.zeros(0)
    obj = tr.objective_values(values, objective) if pairs else values
    groups: dict[int, list[int]] = {}
    for i, (t, _) in enumerate(pairs, start=1):
        groups.setdefault(t, []).append(i)
    eva = sc["eva_max_min"] if eva is None else eva
    cons_total = sc["consumables_total_min"] if cons_total is None else cons_total
    return select.Problem(
        value=np.r_[0.0, obj, 0.0],
        service_min=np.r_[0.0, [s["minutes"] for s in svc], 0.0],
        service_cons=np.r_[0.0, [s["consumables"] for s in svc], 0.0],
        minutes=mins,
        consumables=cons,
        cost=cost,
        eva_max_min=eva,
        consumables_budget=cons_total - lim["reserve_min"] - cs.DISCRETISATION_MARGIN_MIN,
        value_weight=lam,
        groups=list(groups.values()),
        end_node=END,
    )


def usable_pairs(m, nodes, pairs, lim) -> list[tuple[int, int]]:
    """Pairs whose internal walks exist and keep the limits under their relay."""
    out = []
    for t, r in pairs:
        legs = m["internal"][t - 1]
        if legs is None:
            continue
        if all(lg["shadow"][r] <= lim["comm_shadow_max_min"] and
               lg["shelter"][r] <= lim["shelter_max_min"] for lg in legs):  # fmt: skip
            out.append((t, r))
    return out


def expand(m, nodes, pairs, route, fields_r):
    """Legs, stations, per-leg fields and station info of a node route [0, ..., END]. Leg k
    ends at station k; station info carries the relay the rover is parked at for it."""
    T = len(nodes)
    legs, lf, stations, info = [], [], [], []
    prev = 0
    seq = [pairs[i - 1] for i in route[1:-1]]
    for t, r in seq:
        legs.append(m["paths"][(prev, t - 1)])
        lf.append(fields_r[r])
        nd = nodes[t - 1]
        for k, (cell, role) in enumerate(zip(nd["points"], nd["roles"], strict=True)):
            if k > 0:
                legs.append(m["internal"][t - 1][k - 1]["path"])
                lf.append(fields_r[r])
            stations.append(cell)
            info.append({"transect": nd["transect"], "role": role, "node": t, "relay": r})
        prev = t
    r_end = seq[-1][1] if seq else 0
    if prev != 0:
        legs.append(m["paths"][(prev, T + r_end)])
        lf.append(fields_r[r_end])
    return legs, lf, stations, info, seq, r_end


def schedule(seq, rel) -> list[dict]:
    """The rover's moves: where it parks for each transect and when it drives."""
    out = []
    cur = 0
    for k, (_t, r) in enumerate(seq):
        if r != cur:
            drive = float(rel["times"][cur].minutes[rel["cells"][r]])
            out.append({"before_transect": k + 1, "from_relay": cur, "to_relay": r,
                        "drive_min": round(drive, 2),
                        "when": "during the first leg" if k == 0 else
                        "during the last station of the previous transect"})  # fmt: skip
            cur = r
    return out


def moving(seq, info, sw_shelter, mv):
    """Where the rover drives: walking minutes to it during each station visit at which it moves
    (None elsewhere), and its first-leg track if it drives during the first leg."""
    visit = [None] * len(info)
    for k in range(len(info) - 1):
        a, b = info[k], info[k + 1]
        if a["node"] != b["node"] and a["relay"] != b["relay"] and sw_shelter is not None:
            visit[k] = float(sw_shelter[a["node"] - 1, a["relay"], b["relay"]])
    first = None
    if seq and seq[0][1] != 0 and mv is not None:
        first = mv.get(seq[0][1])
    return visit, first


def check(fields_r, suit, w, m, nodes, pairs, route, sc, lim, cons_total, sw_shelter=None,
          mv=None):  # fmt: skip
    legs, lf, stations, info, seq, r_end = expand(m, nodes, pairs, route, fields_r)
    if not legs:
        return None, legs, stations, info, seq, r_end, lf
    visit, first = moving(seq, info, sw_shelter, mv)
    res = cs.check_route(lf[0], suit, w, legs, stations, sc["service_min"],
                         sc["service_min"] * suit.station_rate_ratio, cons_total, lim,
                         buddy_ok=[True] * len(stations), leg_fields=lf,
                         visit_shelter=visit, first_leg_rover=first)  # fmt: skip
    return res, legs, stations, info, seq, r_end, lf
