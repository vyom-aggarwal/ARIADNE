# Written with AI assistance (Claude Code). See AI_USE.md.
"""Station selection as prize-collecting routing (PROMPT.md 5.8): the OR-Tools reference.

Node 0 is the staging point (the rover), where the walk starts and ends. Every other node is an
optional station: skipping it costs its science value times `value_weight`, and visiting it adds
its service time and consumables. The route must fit the EVA time limit and the consumables
budget (consumables at the start, less the reserve). OR-Tools minimises the preset-weighted walking
cost plus the value of the skipped stations, so with a large `value_weight` it maximises science
value and uses cost only to break ties.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SCALE = 100  # OR-Tools works in integers: hundredths of a minute or cost unit


@dataclass
class Problem:
    value: np.ndarray  # per node; node 0 (staging) is 0
    service_min: np.ndarray
    service_cons: np.ndarray
    minutes: np.ndarray  # leg matrices, from row node to column node
    consumables: np.ndarray
    cost: np.ndarray
    eva_max_min: float
    consumables_budget: float
    value_weight: float = 1e6


@dataclass
class Solution:
    route: list[int]
    value: float
    minutes: float
    consumables: float
    cost: float
    status: str


def route_totals(p: Problem, route: list[int]) -> tuple[float, float]:
    """EVA minutes and consumables of a route, with service at every visited station."""
    t = c = 0.0
    for a, b in zip(route[:-1], route[1:], strict=True):
        t += p.minutes[a, b]
        c += p.consumables[a, b]
    for k in route[1:-1]:
        t += p.service_min[k]
        c += p.service_cons[k]
    return float(t), float(c)


def solve(p: Problem, time_limit_s: float = 5.0, first_solution_only: bool = False) -> Solution:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    n = len(p.value)
    big = 10**9  # unreachable legs
    mins = np.where(np.isfinite(p.minutes), p.minutes, big / SCALE)
    cons = np.where(np.isfinite(p.consumables), p.consumables, big / SCALE)
    cost = np.where(np.isfinite(p.cost), p.cost, big / SCALE)
    t_arc = np.rint((mins + p.service_min[:, None]) * SCALE).astype(np.int64)
    c_arc = np.rint((cons + p.service_cons[:, None]) * SCALE).astype(np.int64)
    k_arc = np.rint(cost * SCALE).astype(np.int64)
    for a in (t_arc, c_arc, k_arc):
        np.fill_diagonal(a, 0)
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def cb(mat):
        def f(i, j):
            return int(mat[manager.IndexToNode(i), manager.IndexToNode(j)])

        return routing.RegisterTransitCallback(f)

    routing.SetArcCostEvaluatorOfAllVehicles(cb(k_arc))
    routing.AddDimension(cb(t_arc), 0, int(np.floor(p.eva_max_min * SCALE)), True, "time")
    routing.AddDimension(
        cb(c_arc), 0, int(np.floor(p.consumables_budget * SCALE)), True, "consumables"
    )
    for node in range(1, n):
        penalty = int(round(p.value[node] * p.value_weight * SCALE))
        routing.AddDisjunction([manager.NodeToIndex(node)], max(penalty, 0))
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    if not first_solution_only:
        params.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        params.time_limit.FromMilliseconds(int(time_limit_s * 1000))
    sol = routing.SolveWithParameters(params)
    if sol is None:
        return Solution([0, 0], 0.0, 0.0, 0.0, 0.0, "no solution")
    route = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        route.append(manager.IndexToNode(idx))
        idx = sol.Value(routing.NextVar(idx))
    route.append(0)
    t, c = route_totals(p, route)
    k = float(sum(p.cost[a, b] for a, b in zip(route[:-1], route[1:], strict=True)))
    return Solution(route, float(p.value[route[1:-1]].sum()), t, c, k, "ok")
