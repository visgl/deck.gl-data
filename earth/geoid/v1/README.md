# EGM96 geoid node tables

Lossless Parquet conversions of the optional math.gl EGM96 grids. Model data are
**public domain (NGA)**; conversion code is MIT licensed. Heights are geoid
undulation N in meters relative to WGS84: ellipsoidal h = orthometric H + N.
This is not terrain elevation.

| File | Grid | Nodes | Purpose |
| --- | --- | ---: | --- |
| `geoid-egm96-low.parquet` | 360 × 181, 1° | 65,160 | Visualization preview |
| `geoid-egm96-hi.parquet` | 1440 × 721, 15′ | 1,038,240 | Original grid nodes |

The preview samples every fourth row and column of the original; it does not
retain the original interpolation error bounds. Neither table performs
interpolation. math.gl's `parsePGM` continues to use the packaged PGM grids.

## Schema

| Column | Arrow type | Meaning |
| --- | --- | --- |
| `row` | int32 | Zero-based PGM row, north to south |
| `column` | int32 | Zero-based PGM column, east from Greenwich |
| `longitude` | float64 | Degrees east, normalized to [-180, 180) |
| `latitude` | float64 | Degrees north; both poles included |
| `geoid_height` | float64 | N = −108 + 0.003 × raw_value, meters |
| `raw_value` | uint16 | Exact original PGM sample |

Rows retain PGM order. Pole coordinates repeat for every longitude, as in the
original grid. Files use Zstandard compression and row groups of 32 grid rows.
The `geoid` schema metadata makes each file self-describing. `manifest.json`
also records dimensions, source hashes, artifact hashes, and sizes.

## Provenance and regeneration

Source: [GeographicLib EGM96 15′ archive](https://downloads.sourceforge.net/project/geographiclib/geoids-distrib/egm96-15.tar.bz2).
See [GeographicLib geoid documentation](https://geographiclib.sourceforge.io/C++/doc/geoid.html)
and [PROJ's NGA public-domain attribution](https://github.com/OSGeo/PROJ-data/blob/master/us_nga/us_nga_README.txt).
Source and PGM SHA-256 checksums are pinned in `scripts/source-manifest.json`.

From a math.gl checkout containing `modules/geoid/data`:

```sh
python3 -m pip install -r scripts/requirements.txt
python3 scripts/generate-parquet.py --source /path/to/math.gl/modules/geoid/data --output .
```

The converter checks both PGM hashes, verifies every column after writing and
reading each file, and reconstructs the original pixel bytes exactly.

For public downloads of Git LFS files, use `media.githubusercontent.com`, e.g.
`https://media.githubusercontent.com/media/visgl/deck.gl-data/master/earth/geoid/v1/geoid-egm96-hi.parquet`
after this dataset has been merged into master.
