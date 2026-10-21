"""Unit tests for the provenance-gated GeoParquet converter."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("convert.py")
spec = importlib.util.spec_from_file_location("paleo_convert", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ConversionTests(unittest.TestCase):
    def setUp(self):
        try:
            import geopandas  # noqa: F401
            import pyarrow  # noqa: F401
            import shapely  # noqa: F401
        except ImportError:
            self.skipTest("Install scripts/requirements.txt to run conversion tests")

    def test_geojson_to_geoparquet_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.geojson"
            output = root / "features.parquet"
            manifest = root / "features.manifest.json"
            source.write_text(json.dumps({
                "type": "FeatureCollection",
                "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
                "features": [{
                    "type": "Feature",
                    "properties": {"name": "Synthetic example", "plate_id": 7},
                    "geometry": {"type": "Point", "coordinates": [12, 34]}
                }]
            }))
            result = module.convert(
                source, output, manifest, citation="Synthetic test fixture",
                license_id="CC0-1.0", model="TEST", coordinate_epoch="Ma:300"
            )
            self.assertEqual(result["feature_count"], 1)
            self.assertEqual(result["coordinate_epoch"], "Ma:300")
            self.assertEqual(len(result["sha256"]), 64)
            self.assertTrue(output.is_file())
            self.assertEqual(json.loads(manifest.read_text())["sha256"], result["sha256"])
            import geopandas as gpd
            restored = gpd.read_parquet(output)
            self.assertEqual(restored.iloc[0]["name"], "Synthetic example")
            self.assertEqual(int(restored.iloc[0]["plate_id"]), 7)

    def test_rejects_unattributed_data(self):
        with self.assertRaises(ValueError):
            module.convert("missing.geojson", "out.parquet", "manifest.json",
                           citation="", license_id="CC-BY-4.0",
                           model="TEST", coordinate_epoch="present")

    def test_rejects_nonfinite_epoch(self):
        for epoch in ("Ma:nan", "Ma:inf", "Ma:-1", "Ma:invalid", "Ma:"):
            with self.subTest(epoch=epoch), self.assertRaises(ValueError):
                module.convert("missing.geojson", "out.parquet", "manifest.json",
                               citation="Source", license_id="CC-BY-4.0",
                               model="TEST", coordinate_epoch=epoch)

    def test_rejects_coordinates_outside_geographic_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "invalid.geojson"
            source.write_text(json.dumps({
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "properties": {},
                              "geometry": {"type": "Point", "coordinates": [190, 20]}}]
            }))
            with self.assertRaisesRegex(ValueError, "Coordinates outside"):
                module.convert(source, root / "out.parquet", root / "manifest.json",
                               citation="Source", license_id="CC-BY-4.0",
                               model="TEST", coordinate_epoch="present")

    def test_rejects_unsupported_declared_crs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "invalid.geojson"
            source.write_text(json.dumps({
                "type": "FeatureCollection",
                "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
                "features": [{"type": "Feature", "properties": {},
                              "geometry": {"type": "Point", "coordinates": [10, 20]}}]
            }))
            with self.assertRaisesRegex(ValueError, "Unsupported GeoJSON CRS"):
                module.convert(source, root / "out.parquet", root / "manifest.json",
                               citation="Source", license_id="CC-BY-4.0",
                               model="TEST", coordinate_epoch="present")

    def test_rejects_unsupported_epoch(self):
        with self.assertRaises(ValueError):
            module.convert("missing.geojson", "out.parquet", "manifest.json",
                           citation="Source", license_id="CC-BY-4.0",
                           model="TEST", coordinate_epoch="unknown")

if __name__ == "__main__":
    unittest.main()
