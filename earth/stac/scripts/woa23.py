# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Add the immutable WOA23 temperature and salinity collection to the Earth catalog."""
import argparse
import json
from pathlib import Path
from generate import ROOT, WORLD, GEOMETRY, FILE_EXTENSION, link, write, url

COMMIT = 'ddd9edb07c99282cc4c142706f804e2208a0bfe0'
DATE = '2026-11-19T20:23:32Z'
FOLDER = 'earth/oceanography/v1/woa23'
TYPES = {'.parquet': 'application/vnd.apache.parquet', '.gz': 'application/gzip', '.json': 'application/json'}
CITATIONS = [
    ('https://doi.org/10.25923/54bh-1613',
     'Locarnini et al. (2023). World Ocean Atlas 2023, Volume 1: Temperature. NOAA Atlas NESDIS 89.'),
    ('https://doi.org/10.25923/70qt-9574',
     'Reagan et al. (2023). World Ocean Atlas 2023, Volume 2: Salinity. NOAA Atlas NESDIS 90.'),
]


def generate_woa23(manifest_path=None, commit=COMMIT, date=DATE):
    assert commit and date, 'Set COMMIT and DATE to the dataset commit first'
    manifest_path = manifest_path or ROOT.parents[1] / FOLDER / 'manifest.json'
    manifest = json.loads(Path(manifest_path).read_text())
    catalog = json.loads((ROOT / 'catalog.json').read_text())
    identifier = 'visgl-woa23'
    source = {'commit': commit, 'path': FOLDER}
    depths = [entry['depthMeters'] for entry in manifest['rowGroupIndex']]
    description = ('NOAA NCEI World Ocean Atlas 2023 annual 1° climatology of in-situ temperature (°C) and '
                   'practical salinity (PSS-78) at 102 standard depths from 0 to 5500 m, averaged over all '
                   'decades 1955–2022. ' + manifest['conversion'] + ' NCEI states that the data are openly '
                   'available to the public and asks users to acknowledge them; no named license applies. '
                   'Climatological means, not measured profiles; not for navigation.')
    collection = {
        'type': 'Collection', 'stac_version': '1.1.0', 'id': identifier,
        'title': 'NOAA World Ocean Atlas 2023 temperature and salinity', 'description': description,
        'license': 'other',
        'providers': [{'name': 'NOAA National Centers for Environmental Information (NCEI)',
                       'roles': ['producer', 'licensor'], 'url': manifest['dataset']},
                      {'name': 'vis.gl', 'roles': ['processor', 'host'], 'url': 'https://github.com/visgl/deck.gl-data'}],
        'extent': {'spatial': {'bbox': [WORLD]}, 'temporal': {'interval': [[date, date]]}},
        'summaries': {'ocean:depth_min_m': [min(depths)], 'ocean:depth_max_m': [max(depths)],
                      'ocean:climatology': ['WOA23 annual decav']},
        'links': [link('root', '../catalog.json'), link('parent', '../catalog.json'), link('self', 'collection.json'),
                  link('license', manifest['licenseUrl'], 'text/html', title='NCEI World Ocean Atlas access statement'),
                  link('license', url(source, 'license-evidence.json'), 'application/json', title='License evidence'),
                  link('derived_from', manifest['accession'], 'text/html', title='NCEI Accession 0270533'),
                  *[link('cite-as', doi, 'text/html', title=title) for doi, title in CITATIONS],
                  link('item', 'snapshot.json', 'application/geo+json')]}
    assets = {}
    for record in manifest['files']:
        filename = record['path']
        assets[filename] = {'href': url(source, filename, media=Path(filename).suffix in ['.parquet', '.gz']),
                            'type': TYPES[Path(filename).suffix],
                            'roles': ['metadata'] if filename == 'preview-manifest.json' else ['data'],
                            'file:size': record['bytes'], 'file:checksum': '1220' + record['sha256']}
    assets.update(manifest={'href': url(source, 'manifest.json'), 'type': 'application/json', 'roles': ['metadata']},
                  attribution={'href': url(source, 'ATTRIBUTION.md'), 'type': 'text/markdown', 'roles': ['metadata']})
    item = {'type': 'Feature', 'stac_version': '1.1.0', 'stac_extensions': [FILE_EXTENSION],
            'id': identifier + '-snapshot', 'collection': identifier, 'bbox': WORLD, 'geometry': GEOMETRY,
            'properties': {'datetime': date, 'visgl:source_commit': commit,
                           'visgl:datetime_semantics': 'Repository dataset snapshot commit time; not observation time or climatology period',
                           'ocean:climatology': 'WOA23 annual decav', 'ocean:time_coverage': manifest['timeCoverage'],
                           'ocean:spacing_degrees': 1, 'ocean:depth_levels': len(depths),
                           'ocean:depth_min_m': min(depths), 'ocean:depth_max_m': max(depths),
                           'ocean:variables': manifest['columns'], 'visgl:rows': manifest['rows']},
            'links': [link('root', '../catalog.json'), link('parent', 'collection.json'),
                      link('collection', 'collection.json'), link('self', 'snapshot.json', 'application/geo+json')],
            'assets': assets}
    write('woa23/collection.json', collection)
    write('woa23/snapshot.json', item)
    catalog['links'] = [entry for entry in catalog['links'] if entry['href'] != 'woa23/collection.json']
    catalog['links'].append(link('child', 'woa23/collection.json', title=collection['title']))
    write('catalog.json', catalog)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--commit', default=COMMIT)
    parser.add_argument('--date', default=DATE)
    args = parser.parse_args()
    generate_woa23(args.manifest, args.commit, args.date)
