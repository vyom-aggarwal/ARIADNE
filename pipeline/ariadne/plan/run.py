# Written with AI assistance (Claude Code). See AI_USE.md.
"""`ariadne plan`: fields, candidate stations, leg matrices, reference plans and checks.

Reads the derived layers of a site, builds the 2 m planning grid around the staging point, and
writes (data/sites/<site>/plan/, not committed) the fields and the leg bundle for the browser,
plus (committed) one plan.json per preset in docs/plan/, the browser solver's benchmark fixture
in web/tests/fixtures/, and the report docs/plan/<site>.md.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from affine import Affine

from ariadne import __version__ as PIPELINE_VERSION
from ariadne.config import config_dir, load_derive_config, setting
from ariadne.derive.io import read_raster, write_layer
from ariadne.guardrails import repo_root
from ariadne.labels import Label
from ariadne.models import metabolic as mb
from ariadne.plan import constraints as cs
from ariadne.plan import graph as g
from ariadne.plan import select
from ariadne.plan import transects as tr

CONSUMABLES = {"time": 0.0, "metabolic": 1.0, "hazard": 0.0, "dose": 0.0, "uncertainty": 0.0}
TIME_ONLY = {"time": 1.0, "metabolic": 0.0, "hazard": 0.0, "dose": 0.0, "uncertainty": 0.0}
WALKER_NOGO, NODATA = 2, 255


def load_presets() -> dict:
    return json.loads((config_dir() / "presets.json").read_text(encoding="utf-8"))


def scenario_values(presets: dict) -> dict:
    return {k: float(v["value"]) for k, v in presets["scenario"].items()}


def block(a: np.ndarray, k: int, how: str) -> np.ndarray:
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    b = a[:h, :w].reshape(h // k, k, w // k, k)
    if how == "mean":
        return b.mean(axis=(1, 3))
    if how == "max":
        return b.max(axis=(1, 3))
    if how == "any":
        return b.any(axis=(1, 3))
    if how == "all":
        return b.all(axis=(1, 3))
    raise ValueError(how)


def planning_grid(site_dir: Path, staging_xy, half_m: float, k: int):
    """2 m layers (k x k blocks of the 1 m layers) in a square window around the staging point."""
    d = site_dir / "derived"
    dem, t, crs = read_raster(site_dir / "dem.tif")
    r0 = int((staging_xy[1] - t.f) / t.e - half_m)
    c0 = int((staging_xy[0] - t.c) / t.a - half_m)
    r0, c0 = max(0, r0), max(0, c0)
    r1 = min(dem.shape[0], r0 + int(2 * half_m))
    c1 = min(dem.shape[1], c0 + int(2 * half_m))
    win = (slice(r0, r1), slice(c0, c1))

    def lay(name, as_float=True):
        a, _, _ = read_raster(d / name, as_float=as_float)
        return a[win]

    z = block(dem[win].astype(np.float64), k, "mean")
    walker = block(lay("walk_class_walker.tif", False).astype(np.int16), k, "max")
    rover = lay("walk_class_rover.tif", False)
    cost = lay("walk_cost_walker.tif")
    hazard = block(np.where(np.isfinite(cost), cost - 1.0, 0.0), k, "mean")
    s = block(np.nan_to_num(lay("shielding.tif"), nan=1.0), k, "mean")
    conf = block(np.nan_to_num(lay("confidence.tif"), nan=0.0), k, "mean")
    shelters = block(lay("shelters.tif", False) > 0, k, "any")
    view = block(lay("viewshed_staging.tif", False) > 0, k, "all")
    t2 = Affine(t.a * k, 0, t.c + c0 * t.a, 0, t.e * k, t.f + r0 * t.e)
    passable = np.isfinite(z) & (walker != WALKER_NOGO) & (walker != NODATA)
    grid = g.Grid(np.nan_to_num(z, nan=0.0), passable, np.clip(hazard, 0, None), s, 1.0 - conf,
                  abs(t2.a))  # fmt: skip
    rover_rc = (int((staging_xy[1] - t.f) / t.e) - r0, int((staging_xy[0] - t.c) / t.a) - c0)
    rover_ok = bool(0 <= rover_rc[0] < rover.shape[0] and 0 <= rover_rc[1] < rover.shape[1]
                    and rover[rover_rc] in (0, 1))  # fmt: skip
    return grid, t2, crs, {"shelters": shelters, "comms": view, "rover_ok": rover_ok}


def xy_to_rc(t: Affine, x, y):
    return int(np.floor((y - t.f) / t.e)), int(np.floor((x - t.c) / t.a))


def rc_to_xy(t: Affine, r, c):
    return [round(float(t.c + (c + 0.5) * t.a), 2), round(float(t.f + (r + 0.5) * t.e), 2)]


def transect_candidates(features, gr, t2, staging_rc, fields: cs.Fields, sc, log) -> list[dict]:
    """Whole transects whose three points are all within reach, walkable, in comms line of sight
    and have an overwatch point; the `candidate_transects` with the highest science value."""
    groups: dict[int, list] = {}
    for f in features:
        if f["geometry"]["type"] != "Point" or "score" not in f["properties"]:
            continue
        p = f["properties"]
        x, y = f["geometry"]["coordinates"][:2]
        groups.setdefault(int(p["transect"]), []).append(
            (p["role"], xy_to_rc(t2, x, y), float(p["score"]))
        )
    h, w = gr.z.shape
    max_d = sc["max_station_distance_m"]
    rejected = {"incomplete": 0, "far": 0, "outside": 0, "unwalkable": 0, "no comms": 0,
                "no overwatch": 0}  # fmt: skip
    ranked = []
    for tid, pts in groups.items():
        o = tr.order_transect(pts)
        if o is None:
            rejected["incomplete"] += 1
            continue
        ranked.append((sum(o[2]), tid, o))
    ranked.sort(key=lambda r: -r[0])
    out = []
    for value, tid, (roles, cells, scores) in ranked:
        reason = None
        for r, c in cells:
            if np.hypot(r - staging_rc[0], c - staging_rc[1]) * gr.res > max_d:
                reason = "far"
            elif not (0 <= r < h and 0 <= c < w):
                reason = "outside"
            elif not gr.passable[r, c] or not np.isfinite(fields.c_home[r, c]):
                reason = "unwalkable"
            elif not fields.comms[r, c]:
                reason = "no comms"
            if reason:
                break
        ows = []
        if reason is None:
            for cell in cells:
                ow = cs.overwatch_point(gr, cell, sc["buddy_max_m"], sc["buddy_min_m"],
                                        sc["helmet_height_m"])  # fmt: skip
                if ow is None:
                    reason = "no overwatch"
                    break
                ows.append(ow)
        if reason:
            rejected[reason] += 1
            continue
        out.append(
            {
                "transect": tid,
                "points": [tuple(map(int, c)) for c in cells],
                "roles": roles,
                "scores": scores,
                "value": float(value),
                "xy_m": [rc_to_xy(t2, *c) for c in cells],
                "overwatch_xy_m": [rc_to_xy(t2, *o["cell"]) for o in ows],
                "overwatch_distance_m": [round(o["distance_m"], 1) for o in ows],
            }
        )
        if len(out) >= int(sc["candidate_transects"]):
            break
    log(f"  candidate transects: {len(out)} kept; rejected {rejected}")
    return out


def leg_extras(gr, suit, w, paths, fields: cs.Fields, shape) -> dict:
    """Longest comm shadow and worst minutes to shelter along each smoothed leg."""
    shadow = np.zeros(shape)
    shelter = np.zeros(shape)
    for key, pts in paths.items():
        shadow[key], shelter[key] = path_extras(gr, suit, w, pts, fields)
    return {"shadow_max_min": shadow, "shelter_max_min": shelter}


def path_extras(gr, suit, w, pts, fields: cs.Fields) -> tuple[float, float]:
    s = cs.route_samples(gr, suit, w, [pts], [], 0.0, 0.0)
    start, longest, worst = None, 0.0, 0.0
    for smp in s:
        rc = cs._cell(gr, smp["r"], smp["c"])
        worst = max(worst, float(fields.shelter_min[rc]))
        if not fields.comms[rc]:
            start = smp["t"] if start is None else start
            longest = max(longest, smp["t"] - start)
        else:
            start = None
    return longest, worst


def node_internals(gr, suit, w, nodes, fields: cs.Fields) -> list:
    """For each transect node, its two internal walks (fracture or crest to wall, wall to
    hollow): smoothed paths, metrics, and the longest shadow and worst shelter time on them.
    None where a walk is impossible on this grid."""
    out = []
    for nd in nodes:
        a, b, c = nd["points"]
        legs = []
        for p, q in ((a, b), (b, c)):
            if not (gr.passable[p] and gr.passable[q]):
                legs = None
                break
            path = g.astar(gr, suit, w, p, q)
            if path is None:
                legs = None
                break
            pts = g.smooth(gr, suit, w, path.path)
            if len(pts) < 2:  # both points in one planning cell
                pts = [p, q]
            met = g.polyline_metrics(gr, suit, w, pts)
            sh, sl = path_extras(gr, suit, w, pts, fields)
            legs.append({"path": pts, "metrics": met, "shadow": sh, "shelter": sl})
        out.append(legs)
    return out


def cached_node_legs(path: Path, gr, suit, w, staging, nodes, fields, log) -> dict:
    """Leg matrix (staging and node exits to staging and node entries), per-leg extras and the
    nodes' internal walks, reused from `path` when every input is the same."""
    import hashlib
    import pickle

    key = hashlib.sha256(
        json.dumps(
            {"staging": list(map(int, staging)), "nodes": [n["points"] for n in nodes], "w": w,
             "suit": suit.__dict__, "shape": list(gr.z.shape), "res": gr.res,
             "version": PIPELINE_VERSION, "cache_format": 2},
            sort_keys=True,
        ).encode()
        + gr.z.tobytes() + gr.passable.tobytes() + gr.hazard.tobytes() + gr.dose.tobytes()
        + gr.unc.tobytes() + fields.comms.tobytes() + fields.shelter_min.tobytes()
    ).hexdigest()  # fmt: skip
    if path.exists():
        with path.open("rb") as f:
            saved = pickle.load(f)
        if saved.get("key") == key:
            log(f"  legs: reusing {path.name}")
            return saved["m"]
    sources = [staging] + [n["points"][-1] for n in nodes]
    targets = [staging] + [n["points"][0] for n in nodes]
    m = g.leg_matrix_st(gr, suit, w, sources, targets)
    m.update(leg_extras(gr, suit, w, m["paths"], fields, m["minutes"].shape))
    m["internal"] = node_internals(gr, suit, w, nodes, fields)
    with path.open("wb") as f:
        pickle.dump({"key": key, "m": m}, f)
    return m


def node_ok(m, k: int, limits: dict) -> bool:
    """Node k (1-based) is usable: both internal walks exist and keep the limits."""
    legs = m["internal"][k - 1]
    return legs is not None and all(
        lg["shadow"] <= limits["comm_shadow_max_min"] and lg["shelter"] <= limits["shelter_max_min"]
        for lg in legs
    )


def problem_for(
    m: dict,
    idx: list[int],
    nodes: list,
    sc: dict,
    limits: dict,
    suit: mb.Suit,
    lam: float,
    objective: str = "value",
    eva: float | None = None,
    cons_total: float | None = None,
) -> select.Problem:
    """The routing problem over the nodes in `idx` (0 = staging first)."""
    ix = np.array(idx)
    eva = sc["eva_max_min"] if eva is None else eva
    cons_total = sc["consumables_total_min"] if cons_total is None else cons_total
    svc = [tr.node_service([lg["metrics"] for lg in m["internal"][k - 1]], sc["service_min"],
                           suit.station_rate_ratio) for k in idx[1:]]  # fmt: skip
    bad = (m["shadow_max_min"] > limits["comm_shadow_max_min"]) | (
        m["shelter_max_min"] > limits["shelter_max_min"]
    )
    values = np.array([nodes[k - 1]["value"] for k in idx[1:]])
    return select.Problem(
        value=np.r_[0.0, tr.objective_values(values, objective)],
        service_min=np.r_[0.0, [s["minutes"] for s in svc]],
        service_cons=np.r_[0.0, [s["consumables"] for s in svc]],
        minutes=np.where(bad, np.inf, m["minutes"])[np.ix_(ix, ix)],
        consumables=m["consumables"][np.ix_(ix, ix)],
        cost=m["cost"][np.ix_(ix, ix)],
        eva_max_min=eva,
        consumables_budget=cons_total - limits["reserve_min"] - cs.DISCRETISATION_MARGIN_MIN,
        value_weight=lam,
    )


def expanded(m, route: list[int], nodes: list):
    """Legs and stations of a node route, with each transect's internal walks."""
    internal = {k: [lg["path"] for lg in m["internal"][k - 1]] for k in route[1:-1]}
    return tr.expand_route(route, nodes, m["paths"], internal)


def check_plan(fields, suit, w, m, route, nodes, sc, limits, cons_total, staging_rc):
    legs, stations, info = expanded(m, route, nodes)
    res = cs.check_route(
        fields, suit, w, legs or [[staging_rc, staging_rc]], stations, sc["service_min"],
        sc["service_min"] * suit.station_rate_ratio, cons_total, limits,
        buddy_ok=[True] * len(stations),
    )  # fmt: skip
    return res, legs, stations, info


def plan_json(site, preset, pr, route, nodes, m, legs, info, gr, suit, t2, res, sc, limits,
              inputs) -> dict:  # fmt: skip
    ids = []
    stations = []
    for n_, inf in enumerate(info, start=1):
        nd = nodes[inf["node"] - 1]
        k = nd["roles"].index(inf["role"])
        sid = f"S{n_:02d}"
        ids.append(sid)
        stations.append(
            {
                "id": sid,
                "role": inf["role"],
                "transect": f"T{route[1:-1].index(inf['node']) + 1:02d}",
                "transect_source_id": nd["transect"],
                "xy_m": nd["xy_m"][k],
                "value": round(nd["scores"][k], 4),
                "service_min": sc["service_min"],
                "label": "MODELED",
                "overwatch_xy_m": nd["overwatch_xy_m"][k],
                "overwatch_distance_m": nd["overwatch_distance_m"][k],
            }
        )
    chain = ["STAGING", *ids, "STAGING"]
    out_legs = []
    for k, pts in enumerate(legs):
        met = g.polyline_metrics(gr, suit, pr["weights"], pts)
        out_legs.append(
            {
                "from": chain[k],
                "to": chain[k + 1],
                "path_xy_m": [rc_to_xy(t2, r, c) for r, c in pts],
                "minutes": round(met["minutes"], 3),
                "consumables_min": round(met["consumables"], 3),
                "relative_dose": round(met["dose"], 4),
                "within_transect": bool(
                    0 < k < len(stations)
                    and stations[k - 1]["transect"] == stations[k]["transect"]
                ),
            }
        )  # fmt: skip
    for x in res["margins"]:
        r, c = x.pop("xy_cell")
        x["xy_m"] = rc_to_xy(t2, r, c)
    n_tr = len(route) - 2
    return {
        "site": site,
        "scenario": {
            "start_utc": None,
            "preset": preset,
            "suit_profile": "default",
            "rover_profile": "default",
            "eva_max_min": sc["eva_max_min"],
            "consumables_total_min": sc["consumables_total_min"],
            "reserve_min": limits["reserve_min"],
            "shelter_max_min": limits["shelter_max_min"],
            "weights": pr["weights"],
            "objective": pr["objective"],
            "label": "PLACEHOLDER",
        },
        "stations": stations,
        "legs": out_legs,
        "margins": res["margins"],
        "checks": res["checks"],
        "totals": {
            "transects": n_tr,
            "stations": len(stations),
            "science_value": round(sum(nodes[k - 1]["value"] for k in route[1:-1]), 4),
            "minutes": res["details"]["minutes"],
            "consumables_min": res["details"]["consumables"],
            "relative_dose_min": res["details"]["relative_dose"],
            "distance_m": res["details"]["metres"],
            "min_thread_margin_min": res["details"]["thread_min_margin_min"],
            "worst_minutes_to_shelter": res["details"]["worst_minutes_to_shelter"],
            "longest_comm_shadow_min": res["details"]["longest_comm_shadow_min"],
            "label": "MODELED",
        },
        "walker_model": {
            "label": "MODELED with PLACEHOLDER suit settings",
            "extrapolated": True,
            "note": "Minetti et al. 2002 cost of walking with a PLACEHOLDER suit and gravity "
            "factor; Mars gravity is outside NASA/TP-2010-216125's tested range.",
        },
        "provenance": {"pipeline_version": PIPELINE_VERSION, "inputs": inputs},
    }


def validate_plan(plan: dict) -> None:
    import jsonschema

    schema = json.loads((config_dir() / "schemas" / "plan.schema.json").read_text("utf-8"))
    jsonschema.validate(plan, schema)


def thread_scenarios(m, nodes, usable, fields, gr, suit, w, sc, limits, n, seed, log) -> dict:
    """Plan n random scenarios (transect subsets and budgets) and check the thread on each."""
    rng = np.random.default_rng(seed)
    fails, worst, visited = 0, np.inf, 0
    pool = np.array(usable)
    for _ in range(n):
        k = int(rng.integers(1, len(pool) + 1))
        idx = [0, *sorted(rng.choice(pool, k, replace=False).tolist())]
        total = float(rng.uniform(150, 450))
        p = problem_for(m, idx, nodes, sc, limits, suit, 1e6, eva=float(rng.uniform(120, 420)),
                        cons_total=total)  # fmt: skip
        sol = select.solve(p, first_solution_only=True)
        route = [idx[r] for r in sol.route]
        visited += len(route) - 2
        if len(route) <= 2:
            continue
        res, *_ = check_plan(fields, suit, w, m, route, nodes, sc, limits, total, None)
        fails += res["checks"]["thread"] != "pass"
        worst = min(worst, res["details"]["thread_min_margin_min"])
    log(f"  thread: {n - fails} of {n} random scenarios hold (worst margin {worst:.2f} min)")
    return {
        "scenarios": n,
        "held": n - fails,
        "worst_margin_min": round(float(worst), 3),
        "mean_transects_visited": round(visited / n, 2),
        "seed": seed,
    }


def bench_fixture(m, nodes, usable, sc, limits, suit, n, seed, time_limit, log) -> dict:
    """Random scenarios solved by OR-Tools (time-limited), for the browser solver's benchmark."""
    rng = np.random.default_rng(seed)
    scen = []
    pool = np.array(usable)
    for _ in range(n):
        k = int(rng.integers(min(8, len(pool)), len(pool) + 1))
        idx = [0, *sorted(rng.choice(pool, k, replace=False).tolist())]
        eva = float(rng.uniform(120, 420))
        total = float(rng.uniform(150, 450))
        p = problem_for(m, idx, nodes, sc, limits, suit, 1e6, eva=eva, cons_total=total)
        sol = select.solve(p, time_limit_s=time_limit)
        scen.append(
            {
                "nodes": idx,
                "eva_max_min": round(eva, 3),
                "consumables_budget": round(p.consumables_budget, 3),
                "ortools_route": [idx[r] for r in sol.route],
                "ortools_value": round(sol.value, 6),
            }
        )
    log(f"  benchmark: {n} OR-Tools scenarios")
    svc_min = [0.0] + [
        tr.node_service([lg["metrics"] for lg in m["internal"][k]], sc["service_min"],
                        suit.station_rate_ratio)["minutes"] if m["internal"][k] else None
        for k in range(len(nodes))
    ]  # fmt: skip
    svc_cons = [0.0] + [
        tr.node_service([lg["metrics"] for lg in m["internal"][k]], sc["service_min"],
                        suit.station_rate_ratio)["consumables"] if m["internal"][k] else None
        for k in range(len(nodes))
    ]  # fmt: skip
    bad = (m["shadow_max_min"] > limits["comm_shadow_max_min"]) | (
        m["shelter_max_min"] > limits["shelter_max_min"]
    )

    def mat(a):
        return [[None if not np.isfinite(v) else round(float(v), 4) for v in row] for row in a]

    return {
        "_about": "Browser solver benchmark (test D11): OR-Tools reference plans, with a "
        f"{time_limit:g} s guided local search per scenario (a time-limited reference, not a "
        "proven optimum), on random subsets of the boxwork transect nodes, Balanced legs. "
        "Generated by ariadne plan.",
        "pipeline_version": PIPELINE_VERSION,
        "ortools_time_limit_s": time_limit,
        "service_min": [None if v is None else round(v, 4) for v in svc_min],
        "service_consumables_min": [None if v is None else round(v, 4) for v in svc_cons],
        "values": [0.0] + [round(nd["value"], 6) for nd in nodes],
        "minutes": mat(np.where(bad, np.inf, m["minutes"])),
        "consumables": mat(m["consumables"]),
        "cost": mat(m["cost"]),
        "scenarios": scen,
    }


def preset_limits(sc: dict, pr: dict) -> dict:
    lim = {k: sc[k] for k in ("reserve_min", "shelter_max_min", "comm_shadow_max_min",
                              "sample_step_m")}  # fmt: skip
    lim.update({k: float(v) for k, v in pr.get("limits", {}).items()})
    return lim


def plan_site(site: str = "boxwork", log=print, quick: bool = False) -> dict:
    t0 = time.time()
    root = repo_root()
    site_dir = root / "data" / "sites" / site
    out = site_dir / "plan"
    out.mkdir(parents=True, exist_ok=True)
    presets = load_presets()
    sc = scenario_values(presets)
    suit = mb.load_suit()
    summary_d = json.loads((site_dir / "derived" / "summary.json").read_text(encoding="utf-8"))
    staging_xy = summary_d["shelters"]["staging_xy"]
    k = int(round(sc["planning_resolution_m"]))
    half = sc["max_station_distance_m"] + sc["grid_margin_m"]
    log(f"Planning {site}: staging at E {staging_xy[0]:.1f} N {staging_xy[1]:.1f}")
    gr0, t2, crs, extra = planning_grid(site_dir, staging_xy, half, k)
    staging_rc = xy_to_rc(t2, *staging_xy)
    if not gr0.passable[staging_rc]:
        raise RuntimeError("the staging point is not walkable on the planning grid")
    cfg = load_derive_config()
    rover_s = float(setting(cfg, "shielding", "rover_shelter_s"))
    # minutes to shelter (terrain shelters and the rover) and storm pointers
    sh_cells = np.argwhere(extra["shelters"] & gr0.passable)
    sources = [tuple(x) for x in sh_cells] + [staging_rc]
    ties = [float(gr0.dose[tuple(x)]) for x in sh_cells] + [rover_s]
    storm = g.dijkstra(gr0, suit, TIME_ONLY, sources, reverse=True, tie_break=ties)

    def fields_for(shelter_max):
        passable = gr0.passable & (storm.time <= shelter_max)
        grid = g.Grid(gr0.z, passable, gr0.hazard, gr0.dose, gr0.unc, gr0.res)
        home = g.dijkstra(grid, suit, CONSUMABLES, [staging_rc], reverse=True)
        return cs.Fields(grid, home.consumables, storm.time, extra["comms"], extra["rover_ok"])

    limits = {name: preset_limits(sc, pr) for name, pr in presets["presets"].items()}
    loosest = max(lim["shelter_max_min"] for lim in limits.values())
    fields = {s: fields_for(s) for s in sorted({lim["shelter_max_min"] for lim in limits.values()})}
    f_loose = fields[loosest]
    log(f"  fields ready ({time.time() - t0:.0f} s)")
    common = dict(resolution_m=gr0.res, inputs=["derived layers"])
    home = f_loose.c_home
    for name, arr, pid in (
        ("c_home.tif", np.where(np.isfinite(home), home, np.nan),
         "Consumables to walk back to the staging point, minutes at the nominal rate"),
        ("shelter_minutes.tif", np.where(np.isfinite(storm.time), storm.time, np.nan),
         "Walking minutes to the nearest shelter or the rover"),
        ("storm_pointer.tif", storm.pred.astype(np.int16),
         "Storm mode: index of the next move toward the earliest shelter (-1 at shelters)"),
    ):  # fmt: skip
        write_layer(out / name, arr.astype(np.float32 if arr.dtype != np.int16 else np.int16),
                    t2, crs, None, product_id=pid, label=Label.MODELED,
                    notes="Walker model with PLACEHOLDER suit settings.", **common)  # fmt: skip
    transects = json.loads((site_dir / "derived" / "transects.geojson").read_text("utf-8"))
    nodes = transect_candidates(transects["features"], f_loose.grid, t2, staging_rc, f_loose,
                                sc, log)  # fmt: skip
    inputs = ["usgs-gale-dem-1m", "usgs-gale-ortho-25cm", "msl-places", "mola-dem-463m",
              "derived layers (docs/derived)"]  # fmt: skip
    mats, plans, usable_by = {}, {}, {}
    for name, pr in presets["presets"].items():
        w, lim = pr["weights"], limits[name]
        f = fields[lim["shelter_max_min"]]
        m = cached_node_legs(out / f"legs_{name}.pkl", f.grid, suit, w, staging_rc, nodes, f, log)
        mats[name] = m
        usable = [k_ for k_ in range(1, len(nodes) + 1) if node_ok(m, k_, lim)]
        usable_by[name] = usable
        p = problem_for(m, [0, *usable], nodes, sc, lim, suit, float(pr["value_weight"]),
                        pr["objective"])  # fmt: skip
        sol = select.solve(p, time_limit_s=3.0 if quick else 20.0)
        route = [[0, *usable][r] for r in sol.route]
        res, legs, stations, info = check_plan(f, suit, w, m, route, nodes, sc, lim,
                                               sc["consumables_total_min"], staging_rc)  # fmt: skip
        plan = plan_json(site, name, pr, route, nodes, m, legs, info, f.grid, suit, t2, res, sc,
                         lim, inputs)  # fmt: skip
        validate_plan(plan)
        plans[name] = plan
        log(f"  {name}: {len(route) - 2} transects ({len(stations)} stations) of {len(usable)} "
            f"usable, value {plan['totals']['science_value']:.2f}, "
            f"{res['details']['minutes']:.0f} min, checks {res['checks']}")  # fmt: skip
    bal = mats["balanced"]
    w_bal = presets["presets"]["balanced"]["weights"]
    f_bal = fields[limits["balanced"]["shelter_max_min"]]
    n_thread = 100 if quick else 1000
    lim_bal = limits["balanced"]
    thread = thread_scenarios(
        bal, nodes, usable_by["balanced"], f_bal, f_bal.grid, suit, w_bal, sc, lim_bal, n_thread,
        20261109, log,
    )  # fmt: skip
    bench = bench_fixture(bal, nodes, usable_by["balanced"], sc, limits["balanced"], suit,
                          10 if quick else 60, 1109, 0.5 if quick else 2.0, log)  # fmt: skip
    docs = root / "docs" / "plan"
    docs.mkdir(parents=True, exist_ok=True)
    for name, plan in plans.items():
        (docs / f"{site}-{name}.json").write_text(json.dumps(plan, indent=1) + "\n",
                                                  encoding="utf-8", newline="\n")  # fmt: skip
    fx = root / "web" / "tests" / "fixtures"
    fx.mkdir(parents=True, exist_ok=True)
    (fx / f"{site}-bench.json").write_text(json.dumps(bench) + "\n", encoding="utf-8",
                                           newline="\n")  # fmt: skip
    summary = {
        "site": site,
        "pipeline_version": PIPELINE_VERSION,
        "computed_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "grid": {"resolution_m": gr0.res, "shape": list(gr0.z.shape)},
        "staging_xy_m": staging_xy,
        "candidate_transects": len(nodes),
        "usable_transects": {n_: len(u) for n_, u in usable_by.items()},
        "walkable_share": round(float(gr0.passable.mean()), 4),
        "within_shelter_limit_share": {
            str(s): round(float(f_.grid.passable.sum() / max(1, gr0.passable.sum())), 4)
            for s, f_ in fields.items()
        },
        "comms_share": round(float(extra["comms"].mean()), 4),
        "rover_ok": extra["rover_ok"],
        "presets": {
            n_: {
                "weights": pr["weights"],
                "limits": limits[n_],
                "objective": pr["objective"],
                "value_weight": pr["value_weight"],
            }
            for n_, pr in presets["presets"].items()
        },  # fmt: skip
        "plans": {n_: p_["totals"] | {"checks": p_["checks"]} for n_, p_ in plans.items()},
        "thread": thread,
        "scenario": sc,
        "seconds": round(time.time() - t0),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8",
                                      newline="\n")  # fmt: skip
    from ariadne.plan.report import plan_markdown

    (docs / f"{site}.md").write_text(plan_markdown(summary), encoding="utf-8", newline="\n")
    log(f"  plan written ({summary['seconds']} s)")
    return summary
