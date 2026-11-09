# Written with AI assistance (Claude Code). See AI_USE.md.
"""The rover as a mobile comms relay (team decision, 2026-11-09).

The rover drives on its own cost surface: its walkability class sets its speed (PLACEHOLDER,
config/rovers.json) and no-go cells are impassable. A few relay sites it can reach are chosen
by greedy maximum coverage: each site's viewshed (3 m antenna to a 1.8 m helmet, line of sight
only) puts some transects wholly in sight, and the sites that add the most transect value win.
The rover moves between relay sites while the crew works a station that stays in sight of the
rover along the whole drive, and the drive must fit in that station visit.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from skimage.graph import MCP_Geometric

from ariadne.config import config_dir


def load_rover(profile: str = "default") -> dict:
    d = json.loads((config_dir() / "rovers.json").read_text(encoding="utf-8"))[profile]
    return {k: v["value"] for k, v in d.items() if isinstance(v, dict) and "value" in v}


@dataclass
class RoverTimes:
    minutes: np.ndarray  # driving minutes from the source (inf where unreachable)
    mcp: MCP_Geometric


def rover_times(cls: np.ndarray, res: float, speeds: dict, source) -> RoverTimes:
    """Driving minutes from `source` over a class grid (0 go, 1 caution; anything else is
    impassable), with the speed of each class in m/s; diagonal moves cost sqrt(2) more."""
    c = np.asarray(cls)
    sec_per_m = np.full(c.shape, np.inf)
    for k, v in speeds.items():
        sec_per_m[c == int(k)] = 1.0 / float(v)
    mcp = MCP_Geometric(sec_per_m, fully_connected=True, sampling=(res, res))
    cost, _ = mcp.find_costs([tuple(source)])
    return RoverTimes(np.where(np.isfinite(cost), cost / 60.0, np.inf), mcp)


def drive_path(times: RoverTimes, target) -> list[tuple[int, int]]:
    if not np.isfinite(times.minutes[tuple(target)]):
        return []
    return [tuple(map(int, p)) for p in times.mcp.traceback(tuple(target))]


def candidate_sites(reach: np.ndarray, staging, spacing: int, max_cells: float) -> list:
    """Rover-reachable cells on a grid `spacing` cells apart within `max_cells` of staging."""
    h, w = reach.shape
    r0, c0 = staging
    out = []
    for r in range(r0 % spacing, h, spacing):
        for c in range(c0 % spacing, w, spacing):
            if reach[r, c] and np.hypot(r - r0, c - c0) <= max_cells and (r, c) != tuple(staging):
                out.append((r, c))
    return out


def greedy_relays(sees: list[set], values: dict, k: int, base: set) -> list[int]:
    """Indices of up to k sites, each adding the most value of transects newly seen whole (the
    staging point already sees `base`). Stops early when no site adds anything."""
    covered = set(base)
    picked: list[int] = []
    for _ in range(k):
        best, gain = None, 0.0
        for i, s in enumerate(sees):
            if i in picked:
                continue
            add = sum(values[t] for t in s - covered)
            if add > gain + 1e-12:
                best, gain = i, add
        if best is None:
            break
        picked.append(best)
        covered |= sees[best]
    return picked


def switch_feasible(drive_min: float, service_min: float, path, station, los: Callable) -> bool:
    """The rover may move during a station visit if the drive fits the visit and the station
    stays in line of sight of the rover at every sampled point of the drive."""
    if not np.isfinite(drive_min) or drive_min > service_min + 1e-9:
        return False
    return all(los(tuple(p), tuple(station)) for p in path)


def sees_transect(view: np.ndarray, points) -> bool:
    return all(bool(view[tuple(p)]) for p in points)
