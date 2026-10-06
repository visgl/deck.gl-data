# Tectonic reconstruction snapshots v1

Present-day geometry templates and finite rotations for the math.gl tectonic
time machine and other vis.gl examples. The files are derived from pinned scientific
datasets and are **CC-BY-4.0**, not MIT. See each model’s attribution and manifest,
and the adjacent [license text](./LICENSE.CC-BY-4.0.txt).

| Model | Source revision | Files | Total size | Ages before present | Frame |
| --- | --- | --- | ---: | --- | --- |
| [Cao et al. (2024)](https://zenodo.org/records/13628813) | 2.4 | `tectonic.parquet` | 1,580,095 bytes | 0–1800 Ma | Paleomagnetic |
| [Müller et al. (2022)](https://zenodo.org/records/13636799) | 1.2.4 | `geometry.parquet` + `rotations.parquet` | 1,912,215 bytes | 0–1000 Ma | Optimised mantle |

The three files total **3,492,310 bytes** (3.49 MB), with **ZSTD level 6** compression.
Git LFS stores the Parquet files following this repository’s `.gitattributes` policy.
The manifest records sizes, SHA-256 hashes, source archive/file hashes, schemas,
source revisions, licenses and conversion tool versions.

## Downloading

The URLs below pin the data snapshot commit
`8b95071efc14871065d800d8e430e14b4496b506`. Use GitHub’s **media** endpoint for
Parquet:

```text
https://media.githubusercontent.com/media/visgl/deck.gl-data/8b95071efc14871065d800d8e430e14b4496b506/earth/tectonic-movements/v1/cao2024/tectonic.parquet
https://media.githubusercontent.com/media/visgl/deck.gl-data/8b95071efc14871065d800d8e430e14b4496b506/earth/tectonic-movements/v1/muller2022/geometry.parquet
https://media.githubusercontent.com/media/visgl/deck.gl-data/8b95071efc14871065d800d8e430e14b4496b506/earth/tectonic-movements/v1/muller2022/rotations.parquet
```

Use `raw.githubusercontent.com/visgl/deck.gl-data/8b95071efc14871065d800d8e430e14b4496b506/...` for manifests and
attribution. Raw URLs for LFS-backed Parquet may return a small LFS pointer instead
of the data. With Git, install Git LFS and run `git lfs pull` with an include filter
for `earth/tectonic-movements/v1/**/*.parquet`.

## Data conventions

Geometry records are GeoParquet 1.1.0, containing WKB Polygon geometry in
longitude/latitude degrees (implicit OGC:CRS84) with spherical edges. Each row has
`featureId`, `polygonIndex`, `plateId`, `name`, `beginAge`, `endAge` and `geometry`.
Source vertices and holes are retained; ring closure is added when absent. Source
winding is retained without an orientation assertion. These are unreconstructed
present-day templates, not reconstructed paleoshorelines or evolving plate topology.

Rotation records contain `age`, `plateId`, `available`, `w`, `x`, `y` and `z`.
Ages are millions of years before present, sampled every 10 Ma. Quaternions use
w,x,y,z order with anchor plate 0, and Cartesian X at lon=0/lat=0, Y at lon=90/lat=0,
Z at the North Pole. Keep each model’s geometry, rotations and reference frame paired.
A missing rotation has `available=false` and null quaternion components; it is never
replaced with an identity rotation. Filter geometry by its valid age range and
handle unavailable rotations explicitly. Interpolate between sampled rotations for
playback; no future reconstruction scenarios are included.

Cao’s `tectonic.parquet` is a tagged table: `recordType` is `geometry` or `rotation`.
Both record types share `plateId`. Geometry fields are null on rotation rows; rotation
fields are null on geometry rows. The `geometry` column is nullable WKB. Templates
are stored once, without duplicating them for each age. Its first row group contains
all 877 geometry records; the following 18 groups contain rotations. Müller retains
separate files, with ten geometry groups and ten rotation groups.

Rotation groups cover **100 Ma windows**, sorted youngest first. Windows are
half-open, for example 0–90 and 100–190 Ma at 10 Ma sampling. The final window
also includes the model’s final endpoint (1700–1800 Ma for Cao, 900–1000 for Müller).
All plates for an age stay together. Cao’s two source rotation files are complementary
0–1000 and 1000–1800 Ma time slices, combined into this one snapshot. Müller uses
only `optimisation/1000_0_rotfile_MantleOpt.rot`; its paleomagnetic file covers the
same interval in an alternative frame and must not be merged with it.

Each file’s footer contains a JSON `math.gl.tectonic.rowGroups` index with
`rowGroup`, `recordType`, `rows`, `minAge` and `maxAge`. The same index appears in
the manifest, so consumers can choose groups before fetching the footer. Geometry
ranges are null. Parquet column statistics also include rotation age min/max and,
for Cao, record type. Readers can skip unwanted age windows and decode only needed
columns. HTTP range access requires support from both the reader and the host;
row groups alone do not make an HTTP client stream ranges automatically.

For example, select Cao’s 500–590 Ma window from the manifest, then decode it in
batches without reading names or geometry:

```python
import json
import pyarrow.parquet as pq

manifest = json.load(open('cao2024/manifest.json'))
file = manifest['files'][0]
groups = [entry['rowGroup'] for entry in file['rowGroupIndex']
          if entry['recordType'] == 'rotation'
          and entry['minAge'] <= 550 <= entry['maxAge']]
parquet = pq.ParquetFile('cao2024/tectonic.parquet')
for batch in parquet.iter_batches(row_groups=groups, batch_size=4096,
        columns=['age', 'plateId', 'available', 'w', 'x', 'y', 'z']):
    # Process each Arrow batch; apply an exact-age filter if needed.
    pass
```

Compression alone is not a browser-startup benchmark; measure transfer, decoding
and first usable pose.

## Reproducing and validating

The original MIT conversion and validation scripts are in [scripts](./scripts/).
Use a separate environment. pyGPlates is an external GPL-2.0 offline tool; no
GPlates implementation or runtime dependency is included in these assets or the
browser application. The converted scientific data retains CC-BY-4.0.

From this directory:

```sh
python -m venv /tmp/tectonic-converter
/tmp/tectonic-converter/bin/pip install -r scripts/requirements.txt
curl --fail --location https://zenodo.org/api/records/13628813/files/1.8Ga_model_GSF.zip/content -o /tmp/cao2024-v2.4.zip
curl --fail --location https://zenodo.org/api/records/13636799/files/Muller_etal_2022_SE_v1.2.4.zip/content -o /tmp/muller2022-v1.2.4.zip
/tmp/tectonic-converter/bin/python scripts/create-parquet.py --cao /tmp/cao2024-v2.4.zip --muller /tmp/muller2022-v1.2.4.zip --out /tmp/tectonic-parquet-regenerated
/tmp/tectonic-converter/bin/python scripts/validate-parquet.py --root /tmp/tectonic-parquet-regenerated
/tmp/tectonic-converter/bin/python scripts/validate-parquet.py
/tmp/tectonic-converter/bin/python scripts/validate-source-rotations.py --cao /tmp/cao2024-v2.4.zip --muller /tmp/muller2022-v1.2.4.zip
```

Validation reads every file and checks checksums, schemas, actual column compression,
GeoParquet metadata, polygon coordinates/rings, age statistics, complete plate sets,
unit quaternions, streaming column reads, indexed 100 Ma windows and missing-value
conventions. The independent source validator checks every rotation sample against
explicitly selected canonical source files without importing the converter configuration. Conversion additionally checks full
Arrow/Parquet round trips and reconstructed test points against pyGPlates. Compression
level is recorded by the converter; the Parquet footer reports the codec, not its level.
