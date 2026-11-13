# Written with AI assistance (Claude Code). See AI_USE.md.
"""Hard constraints along a route (PROMPT.md 5.4 and 5.9), checked at least every 5 m.

- Thread: C_left(x) - C_home(x) >= C_reserve at every sample, where C_left is consumables left
  (minutes at the nominal rate) and C_home the least consumables needed to walk home from x.
- Buddy: every station has an overwatch point within 50 m with mutual helmet line of sight.
- Shelter: walking minutes to the rover, wherever it is (team decision, 2026-11-10), stay at
  or below the limit. Terrain shielding is not shelter: it blocks a few percent at most.
- Comms: no comm shadow (out of line of sight of the rover antenna) lasts longer than the limit,
  counting station work done in a shadow.
- Rover: the staging point, where the walk ends, is passable for the rover.

Why the thread holds for any plan within budget: the rest of the route from x includes a walk
home, which needs at least C_home(x); so used(x) + C_home(x) <= used(end) <= budget. Legs are
smoothed off the grid, so they can be a little cheaper than C_home, which comes from grid paths;
DISCRETISATION_MARGIN_MIN covers that, and the check measures rather than assumes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from affine import Affine

from ariadne.models import metabolic as mb
from ariadne.plan import graph as g

DISCRETISATION_MARGIN_MIN = 2.0  # PLACEHOLDER: grid versus smoothed legs


@dataclass
class Fields:
    grid: g.Grid
    c_home: np.ndarray  # consumables minutes to the staging point (least)
    shelter_min: np.ndarray  # walking minutes to the rover at this relay
    comms: np.ndarray  # True where the rover antenna is in line of sight
    rover_ok: bool


def rover_walk_at(mv, rc, t: float) -> float:
    """Walking minutes from cell rc to a rover that is driving: `mv` is (sample times, walking-
    minute fields to the rover at each sample); between two samples the larger is taken, and
    after the last sample the rover has arrived."""
    times, fields = mv
    if t >= times[-1]:
        return float(fields[-1][rc])
    k = int(np.searchsorted(times, t, side="right"))
    return float(max(fields[max(k - 1, 0)][rc], fields[min(k, len(fields) - 1)][rc]))


def _cell(gr: g.Grid, r: float, c: float) -> tuple[int, int]:
    h, w = gr.z.shape
    return int(np.clip(np.rint(r), 0, h - 1)), int(np.clip(np.rint(c), 0, w - 1))


def route_samples(gr, suit, w, legs, stations, service_min: float, service_cons: float) -> list:
    """Every step along the route (at most one cell apart on long segments, one grid move
    otherwise), with running minutes, consumables, dose and metres; station work is added as a
    sample at the station. Leg k ends at stations[k]; the last leg ends at the staging point."""
    r0, c0 = legs[0][0] if legs else (0, 0)
    out = [{"r": float(r0), "c": float(c0), "t": 0.0, "cons": 0.0, "dose": 0.0, "m": 0.0,
            "station": None, "leg": 0}]  # fmt: skip
    for k, leg in enumerate(legs):
        for p, q in zip(leg[:-1], leg[1:], strict=True):
            s = g.segment_steps(gr, suit, w, p, q)
            base = out[-1]
            for j in range(len(s["r"])):
                out.append(
                    {
                        "r": float(s["r"][j]),
                        "c": float(s["c"][j]),
                        "t": base["t"] + float(s["minutes"][j]),
                        "cons": base["cons"] + float(s["consumables"][j]),
                        "dose": base["dose"] + float(s["dose"][j]),
                        "m": base["m"] + float(s["metres"][j]),
                        "station": None,
                        "leg": k,
                    }
                )
        if k < len(stations):
            last = dict(out[-1])
            last.update(
                t=last["t"] + service_min, cons=last["cons"] + service_cons, station=k, leg=k
            )
            out.append(last)
    return out


def overwatch_point(gr: g.Grid, station, max_m=50.0, min_m=3.0, helmet_m=1.8) -> dict | None:
    """The nearest passable cell between min_m and max_m from the station with mutual helmet
    line of sight, or None."""
    from ariadne.derive import los

    r, c = station
    k = int(np.ceil(max_m / gr.res))
    h, w = gr.z.shape
    rr, cc = np.mgrid[max(0, r - k) : min(h, r + k + 1), max(0, c - k) : min(w, c + k + 1)]
    d = gr.res * np.hypot(rr - r, cc - c)
    ok = (d >= min_m) & (d <= max_m) & gr.passable[rr, cc]
    order = np.argsort(d[ok], kind="stable")
    cand = np.stack([rr[ok], cc[ok]], axis=1)[order]
    dist = d[ok][order]
    t = Affine(gr.res, 0, 0, 0, -gr.res, 0)

    def xy(rc):
        return ((rc[1] + 0.5) * gr.res, -(rc[0] + 0.5) * gr.res)

    for (a, b), dd in zip(cand, dist, strict=True):
        if los.line_of_sight(gr.z, t, xy((r, c)), xy((a, b)), helmet_m, helmet_m):
            return {"cell": (int(a), int(b)), "distance_m": float(dd)}
    return None


def check_route(
    fields: Fields,
    suit: mb.Suit,
    w: dict,
    legs,
    stations,
    service_min: float,
    service_cons: float,
    consumables_total: float,
    limits: dict,
    buddy_ok: list[bool] | None = None,
    leg_fields: list[Fields] | None = None,
    visit_shelter: list[float | None] | None = None,
    first_leg_rover=None,
) -> dict:
    """Check a route. With `leg_fields` (one Fields per leg) the rover moves: each leg uses its
    own C_home, shelter and comms fields (those of the relay the rover is parked at), and at a
    station where the rover changes relay, C_home is the larger of the two and the station must
    be in sight of both. `visit_shelter[k]` is the walk to the rover while it drives during
    station k's visit; `first_leg_rover` (sample times, fields) follows it while it drives during
    the first leg."""
    gr = fields.grid
    samples = route_samples(gr, suit, w, legs, stations, service_min, service_cons)
    reserve = float(limits["reserve_min"])
    margins, worst = [], np.inf
    shelter_worst, shadow, longest = 0.0, None, 0.0
    for s in samples:
        rc = _cell(gr, s["r"], s["c"])
        f = fields if leg_fields is None else leg_fields[min(s["leg"], len(leg_fields) - 1)]
        ch = float(f.c_home[rc])
        in_sight = bool(f.comms[rc])
        if leg_fields is not None and s["station"] is not None and s["leg"] + 1 < len(leg_fields):
            nxt = leg_fields[s["leg"] + 1]
            if nxt is not f:  # the rover moves during this visit
                ch = max(ch, float(nxt.c_home[rc]))
                in_sight = in_sight and bool(nxt.comms[rc])
        c_left = consumables_total - s["cons"]
        worst = min(worst, c_left - ch - reserve if np.isfinite(ch) else -np.inf)
        sh = float(f.shelter_min[rc])
        if first_leg_rover is not None and s["leg"] == 0 and s["station"] is None:
            sh = rover_walk_at(first_leg_rover, rc, s["t"])
        if visit_shelter is not None and s["station"] is not None:
            v = visit_shelter[s["station"]]
            sh = sh if v is None else max(sh, v)
        shelter_worst = max(shelter_worst, sh)
        if not in_sight:
            shadow = s["t"] if shadow is None else shadow
            longest = max(longest, s["t"] - shadow)
        else:
            shadow = None
        s.update(c_left=c_left, c_home=ch, shelter=sh)
    # keep a sample whenever the next step would put more than step_m since the last kept one
    step = float(limits["sample_step_m"])
    last_m = 0.0
    for i, s in enumerate(samples):
        nxt = samples[i + 1]["m"] if i + 1 < len(samples) else None
        if i == 0 or s["station"] is not None or nxt is None or nxt - last_m > step:
            margins.append(
                {
                    "t_min": round(s["t"], 3),
                    "c_left": round(s["c_left"], 3),
                    "c_home": round(s["c_home"], 3) if np.isfinite(s["c_home"]) else None,
                    "c_reserve": reserve,
                    "step_m": round(s["m"] - last_m, 3),
                    "minutes_to_rover": round(s["shelter"], 2)
                    if np.isfinite(s["shelter"])
                    else None,
                    "leg": s["leg"],
                    "station": s["station"],
                    "xy_cell": [round(s["r"], 2), round(s["c"], 2)],
                }
            )
            last_m = s["m"]
    checks = {
        "thread": "pass" if worst >= -1e-9 else "fail",
        "buddy": "not checked" if buddy_ok is None else ("pass" if all(buddy_ok) else "fail"),
        "shelter": "pass" if shelter_worst <= limits["shelter_max_min"] + 1e-9 else "fail",
        "comms": "pass" if longest <= limits["comm_shadow_max_min"] + 1e-9 else "fail",
        "rover": "pass"
        if fields.rover_ok and all(x.rover_ok for x in leg_fields or [])
        else "fail",
    }
    return {
        "margins": margins,
        "checks": checks,
        "details": {
            "thread_min_margin_min": round(float(worst), 3),
            "worst_minutes_to_shelter": round(shelter_worst, 2),
            "longest_comm_shadow_min": round(longest, 2),
            "samples": len(samples),
            "minutes": round(samples[-1]["t"], 3),
            "consumables": round(samples[-1]["cons"], 3),
            "relative_dose": round(samples[-1]["dose"], 4),
            "metres": round(samples[-1]["m"], 1),
        },
    }
