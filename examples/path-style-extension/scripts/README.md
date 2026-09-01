# PathStyleExtension Seattle road-diagram data

These scripts create and validate the pinned data snapshot used by the
[`PathStyleExtension` street-design example](https://github.com/visgl/deck.gl/tree/master/examples/website/path-style-extension).
The website never queries the live City of Seattle ArcGIS services.

From the repository root:

```bash
node examples/path-style-extension/scripts/score-candidate-sites.mjs
node examples/path-style-extension/scripts/extract-seattle-road-diagram.mjs
node examples/path-style-extension/scripts/validate-seattle-road-diagram.mjs
```

The scripts read and write the adjacent `examples/path-style-extension/data` directory by default.

The extractor pages a bounded query by sorted object ID, requests WGS84 GeoJSON, and records the
exact page URLs and hashes in a machine-readable manifest and human-readable audit report. It
publishes a compact runtime snapshot whose path and polygon collections already contain the
geometry, dimensions, dash patterns, tooltip fields, and source links consumed by the example.

The render-ready output includes two documented cartographic derivations and one topology-repaired
display representation:

- equal-width approach lane bands from Seattle Streets centerlines and nearby 12-foot `LaneWidth`
  records;
- justified crosswalk guides from in-service Marked Crosswalk points and Seattle Streets surface
  widths. The extractor records which source stripe polygons each guide replaces in the display so
  the same crosswalk is not painted twice.
- continuous pavement-symbol paths by joining CAD fragment endpoints no more than 2 millimeters
  apart. Every source coordinate is retained, and any nonzero bridge is recorded in the manifest.

Source geometry used by the runtime assets is not simplified, manually redrawn, or snapped. Raw
source layers remain reproducible through the recorded queries but are not included in the
checked-in runtime snapshot. The snapshot is for demonstrating deck.gl and is not suitable for
engineering, construction, legal interpretation, or navigation.

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
