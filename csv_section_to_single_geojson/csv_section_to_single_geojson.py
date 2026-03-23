#!/usr/bin/env python3
"""
Convert SCDB section-control CSV files into a single GeoJSON FeatureCollection.

Reads a folder of CSV files from the SCDB section-control database export,
classifies them by point role (start / mid / end) based on filename, enriches
features with max_speed and role properties, and writes a single combined
GeoJSON file.

Point roles:
  - section_start — from SCDB_Section_<N>.csv / SCDB_Section_variable.csv
  - section_mid   — from SCDB_Section_MID.csv
  - section_end   — from SCDB_Section_End.csv

Usage:
    python csv_section_to_single_geojson.py --input <FOLDER> --output <FILE>
"""

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

# ── ANSI colours ─────────────────────────────────────────────────────────────

_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[91m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_BLUE = "\033[94m"
_MAGENTA = "\033[95m"
_CYAN = "\033[96m"
_RESET = "\033[0m"

# ── Filename classification patterns ────────────────────────────────────────

_RE_SECTION_SPEED = re.compile(r"^SCDB_Section_(\d+)\.csv$")
_SECTION_VARIABLE = "SCDB_Section_variable.csv"
_SECTION_END = "SCDB_Section_End.csv"
_SECTION_MID = "SCDB_Section_MID.csv"

CATEGORIES = [
    ("section_start", "🚀 Section start points", _BLUE),
    ("section_mid",   "📍 Section mid points",   _MAGENTA),
    ("section_end",   "🏁 Section end points",   _CYAN),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert SCDB section-control CSV files into a single combined GeoJSON file."
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to folder containing SCDB section CSV files"
    )
    parser.add_argument(
        "--output", required=True,
        help="Path to the output GeoJSON file"
    )
    return parser.parse_args()


# ── CSV parsing ──────────────────────────────────────────────────────────────

def _extract_id(raw: str) -> str:
    """Return only the digit characters from a raw ID string."""
    return re.sub(r"\D", "", raw)


def _clean_description(raw: str) -> str:
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


def _parse_csv_features(csv_path: Path) -> tuple:
    """Read a single CSV and return ``(features_list, warning_count)``."""
    features = []
    warnings = 0

    with _open_csv(csv_path) as fh:
        reader = csv.reader(fh)
        for lineno, row in enumerate(reader, start=1):
            if not row or all(cell.strip() == "" for cell in row):
                continue

            if len(row) < 4:
                print(
                    f"    {_YELLOW}⚠️  {csv_path.name}:{lineno} — expected 4 columns, "
                    f"got {len(row)}, skipping{_RESET}",
                    file=sys.stderr,
                )
                warnings += 1
                continue

            try:
                lng = float(row[0])
                lat = float(row[1])
            except ValueError:
                print(
                    f"    {_YELLOW}⚠️  {csv_path.name}:{lineno} — invalid coordinates "
                    f"({row[0]!r}, {row[1]!r}), skipping{_RESET}",
                    file=sys.stderr,
                )
                warnings += 1
                continue

            description = _clean_description(row[2].strip())
            point_id = _extract_id(row[3])

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

    return features, warnings


# ── File classification ──────────────────────────────────────────────────────

def _classify_csv_files(csv_files: list) -> tuple:
    """Classify CSV files into section-control point-role buckets.

    Returns ``(buckets, skipped)`` where *buckets* maps category name to a list
    of ``(path, max_speed, is_variable)`` tuples, and *skipped* is a list of
    paths that didn't match any known pattern.
    """
    buckets = {cat[0]: [] for cat in CATEGORIES}
    skipped = []

    for path in csv_files:
        name = path.name

        m = _RE_SECTION_SPEED.match(name)
        if m:
            buckets["section_start"].append((path, int(m.group(1)), False))
            continue

        if name == _SECTION_VARIABLE:
            buckets["section_start"].append((path, None, True))
            continue

        if name == _SECTION_END:
            buckets["section_end"].append((path, None, False))
            continue

        if name == _SECTION_MID:
            buckets["section_mid"].append((path, None, False))
            continue

        skipped.append(path)

    return buckets, skipped


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    input_dir = Path(args.input)
    output_path = Path(args.output)

    if not input_dir.is_dir():
        print(f"{_RED}Error: input folder '{input_dir}' does not exist.{_RESET}",
              file=sys.stderr)
        sys.exit(1)

    csv_files = sorted(input_dir.glob("SCDB_Section*.csv"))
    if not csv_files:
        print(f"{_RED}Error: no SCDB_Section* CSV files found in '{input_dir}'.{_RESET}",
              file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Header ────────────────────────────────────────────────────────────
    print()
    print(f"  {_BOLD}📂 Input folder:{_RESET}  {input_dir}")
    print(f"  {_BOLD}📄 CSV files:{_RESET}     {len(csv_files)}")
    print(f"  {_BOLD}💾 Output:{_RESET}        {output_path}")
    print()
    print(f"  {_DIM}{'━' * 60}{_RESET}")
    print()

    # ── Step 1: Classify ──────────────────────────────────────────────────
    print(f"  {_BOLD}🏷️  Step 1/2 — Classifying CSV files by point role{_RESET}")
    print()

    buckets, skipped = _classify_csv_files(csv_files)

    classified_count = sum(len(entries) for entries in buckets.values())

    for cat_key, cat_label, cat_color in CATEGORIES:
        entries = buckets[cat_key]
        if not entries:
            print(f"    {_DIM}{cat_label}: (none){_RESET}")
            continue
        print(f"    {cat_color}{cat_label}:{_RESET}")
        for path, speed, is_var in sorted(entries, key=lambda e: (e[1] or 0, e[0].name)):
            if is_var:
                print(f"      {_DIM}•{_RESET} {path.name} {_DIM}(variable){_RESET}")
            elif speed is not None:
                print(f"      {_DIM}•{_RESET} {path.name} {_DIM}(max_speed={speed}){_RESET}")
            else:
                print(f"      {_DIM}•{_RESET} {path.name}")
    print()

    if skipped:
        print(f"    {_YELLOW}⏭️  Skipped {len(skipped)} file(s) not matching any section pattern:{_RESET}")
        for path in skipped:
            print(f"      {_DIM}• {path.name}{_RESET}")
        print()

    print(f"    {_CYAN}📊 {classified_count} file(s) classified, "
          f"{len(skipped)} skipped{_RESET}")
    print()
    print(f"  {_DIM}{'━' * 60}{_RESET}")
    print()

    # ── Step 2: Convert & stream ──────────────────────────────────────────
    print(f"  {_BOLD}📝 Step 2/2 — Converting CSV → GeoJSON{_RESET}")
    print()

    total_features = 0
    total_warnings = 0
    t_start = time.time()

    with open(output_path, "w", encoding="utf-8") as out_fh:
        out_fh.write('{"type":"FeatureCollection","features":[\n')
        need_comma = False

        for cat_key, cat_label, cat_color in CATEGORIES:
            entries = buckets[cat_key]
            if not entries:
                continue

            cat_count = 0
            print(f"    {cat_color}{cat_label}:{_RESET}")

            for path, max_speed, is_variable in sorted(
                entries, key=lambda e: (e[1] or 0, e[0].name)
            ):
                features, warnings = _parse_csv_features(path)
                total_warnings += warnings

                for feat in features:
                    props = feat["properties"]
                    props["type"] = cat_key

                    if cat_key == "section_start":
                        props["max_speed"] = max_speed
                        props["is_variable"] = is_variable

                    if need_comma:
                        out_fh.write(",\n")
                    json.dump(feat, out_fh, ensure_ascii=False)
                    need_comma = True

                count = len(features)
                cat_count += count

                detail_parts = [f"{count:,} features"]
                if max_speed is not None:
                    detail_parts.append(f"max_speed={max_speed}")
                if is_variable:
                    detail_parts.append("variable")
                detail = ", ".join(detail_parts)

                print(f"      {_GREEN}✅{_RESET} {path.name}  {_DIM}({detail}){_RESET}")

            total_features += cat_count
            print(f"      {_CYAN}↳ Subtotal: {cat_count:,} features{_RESET}")
            print()

        out_fh.write("\n]}\n")

    elapsed = time.time() - t_start

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"  {_DIM}{'━' * 60}{_RESET}")
    print()
    print(f"  {_GREEN}{_BOLD}✨ Done!{_RESET}  {classified_count} CSV files → "
          f"{_BOLD}{total_features:,}{_RESET} features → {output_path.name}")
    warn_str = f"  {_YELLOW}⚠️  {total_warnings} warning(s){_RESET}" if total_warnings else ""
    print(f"  {_DIM}⏱️  {elapsed:.1f}s{_RESET}{warn_str}")
    print()


if __name__ == "__main__":
    main()
