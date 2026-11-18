# Full GeoParquet example datasets

These files contain every feature from the corresponding website dataset, in source order:

| File | Features | Source |
| --- | ---: | --- |
| `examples/geojson/vancouver-blocks.parquet` | 4,627 | `website/vancouver-blocks.txt` |
| `examples/highway/roads.parquet` | 20,592 | `website/highway-roads.txt` |
| `examples/arc/counties.parquet` | 3,220 | `website/arc-data.txt` |

The files use GeoParquet 1.0 metadata, WKB geometry and internal Zstd compression. Coordinates retain the source precision and longitude/latitude order (the GeoParquet default CRS, OGC:CRS84). Polygon rings are closed for WKB. Original files remain available for existing consumers.

Vancouver properties are `valuePerParcel`, `valuePerSqm` and `growth`. Highway properties are `state`, `type`, `id`, `name` and `length` (miles). County properties are `name`, `centroid` and `flows`, a map from county row index to signed net migration. County row order must be preserved when resolving flows.

`examples/highway/accidents-full.csv` contains all 29,342 nonspatial accident records, with `state`, `type`, `id`, `year`, `incidents` and `fatalities`. It accompanies the full road dataset.

## Regeneration

Use Python with `pyarrow==21.0.0` and `shapely==2.0.7`, plus Node.js. Supply a deck.gl checkout at `f01ffcdbf3` (or one with identical website decoders):

```sh
python scripts/build-example-geoparquet.py /path/to/deck.gl
```

The script runs deck.gl's original MIT-licensed decoders, checks record counts, and verifies Parquet round trips. It preserves property values, coordinate precision, feature order, and reverse migration flows. Numeric properties use float64 so JavaScript receives numbers rather than BigInts.

Parquet files are stored in Git LFS. Downloads use `https://media.githubusercontent.com/media/visgl/deck.gl-data/<ref>/examples/...` to retrieve the binary contents.
