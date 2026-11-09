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
