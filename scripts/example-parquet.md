# Full example tables

These tables provide one full dataset for both standalone and website examples.
They use Zstandard-compressed Parquet. Read them with loaders.gl's `ParquetLoader`.
Files use Git LFS; browser applications should use `media.githubusercontent.com/media/visgl/deck.gl-data/master/` URLs.

| File | Rows | Bytes | Source |
| --- | ---: | ---: | --- |
| `examples/text-layer/cities-1000.parquet` | 140,867 | 2,457,395 | `examples/text-layer/cities-1000.csv` |
| `examples/icon/meteorites.parquet` | 45,716 | 397,619 | `website/meteorites.txt` |
| `examples/data-filter/earthquakes.parquet` | 218,396 | 2,963,099 | `website/earthquakes.txt` |

Cities retain the original CSV coordinates, including negative latitudes lost in
`website/geonames.txt`. Meteorites retain all website records, including unknown
years represented by zero; their `coordinates` field is a fixed-size pair in
longitude/latitude order. Earthquakes retain the full 1979–2019 website series,
with Unix timestamps in milliseconds, depth in kilometers and magnitude unchanged.
Numeric fields use JavaScript-compatible Arrow numbers rather than int64 BigInts.

The meteorite and earthquake tables preserve the precision available in the
compact website datasets; they do not claim to recover original source precision.
No records are filtered or reordered. Existing files remain for older consumers.

## Rebuild and verify

With Python 3 and `pyarrow==21.0.0` installed:

```sh
python scripts/build-example-parquet.py
```

The script checks row counts and exact Arrow table equality after a Parquet
round trip. The source files are versioned alongside it. Source attribution is
unchanged: GeoNames (cities), The Meteoritical Society/NASA (meteorites), and
USGS (earthquakes). Dataset decoding follows deck.gl's MIT-licensed workers.
