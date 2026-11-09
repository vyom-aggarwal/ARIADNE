# Route plans: boxwork

Written by `ariadne plan` (pipeline 0.0.0, 2026-11-09T10:32:02+00:00). Every plan is MODELED and rests on PLACEHOLDER settings (config/presets.json, config/suits.json); the walker model is EXTRAPOLATED to Mars gravity.

## Setting

| Item | Value |
| --- | --- |
| Staging point (rover), PLACEHOLDER | E 8,143,367.9 m, N -284,509.5 m |
| Planning grid | 2 m cells, 1200 × 1200 |
| Walkable for the walker | 74.8% of the grid; 100.0% of that is within 20 min of shelter |
| In line of sight of the rover antenna | 22.0% of the grid |
| Candidate stations | 40 (walkable, in line of sight, with an overwatch point within 50 m, within 800 m) |
| Scenario (PLACEHOLDER) | EVA up to 240 min; 300 min of consumables; reserve 30 min; 15 min per station |
| Staging point passable for the rover | yes (rover class go or caution there; the rover's drive to it is not planned) |

## Reference plans (OR-Tools)

| Preset | Stations | Science value | Minutes | Consumables (min) | Distance (m) | Least thread margin (min) | Worst minutes to shelter | Longest comm shadow (min) | Checks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| safest | 13 | 12.35 | 235 | 164 | 2,078 | 105.9 | 3.3 | 1.4 | thread pass, buddy pass, shelter pass, comms pass, rover pass |
| balanced | 13 | 12.38 | 240 | 170 | 2,288 | 99.7 | 3.4 | 1.4 | thread pass, buddy pass, shelter pass, comms pass, rover pass |
| most_science | 13 | 12.37 | 238 | 167 | 2,175 | 102.9 | 3.4 | 1.4 | thread pass, buddy pass, shelter pass, comms pass, rover pass |

With these PLACEHOLDER settings the 240-minute EVA limit binds before the consumables do, and every preset's value weight is high enough that each takes nearly every station it can fit. So the three presets pick almost the same stations and differ mainly in the paths between them. The preset weights are PLACEHOLDER and are for the team to set.

## Thread over random scenarios

1000 of 1000 random scenarios kept the thread at every sample (random station subsets, EVA limits of 90 to 300 min and consumables of 120 to 360 min; seed 20261109). The least margin above the reserve was 1.99 min; plans visited 7.6 stations on average.

## Assumptions

- Walker model: Minetti et al. 2002 cost of walking against gradient (Earth, unsuited) with a PLACEHOLDER suit and gravity factor of 1.0, a PLACEHOLDER top speed of 1.0 m/s and a PLACEHOLDER power ceiling. NASA/TP-2010-216125 publishes no coefficients for its model, so it is used only for the tested ranges behind the EXTRAPOLATED flag.
- Hazard is the Phase 2 walker cost multiplier less 1; relative dose is the shielding index S; uncertainty is 1 − confidence. Station value is the Phase 2 station score (spectral term missing).
- Comms is line of sight only from a 3 m antenna on the rover at the staging point; no radio model and no relays.
- The buddy rule is met by an overwatch point found for every candidate station; the partner's own walk to it is not timed.
- The rover stays at the staging point; pickups elsewhere are not planned yet.
