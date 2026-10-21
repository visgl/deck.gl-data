# PALEOMAP PaleoDEMs v2

**Dataset license: [Creative Commons Attribution 4.0 International (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0/).**
The repository's MIT license applies to conversion code, not to these source data.

Credit: Scotese, Christopher R. and Wright, Nicky M. (2018).
*PALEOMAP Paleodigital Elevation Models (PaleoDEMs) for the Phanerozoic*, v2.
[DOI: 10.5281/zenodo.5460860](https://doi.org/10.5281/zenodo.5460860).

Source: [PaleoDEMS_long_lat_elev_csv_v2.zip](https://zenodo.org/records/5460860/files/PaleoDEMS_long_lat_elev_csv_v2.zip).
The archive's root `License.txt` is reproduced unchanged in `LICENSE.source.txt`.
The [release API](https://zenodo.org/api/records/5460860) also declares `cc-by-4.0`.

Changes by vis.gl: CSV values converted to a numeric Parquet node table with
ZSTD level 6, age columns, row-group statistics, and embedded provenance.
All 109 CSV snapshots and every original node/value are retained. No resampling,
smoothing, deduplication, contour extraction, plate rotation or datum conversion
was performed. This is not an endorsement by the original creators.

Coordinates and elevations belong to the source's reconstructed PALEOMAP grids.
They are model estimates of ancient topography and bathymetry, not measurements
or modern terrain, vegetation, or a geodetic vertical-datum grid. Do not apply
Cao/Müller plate rotations to these already reconstructed coordinates. Keep
source attribution, the DOI, license link and modification notices when reusing.
