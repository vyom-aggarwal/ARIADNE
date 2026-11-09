# Written with AI assistance (Claude Code). See AI_USE.md.
"""The rover as a mobile comms relay (tests F1 to F4)."""

import itertools

import numpy as np
import pytest

from ariadne.models import metabolic as mb
from ariadne.plan import constraints as cs
from ariadne.plan import graph as g
from ariadne.plan import relay, select

# --- F1: choosing relay sites ---


def test_greedy_coverage_picks_the_best_sets():
    # transect values and which candidate site sees each transect whole
    values = {0: 3.0, 1: 2.0, 2: 2.0, 3: 1.0}
    sees = [{0}, {1, 2}, {0, 3}, {3}]
    base = {0}  # the staging point already sees transect 0
    picked = relay.greedy_relays(sees, values, k=2, base=base)
    # first +4.0 (transects 1 and 2); then sites 2 and 3 tie at +1.0 (transect 3) and the
    # lower index wins
    assert picked == [1, 2]
    assert relay.greedy_relays(sees, values, k=5, base=base) == [1, 2]  # stops when nothing gains


def test_candidate_sites_are_reachable_by_the_rover_only():
    reach = np.zeros((40, 40), bool)
    reach[:, :20] = True
    sites = relay.candidate_sites(reach, staging=(20, 5), spacing=5, max_cells=30)
    assert sites and all(reach[r, c] for r, c in sites)
    assert all(np.hypot(r - 20, c - 5) <= 30 for r, c in sites)


def test_rover_times_follow_class_speeds():
    cls = np.zeros((5, 50), dtype=np.int16)
    cls[:, 25:] = 1  # caution on the east half
    t = relay.rover_times(cls, res=2.0, speeds={0: 1.0, 1: 0.5}, source=(2, 0))
    assert t.minutes[2, 24] == pytest.approx(24 * 2.0 / 1.0 / 60, rel=0.05)
    assert t.minutes[2, 49] > t.minutes[2, 24] + 24 * 2.0 / 0.5 / 60 * 0.9
    blocked = cls.copy()
    blocked[:, 10] = 2  # a no-go wall
    assert np.isinf(relay.rover_times(blocked, 2.0, {0: 1.0, 1: 0.5}, (2, 0)).minutes[2, 20])


# --- F2: moving the rover between relays ---


def test_a_move_needs_time_and_line_of_sight_all_the_way():
    path = [(0, 0), (0, 5), (0, 10)]
    always = lambda rover, station: True  # noqa: E731
    never_mid = lambda rover, station: rover != (0, 5)  # noqa: E731
    assert relay.switch_feasible(12.0, 15.0, path, (5, 5), always)
    assert not relay.switch_feasible(16.0, 15.0, path, (5, 5), always)
    assert not relay.switch_feasible(12.0, 15.0, path, (5, 5), never_mid)


# --- F3: groups and a separate end in the routing problem ---


def grouped_problem(seed=0):
    rng = np.random.default_rng(seed)
    # node 0 start, nodes 1..6 = three transects x two relays, node 7 = END
    n = 8
    minutes = rng.uniform(5, 30, (n, n))
    minutes[:, 0] = np.inf  # nothing returns to the start
    minutes[7, :] = np.inf
    np.fill_diagonal(minutes, 0.0)
    value = np.array([0.0, 1.0, 1.0, 0.8, 0.8, 0.6, 0.6, 0.0])
    return select.Problem(
        value=value, service_min=np.r_[0, np.full(6, 20.0), 0],
        service_cons=np.r_[0, np.full(6, 12.0), 0], minutes=minutes, consumables=minutes * 1.1,
        cost=minutes, eva_max_min=110.0, consumables_budget=120.0,
        groups=[[1, 2], [3, 4], [5, 6]], end_node=7,
    )  # fmt: skip


def brute(p):
    best = 0.0
    nodes = list(range(1, 7))
    for k in range(0, 4):
        for seq in itertools.permutations(nodes, k):
            groups = [next(i for i, gr in enumerate(p.groups) if s in gr) for s in seq]
            if len(set(groups)) < len(groups):
                continue
            t, c = select.route_totals(p, [0, *seq, 7])
            if t <= p.eva_max_min + 1e-9 and c <= p.consumables_budget + 1e-9:
                best = max(best, float(p.value[list(seq)].sum()))
    return best


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_grouped_routing_with_a_separate_end(seed):
    p = grouped_problem(seed)
    sol = select.solve(p, time_limit_s=1.0)
    assert sol.route[0] == 0 and sol.route[-1] == 7
    inner = sol.route[1:-1]
    assert len({next(i for i, gr in enumerate(p.groups) if s in gr) for s in inner}) == len(inner)
    assert sol.value == pytest.approx(brute(p), abs=1e-9)


# --- F4: the thread follows the rover ---


def test_thread_follows_the_rover_and_is_conservative_during_a_move():
    suit = mb.load_suit()
    n = 40
    z = np.zeros((n, n))
    gr = g.Grid(z, np.ones((n, n), bool), np.zeros((n, n)), np.zeros((n, n)), np.zeros((n, n)), 2.0)
    w = {"time": 1.0, "metabolic": 0.5, "hazard": 0.0, "dose": 0.0, "uncertainty": 0.0}
    cons = {"time": 0.0, "metabolic": 1.0, "hazard": 0.0, "dose": 0.0, "uncertainty": 0.0}
    tim = {"time": 1.0, "metabolic": 0.0, "hazard": 0.0, "dose": 0.0, "uncertainty": 0.0}
    a, b = (20, 2), (20, 37)  # two relay sites, west and east

    def fields(site):
        home = g.dijkstra(gr, suit, cons, [site], reverse=True).consumables
        sh = g.dijkstra(gr, suit, tim, [site], reverse=True).time
        return cs.Fields(gr, home, sh, np.ones((n, n), bool), True)

    fa, fb = fields(a), fields(b)
    # walk from relay a to a station in the middle (rover at a), the rover moves to b during the
    # station visit, then walk on to relay b, where the thread ends
    st = (20, 20)
    legs = [[a, st], [st, b]]
    limits = {"reserve_min": 30.0, "shelter_max_min": 60.0, "comm_shadow_max_min": 10.0,
              "sample_step_m": 5.0}  # fmt: skip
    res = cs.check_route(fa, suit, w, legs, [st], 15.0, 9.0, 200.0, limits, leg_fields=[fa, fb])
    m = res["margins"]
    assert m[0]["c_home"] == pytest.approx(0.0, abs=1e-6)  # at relay a
    assert m[-1]["c_home"] == pytest.approx(0.0, abs=1e-6)  # the walk ends at the rover (b)
    at_station = [x for x in m if x["xy_cell"] == [20.0, 20.0]]
    expect = max(float(fa.c_home[st]), float(fb.c_home[st]))
    assert max(x["c_home"] for x in at_station) == pytest.approx(expect, abs=1e-3)
    assert res["checks"]["thread"] == "pass"
