# Route plans: boxwork

Written by `ariadne plan` (pipeline 0.0.0, 2026-11-09T20:37:10+00:00). Every plan is MODELED and rests on PLACEHOLDER settings (config/presets.json, config/suits.json); the walker model is EXTRAPOLATED to Mars gravity.

## Setting

| Item | Value |
| --- | --- |
| Staging point (rover), PLACEHOLDER | E 8,143,367.9 m, N -284,509.5 m |
| Planning grid | 2 m cells, 1200 × 1200 |
| Walkable for the walker | 74.8% of the grid; of that, 100.0% within 10 min, 100.0% within 20 min of shelter |
| In line of sight of the rover antenna | 22.0% of the grid from the staging point; 51.2% from the staging point or a relay site |
| Candidate transects | 30 whole fracture (or crest), wall and hollow transects: all three points walkable and in line of sight of the rover at some relay site, each with an overwatch point within 50 m, within 800 m |
| Scenario (PLACEHOLDER) | EVA up to 360 min (6 h); 390 min of consumables (6 h plus the 30 min reserve); 15 min per station, so 45 min per transect plus its internal walk |
| Staging point passable for the rover | yes (rover class go or caution there; the rover's drive to it is not planned) |

## Presets (all PLACEHOLDER)

| Preset | Reserve (min) | Shelter limit (min) | Caution (hazard) weight | Uncertainty weight | Objective | Usable transects |
| --- | --- | --- | --- | --- | --- | --- |
| safest | 45 | 10 | 3 | 3 | science value | 27 |
| balanced | 30 | 20 | 1 | 1 | science value | 27 |
| most_science | 30 | 20 | 0 | 1 | complete transects, then value | 27 |

## Rover as a mobile comms relay (PLACEHOLDER rover settings)

From 311 rover-reachable candidate sites (50 m grid within 800 m of the staging point), greedy coverage chose 3 relay sites. Of the 150 highest-value whole transects within reach, 41 are in full sight of the rover at the staging point and 112 with the relay sites. The rover drives at 1 m/s on rover-go ground and 0.5 m/s on caution ground; it moves only during the last station of a transect (within the 15-minute visit, with that station in sight along the whole drive) or during the first leg, and the walk ends where the rover is.

| Relay | Easting, northing (m) | Drive from staging (min) |
| --- | --- | --- |
| STAGING | 8,143,368.5, -284,510.1 | 0.0 |
| RELAY1 | 8,142,918.5, -284,310.1 | 12.6 |
| RELAY2 | 8,143,168.5, -284,210.1 | 10.7 |
| RELAY3 | 8,143,168.5, -283,760.1 | 26.7 |

| Preset | Usable transects: staging only, with relay | Planned transects: staging only, with relay | Science value: staging only, with relay |
| --- | --- | --- | --- |
| safest | 15, 27 | 7, 7 | 18.94, 18.94 |
| balanced | 15, 27 | 7, 7 | 18.94, 18.94 |
| most_science | 15, 27 | 7, 7 | 19.11, 19.11 |

## Reference plans (OR-Tools)

Each plan visits whole transects only: every visited transect's fracture (or crest), wall and hollow stations, in that order.

| Preset | Transects | Stations | Science value | Minutes | Consumables (min) | Distance (m) | Least thread margin (min) | Worst minutes to shelter | Longest comm shadow (min) | Rover moves, ends at | Checks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| safest | 7 | 21 | 18.94 | 356 | 237 | 1,958 | 107.8 | 4.2 | 2.1 | 2, STAGING | thread pass, buddy pass, shelter pass, comms pass, rover pass |
| balanced | 7 | 21 | 18.94 | 355 | 236 | 1,912 | 124.0 | 4.2 | 2.1 | 2, STAGING | thread pass, buddy pass, shelter pass, comms pass, rover pass |
| most_science | 7 | 21 | 19.11 | 359 | 241 | 2,337 | 119.3 | 2.5 | 0.3 | 2, STAGING | thread pass, buddy pass, shelter pass, comms pass, rover pass |

## Thread over random scenarios

1000 of 1000 random scenarios kept the thread at every sample (random transect subsets, EVA limits of 120 to 420 min and consumables of 150 to 450 min, Balanced limits; seed 20261109). The least margin above the reserve was 2.10 min; plans visited 3.5 transects and moved the rover 1.0 times on average; C_home follows the rover.

## Assumptions

- Walker model: Minetti et al. 2002 cost of walking against gradient (Earth, unsuited) with a PLACEHOLDER suit and gravity factor of 1.0, a PLACEHOLDER top speed of 1.0 m/s and a PLACEHOLDER power ceiling. NASA/TP-2010-216125 publishes no coefficients for its model, so it is used only for the tested ranges behind the EXTRAPOLATED flag.
- Hazard (the caution penalty) is the Phase 2 walker cost multiplier less 1; relative dose is the shielding index S; uncertainty is 1 − confidence. A transect's value is the sum of its three Phase 2 station scores (spectral term missing).
- The planner stays conservative: slope no-go cells are never entered, even where the map may be over-cautious (seam or low-confidence zones); the surfaces mark those cells for the crew to check by eye.
- Comms is line of sight only from a 3 m antenna on the rover at the relay site it is parked at; no radio model. While the rover drives during the first leg, contact is assumed from its destination.
- The buddy rule is met by an overwatch point found for every station; the partner's own walk to it is not timed.
- The thread's C_home is the consumables to walk to the rover's current relay site; during a move, the larger of the two sites' values at that station.
