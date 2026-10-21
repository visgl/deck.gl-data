# Paleogeography GeoParquet ingestion (proposed)

This directory contains the licensed [PALEOMAP PaleoDEMs v2 dataset](paleodem/),
with all 109 source CSV age grids converted losslessly to ZSTD Parquet, plus a
reproducible conversion pipeline for separately audited vector sources.

## Licensed source candidates

The [source audit](SOURCE-AUDIT.md) records release-specific evidence checked on
2026-10-20. PALEOMAP PaleoDEMs v2 has an explicit **CC-BY-4.0** license in both
its Zenodo release metadata and downloaded CSV archive. Macrostrat also states
CC-BY-4.0 with attribution to Macrostrat and original providers. These findings
replace the earlier blanket permission restriction on PALEOMAP.

PaleoDEMs are elevation grids, not named vector geological features. Converting
them requires a raster/contour preparation step before this GeoJSON converter.
GPlates GeoData contains multiple components whose notices require separate
inspection. Only the audited PaleoDEM CSV release is included here.

## Conversion

Install `geopandas`, `pyarrow` and `shapely` in a Python environment.
Use an explicitly licensed, vetted source GeoJSON with EPSG:4326 coordinates:

```sh
python3 scripts/convert.py input.geojson output.parquet \
  --manifest output.manifest.json \
  --citation 'Publication and dataset DOI / version' \
  --license 'CC-BY-4.0' \
  --model 'source-model-and-frame' \
  --coordinate-epoch 'Ma:300'
```

`--coordinate-epoch present` is for modern geological evidence. A reconstruction
epoch does not imply a plate rotation has been performed. Never assign an epoch
to modern geometry without actually reconstructing it.

The converter checks the source CRS and geometries, writes WKB GeoParquet
with ZSTD compression, and records source and output SHA-256 digests.
The metadata manifest is a conversion record, **not proof of legal permission**.
Upstream provenance and attribution must be independently reviewed.

## STAC publication gate

Do not create an Item with downloadable data asset URLs until the converted
GeoParquet exists at an immutable URL and has a verified size/checksum.
The corresponding STAC Collection must include the actual source license,
producers, citation, coordinate reference frame, reconstruction model, and
separate geological-age metadata. STAC datetime is the repository snapshot
time, not geological age. Add a Collection to `earth/stac/catalog.json` only
once it has at least one validated, hosted Item. Follow existing STAC
generation/validation workflows rather than hand-maintaining divergent files.

## Future work

1. Select and license-audit a named vector geological feature archive.
2. Pin upstream source version and reproduce conversion.
3. Check name/plate ID retention, topology, age validity, reference frame.
4. Publish immutable assets and manifests, then register STAC Items/Collections.
5. Consume verified assets from the math.gl Tectonic Time Machine.

## Local publication preflight

After converting an approved source archive, verify the manifest against
the actual artifact before proposing a STAC Item:

```sh
python3 scripts/validate_manifest.py output.manifest.json --artifact output.parquet
python3 -m unittest discover -s scripts -p 'test_*.py'
```

The preflight verifies the file's byte size and SHA-256, required provenance
fields, GeoParquet CRS, and feature count. This does not establish that
third-party redistribution rights have been secured, or that the asset is
already hosted at a stable URL.
