# Credits

Everything ARIADNE uses that we did not make, with its license or credit line. Each item is added when it is first used (CLAUDE.md rule 4). Only openly licensed or public-domain material is used (rule 13).

ARIADNE's own code is licensed under [Apache-2.0](LICENSE).

## Data

None used yet. The sources checked for the first phases, and what was confirmed about each, are in [docs/SOURCES_LOG.md](docs/SOURCES_LOG.md). Each one moves here, with its credit line, when the pipeline first uses it.

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
