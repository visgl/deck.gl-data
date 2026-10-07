# Glaciation and climate datasets v1

Source scientific datasets, lossless Parquet representations, and separate compact
math.gl browser previews. Data retains its attributed Creative Commons license;
the repository MIT license applies only to conversion scripts.

| Dataset | Coverage | Native grid | License |
| --- | --- | --- | --- |
| Seguinot et al. (2018), Zenodo v3 | 119–0 ka, 1 ka samples | Alpine PISM, 2 km, EPSG:32632 | CC-BY-4.0 |
| Gowan et al. (2021), PaleoMIST corrected April 2021 | 80–0 ka, 2.5 ka samples | 1° global, minimal MIS 3 scenario | CC-BY-4.0 |
| Köhler et al. (2015) | 5000–0 ka temperature; albedo ends at 2 ka | Global time series | CC-BY-3.0 |

See each directory's ATTRIBUTION.md and manifest.json for source links, checksums,
licenses and exact inventory. Source NetCDF files and the climate ZIP are retained.
PaleoMIST `source.nc` is the `ice_reconstruction/global_grid/reconstruction_1_degree.nc`
member of https://hs.pangaea.de/Maps/Global_Ice_Sheets/Gowan_ice_reconstruction.zip.
Alpine source: https://zenodo.org/records/7802275/files/alpcyc.2km.epic.pp.ex.1ka.nc.
Climate source: https://epic.awi.de/39169/1/Koehler-etal_2015.zip.

## Parquet

`grids.parquet` is an ordinary Arrow table, not polygon GeoParquet. One row is one
native grid node at one source age. Each age has a separate row group, with age
statistics for range selection. `gridX` and `gridY` are zero-based source indices;
coordinates are source x/y meters and lon/lat degrees for Alpine, lon/lat degrees
for PaleoMIST. All source grid nodes, including PaleoMIST's repeated seam, remain.
Masked values are null. Thickness, bed and other fields retain their source names,
float precision and variable attributes in manifest metadata. Alpine includes both
changing bedrock and all supplied velocity and basal temperature variables.
PaleoMIST includes thickness, base/paleo topography and sea level.

Climate Parquet retains all three temperature variants and 1σ uncertainties, plus
land-ice radiative forcing and its 1σ uncertainty. Kelvin temperature *differences*
are numerically Celsius differences. Negative source time becomes positive ka BP;
values retain their published reference, with no modern baseline substitution.
Albedo forcing (W/m²) is not a planetary reflectivity fraction. Independent climate
and ice reconstructions should not be represented as one coupled simulation.

Preview gzip assets and preview manifests reproduce the math.gl app's decimated,
quantized display grids; climate.json is its subset. These are not the Parquet
representation's scientific precision. Günz, Mindel and Riss are outside the Alpine and PaleoMIST ice
grid time ranges; the climate series alone does not supply their mapped extents.
The additional Krapp masks below extend the global age range.

## Reproduce

Install scripts/requirements.txt in a separate Python environment. Pass the three
source paths to `scripts/create-parquet.py --alpine FILE --global-ice FILE
--climate FILE --out DIRECTORY`. Checksums are enforced before conversion. The
converter independently compares every written scientific column against source
arrays and checks climate Arrow round trips. ZSTD compression level is 6.

Use Git LFS to download .nc, .zip, .gz and .parquet files. Public HTTP consumers
must use GitHub's media endpoint with an immutable commit; raw endpoints can return
LFS pointers. The STAC catalog supplies pinned URLs and file checksums.

## Older global ice masks

[Krapp et al. (2021)](krapp2021/README.md) adds 800 global 0.5° ice/ocean/land mask snapshots from 799–0 ka (CC BY 4.0), unchanged NetCDF and lossless Parquet. Unlike the younger thickness grids, these masks provide no thickness or volume. They extend coverage into earlier glaciations; regional stage correlations and any interpolated animation remain interpretive.
