# Written with AI assistance (Claude Code). See AI_USE.md.
"""Curiosity Navcam photos as 3D billboards: placement and facing.

Each frame from NASA's raw-image API names the rover's site and drive and the mast azimuth and
elevation in the rover frame. The capture point is that site and drive's PLACES localization,
and the compass direction of view is the rover's yaw there plus the mast azimuth. Credit
"Courtesy NASA/JPL-Caltech" (JPL image use policy).
"""

from __future__ import annotations

import math

CREDIT = "Courtesy NASA/JPL-Caltech"
API = "https://mars.nasa.gov/api/v1/raw_image_items/"


def place(item: dict, localizations: dict) -> dict | None:
    key = (item.get("site"), item.get("drive"))
    loc = localizations.get(key)
    ext = item.get("extended") or {}
    if loc is None or ext.get("mast_az") in (None, "") or ext.get("mast_el") in (None, ""):
        return None
    return {
        "imageid": item["imageid"],
        "instrument": item["instrument"],
        "sol": int(item["sol"]),
        "site": key[0],
        "drive": key[1],
        "xy_m": [round(float(loc["easting"]), 2), round(float(loc["northing"]), 2)],
        "view_azimuth_deg": round((float(loc["yaw"]) + float(ext["mast_az"])) % 360.0, 2),
        "view_elevation_deg": round(float(ext["mast_el"]), 2),
        "url": item["https_url"],
        "credit": CREDIT,
        "source_credit": item.get("image_credit"),
    }


def bearing(a, b) -> float:
    return math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) % 360.0


def looks_at(photo: dict, xy, max_m: float, max_angle_deg: float) -> bool:
    """True if `xy` is within max_m of the capture point and within max_angle_deg of the view."""
    d = math.hypot(xy[0] - photo["xy_m"][0], xy[1] - photo["xy_m"][1])
    if d > max_m or d < 1.0:
        return False
    diff = (bearing(photo["xy_m"], xy) - photo["view_azimuth_deg"] + 180.0) % 360.0 - 180.0
    return abs(diff) <= max_angle_deg
