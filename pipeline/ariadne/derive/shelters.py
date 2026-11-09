# Written with AI assistance (Claude Code). See AI_USE.md.
"""Radiation shelters and minutes-to-shelter (PROMPT.md 4.6). Label: MODELED.

Shelter cells have S at or below a threshold and are walkable; they count only in connected
zones of at least a minimum area. The rover (or habitat) can be added as a point shelter.
Minutes-to-shelter comes from a multi-source least-cost pass (scikit-image MCP, 8 neighbours,
diagonal steps weighted by their length) over seconds per metre = cost multiplier / speed.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage
from skimage.graph import MCP_Geometric

from ariadne.derive.walkability import NOGO


def shelter_zones(s, walk_class, s_max: float, min_area_m2: float, res: float) -> np.ndarray:
    cand = (np.asarray(s) <= s_max) & (np.asarray(walk_class) != NOGO)
    lab, n = ndimage.label(cand, structure=np.ones((3, 3)))
    if n == 0:
        return cand
    sizes = ndimage.sum(cand, lab, index=np.arange(1, n + 1)) * res * res
    keep = np.zeros(n + 1, dtype=bool)
    keep[1:] = sizes >= min_area_m2
    return keep[lab]


def minutes_to_shelter(
    cost_multiplier: np.ndarray,
    shelters: np.ndarray,
    res: float,
    speed_m_s: float,
    extra_sources: list[tuple[int, int]] | None = None,
) -> np.ndarray:
    """Least walking time (minutes) to any shelter cell or extra source; NaN if unreachable."""
    sec_per_m = np.asarray(cost_multiplier, dtype=np.float64) / speed_m_s
    costs = np.where(np.isfinite(sec_per_m), sec_per_m, np.inf)
    starts = [tuple(x) for x in np.argwhere(shelters & np.isfinite(costs))]
    for rc in extra_sources or []:
        starts.append(tuple(rc))
        costs[rc] = max(costs[rc], 1e-6) if np.isfinite(costs[rc]) else 1e-6
    if not starts:
        return np.full(costs.shape, np.nan, dtype=np.float32)
    mcp = MCP_Geometric(costs, fully_connected=True, sampling=(res, res))
    cum, _ = mcp.find_costs(starts)
    out = cum / 60.0
    out[~np.isfinite(out)] = np.nan
    return out.astype(np.float32)
