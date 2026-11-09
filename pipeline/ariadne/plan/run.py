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


def candidate_stations(transects: list, gr, t2, staging_rc, fields: cs.Fields, sc, log) -> list:
    """Transect stations that are reachable, walkable, in comms line of sight and have an
    overwatch point; the highest-scoring `candidate_stations` of them."""
    pts = [f for f in transects if f["geometry"]["type"] == "Point" and "score" in f["properties"]]
    feats = sorted(pts, key=lambda f: -float(f["properties"]["score"]))
    out, seen = [], set()
    h, w = gr.z.shape
    max_d = sc["max_station_distance_m"]
    rejected = {"far": 0, "outside": 0, "unwalkable": 0, "no comms": 0, "no overwatch": 0}
    for f in feats:
        x, y = f["geometry"]["coordinates"][:2]
        r, c = xy_to_rc(t2, x, y)
        if np.hypot(r - staging_rc[0], c - staging_rc[1]) * gr.res > max_d:
            rejected["far"] += 1
            continue
        if not (0 <= r < h and 0 <= c < w) or (r, c) in seen:
            rejected["outside"] += 1
            continue
        if not gr.passable[r, c] or not np.isfinite(fields.c_home[r, c]):
            rejected["unwalkable"] += 1
            continue
        if not fields.comms[r, c]:
            rejected["no comms"] += 1
            continue
        ow = cs.overwatch_point(gr, (r, c), sc["buddy_max_m"], sc["buddy_min_m"],
                                sc["helmet_height_m"])  # fmt: skip
        if ow is None:
            rejected["no overwatch"] += 1
            continue
        p = f["properties"]
        out.append(
            {
                "rc": (r, c),
                "xy_m": rc_to_xy(t2, r, c),
                "role": p["role"],
                "value": float(p["score"]),
                "transect": int(p["transect"]),
                "overwatch_xy_m": rc_to_xy(t2, *ow["cell"]),
                "overwatch_distance_m": round(ow["distance_m"], 1),
            }
        )
        seen.add((r, c))
        if len(out) >= int(sc["candidate_stations"]):
            break
    log(f"  candidates: {len(out)} kept; rejected {rejected}")
    return out


def leg_extras(gr, suit, w, paths, fields: cs.Fields, n: int) -> dict:
    """Longest comm shadow and worst minutes to shelter along each smoothed leg."""
    shadow = np.zeros((n, n))
    shelter = np.zeros((n, n))
    for (i, j), pts in paths.items():
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
        shadow[i, j], shelter[i, j] = longest, worst
    return {"shadow_max_min": shadow, "shelter_max_min": shelter}


def cached_leg_matrix(path: Path, gr, suit, w, points, fields, log) -> dict:
    """The leg matrix and per-leg extras, reused from `path` when every input is the same."""
    import hashlib
    import pickle

    key = hashlib.sha256(
        json.dumps(
            {"points": [list(map(int, p)) for p in points], "w": w, "suit": suit.__dict__,
             "shape": list(gr.z.shape), "res": gr.res, "version": PIPELINE_VERSION},
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
    m = g.leg_matrix(gr, suit, w, points)
    m.update(leg_extras(gr, suit, w, m["paths"], fields, len(points)))
    with path.open("wb") as f:
        pickle.dump({"key": key, "m": m}, f)
    return m


def problem_for(
    m: dict,
    nodes: list[int],
    cands: list,
    sc: dict,
    suit: mb.Suit,
    lam: float,
    eva: float | None = None,
    cons_total: float | None = None,
) -> select.Problem:
    idx = np.array(nodes)
    k = len(nodes) - 1
    service = sc["service_min"]
    eva = sc["eva_max_min"] if eva is None else eva
    cons_total = sc["consumables_total_min"] if cons_total is None else cons_total
    # a leg that would break the comms or shelter limits is not allowed
    bad = (m["shadow_max_min"] > sc["comm_shadow_max_min"]) | (
        m["shelter_max_min"] > sc["shelter_max_min"]
    )
    minutes = np.where(bad, np.inf, m["minutes"])[np.ix_(idx, idx)]
    return select.Problem(
        value=np.r_[0.0, [cands[i - 1]["value"] for i in nodes[1:]]],
        service_min=np.r_[0.0, np.full(k, service)],
        service_cons=np.r_[0.0, np.full(k, service * suit.station_rate_ratio)],
        minutes=minutes,
        consumables=m["consumables"][np.ix_(idx, idx)],
        cost=m["cost"][np.ix_(idx, idx)],
        eva_max_min=eva,
        consumables_budget=cons_total - sc["reserve_min"] - cs.DISCRETISATION_MARGIN_MIN,
        value_weight=lam,
    )


def plan_json(site, preset, sol, nodes, cands, m, t2, res, sc, inputs) -> dict:
    route = [nodes[r] for r in sol.route]
    ids = {0: "STAGING"}
    stations = []
    for n_, node in enumerate(route[1:-1], start=1):
        cnd = cands[node - 1]
        ids[node] = f"S{n_:02d}"
        stations.append(
            {
                "id": ids[node],
                "role": cnd["role"],
                "xy_m": cnd["xy_m"],
                "value": round(cnd["value"], 4),
                "service_min": sc["service_min"],
                "label": "MODELED",
                "overwatch_xy_m": cnd["overwatch_xy_m"],
                "overwatch_distance_m": cnd["overwatch_distance_m"],
            }
        )
    legs = []
    for a, b in zip(route[:-1], route[1:], strict=True):
        if a == b:
            continue
        legs.append(
            {
                "from": ids[a],
                "to": ids[b],
                "path_xy_m": [rc_to_xy(t2, r, c) for r, c in m["paths"][(a, b)]],
                "minutes": round(float(m["minutes"][a, b]), 3),
                "consumables_min": round(float(m["consumables"][a, b]), 3),
                "relative_dose": round(float(m["dose"][a, b]), 4),
            }
        )
    for x in res["margins"]:
        r, c = x.pop("xy_cell")
        x["xy_m"] = rc_to_xy(t2, r, c)
    return {
        "site": site,
        "scenario": {
            "start_utc": None,
            "preset": preset,
            "suit_profile": "default",
            "rover_profile": "default",
            "eva_max_min": sc["eva_max_min"],
            "consumables_total_min": sc["consumables_total_min"],
            "label": "PLACEHOLDER",
        },
        "stations": stations,
        "legs": legs,
        "margins": res["margins"],
        "checks": res["checks"],
        "totals": {
            "science_value": round(sol.value, 4),
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


def thread_scenarios(m, cands, fields, gr, suit, w, sc, n: int, seed: int, log) -> dict:
    """Plan n random scenarios (station subsets and budgets) and check the thread on each."""
    rng = np.random.default_rng(seed)
    limits = {k: sc[k] for k in ("reserve_min", "shelter_max_min", "comm_shadow_max_min",
                                 "sample_step_m")}  # fmt: skip
    fails, worst, visited = 0, np.inf, 0
    for _ in range(n):
        k = int(rng.integers(3, len(cands) + 1))
        nodes = [0, *sorted(rng.choice(np.arange(1, len(cands) + 1), k, replace=False).tolist())]
        total = float(rng.uniform(120, 360))
        p = problem_for(m, nodes, cands, sc, suit, 1e6, eva=float(rng.uniform(90, 300)),
                        cons_total=total)  # fmt: skip
        sol = select.solve(p, first_solution_only=True)
        route = [nodes[r] for r in sol.route]
        legs = [m["paths"][(a, b)] for a, b in zip(route[:-1], route[1:], strict=True) if a != b]
        visited += len(route) - 2
        if not legs:
            continue
        res = cs.check_route(fields, suit, w, legs, [cands[r - 1]["rc"] for r in route[1:-1]],
                             sc["service_min"], sc["service_min"] * suit.station_rate_ratio,
                             total, limits)  # fmt: skip
        fails += res["checks"]["thread"] != "pass"
        worst = min(worst, res["details"]["thread_min_margin_min"])
    log(f"  thread: {n - fails} of {n} random scenarios hold (worst margin {worst:.2f} min)")
    return {
        "scenarios": n,
        "held": n - fails,
        "worst_margin_min": round(float(worst), 3),
        "mean_stations_visited": round(visited / n, 2),
        "seed": seed,
    }


def bench_fixture(m, cands, sc, suit, n: int, seed: int, time_limit: float, log) -> dict:
    """Random scenarios solved by OR-Tools, for the browser solver's benchmark."""
    rng = np.random.default_rng(seed)
    scen = []
    for _ in range(n):
        k = int(rng.integers(12, len(cands) + 1))
        nodes = [0, *sorted(rng.choice(np.arange(1, len(cands) + 1), k, replace=False).tolist())]
        eva = float(rng.uniform(90, 300))
        total = float(rng.uniform(120, 360))
        p = problem_for(m, nodes, cands, sc, suit, 1e6, eva=eva, cons_total=total)
        sol = select.solve(p, time_limit_s=time_limit)
        scen.append(
            {
                "nodes": nodes,
                "eva_max_min": round(eva, 3),
                "consumables_budget": round(p.consumables_budget, 3),
                "ortools_route": [nodes[r] for r in sol.route],
                "ortools_value": round(sol.value, 6),
            }
        )
    log(f"  benchmark: {n} OR-Tools scenarios")
    bad = (m["shadow_max_min"] > sc["comm_shadow_max_min"]) | (
        m["shelter_max_min"] > sc["shelter_max_min"]
    )

    def mat(a):
        return [[None if not np.isfinite(v) else round(float(v), 4) for v in row] for row in a]

    return {
        "_about": "Browser solver benchmark (test D11): OR-Tools reference plans on random "
        "subsets of the boxwork candidates, balanced preset legs. Generated by ariadne plan.",
        "pipeline_version": PIPELINE_VERSION,
        "service_min": sc["service_min"],
        "service_consumables_min": round(sc["service_min"] * suit.station_rate_ratio, 4),
        "values": [0.0] + [round(c["value"], 6) for c in cands],
        "minutes": mat(np.where(bad, np.inf, m["minutes"])),
        "consumables": mat(m["consumables"]),
        "cost": mat(m["cost"]),
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
    passable = gr0.passable & (storm.time <= sc["shelter_max_min"])
    gr = g.Grid(gr0.z, passable, gr0.hazard, gr0.dose, gr0.unc, gr0.res)
    home = g.dijkstra(gr, suit, CONSUMABLES, [staging_rc], reverse=True)
    fields = cs.Fields(gr, home.consumables, storm.time, extra["comms"], extra["rover_ok"])
    log(f"  fields ready ({time.time() - t0:.0f} s)")
    common = dict(resolution_m=gr.res, inputs=["derived layers"])
    for name, arr, pid, label in (
        ("c_home.tif", np.where(np.isfinite(home.consumables), home.consumables, np.nan),
         "Consumables to walk back to the staging point, minutes at the nominal rate",
         Label.MODELED),
        ("shelter_minutes.tif", np.where(np.isfinite(storm.time), storm.time, np.nan),
         "Walking minutes to the nearest shelter or the rover", Label.MODELED),
        ("storm_pointer.tif", storm.pred.astype(np.int16),
         "Storm mode: index of the next move toward the earliest shelter (-1 at shelters)",
         Label.MODELED),
    ):  # fmt: skip
        write_layer(out / name, arr.astype(np.float32 if arr.dtype != np.int16 else np.int16),
                    t2, crs, None, product_id=pid, label=label,
                    notes="Walker model with PLACEHOLDER suit settings.", **common)  # fmt: skip
    transects = json.loads((site_dir / "derived" / "transects.geojson").read_text("utf-8"))
    cands = candidate_stations(transects["features"], gr, t2, staging_rc, fields, sc, log)
    points = [staging_rc] + [c["rc"] for c in cands]
    limits = {k_: sc[k_] for k_ in ("reserve_min", "shelter_max_min", "comm_shadow_max_min",
                                    "sample_step_m")}  # fmt: skip
    inputs = ["usgs-gale-dem-1m", "usgs-gale-ortho-25cm", "msl-places", "mola-dem-463m",
              "derived layers (docs/derived)"]  # fmt: skip
    mats, plans = {}, {}
    for name, pr in presets["presets"].items():
        w = pr["weights"]
        m = cached_leg_matrix(out / f"legs_{name}.pkl", gr, suit, w, points, fields, log)
        mats[name] = m
        nodes = list(range(len(points)))
        p = problem_for(m, nodes, cands, sc, suit, float(pr["value_weight"]))
        sol = select.solve(p, time_limit_s=3.0 if quick else 15.0)
        route = sol.route
        legs = [m["paths"][(a, b)] for a, b in zip(route[:-1], route[1:], strict=True) if a != b]
        res = cs.check_route(
            fields, suit, w, legs or [[staging_rc, staging_rc]],
            [cands[r - 1]["rc"] for r in route[1:-1]], sc["service_min"],
            sc["service_min"] * suit.station_rate_ratio, sc["consumables_total_min"], limits,
            buddy_ok=[True] * (len(route) - 2),
        )  # fmt: skip
        plan = plan_json(site, name, sol, nodes, cands, m, t2, res, sc, inputs)
        validate_plan(plan)
        plans[name] = plan
        log(f"  {name}: {len(route) - 2} stations, value {sol.value:.2f}, "
            f"{res['details']['minutes']:.0f} min, checks {res['checks']}")  # fmt: skip
    bal = mats["balanced"]
    w_bal = presets["presets"]["balanced"]["weights"]
    thread = thread_scenarios(
        bal, cands, fields, gr, suit, w_bal, sc, 100 if quick else 1000, 20261109, log
    )
    bench = bench_fixture(bal, cands, sc, suit, 10 if quick else 60, 1109,
                          0.5 if quick else 2.0, log)  # fmt: skip
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
        "grid": {"resolution_m": gr.res, "shape": list(gr.z.shape)},
        "staging_xy_m": staging_xy,
        "candidates": len(cands),
        "walkable_share": round(float(gr0.passable.mean()), 4),
        "within_shelter_limit_share": round(float(passable.sum() / max(1, gr0.passable.sum())), 4),
        "comms_share": round(float(extra["comms"].mean()), 4),
        "rover_ok": extra["rover_ok"],
        "plans": {
            n_: p_["totals"] | {"stations": len(p_["stations"]), "checks": p_["checks"]}
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
