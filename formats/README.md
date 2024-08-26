# Attributions

| File(s)                                                                                                                | License                                     | Source                                                   | Details                                            |
| ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------- |
| **geojson**                                                                                                            |                                             |                                                          |                                                    |
| `countries.geojson`                                                                                                    | [Open Data Commons Public Domain](opendata) | https://datahub.io/core/geo-countries                    |                                                    |
| **pmtiles**                                                                                                            | BSD-3                                       | [PMTiles][PMTiles]                                       |                                                    |
| **kml**                                                                                                                | Census                                      | [census][census]                                         |                                                    |
| **geoparquet**                                                                                                         |                                             |                                                          |                                                    |
| [`nz-building-outlines.geoparquet`][geoparquet]                                                                        | [LINZ][linz]                                | [CC BY 4.0][ccby40]                                      |                                                    |
| `countries/countries_0.4.0_{brotli, gzip, snappy, no_compression}.parquet`                                             | [Open Data Commons Public Domain](opendata) | https://datahub.io/core/geo-countries                    | Converted with [Geopandas](https://geopandas.org/) |
| `countries/countries_zstd.parquet`                                                                                     | [Open Data Commons Public Domain](opendata) | https://datahub.io/core/geo-countries                    | Converted on https://geoparquet.org/convert        |
| `major-rivers/major-rivers_0.4.0_{brotli, gzip, snappy, no_compression}.parquet`                                       | Creative Commons Attribution 4.0            | https://datacatalog.worldbank.org/search/dataset/0042032 | Converted with [Geopandas](https://geopandas.org/) |
| `fort-collins-{streets, address}/fort-collins-{streets, address}_0.4.0_{brotli, gzip, snappy, no_compression}.parquet` |                                             | https://www.fcgov.com/gis/downloadable-data              | Converted with [Geopandas](https://geopandas.org/) |
| `fort-collins-{streets}/fort-collins-streets_zstd.parquet`                                                             |                                             | https://www.fcgov.com/gis/downloadable-data              | Converted on https://geoparquet.org/convert        |
| **glTF**                                                                                                               |                                             |                                                          |                                                    |
| `gltf/EXT_meshopt_compression/pirate.{glb,obj}`                                                                        | MIT                                         | [meshoptimizer][meshoptimizer]                           |                                                    |
| `gltf/KHR_texture_basisu` KTX2 Flight Helmet, Sponza by Don McCurdy                                                    |                                             | https://github.com/KhronosGroup/glTF/issues/1750         |                                                    |

[PMTiles]: https://github.com/protomaps/PMTiles/blob/main/LICENSE
[geoparquet]: ./geoparquet/nz-building-outlines.geoparquet
[linz]: https://data.linz.govt.nz/layer/101290-nz-building-outlines/
[ccby40]: https://creativecommons.org/licenses/by/4.0/
[meshoptimizer]: https://github.com/zeux/meshoptimizer/tree/master/demo
[opendata]: http://opendatacommons.org/licenses/pddl/1.0/
[census]: https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html
