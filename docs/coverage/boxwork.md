# Coverage and georeferencing: Mount Sharp boxwork, Gale crater

Written by `ariadne fetch --site boxwork` (pipeline 0.0.0) on 2026-11-09T00:02:49Z. Do not edit by hand; rerun the fetch instead.

## Site box

| Item | Value | Label |
| --- | --- | --- |
| Selection | rover extent, sols 4526 to 4853 (2025-05-01 to 2026-03-31 UTC) | DERIVED from PLACES |
| Rover localizations in the window | 2,893 | MEASURED (PLACES) |
| Buffer | 1,500 m | PLACEHOLDER |
| Box, easting | 8,141,605.6 to 8,145,119.5 m (3,514 m) | DERIVED |
| Box, northing | −286,730.7 to −282,806.7 m (3,924 m) | DERIVED |
| Box, longitude (east) | 137.35381 to 137.41309° | DERIVED |
| Box, latitude (planetocentric) | −4.83732 to −4.77112° | DERIVED |

## Products

| File | Source | Pixels | Pixel size | Read method | Time | Label |
| --- | --- | --- | --- | --- | --- | --- |
| dem.tif | `usgs-gale-dem-1m` | 3,514 × 3,925 | 1.0 m | gdal-bands | 32 s | MEASURED |
| ortho.tif | `usgs-gale-ortho-25cm` | 14,056 × 15,697 | 0.25 m | range-requests | 41 s | MEASURED |
| color.tif | `usgs-gale-hirise-lrgb` | 14,056 × 15,697 | 0.25 m | gdal-bands | 13 s | MEASURED |

## Where the elevation comes from

The USGS product lists 12 HiRISE stereo pairs and falls back to CTX, then HRSC, then MOLA elsewhere. A pair counts as HiRISE stereo where its two images overlap (footprints from the PDS Orbital Data Explorer). Label: DERIVED. Footprint vertices are rounded to 0.001° of longitude (about 59 m), so class edges are uncertain by roughly 30 m.

| DEM source | Share of the site box | Share of Curiosity's localizations in the box |
| --- | --- | --- |
| HiRISE stereo | 100.0% | 100.0% |
| CTX, HRSC or MOLA | 0.0% | 0.0% |

Localizations checked: 8,945. DEM nodata cells in the box: 0.

| USGS stereo pair | Share of the site box |
| --- | --- |
| T3 | 95.7% |
| Traverse | 79.4% |
| West | 26.2% |

Pairs with no stereo overlap inside the box: Center, Center Gap, East, East Gap, G2, T1, T2, West Gap, West of Center.

| Public HiRISE DTM | Share of the site box |
| --- | --- |
| DTEEC_019698_1750_019988_1750_U01 | 96.3% |
| DTEEC_009149_1750_009294_1750_U01 | 77.4% |
| DTEEC_009650_1755_009716_1755_U01 | 24.2% |
| DTEEC_040770_1755_039280_1755_A01 | 22.3% |

**Gap-fill decision:** not needed. 100.0% of Curiosity's localizations and 100.0% of the box lie on HiRISE stereo (team rule: at least 99% and 90%). Cells outside HiRISE stereo get a lower confidence in the Phase 2 uncertainty layer.

## Georeferencing check (acceptance test B8)

The DEM crop is sampled at every PLACES localization inside the box (all sols) and compared with the PLACES elevation; the comparison is repeated for horizontal shifts of up to ±10 m to find the best fit.
PLACES records the DEM pixel of each localization, so its elevations are tied to an orbital DEM: close agreement confirms that the crop lines up with Curiosity's recorded positions, not the DEM's absolute height accuracy. The shift search is the test of horizontal alignment.

| Measure | Value | Target |
| --- | --- | --- |
| Localizations compared | 8,944 (1 outside or on nodata) | |
| Median of DEM − PLACES elevation | −0.00 m | within ±2.0 m |
| Median absolute deviation | 0.10 m | |
| 90th percentile of absolute deviation | 0.49 m | |
| Best-fit shift (east, north) | +0 m, +0 m | within ±2.0 m |
| Median absolute deviation at best shift | 0.10 m | |
| Crop bounds agree (DEM and orthophoto) | yes (largest edge difference 0.42 m) | within one DEM pixel |
| **Result** | **PASS** | |

Quicklook for a visual check (orthophoto, hillshade and every localization in the box in cyan): `data/sites/boxwork/quicklook.png` (not committed).
