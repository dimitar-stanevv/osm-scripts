#!/usr/bin/env python3
"""
Combine four camera-type GeoJSON files into a single GeoJSON file.

Reads a folder that must contain exactly these files:

- ``combined_cams.geojson``
- ``redlight_cams.geojson``
- ``speed_cams.geojson``
- ``tunnel_cams.geojson``

Each feature gets a ``type`` property indicating its source file.
Features from ``speed_cams`` and ``combined_cams`` also get a ``speed_limit``
property (copied from the existing ``speedLimit`` if present).

Usage:
    python combine_scdb_dataset_single.py --input <FOLDER> --output <FILE>
"""

import argparse
import json
import sys
from pathlib import Path

_RED = "\033[91m"
_RESET = "\033[0m"

FILE_TYPE_MAP = {
    "combined_cams.geojson": "combined_cam",
    "redlight_cams.geojson": "redlight_cam",
    "speed_cams.geojson": "speed_cam",
    "tunnel_cams.geojson": "tunnel_cam",
}

_TYPES_WITH_SPEED_LIMIT = {"speed_cam", "combined_cam"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Combine four camera-type GeoJSON files into a single GeoJSON file."
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to folder containing the four camera GeoJSON files"
    )
    parser.add_argument(
        "--output", required=True,
        help="Path to the output GeoJSON file"
    )
    return parser.parse_args()


def error(msg: str) -> None:
    print(f"{_RED}Error: {msg}{_RESET}", file=sys.stderr)
    sys.exit(1)


def validate_input(input_dir: Path) -> None:
    if not input_dir.is_dir():
        error(f"Input folder '{input_dir}' does not exist.")

    present = {p.name for p in input_dir.iterdir() if p.is_file()}
    expected = set(FILE_TYPE_MAP.keys())
    missing = expected - present
    extra = present - expected

    if missing or extra:
        parts = [f"Input folder must contain exactly these 4 files: {', '.join(sorted(expected))}"]
        if missing:
            parts.append(f"Missing: {', '.join(sorted(missing))}")
        if extra:
            parts.append(f"Unexpected: {', '.join(sorted(extra))}")
        error("\n       ".join(parts))


def stream_features(input_path: Path, cam_type: str, out_fh, need_comma: bool) -> tuple:
    """Load one GeoJSON file and stream its features to *out_fh*.

    Processes features in chunks to keep peak memory bounded: each input file
    is loaded once, then features are written one by one so the serialised
    output is never held in memory as a single string.

    Returns ``(need_comma, count)`` where *need_comma* indicates whether the
    next call should prepend a comma separator.
    """
    with open(input_path, encoding="utf-8") as fh:
        data = json.load(fh)

    features = data.get("features", [])
    del data

    count = 0
    add_speed_limit = cam_type in _TYPES_WITH_SPEED_LIMIT

    for feat in features:
        props = feat["properties"]
        props["type"] = cam_type

        if add_speed_limit:
            props["speed_limit"] = props.get("speedLimit")

        if need_comma:
            out_fh.write(",\n")
        json.dump(feat, out_fh, ensure_ascii=False)
        need_comma = True
        count += 1

    return need_comma, count


def main():
    args = parse_args()
    input_dir = Path(args.input)
    output_path = Path(args.output)

    validate_input(input_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    with open(output_path, "w", encoding="utf-8") as out_fh:
        out_fh.write('{"type":"FeatureCollection","features":[\n')
        need_comma = False

        for filename, cam_type in FILE_TYPE_MAP.items():
            filepath = input_dir / filename
            need_comma, count = stream_features(filepath, cam_type, out_fh, need_comma)
            total += count
            print(f"  + {filename}  ({count:,} features, type={cam_type})")

        out_fh.write("\n]}\n")

    print(f"\n  → {output_path}  ({total:,} total features)")
    print("Done!")


if __name__ == "__main__":
    main()
