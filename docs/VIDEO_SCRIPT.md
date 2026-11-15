# ARIADNE: 30-second demo video

The 2026 rules: 30 seconds or less, English subtitles, public link with no login, nobody under 18 in it. This storyboard follows the guide's beats (0:00 who we are, 0:02 lead-in, 0:05 title and tagline, 0:10 the idea, 0:20 to 0:30 the future) and uses only screen recordings of the app and real NASA imagery. Nothing in it is AI-generated; the end card says the software was written with AI assistance, as the SI rules ask.

The screen recordings come from `make footage` (Playwright records the live app at 1280 × 720; clips land in `footage/`). Subtitles are in [video_subtitles.srt](video_subtitles.srt); burn them in or upload them with the video.

| Time | Picture | Subtitle (English) | Source |
| --- | --- | --- | --- |
| 0:00 to 0:02 | Team name over the boxwork orthophoto from the planner map | We're [team name]. | Clip `planner` (first second) |
| 0:02 to 0:05 | Apollo 14 photograph AS14-66-09305: the lunar module with Cone Crater behind it | 1971: Apollo 14's moonwalkers turned back an estimated 50 to 75 m short of Cone Crater's rim. | NASA, https://images-assets.nasa.gov/image/as14-66-09305/as14-66-09305~large.jpg (credit: NASA). Fact: NASA, Apollo 14 Mission Details, https://www.nasa.gov/missions/apollo/apollo-14-mission-details/ |
| 0:05 to 0:10 | Title card: "ARIADNE: a thread home on Mars", over the planner map with the three routes drawn | ARIADNE: a thread home on Mars. | Clip `planner` |
| 0:10 to 0:15 | Layers switching on the map, then the three route options with the price of safety | NASA terrain, Curiosity's path and radiation data become a meter-scale walk plan. | Clip `planner` |
| 0:15 to 0:20 | 3D rehearsal at walking height past a Curiosity Navcam photo, then the visor HUD | Rehearse it in 3D past real Curiosity photos, then follow it on a four-item visor. | Clips `rehearsal`, `hud` |
| 0:20 to 0:27 | Storm replay: the alert appears, the arrow turns toward the rover, the panel shows 8,100 µGy measured beside the modeled doses | May 20, 2024: a solar storm reached Mars in tens of minutes. ARIADNE sends both walkers to the rover. | Clip `replay`. Facts: JPL, June 10, 2024; DONKI |
| 0:27 to 0:30 | End card: tagline, live link, "Data: NASA, USGS, JPL. Software written with AI assistance (Claude Code)." | Every step keeps a way home. vyom-aggarwal.github.io/ARIADNE | Title card |

## Notes for the editor

- Keep the Apollo photo's credit ("NASA") on screen while it shows, and "Courtesy NASA/JPL-Caltech" while a Curiosity photo shows.
- The storm replay's 8,100 µGy must keep its label in frame: it is the dose JPL says an astronaut beside Curiosity would have received, measured by RAD. The modeled doses keep their MODELED labels.
- Do not add NASA logos, mission patches or music you lack the rights to. Silence or a voice reading the subtitles is fine.
- Check the final length is 30 seconds or less: longer demos are not eligible for global judging.
