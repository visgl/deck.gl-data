# PathStyleExtension Seattle road-diagram data

These scripts create and validate the pinned data snapshot used by the
[`PathStyleExtension` street-design example](https://github.com/visgl/deck.gl/tree/master/examples/website/path-style-extension).
The website never queries the live City of Seattle ArcGIS services.

From the repository root:

```bash
node scripts/path-style-extension/score-candidate-sites.mjs
node scripts/path-style-extension/extract-seattle-road-diagram.mjs
node scripts/path-style-extension/validate-seattle-road-diagram.mjs
```

The generated files are written to `examples/path-style-extension/data`.

The extractor pages a bounded query by sorted object ID, requests WGS84 GeoJSON, preserves every
returned source property, records the exact page URLs and hashes, and writes a machine-readable
manifest plus a human-readable audit report. It also creates two documented cartographic
derivations and one topology-repaired display representation:

- equal-width approach lane bands from Seattle Streets centerlines and nearby 12-foot `LaneWidth`
  records;
- justified crosswalk guides from in-service Marked Crosswalk points and Seattle Streets surface
  widths. The extractor records which source stripe polygons each guide replaces in the display so
  the same crosswalk is not painted twice.
- continuous pavement-symbol paths by joining CAD fragment endpoints no more than 2 millimeters
  apart. Every source coordinate is retained, and any nonzero bridge is recorded in the manifest.

Raw source geometry is preserved without simplification, manual redrawing, or snapping. The
checked-in snapshot is for demonstrating deck.gl and is not suitable for engineering,
construction, legal interpretation, or navigation.

## Sources

- [Thomas Street project](https://www.seattle.gov/transportation/projects-and-programs/programs/greenways-program/thomas-st-5th-ave-n-to-dexter-ave-n)
- [SDOT protected-intersection update](https://sdotblog.seattle.gov/2024/05/10/thomas-and-dexter-protected-intersection-update/)
- [SDOT Channelization FeatureServer](https://services.arcgis.com/ZOyb2t4B0UYuYNYH/arcgis/rest/services/SDOT_Channelization_view/FeatureServer)
- [Seattle Streets](https://catalog.data.gov/dataset/seattle-streets)
- [Sidewalks](https://catalog.data.gov/dataset/sidewalks-32d94)
- [Marked Crosswalks](https://catalog.data.gov/dataset/marked-crosswalks)
- [Existing Bike Facilities](https://catalog.data.gov/dataset/existing-bike-facilities)
- [SDOT GIS datasets and public-data terms](https://cos-data.seattle.gov/Transportation/SDOT-GIS-Datasets/jyjy-n3ap)

City of Seattle Department of Transportation data is used under the Public Domain Dedication and
License (PDDL) 1.0 and remains subject to the city's accuracy and service-availability disclaimers.
