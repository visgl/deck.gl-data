# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Verify all inventory checksums, Parquet age groups and compression."""
import hashlib,json
from pathlib import Path
import pyarrow.parquet as pq
root=Path(__file__).resolve().parents[1]
for path in root.glob('*/manifest.json'):
    manifest=json.loads(path.read_text())
    assert manifest['license'] in ['CC-BY-4.0','CC-BY-3.0']
    for record in manifest['files']:
        file=path.parent/record['path']
        assert file.stat().st_size==record['bytes']
        assert hashlib.sha256(file.read_bytes()).hexdigest()==record['sha256']
        if file.suffix!='.parquet':continue
        parquet=pq.ParquetFile(file)
        assert parquet.schema_arrow.metadata
        for i in range(parquet.num_row_groups):
            group=parquet.metadata.row_group(i)
            for j in range(group.num_columns):assert group.column(j).compression=='ZSTD'
        if file.name=='grids.parquet':
            assert parquet.num_row_groups==len(manifest['ages'])
            for i,age in enumerate(manifest['ages']):
                group=parquet.metadata.row_group(i)
                stats=group.column(0).statistics
                assert stats.min==stats.max==age
                assert group.num_rows==manifest['rowGroupIndex'][i]['rows']
    print(manifest['id'],'validated')
