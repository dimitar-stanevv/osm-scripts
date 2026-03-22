#!/usr/bin/env python3
"""
Count features in GeoJSON and CSV files within a given folder.

For GeoJSON files, counts the number of features in the FeatureCollection.
For CSV files, counts the number of data rows (excluding the header).

Usage:
    python count_features.py --input <FOLDER>
"""

import argparse
import csv
import json
import sys
from pathlib import Path

SUPPORTED_EXTENSIONS = {".geojson", ".csv"}


def count_geojson_features(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "features" in data:
        return len(data["features"])
    return 0


def count_csv_rows(path: Path) -> int:
    for encoding in ("utf-8", "latin-1"):
        try:
            with open(path, encoding=encoding, newline="") as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header
                return sum(1 for _ in reader)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("utf-8/latin-1", b"", 0, 1, "all encodings failed")


def count_features(folder: Path) -> list[tuple[str, int]]:
    results = []
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        try:
            if ext == ".geojson":
                count = count_geojson_features(path)
            else:
                count = count_csv_rows(path)
            results.append((path.name, count))
        except Exception as exc:
            print(f"Warning: could not read {path.name}: {exc}", file=sys.stderr)
    return results


def parse_args():
    parser = argparse.ArgumentParser(
        description="Count features in GeoJSON and CSV files within a folder."
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to folder containing GeoJSON / CSV files"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    folder = Path(args.input)

    if not folder.is_dir():
        print(f"Error: {folder} is not a directory", file=sys.stderr)
        sys.exit(1)

    results = count_features(folder)

    if not results:
        print("No supported files (.geojson, .csv) found in the folder.")
        return

    name_width = max(len(name) for name, _ in results)
    total = 0
    for name, count in results:
        print(f"  {name:<{name_width}}  {count:>8,}")
        total += count

    print(f"  {'─' * name_width}  {'─' * 8}")
    print(f"  {'Total':<{name_width}}  {total:>8,}")
    print(f"\n  {len(results)} file(s)")


if __name__ == "__main__":
    main()
