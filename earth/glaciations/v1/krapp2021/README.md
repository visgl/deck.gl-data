# Krapp et al. (2021) global ice masks

800 global 0.5° snapshots, 799–0 ka before present, from [Terrestrial climate of the last 800,000 years](https://osf.io/8n43x/). Data are **CC BY 4.0**; see [attribution](ATTRIBUTION.md) and [license evidence](license-evidence.json).

- `source.nc`: unchanged upstream `icesheets_000-800_cru.nc`, OSF file version 1.
- `grids.parquet`: lossless tabular conversion of all 207,360,000 cells, 800 row groups in source time order (799 ka first, present last).
- `manifest.json`: source hash, dimensions, native variable/global attributes, conversion details and asset checksums.

Each row has `gridX`, `gridY` (zero-based source indices), `longitude`, `latitude` (original float32 cell centers), `ageKa` (positive ka before present), `sourceTimeYears` (original float64 time), and original int16 `land_max` and `mask`. Mask classes are 0 ocean, 1 land, 2 ice. `land_max` retains the separate upstream maximum land extent variable. All cells are included, without interpolation, simplification or quantization. Arrow schema metadata retains native attributes, including the source time units `years since 0000-01-01` and `360_day` calendar. Coordinates are longitude −179.75…179.75 and latitude −89.75…89.75.

The masks are reconstructions, combining ICE-6G for 0–122 ka, Ganopolski & Calov (2011) for 123–799 ka, and Spratt & Lisiecki (2016) sea level (as recorded in the NetCDF history). They contain no ice thickness or volume. Older coverage enables earlier ice-age visualizations, but does not establish exact boundaries or dates for the regional Günz, Mindel and Riss terminology. Any interpolated animation should be identified as interpolation.

## Reproduce

From the repository root, install `earth/glaciations/v1/scripts/requirements.txt`, then run:

```sh
python earth/glaciations/v1/scripts/create-krapp-parquet.py \
  --source earth/glaciations/v1/krapp2021/source.nc \
  --out earth/glaciations/v1/krapp2021
```

Fetch Git LFS assets first. The converter rejects a source with a different SHA-256. Use immutable `media.githubusercontent.com/media/visgl/deck.gl-data/<commit>/earth/glaciations/v1/krapp2021/` URLs for binary downloads; raw GitHub URLs can return LFS pointers. This is ordinary tabular Parquet, not polygon GeoParquet.
