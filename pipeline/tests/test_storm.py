# Written with AI assistance (Claude Code). See AI_USE.md.
"""Storm mode by lowest modeled dose (test D15, team decision of 2026-11-10)."""

import numpy as np
import pytest

from ariadne.models import metabolic as mb
from ariadne.plan import graph as g
from ariadne.plan import storm


def test_event_dose_counts_the_exposed_walk_then_the_refuge():
    # 10 minutes walking at S 1 (dose 10), then 110 minutes at S 0.5
    assert storm.event_dose(10.0, 10.0, 0.5, 120.0) == pytest.approx(10.0 + 110.0 * 0.5)
    # a walk longer than the event is cut at the event's end
    assert storm.event_dose(240.0, 200.0, 0.5, 120.0) == pytest.approx(100.0)
    assert storm.event_dose(0.0, 0.0, 0.9, 120.0) == pytest.approx(108.0)  # staying put


def test_the_lowest_dose_wins_not_the_earliest_arrival():
    options = [
        {"name": "stay", "walk_min": 0.0, "walk_dose": 0.0, "s_dest": 1.0},
        {"name": "terrain", "walk_min": 2.0, "walk_dose": 2.0, "s_dest": 0.9},
        {"name": "rover", "walk_min": 15.0, "walk_dose": 15.0, "s_dest": 0.5},
    ]
    best = storm.choose(options, 120.0)
    assert best["name"] == "rover"  # 15 + 105 x 0.5 = 67.5, against 2 + 118 x 0.9 = 108.2
    assert storm.choose(options, 10.0)["name"] == "terrain"  # a short event: 2 + 8 x 0.9 = 9.2
    far = [options[0], {**options[2], "walk_min": 300.0, "walk_dose": 300.0}]
    assert storm.choose(far, 120.0)["name"] == "stay"


def test_response_on_a_grid_follows_the_fastest_path_to_the_chosen_refuge():
    suit = mb.load_suit()
    n = 60
    z = np.zeros((n, n))
    s = np.ones((n, n))
    s[30, 50] = 0.8  # one shielded terrain cell
    gr = g.Grid(z, np.ones((n, n), bool), np.zeros((n, n)), s, np.zeros((n, n)), 2.0)
    rover, terrain = (30, 2), [(30, 50)]
    f = storm.refuge_fields(gr, suit, rover, 0.5, terrain, [0.8])
    near_rover = storm.response(gr, f, (30, 5), 0.5, 120.0)
    assert near_rover["choice"] == "rover" and near_rover["path"][-1] == rover
    # a 1-minute event: the rover (92 m) cannot be reached in time, the terrain cell (4 m) can
    near_terrain = storm.response(gr, f, (30, 48), 0.5, 1.0)
    assert near_terrain["choice"] == "terrain" and near_terrain["path"][-1] == (30, 50)
    assert near_terrain["dose"] < near_terrain["dose_staying"]
    assert near_rover["dose_avoided"] == pytest.approx(
        near_rover["dose_staying"] - near_rover["dose"]
    )


def test_track_samples_the_plan_and_carries_the_line_home():
    suit = mb.load_suit()
    n = 40
    gr = g.Grid(np.zeros((n, n)), np.ones((n, n), bool), np.zeros((n, n)), np.ones((n, n)),
                np.zeros((n, n)), 2.0)  # fmt: skip
    rover = (20, 2)
    walk_f = [g.dijkstra(gr, suit, storm.TIME_ONLY, [rover], reverse=True, tie_break=[0.5])]
    margins = [
        {"t_min": float(t), "xy_cell": [20.0, 2.0 + 3 * t], "leg": 0, "station": None}
        for t in range(12)
    ]
    out = storm.track(gr, margins, [0], {}, walk_f, None, 0.5, 120.0, 5.0,
                      lambda r, c: [float(c), float(-r)])  # fmt: skip
    assert [x["t_min"] for x in out] == [0.0, 5.0, 10.0]
    for x in out:
        assert x["home_path_xy_m"][-1] == [2.0, -20.0]  # ends at the rover
        assert x["home_walk_min"] >= 0 and x["choice"] in {"rover", "stay"}
    assert out[0]["home_walk_min"] == 0.0 and out[-1]["home_walk_min"] > out[1]["home_walk_min"]
