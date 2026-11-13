# Derived layers: boxwork

Written by `ariadne derive --site boxwork` (pipeline 0.0.0, 2026-11-09). Do not edit by hand. The layers themselves are in `data/sites/boxwork/derived/` (not committed); each has a provenance record.

Grid: 3,514 × 3,925 cells of 1 m.

## Horizons and shielding

Shielding uses n = 1.19 from the Murray Buttes calibration. Horizons combine the 1 m DEM out to 2 km with MOLA out to 100 km, both with the planet's curvature subtracted. MOLA is placed on the 1 m DEM by co-registration: sampled 230 m east and 400 m south of each point, then lowered 13.9 m, which brings the median absolute difference between the two (after smoothing the 1 m DEM to MOLA's pixel size) to 14.8 m, from 18.5 m with a height offset alone. The far field sets the horizon in 46.9% of all cell and azimuth pairs.

| Layer | 5th percentile | Median | 95th percentile | Minimum |
| --- | --- | --- | --- | --- |
| S, near and far field | 0.9040 | 0.9745 | 0.9931 | 0.1829 |
| S, near field only | 0.9072 | 0.9760 | 0.9971 | 0.1829 |
| Blocked share of the sky | 7.8% | 14.6% | 25.3% | max 88.9% |

| Point | S | Blocked sky |
| --- | --- | --- |
| Altadena | 0.9896 | 10.5% |
| Valle de la Luna | 0.9785 | 14.3% |
| Nevado Sajama | 0.9789 | 14.1% |
| Nevado Sajama2 | 0.9790 | 14.1% |

## How far-field horizons shift sunrise and sunset

Times are local true solar time at the site centre; the sun's centre is used. 'Far field' is the change from adding MOLA terrain to the 1 m DEM horizons, which reach 2 km or the crop edge; 'all terrain' is the change from a flat, open horizon. Statistics cover every 25th cell in each direction that lies at least 1 km from the crop edge, so its 1 m DEM horizons reach at least that far in every direction; nearer the edge, a near-field-only horizon would be cut short and exaggerate the far field.

| Date | Ls | Flat-horizon sunrise and sunset | Far field delays sunrise (median, 90th percentile, max) | Cells where the far field delays sunrise over 1 min | Far field advances sunset (median, 90th percentile, max) | All terrain delays sunrise (median) | All terrain advances sunset (median) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ls 0 (2024-11-13) | 0° | 06:00 and 18:00 | 0.0, 14.4, 31.2 min | 34.2% | 2.0, 25.9, 42.9 min | 53.2 min | 7.1 min |
| Ls 90 (2025-05-30) | 90° | 06:09 and 17:51 | 0.0, 0.0, 20.3 min | 3.0% | 19.4, 45.1, 68.2 min | 43.1 min | 9.0 min |
| Ls 180 (2025-11-30) | 180° | 06:00 and 18:00 | 0.0, 14.5, 31.3 min | 34.2% | 1.7, 25.6, 42.5 min | 53.4 min | 7.1 min |
| Ls 270 (2026-04-25) | 270° | 05:51 and 18:09 | 0.0, 8.1, 27.2 min | 22.3% | 0.0, 11.9, 33.9 min | 65.0 min | 26.6 min |
| sol 4718 (reference) (2025-11-13) | 171° | 06:01 and 17:59 | 0.0, 12.8, 30.0 min | 30.8% | 5.2, 28.0, 44.9 min | 51.6 min | 7.0 min |

At named points (sunrise and sunset; near field only, then with the far field):

| Date | Point | Sunrise | Sunset | Far field delays sunrise | Far field advances sunset |
| --- | --- | --- | --- | --- | --- |
| Ls 0 | Altadena | 06:41 → 06:41 | 17:41 → 17:41 | 0.0 min | 0.0 min |
| Ls 0 | Valle de la Luna | 06:43 → 06:43 | 17:10 → 17:10 | 0.0 min | 0.0 min |
| Ls 0 | Nevado Sajama | 06:42 → 06:42 | 17:08 → 17:08 | 0.0 min | 0.0 min |
| Ls 0 | Nevado Sajama2 | 06:42 → 06:42 | 17:08 → 17:08 | 0.0 min | 0.0 min |
| Ls 90 | Altadena | 06:31 → 06:31 | 17:30 → 17:30 | 0.0 min | 0.0 min |
| Ls 90 | Valle de la Luna | 06:36 → 06:36 | 17:29 → 17:29 | 0.0 min | 0.0 min |
| Ls 90 | Nevado Sajama | 06:35 → 06:35 | 17:33 → 17:33 | 0.0 min | 0.0 min |
| Ls 90 | Nevado Sajama2 | 06:35 → 06:35 | 17:33 → 17:33 | 0.0 min | 0.0 min |
| Ls 180 | Altadena | 06:41 → 06:41 | 17:41 → 17:41 | 0.0 min | 0.0 min |
| Ls 180 | Valle de la Luna | 06:43 → 06:43 | 17:09 → 17:09 | 0.0 min | 0.0 min |
| Ls 180 | Nevado Sajama | 06:42 → 06:42 | 17:07 → 17:07 | 0.0 min | 0.0 min |
| Ls 180 | Nevado Sajama2 | 06:42 → 06:42 | 17:07 → 17:07 | 0.0 min | 0.0 min |
| Ls 270 | Altadena | 06:37 → 06:37 | 17:48 → 17:48 | 0.0 min | 0.0 min |
| Ls 270 | Valle de la Luna | 06:43 → 06:43 | 16:55 → 16:55 | 0.0 min | 0.0 min |
| Ls 270 | Nevado Sajama | 06:43 → 06:43 | 16:56 → 16:56 | 0.0 min | 0.0 min |
| Ls 270 | Nevado Sajama2 | 06:43 → 06:43 | 16:56 → 16:56 | 0.0 min | 0.0 min |
| sol 4718 (reference) | Altadena | 06:42 → 06:42 | 17:39 → 17:39 | 0.0 min | 0.0 min |
| sol 4718 (reference) | Valle de la Luna | 06:43 → 06:43 | 17:15 → 17:15 | 0.0 min | 0.0 min |
| sol 4718 (reference) | Nevado Sajama | 06:42 → 06:42 | 17:11 → 17:11 | 0.0 min | 0.0 min |
| sol 4718 (reference) | Nevado Sajama2 | 06:42 → 06:42 | 17:12 → 17:12 | 0.0 min | 0.0 min |

## Other layers

| Layer | Summary |
| --- | --- |
| Slope scale (MODELED) | walker 2.50 m disc, rover 3.05 m disc: a plane fit no finer than the DEM's effective resolution (2.5 m) or the rover's length |
| Walkability, walker (MODELED) | go 55.3%, caution 26.3%, no-go 18.4% |
| Walkability, rover (MODELED) | go 37.5%, caution 33.0%, no-go 29.5% |
| Rover, for comparison (not used) | 1 m Horn slope (Phase 2 first run): no-go 29.5%; coarse resolution (5.0 m disc): no-go 28.4% |
| Sand proxy | uses THEMIS night IR: yes; drop-off cells 5.3% |
| Ridges and hollows (MODELED, PLACEHOLDER thresholds) | ridges 14.0%, hollows 16.6% of the site |
| Fractures | 2734 lines of 10 m or more, 62.51 km in all, median 16 m |
| Terrain shielding zones (S ≤ 0.95, PLACEHOLDER; information only, not shelter) | 1,310,076 m² (9.5% of the site) |
| Minutes to a shielding zone or the staging point (PLACEHOLDER pace; the route engine uses walking minutes to the rover) | median 4.2, 95th percentile 12.3, max 33.1 |
| Line of sight from the staging antenna | 14.8% of the site (line of sight only, no radio model) |
| Science transects | 2655 transects (206 on mapped fractures); station scores median 0.88 (5th to 95th percentile 0.63 to 0.95); 254 prior targets; missing term: spectral |
| Confidence | median 0.60; 0.0% of cells below 0.5 |
| Candidate DEM mosaic seams | 10.9 km of stereo-pair footprint edges (T3, Traverse, West); 4.7% of the site within 30 m |
| Map may be over-cautious here (check by eye) | walker: 0.9% of the site (4.9% of its slope no-go cells); rover: 1.4% (5.0%); no-go by slope in a seam zone or below confidence 0.55 |
| Light, sol 4718 | sunrise median 06:45, sunset median 17:51; insolation median 0.99 of flat open ground |

## Drill sites

| Hole | Sol (blog) | PLACES site, drive | Held sols | Easting, northing (m) |
| --- | --- | --- | --- | --- |
| Altadena | 4564 | 116, 1944 | 4560 to 4570 | 8,143,367.9, -284,509.5 |
| Valle de la Luna | 4693 | 119, 1722 | 4687 to 4708 | 8,143,219.3, -284,983.2 |
| Nevado Sajama | 4718 | 120, 82 | 4711 to 4740 | 8,143,217.5, -284,993.2 |
| Nevado Sajama2 | 4795 | 120, 574 | 4789 to 4804 | 8,143,216.8, -284,993.1 |

## Not done here

- Relative ground temperature is implemented and tested, but needs the REMS archive, which Phase 6 reads.
- The spectral term of the science score needs CRISM summary parameters, not read yet; its weight is set aside.
- Ridge thresholds are PLACEHOLDER until the hand labels arrive (`ariadne ridge-sample` builds the labeling page; `ariadne ridge-tune` tunes on one half and tests on the other).
- Seams between the CCDs inside one HiRISE image are not mapped; only stereo-pair footprint edges are.
- Terrain shielding zones block a few percent of the dose at most, so they are information only, not shelter; the rover is the shelter (team decision, 2026-11-10). Their minutes use a PLACEHOLDER pace; the route engine works out walking minutes to the rover with the walker model.
