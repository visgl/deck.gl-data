# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Human-readable Item labels describing data types, coverage and formats."""

ITEM_METADATA = {'alpine/snapshot.json': ['Alpine PISM glacier thickness, temperature and velocity grids',
                          'Alpine ice-sheet simulation grids covering 119,000 years ago to the '
                          'present, with ice thickness, bed topography, basal temperature and '
                          'basal/surface velocity components. Includes the source NetCDF, lossless '
                          'Parquet grids and a binary preview with its manifest. Ages are in '
                          'thousands of years before present.'],
 'cao2024/snapshot.json': ['Cao et al. (2024) tectonic plate geometries and rotations',
                           'Present-day tectonic geometry templates and finite plate rotations '
                           'from the Cao et al. (2024) model, provided as Parquet tables. Geometry '
                           'is unreconstructed; rotation records describe plate motion at '
                           'geological ages in millions of years before present.'],
 'countries/snapshot.json': ['World country boundaries and attributes',
                             'Country boundary polygons and source attributes from Natural Earth / '
                             'DataHub, provided as GeoParquet and a separately retained legacy '
                             'GeoJSON asset. Source rows and WKB geometries are preserved in '
                             'Parquet; the GeoJSON is not claimed to have byte-equivalent '
                             'geometry.'],
 'egm2008/snapshot.json': ['EGM2008 geoid undulation grid (5 arc minutes)',
                           'Global 5-arc-minute NGA EGM2008 geoid grid with source and Parquet '
                           'assets. Geoid undulation N is measured in meters relative to WGS84; '
                           'ellipsoidal height h = orthometric height H + N. These values are not '
                           'terrain elevation.'],
 'egm96/hi.json': ['EGM96 geoid undulation grid (15 arc minutes)',
                   'Global 15-arc-minute EGM96 geoid undulation grid in PGM and Parquet. Heights N '
                   'are meters relative to the WGS84 ellipsoid; ellipsoidal height h = orthometric '
                   'height H + N. These values are not terrain elevation.'],
 'egm96/low.json': ['EGM96 geoid undulation grid (1° preview)',
                    'Global 1-degree preview grid of EGM96 geoid heights in meters relative to the '
                    'WGS84 ellipsoid, provided as PGM and Parquet. Decimated from the '
                    '15-arc-minute grid; these values are geoid undulation, not terrain '
                    'elevation.'],
 'koehler2015/snapshot.json': ['Köhler et al. (2015) paleoclimate temperature and albedo time '
                               'series',
                               'Temperature and albedo time series spanning the last 5 million '
                               'years, with original source data and Parquet tables. All three '
                               'source temperature variants are retained, without rebasing or '
                               'extrapolation. Ages are expressed as thousands of years before '
                               'present.'],
 'krapp2021/snapshot.json': ['Krapp et al. (2021) global ice-mask grids',
                             'Global ice-mask snapshots from 799,000 years ago to the present at '
                             '1,000-year intervals, provided as source NetCDF and lossless Parquet '
                             'grids. All native cells and values are retained, with one age '
                             'snapshot per Parquet row group.'],
 'major-rivers/snapshot.json': ['Major rivers of the world: river lines and attributes',
                                'World Bank major-river line geometries and source attributes, '
                                'provided as GeoParquet. Source rows, WKB geometries and '
                                'attributes are retained, with GeoParquet 1.1.0 metadata and ZSTD '
                                'compression.'],
 'muller2022/snapshot.json': ['Müller et al. (2022) tectonic plate geometries and rotations',
                              'Present-day tectonic geometry templates and finite plate rotations '
                              'from the Müller et al. (2022) model, provided as Parquet tables. '
                              'Geometry is unreconstructed; rotation records describe plate motion '
                              'at geological ages in millions of years before present.'],
 'paleodem/snapshot.json': ['PALEOMAP PaleoDEM elevation and bathymetry grids (0–540 Ma)',
                            '109 reconstructed global elevation and bathymetry grids at '
                            '5-million-year intervals from the present to 540 million years ago. '
                            'Converted losslessly from PALEOMAP PaleoDEMs v2 CSV grids to numeric '
                            'Parquet nodes, with one age grid per row group. Source grid '
                            'dimensions and coordinates are preserved; these are gridded heights, '
                            'not vector geometries.'],
 'paleomist/snapshot.json': ['PaleoMIST ice-sheet thickness and paleotopography grids',
                             'Global PaleoMIST grids of ice thickness, base topography, '
                             'paleotopography and sea level from 80,000 years ago to the present. '
                             'Includes the source NetCDF, lossless Parquet grids and a binary '
                             'preview with its manifest. Ages are in thousands of years before '
                             'present, separate from the repository snapshot date.']}
