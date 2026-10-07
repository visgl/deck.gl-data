# Major rivers of the world

98 river features from the repository's World Bank snapshot, retained under
CC-BY-4.0. See ATTRIBUTION.md and manifest.json for source and license evidence.

`source.parquet` retains the legacy GZIP GeoParquet 0.4.0 file. The new
`major-rivers.parquet` preserves every WKB and attribute, upgrades metadata to
GeoParquet 1.1.0, and uses ZSTD level 6. Source WGS84 CRS metadata is retained;
geometry coordinates remain longitude/latitude. These are selected major rivers,
not a complete hydrographic network or a map of seasonal discharge.

Legacy formats/geoparquet paths remain available. Conversion and verification:
../../../../scripts/prepare-reference.py.
