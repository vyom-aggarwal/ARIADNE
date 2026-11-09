# Written with AI assistance (Claude Code). See AI_USE.md.
"""Route graph on the DEM grid (PROMPT.md 5.1, 5.3, 5.5 to 5.7).

Cells are nodes; each cell links to 16 neighbours (the 8 adjacent cells and the 8 knight
moves). A move may not cut a corner: a diagonal needs both cells beside it, and a knight move
needs the two cells its segment crosses. The cost of a move from a to b depends on the signed
grade (z_b - z_a) / L through the walker model, so uphill and downhill differ:

    c(e) = dt [w_t + w_m M/M_nom + w_r R + w_d D + w_u U]

with dt in minutes at the model pace, M/M_nom the metabolic rate relative to the nominal rate,
and R (hazard), D (relative dose rate) and U (uncertainty) averaged over the two cells. Time,
consumables (minutes at the nominal rate, dt M/M_nom) and dose (dt D) are summed alongside.

`dijkstra` runs from one or more sources, forward (cost of leaving the sources) or on the
reversed graph (cost of reaching them, as for cost-to-home and storm fields). `astar` finds one
path with the heuristic straight-line distance x the least cost per metre any move can have.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import numpy as np
from numba import njit

from ariadne.models import metabolic as mb

OFFSETS = np.array(
    [
        (0, 1), (1, 0), (0, -1), (-1, 0),
        (1, 1), (1, -1), (-1, 1), (-1, -1),
        (1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1),
    ],
    dtype=np.int64,
)  # fmt: skip
WEIGHT_KEYS = ("time", "metabolic", "hazard", "dose", "uncertainty")
CW = np.array(mb.MINETTI_CW, dtype=np.float64)


@dataclass
class Grid:
    z: np.ndarray
    passable: np.ndarray
    hazard: np.ndarray
    dose: np.ndarray
    unc: np.ndarray
    res: float


@dataclass
class Field:
    cost: np.ndarray
    time: np.ndarray
    consumables: np.ndarray
    dose: np.ndarray
    pred: np.ndarray  # offset index used to reach each cell (-1 at sources and unreached)


@dataclass
class Path:
    cost: float
    time: float
    consumables: float
    dose: float
    path: list[tuple[int, int]]


def _suit_vec(suit: mb.Suit) -> np.ndarray:
    return np.array(
        [suit.suit_gravity_factor, suit.max_speed_m_s, suit.power_ceiling_w_kg,
         mb.nominal_rate(suit)],
        dtype=np.float64,
    )  # fmt: skip


def _w_vec(w: dict) -> np.ndarray:
    return np.array([float(w[k]) for k in WEIGHT_KEYS], dtype=np.float64)


@njit(cache=True)
def _move(za, zb, length, sv):
    """Minutes and rate ratio for walking `length` metres from height za to zb."""
    i = (zb - za) / length
    if i < -0.45:
        i = -0.45
    elif i > 0.45:
        i = 0.45
    cw = ((((CW[0] * i + CW[1]) * i + CW[2]) * i + CW[3]) * i + CW[4]) * i + CW[5]
    cw *= sv[0]
    v = sv[1]
    if sv[2] / cw < v:
        v = sv[2] / cw
    return length / v / 60.0, cw * v / sv[3]


@njit(cache=True)
def _clear(passable, r, c, dr, dc):
    adr, adc = abs(dr), abs(dc)
    if adr == 1 and adc == 1:
        return passable[r + dr, c] and passable[r, c + dc]
    if adr == 1 and adc == 2:
        sc = 1 if dc > 0 else -1
        return passable[r, c + sc] and passable[r + dr, c + sc]
    if adr == 2 and adc == 1:
        sr = 1 if dr > 0 else -1
        return passable[r + sr, c] and passable[r + sr, c + dc]
    return True


@njit(cache=True)
def _search(z, passable, hazard, dose, unc, res, wv, sv, offs, src, src_key, src_tie, reverse,
            max_cost, tr, tc, hmin):  # fmt: skip
    h, w = z.shape
    n = h * w
    cost = np.full(n, np.inf)
    tim = np.zeros(n)
    con = np.zeros(n)
    dos = np.zeros(n)
    tie = np.full(n, np.inf)
    pred = np.full(n, -1, dtype=np.int8)
    done = np.zeros(n, dtype=np.bool_)
    heap = [(0.0, 0.0, np.int64(0))]
    heap.pop()
    for s in range(src.shape[0]):
        k = src[s, 0] * w + src[s, 1]
        if src_key[s] < cost[k] or (src_key[s] == cost[k] and src_tie[s] < tie[k]):
            cost[k] = src_key[s]
            tie[k] = src_tie[s]
            hk = 0.0
            if tr >= 0:
                hk = hmin * res * math.hypot(src[s, 0] - tr, src[s, 1] - tc)
            heapq.heappush(heap, (cost[k] + hk, tie[k], np.int64(k)))
    lens = np.empty(offs.shape[0])
    for m in range(offs.shape[0]):
        lens[m] = res * math.hypot(offs[m, 0], offs[m, 1])
    while len(heap) > 0:
        _, _, k = heapq.heappop(heap)
        if done[k]:
            continue
        done[k] = True
        r, c = k // w, k % w
        if tr >= 0 and r == tr and c == tc:
            break
        if cost[k] > max_cost:
            continue
        for m in range(offs.shape[0]):
            dr, dc = offs[m, 0], offs[m, 1]
            rr, cc = r + dr, c + dc
            if rr < 0 or rr >= h or cc < 0 or cc >= w:
                continue
            if not passable[rr, cc] or not _clear(passable, r, c, dr, dc):
                continue
            kk = rr * w + cc
            if done[kk]:
                continue
            if reverse:
                dt, ratio = _move(z[rr, cc], z[r, c], lens[m], sv)
            else:
                dt, ratio = _move(z[r, c], z[rr, cc], lens[m], sv)
            hz = 0.5 * (hazard[r, c] + hazard[rr, cc])
            dd = 0.5 * (dose[r, c] + dose[rr, cc])
            uu = 0.5 * (unc[r, c] + unc[rr, cc])
            nc = cost[k] + dt * (wv[0] + wv[1] * ratio + wv[2] * hz + wv[3] * dd + wv[4] * uu)
            better = nc < cost[kk] - 1e-12 * (1.0 + nc)
            same = abs(nc - cost[kk]) <= 1e-12 * (1.0 + nc) and tie[k] < tie[kk]
            if better or same:
                cost[kk] = nc
                tie[kk] = tie[k]
                tim[kk] = tim[k] + dt
                con[kk] = con[k] + dt * ratio
                dos[kk] = dos[k] + dt * dd
                pred[kk] = m
                hk = 0.0
                if tr >= 0:
                    hk = hmin * res * math.hypot(rr - tr, cc - tc)
                heapq.heappush(heap, (nc + hk, tie[kk], np.int64(kk)))
    return cost, tim, con, dos, pred


def dijkstra(
    gr: Grid,
    suit: mb.Suit,
    w: dict,
    sources,
    reverse: bool = False,
    source_keys=None,
    tie_break=None,
    max_cost: float = np.inf,
) -> Field:
    src = np.array(sources, dtype=np.int64).reshape(-1, 2)
    keys = np.zeros(len(src)) if source_keys is None else np.asarray(source_keys, float)
    ties = np.zeros(len(src)) if tie_break is None else np.asarray(tie_break, float)
    cost, tim, con, dos, pred = _search(
        np.ascontiguousarray(gr.z, dtype=np.float64), np.ascontiguousarray(gr.passable),
        np.ascontiguousarray(gr.hazard, dtype=np.float64),
        np.ascontiguousarray(gr.dose, dtype=np.float64),
        np.ascontiguousarray(gr.unc, dtype=np.float64), float(gr.res), _w_vec(w),
        _suit_vec(suit), OFFSETS, src, keys, ties, reverse, float(max_cost), -1, -1, 0.0,
    )  # fmt: skip
    s = gr.z.shape
    return Field(cost.reshape(s), tim.reshape(s), con.reshape(s), dos.reshape(s), pred.reshape(s))


def min_cost_per_metre(suit: mb.Suit, w: dict) -> float:
    """A lower bound on any move's cost per metre (hazard, dose and uncertainty are >= 0)."""
    i = np.linspace(-0.45, 0.45, 9001)
    v = mb.speed(i, suit)
    ratio = mb.metabolic_rate(i, v, suit) / mb.nominal_rate(suit)
    per_m = (w["time"] + w["metabolic"] * ratio) / (60.0 * v)
    return 0.999 * float(per_m.min())


def extract_path(field: Field, target) -> list[tuple[int, int]]:
    """Cells from the source to `target` (forward field), following the predecessors back."""
    r, c = target
    if not np.isfinite(field.cost[r, c]):
        return []
    out = [(int(r), int(c))]
    while field.pred[r, c] >= 0:
        dr, dc = OFFSETS[field.pred[r, c]]
        r, c = r - dr, c - dc
        out.append((int(r), int(c)))
    return out[::-1]


def follow_pointers(field: Field, start) -> list[tuple[int, int]]:
    """Cells from `start` to the source it reaches (reverse field: pointers are next steps)."""
    return extract_path(field, start)[::-1]


def astar(gr: Grid, suit: mb.Suit, w: dict, start, goal) -> Path | None:
    src = np.array([start], dtype=np.int64)
    cost, tim, con, dos, pred = _search(
        np.ascontiguousarray(gr.z, dtype=np.float64), np.ascontiguousarray(gr.passable),
        np.ascontiguousarray(gr.hazard, dtype=np.float64),
        np.ascontiguousarray(gr.dose, dtype=np.float64),
        np.ascontiguousarray(gr.unc, dtype=np.float64), float(gr.res), _w_vec(w),
        _suit_vec(suit), OFFSETS, src, np.zeros(1), np.zeros(1), False, np.inf,
        int(goal[0]), int(goal[1]), min_cost_per_metre(suit, w),
    )  # fmt: skip
    s = gr.z.shape
    f = Field(cost.reshape(s), tim.reshape(s), con.reshape(s), dos.reshape(s), pred.reshape(s))
    r, c = goal
    if not np.isfinite(f.cost[r, c]):
        return None
    return Path(
        float(f.cost[r, c]), float(f.time[r, c]), float(f.consumables[r, c]),
        float(f.dose[r, c]), extract_path(f, goal),
    )  # fmt: skip


# --- straight segments: clearance, metrics and smoothing ---

_OFFSET_INDEX = {(int(a), int(b)): k for k, (a, b) in enumerate(OFFSETS)}


@njit(cache=True)
def _bilin(z, r, c):
    h, w = z.shape
    r = min(max(r, 0.0), h - 1.0)
    c = min(max(c, 0.0), w - 1.0)
    r0 = min(int(math.floor(r)), h - 2)
    c0 = min(int(math.floor(c)), w - 2)
    fr, fc = r - r0, c - c0
    return (
        z[r0, c0] * (1 - fr) * (1 - fc) + z[r0, c0 + 1] * (1 - fr) * fc
        + z[r0 + 1, c0] * fr * (1 - fc) + z[r0 + 1, c0 + 1] * fr * fc
    )  # fmt: skip


@njit(cache=True)
def _seg_walk(z, hazard, dose, unc, res, wv, sv, r0, c0, r1, c1, single):
    """Running totals at each step of a straight walk from (r0, c0) to (r1, c1): one step with
    cell heights for a single grid move, else steps of at most half a cell on the bilinear
    surface. Columns: r, c, cost, minutes, consumables, dose, metres."""
    h, w = z.shape
    dr, dc = r1 - r0, c1 - c0
    if single:
        n = 1
    else:
        n = max(1, int(math.ceil(max(abs(dr), abs(dc)) * 2)))
    out = np.empty((n, 7))
    acc = np.zeros(5)
    ra, ca = r0, c0
    za = z[int(r0), int(c0)] if single else _bilin(z, r0, c0)
    for s in range(1, n + 1):
        f = s / n
        rb, cb = r0 + dr * f, c0 + dc * f
        zb = z[int(r1), int(c1)] if single else _bilin(z, rb, cb)
        ia = (min(max(int(round(ra)), 0), h - 1), min(max(int(round(ca)), 0), w - 1))
        ib = (min(max(int(round(rb)), 0), h - 1), min(max(int(round(cb)), 0), w - 1))
        length = res * math.hypot(rb - ra, cb - ca)
        dt, ratio = _move(za, zb, length, sv)
        hz = 0.5 * (hazard[ia] + hazard[ib])
        dd = 0.5 * (dose[ia] + dose[ib])
        uu = 0.5 * (unc[ia] + unc[ib])
        acc[0] += dt * (wv[0] + wv[1] * ratio + wv[2] * hz + wv[3] * dd + wv[4] * uu)
        acc[1] += dt
        acc[2] += dt * ratio
        acc[3] += dt * dd
        acc[4] += length
        out[s - 1, 0] = rb
        out[s - 1, 1] = cb
        out[s - 1, 2:] = acc
        ra, ca, za = rb, cb, zb
    return out


@njit(cache=True)
def _seg_clear(passable, r0, c0, r1, c1):
    h, w = passable.shape
    n = max(2, int(math.ceil(max(abs(r1 - r0), abs(c1 - c0)) * 10)))
    for s in range(n + 1):
        f = s / n
        r, c = r0 + (r1 - r0) * f, c0 + (c1 - c0) * f
        for er in (-0.05, 0.05):
            for ec in (-0.05, 0.05):
                rr = min(max(int(round(r + er)), 0), h - 1)
                cc = min(max(int(round(c + ec)), 0), w - 1)
                if not passable[rr, cc]:
                    return False
    return True


def _arrays(gr: Grid):
    return (
        np.ascontiguousarray(gr.z, dtype=np.float64),
        np.ascontiguousarray(gr.hazard, dtype=np.float64),
        np.ascontiguousarray(gr.dose, dtype=np.float64),
        np.ascontiguousarray(gr.unc, dtype=np.float64),
    )


def segment_clear(gr: Grid, p, q) -> bool:
    """True if every cell the segment p-q touches is passable (corners count)."""
    return bool(_seg_clear(np.ascontiguousarray(gr.passable), float(p[0]), float(p[1]),
                           float(q[0]), float(q[1])))  # fmt: skip


def segment_steps(gr: Grid, suit: mb.Suit, w: dict, p, q, arrays=None) -> dict:
    """Walk straight from cell p to cell q and return each step's end point and running totals
    (cost, minutes, consumables, dose, metres). A single grid move is one step with the edge
    formula exactly; a longer segment is walked in steps of at most half a cell on the bilinear
    surface."""
    z, hz, dd, uu = arrays or _arrays(gr)
    single = (int(q[0] - p[0]), int(q[1] - p[1])) in _OFFSET_INDEX and float(p[0]).is_integer()
    a = _seg_walk(z, hz, dd, uu, float(gr.res), _w_vec(w), _suit_vec(suit), float(p[0]),
                  float(p[1]), float(q[0]), float(q[1]), single)  # fmt: skip
    keys = ("r", "c", "cost", "minutes", "consumables", "dose", "metres")
    return {k: a[:, j] for j, k in enumerate(keys)}


def segment_metrics(gr: Grid, suit: mb.Suit, w: dict, p, q, arrays=None) -> dict:
    """Cost, minutes, consumables and dose of walking straight from cell p to cell q."""
    s = segment_steps(gr, suit, w, p, q, arrays)
    return {k: float(s[k][-1]) for k in ("cost", "minutes", "consumables", "dose")}


def polyline_metrics(gr: Grid, suit: mb.Suit, w: dict, pts) -> dict:
    arrays = _arrays(gr)
    tot = {"cost": 0.0, "minutes": 0.0, "consumables": 0.0, "dose": 0.0}
    for p, q in zip(pts[:-1], pts[1:], strict=True):
        m = segment_metrics(gr, suit, w, p, q, arrays)
        for k in tot:
            tot[k] += m[k]
    return tot


def smooth(gr: Grid, suit: mb.Suit, w: dict, path, lookahead: int = 40):
    """Line-of-sight smoothing: from each kept cell, jump to the farthest cell ahead (within
    `lookahead`) whose straight segment is clear of no-go cells and costs no more than the grid
    path it replaces. Never crosses a no-go cell, never raises the cost."""
    if len(path) <= 2:
        return list(path)
    arrays = _arrays(gr)
    passable = np.ascontiguousarray(gr.passable)
    edge = [segment_metrics(gr, suit, w, a, b, arrays)["cost"]
            for a, b in zip(path[:-1], path[1:], strict=True)]  # fmt: skip
    prefix = np.concatenate([[0.0], np.cumsum(edge)])
    out = [path[0]]
    i = 0
    while i < len(path) - 1:
        best = i + 1
        for j in range(min(len(path) - 1, i + lookahead), i + 1, -1):
            p, q = path[i], path[j]
            if not _seg_clear(passable, float(p[0]), float(p[1]), float(q[0]), float(q[1])):
                continue
            if segment_metrics(gr, suit, w, p, q, arrays)["cost"] <= prefix[j] - prefix[i]:
                best = j
                break
        out.append(path[best])
        i = best
    return out


def leg_matrix(gr: Grid, suit: mb.Suit, w: dict, points, max_cost: float = np.inf) -> dict:
    """Asymmetric matrices between points from one forward Dijkstra per point. Each leg is then
    smoothed, and cost, minutes, consumables and dose describe the smoothed leg, so plans and
    their checks measure the same path; `grid_cost` keeps the Dijkstra cost."""
    n = len(points)
    keys = ("cost", "minutes", "consumables", "dose", "grid_cost")
    mats = {k: np.full((n, n), np.inf) for k in keys}
    paths = {}
    for i, p in enumerate(points):
        f = dijkstra(gr, suit, w, [p], max_cost=max_cost)
        for j, q in enumerate(points):
            mats["grid_cost"][i, j] = f.cost[q]
            if i != j and np.isfinite(f.cost[q]):
                pts = smooth(gr, suit, w, extract_path(f, q))
                paths[(i, j)] = pts
                met = polyline_metrics(gr, suit, w, pts)
                for k in ("cost", "minutes", "consumables", "dose"):
                    mats[k][i, j] = met[k]
    for k in mats:
        np.fill_diagonal(mats[k], 0.0)
    mats["paths"] = paths
    return mats
