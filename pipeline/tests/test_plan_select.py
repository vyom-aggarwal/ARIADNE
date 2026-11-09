# Written with AI assistance (Claude Code). See AI_USE.md.
"""Station selection with OR-Tools (test D6): prize-collecting routing with time and
consumables budgets, checked against brute force on small cases."""

import itertools

import numpy as np
import pytest

from ariadne.plan import select


def random_problem(n=6, seed=0, eva=120.0, cons=110.0, lam=1e6):
    rng = np.random.default_rng(seed)
    xy = rng.uniform(0, 400, (n + 1, 2))
    d = np.hypot(*(xy[:, None, :] - xy[None, :, :]).transpose(2, 0, 1))
    minutes = d / 60.0 * (1 + 0.3 * rng.random((n + 1, n + 1)))  # asymmetric
    np.fill_diagonal(minutes, 0.0)
    return select.Problem(
        value=np.r_[0.0, rng.uniform(0.2, 1.0, n)],
        service_min=np.r_[0.0, np.full(n, 15.0)],
        service_cons=np.r_[0.0, np.full(n, 9.0)],
        minutes=minutes,
        consumables=minutes * 1.2,
        cost=minutes * 1.5,
        eva_max_min=eva,
        consumables_budget=cons,
        value_weight=lam,
    )


def brute_force_best_value(p):
    n = len(p.value) - 1
    best = 0.0
    for k in range(1, n + 1):
        for sub in itertools.permutations(range(1, n + 1), k):
            route = [0, *sub, 0]
            t, c = select.route_totals(p, route)
            if t <= p.eva_max_min + 1e-9 and c <= p.consumables_budget + 1e-9:
                best = max(best, float(p.value[list(sub)].sum()))
    return best


@pytest.mark.parametrize("seed", range(4))
def test_ortools_finds_the_brute_force_optimum(seed):
    p = random_problem(seed=seed)
    sol = select.solve(p, time_limit_s=1.0)
    assert sol.value == pytest.approx(brute_force_best_value(p), abs=1e-9)
    t, c = select.route_totals(p, sol.route)
    assert t <= p.eva_max_min + 1e-6 and c <= p.consumables_budget + 1e-6
    assert sol.route[0] == 0 and sol.route[-1] == 0


def test_tight_budget_visits_nothing_and_loose_budget_visits_all():
    p = random_problem(eva=5.0, cons=5.0)
    assert select.solve(p, time_limit_s=0.5).route == [0, 0]
    p = random_problem(eva=10_000.0, cons=10_000.0)
    assert sorted(select.solve(p, time_limit_s=0.5).route[1:-1]) == list(range(1, 7))


def test_a_low_value_weight_skips_stations_not_worth_their_cost():
    p = random_problem(eva=10_000.0, cons=10_000.0, lam=1.0)
    sol = select.solve(p, time_limit_s=0.5)
    assert len(sol.route) == 2  # each station costs more than it is worth at lam = 1


def test_route_totals_include_service_at_each_station():
    p = random_problem()
    t, c = select.route_totals(p, [0, 1, 0])
    assert t == pytest.approx(p.minutes[0, 1] + 15.0 + p.minutes[1, 0])
    assert c == pytest.approx(p.consumables[0, 1] + 9.0 + p.consumables[1, 0])
