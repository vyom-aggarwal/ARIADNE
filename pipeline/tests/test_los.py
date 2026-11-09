# Written with AI assistance (Claude Code). See AI_USE.md.
"""Line of sight (acceptance test C8)."""

import numpy as np
from affine import Affine

from ariadne.derive import los


def test_flat_ground_is_all_visible_and_a_wall_hides_what_is_behind():
    z = np.zeros((101, 101))
    vis = los.viewshed(z, 1.0, (50, 50), 3.0, 1.8, 40.0)
    assert vis[50, 50] and vis[50, 89] and vis[11, 11]
    z[:, 60] = 10.0  # a 10 m wall 10 m east of the observer
    vis = los.viewshed(z, 1.0, (50, 50), 3.0, 1.8, 40.0)
    assert vis[50, 60]  # the wall itself
    assert not vis[50, 70]  # behind it
    assert vis[50, 40]  # the other way


def test_pairwise_line_of_sight_is_symmetric_and_height_matters():
    z = np.zeros((50, 50))
    z[:, 25] = 1.5  # a 1.5 m ridge
    t = Affine(1, 0, 0, 0, -1, 50)
    a, b = (5.5, -25.5 + 50), (45.5, -25.5 + 50)
    assert not los.line_of_sight(z, t, a, b, 1.0, 1.0)
    assert los.line_of_sight(z, t, a, b, 1.8, 1.8)
    assert los.line_of_sight(z, t, a, b, 1.8, 1.8) == los.line_of_sight(z, t, b, a, 1.8, 1.8)
