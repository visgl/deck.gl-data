# PALEOMAP PaleoDEMs v2 — streamable Parquet

Actual reconstructed topography/bathymetry from Scotese and Wright (2018),
licensed **CC-BY-4.0**. See [attribution](ATTRIBUTION.md) and the unchanged
[source license](LICENSE.source.txt).

`paleodem.parquet` includes all **109 CSV snapshots, 0–540 Ma in 5 Ma steps**.
The one-degree source grids contain **7,095,119 nodes** in total: 59 grids
are 361 × 181 (longitude -180…180, latitude 90…-90), and 50 are
360 × 180 (longitude -180…179, latitude 90…-89). The release's general description mentions 117 models; this particular
CSV v2 archive contains 109, and no extra snapshots are invented or omitted.

| Column | Arrow type | Meaning |
| --- | --- | --- |
| `age_ma` | uint16 | Million years before present, positive into the past |
| `longitude` | float64 | Reconstructed longitude in degrees east |
| `latitude` | float64 | Reconstructed latitude in degrees north |
| `elevation_m` | float64 | Model elevation/bathymetry in meters; negative values represent ocean depth |

These are numeric raster nodes, **not GeoParquet vector geometries**. Coordinates
are the original PALEOMAP paleogeographic frame; no WGS84 datum transformation is
claimed. Elevations are source model values, not a modern geodetic height datum.
Do not apply tectonic plate rotations again.

There are **109 ZSTD level 6 row groups**, one complete age grid each (64,800 or 65,341
rows at most). `age_ma` min/max statistics enable row-group pruning. Columns can be
selected independently. Arrow/Parquet batch readers can decode and display one
snapshot before decoding subsequent row groups; this is batch decoding, not a
guarantee of HTTP range support by a particular host or reader.

Rows are sorted by increasing age, then preserve source CSV order: latitude
descending, longitude ascending (longitude varies fastest). Source-specific
endpoints and repeated polar nodes remain intact; missing edges are not filled.
A tiny near-zero latitude in the 145 Ma CSV is preserved exactly. CSV headers
and line endings vary and are handled explicitly by the converter. Source values, including any
source artifacts, are preserved without correction. No nodata mask is inferred.

The `paleodem` Parquet key/value metadata embeds citation, license, source checksum,
grid/column conventions, all source filenames, age-to-row-group indexes and
conversion details. `manifest.json` repeats these fields and records the final
file size and SHA-256. The file cannot embed its own checksum without changing it.

## Reproduce and validate

```sh
python3 -m venv /tmp/paleodem-env
/tmp/paleodem-env/bin/pip install -r ../scripts/requirements-paleodem.txt
curl -fL 'https://zenodo.org/records/5460860/files/PaleoDEMS_long_lat_elev_csv_v2.zip' -o /tmp/paleodem-v2.zip
/tmp/paleodem-env/bin/python ../scripts/paleodem.py /tmp/paleodem-v2.zip
# Independent read-back, including comparison of every node to the source CSV:
/tmp/paleodem-env/bin/python ../scripts/paleodem.py /tmp/paleodem-v2.zip --validate-only
```

Validation checks the audited archive SHA-256, source license, complete age
inventory and regular grids, exact numeric round trip, Parquet magic/schema,
ZSTD on every column chunk, row counts and age statistics, metadata/manifest
agreement, age predicate pruning and batch iteration. Peak conversion memory
is bounded to individual snapshots rather than the entire time series.

## Read a selected age

```python
import pyarrow.dataset as ds

dataset = ds.dataset('paleodem.parquet', format='parquet')
for batch in dataset.to_batches(
    columns=['longitude', 'latitude', 'elevation_m'],
    filter=ds.field('age_ma') == 300,
    batch_size=16384,
):
    consume(batch)  # application callback
```

Immutable public download URLs and the repository snapshot date are registered
in [the STAC Item](../../../stac/paleodem/snapshot.json). STAC datetime is the
repository snapshot date; `paleo:age_*_ma` fields describe geological age.
