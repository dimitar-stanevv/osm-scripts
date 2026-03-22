#!/usr/bin/env python3
"""
Extract the features array from a GeoJSON FeatureCollection into a plain
JSON array suitable for MongoDB import (mongoimport --jsonArray).

Usage:
    python prepare_for_mongo_import.py --input data/cams.geojson --output data/cams.json
"""

import argparse
import json
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Convert a GeoJSON FeatureCollection into a plain JSON array "
            "of its features, ready for MongoDB import."
        ),
    )
    parser.add_argument("--input", required=True, help="Path to the input GeoJSON file")
    parser.add_argument("--output", required=True, help="Path for the output JSON file")
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

    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        print(
            "Error: input file is not a GeoJSON FeatureCollection",
            file=sys.stderr,
        )
        sys.exit(1)

    features = data.get("features", [])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(features, f, ensure_ascii=False)

    print(f"Wrote {len(features):,} features to {output_path}")


if __name__ == "__main__":
    main()
