# Written with AI assistance (Claude Code). See AI_USE.md.
"""Route graph, Dijkstra, A*, smoothing and fields on synthetic terrain (tests D2 to D5)."""

import math

import numpy as np
import pytest

from ariadne.models import metabolic as mb
from ariadne.plan import graph as g

RES = 2.0


@pytest.fixture(scope="module")
def suit():
    return mb.load_suit()


def grid(z, passable=None, hazard=0.0, dose=0.0, unc=0.0):
    z = np.asarray(z, dtype=np.float64)
    return g.Grid(
        z=z,
        passable=np.ones(z.shape, bool) if passable is None else passable,
        hazard=np.full(z.shape, hazard),
        dose=np.full(z.shape, dose),
        unc=np.full(z.shape, unc),
        res=RES,
    )


W_TIME = {"time": 1.0, "metabolic": 0.0, "hazard": 0.0, "dose": 0.0, "uncertainty": 0.0}


# --- D2: graph and costs ---


def test_sixteen_neighbour_moves_and_flat_ground_time(suit):
    gr = grid(np.zeros((41, 41)))
    assert len(g.OFFSETS) == 16
    out = g.dijkstra(gr, suit, W_TIME, sources=[(20, 20)])
    v = suit.max_speed_m_s
    # straight and knight-move directions are exact on flat ground
    assert out.time[20, 40] == pytest.approx(20 * RES / v / 60)
    assert out.time[30, 40] == pytest.approx(10 * math.sqrt(5) * RES / v / 60)
    # any direction is within the 16-neighbour approximation error (under 3%)
    d = math.hypot(13, 7) * RES / v / 60
    assert d <= out.time[33, 27] <= 1.03 * d


def test_uphill_costs_more_than_downhill_on_a_ramp(suit):
    z = np.tile(np.arange(60) * 0.3 * RES, (5, 1))  # 30% grade rising eastward
    gr = grid(z)
    up = g.dijkstra(gr, suit, W_TIME, sources=[(2, 0)])
    down = g.dijkstra(gr, suit, W_TIME, sources=[(2, 59)])
    assert up.time[2, 59] > 1.5 * down.time[2, 0]
    assert up.consumables[2, 59] > down.consumables[2, 0]


def test_no_go_cells_are_never_entered_and_corners_are_not_cut(suit):
    passable = np.ones((21, 21), bool)
    passable[:, 10] = False
    passable[20, 10] = True  # one gap at the bottom
    gr = grid(np.zeros((21, 21)), passable)
    out = g.dijkstra(gr, suit, W_TIME, sources=[(0, 0)])
    path = g.extract_path(out, (0, 20))
    assert all(passable[r, c] for r, c in path)
    assert (20, 10) in path
    # a diagonal step between two blocked cells is not allowed
    p2 = np.zeros((3, 3), bool)
    p2[0, 0] = p2[1, 1] = True
    out2 = g.dijkstra(grid(np.zeros((3, 3)), p2), suit, W_TIME, sources=[(0, 0)])
    assert np.isinf(out2.cost[1, 1])


def test_cost_terms_add_as_in_the_edge_formula(suit):
    gr = grid(np.zeros((3, 12)), hazard=0.5, dose=0.8, unc=0.2)
    w = {"time": 1.0, "metabolic": 0.5, "hazard": 2.0, "dose": 1.0, "uncertainty": 3.0}
    out = g.dijkstra(gr, suit, w, sources=[(1, 0)])
    t = out.time[1, 11]
    expect = t * (1.0 + 0.5 * 1.0 + 2.0 * 0.5 + 1.0 * 0.8 + 3.0 * 0.2)
    assert out.cost[1, 11] == pytest.approx(expect)
    assert out.dose[1, 11] == pytest.approx(t * 0.8)


# --- D3: A* and smoothing ---


def rough_terrain(seed=0, n=50):
    rng = np.random.default_rng(seed)
    from scipy import ndimage

    z = ndimage.gaussian_filter(rng.normal(0, 6, (n, n)), 3)
    passable = ndimage.gaussian_filter(rng.random((n, n)), 1.5) > 0.42
    passable[2, 2] = passable[n - 3, n - 3] = True
    return z, passable


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_astar_matches_dijkstra(suit, seed):
    z, passable = rough_terrain(seed)
    gr = grid(z, passable, hazard=0.1, dose=0.5, unc=0.1)
    w = {"time": 1.0, "metabolic": 0.5, "hazard": 1.0, "dose": 0.5, "uncertainty": 0.5}
    d = g.dijkstra(gr, suit, w, sources=[(2, 2)])
    a = g.astar(gr, suit, w, (2, 2), (47, 47))
    if np.isinf(d.cost[47, 47]):
        assert a is None
    else:
        assert a.cost == pytest.approx(d.cost[47, 47], rel=1e-9)
        assert a.path[0] == (2, 2) and a.path[-1] == (47, 47)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_smoothing_never_crosses_no_go_or_costs_more(suit, seed):
    z, passable = rough_terrain(seed)
    gr = grid(z, passable, hazard=0.1)
    w = {"time": 1.0, "metabolic": 0.5, "hazard": 1.0, "dose": 0.0, "uncertainty": 0.0}
    a = g.astar(gr, suit, w, (2, 2), (47, 47))
    if a is None:
        pytest.skip("no path on this random terrain")
    pts = g.smooth(gr, suit, w, a.path)
    assert pts[0] == a.path[0] and pts[-1] == a.path[-1]
    assert len(pts) <= len(a.path)
    for p, q in zip(pts[:-1], pts[1:], strict=True):
        assert g.segment_clear(gr, p, q)
    assert g.polyline_metrics(gr, suit, w, pts)["cost"] <= a.cost + 1e-9


# --- D4: fields ---


def test_cost_to_home_is_the_reversed_graph(suit):
    z = np.tile(np.arange(40) * 0.2 * RES, (40, 1)) + np.random.default_rng(5).normal(
        0, 0.3, (40, 40)
    )
    gr = grid(z)
    home = g.dijkstra(gr, suit, W_TIME, sources=[(20, 5)], reverse=True)
    for r, c in [(3, 30), (35, 38), (20, 20)]:
        fwd = g.dijkstra(gr, suit, W_TIME, sources=[(r, c)])
        assert home.time[r, c] == pytest.approx(fwd.time[20, 5], rel=1e-9)
    # following the pointers from any cell walks home
    path = g.follow_pointers(home, (35, 38))
    assert path[-1] == (20, 5)


def test_storm_field_goes_to_the_earliest_shelter_breaking_ties_by_lower_s(suit):
    gr = grid(np.zeros((21, 41)))
    sources = [(10, 0), (10, 40)]
    field = g.dijkstra(
        gr,
        suit,
        W_TIME,
        sources=sources,
        reverse=True,
        source_keys=[0.0, 0.0],
        tie_break=[0.9, 0.5],
    )
    assert g.follow_pointers(field, (10, 10))[-1] == (10, 0)  # nearer
    assert g.follow_pointers(field, (10, 20))[-1] == (10, 40)  # equal time: lower S wins


# --- D5: leg matrix ---


def test_leg_matrix_is_asymmetric_on_a_ramp_and_matches_astar(suit):
    z = np.tile(np.arange(50) * 0.25 * RES, (30, 1))
    gr = grid(z)
    pts = [(15, 2), (15, 47), (5, 25)]
    m = g.leg_matrix(gr, suit, W_TIME, pts)
    assert np.all(np.diag(m["minutes"]) == 0)
    assert m["minutes"][0, 1] > m["minutes"][1, 0]  # uphill leg is slower
    a = g.astar(gr, suit, W_TIME, pts[2], pts[0])
    assert m["grid_cost"][2, 0] == pytest.approx(a.cost, rel=1e-9)
    # the matrices describe the smoothed legs, which never cost more than the grid path
    assert m["cost"][2, 0] <= a.cost + 1e-9
    assert m["minutes"][2, 0] == pytest.approx(
        g.polyline_metrics(gr, suit, W_TIME, m["paths"][(2, 0)])["minutes"]
    )
    assert len(m["paths"][(0, 1)]) >= 2


def test_a_zero_length_segment_costs_nothing(suit):
    gr = grid(np.zeros((5, 5)))
    m = g.polyline_metrics(gr, suit, W_TIME, [(2, 2), (2, 2)])
    assert m == {"cost": 0.0, "minutes": 0.0, "consumables": 0.0, "dose": 0.0}
