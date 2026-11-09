# Written with AI assistance (Claude Code). See AI_USE.md.
"""Science transects and scores (acceptance test C10)."""

import numpy as np
import pytest

from ariadne.derive import ridges, science
from ariadne.derive.walkability import GO, NOGO

W = {"role": 0.4, "novelty": 0.3, "spectral": 0.15, "access": 0.15}


def ridge_scene(length=60):
    """One ridge running east-west at row 30 (3 m wide, 1.5 m tall) with hollows either side."""
    n = 61
    z = np.zeros((n, length + 20))
    cls = np.full(z.shape, ridges.HOLLOW, dtype=np.uint8)
    z[29:32, 10 : 10 + length] = 1.5
    z[28, 10 : 10 + length] = z[32, 10 : 10 + length] = 0.7  # flanks
    cls[28:33, 10 : 10 + length] = ridges.RIDGE
    walk = np.full(z.shape, GO, dtype=np.uint8)
    return z, cls, walk


def test_transects_only_on_long_crests_with_stations_at_the_right_distances():
    z, cls, walk = ridge_scene(60)
    tr = science.transects(cls, z, walk, None, 1.0, 25, 20, (1, 2), (3, 10), 2)
    assert len(tr) >= 2
    for t in tr:
        r0, c0, role = t["crest"]
        assert role == "crest"
        assert 1 <= t["wall"][2] <= 2 and 3 <= t["hollow"][2] <= 10
        assert cls[t["hollow"][0], t["hollow"][1]] == ridges.HOLLOW
        assert z[t["wall"][0], t["wall"][1]] < z[r0, c0]
    z, cls, walk = ridge_scene(12)  # too short
    assert science.transects(cls, z, walk, None, 1.0, 25, 20, (1, 2), (3, 10), 2) == []


def test_stations_avoid_no_go_ground_and_snap_to_fractures():
    z, cls, walk = ridge_scene(60)
    walk[:30, :] = NOGO  # the north side is off limits
    frac = np.zeros(z.shape, dtype=bool)
    frac[31, 10:70] = True  # a fracture along the crest
    tr = science.transects(cls, z, walk, frac, 1.0, 25, 20, (1, 2), (3, 10), 2)
    assert tr and all(t["hollow"][0] > 30 for t in tr)
    assert all(t["crest"][2] == "fracture" for t in tr)


def test_scores_are_weighted_means_of_available_terms():
    s, missing = science.score({"role": 1.0, "novelty": 0.5, "spectral": None, "access": 0.0}, W)
    assert missing == ["spectral"]
    assert s == pytest.approx((0.4 * 1.0 + 0.3 * 0.5) / 0.85)
    assert 0 <= s <= 1


def test_novelty_grows_with_distance_and_access_with_nearness():
    assert science.novelty(0, 200) == 0 and science.novelty(100, 200) == 0.5
    assert science.novelty(500, 200) == 1.0
    assert science.access(0, 30) == 1.0 and science.access(45, 30) == 0.0
    assert science.access(float("nan"), 30) is None
