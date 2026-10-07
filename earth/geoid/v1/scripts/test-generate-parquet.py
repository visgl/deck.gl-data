# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Regression checks for the committed source-manifest trust boundary."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
DATA = SCRIPTS.parent
spec = importlib.util.spec_from_file_location('converter', SCRIPTS / 'generate-parquet.py')
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class PinnedSourceTests(unittest.TestCase):
    def test_accepts_pgm_files_without_a_source_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'input'
            source.mkdir()
            for path in DATA.glob('*.pgm'):
                shutil.copyfile(path, source / path.name)
            converter.convert(source, root / 'output')
            expected = json.loads((DATA / 'manifest.json').read_text())
            actual = json.loads((root / 'output/manifest.json').read_text())
            self.assertEqual(actual, expected)

    def test_rejects_modified_pgm_with_matching_untrusted_manifests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'input'
            (source / 'scripts').mkdir(parents=True)
            manifest = json.loads((SCRIPTS / 'source-manifest.json').read_text())
            name = 'geoid-egm96-low.pgm'
            content = bytearray((DATA / name).read_bytes())
            content[-1] ^= 1
            (source / name).write_bytes(content)
            manifest['files'][name]['sha256'] = hashlib.sha256(content).hexdigest()
            for path in [source / 'geoid-manifest.json', source / 'scripts/source-manifest.json']:
                path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'pinned source manifest'):
                converter.convert(source, root / 'output')
            self.assertFalse((root / 'output' / name).exists())


if __name__ == '__main__':
    unittest.main()
