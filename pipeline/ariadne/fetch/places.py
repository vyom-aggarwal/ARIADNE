# Written with AI assistance (Claude Code). See AI_USE.md.
"""Curiosity's positions from the MSL PLACES localization table."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

MARS_RADIUS_M = 3_396_190.0  # sphere of the USGS Gale mosaics and PLACES easting/northing

COLUMNS = [
    "frame",
    "site",
    "drive",
    "pose",
    "easting",
    "northing",
    "planetocentric_latitude",
    "longitude",
    "elevation",
    "sclk",
    "sol",
]


def lonlat_to_eqc(lon_east: float, lat: float) -> tuple[float, float]:
    """Equirectangular meters on the Mars sphere (longitude of origin 0, standard parallel 0)."""
    return MARS_RADIUS_M * math.radians(lon_east), MARS_RADIUS_M * math.radians(lat)


def load_rover_positions(csv_path: Path) -> pd.DataFrame:
    """ROVER-frame localizations, ordered by spacecraft clock."""
    df = pd.read_csv(csv_path, usecols=lambda c: c in COLUMNS)
    df = df[df["frame"] == "ROVER"]
    return df.sort_values("sclk", kind="stable").reset_index(drop=True)


def in_sols(df: pd.DataFrame, first: int, last: int) -> pd.DataFrame:
    return df[(df["sol"] >= first) & (df["sol"] <= last)]


def parking_position(df: pd.DataFrame, first: int, last: int) -> dict:
    """The localization within sols first..last held for the most sols before the next one."""
    held = df.copy()
    held["left_sol"] = held["sol"].shift(-1)
    held = in_sols(held, first, last).dropna(subset=["left_sol"])
    held["held_sols"] = held["left_sol"] - held["sol"]
    best = held.sort_values(["held_sols", "sclk"], ascending=[False, True]).iloc[0]
    return {
        "site": int(best["site"]),
        "drive": int(best["drive"]),
        "arrived_sol": int(best["sol"]),
        "left_sol": int(best["left_sol"]),
        "held_sols": int(best["held_sols"]),
        "easting": float(best["easting"]),
        "northing": float(best["northing"]),
        "longitude": float(best["longitude"]),
        "planetocentric_latitude": float(best["planetocentric_latitude"]),
        "elevation": float(best["elevation"]),
        "sclk": int(best["sclk"]),
    }


def rover_path_geojson(df: pd.DataFrame, site: str) -> dict:
    """GeoJSON: the driven path as a LineString plus the localizations as a MultiPoint.

    Coordinates are [east longitude, planetocentric latitude] in degrees on the Mars sphere.
    """
    coords = [
        [round(lon, 7), round(lat, 7)]
        for lon, lat in zip(df["longitude"], df["planetocentric_latitude"], strict=True)
    ]
    props = {
        "site": site,
        "label": "MEASURED",
        "source_id": "msl-places",
        "first_sol": int(df["sol"].min()),
        "last_sol": int(df["sol"].max()),
        "localizations": int(len(df)),
    }
    return {
        "type": "FeatureCollection",
        "ariadne_crs": "Mars sphere R=3396190 m; east longitude, planetocentric latitude (degrees)",
        "features": [
            {
                "type": "Feature",
                "properties": {**props, "kind": "rover_path"},
                "geometry": {"type": "LineString", "coordinates": coords},
            },
            {
                "type": "Feature",
                "properties": {**props, "kind": "localizations"},
                "geometry": {"type": "MultiPoint", "coordinates": coords},
            },
        ],
    }
