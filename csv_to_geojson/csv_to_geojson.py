#!/usr/bin/env python3
"""
Convert CSV files containing point data into GeoJSON FeatureCollections.

Each CSV row is expected to have the format:

    lng,lat,"description","id"

The ID field is cleaned to contain only digits (e.g. "[3420-]" → "3420").

Usage:
    python csv_to_geojson.py --input <FOLDER> --output <FOLDER>
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert CSV point-data files to GeoJSON FeatureCollections."
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to folder containing CSV files"
    )
    parser.add_argument(
        "--output", required=True,
        help="Path to output folder for GeoJSON files"
    )
    return parser.parse_args()


def extract_id(raw: str) -> str:
    """Return only the digit characters from a raw ID string."""
    return re.sub(r"\D", "", raw)


def clean_description(raw: str) -> str:
    """Return empty string if the description is just digits/brackets/dashes/symbols."""
    if re.fullmatch(r"[\d\[\]\(\)\-–—_.,:;/\\#*!?&@+= ]*", raw):
        return ""
    return raw


def _open_csv(csv_path: Path):
    """Open a CSV file, trying UTF-8 first then falling back to Latin-1."""
    try:
        fh = open(csv_path, encoding="utf-8-sig", newline="")
        fh.read()
        fh.seek(0)
        return fh
    except UnicodeDecodeError:
        return open(csv_path, encoding="latin-1", newline="")


def convert_csv(csv_path: Path) -> dict:
    """Read a single CSV file and return a GeoJSON FeatureCollection."""
    features = []

    with _open_csv(csv_path) as fh:
        reader = csv.reader(fh)
        for lineno, row in enumerate(reader, start=1):
            if not row or all(cell.strip() == "" for cell in row):
                continue

            if len(row) < 4:
                print(
                    f"  ⚠  {csv_path.name}:{lineno} — expected 4 columns, "
                    f"got {len(row)}, skipping",
                    file=sys.stderr,
                )
                continue

            try:
                lng = float(row[0])
                lat = float(row[1])
            except ValueError:
                print(
                    f"  ⚠  {csv_path.name}:{lineno} — invalid coordinates "
                    f"({row[0]!r}, {row[1]!r}), skipping",
                    file=sys.stderr,
                )
                continue

            description = clean_description(row[2].strip())
            point_id = extract_id(row[3])

            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat],
                },
                "properties": {
                    "id": point_id,
                    "description": description,
                },
            }
            features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def main():
    args = parse_args()
    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.is_dir():
        print(f"Error: input folder '{input_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    csv_files = sorted(input_dir.glob("*.csv"))
    if not csv_files:
        print(f"Error: no CSV files found in '{input_dir}'.", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Converting {len(csv_files)} CSV file(s) from {input_dir} → {output_dir}")

    for csv_path in csv_files:
        collection = convert_csv(csv_path)
        out_path = output_dir / f"{csv_path.stem}.geojson"

        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(collection, fh, ensure_ascii=False, indent=2)

        print(f"  ✓ {csv_path.name} → {out_path.name}  ({len(collection['features'])} features)")

    print("Done!")


if __name__ == "__main__":
    main()
