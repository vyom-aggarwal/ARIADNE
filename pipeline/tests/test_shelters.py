# Written with AI assistance (Claude Code). See AI_USE.md.
"""Shelters and minutes-to-shelter (acceptance test C7)."""

import math

import numpy as np
import pytest

from ariadne.derive import shelters
from ariadne.derive.walkability import CAUTION, GO, NOGO


def test_small_or_unwalkable_zones_are_dropped():
    s = np.ones((20, 20))
    s[2:4, 2:4] = 0.9  # 4 m2: kept
    s[10, 10] = 0.9  # 1 m2: dropped
    s[15:18, 15:18] = 0.9  # 9 m2 but no-go: dropped
    walk = np.full((20, 20), GO, dtype=np.uint8)
    walk[15:18, 15:18] = NOGO
    walk[3, 3] = CAUTION  # caution is still walkable
    z = shelters.shelter_zones(s, walk, 0.95, 4.0, 1.0)
    assert z[2:4, 2:4].all()
    assert not z[10, 10] and not z[15:18, 15:18].any()


def test_minutes_on_flat_ground_equal_distance_over_speed():
    cost = np.ones((41, 41), dtype=np.float32)
    shel = np.zeros((41, 41), dtype=bool)
    shel[20, 20] = True
    m = shelters.minutes_to_shelter(cost, shel, 1.0, 0.5)
    assert m[20, 20] == pytest.approx(0.0)
    assert m[20, 40] == pytest.approx(20 / 0.5 / 60, rel=1e-6)  # straight
    assert m[0, 0] == pytest.approx(20 * math.sqrt(2) / 0.5 / 60, rel=1e-6)  # diagonal


def test_rover_counts_as_a_shelter_and_walls_block():
    cost = np.ones((21, 21), dtype=np.float32)
    cost[:, 10] = np.nan  # a no-go wall
    shel = np.zeros((21, 21), dtype=bool)
    m = shelters.minutes_to_shelter(cost, shel, 1.0, 1.0, extra_sources=[(10, 2)])
    assert m[10, 2] == pytest.approx(0.0)
    assert m[10, 5] == pytest.approx(3 / 60)
    assert np.isnan(m[10, 15])  # unreachable behind the wall
