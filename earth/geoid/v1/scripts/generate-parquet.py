# math.gl
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Convert checksum-pinned EGM96 PGM grids to lossless node tables.

Requires numpy==2.5.3 and pyarrow==23.0.1. Usage:
python generate-parquet.py --source modules/geoid/data --output /path/to/output
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


def convert(source, output):
    # Trust the manifest committed beside this converter, never source inputs.
    manifest_path = Path(__file__).resolve().with_name('source-manifest.json')
    manifest = json.loads(manifest_path.read_text())
    output.mkdir(parents=True, exist_ok=True)
    result = dict(model=manifest['model'], source=manifest['source'],
                  sourceSha256=manifest['sourceSha256'], license=manifest['license'], files={})
    for name, info in manifest['files'].items():
        if not name.endswith('.pgm'):
            continue
        content = (source / name).read_bytes()
        if hashlib.sha256(content).hexdigest() != info['sha256']:
            raise ValueError(f'{name}: SHA-256 does not match the pinned source manifest')
        (output / name).write_bytes(content)
        result['files'][name] = dict(info, format='PGM')
        header, pixels = content.split(b'65535\n', 1)
        lines = header.decode('ascii').splitlines()
        width, height = map(int, lines[-1].split())
        assert (width, height) == (info['width'], info['height'])
        fields = dict(line[2:].split(' ', 1) for line in lines if line.startswith('# '))
        offset, scale = float(fields['Offset']), float(fields['Scale'])
        raw = np.frombuffer(pixels, dtype='>u2').astype(np.uint16)
        assert len(raw) == width * height
        row = np.repeat(np.arange(height, dtype=np.int32), width)
        column = np.tile(np.arange(width, dtype=np.int32), height)
        longitude = column.astype(np.float64) * (360 / width)
        longitude = np.where(longitude >= 180, longitude - 360, longitude)
        latitude = 90 - row.astype(np.float64) * (180 / (height - 1))
        heights = offset + scale * raw.astype(np.float64)
        metadata = dict(model=manifest['model'], license=manifest['license'],
                        source=manifest['source'], sourceSha256=manifest['sourceSha256'],
                        pgmFile=name, pgmSha256=info['sha256'], width=width, height=height,
                        spacingArcMinutes=info['spacingArcMinutes'], offset=offset, scale=scale,
                        units='meters', heightReference='WGS84 ellipsoid',
                        heightDefinition='geoid undulation N; ellipsoidal h = orthometric H + N',
                        order='row-major, north to south, columns east from 0 degrees',
                        longitudeRange='[-180, 180)', polesIncluded=True,
                        preview=info['spacingArcMinutes'] == 60)
        table = pa.table(dict(row=row, column=column, longitude=longitude,
                              latitude=latitude, geoid_height=heights, raw_value=raw))
        table = table.replace_schema_metadata({b'geoid': json.dumps(metadata).encode()})
        path = output / name.replace('.pgm', '.parquet')
        pq.write_table(table, path, compression='zstd', row_group_size=width * 32,
                       use_dictionary=False, write_statistics=True, version='2.6')
        restored = pq.read_table(path)
        assert restored.schema.equals(table.schema, check_metadata=True)
        for field in table.column_names:
            assert np.array_equal(restored[field].to_numpy(), table[field].to_numpy()), field
        assert np.array_equal(restored['raw_value'].to_numpy().astype('>u2').tobytes(), pixels)
        result['files'][path.name] = dict(metadata, rows=table.num_rows,
                                         bytes=path.stat().st_size,
                                         sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        print(f'{path.name}: {table.num_rows:,} nodes, {path.stat().st_size:,} bytes; exact round-trip')
    (output / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    convert(args.source, args.output)
