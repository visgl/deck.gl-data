# deck.gl-data
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Validate the paired Parquet snapshots and their provenance manifests."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import pyarrow as pa
import pyarrow.parquet as pq

GEOMETRY = pa.schema([
    ('featureId', pa.string()), ('polygonIndex', pa.int32()), ('plateId', pa.int32()),
    ('name', pa.string()), ('beginAge', pa.float64()), ('endAge', pa.float64()),
    ('geometry', pa.binary()),
])
ROTATIONS = pa.schema([
    ('age', pa.int16()), ('plateId', pa.int32()), ('available', pa.bool_()),
    ('w', pa.float64()), ('x', pa.float64()), ('y', pa.float64()), ('z', pa.float64()),
])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(root):
    total = 0
    for name in ('cao2024', 'muller2022'):
        model = root / name
        manifest = json.loads((model / 'manifest.json').read_text())
        require(manifest['license'] == 'CC-BY-4.0', 'Dataset license mismatch')
        require(manifest['anchorPlateId'] == 0, 'Unexpected reference anchor')
        require(manifest['quaternionOrder'] == ['w', 'x', 'y', 'z'], 'Quaternion order mismatch')
        require((model / 'ATTRIBUTION.md').is_file(), 'Missing attribution')
        tables = {}
        for record in manifest['files']:
            path = model / record['path']
            require(path.name in ('geometry.parquet', 'rotations.parquet'), 'Unexpected snapshot file')
            data = path.read_bytes()
            require(data[:4] == b'PAR1' and data[-4:] == b'PAR1', 'Not binary Parquet')
            require(len(data) == record['bytes'], 'File size mismatch')
            require(hashlib.sha256(data).hexdigest() == record['sha256'], 'SHA-256 mismatch')
            require(record['compression'] == 'ZSTD' and record['compressionLevel'] == 6,
                    'Unexpected declared compression')
            parquet = pq.ParquetFile(path)
            require(parquet.metadata.num_rows == record['rows'], 'Row count mismatch')
            require(parquet.metadata.num_row_groups == record['rowGroups'], 'Row group count mismatch')
            for group in range(parquet.metadata.num_row_groups):
                row_group = parquet.metadata.row_group(group)
                for column in range(row_group.num_columns):
                    require(row_group.column(column).compression == 'ZSTD', 'Uncompressed column')
            table = parquet.read()
            expected = GEOMETRY if path.name == 'geometry.parquet' else ROTATIONS
            require(table.schema.remove_metadata().equals(expected), 'Column schema mismatch')
            metadata = json.loads(table.schema.metadata[b'math.gl.tectonic'])
            require(metadata['model'] == manifest['model'] and metadata['version'] == manifest['version'],
                    'Model revision mismatch')
            require(metadata['referenceFrame'] == manifest['referenceFrame'], 'Frame mismatch')
            tables[path.name] = table
            total += len(data)

        geometry = tables['geometry.parquet']
        geo = json.loads(geometry.schema.metadata[b'geo'])
        require(geo['version'] == '1.1.0' and geo['primary_column'] == 'geometry', 'GeoParquet metadata mismatch')
        require(geo['columns']['geometry'] == {
            'encoding': 'WKB', 'geometry_types': ['Polygon'], 'edges': 'spherical'
        }, 'Geometry encoding or CRS convention mismatch')
        polygons = geometry.to_pylist()
        ids = {row['plateId'] for row in polygons}
        require(len(ids) == manifest['plateCount'], 'Plate count mismatch')
        require(len(polygons) == manifest['polygonRows'], 'Polygon count mismatch')
        vertices = holes = 0
        for row in polygons:
            require(row['beginAge'] >= row['endAge'], 'Invalid feature age range')
            data = row['geometry']
            byte_order, kind, rings = struct.unpack_from('<BII', data)
            require(byte_order == 1 and kind == 3 and rings > 0, 'Invalid WKB polygon')
            holes += rings - 1
            offset = 9
            for _ in range(rings):
                count, = struct.unpack_from('<I', data, offset)
                offset += 4
                require(count >= 4, 'Degenerate polygon ring')
                first = struct.unpack_from('<dd', data, offset)
                last = struct.unpack_from('<dd', data, offset + 16 * (count - 1))
                require(first == last, 'Unclosed polygon ring')
                for index in range(count):
                    lon, lat = struct.unpack_from('<dd', data, offset + 16 * index)
                    require(math.isfinite(lon) and math.isfinite(lat) and abs(lon) <= 180 and abs(lat) <= 90,
                            'Invalid geographic coordinate')
                vertices += count
                offset += 16 * count
            require(offset == len(data), 'Trailing WKB bytes')

        rotation_path = model / 'rotations.parquet'
        parquet = pq.ParquetFile(rotation_path)
        ages = manifest['ages']
        expected_ages = list(range(ages['min'], ages['max'] + 1, ages['step']))
        require(parquet.metadata.num_row_groups == len(expected_ages), 'Age group count mismatch')
        missing = 0
        for index, age in enumerate(expected_ages):
            group = parquet.metadata.row_group(index)
            stats = group.column(0).statistics
            require(stats is not None and stats.min == stats.max == age, 'Missing or incorrect age statistics')
            rows = parquet.read_row_group(index).to_pylist()
            require(len(rows) == len(ids), 'Incomplete age group')
            require({row['plateId'] for row in rows} == ids, 'Unexpected or duplicate plates')
            for row in rows:
                require(row['age'] == age, 'Mixed ages in row group')
                q = [row[component] for component in 'wxyz']
                if row['available']:
                    require(all(value is not None and math.isfinite(value) for value in q), 'Invalid quaternion')
                    require(abs(sum(value * value for value in q) - 1) <= 1e-12, 'Non-unit quaternion')
                else:
                    require(q == [None] * 4, 'Missing rotation must not be fabricated')
                    missing += 1
        print(f'{name}: {len(polygons)} polygons, {vertices} vertices, {holes} holes, '
              f'{len(expected_ages)} complete age groups, {missing} unavailable rotations')
    print(f'Validated all four Parquet files: {total:,} bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    validate(parser.parse_args().root)
