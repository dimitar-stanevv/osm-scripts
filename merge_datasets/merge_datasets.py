#!/usr/bin/env python3
"""
Merge multiple GeoJSON FeatureCollection files from a folder into a single
combined GeoJSON FeatureCollection.

Usage:
    python merge_datasets.py --input data/geojsons --output data/merged.geojson
"""

import argparse
import json
import sys
from pathlib import Path

COLORS = {
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "cyan": "\033[96m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def c(text, color):
    return f"{COLORS[color]}{text}{COLORS['reset']}"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Merge multiple GeoJSON files from a folder into one FeatureCollection.",
    )
    parser.add_argument(
        "--input", required=True, help="Path to folder containing GeoJSON files"
    )
    parser.add_argument(
        "--output", required=True, help="Path for the merged GeoJSON output file"
    )
    return parser.parse_args()


def load_features(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise ValueError("not a GeoJSON FeatureCollection")

    return data.get("features", [])


def main():
    args = parse_args()
    input_dir = Path(args.input)
    output_path = Path(args.output)

    if not input_dir.is_dir():
        print(f"{c('Error:', 'red')} {input_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    geojson_files = sorted(input_dir.glob("*.geojson"))

    if not geojson_files:
        print(
            f"{c('Error:', 'red')} no .geojson files found in {input_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\n📂 Scanning {c(str(input_dir), 'cyan')} …")
    print(f"   Found {c(str(len(geojson_files)), 'bold')} GeoJSON file(s)\n")

    all_features: list[dict] = []
    name_width = max(len(p.name) for p in geojson_files)

    for path in geojson_files:
        try:
            features = load_features(path)
            all_features.extend(features)
            print(
                f"  {c('✔', 'green')} {path.name:<{name_width}}  "
                f"{c(f'{len(features):>8,}', 'green')} features"
            )
        except Exception as exc:
            print(
                f"  {c('✘', 'red')} {path.name:<{name_width}}  "
                f"{c(f'skipped ({exc})', 'yellow')}"
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    collection = {"type": "FeatureCollection", "features": all_features}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False)

    print(f"\n{'─' * 50}")
    print(
        f"  📦 Wrote {c(f'{len(all_features):,}', 'bold')} total features "
        f"→ {c(str(output_path), 'cyan')}\n"
    )


if __name__ == "__main__":
    main()
