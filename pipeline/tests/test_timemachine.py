# Written with AI assistance (Claude Code). See AI_USE.md.
"""Time Machine (tests H1 to H3): light time from Horizons, the DONKI snapshot and the replay."""

import json

import pytest

from ariadne import timemachine as tm
from ariadne.guardrails import repo_root

ROOT = repo_root()

HORIZONS_SAMPLE = """
 Date__(UT)__HR:MN                delta      deldot  1-way_down_LT
******************************************************************
$$SOE
 2024-May-20 00:00     1.90487464110158  -6.5637624    15.84235931
 2024-May-20 06:00     1.90392689280112  -6.5647330    15.83447713
$$EOE
"""


def test_horizons_rows_are_parsed():
    rows = tm.parse_horizons(HORIZONS_SAMPLE)
    assert rows[0] == {"utc": "2024-05-20T00:00:00Z", "delta_au": 1.90487464110158,
                       "deldot_km_s": -6.5637624, "light_time_min": 15.84235931}  # fmt: skip
    assert len(rows) == 2
    with pytest.raises(ValueError):
        tm.parse_horizons("no table here")


def test_light_time_interpolates_and_refuses_outside_the_table():
    rows = tm.parse_horizons(HORIZONS_SAMPLE)
    mid = tm.light_time_at(rows, "2024-05-20T03:00:00Z")
    assert mid == pytest.approx((15.84235931 + 15.83447713) / 2)
    # the light time is the range over c: 1.9049 au is 15.84 light-minutes
    assert rows[0]["delta_au"] * 149597870.7 / 299792.458 / 60 == pytest.approx(15.842, abs=0.01)
    with pytest.raises(ValueError):
        tm.light_time_at(rows, "2024-06-01T00:00:00Z")


def test_bundled_table_is_within_one_second_of_horizons():
    lt, _ = tm.load_snapshots(ROOT)
    res = tm.light_time_check(lt)
    assert len(res["rows"]) == 3 and res["passed"], res
    assert res["worst_difference_s"] <= 1.0
    v = json.loads((ROOT / "validation.json").read_text(encoding="utf-8"))
    check = next(c for c in v["checks"] if c["id"] == "light-time")
    assert check["status"] == "pass"


def test_donki_snapshot_holds_the_may_20_event():
    _, dk = tm.load_snapshots(ROOT)
    cme = next(c for c in dk["cme"] if c["activityID"] == tm.EVENT_CME)
    assert cme["speed_km_s"] == pytest.approx(2678)
    assert "backsided" in cme["note"] and "05:22Z" in cme["note"]
    assert dk["notifications"] and dk["source"].startswith("https://api.nasa.gov/DONKI/")
    assert dk["flares_status"] == "ok" or dk["flares_status"].startswith("unavailable")


def test_replay_is_packaged_with_its_sources_and_mid_walk_starts():
    site = ROOT / "web" / "public" / "sites" / "boxwork"
    m = json.loads((site / "manifest.json").read_text(encoding="utf-8"))
    r = json.loads((site / m["replay"]).read_text(encoding="utf-8"))
    assert r["rad_dose_uGy"]["value"] == 8100 and r["rad_dose_uGy"]["label"] == "MEASURED"
    assert "astronaut standing next to Curiosity" in r["rad_dose_uGy"]["meaning"]
    assert r["event"]["onset_utc"] == "2024-05-20T05:22Z"
    lt, _ = tm.load_snapshots(ROOT)
    assert r["light_time_min"]["value"] == pytest.approx(tm.light_time_at(lt["table"],
                                                                          "2024-05-20T05:22Z"),
                                                         abs=0.01)  # fmt: skip
    for preset, start in r["alignment"]["start_min"].items():
        plan = json.loads((site / "plans" / f"{preset}.json").read_text(encoding="utf-8"))
        assert abs(start - plan["totals"]["minutes"] / 2) < plan["totals"]["minutes"] / 4
    assert "ai_assistance" in m
