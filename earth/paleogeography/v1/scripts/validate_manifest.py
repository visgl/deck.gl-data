#!/usr/bin/env python3
"""Validate a local GeoParquet conversion manifest and its output artifact.

This is a publication preflight, not a license audit or remote STAC validator.
"""
import argparse
import hashlib
import json
from pathlib import Path

REQUIRED = ("citation", "license", "reconstruction_model", "coordinate_epoch",
            "source_sha256", "sha256", "size", "feature_count", "output")

def validate(manifest_path, artifact_path=None):
    manifest_path = Path(manifest_path)
    record = json.loads(manifest_path.read_text())
    errors = [f"Missing {key}" for key in REQUIRED if key not in record]
    if errors:
        return errors
    artifact = Path(artifact_path) if artifact_path else manifest_path.parent / record["output"]
    if not artifact.is_file():
        return [f"Missing artifact: {artifact}"]
    data = artifact.read_bytes()
    if len(data) != record["size"]:
        errors.append("Size mismatch")
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        errors.append("SHA-256 mismatch")
    if not all(isinstance(record[key], str) and record[key].strip()
               for key in ("citation", "license", "reconstruction_model", "coordinate_epoch")):
        errors.append("Missing provenance field")
    if not isinstance(record["feature_count"], int) or record["feature_count"] < 1:
        errors.append("Feature count must be positive")
    if not errors:
        import geopandas as gpd
        frame = gpd.read_parquet(artifact)
        if len(frame) != record["feature_count"]:
            errors.append("GeoParquet row count mismatch")
        if frame.crs is None or frame.crs.to_epsg() != 4326:
            errors.append("GeoParquet CRS mismatch")
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--artifact")
    args = parser.parse_args()
    errors = validate(args.manifest, args.artifact)
    if errors:
        parser.exit(1, "\n".join(errors) + "\n")
    print("Validated GeoParquet artifact and provenance manifest")

if __name__ == "__main__":
    main()
