# Oceanography datasets v1

Source scientific datasets, lossless Parquet representations and separate compact
browser previews for the `@math.gl/earth/ocean` functions and examples. Data keep
their own license terms; the repository MIT license applies only to the scripts.

| Dataset | Coverage | Native grid | License |
| --- | --- | --- | --- |
| NOAA NCEI World Ocean Atlas 2023, annual `decav` | 1955–2022 climatology, 0–5500 m | 1° global, 102 standard depths | Public, no named license (`other`) |

## WOA23 temperature and salinity

Sources (NCEI THREDDS, Last-Modified 2024-01-29):

| File | Bytes |
| --- | --- |
| https://www.ncei.noaa.gov/thredds-ocean/fileServer/woa23/DATA/temperature/netcdf/decav/1.00/woa23_decav_t00_01.nc | 85,168,080 |
| https://www.ncei.noaa.gov/thredds-ocean/fileServer/woa23/DATA/salinity/netcdf/decav/1.00/woa23_decav_s00_01.nc | 77,439,270 |

`woa23/grids.parquet` is an ordinary Arrow table, not polygon GeoParquet. One row is
one source cell at one standard depth. Each depth is one row group, surface first.
Rows hold `depthIndex`, `gridX`, `gridY` (zero-based source indices), `depth` (m,
positive down), `longitude` and `latitude` (source float32 cell centers), and every
source statistic: `t_an`, `t_mn`, `t_dd`, `t_sd`, `t_se`, `t_oa`, `t_gp`, `t_sdo`,
`t_sea` and the same `s_*` fields. `*_an` is the objectively analyzed mean:
in-situ temperature (°C, ITS-90) and Practical Salinity (PSS-78). Fill values are
null. Arrow schema metadata keeps the global and variable attributes, depth bounds
and climatology bounds.

`woa23/preview.bin.gz` is the display preview for the math.gl bathymetry example.
It holds `t_an` and `s_an` at 33 standard depths on every second source node
(180 × 90). Values are little-endian int16 (0.001 °C) and uint16 (0.001 salinity
units), cell-major (`[latitude][longitude][depth]`), with fill −32768 and 65535.
`preview-manifest.json` gives the axes, scales and fill values. The preview is not
the scientific precision of the Parquet.

A climatology is a long-term mean, not a measured profile. It does not resolve
fronts, eddies or seasonal change, and it is not for navigation.

## Reproduce

Install `scripts/requirements.txt` in a separate Python environment. Download the two
source files, then run:

```sh
python earth/oceanography/v1/scripts/create-woa23-parquet.py \
  --temperature woa23_decav_t00_01.nc --salinity woa23_decav_s00_01.nc \
  --out earth/oceanography/v1/woa23
```

The converter checks the source sizes and dataset IDs, and the pinned SHA-256 values
once they are set. It compares every written value and null with the source arrays,
bit for bit. `scripts/test-create-woa23-parquet.py` runs the converter on small
synthetic files with the WOA23 layout and needs no download.
