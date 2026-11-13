# Route plans: boxwork

Written by `ariadne plan` (pipeline 0.0.0, 2026-11-12T03:33:52+00:00). Every plan is MODELED and rests on PLACEHOLDER settings (config/presets.json, config/suits.json); the walker model is EXTRAPOLATED to Mars gravity.

## Setting

| Item | Value |
| --- | --- |
| Staging point (rover), PLACEHOLDER | E 8,143,367.9 m, N -284,509.5 m |
| Planning grid | 2 m cells, 1200 × 1200 |
| Walkable for the walker | 74.8% of the grid; of that, 35.1% within 10 min, 61.3% within 20 min walk of a place the rover can park |
| In line of sight of the rover antenna | 22.0% of the grid from the staging point; 51.2% from the staging point or a relay site |
| Candidate transects | 30 whole fracture (or crest), wall and hollow transects: all three points walkable and in line of sight of the rover at some relay site, each with an overwatch point within 50 m, within 800 m |
| Scenario (PLACEHOLDER) | EVA up to 360 min (6 h); 390 min of consumables (6 h plus the 30 min reserve); 15 min per station, so 45 min per transect plus its internal walk |
| Staging point passable for the rover | yes (rover class go or caution there; the rover's drive to it is not planned) |

## Presets (all PLACEHOLDER)

| Preset | Reserve (min) | Walking limit to the rover (min) | Caution (hazard) weight | Uncertainty weight | Objective | Usable transects |
| --- | --- | --- | --- | --- | --- | --- |
| safest | 45 | 10 | 3 | 3 | science value | 8 |
| balanced | 30 | 20 | 1 | 1 | science value | 20 |
| most_science | 30 | 20 | 0 | 1 | complete transects, then value | 20 |

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
| safest | 4, 8 | 4, 4 | 10.93, 10.93 |
| balanced | 15, 20 | 7, 7 | 18.94, 18.94 |
| most_science | 15, 20 | 7, 7 | 19.11, 19.11 |

## Reference plans (OR-Tools)

Each plan visits whole transects only: every visited transect's fracture (or crest), wall and hollow stations, in that order.

| Preset | Transects | Stations | Science value | Minutes | Consumables (min) | Distance (m) | Least thread margin (min) | Worst walking minutes to the rover | Longest comm shadow (min) | Rover moves, ends at | Checks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| safest | 4 | 12 | 10.93 | 216 | 150 | 1,878 | 195.1 | 9.7 | 1.1 | 0, STAGING | thread pass, buddy pass, shelter pass, comms pass, rover pass |
| balanced | 7 | 21 | 18.94 | 355 | 236 | 1,912 | 124.0 | 19.6 | 2.1 | 2, STAGING | thread pass, buddy pass, shelter pass, comms pass, rover pass |
| most_science | 7 | 21 | 19.11 | 359 | 241 | 2,337 | 119.3 | 15.8 | 0.3 | 2, STAGING | thread pass, buddy pass, shelter pass, comms pass, rover pass |

## Price of safety (Safest against Most science)

Safest gives up 8.18 of science value (42.8% of Most science's 19.11) and 3 transect(s), and gains 75.8 min of least thread margin above its reserve (195.1 against 119.3); its reserve is 45 min against 30, and its worst walk to the rover 9.7 min against 15.8. All MODELED, on PLACEHOLDER presets.

Do the presets separate? Yes: Safest visits 4 transects and Most science 7, 3 of them in common.

## Storm mode along the plans (MODELED, PLACEHOLDER event)

At least every 5 minutes of walking along each plan (and once per station visit, where the crew stands still), the refuge with the lowest modeled dose over a 120-minute event (PLACEHOLDER until Phase 6 replays May 2024), counting the exposed walk there: the rover (S 0.5, PLACEHOLDER), the nearest terrain shielding zone at its own S, or staying put. Doses are relative, in open-sky minutes. Over an event this long the rover wins wherever it can be reached: terrain shields a few percent, so it wins only for events of a few minutes.

| Preset | Samples | Rover chosen | Terrain chosen | Stay chosen | Longest walk to the refuge (min) | Mean dose avoided (open-sky min) |
| --- | --- | --- | --- | --- | --- | --- |
| safest | 17 | 17 | 0 | 0 | 9.6 | 51.5 |
| balanced | 26 | 26 | 0 | 0 | 19.6 | 47.2 |
| most_science | 28 | 28 | 0 | 0 | 15.4 | 50.4 |

## Thread over random scenarios

1000 of 1000 random scenarios kept the thread at every sample (random transect subsets, EVA limits of 120 to 420 min and consumables of 150 to 450 min, Balanced limits; seed 20261109). The least margin above the reserve was 2.07 min; plans visited 3.6 transects and moved the rover 1.1 times on average; C_home follows the rover.

## Assumptions

- Walker model: Minetti et al. 2002 cost of walking against gradient (Earth, unsuited) with a PLACEHOLDER suit and gravity factor of 1.0, a PLACEHOLDER top speed of 1.0 m/s and a PLACEHOLDER power ceiling. NASA/TP-2010-216125 publishes no coefficients for its model, so it is used only for the tested ranges behind the EXTRAPOLATED flag.
- Hazard (the caution penalty) is the Phase 2 walker cost multiplier less 1; relative dose is the shielding index S; uncertainty is 1 − confidence. A transect's value is the sum of its three Phase 2 station scores (spectral term missing).
- The planner stays conservative: slope no-go cells are never entered, even where the map may be over-cautious (seam or low-confidence zones); the surfaces mark those cells for the crew to check by eye.
- Comms is line of sight only from a 3 m antenna on the rover at the relay site it is parked at; no radio model. While the rover drives during the first leg, contact is assumed from its destination.
- The buddy rule is met by an overwatch point found for every station; the partner's own walk to it is not timed.
- The thread's C_home is the consumables to walk to the rover's current relay site; during a move, the larger of the two sites' values at that station.
- Shelter is the rover (team decision, 2026-11-10): the shelter limit is walking minutes to the rover wherever it is. Parked, that is the walk to its relay site; driving during a station visit, the walk from the station to the farthest point of its drive; driving during the first leg, the walk to where it is at that moment (positions every half minute of the drive, the larger of the two around each moment). Terrain shielding zones block a few percent of the dose at most and are not shelter.
