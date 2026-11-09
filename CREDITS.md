# Credits

Everything ARIADNE uses that we did not make, with its license or credit line. Each item is added when it is first used (CLAUDE.md rule 4). Only openly licensed or public-domain material is used (rule 13).

ARIADNE's own code is licensed under [Apache-2.0](LICENSE).

## Data

Sources move here, with their credit lines, when the pipeline first uses them. What was checked about each is in [docs/SOURCES_LOG.md](docs/SOURCES_LOG.md).

| Data | Use | Source and credit | License or terms |
| --- | --- | --- | --- |
| IERS leap-second table (`Leap_Second.dat`, through Bulletin C 72) | TT − UTC for Mars time; bundled verbatim in `pipeline/ariadne/models/data/` | International Earth Rotation and Reference Systems Service (IERS), https://hpiers.obspm.fr/iers/bul/bulc/Leap_Second.dat | Public reference data, credited to IERS; the file states no license |
| Mars24 algorithm and worked examples | Mars solar time and sun position (`pipeline/ariadne/models/mars24.py`) and its tests | NASA Goddard Institute for Space Studies, Mars24 Sunclock, https://www.giss.nasa.gov/tools/mars24/help/algorithm.html; Allison and McEwen (2000), Planet. Space Sci. 48, 215-235 | US government work (NASA) |
| MSL mission-clock definition | Sol 0 and the 137.42° E mission clock | Mars24 notes, https://www.giss.nasa.gov/tools/mars24/help/notes.html | US government work (NASA) |
| MSL LMST clock kernel `msl_lmst_ops120808_v1.tsc` | Touchdown time; independent check of sol starts in tests | NASA/JPL NAIF, https://naif.jpl.nasa.gov/pub/naif/MSL/kernels/sclk/ | NASA public data |
| MSL REMS daily report feed, 93-sol sample | Test cross-check only (dates and Ls), never app data | NASA/JPL-Caltech/CAB (CSIC-INTA), https://mars.nasa.gov/rss/api/?feed=weather&category=msl&feedtype=json | Provider marks it for outreach purposes only |
| MSL Gale Merged DEM 1 m (v3) | Elevation crops for each site (`data/sites/<site>/dem.tif`) | USGS Astrogeology (Parker and Calef III), https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m; built from HiRISE (NASA/JPL-Caltech/University of Arizona), CTX (NASA/JPL-Caltech/MSSS) and HRSC (ESA/DLR/FU Berlin) stereo, tied to MOLA | US government work (USGS), public domain; credit the authors |
| MSL Gale Merged Orthophoto Mosaic 25 cm (v3) | Image crops for each site (`ortho.tif`) | USGS Astrogeology, https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm; HiRISE images NASA/JPL-Caltech/University of Arizona | US government work (USGS), public domain |
| MSL Gale HiRISE LRGB color mosaic | Color crop for the boxwork (`color.tif`; it does not cover Murray Buttes) | USGS Astrogeology; HiRISE images NASA/JPL-Caltech/University of Arizona | US government work (USGS), public domain |
| MSL PLACES localizations (`localized_interp.csv`) | Curiosity's positions: site boxes, the rover path, the georeferencing check; a 3,781-row extract is a test fixture | NASA/JPL-Caltech, PDS Cartography and Imaging Sciences Node, https://planetarydata.jpl.nasa.gov/img/data/msl/msl_places/ | NASA PDS archive data, public domain |
| HiRISE image and DTM footprints | DEM source-class mask and coverage report | PDS Geosciences Node Orbital Data Explorer (Washington University in St. Louis), https://oderest.rsl.wustl.edu/; HiRISE NASA/JPL-Caltech/University of Arizona | NASA PDS archive metadata, public domain |
| USGS list of the 12 HiRISE stereo pairs in the merged DEM | Which images count as HiRISE stereo | USGS Astrogeology product page for the merged DEM | US government work (USGS), public domain |
| MGS MOLA DEM 463 m (MEGDR), global mosaic | Far-field horizons from 2 km to 100 km (`regional_dem.tif`, the site box plus 102 km) | MOLA Science Team (NASA/GSFC); mosaic by USGS Astrogeology, https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m | CC0 (public domain), per the USGS product page |
| THEMIS night IR controlled mosaic 100 m (v2, Oct 2018) | Relative sand proxy at the boxwork (`themis_night_ir.tif`) | THEMIS, NASA/JPL-Caltech/Arizona State University; tiles from NASA Mars Trek, https://trek.nasa.gov/ | NASA data, public domain |
| MSL ChemCam LIBS oxide tables (MOC), sols 4489 to 4843 | Curiosity's prior targets for the science novelty score (`chemcam_targets.csv`) | NASA/JPL-Caltech/LANL/IRAP, MSL ChemCam team; PDS Geosciences Node, https://pds-geosciences.wustl.edu/msl/msl-m-chemcam-libs-4_5-rdr-v1/ | NASA PDS archive data, public domain |
| NASA Curiosity blog posts, sols 4563 to 4803 | Sols of the four boxwork drill holes (Altadena, Valle de la Luna, Nevado Sajama, Nevado Sajama2) | NASA/JPL-Caltech, Mars Science Laboratory mission team, https://science.nasa.gov/blog/ (posts listed in docs/SOURCES_LOG.md) | US government work (NASA) |
| NASA NSSDCA Mars Fact Sheet | Atmospheric scale height (11.0 km), surface gravity (3.69 m/s²) and flattening (0.00589) | NASA Goddard Space Flight Center, https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html | US government work (NASA) |

## Published values used in models

| Value | Use | Source | License |
| --- | --- | --- | --- |
| Murray Buttes dose drop (3.8% ± 0.4%), baseline sols 1440 to 1455 and 1468 to 1480, parked sols 1456 to 1467, 19% blocked sky, 7.5% neutral drop, 23 g/cm² column | Shielding calibration and its checks | Ehresmann, B., Hassler, D. M., Zeitlin, C., Guo, J., Wimmer-Schweingruber, R. F., Khaksari, S. and Loeffler, S. (2021), Natural Radiation Shielding on Mars Measured With the MSL/RAD Instrument, JGR Planets 126, e2021JE006851, https://doi.org/10.1029/2021JE006851 | Values cited, no text reused; free to read on Wiley |
| Dose-pressure coefficient κ (upper limit 0.21 µGy/day per Pa) and the matching mean dose (about 300 µGy/day) | The pressure factor f(p) | Guo, J. et al. (2021), Radiation environment for future human exploration on the surface of Mars, Astron. Astrophys. Rev. 29:8, https://doi.org/10.1007/s00159-021-00136-5 | CC BY 4.0; values cited |
| Curiosity's size: 10 ft long, 9 ft wide, 7 ft tall, not counting the arm | The rover's footprint for slope (3.05 m) | NASA Science, Mars Science Laboratory: Curiosity Rover, https://science.nasa.gov/mission/msl-curiosity/ | NASA public information; value cited |
| DTM posts at about 4 image pixels; HiRISE DTM artifacts (boxes, CCD seams) | The DEM's resolution and seams | HiRISE team (University of Arizona), Overview of Digital Terrain Models, https://www.uahirise.org/dtm/about.php | Values cited, no text reused |
| HiRISE DTM grid of 1 m (3–4 image pixels) | The DEM's resolution | Kirk, R. L. et al. (2008), Ultrahigh resolution topographic mapping of Mars with MRO HiRISE stereo images: Meter-scale slopes of candidate Phoenix landing sites, JGR, https://doi.org/10.1029/2007JE003000 | Abstract cited |
| Stereo DTM resolution of 10 to 20 image pixels (USGS products at the finer end); blocky DTMs overstate slopes; vertical discontinuities in the Gale HiRISE mosaic | The slope scale (r_eff = 2.5 m) and the seam map | Kirk, R. L. et al. (2021), Further adventures in Mars DTM quality: smoothing errors, sharpening details, ISPRS Archives XLIII-B3-2021, 659–666, https://doi.org/10.5194/isprs-archives-XLIII-B3-2021-659-2021 | CC BY 4.0; values cited |

## Images

None used yet. No AI-generated images are used, and no NASA logos, flags, insignia or mission patches appear as graphics.

## Text

| Item | Source | License |
| --- | --- | --- |
| Apache License 2.0 text in [LICENSE](LICENSE) | https://www.apache.org/licenses/LICENSE-2.0.txt | Published by the Apache Software Foundation for use as a license |

## Software: pipeline (Python)

Versions confirmed on Python 3.13 on 2026-11-08; `pipeline/pyproject.toml` sets minimum versions.

| Package | Use | License | Link |
| --- | --- | --- | --- |
| NumPy | Arrays and math | BSD-3-Clause (bundled parts: 0BSD, MIT, Zlib, CC0-1.0) | https://numpy.org |
| SciPy | Filters, interpolation, optimization | BSD-3-Clause | https://scipy.org |
| scikit-image | Image and terrain processing | BSD-3-Clause | https://scikit-image.org |
| rasterio | Reading and writing GeoTIFFs | BSD-3-Clause; its wheels bundle GDAL (MIT) | https://rasterio.readthedocs.io |
| pyproj | Map projections | MIT; its wheels bundle PROJ (MIT) | https://pyproj4.github.io/pyproj |
| shapely | Geometry | BSD-3-Clause; its wheels bundle GEOS (LGPL-2.1) | https://shapely.readthedocs.io |
| numba | Fast compiled loops | BSD-2-Clause | https://numba.pydata.org |
| llvmlite | Compiler backend for numba | BSD-2-Clause and Apache-2.0 with LLVM exception | https://llvmlite.readthedocs.io |
| Google OR-Tools | Reference route and station planning | Apache-2.0 | https://developers.google.com/optimization |
| astroquery | JPL Horizons ephemerides | BSD-3-Clause | https://astroquery.readthedocs.io |
| pandas | Tables | BSD-3-Clause | https://pandas.pydata.org |
| PyYAML | Site config files | MIT | https://pyyaml.org |
| pytest | Tests | MIT | https://pytest.org |
| Ruff | Linting | MIT | https://docs.astral.sh/ruff |

## Software: web app (JavaScript and TypeScript)

Exact versions are in `web/package-lock.json`. `npm run licenses` checks every package in it (138 on 2026-11-08) against the allowed list of open licenses.

| Package | Use | License | Link |
| --- | --- | --- | --- |
| React and React DOM | User interface | MIT | https://react.dev |
| Vite and @vitejs/plugin-react | Build and dev server | MIT | https://vite.dev |
| TypeScript | Type checking | Apache-2.0 | https://www.typescriptlang.org |
| Vitest | Unit tests | MIT | https://vitest.dev |
| jsdom | Browser environment for unit tests | MIT | https://github.com/jsdom/jsdom |
| Testing Library (DOM and React) | Component tests | MIT | https://testing-library.com |
| Playwright | Browser tests | Apache-2.0 | https://playwright.dev |
| axe-core and @axe-core/playwright | Accessibility checks | MPL-2.0 | https://github.com/dequelabs/axe-core |
| DefinitelyTyped type packages (@types/node, @types/react, @types/react-dom) | Type definitions | MIT | https://github.com/DefinitelyTyped/DefinitelyTyped |

## Build and hosting

| Item | Use | License or terms | Link |
| --- | --- | --- | --- |
| GitHub Actions: checkout, setup-python, setup-node, configure-pages, upload-pages-artifact, deploy-pages | CI and deployment | MIT | https://github.com/actions |
| GitHub Pages | Hosting the static site | GitHub terms of service | https://pages.github.com |
