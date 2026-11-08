# Written with AI assistance (Claude Code). See AI_USE.md.
"""Phase 0 environment check (A5): the pipeline stack installs and runs on this Python."""

import sys

import numpy as np


def test_python_is_at_least_3_12():
    assert sys.version_info >= (3, 12)


def test_ortools_cp_sat_solves_a_tiny_model():
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    x = model.new_int_var(0, 10, "x")
    y = model.new_int_var(0, 10, "y")
    model.add(x + y <= 12)
    model.maximize(2 * x + y)
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    assert status == cp_model.OPTIMAL
    assert (solver.value(x), solver.value(y)) == (10, 2)


def test_ortools_routing_solves_a_four_stop_loop():
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    # Four stops on a line at 0, 1, 2, 3; the shortest closed loop from 0 has length 6.
    pos = [0, 1, 2, 3]
    manager = pywrapcp.RoutingIndexManager(len(pos), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def dist(i, j):
        return abs(pos[manager.IndexToNode(i)] - pos[manager.IndexToNode(j)])

    cb = routing.RegisterTransitCallback(dist)
    routing.SetArcCostEvaluatorOfAllVehicles(cb)
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    solution = routing.SolveWithParameters(params)
    assert solution is not None
    assert solution.ObjectiveValue() == 6


def test_numba_compiles_a_loop():
    import numba

    @numba.njit(cache=False)
    def total(a):
        s = 0.0
        for v in a:
            s += v
        return s

    assert total(np.arange(10.0)) == 45.0


def test_rasterio_writes_and_reads_a_georeferenced_raster():
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio.transform import from_origin

    data = np.arange(12, dtype="float32").reshape(3, 4)
    transform = from_origin(8_141_606.0, -282_807.0, 1.0, 1.0)
    profile = dict(driver="GTiff", width=4, height=3, count=1, dtype="float32", transform=transform)
    with MemoryFile() as mem:
        with mem.open(**profile) as dst:
            dst.write(data, 1)
        with mem.open() as src:
            assert src.transform == transform
            np.testing.assert_array_equal(src.read(1), data)
    assert rasterio.__gdal_version__


def test_pyproj_handles_a_mars_sphere_projection():
    from pyproj import CRS, Transformer

    # Equirectangular on the 3,396,190 m Mars sphere, as used by the USGS Gale mosaics.
    mars_eqc = CRS.from_proj4("+proj=eqc +lat_ts=0 +lon_0=0 +R=3396190 +units=m +no_defs")
    mars_lonlat = CRS.from_proj4("+proj=longlat +R=3396190 +no_defs")
    fwd = Transformer.from_crs(mars_lonlat, mars_eqc, always_xy=True)
    inv = Transformer.from_crs(mars_eqc, mars_lonlat, always_xy=True)
    x, y = fwd.transform(137.4, -4.8)
    lon, lat = inv.transform(x, y)
    assert abs(lon - 137.4) < 1e-9 and abs(lat - (-4.8)) < 1e-9
    # x = R * lon in radians on a sphere.
    assert abs(x - 3_396_190 * np.radians(137.4)) < 1e-3


def test_remaining_stack_imports():
    import astroquery  # noqa: F401
    import pandas  # noqa: F401
    import scipy.ndimage  # noqa: F401
    import shapely.geometry
    import skimage.morphology  # noqa: F401
    import yaml  # noqa: F401

    assert shapely.geometry.box(0, 0, 2, 3).area == 6
