# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Validate schemas, catalog relationships, and optional public asset downloads."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

import pystac

ROOT = Path(__file__).resolve().parents[1]


def validate(downloads=False):
    paths = sorted(ROOT.rglob('*.json'))
    documents = {path.resolve(): json.loads(path.read_text()) for path in paths}
    ids = set()
    assets_checked = 0
    root = (ROOT / 'catalog.json').resolve()
    for path, document in documents.items():
        # Core and declared-extension JSON Schema validation; schemas load online.
        pystac.validation.validate_dict(document)
        assert document['id'] not in ids, document['id']
        ids.add(document['id'])
        for link in document['links']:
            href = link['href']
            if urlparse(href).scheme:
                # External provenance/license pages may restrict automated access.
                # Dataset assets are checked separately below.
                continue
            target = (path.parent / href).resolve()
            assert target in documents, (path, href)
            linked = documents[target]
            if link['rel'] == 'root':
                assert target == root
            elif link['rel'] == 'self':
                assert target == path
            elif link['rel'] == 'collection':
                assert linked['type'] == 'Collection'
                assert linked['id'] == document['collection']
                assert any((target.parent / entry['href']).resolve() == path
                           for entry in linked['links'] if entry['rel'] == 'item')
            elif link['rel'] in ['child', 'item']:
                assert any((target.parent / entry['href']).resolve() == path
                           for entry in linked['links'] if entry['rel'] == 'parent')
        if document['type'] != 'Feature':
            continue
        assert document['properties']['visgl:datetime_semantics'].startswith('Repository dataset snapshot')
        commit = document['properties']['visgl:source_commit']
        assert len(commit) == 40 and all(c in '0123456789abcdef' for c in commit)
        if downloads:
            with urlopen(document['assets']['manifest']['href']) as response:
                manifest = json.load(response)
            inventory = manifest['files']
            if isinstance(inventory, list):
                inventory = {entry['path']: entry for entry in inventory}
        for asset in document['assets'].values():
            assert f'/{commit}/' in asset['href'], asset['href']
            if not downloads:
                continue
            with urlopen(asset['href']) as response:
                content = response.read()
            if 'data' in asset['roles']:
                assert asset['href'].startswith('https://media.githubusercontent.com/media/')
                digest = hashlib.sha256(content).hexdigest()
                assert asset['file:size'] == len(content)
                assert asset['file:checksum'] == '1220' + digest
                info = inventory[asset['href'].rsplit('/', 1)[-1]]
                assert info['sha256'] == digest and info['bytes'] == len(content)
                assert not content.startswith(b'version https://git-lfs.github.com/spec/v1')
                assets_checked += 1
    catalog = pystac.Catalog.from_file(str(root))
    assert len(list(catalog.get_all_items())) == 4
    print(f'Validated {len(documents)} STAC documents, schema extensions, and reciprocal links.')
    if downloads:
        print(f'Verified {assets_checked} public data downloads against sizes, checksums, and source manifests.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--downloads', action='store_true')
    validate(parser.parse_args().downloads)
