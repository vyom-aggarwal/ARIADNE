# Written with AI assistance (Claude Code). See AI_USE.md.
"""Transects as routing nodes (test D14): a node is a whole fracture-wall-hollow transect, with
its three station visits and its internal walk in the service time, and a route expands back
into complete triples in that order."""

import numpy as np
import pytest

from ariadne.plan import transects as tr


def node(i, base):
    return {
        "transect": i,
        "points": [(base, base), (base, base + 1), (base, base + 3)],
        "roles": ["fracture", "wall", "hollow"],
        "scores": [0.9, 0.8, 0.7],
        "value": 2.4,
    }


def test_node_service_counts_three_visits_and_the_internal_walk():
    internal = [{"minutes": 1.5, "consumables": 1.8}, {"minutes": 2.5, "consumables": 2.0}]
    s = tr.node_service(internal, service_min=15.0, station_rate_ratio=0.6)
    assert s["minutes"] == pytest.approx(45.0 + 4.0)
    assert s["consumables"] == pytest.approx(27.0 + 3.8)


def test_roles_are_ordered_fracture_or_crest_then_wall_then_hollow():
    pts = [("hollow", (3, 3), 0.5), ("crest", (1, 1), 0.9), ("wall", (2, 2), 0.7)]
    roles, cells, scores = tr.order_transect(pts)
    assert roles == ["crest", "wall", "hollow"] and cells == [(1, 1), (2, 2), (3, 3)]
    assert scores == [0.9, 0.7, 0.5]
    assert tr.order_transect([("wall", (2, 2), 0.7), ("hollow", (3, 3), 0.5)]) is None


def test_route_expands_into_complete_triples_with_internal_legs():
    nodes = [node(7, 10), node(9, 20)]
    staging = (0, 0)
    leg = {(0, 1): [staging, (10, 10)], (1, 2): [(10, 13), (20, 20)], (2, 0): [(20, 23), staging]}
    internal = {1: [[(10, 10), (10, 11)], [(10, 11), (10, 13)]],
                2: [[(20, 20), (20, 21)], [(20, 21), (20, 23)]]}  # fmt: skip
    legs, stations, info = tr.expand_route([0, 1, 2, 0], nodes, leg, internal)
    assert stations == [(10, 10), (10, 11), (10, 13), (20, 20), (20, 21), (20, 23)]
    assert len(legs) == 7  # out, 2 internal, between, 2 internal, home
    assert [i["role"] for i in info] == ["fracture", "wall", "hollow"] * 2
    assert [i["transect"] for i in info] == [7, 7, 7, 9, 9, 9]
    for a, b in zip(legs[:-1], legs[1:], strict=True):
        assert a[-1] == b[0]  # each leg starts where the last ended


def test_transect_objective_counts_complete_transects_first():
    values = np.array([2.7, 1.2, 2.9])
    obj = tr.objective_values(values, "transects")
    # any extra transect beats any gain in value among the same number of transects
    assert obj[1] > 0.99 and obj.max() < 1.01
    assert obj[2] > obj[0] > obj[1]
    assert np.array_equal(tr.objective_values(values, "value"), values)
