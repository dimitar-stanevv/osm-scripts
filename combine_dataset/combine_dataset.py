#!/usr/bin/env python3
"""
Combine per-speed-limit GeoJSON files from the SCDB dataset into merged
output files grouped by camera type.

Reads a folder of GeoJSON files produced by csv_to_geojson (naming pattern
``SCDB_<Type>_<SpeedLimit>.geojson``) and writes:

- ``combined_cams.geojson``  — red-light + speed combination cameras
- ``speed_cams.geojson``     — fixed and variable speed cameras
- ``redlight_cams.geojson``  — red-light-only cameras (copy)
- ``tunnel_cams.geojson``    — tunnel cameras (copy)

Usage:
    python combine_dataset.py --input <FOLDER> --output <FOLDER>
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

# Patterns for classifying input files
_RE_REDLIGHT_SPEED = re.compile(r"^SCDB_Redlight_(\d+)\.geojson$")
_RE_SPEED_FIXED = re.compile(r"^SCDB_Speed_(\d+)\.geojson$")
_SPEED_VARIABLE = "SCDB_Speed_variable.geojson"
_REDLIGHT_ONLY = "SCDB_Redlight.geojson"
_TUNNEL = "SCDB_Tunnel.geojson"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Combine per-speed-limit SCDB GeoJSON files into merged datasets."
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to folder containing SCDB GeoJSON files"
    )
    parser.add_argument(
        "--output", required=True,
        help="Path to output folder for the combined GeoJSON files"
    )
    return parser.parse_args()


def load_geojson(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_geojson(collection: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(collection, fh, ensure_ascii=False, indent=2)


def add_property(features: list, key: str, value) -> list:
    """Return a copy of *features* with an extra property injected."""
    out = []
    for feat in features:
        feat = json.loads(json.dumps(feat))
        feat["properties"][key] = value
        out.append(feat)
    return out


def build_combined_cams(input_dir: Path) -> dict:
    """Merge SCDB_Redlight_<speed>.geojson files, adding speedLimit."""
    features = []
    matched = sorted(input_dir.glob("SCDB_Redlight_*.geojson"))

    for path in matched:
        m = _RE_REDLIGHT_SPEED.match(path.name)
        if not m:
            continue
        speed = int(m.group(1))
        coll = load_geojson(path)
        enriched = add_property(coll["features"], "speedLimit", speed)
        features.extend(enriched)
        print(f"  + {path.name}  ({len(enriched)} features, speedLimit={speed})")

    return {"type": "FeatureCollection", "features": features}


def build_speed_cams(input_dir: Path) -> dict:
    """Merge SCDB_Speed_<speed>.geojson and SCDB_Speed_variable.geojson."""
    features = []
    matched = sorted(input_dir.glob("SCDB_Speed_*.geojson"))

    for path in matched:
        m = _RE_SPEED_FIXED.match(path.name)
        if m:
            speed = int(m.group(1))
            coll = load_geojson(path)
            enriched = add_property(coll["features"], "speedLimit", speed)
            enriched = add_property(enriched, "isVariable", False)
            features.extend(enriched)
            print(f"  + {path.name}  ({len(enriched)} features, speedLimit={speed})")

    variable_path = input_dir / _SPEED_VARIABLE
    if variable_path.is_file():
        coll = load_geojson(variable_path)
        enriched = add_property(coll["features"], "speedLimit", None)
        enriched = add_property(enriched, "isVariable", True)
        features.extend(enriched)
        print(f"  + {variable_path.name}  ({len(enriched)} features, variable)")

    return {"type": "FeatureCollection", "features": features}


def copy_single(input_dir: Path, filename: str, label: str) -> Optional[dict]:
    """Load a single GeoJSON file if it exists."""
    path = input_dir / filename
    if not path.is_file():
        print(f"  ⚠  {filename} not found — skipping {label}")
        return None
    coll = load_geojson(path)
    print(f"  + {filename}  ({len(coll['features'])} features)")
    return coll


def main():
    args = parse_args()
    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.is_dir():
        print(f"Error: input folder '{input_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Combined cams (red-light + speed) ----
    print("Combined cams (red-light + speed):")
    combined = build_combined_cams(input_dir)
    out_path = output_dir / "combined_cams.geojson"
    write_geojson(combined, out_path)
    print(f"  → {out_path}  ({len(combined['features'])} total features)\n")

    # ---- Speed cams ----
    print("Speed cams:")
    speed = build_speed_cams(input_dir)
    out_path = output_dir / "speed_cams.geojson"
    write_geojson(speed, out_path)
    print(f"  → {out_path}  ({len(speed['features'])} total features)\n")

    # ---- Red-light only ----
    print("Red-light cams:")
    redlight = copy_single(input_dir, _REDLIGHT_ONLY, "red-light cams")
    if redlight:
        out_path = output_dir / "redlight_cams.geojson"
        write_geojson(redlight, out_path)
        print(f"  → {out_path}  ({len(redlight['features'])} total features)\n")

    # ---- Tunnel ----
    print("Tunnel cams:")
    tunnel = copy_single(input_dir, _TUNNEL, "tunnel cams")
    if tunnel:
        out_path = output_dir / "tunnel_cams.geojson"
        write_geojson(tunnel, out_path)
        print(f"  → {out_path}  ({len(tunnel['features'])} total features)\n")

    # ---- Report skipped files ----
    handled_patterns = {_REDLIGHT_ONLY, _TUNNEL, _SPEED_VARIABLE}
    all_geojson = set(p.name for p in input_dir.glob("*.geojson"))
    handled = set()
    for name in all_geojson:
        if name in handled_patterns:
            handled.add(name)
        elif _RE_REDLIGHT_SPEED.match(name):
            handled.add(name)
        elif _RE_SPEED_FIXED.match(name):
            handled.add(name)

    skipped = sorted(all_geojson - handled)
    if skipped:
        print(f"Skipped {len(skipped)} file(s) not matching any category:")
        for name in skipped:
            print(f"  - {name}")

    print("\nDone!")


if __name__ == "__main__":
    main()
