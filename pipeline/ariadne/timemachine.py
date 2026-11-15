# Written with AI assistance (Claude Code). See AI_USE.md.
"""Time Machine (PROMPT.md section 7): light time, a space-weather snapshot and the storm replay.

- Light time: Earth-Mars one-way light time from the JPL Horizons API (observer table, quantities
  20 and 21, Mars seen from Earth's centre), bundled as a table and interpolated. The brief names
  astroquery; this calls the same Horizons service directly, so the step needs no compiled
  libraries.
- Space weather: a DONKI snapshot around the May 20, 2024 storm (CMEs, SEP events, notifications)
  through NASA's API gateway, because the CCMC host times out from here. NASA's public DEMO_KEY is
  used unless NASA_API_KEY is set; it is not a secret.
- Storm replay: the event as DONKI records it, the dose JPL reports from Curiosity's RAD
  instrument, the light time that day, and where the event starts in each walk (PLACEHOLDER: the
  middle of the walk).

Snapshots are committed in config/snapshots/, so CI and the package step never need the network.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ariadne import __version__ as PIPELINE_VERSION
from ariadne.fetch.raster import USER_AGENT

HORIZONS_API = "https://ssd.jpl.nasa.gov/api/horizons.api"
DONKI_API = "https://api.nasa.gov/DONKI/"
EVENT_CME = "2024-05-20T05:36:00-CME-001"
JPL_ARTICLE = "https://www.jpl.nasa.gov/news/nasa-watches-mars-light-up-during-epic-solar-storm/"

# Light-time table windows: the replay week, the plan's reference sol, and November 2026.
LIGHT_TIME_WINDOWS = [
    ("2024-05-13 00:00", "2024-05-31 00:00", "6 h"),
    ("2025-11-01 00:00", "2025-12-31 00:00", "1 d"),
    ("2026-11-01 00:00", "2026-11-30 00:00", "1 d"),
]
# Times off the table's grid, checked directly against Horizons (test: within 1 s).
LIGHT_TIME_CHECKS = ["2024-05-20 05:22", "2024-05-24 15:30", "2026-11-14 09:00"]


def _get(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def horizons_url(start: str, stop: str, step: str) -> str:
    q = {
        "format": "json",
        "COMMAND": "'499'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'500@399'",
        "START_TIME": f"'{start}'",
        "STOP_TIME": f"'{stop}'",
        "STEP_SIZE": f"'{step}'",
        "QUANTITIES": "'20,21'",
    }
    return HORIZONS_API + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)


def parse_horizons(result: str) -> list[dict]:
    """Rows of a Horizons observer table with quantities 20 and 21: UTC, range (au), range rate
    (km/s) and one-way down-leg light time (minutes)."""
    s, e = result.find("$$SOE"), result.find("$$EOE")
    if s < 0 or e < 0:
        raise ValueError("no ephemeris rows in the Horizons result")
    rows = []
    for line in result[s + 5 : e].strip().splitlines():
        parts = line.split()
        when = datetime.strptime(f"{parts[0]} {parts[1]}", "%Y-%b-%d %H:%M").replace(tzinfo=UTC)
        rows.append(
            {
                "utc": when.isoformat().replace("+00:00", "Z"),
                "delta_au": float(parts[2]),
                "deldot_km_s": float(parts[3]),
                "light_time_min": float(parts[4]),
            }
        )
    return rows


def _t(utc: str) -> datetime:
    return datetime.fromisoformat(utc.replace("Z", "+00:00"))


def light_time_at(table: list[dict], utc: str) -> float:
    """One-way light time (minutes) at `utc`, linearly interpolated in the table."""
    t = _t(utc)
    rows = sorted(table, key=lambda r: r["utc"])
    for a, b in zip(rows, rows[1:], strict=False):
        ta, tb = _t(a["utc"]), _t(b["utc"])
        if ta <= t <= tb:
            f = (t - ta) / (tb - ta) if tb > ta else 0.0
            return a["light_time_min"] + f * (b["light_time_min"] - a["light_time_min"])
    raise ValueError(f"{utc} is outside the light-time table")


def fetch_light_time(log=print) -> dict:
    table = []
    for start, stop, step in LIGHT_TIME_WINDOWS:
        table += parse_horizons(json.loads(_get(horizons_url(start, stop, step)))["result"])
        log(f"  Horizons {start} to {stop}: {len(table)} rows so far")
    checks = []
    for when in LIGHT_TIME_CHECKS:
        end = (datetime.strptime(when, "%Y-%m-%d %H:%M") + timedelta(minutes=1)).strftime(
            "%Y-%m-%d %H:%M"
        )
        row = parse_horizons(json.loads(_get(horizons_url(when, end, "1 m")))["result"])[0]
        checks.append({"utc": row["utc"], "horizons_light_time_min": row["light_time_min"]})
    return {
        "_about": "Earth-Mars one-way light time from the JPL Horizons API (observer table, Mars "
        "(499) from Earth's centre (500@399), quantities 20 and 21). `checks` are Horizons values "
        "at times off the table's grid, for the 1 s interpolation test. Fetched by "
        "`ariadne timemachine`.",
        "source": HORIZONS_API,
        "label": "DERIVED",
        "fetched_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "pipeline_version": PIPELINE_VERSION,
        "table": table,
        "checks": checks,
    }


def donki_url(kind: str, start: str, end: str, extra: dict | None = None) -> str:
    q = {"startDate": start, "endDate": end, "api_key": os.environ.get("NASA_API_KEY", "DEMO_KEY")}
    q.update(extra or {})
    return DONKI_API + kind + "?" + urllib.parse.urlencode(q)


def _trim_cme(e: dict) -> dict:
    analyses = e.get("cmeAnalyses") or []
    best = [a for a in analyses if a.get("isMostAccurate")] or analyses
    a = best[0] if best else {}
    impacts = sorted(
        {
            (i["location"], i["arrivalTime"], bool(i.get("isGlancingBlow")))
            for an in analyses
            for en in an.get("enlilList") or []
            for i in en.get("impactList") or []
        }
    )
    return {
        "activityID": e["activityID"],
        "startTime": e["startTime"],
        "sourceLocation": e.get("sourceLocation") or None,
        "speed_km_s": a.get("speed"),
        "type": a.get("type"),
        "predicted_impacts": [{"location": x, "arrival": t, "glancing": g} for x, t, g in impacts],
        "note": e.get("note"),
        "link": e.get("link"),
    }


def fetch_donki(log=print) -> dict:
    start, end = "2024-05-13", "2024-05-31"
    cme = json.loads(_get(donki_url("CME", start, end)))
    sep = json.loads(_get(donki_url("SEP", start, end)))
    notes = json.loads(
        _get(donki_url("notifications", "2024-05-20", "2024-05-22", {"type": "all"}))
    )
    try:
        flr = json.loads(_get(donki_url("FLR", start, end)))
        flr_status = "ok"
    except Exception as ex:  # the gateway answered 404 for FLR on 2026-11-15
        flr, flr_status = [], f"unavailable through api.nasa.gov ({ex})"
    log(f"  DONKI: {len(cme)} CMEs, {len(sep)} SEP events, {len(notes)} notifications, "
        f"flares {flr_status}")  # fmt: skip
    return {
        "_about": "DONKI snapshot around the May 20, 2024 storm, through NASA's API gateway "
        "(https://api.nasa.gov/DONKI/). Fetched by `ariadne timemachine`. DONKI's disclaimer: "
        "NOAA's Space Weather Prediction Center is the official US source for space weather "
        "forecasts; DONKI holds preliminary NASA research products.",
        "source": DONKI_API,
        "window": [start, end],
        "fetched_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "pipeline_version": PIPELINE_VERSION,
        "label": "MEASURED",
        "cme": [_trim_cme(e) for e in cme],
        "sep": [
            {
                "sepID": e["sepID"],
                "eventTime": e["eventTime"],
                "instruments": [i["displayName"] for i in e.get("instruments", [])],
            }
            for e in sep
        ],  # fmt: skip
        "notifications": [
            {
                "messageType": n["messageType"],
                "messageID": n["messageID"],
                "messageIssueTime": n["messageIssueTime"],
                "messageURL": n.get("messageURL"),
                "title": next(
                    (
                        ln.split(":", 1)[1].strip()
                        for ln in n["messageBody"].splitlines()
                        if ln.startswith("## Message Type:")
                    ),
                    n["messageType"],
                ),
            }
            for n in notes
        ],  # fmt: skip
        "flares": flr,
        "flares_status": flr_status,
    }


def snapshot_dir(root: Path) -> Path:
    return root / "config" / "snapshots"


def fetch_snapshots(root: Path, log=print) -> dict:
    out = snapshot_dir(root)
    out.mkdir(parents=True, exist_ok=True)
    lt = fetch_light_time(log)
    dk = fetch_donki(log)
    (out / "horizons_light_time.json").write_text(json.dumps(lt, indent=1) + "\n",
                                                  encoding="utf-8", newline="\n")  # fmt: skip
    (out / "donki_2024-05.json").write_text(json.dumps(dk, indent=1) + "\n", encoding="utf-8",
                                            newline="\n")  # fmt: skip
    return {"light_time": lt, "donki": dk}


def light_time_check(lt: dict) -> dict:
    """Interpolated table against direct Horizons values at off-grid times (target: within 1 s)."""
    rows = []
    for c in lt["checks"]:
        got = light_time_at(lt["table"], c["utc"])
        rows.append(
            {
                "utc": c["utc"],
                "horizons_min": c["horizons_light_time_min"],
                "table_min": round(got, 6),
                "difference_s": round(abs(got - c["horizons_light_time_min"]) * 60, 3),
            }
        )
    worst = max(r["difference_s"] for r in rows)
    return {"rows": rows, "worst_difference_s": worst, "passed": worst <= 1.0}


def replay(plans: dict, lt: dict, dk: dict) -> dict:
    """The May 20, 2024 storm replay for the web app."""
    cme = next(c for c in dk["cme"] if c["activityID"] == EVENT_CME)
    onset = "2024-05-20T05:22Z"  # the EUV wave DONKI's note gives as the eruption's first sign
    starts = {}
    for name, p in plans.items():
        mid = p["totals"]["minutes"] / 2
        walking = [m["t_min"] for m in p["margins"] if m.get("station") is None]
        starts[name] = round(min(walking, key=lambda t: abs(t - mid)), 2) if walking else mid
    light = light_time_at(lt["table"], onset)
    return {
        "title": "May 20, 2024 solar storm",
        "event": {
            "onset_utc": onset,
            "label": "MEASURED",
            "source": f"DONKI {EVENT_CME}: EUV wave seen by SDO at 05:22Z, fast halo CME at "
            "05:36Z; source on the Sun's far side",
            "cme": cme,
        },
        "flare": {
            "value": "X12 (estimated)",
            "label": "DERIVED",
            "source": f"JPL, June 10, 2024 ({JPL_ARTICLE}): estimated from Solar Orbiter "
            "data; the flare was on the far side of the Sun as seen from Earth",
        },  # fmt: skip
        "arrival": {
            "text": "Particles reached Mars in tens of minutes.",
            "label": "MEASURED",
            "source": f"JPL, June 10, 2024 ({JPL_ARTICLE})",
        },  # fmt: skip
        "rad_dose_uGy": {
            "value": 8100,
            "label": "MEASURED",
            "meaning": "the dose an astronaut standing next to Curiosity would have received, "
            "from Curiosity's RAD instrument (JPL: the biggest surge RAD had measured since "
            "landing)",
            "source": f"JPL, June 10, 2024 ({JPL_ARTICLE})",
        },
        "light_time_min": {
            "value": round(light, 2),
            "label": "DERIVED",
            "source": "JPL Horizons, Earth-Mars one-way light time at the onset",
        },  # fmt: skip
        "alignment": {
            "label": "PLACEHOLDER",
            "start_min": starts,
            "rule": "the event begins at the walking sample nearest the middle of each walk",
        },  # fmt: skip
        "dose_scaling": {
            "label": "MODELED",
            "text": "Modeled doses are scaled so that the whole event under an open sky equals "
            "RAD's 8,100 micrograys, at a constant dose rate over the PLACEHOLDER event length; "
            "real storms rise and fall, and JPL gives no duration.",
        },
        "donki": {
            "cmes_may_20": [c for c in dk["cme"] if c["startTime"].startswith("2024-05-20")],
            "notifications": dk["notifications"],
            "sep_in_window": dk["sep"],
            "flares_status": dk["flares_status"],
            "disclaimer": "DONKI holds preliminary NASA research products; NOAA's Space Weather "
            "Prediction Center is the official US source for space weather forecasts.",
        },
        "pipeline_version": PIPELINE_VERSION,
    }


def load_snapshots(root: Path) -> tuple[dict, dict]:
    d = snapshot_dir(root)
    lt = json.loads((d / "horizons_light_time.json").read_text(encoding="utf-8"))
    dk = json.loads((d / "donki_2024-05.json").read_text(encoding="utf-8"))
    return lt, dk
