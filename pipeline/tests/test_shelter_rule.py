# Written with AI assistance (Claude Code). See AI_USE.md.
"""Shelter is the rover, wherever it is (test E11, team decision of 2026-11-10)."""

import numpy as np
import pytest

from ariadne.models import metabolic as mb
from ariadne.plan import constraints as cs
from ariadne.plan import graph as g
from ariadne.plan import relay
from ariadne.plan import relay_plan as rp

TIME_ONLY = rp.TIME_ONLY


def flat(h=30, w=80, res=2.0):
    z = np.zeros((h, w))
    return g.Grid(z, np.ones((h, w), bool), np.zeros((h, w)), np.ones((h, w)), np.zeros((h, w)),
                  res)  # fmt: skip


def rel_for(gr, cells, speed=1.0):
    cls = np.zeros(gr.z.shape, dtype=np.uint8)
    times = [relay.rover_times(cls, gr.res, {0: speed}, c) for c in cells]
    return {"cells": cells, "times": times,
            "drive_from_staging_min": [float(times[0].minutes[c]) for c in cells]}  # fmt: skip


def test_rover_walk_at_takes_the_larger_of_the_two_samples_around_t():
    f = [np.full((2, 2), v) for v in (1.0, 2.0, 3.0)]
    mv = (np.array([0.0, 0.5, 1.0]), f)
    assert cs.rover_walk_at(mv, (0, 0), 0.25) == 2.0
    assert cs.rover_walk_at(mv, (0, 0), 0.75) == 3.0
    assert cs.rover_walk_at(mv, (0, 0), 1.0) == 3.0  # arrived
    assert cs.rover_walk_at(mv, (0, 0), 9.0) == 3.0


def test_rover_track_samples_the_drive_every_step_and_ends_at_the_relay():
    gr = flat()
    rel = rel_for(gr, [(15, 40), (15, 5)])
    track = rp.rover_track(rel, 1, 0.5)
    times = np.array([x[0] for x in track])
    assert track[0][1] == (15, 40) and track[-1][1] == (15, 5)
    assert np.all(np.diff(times) > 0)
    assert np.diff(times).max() <= 0.5 + gr.res / 60.0 + 1e-9  # one cell's drive at most past
    assert times[-1] == pytest.approx(rel["drive_from_staging_min"][1])


def first_leg_worst(gr, suit, rover_to, crew_to):
    staging = (15, 40)
    rel = rel_for(gr, [staging, rover_to])
    walks = [f.time for f in rp.walk_fields(gr, suit, rel["cells"], 0.5)]
    mv = rp.moving_rover_fields(gr, suit, rel, walks, 0.5)
    leg = [staging, crew_to]
    home = g.dijkstra(gr, suit, rp.CONSUMABLES, [rover_to], reverse=True).consumables
    f = cs.Fields(gr, home, walks[1], np.ones(gr.z.shape, bool), True)
    lim = {"reserve_min": 0.0, "shelter_max_min": 99.0, "comm_shadow_max_min": 99.0,
           "sample_step_m": 5.0}  # fmt: skip
    moving = cs.check_route(f, suit, TIME_ONLY, [leg], [crew_to], 0.0, 0.0, 999.0, lim,
                            leg_fields=[f, f], first_leg_rover=mv[1])  # fmt: skip
    parked = cs.check_route(f, suit, TIME_ONLY, [leg], [crew_to], 0.0, 0.0, 999.0, lim,
                            leg_fields=[f, f])  # fmt: skip
    return moving, parked, walks


def test_first_leg_shelter_follows_the_driving_rover():
    gr, suit = flat(), mb.load_suit()
    # the rover drives alongside the crew to where they are going: the walk to it stays short,
    # shorter than to its destination from the start of the leg
    moving, parked, walks = first_leg_worst(gr, suit, (15, 75), (15, 72))
    assert moving["details"]["worst_minutes_to_shelter"] < walks[1][15, 40]
    worst_parked = parked["details"]["worst_minutes_to_shelter"]
    assert worst_parked == pytest.approx(walks[1][15, 40], abs=0.01)
    # the rover drives away while the crew walks the other way: worse than either end alone
    away, _, walks2 = first_leg_worst(gr, suit, (15, 5), (15, 60))
    assert away["details"]["worst_minutes_to_shelter"] > walks2[0][15, 60]
    samples = [x["minutes_to_rover"] for x in away["margins"]]
    # crew and rover start together: at most the rover's first half minute of driving away
    assert samples[0] <= 0.5 + 0.05 and samples[0] < max(samples)


def test_switch_shelter_is_the_farthest_point_of_the_drive():
    gr, suit = flat(), mb.load_suit()
    rel = rel_for(gr, [(15, 2), (15, 77)])
    node = {"points": [(3, 38), (4, 39), (5, 40)]}
    sh = rp.switch_shelter(gr, suit, [node], rel)
    f = g.dijkstra(gr, suit, TIME_ONLY, [(5, 40)]).time
    path = relay.drive_path(rel["times"][0], (15, 77))
    assert sh[0, 0, 1] == pytest.approx(max(f[c] for c in path))
    assert sh[0, 0, 1] >= max(f[15, 2], f[15, 77]) - 1e-9
    assert sh[0, 0, 0] == 0.0


def test_moving_marks_the_visit_where_the_rover_changes_relay():
    info = [{"node": 1, "relay": 0}] * 3 + [{"node": 2, "relay": 1}] * 3
    sw = np.zeros((2, 2, 2))
    sw[0, 0, 1] = 7.5
    visit, first = rp.moving([(1, 0), (2, 1)], info, sw, {1: "track"})
    assert visit == [None, None, 7.5, None, None, None]
    assert first is None  # the first transect is served from the staging point
    _, first = rp.moving([(2, 1)], info[3:], sw, {1: "track"})
    assert first == "track"


def test_a_visit_during_a_rover_move_counts_the_drive():
    gr, suit = flat(), mb.load_suit()
    f = cs.Fields(gr, np.zeros(gr.z.shape), np.zeros(gr.z.shape), np.ones(gr.z.shape, bool), True)
    lim = {"reserve_min": 0.0, "shelter_max_min": 5.0, "comm_shadow_max_min": 99.0,
           "sample_step_m": 5.0}  # fmt: skip
    legs = [[(15, 40), (15, 45)], [(15, 45), (15, 40)]]
    ok = cs.check_route(f, suit, TIME_ONLY, legs, [(15, 45)], 15.0, 15.0, 999.0, lim,
                        leg_fields=[f, f], visit_shelter=[4.0])  # fmt: skip
    bad = cs.check_route(f, suit, TIME_ONLY, legs, [(15, 45)], 15.0, 15.0, 999.0, lim,
                         leg_fields=[f, f], visit_shelter=[6.0])  # fmt: skip
    assert ok["checks"]["shelter"] == "pass" and bad["checks"]["shelter"] == "fail"
    assert bad["details"]["worst_minutes_to_shelter"] == 6.0
