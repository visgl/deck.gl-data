# EGM2008 5-minute geoid grid

Full native NGA EGM2008 GeographicLib grid: 4320 × 2161 nodes at 5 arc-minute
spacing, including both poles. Model data is public domain, as documented by
OSGeo PROJ-data; this is not an assertion of CC0. See ATTRIBUTION.md.

`source.zip` retains the existing egm/egm2008-5.zip archive; `egm2008-5.pgm`
is extracted byte-for-byte. Parquet retains raw uint16 pixels and float64 geoid
heights N = -108 + 0.003 × raw_value, in meters above the WGS84 ellipsoid.
This is geoid undulation, not terrain elevation: h = H + N.

Rows run north to south; columns run east from 0°. Longitude is normalized to
[-180,180) in the node table. Pixel indices retain the source order. Each group
contains up to 120 latitude rows; rowGroupIndex records source row ranges with
exclusive rowStop. All 9,335,520 raw pixels and scaled heights are verified during
conversion. Original interpolation-error estimates remain in the PGM header.

Legacy egm/ download paths remain available. Conversion and verification:
../../../scripts/prepare-reference.py. Sources, checksums and license evidence are
in manifest.json. Scientific data is separate from MIT conversion code.
