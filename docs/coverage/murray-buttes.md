# Coverage and georeferencing: Murray Buttes parking spot, Gale crater

Written by `ariadne fetch --site murray-buttes` (pipeline 0.0.0) on 2026-11-09T05:20:00Z. Do not edit by hand; rerun the fetch instead.

## Site box

| Item | Value | Label |
| --- | --- | --- |
| Selection | parking position, sols 1455 to 1468 (2016-09-09 to 2016-09-21 UTC) | DERIVED from PLACES |
| Rover localizations in the window | 151 | MEASURED (PLACES) |
| Buffer | 2,000 m | PLACEHOLDER |
| Box, easting | 8,139,557.9 to 8,143,557.9 m (4,000 m) | DERIVED |
| Box, northing | −280,306.7 to −276,306.7 m (4,000 m) | DERIVED |
| Box, longitude (east) | 137.31927 to 137.38675° | DERIVED |
| Box, latitude (planetocentric) | −4.72894 to −4.66146° | DERIVED |
| Parking position | site 57, drive 2798, held from sol 1455 to sol 1468; E 8,141,557.908 m, N −278,306.692 m, elevation −4,379.46 m | MEASURED (PLACES) |

## Products

| File | Source | Pixels | Pixel size | Read method | Time | Label |
| --- | --- | --- | --- | --- | --- | --- |
| dem.tif | `usgs-gale-dem-1m` | 4,001 × 4,001 | 1.0 m | gdal-bands | 35 s | MEASURED |
| ortho.tif | `usgs-gale-ortho-25cm` | 16,001 × 16,001 | 0.25 m | range-requests | 40 s | MEASURED |
| regional_dem.tif | `mola-dem-463m` | 450 × 450 | 463.09 m | range-requests | 5 s | MEASURED |
| color.tif | `usgs-gale-hirise-lrgb` | not made: the source does not cover the whole site box | | | | |

## Where the elevation comes from

The USGS product lists 12 HiRISE stereo pairs and falls back to CTX, then HRSC, then MOLA elsewhere. A pair counts as HiRISE stereo where its two images overlap (footprints from the PDS Orbital Data Explorer). Label: DERIVED. Footprint vertices are rounded to 0.001° of longitude (about 59 m), so class edges are uncertain by roughly 30 m.

| DEM source | Share of the site box | Share of Curiosity's localizations in the box |
| --- | --- | --- |
| HiRISE stereo | 100.0% | 100.0% |
| CTX, HRSC or MOLA | 0.0% | 0.0% |

Localizations checked: 16,064. DEM nodata cells in the box: 0.

| USGS stereo pair | Share of the site box |
| --- | --- |
| West | 69.0% |
| Traverse | 48.9% |
| West of Center | 32.7% |

Pairs with no stereo overlap inside the box: Center, Center Gap, East, East Gap, G2, T1, T2, T3, West Gap.

| Public HiRISE DTM | Share of the site box |
| --- | --- |
| DTEEC_009650_1755_009716_1755_U01 | 65.3% |
| DTEEC_040770_1755_039280_1755_A01 | 58.3% |
| DTEEC_009149_1750_009294_1750_U01 | 28.8% |
| DTEEC_018854_1755_018920_1755_U01 | 27.2% |
| DTEEC_001488_1750_001752_1750_U02 | 1.7% |

**Gap-fill decision:** not needed. 100.0% of Curiosity's localizations and 100.0% of the box lie on HiRISE stereo (team rule: at least 99% and 90%). Cells outside HiRISE stereo get a lower confidence in the Phase 2 uncertainty layer.

## Georeferencing check (acceptance test B8)

The DEM crop is sampled at every PLACES localization inside the box (all sols) and compared with the PLACES elevation; the comparison is repeated for horizontal shifts of up to ±10 m to find the best fit.
PLACES records the DEM pixel of each localization, so its elevations are tied to an orbital DEM: close agreement confirms that the crop lines up with Curiosity's recorded positions, not the DEM's absolute height accuracy. The shift search is the test of horizontal alignment.

| Measure | Value | Target |
| --- | --- | --- |
| Localizations compared | 16,061 (3 outside or on nodata) | |
| Median of DEM − PLACES elevation | 0.01 m | within ±2.0 m |
| Median absolute deviation | 0.07 m | |
| 90th percentile of absolute deviation | 0.22 m | |
| Best-fit shift (east, north) | +0 m, +0 m | within ±2.0 m |
| Median absolute deviation at best shift | 0.07 m | |
| Crop bounds agree (DEM and orthophoto) | yes (largest edge difference 0.49 m) | within one DEM pixel |
| **Result** | **PASS** | |

Quicklook for a visual check (orthophoto, hillshade and every localization in the box in cyan): `data/sites/murray-buttes/quicklook.png` (not committed).
