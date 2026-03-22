#!/usr/bin/env python3
"""
Wrap a MongoDB export JSON array into a GeoJSON FeatureCollection.

The MongoDB export is expected to be a JSON array of Feature objects
(as produced by mongoimport --jsonArray). Each feature's ``_id`` field
is stripped before writing.

Usage:
    python mongo_export_to_geojson.py --input data/cams.json --output data/cams.geojson
"""

import argparse
import json
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Convert a MongoDB export JSON array into a GeoJSON FeatureCollection, "
            "removing the _id field from every feature."
        ),
    )
    parser.add_argument("--input", required=True, help="Path to the MongoDB export JSON file")
    parser.add_argument("--output", required=True, help="Path for the output GeoJSON file")
    return parser.parse_args()


def main():
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.is_file():
        print(f"Error: {input_path} does not exist or is not a file", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        print("Error: input file is not a JSON array", file=sys.stderr)
        sys.exit(1)

    for feature in data:
        feature.pop("_id", None)

    feature_collection = {
        "type": "FeatureCollection",
        "features": data,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(feature_collection, f, ensure_ascii=False)

    print(f"Wrote {len(data):,} features to {output_path}")


if __name__ == "__main__":
    main()
