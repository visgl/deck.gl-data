# Global country boundaries

255 country/territory features from the existing Natural Earth / DataHub repository
snapshot. Data is ODC-PDDL-1.0; see ATTRIBUTION.md and manifest.json. This is a pinned
legacy snapshot, not a claim that it matches DataHub's current dataset revision.

`source.parquet` preserves the original repository Parquet. `countries.parquet`
retains its WKB and attributes exactly, with GeoParquet 1.1.0 metadata and ZSTD
compression. Longitude/latitude degrees use implicit OGC:CRS84. `countries.geojson`
is the existing separate GeoJSON fixture; do not assume coordinate precision or
byte-for-byte equivalence between fixtures. Existing formats/* paths stay available.
Country and disputed-boundary conventions follow the source, not a new policy.

Conversion and verification: ../../../../scripts/prepare-reference.py.
