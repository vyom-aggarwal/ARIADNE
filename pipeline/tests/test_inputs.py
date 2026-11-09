# Written with AI assistance (Claude Code). See AI_USE.md.
"""Phase 2 inputs: drill sites, baseline sols, ChemCam tables, Trek tiles (acceptance test C12)."""

import math
from pathlib import Path

import pandas as pd
import pytest

from ariadne.config import load_derive_config, load_site_config, load_sources, setting
from ariadne.fetch import context, places
from ariadne.fetch.places import MARS_RADIUS_M

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def rover():
    return places.load_rover_positions(FIXTURES / "places_extract.csv")


def test_drill_sites_are_the_localizations_held_on_the_blog_sols(rover):
    cfg = load_site_config("boxwork")
    assert [d["name"] for d in cfg.drill_sites] == [
        "Altadena",
        "Valle de la Luna",
        "Nevado Sajama",
        "Nevado Sajama2",
    ]
    assert [d["sol"] for d in cfg.drill_sites] == [4564, 4693, 4718, 4795]
    got = {d["name"]: d for d in context.drill_site_positions(cfg.drill_sites, rover)}
    # docs/SOURCES_LOG.md, drill-positions-places
    expect = {
        "Altadena": (116, 1944, 8143367.86, -284509.49),
        "Valle de la Luna": (119, 1722, 8143219.32, -284983.21),
        "Nevado Sajama": (120, 82, 8143217.46, -284993.19),
        "Nevado Sajama2": (120, 574, 8143216.77, -284993.07),
    }
    for name, (site, drive, e, n) in expect.items():
        d = got[name]
        assert (d["site"], d["drive"]) == (site, drive)
        assert d["easting"] == pytest.approx(e, abs=0.01)
        assert d["northing"] == pytest.approx(n, abs=0.01)
    # the blog's "about 10 meters" between the hollow and ridge holes
    vl, ns = got["Valle de la Luna"], got["Nevado Sajama"]
    assert math.hypot(
        vl["easting"] - ns["easting"], vl["northing"] - ns["northing"]
    ) == pytest.approx(10.2, abs=0.2)


def test_sol_positions_give_start_and_end():
    df = pd.DataFrame(
        {
            "sol": [10, 12, 12, 15],
            "sclk": [1, 2, 3, 4],
            "site": [1, 1, 1, 1],
            "drive": [0, 1, 2, 3],
            "easting": [0.0, 1.0, 2.0, 3.0],
            "northing": [0.0] * 4,
            "elevation": [0.0] * 4,
        }
    )
    a, b = context.sol_positions(df, 12)  # drove on sol 12
    assert (a.easting, b.easting) == (0.0, 2.0)
    a, b = context.sol_positions(df, 13)  # parked all sol
    assert a.easting == b.easting == 2.0
    assert context.held_localization(df, 14).easting == 2.0
    with pytest.raises(ValueError):
        context.sol_positions(df, 5)


def test_baseline_sols_and_targets_come_from_the_paper():
    cfg = load_derive_config()
    assert setting(cfg, "calibration", "baseline_sols") == [[1440, 1455], [1468, 1480]]
    assert setting(cfg, "calibration", "parked_sols") == [1456, 1467]
    assert setting(cfg, "calibration", "reduction") == 0.038
    assert setting(cfg, "calibration", "reduction_uncertainty") == 0.004
    assert setting(cfg, "shielding", "kappa_ugy_per_day_per_pa") == -0.21
    for key in ("kappa_ugy_per_day_per_pa", "dose_ref_ugy_per_day", "scale_height_m"):
        assert cfg["shielding"][key]["label"] == "MEASURED" and cfg["shielding"][key]["source"]


def test_every_derive_setting_is_labeled():
    cfg = load_derive_config()
    for section, items in cfg.items():
        for key, item in items.items():
            if isinstance(item, dict) and "value" in item:
                assert item.get("label") in {"MEASURED", "DERIVED", "MODELED", "PLACEHOLDER"}, (
                    section,
                    key,
                )


def test_chemcam_file_names_yield_sclks(tmp_path):
    assert context.sclk_from_chemcam_file("CL5_815612460CCS_F1200000CCAM04709P3.CSV") == 815612460
    assert context.sclk_from_chemcam_file("notes.txt") is None
    table = tmp_path / "moc.csv"
    table.write_text(
        "sPDL Tool,Testset Quartiles,SiO2\n"
        ",Min,0.1\n"
        "File,Target,SiO2,Distance (m)\n"
        "CL5_815612460CCS_F1200000CCAM04709P3.CSV,aegis_post_4710a,50.9,2.50512\n"
        "CL5_815612540CCS_F1200000CCAM04709P3.CSV,aegis_post_4710a,49.7,2.50512\n",
        encoding="utf-8",
    )
    df = context.read_chemcam_moc(table)
    assert list(df.sclk) == [815612460, 815612540]
    assert df.distance_m.iloc[0] == pytest.approx(2.50512)


def test_trek_tiles_cover_a_box():
    lon, lat = 137.39, -4.81
    x, y = math.radians(lon) * MARS_RADIUS_M, math.radians(lat) * MARS_RADIUS_M
    tiles, t = context.trek_tiles_for_bounds((x - 1500, y - 1500, x + 1500, y + 1500), 9)
    assert (269, 902) in tiles
    size = context.trek_tile_size_deg(9)
    assert size == pytest.approx(360 / 1024)
    # the mosaic's top-left corner is the top-left of the first tile
    r0 = min(r for r, _ in tiles)
    assert t.f == pytest.approx(math.radians(90 - r0 * size) * MARS_RADIUS_M)
    assert t.a == pytest.approx(math.radians(size / 256) * MARS_RADIUS_M)


def test_new_sources_are_configured():
    s = load_sources()
    assert s["mola-dem-463m"].crop_buffer_m == 102000
    assert "CC0" in s["mola-dem-463m"].license
    assert s["trek-themis-night-ir"].kind == "wmts" and s["trek-themis-night-ir"].level == 9
    assert s["msl-chemcam-moc"].kind == "table" and len(s["msl-chemcam-moc"].files) == 3
