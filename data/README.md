# data/

Local cache for raw and cropped source data. Everything here except this file is gitignored, because the crops are large (several hundred MB per site) and can be rebuilt with `make fetch SITE=<site>`.

| Path | Contents |
| --- | --- |
| `sources/msl-places/localized_interp.csv` | The MSL PLACES localization table, downloaded once |
| `sources/ode/<site>_hirise_*.json` | HiRISE image and DTM footprints from the PDS Orbital Data Explorer |
| `sites/<site>/dem.tif` | 1 m DEM crop (float32, nodata −32767), Cloud Optimized GeoTIFF |
| `sites/<site>/ortho.tif` | 25 cm orthophoto crop (uint8, nodata 0) |
| `sites/<site>/color.tif` | 25 cm HiRISE color crop, where the color mosaic covers the site |
| `sites/<site>/source_class.tif` | Where the DEM comes from HiRISE stereo (1) or CTX, HRSC or MOLA (2) |
| `sites/<site>/rover_path.geojson` | Curiosity's localizations in the site's sol window |
| `sites/<site>/fetch_summary.json`, `quicklook.png` | Check results and a visual overview |

Every file has a `<file>.prov.json` provenance sidecar (source, URL, product ID, resolution, dates, pipeline version and label); GeoTIFFs also carry it in an `ARIADNE_PROVENANCE` tag. The human-readable results are committed in `docs/coverage/<site>.md`, and each fetch is listed in the fetch log at the end of `docs/SOURCES_LOG.md`.
