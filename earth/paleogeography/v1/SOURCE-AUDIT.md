# Upstream source audit checklist

**Status: PaleoDEM CSV v2 source grids included as lossless Parquet; other sources remain candidates.**

Record one entry per upstream dataset release before redistribution.

| Field | Required evidence |
| --- | --- |
| Dataset title and DOI | Permanent record identifying the exact release |
| Version and original download URL | Immutable source version or archived checksum |
| Rights holder and individual contributors | Dataset citation and embedded file notices |
| License | Explicit license covering the **specific archive and layers** |
| Third-party layers | Separate permissions for every redistributed component |
| Geometry semantics | Present-day evidence or reconstructed epoch, with source frame |
| Feature fields | Name, type, plate ID, age interval, and source-native IDs |
| Processing | Pinned converter version and complete transformation notes |
| Verification | Source/output SHA-256, row counts, geometry validity |
| STAC | Correct license, producer, snapshot time, source link, immutable asset URL |

## Release-specific findings (2026-10-20)

### PALEOMAP PaleoDEMs v2: explicit CC-BY-4.0 evidence

- Title: *PALEOMAP Paleodigital Elevation Models (PaleoDEMS) for the Phanerozoic*.
- Creators: Christopher R. Scotese and Nicky M. Wright; published 2018-08-01, v2.
- Permanent release: [DOI 10.5281/zenodo.5460860](https://doi.org/10.5281/zenodo.5460860).
- [Zenodo API record](https://zenodo.org/api/records/5460860):
  `metadata.license.id` is `cc-by-4.0`.
- Inspected archive: [PaleoDEMS_long_lat_elev_csv_v2.zip](https://zenodo.org/records/5460860/files/PaleoDEMS_long_lat_elev_csv_v2.zip).
  Publisher MD5 `17b8c13425c71b17f87a540178d45d9c` matches the downloaded archive.
- Downloaded archive SHA-256: `db43e6261411ff468c9030ca240778a73f224bf34bf8186c735477e41454c873`.
- Its root `License.txt` explicitly states that the work is licensed under the
  Creative Commons Attribution 4.0 International License, linking to
  <http://creativecommons.org/licenses/by/4.0/>. This is archive-specific evidence,
  rather than an inference from the publisher's general website.
- [EarthByte's resource page](https://www.earthbyte.org/paleodem-resource-scotese-and-wright-2018/)
  identifies the same release and its scientific description.

CC-BY-4.0 permits redistribution and adaptations, including commercial use,
with attribution, a license link, retained notices, and indication of changes.
Retain Scotese and Wright's citation, release DOI and license alongside derived
assets; the repository's MIT license does not replace the dataset license.
This finding applies to this release/archive, not every PALEOMAP product.

The archive contains reconstructed elevation/bathymetry grids (1 degree,
540–0 Ma, nominal 5 Ma sampling), not named orogen polygons. Derived contours
must record their thresholds, reconstruction frame, source ages and processing.
Do not rotate an already reconstructed grid a second time or silently combine
it with a different plate model. The numeric grid conversion is included under `paleodem/`; contour/vector derivation remains separate work.

### Macrostrat: explicit service-level CC-BY-4.0 terms

[Macrostrat's about page](https://macrostrat.org/about) explicitly licenses data
CC-BY-4.0 and requires credit to Macrostrat and original sources.
[Data-service documentation](https://macrostrat.org/docs/data-services) describes
JSON, CSV and GeoJSON exports. [Tile-server terms](https://tiles.macrostrat.org/)
require citing the source providers associated with each feature's `source_id`.

Before publishing a selected export, pin its endpoint/query and snapshot,
retain original references and response license metadata, and calculate its
checksum. Modern map units provide present-day geological evidence; their rock
ages do not make their coordinates reconstructed ancient geography.

### GPlates 2.5 GeoData: component audit still needed

The [versioned Zenodo release](https://zenodo.org/records/14194897), DOI
10.5281/zenodo.14194897 (v1, 2024-04-15), has `metadata.license.id = cc-by-4.0`
in its [API record](https://zenodo.org/api/records/14194897).
However, the [EarthByte GPlates 2.5 page](https://www.earthbyte.org/gplates-2-5-software-and-data-sets/)
states CC-BY-3.0 for EarthByte-authored data. Record both statements rather
than silently choosing a version. The compilation includes third-party
components (including GSHHG); inspect the selected layer's notices and retain
its exact license before redistribution. The GPlates software license is
separate from these dataset terms. The whole compilation is not approved by
this audit, and no component has been ingested.

## Publication boundary

The catalogue must not advertise a downloadable asset before that asset exists.
Do not infer ancient geometry by attaching present-day coordinates to an age.
License evidence enables selection and conversion; it does not establish
scientific compatibility or substitute for artifact validation.
