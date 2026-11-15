# ARIADNE: backup slide deck (seven slides)

For the demo field if the team uses slides instead of the video. The 2026 rules: at most seven slides including the title and intro slides, in English, with the team name, the team members and the challenge. Pictures are screenshots of the live app (`make footage` also saves stills) and real NASA imagery with credits. No NASA logos or mission patches.

## 1. ARIADNE: a thread home on Mars

- Team: [team name]; members: [names]
- Challenge: Interplanetary Survival Guide: Martian Map (NASA Space Apps 2026)
- Picture: the planner map of the Mount Sharp boxwork with the three routes.
- Footer: "Concept generated with Claude (claude.ai); software written with Claude Code. Data: NASA, USGS, JPL."

## 2. Why a thread home?

- 1971: Apollo 14's moonwalkers turned back an estimated 50 to 75 m short of Cone Crater's rim (NASA). Picture: AS14-66-09305 (credit: NASA).
- On Mars, help is far: Earth was 15.8 light-minutes away on May 20, 2024 (JPL Horizons).
- So every step must keep enough air to walk back to the rover with a reserve, and the crew must be able to act on its own.

## 3. Ten kinds of NASA data, one meter-scale map

- USGS 1 m elevation and 25 cm images (from HiRISE, CTX and ESA's HRSC), MOLA, Curiosity's 2,893 boxwork positions, ChemCam targets, drill holes, THEMIS, RAD.
- Layers: walkability, sky shielding calibrated on RAD at the Murray Buttes (3.8% dose drop reproduced), horizons to 100 km, line of sight, sunlight, ridges and fractures, science score, confidence.
- Picture: the layer panel with each layer's source, resolution, date and label.

## 4. Three plans that never break the thread

- Safest, Balanced and Most science: whole ridge, wall and hollow transects in a 6-hour walk; the rover is radio relay and shelter.
- Price of safety: Safest gives up 43% of the science value and gains 76 minutes of margin.
- Checked every 5 m: thread, buddy, walk to the rover, radio shadows; the thread holds in 1,000 of 1,000 random scenarios.
- Picture: the route options table and the timeline.

## 5. Rehearse it, then follow it

- 3D rehearsal at walking height past Curiosity photos placed where they were taken (Courtesy NASA/JPL-Caltech).
- Visor HUD: at most four elements, white and cyan with a shape each, checked against simulated colour blindness.
- Cuff tablet with glove-sized controls that works offline; a one-page printed cuff card as the backup.
- Pictures: the visor, the tablet and the card.

## 6. May 20, 2024: the storm replay

- A far-side eruption (DONKI, 05:22 UTC); particles reached Mars in tens of minutes (JPL).
- The alert comes mid-walk; both walkers head for the rover.
- RAD: 8,100 µGy for an astronaut beside Curiosity (measured) beside modeled doses with and without the rover.
- Picture: the visor in storm mode with the replay panel.

## 7. Honest about what it knows

- The Validation tab shows every check: the shielding calibration, Mars time and light time pass; the rover-walkability check fails in the boxwork (79.8% against 95%) because the ridges sit at the map's resolution limit, so the planner stays conservative. The same pipeline built the Murray Buttes site, where it passes (99.8%).
- Next: any HiRISE terrain as a new site, a measured Mars-suit walking model, live space-weather alerts.
- Live: https://vyom-aggarwal.github.io/ARIADNE/ · Code: https://github.com/vyom-aggarwal/ARIADNE
