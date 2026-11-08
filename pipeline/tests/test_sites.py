# Written with AI assistance (Claude Code). See AI_USE.md.
"""Site boxes from Curiosity's localizations (acceptance test B6).

The fixture is an extract of real rows from the MSL PLACES table `localized_interp.csv`
(ROVER frame, sols 1440 to 1483 and 4516 to 4863), fetched 2026-11-08.
"""

import json
from pathlib import Path

import pytest

from ariadne.config import load_site_config
from ariadne.fetch import places, sites

FIXTURE = Path(__file__).parent / "fixtures" / "places_extract.csv"


@pytest.fixture(scope="module")
def rover():
    return places.load_rover_positions(FIXTURE)


def test_site_configs_load():
    bw = load_site_config("boxwork")
    mb = load_site_config("murray-buttes")
    assert bw.selection.method == "rover_extent"
    assert mb.selection.method == "parking_position"
    assert bw.buffer_m == 1500 and bw.buffer_label == "PLACEHOLDER"
    assert mb.buffer_m == 2000 and mb.buffer_label == "PLACEHOLDER"


def test_boxwork_box_from_the_rover_extent(rover):
    box = sites.site_box(load_site_config("boxwork"), rover)
    assert (box.first_sol, box.last_sol) == (4526, 4853)
    e0, n0, e1, n1 = box.rover_extent
    assert (e0, e1) == pytest.approx((8143105.6, 8143619.5), abs=0.1)
    assert (n0, n1) == pytest.approx((-285230.7, -284306.7), abs=0.1)
    assert box.bounds == pytest.approx((e0 - 1500, n0 - 1500, e1 + 1500, n1 + 1500))
    assert box.rover_count > 2000


def test_murray_buttes_box_from_the_parking_position(rover):
    box = sites.site_box(load_site_config("murray-buttes"), rover)
    assert (box.first_sol, box.last_sol) == (1455, 1468)
    a = box.anchor
    assert (a["site"], a["drive"]) == (57, 2798)
    assert (a["arrived_sol"], a["left_sol"]) == (1455, 1468)
    assert (a["easting"], a["northing"]) == pytest.approx((8141557.908, -278306.692), abs=1e-3)
    assert box.bounds == pytest.approx(
        (a["easting"] - 2000, a["northing"] - 2000, a["easting"] + 2000, a["northing"] + 2000)
    )


def test_rover_positions_are_rover_frame_and_time_ordered(rover):
    assert (rover["frame"] == "ROVER").all()
    assert rover["sclk"].is_monotonic_increasing


def test_projection_matches_longitude_and_latitude(rover):
    # PLACES easting/northing are equirectangular meters on the 3,396,190 m sphere.
    r = rover.iloc[0]
    e, n = places.lonlat_to_eqc(r["longitude"], r["planetocentric_latitude"])
    assert (e, n) == pytest.approx((r["easting"], r["northing"]), abs=0.01)


def test_rover_path_geojson_uses_lon_lat(rover, tmp_path):
    sub = rover[(rover["sol"] >= 4526) & (rover["sol"] <= 4853)]
    gj = places.rover_path_geojson(sub, site="boxwork")
    path = tmp_path / "rover_path.geojson"
    path.write_text(json.dumps(gj), encoding="utf-8")
    line = gj["features"][0]
    assert line["geometry"]["type"] == "LineString"
    lon, lat = line["geometry"]["coordinates"][0]
    assert 137.3 < lon < 137.5 and -4.9 < lat < -4.7
    assert line["properties"]["label"] == "MEASURED"
    assert gj["features"][1]["geometry"]["type"] == "MultiPoint"
