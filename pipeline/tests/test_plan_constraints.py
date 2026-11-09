# Written with AI assistance (Claude Code). See AI_USE.md.
"""Hard constraints along a route (test D7) and the thread over random scenarios (test D8)."""

import numpy as np
import pytest

from ariadne.models import metabolic as mb
from ariadne.plan import constraints as cs
from ariadne.plan import graph as g
from ariadne.plan import select

RES = 2.0
W = {"time": 1.0, "metabolic": 0.5, "hazard": 1.0, "dose": 0.5, "uncertainty": 0.5}
LIMITS = {"reserve_min": 30.0, "shelter_max_min": 20.0, "comm_shadow_max_min": 10.0,
          "sample_step_m": 5.0}  # fmt: skip


@pytest.fixture(scope="module")
def suit():
    return mb.load_suit()


def terrain(n=60, seed=1):
    from scipy import ndimage

    rng = np.random.default_rng(seed)
    z = ndimage.gaussian_filter(rng.normal(0, 8, (n, n)), 4)
    gr = g.Grid(z, np.ones((n, n), bool), np.zeros((n, n)), np.full((n, n), 0.9),
                np.zeros((n, n)), RES)  # fmt: skip
    return gr


def fields_for(gr, suit, home, shelters=None, comms=None):
    c_home = g.dijkstra(
        gr,
        suit,
        {"time": 0, "metabolic": 1, "hazard": 0, "dose": 0, "uncertainty": 0},
        [home],
        reverse=True,
    ).consumables
    src = [home] + list(shelters or [])
    shelter_min = g.dijkstra(
        gr,
        suit,
        {"time": 1, "metabolic": 0, "hazard": 0, "dose": 0, "uncertainty": 0},
        src,
        reverse=True,
    ).time
    return cs.Fields(gr, c_home, shelter_min,
                     np.ones(gr.z.shape, bool) if comms is None else comms, True)  # fmt: skip


def plan_route(gr, suit, home, stations, cons_total=300.0, eva=300.0, service=15.0):
    pts = [home, *stations]
    m = g.leg_matrix(gr, suit, W, pts)
    n = len(pts)
    p = select.Problem(
        value=np.r_[0.0, np.linspace(1.0, 0.5, n - 1)],
        service_min=np.r_[0.0, np.full(n - 1, service)],
        service_cons=np.r_[0.0, np.full(n - 1, service * 0.6)],
        minutes=m["minutes"], consumables=m["consumables"], cost=m["cost"],
        eva_max_min=eva, consumables_budget=cons_total - 30.0 - cs.DISCRETISATION_MARGIN_MIN,
    )  # fmt: skip
    sol = select.solve(p, time_limit_s=0.3)
    legs = [m["paths"][(a, b)] for a, b in zip(sol.route[:-1], sol.route[1:], strict=True)
            if a != b]  # fmt: skip
    visited = [pts[k] for k in sol.route[1:-1]]
    return sol, legs, visited


def test_margins_are_sampled_at_least_every_5_m_and_add_up(suit):
    gr = terrain()
    home = (30, 30)
    f = fields_for(gr, suit, home)
    sol, legs, visited = plan_route(gr, suit, home, [(10, 10), (50, 15), (45, 50)])
    res = cs.check_route(f, suit, W, legs, visited, 15.0, 9.0, 300.0, LIMITS)
    m = res["margins"]
    assert m[0]["c_left"] == pytest.approx(300.0)
    assert m[0]["c_home"] == pytest.approx(0.0, abs=1e-9)
    assert max(s["step_m"] for s in m) <= 5.0 + 1e-9
    used = 300.0 - m[-1]["c_left"]
    assert used == pytest.approx(sol.consumables, abs=2e-3)
    assert res["checks"]["thread"] == "pass"


def test_thread_fails_when_the_consumables_are_short(suit):
    gr = terrain()
    home = (30, 30)
    f = fields_for(gr, suit, home)
    _, legs, visited = plan_route(gr, suit, home, [(5, 5), (55, 55)], cons_total=10_000)
    res = cs.check_route(f, suit, W, legs, visited, 15.0, 9.0, 40.0, LIMITS)
    assert res["checks"]["thread"] == "fail"
    assert res["details"]["thread_min_margin_min"] < 0


def test_shelter_and_comms_violations_are_found(suit):
    gr = terrain()
    home = (30, 30)
    comms = np.ones(gr.z.shape, bool)
    comms[:, :20] = False  # the west third is out of line of sight
    f = fields_for(gr, suit, home, comms=comms)
    _, legs, visited = plan_route(gr, suit, home, [(30, 2)], cons_total=10_000)
    tight = dict(LIMITS, shelter_max_min=0.5)
    res = cs.check_route(f, suit, W, legs, visited, 15.0, 9.0, 10_000, tight)
    assert res["checks"]["shelter"] == "fail"
    assert res["checks"]["comms"] == "fail"  # 15 min of station work in a comm shadow
    assert res["details"]["longest_comm_shadow_min"] > 15.0


def test_buddy_needs_an_overwatch_point_with_line_of_sight(suit):
    z = np.zeros((40, 40))
    z[:, 21:] = 0.0
    z[5:35, 18:20] = 10.0  # a wall
    gr = g.Grid(z, np.ones((40, 40), bool), np.zeros((40, 40)), np.zeros((40, 40)),
                np.zeros((40, 40)), RES)  # fmt: skip
    ow = cs.overwatch_point(gr, (20, 10), max_m=50.0, min_m=3.0, helmet_m=1.8)
    assert ow is not None and ow["distance_m"] <= 50.0
    # with the walker boxed in by walls on every side, there is no overwatch
    z2 = np.zeros((40, 40))
    z2[14:27, 14:27] = 10.0
    z2[16:25, 16:25] = 0.0
    gr2 = g.Grid(z2, z2 < 5.0, np.zeros((40, 40)), np.zeros((40, 40)),
                 np.zeros((40, 40)), RES)  # walls are no-go  # fmt: skip
    assert cs.overwatch_point(gr2, (20, 20), max_m=50.0, min_m=12.0, helmet_m=1.8) is None


def test_thread_holds_in_1000_random_scenarios(suit):
    """Any plan within the consumables budget keeps the thread at every sample, because the
    route home from any point costs at least C_home there. Checked, not assumed."""
    gr = terrain(n=50, seed=7)
    home = (25, 25)
    f = fields_for(gr, suit, home)
    rng = np.random.default_rng(11)
    cand = [tuple(int(v) for v in rng.integers(2, 48, 2)) for _ in range(12)]
    pts = [home, *cand]
    m = g.leg_matrix(gr, suit, W, pts)
    fails = 0
    for _ in range(1000):
        k = int(rng.integers(1, 6))
        sub = sorted(rng.choice(np.arange(1, len(pts)), size=k, replace=False).tolist())
        total = float(rng.uniform(40, 200))
        idx = [0, *sub]
        p = select.Problem(
            value=np.r_[0.0, rng.uniform(0.2, 1.0, k)],
            service_min=np.r_[0.0, np.full(k, 15.0)],
            service_cons=np.r_[0.0, np.full(k, 9.0)],
            minutes=m["minutes"][np.ix_(idx, idx)],
            consumables=m["consumables"][np.ix_(idx, idx)],
            cost=m["cost"][np.ix_(idx, idx)],
            eva_max_min=400.0,
            consumables_budget=total - 30.0 - cs.DISCRETISATION_MARGIN_MIN,
        )
        sol = select.solve(p, first_solution_only=True)
        route = [idx[r] for r in sol.route]
        legs = [m["paths"][(a, b)] for a, b in zip(route[:-1], route[1:], strict=True) if a != b]
        res = cs.check_route(f, suit, W, legs, [pts[r] for r in route[1:-1]], 15.0, 9.0, total,
                             LIMITS)  # fmt: skip
        fails += res["checks"]["thread"] != "pass"
    assert fails == 0
