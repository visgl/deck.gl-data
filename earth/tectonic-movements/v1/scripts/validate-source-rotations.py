# deck.gl-data
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Check every exported rotation against separately selected canonical source models.

This deliberately does not import the converter or its model configuration.
pyGPlates remains an external offline validation tool.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import tempfile
import zipfile
import pyarrow.parquet as pq
import pygplates

SOURCES = {
    'cao2024': ('4a032d3ab46e6023d14add8a54b6a541', 'Paleomagnetic', [
        '1.8Ga_model_GSF/1000_0_rotfile.rot', '1.8Ga_model_GSF/1800_1000_rotfile.rot']),
    'muller2022': ('1f409e19e42128a8cf245ce54b75f1ae', 'Optimised mantle', [
        'optimisation/1000_0_rotfile_MantleOpt.rot']),
}


def validate(root, name, archive_path):
    md5, frame, source_paths = SOURCES[name]
    if hashlib.md5(archive_path.read_bytes()).hexdigest() != md5:
        raise ValueError('Source archive revision mismatch')
    manifest = json.loads((root / name / 'manifest.json').read_text())
    if manifest['referenceFrame'] != frame:
        raise ValueError('Unexpected declared reference frame')
    declared = {path for path in manifest['sourceFilesSHA256'] if path.endswith('.rot')}
    if declared != set(source_paths):
        raise ValueError('Manifest includes an alternative rotation frame or omits a time slice')
    with zipfile.ZipFile(archive_path) as archive, tempfile.TemporaryDirectory() as temp:
        files = []
        for index, source in enumerate(source_paths):
            data = archive.read(source)
            if hashlib.sha256(data).hexdigest() != manifest['sourceFilesSHA256'][source]:
                raise ValueError('Rotation source checksum mismatch')
            path = Path(temp) / f'{index}.rot'
            path.write_bytes(data)
            files.append(str(path))
        canonical = pygplates.RotationModel(files, default_anchor_plate_id=0)
        record = next(file for file in manifest['files']
                      if file['path'] in ('tectonic.parquet', 'rotations.parquet'))
        parquet = pq.ParquetFile(root / name / record['path'])
        columns = ['age', 'plateId', 'available', 'w', 'x', 'y', 'z']
        if name == 'cao2024':
            columns.append('recordType')
        checked = 0
        for batch in parquet.iter_batches(columns=columns):
            for row in batch.to_pylist():
                if row.get('recordType', 'rotation') != 'rotation':
                    continue
                expected = canonical.get_rotation(row['age'], row['plateId'],
                    use_identity_for_missing_plate_ids=False)
                if row['available'] != (expected is not None):
                    raise ValueError(f'Availability mismatch: {row}')
                if expected is not None:
                    pole, angle = expected.get_euler_pole_and_angle()
                    q = [math.cos(angle / 2), *(value * math.sin(angle / 2) for value in pole.to_xyz())]
                    actual = [row[key] for key in 'wxyz']
                    # Quaternions q and -q encode the same orientation.
                    error = min(max(abs(a-b) for a,b in zip(actual,q)),
                                max(abs(a+b) for a,b in zip(actual,q)))
                    if error > 1e-12:
                        raise ValueError(f'Reference frame mismatch: age={row["age"]}, plate={row["plateId"]}')
                checked += 1
        print(f'{name}: {checked:,} rotation samples match isolated {frame} source')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--cao', type=Path, required=True)
    parser.add_argument('--muller', type=Path, required=True)
    args = parser.parse_args()
    validate(args.root, 'cao2024', args.cao)
    validate(args.root, 'muller2022', args.muller)
