#!/usr/bin/env python3
"""Convert a vetted, source-native GeoJSON FeatureCollection to GeoParquet.

No upstream archives are downloaded or assumed to be redistributable here.
Input geometry must be WGS84 lon/lat at its documented reconstruction epoch,
or explicitly tagged as present-day observations. This script does NOT rotate plates.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

def convert(source, output, manifest, *, citation, license_id, model, coordinate_epoch):
    import geopandas as gpd
    if not citation.strip() or not license_id.strip() or not model.strip():
        raise ValueError("citation, license and model are required")
    if coordinate_epoch != "present":
        try:
            age = float(coordinate_epoch.removeprefix("Ma:"))
        except ValueError as error:
            raise ValueError("coordinate_epoch must be present or Ma:<finite nonnegative number>") from error
        if not coordinate_epoch.startswith("Ma:") or not math.isfinite(age) or age < 0:
            raise ValueError("coordinate_epoch must be present or Ma:<finite nonnegative number>")
    raw = json.loads(Path(source).read_text())
    if raw.get("type") != "FeatureCollection":
        raise ValueError("Input must be a GeoJSON FeatureCollection")
    # GeoJSON is WGS84 by default under RFC 7946; legacy CRS declarations
    # are accepted only when explicitly EPSG:4326.
    declared_crs = raw.get("crs")
    if declared_crs is not None and (
        declared_crs.get("type") != "name" or
        declared_crs.get("properties", {}).get("name") not in
        ("EPSG:4326", "urn:ogc:def:crs:OGC:1.3:CRS84", "OGC:CRS84")
    ):
        raise ValueError("Unsupported GeoJSON CRS declaration")
    frame = gpd.read_file(source)
    if frame.crs is None:
        raise ValueError("Input must declare a geographic CRS; do not guess its CRS")
    if frame.crs.to_epsg() != 4326:
        raise ValueError("Expected EPSG:4326 longitude/latitude geometry")
    if frame.geometry.isna().any() or frame.geometry.is_empty.any():
        raise ValueError("Null/empty geometries are not accepted")
    if not frame.geometry.is_valid.all():
        raise ValueError("Invalid geometries are not accepted")
    if not frame.empty:
        xmin, ymin, xmax, ymax = frame.total_bounds
        if not all(math.isfinite(value) for value in (xmin, ymin, xmax, ymax)):
            raise ValueError("Non-finite geographic coordinates")
        if xmin < -180 or xmax > 180 or ymin < -90 or ymax > 90:
            raise ValueError("Coordinates outside longitude/latitude bounds")
    output = Path(output)
    manifest = Path(manifest)
    if output.resolve() == Path(source).resolve() or manifest.resolve() in (output.resolve(), Path(source).resolve()):
        raise ValueError("Source, output and manifest must be different files")
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False, compression="zstd")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    metadata = {
        "source": str(source), "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "citation": citation, "license": license_id, "reconstruction_model": model,
        "coordinate_epoch": coordinate_epoch, "feature_count": len(frame),
        "output": output.name, "size": output.stat().st_size, "sha256": digest,
        "geometry_encoding": "WKB", "crs": "EPSG:4326"
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Vetted source-native GeoJSON")
    parser.add_argument("output", help="GeoParquet destination")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--citation", required=True)
    parser.add_argument("--license", required=True, dest="license_id")
    parser.add_argument("--model", required=True)
    parser.add_argument("--coordinate-epoch", required=True)
    args = parser.parse_args()
    print(json.dumps(convert(args.source, args.output, args.manifest,
                             citation=args.citation, license_id=args.license_id,
                             model=args.model, coordinate_epoch=args.coordinate_epoch), indent=2))

if __name__ == "__main__":
    main()
