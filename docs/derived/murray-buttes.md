# Derived layers: murray-buttes

Written by `ariadne derive --site murray-buttes` (pipeline 0.0.0, 2026-11-09). Do not edit by hand. The layers themselves are in `data/sites/murray-buttes/derived/` (not committed); each has a provenance record.

Grid: 4,001 × 4,001 cells of 1 m.

## Shielding calibration (Murray Buttes)

Reference: Ehresmann et al. 2021, JGR Planets 126, e2021JE006851. Parked beside Butte M12 on sols 1456 to 1467, RAD measured 3.8% ± 0.4% less dose than the expected dose fitted on sols 1440 to 1455 and 1468 to 1480. So n is fitted to S(parking) f(parking) / mean over baseline sols of S f, with each baseline sol represented by the positions Curiosity held at its start and end.

| Quantity | Value |
| --- | --- |
| Fitted n (target ratio 0.962) | **1.19** |
| n range for 3.8% ± 0.4% | 1.07 to 1.33 |
| n for the rounded 4% (ratio 0.96) | 1.13 |
| Model ratio at n = 0 (isotropic sky) and n = 10 | 0.901 and 1.000 |
| S at the parking spot, mean S over the baseline (at the fitted n) | 0.952, 0.990 |
| Observer height | 1 m above the ground (PLACEHOLDER) |
| MOLA placed on the 1 m DEM | sampled 580 m east and 240 m south of each point, then lowered 17.1 m (median absolute difference 3.8 m; 12.0 m with a height offset alone) |
| Pressure term spread over the baseline | 0.0014 (negligible) |

Result: **PASS**. Label: "calibrated on one RAD measurement". 

### Horizon check against the paper's sky mask

The paper's horizon mask comes from rover images, localization and MSL elevation models; ours comes from the 1 m DEM and MOLA. This is a comparison, not a gate.

| Quantity | This model | Ehresmann et al. 2021 |
| --- | --- | --- |
| Blocked share of the sky | 18.5% | 19.0% |
| Mean blocking angle | 10.8° | 11° |
| Butte half (azimuth 240° to 60°), mean angle | 15.8° | 16° |
| Other half, mean angle | 5.8° | 6° |
| Largest angle | 28.8° | about 30° |
| Blocked share with near-field horizons only | 16.2% | |
| Blocked share, mean over the baseline positions | 9.5% | |

### Sensitivity

| Case | n |
| --- | --- |
| observer 0.5 m above the ground | 1.38 |
| observer 2 m above the ground | 0.84 |
| near-field horizons only (no MOLA) | 1.17 |

Caveats: The butte also sends back some albedo radiation, which the paper could not separate and this model leaves out. RAD's dose is omnidirectional; the model treats the whole dose as arriving from the sky above the horizon. One measurement fixes one number (n); it does not validate the model elsewhere. The model has no neutral-particle term, so the measured 7.5% drop in neutral particles is reported, not predicted.

Other published estimate: Guo et al. 2021 (Astron. Astrophys. Rev. 29:8, section 5.4) find 5% +/- 1% with a different baseline (the same phase of the four previous solar rotations); not fitted here.

## Horizons and shielding

Shielding uses n = 1.19 from the Murray Buttes calibration. Horizons combine the 1 m DEM out to 2 km with MOLA out to 100 km, both with the planet's curvature subtracted. MOLA is placed on the 1 m DEM by co-registration: sampled 580 m east and 240 m south of each point, then lowered 17.1 m, which brings the median absolute difference between the two (after smoothing the 1 m DEM to MOLA's pixel size) to 3.8 m, from 12.0 m with a height offset alone. The far field sets the horizon in 80.7% of all cell and azimuth pairs.

| Layer | 5th percentile | Median | 95th percentile | Minimum |
| --- | --- | --- | --- | --- |
| S, near and far field | 0.9855 | 0.9941 | 0.9955 | 0.6538 |
| S, near field only | 0.9873 | 0.9979 | 0.9998 | 0.6538 |
| Blocked share of the sky | 7.2% | 7.9% | 11.8% | max 53.8% |

| Point | S | Blocked sky |
| --- | --- | --- |
| Parking spot (site 57, drive 2798) | 0.9523 | 18.5% |

## How far-field horizons shift sunrise and sunset

Times are local true solar time at the site centre; the sun's centre is used. 'Far field' is the change from adding MOLA terrain to the 1 m DEM horizons, which reach 2 km or the crop edge; 'all terrain' is the change from a flat, open horizon. Statistics cover every 25th cell in each direction that lies at least 1 km from the crop edge, so its 1 m DEM horizons reach at least that far in every direction; nearer the edge, a near-field-only horizon would be cut short and exaggerate the far field.

| Date | Ls | Flat-horizon sunrise and sunset | Far field delays sunrise (median, 90th percentile, max) | Cells where the far field delays sunrise over 1 min | Far field advances sunset (median, 90th percentile, max) | All terrain delays sunrise (median) | All terrain advances sunset (median) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ls 0 (2015-06-18) | 0° | 06:00 and 18:00 | 9.3, 15.0, 19.1 min | 77.6% | 14.1, 20.0, 27.1 min | 22.8 min | 12.4 min |
| Ls 90 (2016-01-03) | 90° | 06:09 and 17:51 | 1.1, 7.9, 12.2 min | 50.7% | 24.5, 30.0, 35.5 min | 8.3 min | 17.8 min |
| Ls 180 (2016-07-04) | 180° | 06:00 and 18:00 | 9.0, 14.7, 18.8 min | 77.4% | 14.1, 20.1, 27.2 min | 22.5 min | 12.4 min |
| Ls 270 (2016-11-28) | 270° | 05:51 and 18:09 | 30.7, 37.6, 41.1 min | 95.1% | 5.0, 11.9, 19.8 min | 51.8 min | 10.7 min |
| sol 1461 (reference) (2016-09-14) | 222° | 05:54 and 18:06 | 27.7, 32.5, 34.8 min | 94.2% | 6.8, 13.5, 20.4 min | 44.9 min | 9.7 min |

At named points (sunrise and sunset; near field only, then with the far field):

| Date | Point | Sunrise | Sunset | Far field delays sunrise | Far field advances sunset |
| --- | --- | --- | --- | --- | --- |
| Ls 0 | Parking spot (site 57, drive 2798) | 06:07 → 06:21 | 17:29 → 17:29 | 14.4 min | 0.0 min |
| Ls 90 | Parking spot (site 57, drive 2798) | 06:18 → 06:18 | 16:16 → 16:16 | 0.2 min | 0.0 min |
| Ls 180 | Parking spot (site 57, drive 2798) | 06:07 → 06:21 | 17:29 → 17:29 | 13.9 min | 0.0 min |
| Ls 270 | Parking spot (site 57, drive 2798) | 06:09 → 06:41 | 17:51 → 17:51 | 33.5 min | 0.0 min |
| sol 1461 (reference) | Parking spot (site 57, drive 2798) | 06:08 → 06:38 | 17:56 → 17:56 | 30.2 min | 0.1 min |

## Other layers

This site is for validation only. It has no boxwork, so its ridge and fracture layers run the same code as the boxwork but carry no science meaning here.

| Layer | Summary |
| --- | --- |
| Walkability, walker (MODELED) | go 87.2%, caution 11.7%, no-go 1.1% |
| Walkability, rover (MODELED) | go 73.8%, caution 23.9%, no-go 2.4% |
| Sand proxy | uses THEMIS night IR: no (no THEMIS input for this site); drop-off cells 0.2% |
| Ridges and hollows (MODELED, PLACEHOLDER thresholds) | ridges 2.4%, hollows 3.9% of the site |
| Fractures | 908 lines of 10 m or more, 24.62 km in all, median 18 m |
| Terrain shelters (S ≤ 0.95, PLACEHOLDER) | 18,675 m² (0.1% of the site) |
| Minutes to shelter or the staging point (PLACEHOLDER pace) | median 19.5, 95th percentile 61.2, max 100.4 |
| Line of sight from the staging antenna | 16.6% of the site (line of sight only, no radio model) |
| Confidence | median 0.60; 0.0% of cells below 0.5 |
| Light, sol 1461 | sunrise median 06:38, sunset median 17:57; insolation median 0.97 of flat open ground |

## Not done here

- Relative ground temperature is implemented and tested, but needs the REMS archive, which Phase 6 reads.
- The spectral term of the science score needs CRISM summary parameters, not read yet; its weight is set aside.
- Ridge thresholds are PLACEHOLDER until a hand-labeled sample exists, so the ridge map has no precision or recall yet.
- Minutes-to-shelter uses a PLACEHOLDER pace until Phase 3 brings the NASA/TP-2010-216125 walking model.
