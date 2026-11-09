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
from ariadne.config import config_dir
from ariadne.derive.io import read_raster, write_layer
from ariadne.guardrails import repo_root
from ariadne.labels import Label
from ariadne.models import metabolic as mb
from ariadne.plan import constraints as cs
from ariadne.plan import graph as g
from ariadne.plan import relay as rl
from ariadne.plan import relay_plan as rp
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
    rover_cls = block(rover.astype(np.int16), k, "max")
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
    return (
        grid,
        t2,
        crs,
        {"shelters": shelters, "comms": view, "rover_ok": rover_ok, "rover_cls": rover_cls},
    )


def xy_to_rc(t: Affine, x, y):
    return int(np.floor((y - t.f) / t.e)), int(np.floor((x - t.c) / t.a))


def rc_to_xy(t: Affine, r, c):
    return [round(float(t.c + (c + 0.5) * t.a), 2), round(float(t.f + (r + 0.5) * t.e), 2)]


def transect_candidates(
    features, gr, t2, staging_rc, fields: cs.Fields, sc, log, limit=None, check_comms=True
) -> list[dict]:
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
            elif check_comms and not fields.comms[r, c]:
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
        if len(out) >= int(limit or sc["candidate_transects"]):
            break
    log(f"  candidate transects: {len(out)} kept; rejected {rejected}")
    return out


def preset_limits(sc: dict, pr: dict) -> dict:
    lim = {k: sc[k] for k in ("reserve_min", "shelter_max_min", "comm_shadow_max_min",
                              "sample_step_m")}  # fmt: skip
    lim.update({k: float(v) for k, v in pr.get("limits", {}).items()})
    return lim


def cached_relay_legs(path: Path, gr, suit, w, staging, nodes, rel, shelters, log) -> dict:
    """Leg matrix (staging and transect exits to transect entries and relay sites), per-leg
    shadow and shelter for every relay, and each transect's internal walks; reused from `path`
    when every input is the same."""
    import hashlib
    import pickle

    key = hashlib.sha256(
        json.dumps(
            {"staging": list(map(int, staging)), "nodes": [n["points"] for n in nodes],
             "relays": [list(map(int, c)) for c in rel["cells"]], "w": w,
             "suit": suit.__dict__, "shape": list(gr.z.shape), "res": gr.res,
             "version": PIPELINE_VERSION, "cache_format": 3},
            sort_keys=True,
        ).encode()
        + gr.z.tobytes() + gr.passable.tobytes() + gr.hazard.tobytes() + gr.dose.tobytes()
        + gr.unc.tobytes() + b"".join(v.tobytes() for v in rel["views"])
        + b"".join(s.tobytes() for s in shelters)
    ).hexdigest()  # fmt: skip
    if path.exists():
        with path.open("rb") as f:
            saved = pickle.load(f)
        if saved.get("key") == key:
            log(f"  legs: reusing {path.name}")
            return saved["m"]
    sources = [staging] + [n["points"][-1] for n in nodes]
    targets = [n["points"][0] for n in nodes] + list(rel["cells"])
    m = g.leg_matrix_st(gr, suit, w, sources, targets, same_node_diagonal=False)
    m.update(rp.leg_extras_by_relay(gr, suit, w, m["paths"], m["minutes"].shape, rel["views"],
                                    shelters))  # fmt: skip
    m["internal"] = rp.internals_by_relay(gr, suit, w, nodes, rel["views"], shelters)
    with path.open("wb") as f:
        pickle.dump({"key": key, "m": m}, f)
    return m


def validate_plan(plan: dict) -> None:
    import jsonschema

    schema = json.loads((config_dir() / "schemas" / "plan.schema.json").read_text("utf-8"))
    jsonschema.validate(plan, schema)


def plan_json(site, preset, pr, res, legs, info, seq, r_end, nodes, rel, gr, suit, t2, sc, lim,
              inputs) -> dict:  # fmt: skip
    relay_ids = ["STAGING"] + [f"RELAY{k}" for k in range(1, len(rel["cells"]))]
    stations, ids = [], []
    order = []
    for inf in info:
        if inf["node"] not in order:
            order.append(inf["node"])
    for n_, inf in enumerate(info, start=1):
        nd = nodes[inf["node"] - 1]
        k = nd["roles"].index(inf["role"])
        sid = f"S{n_:02d}"
        ids.append(sid)
        stations.append(
            {
                "id": sid,
                "role": inf["role"],
                "transect": f"T{order.index(inf['node']) + 1:02d}",
                "transect_source_id": nd["transect"],
                "xy_m": nd["xy_m"][k],
                "value": round(nd["scores"][k], 4),
                "service_min": sc["service_min"],
                "label": "MODELED",
                "overwatch_xy_m": nd["overwatch_xy_m"][k],
                "overwatch_distance_m": nd["overwatch_distance_m"][k],
                "relay": relay_ids[inf["relay"]],
            }
        )
    chain = ["STAGING", *ids, relay_ids[r_end]]
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
                    0 < k < len(stations) and stations[k - 1]["transect"] == stations[k]["transect"]
                ),
            }
        )
    margins = res["margins"] if res else []
    for x in margins:
        r, c = x.pop("xy_cell")
        x["xy_m"] = rc_to_xy(t2, r, c)
    det = res["details"] if res else {}
    return {
        "site": site,
        "scenario": {
            "start_utc": None,
            "preset": preset,
            "suit_profile": "default",
            "rover_profile": "default",
            "eva_max_min": sc["eva_max_min"],
            "consumables_total_min": sc["consumables_total_min"],
            "reserve_min": lim["reserve_min"],
            "shelter_max_min": lim["shelter_max_min"],
            "weights": pr["weights"],
            "objective": pr["objective"],
            "label": "PLACEHOLDER",
        },
        "stations": stations,
        "legs": out_legs,
        "margins": margins,
        "checks": res["checks"]
        if res
        else {k: "pass" for k in ("thread", "buddy", "shelter", "comms", "rover")},
        "rover": {
            "relays": [
                {
                    "id": relay_ids[i],
                    "xy_m": rc_to_xy(t2, *c),
                    "drive_from_staging_min": round(rel["drive_from_staging_min"][i], 2),
                }
                for i, c in enumerate(rel["cells"])
            ],
            "moves": rp.schedule(seq, rel),
            "ends_at": relay_ids[r_end],
            "label": "PLACEHOLDER",
            "note": "The rover is a mobile comms relay: it parks at a relay site for each "
            "transect and moves only during the last station of a transect (or the first leg); "
            "the walk ends at the rover.",
        },
        "totals": {
            "transects": len(seq),
            "stations": len(stations),
            "science_value": round(sum(nodes[t - 1]["value"] for t, _ in seq), 4),
            "minutes": det.get("minutes", 0.0),
            "consumables_min": det.get("consumables", 0.0),
            "relative_dose_min": det.get("relative_dose", 0.0),
            "distance_m": det.get("metres", 0.0),
            "min_thread_margin_min": det.get("thread_min_margin_min", 0.0),
            "worst_minutes_to_shelter": det.get("worst_minutes_to_shelter", 0.0),
            "longest_comm_shadow_min": det.get("longest_comm_shadow_min", 0.0),
            "rover_moves": len(rp.schedule(seq, rel)),
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


def thread_scenarios(m, nodes, pairs, rel, ok_sw, fields_r, suit, w, sc, lim, n, seed, log):
    """Plan n random scenarios (transect subsets and budgets, rover relays allowed) and check
    the thread, with C_home following the rover, on each."""
    rng = np.random.default_rng(seed)
    fails, worst, visited, moves = 0, np.inf, 0, 0
    tids = sorted({t for t, _ in pairs})
    for _ in range(n):
        k = int(rng.integers(1, len(tids) + 1))
        chosen = set(rng.choice(tids, k, replace=False).tolist())
        sub = [p for p in pairs if p[0] in chosen]
        total = float(rng.uniform(150, 450))
        prob = rp.build_problem(m, nodes, sub, rel, ok_sw, sc, lim, suit, 1e6, "value",
                                eva=float(rng.uniform(120, 420)), cons_total=total)  # fmt: skip
        sol = select.solve(prob, first_solution_only=True)
        res, _, _, _, seq, _, _ = rp.check(fields_r, suit, w, m, nodes, sub, sol.route, sc, lim,
                                           total)  # fmt: skip
        visited += len(seq)
        moves += len(rp.schedule(seq, rel))
        if res is None:
            continue
        fails += res["checks"]["thread"] != "pass"
        worst = min(worst, res["details"]["thread_min_margin_min"])
    log(f"  thread: {n - fails} of {n} random scenarios hold (worst margin {worst:.2f} min)")
    return {
        "scenarios": n,
        "held": n - fails,
        "worst_margin_min": round(float(worst), 3),
        "mean_transects_visited": round(visited / n, 2),
        "mean_rover_moves": round(moves / n, 2),
        "seed": seed,
    }


def bench_fixture(m, nodes, pairs, rel, ok_sw, sc, lim, suit, n, seed, time_limit, log) -> dict:
    """Random relay scenarios solved by OR-Tools (time-limited), for the browser benchmark."""
    rng = np.random.default_rng(seed)
    full = rp.build_problem(m, nodes, pairs, rel, ok_sw, sc, lim, suit, 1e6, "value")
    P = len(pairs)
    group = [-1] + [t for t, _ in pairs] + [-1]
    tids = sorted({t for t, _ in pairs})
    scen = []
    for _ in range(n):
        k = int(rng.integers(min(8, len(tids)), len(tids) + 1))
        chosen = set(rng.choice(tids, k, replace=False).tolist())
        idx = [0] + [i for i, p in enumerate(pairs, start=1) if p[0] in chosen] + [P + 1]
        eva = float(rng.uniform(120, 420))
        total = float(rng.uniform(150, 450))
        sub = [pairs[i - 1] for i in idx[1:-1]]
        prob = rp.build_problem(m, nodes, sub, rel, ok_sw, sc, lim, suit, 1e6, "value", eva=eva,
                                cons_total=total)  # fmt: skip
        sol = select.solve(prob, time_limit_s=time_limit)
        scen.append(
            {
                "nodes": idx,
                "eva_max_min": round(eva, 3),
                "consumables_budget": round(prob.consumables_budget, 3),
                "ortools_route": [idx[r] for r in sol.route],
                "ortools_value": round(sol.value, 6),
            }
        )
    log(f"  benchmark: {n} OR-Tools scenarios")

    def mat(a):
        return [[None if not np.isfinite(v) else round(float(v), 4) for v in row] for row in a]

    return {
        "_about": "Browser solver benchmark (test D11): OR-Tools reference plans, with a "
        f"{time_limit:g} s guided local search per scenario (a time-limited reference, not a "
        "proven optimum), on random subsets of the boxwork (transect, relay) nodes, Balanced "
        "legs. Node 0 is the start, the last node the END (the walk ends at the rover); nodes of "
        "one group (one transect) are visited at most once. Generated by ariadne plan.",
        "pipeline_version": PIPELINE_VERSION,
        "ortools_time_limit_s": time_limit,
        "end_node": P + 1,
        "group": group,
        "service_min": [round(float(v), 4) for v in full.service_min],
        "service_consumables_min": [round(float(v), 4) for v in full.service_cons],
        "values": [round(float(v), 6) for v in full.value],
        "minutes": mat(full.minutes),
        "consumables": mat(full.consumables),
        "cost": mat(full.cost),
        "scenarios": scen,
    }


def plan_site(site: str = "boxwork", log=print, quick: bool = False) -> dict:
    t0 = time.time()
    root = repo_root()
    site_dir = root / "data" / "sites" / site
    out = site_dir / "plan"
    out.mkdir(parents=True, exist_ok=True)
    presets = load_presets()
    sc = scenario_values(presets)
    suit = mb.load_suit()
    rover = rl.load_rover()
    summary_d = json.loads((site_dir / "derived" / "summary.json").read_text(encoding="utf-8"))
    staging_xy = summary_d["shelters"]["staging_xy"]
    k = int(round(sc["planning_resolution_m"]))
    half = sc["max_station_distance_m"] + sc["grid_margin_m"]
    log(f"Planning {site}: staging at E {staging_xy[0]:.1f} N {staging_xy[1]:.1f}")
    gr0, t2, crs, extra = planning_grid(site_dir, staging_xy, half, k)
    staging_rc = xy_to_rc(t2, *staging_xy)
    if not gr0.passable[staging_rc]:
        raise RuntimeError("the staging point is not walkable on the planning grid")
    # terrain shelters, with and without the parked rover (storm pointers use the staging point)
    sh_cells = [tuple(x) for x in np.argwhere(extra["shelters"] & gr0.passable)]
    ties = [float(gr0.dose[x]) for x in sh_cells]
    storm = g.dijkstra(gr0, suit, TIME_ONLY, sh_cells + [staging_rc], reverse=True,
                       tie_break=ties + [float(rover["shelter_s"])])  # fmt: skip
    terrain_sh = g.dijkstra(gr0, suit, TIME_ONLY, sh_cells, reverse=True, tie_break=ties).time
    limits = {name: preset_limits(sc, pr) for name, pr in presets["presets"].items()}
    loosest = max(lim["shelter_max_min"] for lim in limits.values())

    def grid_for(shelter_max):
        passable = gr0.passable & (storm.time <= shelter_max)
        return g.Grid(gr0.z, passable, gr0.hazard, gr0.dose, gr0.unc, gr0.res)

    g_loose = grid_for(loosest)
    home0 = g.dijkstra(g_loose, suit, CONSUMABLES, [staging_rc], reverse=True)
    f_loose = cs.Fields(g_loose, home0.consumables, storm.time, extra["comms"], extra["rover_ok"])
    log(f"  fields ready ({time.time() - t0:.0f} s)")
    common = dict(resolution_m=gr0.res, inputs=["derived layers"])
    for name, arr, pid in (
        ("c_home.tif", np.where(np.isfinite(home0.consumables), home0.consumables, np.nan),
         "Consumables to walk back to the staging point, minutes at the nominal rate"),
        ("shelter_minutes.tif", np.where(np.isfinite(storm.time), storm.time, np.nan),
         "Walking minutes to the nearest shelter or the rover at the staging point"),
        ("storm_pointer.tif", storm.pred.astype(np.int16),
         "Storm mode: index of the next move toward the earliest shelter (-1 at shelters)"),
    ):  # fmt: skip
        write_layer(out / name, arr.astype(np.float32 if arr.dtype != np.int16 else np.int16),
                    t2, crs, None, product_id=pid, label=Label.MODELED,
                    notes="Walker model with PLACEHOLDER suit settings.", **common)  # fmt: skip
    transects = json.loads((site_dir / "derived" / "transects.geojson").read_text("utf-8"))
    # the pool relays are chosen to cover: whole transects within reach, comms not yet required
    pool = transect_candidates(transects["features"], g_loose, t2, staging_rc, f_loose, sc, log,
                               limit=150, check_comms=False)  # fmt: skip
    rel = rp.choose_relays(g_loose, staging_rc, extra["rover_cls"], pool, rover, log)
    in_sight = [nd for nd in pool if any(rl.sees_transect(v, nd["points"]) for v in rel["views"])]
    nodes = in_sight[: int(sc["candidate_transects"])]
    log(f"  candidate transects: {len(nodes)} in sight of the rover at some relay "
        f"({sum(1 for nd in pool if rl.sees_transect(rel['views'][0], nd['points']))} from the "
        "staging point alone)")  # fmt: skip
    ok_sw = rp.switches(g_loose, nodes, rel, sc["service_min"], float(rover["antenna_height_m"]))
    inputs = ["usgs-gale-dem-1m", "usgs-gale-ortho-25cm", "msl-places", "mola-dem-463m",
              "derived layers (docs/derived)"]  # fmt: skip
    plans, mats, ctx_by = {}, {}, {}
    comparison = {}
    for name, pr in presets["presets"].items():
        w, lim = pr["weights"], limits[name]
        gp = grid_for(lim["shelter_max_min"])
        shelters = [np.minimum(terrain_sh, g.dijkstra(gp, suit, TIME_ONLY, [c], reverse=True).time)
                    for c in rel["cells"]]  # fmt: skip
        fields_r = rp.relay_fields(gp, suit, rel["cells"], rel["views"], terrain_sh,
                                   extra["rover_ok"])  # fmt: skip
        m = cached_relay_legs(out / f"legs_{name}.pkl", gp, suit, w, staging_rc, nodes, rel,
                              shelters, log)  # fmt: skip
        pairs = rp.usable_pairs(m, nodes, rp.pairs_for(nodes, rel["views"]), lim)
        mats[name] = m
        ctx_by[name] = (pairs, fields_r)
        prob = rp.build_problem(m, nodes, pairs, rel, ok_sw, sc, lim, suit,
                                float(pr["value_weight"]), pr["objective"])  # fmt: skip
        sol = select.solve(prob, time_limit_s=3.0 if quick else 30.0)
        res, legs, stations, info, seq, r_end, _ = rp.check(
            fields_r, suit, w, m, nodes, pairs, sol.route, sc, lim, sc["consumables_total_min"]
        )
        plan = plan_json(site, name, pr, res, legs, info, seq, r_end, nodes, rel, gp, suit, t2,
                         sc, lim, inputs)  # fmt: skip
        validate_plan(plan)
        plans[name] = plan
        # the same problem with the rover held at the staging point, for comparison
        fixed = [p for p in pairs if p[1] == 0]
        p0 = rp.build_problem(m, nodes, fixed, rel, ok_sw, sc, lim, suit,
                              float(pr["value_weight"]), pr["objective"])  # fmt: skip
        s0 = select.solve(p0, time_limit_s=3.0 if quick else 20.0)
        seq0 = [fixed[i - 1] for i in s0.route[1:-1]]
        comparison[name] = {
            "usable_transects_with_relay": len({t for t, _ in pairs}),
            "usable_transects_staging_only": len({t for t, _ in fixed}),
            "value_with_relay": plan["totals"]["science_value"],
            "value_staging_only": round(sum(nodes[t - 1]["value"] for t, _ in seq0), 4),
            "transects_with_relay": len(seq),
            "transects_staging_only": len(seq0),
        }
        log(f"  {name}: {len(seq)} transects ({len(stations)} stations), value "
            f"{plan['totals']['science_value']:.2f}, {plan['totals']['minutes']:.0f} min, "
            f"rover moves {plan['totals']['rover_moves']}, ends at {plan['rover']['ends_at']}, "
            f"checks {plan['checks']}; staging only: {len(seq0)} transects, value "
            f"{comparison[name]['value_staging_only']:.2f}")  # fmt: skip
    bal = mats["balanced"]
    pairs_b, fields_b = ctx_by["balanced"]
    w_bal = presets["presets"]["balanced"]["weights"]
    lim_b = limits["balanced"]
    n_thread = 100 if quick else 1000
    thread = thread_scenarios(
        bal, nodes, pairs_b, rel, ok_sw, fields_b, suit, w_bal, sc, lim_b, n_thread, 20261109, log
    )
    bench = bench_fixture(bal, nodes, pairs_b, rel, ok_sw, sc, limits["balanced"], suit,
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
        "usable_transects": {n_: len({t for t, _ in ctx_by[n_][0]}) for n_ in plans},
        "walkable_share": round(float(gr0.passable.mean()), 4),
        "within_shelter_limit_share": {
            str(s): round(float(grid_for(s).passable.sum() / max(1, gr0.passable.sum())), 4)
            for s in sorted({lim["shelter_max_min"] for lim in limits.values()})
        },
        "comms_share": round(float(extra["comms"].mean()), 4),
        "comms_share_with_relays": round(float(np.logical_or.reduce(rel["views"]).mean()), 4),
        "rover_ok": extra["rover_ok"],
        "relays": {
            "sites": [rc_to_xy(t2, *c) for c in rel["cells"]],
            "candidates": rel["candidates"],
            "pool": rel["pool"],
            "pool_seen_from_staging": rel["pool_seen_from_staging"],
            "pool_seen_with_relays": rel["pool_seen_with_relays"],
            "drive_from_staging_min": [round(x, 2) for x in rel["drive_from_staging_min"]],
            "rover": rover,
        },
        "comparison": comparison,
        "presets": {
            n_: {
                "weights": pr["weights"],
                "limits": limits[n_],
                "objective": pr["objective"],
                "value_weight": pr["value_weight"],
            }
            for n_, pr in presets["presets"].items()
        },  # fmt: skip
        "plans": {
            n_: p_["totals"] | {"checks": p_["checks"], "ends_at": p_["rover"]["ends_at"]}
            for n_, p_ in plans.items()
        },  # fmt: skip
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
