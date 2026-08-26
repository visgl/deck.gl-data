# PathStyleExtension Seattle road diagram

This directory contains the pinned City of Seattle data used by deck.gl's `PathStyleExtension`
street-design example at Dexter Avenue N and Thomas Street.

## Files

- `data/seattle-road-diagram.json` contains the source features and derived display geometry.
- `data/seattle-road-diagram.manifest.json` records source services, queries, hashes,
  transformations, validation results, and licensing.
- `scripts` contains the reproducible extraction and validation tools.

The extractor also writes `data/seattle-road-diagram-report.md`, a human-readable rendering of the
manifest. It is ignored because it contains no additional information.

From the repository root, validate the checked-in snapshot with:

```bash
node examples/path-style-extension/scripts/validate-seattle-road-diagram.mjs
```

City of Seattle Department of Transportation data is used under the Public Domain Dedication and
License (PDDL) 1.0. See the manifest and extraction-script README for complete source details.
