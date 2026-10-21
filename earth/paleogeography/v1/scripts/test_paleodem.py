# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: Copyright (c) vis.gl contributors
"""Regression cases for variations actually encountered in the source CSV archive."""
import io
import unittest
import zipfile

import numpy as np
from paleodem import inventory, read_source


class PaleoDEMTests(unittest.TestCase):
    def archive(self, content):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as output:
            output.writestr('grid.csv', content)
        return zipfile.ZipFile(io.BytesIO(buffer.getvalue()))

    def test_header_and_line_ending_variants_preserve_equatorial_precision(self):
        for header in ['# lon,lat,elev', 'longitude,latitude,elevation']:
            for newline in ['\n', '\r', '\r\n']:
                content = newline.join([header, '-180,1,-10', '-179,1,20',
                                        '-180,-1.421085e-14,30', '-179,-1.421085e-14,40'])
                with self.archive(content) as archive:
                    data = read_source(archive, 'grid.csv')
                self.assertEqual(data.shape, (4, 3))
                self.assertEqual(data[2, 1], -1.421085e-14)
                np.testing.assert_array_equal(data[:, 2], [-10, 20, 30, 40])

    def test_reject_invalid_values_and_grid_order(self):
        for rows in ['-180,0,nan\n-179,0,1',
                     '-179,0,1\n-180,0,2', '-181,0,1\n-180,0,2']:
            with self.archive('# lon,lat,elev\n' + rows) as archive:
                with self.assertRaises(ValueError):
                    read_source(archive, 'grid.csv')

    def test_reject_unrecognized_headers(self):
        with self.archive('x,y,z\n-180,0,1') as archive:
            with self.assertRaises(ValueError):
                read_source(archive, 'grid.csv')

    def test_age_inventory_requires_every_age_once(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as output:
            for age in range(0, 541, 5):
                output.writestr(f'csv/Map01_{age:03}Ma.csv', '')
        with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as archive:
            self.assertEqual(len(inventory(archive)), 109)
        with self.archive('') as archive:
            with self.assertRaises(ValueError):
                inventory(archive)


if __name__ == '__main__':
    unittest.main()
