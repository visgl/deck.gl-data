# Data attribution and license

The EGM96 gravity model is produced by the US National Geospatial-Intelligence
Agency (NGA). The grid distributed by GeographicLib and its lossless Parquet
conversions here are **public domain**, suitable for redistribution.

License evidence, checked October 7, 2026:

- [OSGeo PROJ-data NGA attribution](https://github.com/OSGeo/PROJ-data/blob/master/us_nga/us_nga_README.txt)
  identifies the worldwide EGM96 15-minute geoid model as Public Domain.
- [GeographicLib documentation](https://geographiclib.sourceforge.io/C++/doc/geoid.html)
  identifies NGA synthesis programs as the source of its EGM96 grids and documents
  the 16-bit sample encoding.

Changes: the preview retains every fourth source row and column; both grids are
converted to Parquet node tables, with normalized longitude, decoded height,
original raw samples, and source metadata. No model values are reinterpolated.

The repository MIT license covers the conversion script, not a relicensing of
the NGA model data. NumPy and PyArrow are external conversion dependencies;
their implementations are not bundled in these dataset files.
