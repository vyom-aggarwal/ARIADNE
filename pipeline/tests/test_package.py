# Written with AI assistance (Claude Code). See AI_USE.md.
"""The packaged site for the web app (tests E1 to E5)."""

import json
import math
import struct
import zlib
from datetime import UTC, datetime

import numpy as np
import pytest
from affine import Affine

from ariadne.guardrails import repo_root
from ariadne.package import layers, photos, png, timeline

ROOT = repo_root()
SITE = ROOT / "web" / "public" / "sites" / "boxwork"


def read_png(path):
    data = path.read_bytes()
    w, h, depth, color = struct.unpack(">IIBB", data[16:26])
    idat, i = b"", 8
    while i < len(data):
        n = struct.unpack(">I", data[i : i + 4])[0]
        kind = data[i + 4 : i + 8]
        if kind == b"IDAT":
            idat += data[i + 8 : i + 8 + n]
        i += 12 + n
    raw = zlib.decompress(idat)
    chans = {0: 1, 2: 3, 6: 4}[color]
    bpp = chans * depth // 8
    rows = [raw[r * (w * bpp + 1) + 1 : (r + 1) * (w * bpp + 1)] for r in range(h)]
    dt = ">u2" if depth == 16 else "u1"
    return np.frombuffer(b"".join(rows), dtype=dt).reshape(h, w, chans).squeeze()


# --- E1: the committed package ---


def test_manifest_lists_every_layer_with_provenance_and_files_exist():
    m = json.loads((SITE / "manifest.json").read_text(encoding="utf-8"))
    assert m["site"] == "boxwork" and len(m["bounds_m"]) == 4
    assert m["pipeline_version"]
    for lay in m["layers"]:
        for key in ("id", "title", "file", "kind", "sources", "resolution_m", "date", "label",
                    "description"):  # fmt: skip
            assert key in lay, (lay.get("id"), key)
        assert lay["label"] in {"MEASURED", "DERIVED", "MODELED", "PLACEHOLDER"}
        assert (SITE / lay["file"]).exists(), lay["file"]
        if lay["kind"] == "raster" and lay.get("legend") is not None:
            assert all("label" in e for e in lay["legend"])
    for p in m["plans"]:
        assert (SITE / p["file"]).exists()
    for ch in m["terrain"]["chunks"]:
        assert all((SITE / f).exists() for f in ch["files"].values())
    for ph in m["photos"]:
        assert (SITE / ph["file"]).exists() and ph["credit"].startswith("Courtesy NASA/JPL-Caltech")
    total = sum(f.stat().st_size for f in SITE.rglob("*") if f.is_file())
    assert total < 200 * 2**20  # well inside the 1 GB GitHub Pages limit


# --- E2: overlays ---


def test_class_colors_follow_the_legend():
    legend = [{"value": 0, "color": [10, 20, 30, 200], "label": "go"},
              {"value": 2, "color": [200, 0, 0, 255], "label": "no-go"}]  # fmt: skip
    rgba = layers.colorize_classes(np.array([[0, 2], [255, 1]]), legend)
    assert rgba[0, 0].tolist() == [10, 20, 30, 200] and rgba[0, 1].tolist() == [200, 0, 0, 255]
    assert rgba[1, 0, 3] == 0 and rgba[1, 1, 3] == 0  # no data and unlisted classes are clear


def test_ramp_and_hatching():
    rgba = layers.colorize_ramp(np.array([[0.0, 1.0, np.nan]]), 0.0, 1.0,
                                [[0, 0, 0], [255, 255, 255]])  # fmt: skip
    assert rgba[0, 0, :3].tolist() == [0, 0, 0] and rgba[0, 1, :3].tolist() == [255, 255, 255]
    assert rgba[0, 2, 3] == 0
    mask = np.ones((8, 8), bool)
    h = layers.hatch(mask, spacing=4, color=[255, 255, 0, 255])
    stripes = h[:, :, 3] > 0
    assert 0 < stripes.mean() < 0.5  # diagonal stripes, not a solid fill
    assert stripes[0, 0] and stripes[1, 1] and not stripes[0, 2]


def test_png_round_trip_rgba_and_16_bit(tmp_path):
    rgba = np.random.default_rng(0).integers(0, 255, (5, 7, 4)).astype(np.uint8)
    png.write_png(tmp_path / "a.png", rgba)
    assert np.array_equal(read_png(tmp_path / "a.png"), rgba)
    h16 = np.array([[0, 1, 65535]], dtype=np.uint16)
    png.write_png(tmp_path / "b.png", h16)
    assert np.array_equal(read_png(tmp_path / "b.png"), h16[0])


def test_bounds_are_corner_coordinates():
    t = Affine(2.0, 0, 100.0, 0, -2.0, 50.0)
    assert layers.bounds(t, (10, 20)) == [100.0, 30.0, 140.0, 50.0]


# --- E3: terrain ---


def test_heightmap_round_trips_within_a_centimetre_and_chunks_tile_the_window():
    rng = np.random.default_rng(1)
    z = -3700 + rng.uniform(0, 300, (300, 260))
    chunks = layers.terrain_chunks(z, chunk=128, coarse=4)
    covered = np.zeros(z.shape, bool)
    for ch in chunks:
        r0, c0, r1, c1 = ch["rows_cols"]
        back = layers.decode_height(ch["fine"], ch["z0"], ch["scale"])
        assert np.abs(back - z[r0:r1, c0:c1]).max() <= 0.005 + 1e-9
        covered[r0:r1, c0:c1] = True
        coarse = layers.decode_height(ch["coarse"], ch["z0"], ch["scale"])
        assert coarse[0, 0] == pytest.approx(z[r0 : r0 + 4, c0 : c0 + 4].mean(), abs=0.006)
    assert covered.all()


# --- E4: timeline ---


def plan_fixture():
    return {
        "stations": [{"id": "S01", "service_min": 15}, {"id": "S02", "service_min": 15}],
        "legs": [
            {"from": "STAGING", "to": "S01", "minutes": 10.0},
            {"from": "S01", "to": "S02", "minutes": 5.0},
            {"from": "S02", "to": "STAGING", "minutes": 12.0},
        ],  # fmt: skip
        "margins": [
            {"t_min": 0.0, "c_left": 300, "c_home": 0, "c_reserve": 30, "xy_m": [0, 0]},
            {"t_min": 10.0, "c_left": 290, "c_home": 8, "c_reserve": 30, "xy_m": [10, 0]},
            {"t_min": 25.0, "c_left": 281, "c_home": 8, "c_reserve": 30, "xy_m": [10, 0]},
            {"t_min": 30.0, "c_left": 276, "c_home": 6, "c_reserve": 30, "xy_m": [20, 0]},
            {"t_min": 45.0, "c_left": 267, "c_home": 6, "c_reserve": 30, "xy_m": [20, 0]},
            {"t_min": 57.0, "c_left": 257, "c_home": 0, "c_reserve": 30, "xy_m": [0, 0]},
        ],
    }


def test_timeline_margins_station_blocks_and_comm_shadows():
    plan = plan_fixture()
    in_sight = {(0, 0): True, (10, 0): False, (20, 0): True}
    tl = timeline.build(plan, lambda xy: in_sight[tuple(xy)], sun=None)
    assert [p["margin_min"] for p in tl["margin"]] == [270, 252, 243, 240, 231, 227]
    assert tl["stations"] == [{"id": "S01", "start_min": 10.0, "end_min": 25.0},
                              {"id": "S02", "start_min": 30.0, "end_min": 45.0}]  # fmt: skip
    assert tl["comm_shadows"] == [{"start_min": 10.0, "end_min": 30.0}]


def test_timeline_sun_elevation_matches_mars24():
    from ariadne.models import mars24

    start = datetime(2025, 11, 13, 14, 0, tzinfo=UTC)
    lon, lat = 137.38, -4.80
    sun = timeline.sun_elevation(start, [0.0, 60.0, 120.0], lon, lat)
    for t, el in zip([0.0, 60.0, 120.0], sun, strict=True):
        from datetime import timedelta

        from ariadne.models.sun import planetographic_latitude

        s = mars24.solar_state(start + timedelta(minutes=t), lon, planetographic_latitude(lat))
        assert el == pytest.approx(90.0 - s.zenith, abs=0.05)


# --- E5: photos ---


def test_photo_placement_and_facing():
    loc = {(120, 82): {"easting": 1000.0, "northing": 2000.0, "yaw": 30.0}}
    item = {"instrument": "NAV_LEFT_B", "site": 120, "drive": 82, "imageid": "NLB_1",
            "extended": {"mast_az": "20.0", "mast_el": "-10.0"},
            "https_url": "https://example.invalid/NLB_1.JPG", "image_credit": "NASA/JPL-Caltech",
            "sol": 4718}  # fmt: skip
    ph = photos.place(item, loc)
    assert ph["xy_m"] == [1000.0, 2000.0]
    assert ph["view_azimuth_deg"] == pytest.approx(50.0)  # rover yaw + mast azimuth
    assert ph["view_elevation_deg"] == pytest.approx(-10.0)
    assert ph["credit"] == "Courtesy NASA/JPL-Caltech"
    # a station 40 m away along azimuth 55 degrees is in view; one behind the camera is not
    ahead = [1000 + 40 * math.sin(math.radians(55)), 2000 + 40 * math.cos(math.radians(55))]
    behind = [1000 - 40 * math.sin(math.radians(50)), 2000 - 40 * math.cos(math.radians(50))]
    assert photos.looks_at(ph, ahead, max_m=60.0, max_angle_deg=25.0)
    assert not photos.looks_at(ph, behind, max_m=60.0, max_angle_deg=25.0)
    assert photos.place({**item, "site": 1, "drive": 1}, loc) is None


# --- E14 and E15: assumptions, site notes and the Validation tab's data ---


def test_manifest_lists_the_placeholder_assumptions_and_the_site_notes():
    m = json.loads((SITE / "manifest.json").read_text(encoding="utf-8"))
    items = m["assumptions"]
    assert items and all(a["label"] == "PLACEHOLDER" for a in items)
    keys = {a["key"] for a in items}
    assert {"eva_max_min", "shelter_max_min", "safest.shelter_max_min", "safest.reserve_min",
            "shelter_s", "storm_event_duration_min", "walker_slope_deg"} <= keys  # fmt: skip
    notes = {n["id"]: n for n in m["site_notes"]}
    assert "conservative" in notes["conservative-slope-no-go"]["text"]
    # the Validation tab reads the same validation.json that make validate writes
    shipped = json.loads((SITE / m["validation"]).read_text(encoding="utf-8"))
    repo = json.loads((ROOT / "validation.json").read_text(encoding="utf-8"))
    assert shipped == repo


def test_no_layer_calls_terrain_a_shelter():
    m = json.loads((SITE / "manifest.json").read_text(encoding="utf-8"))
    ids = {lay["id"] for lay in m["layers"]}
    assert "shelter_minutes" not in ids and "minutes_to_rover" in ids
    shielding = next(lay for lay in m["layers"] if lay["id"] == "shielding")
    assert "not counted as shelter" in shielding["description"]


# --- G5 and the timeline's comm shadows with the rover as a relay ---


def test_numpy_line_of_sight_matches_the_derive_version():
    from ariadne.package import sight

    los = pytest.importorskip("ariadne.derive.los", exc_type=ImportError)  # numba; CI runs it
    rng = np.random.default_rng(5)
    z = rng.normal(0, 1.5, (80, 80)).cumsum(0).cumsum(1) * 0.02
    t = Affine(1.0, 0, 1000.0, 0, -1.0, 2000.0)
    for _ in range(200):
        a = (1000 + rng.uniform(1, 79), 2000 - rng.uniform(1, 79))
        b = (1000 + rng.uniform(1, 79), 2000 - rng.uniform(1, 79))
        assert sight.line_of_sight(z, t, a, b, 3.0, 1.8) == los.line_of_sight(z, t, a, b, 3.0, 1.8)


def test_line_of_sight_is_blocked_by_a_wall_and_follows_the_rover_relay():
    from ariadne.package import sight

    z = np.zeros((40, 40))
    z[:, 20] = 10.0  # a wall down the middle
    t = Affine(1.0, 0, 0.0, 0, -1.0, 40.0)
    assert not sight.line_of_sight(z, t, (5.5, 20.5), (35.5, 20.5), 3.0, 1.8)
    assert sight.line_of_sight(z, t, (5.5, 20.5), (15.5, 30.5), 3.0, 1.8)
    plan = {
        "stations": [{"relay": "STAGING"}, {"relay": "RELAY1"}],
        "rover": {"ends_at": "RELAY1",
                  "relays": [{"id": "STAGING", "xy_m": [5.5, 20.5]},
                             {"id": "RELAY1", "xy_m": [35.5, 20.5]}]},
        "margins": [
            {"xy_m": [10.5, 20.5], "leg": 0, "station": None},
            {"xy_m": [10.5, 20.5], "leg": 0, "station": 0},  # the rover moves during this visit
            {"xy_m": [30.5, 20.5], "leg": 1, "station": None},
            {"xy_m": [30.5, 20.5], "leg": 2, "station": None},
        ],
    }  # fmt: skip
    assert sight.relays_per_sample(plan) == [["STAGING"], ["STAGING", "RELAY1"], ["RELAY1"],
                                              ["RELAY1"]]  # fmt: skip
    assert sight.samples_in_sight(plan, z, t, 3.0, 1.8) == [True, False, True, True]


def test_overcautious_marks_list_the_samples_near_a_flagged_cell():
    plan = {"margins": [{"t_min": float(i), "xy_m": [float(10 * i), 0.0]} for i in range(6)]}
    near = timeline.overcautious_near(plan, np.array([[30.0, 20.0], [500.0, 0.0]]), 25.0)
    assert [x["t_min"] for x in near] == [2.0, 3.0, 4.0]  # 22.4, 20.0 and 22.4 m away
    assert near[1]["nearest_xy_m"] == [30.0, 20.0] and near[1]["distance_m"] == 20.0
    assert timeline.overcautious_near(plan, np.zeros((0, 2)), 25.0) == []


@pytest.mark.parametrize("preset", ["safest", "balanced", "most_science"])
def test_packaged_plans_carry_relay_comm_shadows_and_overcautious_marks(preset):
    plan = json.loads((SITE / "plans" / f"{preset}.json").read_text(encoding="utf-8"))
    oc = plan["overcautious"]
    assert oc["label"] == "MODELED" and oc["radius_m"] == 25
    assert all(x["distance_m"] <= oc["radius_m"] for x in oc["samples"])
    # comm shadows now come from the relay the rover is parked at, so they agree with the plan's
    # own comms check (pairwise on the 1 m DEM against a viewshed on the 2 m grid: close, not equal)
    longest = max((c["end_min"] - c["start_min"] for c in plan["timeline"]["comm_shadows"]),
                  default=0.0)  # fmt: skip
    assert longest <= plan["totals"]["longest_comm_shadow_min"] + 1.0
    assert "relay site it is parked at" in plan["timeline"]["comm_note"]
