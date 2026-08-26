# PathStyleExtension Seattle road diagram

This directory contains the pinned City of Seattle data used by deck.gl's `PathStyleExtension`
street-design example at Dexter Avenue N and Thomas Street.

## Files

- `data/seattle-road-diagram.json` contains render-ready path and polygon assets for the example.
- `scripts` contains the reproducible extraction and validation tools.

The extractor also writes a provenance manifest and audit report next to the snapshot. Both are
ignored because they are reproducible and are not used by the example.

The runtime snapshot contains only the normalized geometry, styles, tooltip fields, and source
links consumed by deck.gl. Raw ArcGIS responses are queried and validated during extraction but are
not shipped to the website.

From the repository root, validate the checked-in snapshot with:

```bash
node examples/path-style-extension/scripts/validate-seattle-road-diagram.mjs
```

City of Seattle Department of Transportation data is used under the Public Domain Dedication and
License (PDDL) 1.0. See the extraction-script README for complete source details.
