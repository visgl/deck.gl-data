# Paleogeography GeoParquet ingestion (proposed)

This directory establishes a reproducible **conversion pipeline**, not a published
paleogeographic dataset. No third-party geometry or unverified license is bundled.
Source archives must be selected and audited separately before publishing assets.

## Candidate sources

- EarthByte / GPlates: inspect the **specific archive**, version, individual
  contributors, and license notices before redistribution. A general EarthByte
  website license is not evidence for every third-party feature collection.
- Macrostrat: inspect the API/database license and the attribution and reuse
  conditions of underlying map sources before selecting any export.
- PALEOMAP: **do not redistribute** without explicit dataset-specific permission.

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

1. Select and license-audit a named geological feature archive.
2. Pin upstream source version and reproduce conversion.
3. Check name/plate ID retention, topology, age validity, reference frame.
4. Publish immutable assets and manifests, then register STAC Items/Collections.
5. Consume verified assets from the math.gl Tectonic Time Machine.
