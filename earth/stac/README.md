# vis.gl Earth STAC catalog

Open [catalog.json](catalog.json) to discover the Earth datasets using a static
[STAC 1.1.0](https://github.com/radiantearth/stac-spec/tree/v1.1.0) catalog.
It contains eleven Collections and twelve Items:

- **Earth reference datasets**: EGM2008 geoid, countries and major rivers, with original and converted assets.
- **EGM96**: one Item per grid resolution, each with PGM and Parquet assets.
- **Cao 2024**: one Item with the combined geometry/rotation Parquet snapshot.
- **Glaciations and climate**: Alpine PISM, PaleoMIST, Krapp 2021 and Köhler 2015; each has a snapshot Item with source files and lossless Parquet. Alpine, PaleoMIST and Köhler additionally provide separate display previews. Krapp provides 799–0 ka global ice/ocean/land masks.
- **PALEOMAP PaleoDEMs v2**: one Item with 109 CC-BY-4.0 reconstructed elevation grids in age-filterable Parquet, plus manifest, attribution and original license.
- **Müller 2022**: one Item pairing geometry and rotation Parquet assets.

Collection and Item links are relative, so the catalog can be browsed locally or
served as static JSON. The catalog provides discovery, not a STAC API search
endpoint. Full-world footprints describe global model coverage; they do not claim
that tectonic geometry covers every point on Earth.

## Downloads and provenance

Data asset URLs use GitHub's LFS media endpoint and immutable commit IDs. Manifest
and attribution assets use the raw endpoint at the same commit. Each data asset
declares its MIME type, size, and SHA-256 multihash through the
[File Info extension](https://github.com/stac-extensions/file/tree/v2.1.0).
Detailed schemas, source provenance, conversion notes, and grid conventions remain
in the linked manifests and attribution files.

The EGM96 snapshot is pinned to the uploaded files in
[dataset PR #46](https://github.com/visgl/deck.gl-data/pull/46); the catalog does not
require those files to be merged into master first. Tectonic assets are pinned to
the master snapshot that merged dataset PR #45. Glaciation assets are pinned to the dataset commit in this PR.

## Licenses and time conventions

EGM96 model data are public domain. Its Collection uses `license: "other"` with
an explicit public-domain license-evidence link; it does not claim CC0. Tectonic
Collections retain `CC-BY-4.0` and link source attribution. Repository MIT licensing
applies to the catalog tooling; it does not replace dataset licenses.

STAC `datetime` identifies the **repository dataset snapshot commit time** in UTC,
not observation/acquisition time, model epoch, or geologic age. Collection temporal
extents reflect those snapshot dates. This convention is explicit on every Item.
Tectonic age coverage and sampling are separate `tectonic:*` properties in millions
of years before present; geological times are not forced into Gregorian dates.
`geoid:*` and `tectonic:*` properties are documented custom fields, not claims of
compliance with additional STAC extensions. Glaciation `paleo:age_min_ka`, `paleo:age_max_ka` and `paleo:age_unit` use thousands of years before present. Alpine, PaleoMIST and Krapp data retain CC-BY-4.0; Köhler climate data retains CC-BY-3.0.

## Regeneration and validation

Run from this directory with Python 3.9 or newer:

```sh
python3 scripts/generate.py
python3 -m pip install -r scripts/requirements.txt
python3 scripts/validate.py --downloads
```

Generation reads immutable manifests specified in the generator. Validation checks
core and File Info extension schemas, reciprocal catalog links, unique IDs, all
discoverable Items, and every public asset's availability. Data downloads must
match both the declared size/checksum and their source manifest. Internet access is
required for source manifests, schema resolution, and download checks. Omit
`--downloads` to skip downloading dataset assets.

PaleoDEM `paleo:age_min_ma`, `paleo:age_max_ma`, `paleo:age_step_ma` and
`paleo:age_unit` use millions of years before present; `paleo:age_count`,
`paleo:row_groups` and `paleo:node_count` describe the Parquet snapshot.
`paleo:coordinate_frame` identifies already reconstructed source coordinates.
These are custom properties, not a claim of a separate STAC extension.
Per-age grid dimensions, units, row-group indexes and source filenames are
available in the embedded Parquet metadata and manifest. PaleoDEM assets are
pinned to their uploaded dataset commit independently of the STAC registration.

To validate all catalog documents while downloading only the PaleoDEM assets:

```sh
python3 scripts/validate.py --downloads --collection visgl-paleodem
```
