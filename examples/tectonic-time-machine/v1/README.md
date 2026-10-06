# Tectonic reconstruction snapshots v1

Paired present-day geometry templates and finite rotations for the math.gl tectonic
time machine and other vis.gl examples. The files are derived from pinned scientific
datasets and are **CC-BY-4.0**, not MIT. See each model’s attribution and manifest,
and the adjacent [license text](./LICENSE.CC-BY-4.0.txt).

| Model | Source revision | Geometry | Rotations | Ages before present | Frame |
| --- | --- | ---: | ---: | --- | --- |
| [Cao et al. (2024)](https://zenodo.org/records/13628813) | 2.4 | 904,504 bytes | 1,220,467 bytes | 0–1800 Ma | Paleomagnetic |
| [Müller et al. (2022)](https://zenodo.org/records/13636799) | 1.2.4 | 1,364,087 bytes | 774,806 bytes | 0–1000 Ma | Optimised mantle |

The four files total **4,263,864 bytes** (4.26 MB), with **ZSTD level 6** compression.
Git LFS stores the Parquet files following this repository’s `.gitattributes` policy.
The manifest records sizes, SHA-256 hashes, source archive/file hashes, schemas,
source revisions, licenses and conversion tool versions.

## Downloading

Use an immutable repository commit and GitHub’s **media** endpoint for Parquet:

```text
https://media.githubusercontent.com/media/visgl/deck.gl-data/<COMMIT_SHA>/examples/tectonic-time-machine/v1/cao2024/geometry.parquet
https://media.githubusercontent.com/media/visgl/deck.gl-data/<COMMIT_SHA>/examples/tectonic-time-machine/v1/cao2024/rotations.parquet
https://media.githubusercontent.com/media/visgl/deck.gl-data/<COMMIT_SHA>/examples/tectonic-time-machine/v1/muller2022/geometry.parquet
https://media.githubusercontent.com/media/visgl/deck.gl-data/<COMMIT_SHA>/examples/tectonic-time-machine/v1/muller2022/rotations.parquet
```

Use `raw.githubusercontent.com/visgl/deck.gl-data/<COMMIT_SHA>/...` for manifests and
attribution. Raw URLs for LFS-backed Parquet may return a small LFS pointer instead
of the data. With Git, install Git LFS and run `git lfs pull` with an include filter
for `examples/tectonic-time-machine/v1/**/*.parquet`.

## Data conventions

`geometry.parquet` is GeoParquet 1.1.0, containing WKB Polygon geometry in
longitude/latitude degrees (implicit OGC:CRS84) with spherical edges. Each row has
`featureId`, `polygonIndex`, `plateId`, `name`, `beginAge`, `endAge` and `geometry`.
Source vertices and holes are retained; ring closure is added when absent. Source
winding is retained without an orientation assertion. These are unreconstructed
present-day templates, not reconstructed paleoshorelines or evolving plate topology.

`rotations.parquet` contains `age`, `plateId`, `available`, `w`, `x`, `y` and `z`.
Ages are millions of years before present, sampled every 10 Ma. Quaternions use
w,x,y,z order with anchor plate 0, and Cartesian X at lon=0/lat=0, Y at lon=90/lat=0,
Z at the North Pole. Keep each model’s geometry, rotations and reference frame paired.
A missing rotation has `available=false` and null quaternion components; it is never
replaced with an identity rotation. Filter geometry by its valid age range and
handle unavailable rotations explicitly. Interpolate between sampled rotations for
playback; no future reconstruction scenarios are included.

One rotation age occupies one row group, with min/max age statistics. Readers can
omit unused columns and skip age groups when they support statistics and the host
supports HTTP range requests. Full-file requests also work. Compression alone is
not a browser-startup benchmark; measure transfer, decoding and first usable pose.

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
```

Validation reads every file and checks checksums, schemas, actual column compression,
GeoParquet metadata, polygon coordinates/rings, age statistics, complete plate sets,
unit quaternions and missing-value conventions. Conversion additionally checks full
Arrow/Parquet round trips and reconstructed test points against pyGPlates. Compression
level is recorded by the converter; the Parquet footer reports the codec, not its level.
