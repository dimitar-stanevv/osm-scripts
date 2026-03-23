#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

# Currently set to European countries (excluding Russia)
INCLUDED_COUNTRIES = ["AL","AD","AT","BY","BE","BA","BG","HR","CY","CZ","DK","EE","FI","FR","DE","GR","HU","IS","IE","IT","LV","LI","LT","LU","MT","MD","MC","ME","NL","MK","NO","PL","PT","RO","SM","RS","SK","SI","ES","SE","CH","UA","GB","VA","XK"]
KNOWN_TYPES = ("redlight_cam", "speed_cam", "combined_cam", "tunnel_cam")

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
WHITE = "\033[97m"


def parse_country_list(values):
    parsed = []
    seen = set()

    for raw in values:
        code = raw.strip().upper()
        if not code:
            raise ValueError("Country list contains an empty value.")
        if len(code) != 2 or not code.isalpha():
            raise ValueError(f"Invalid country code: {raw}")
        if code not in seen:
            seen.add(code)
            parsed.append(code)

    if not parsed:
        raise ValueError("Country list is empty.")

    return parsed


def normalize_feature_country(feature):
    if not isinstance(feature, dict):
        return None

    if feature.get("type") != "Feature":
        return None

    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None

    country = properties.get("country")
    if not isinstance(country, str):
        return None

    code = country.strip().upper()
    if len(code) != 2 or not code.isalpha():
        return None

    return code


def filter_features(features, allowed_countries):
    filtered = []
    skipped = 0

    for feature in features:
        country = normalize_feature_country(feature)
        if country is None or country not in allowed_countries:
            skipped += 1
            continue
        filtered.append(feature)

    return filtered, skipped


def count_feature_types(features):
    counts = {name: 0 for name in KNOWN_TYPES}
    counts["other"] = 0

    for feature in features:
        properties = feature.get("properties") or {}
        feature_type = properties.get("type")
        if feature_type in KNOWN_TYPES:
            counts[feature_type] += 1
        else:
            counts["other"] += 1

    return counts


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Filter GeoJSON features by country.")
    parser.add_argument("--input", required=True, help="Path to the input GeoJSON file")
    parser.add_argument("--output", required=True, help="Path to the output GeoJSON file")
    parser.add_argument(
        "--countries",
        help="Comma-separated list of country codes that overrides INCLUDED_COUNTRIES",
    )
    return parser.parse_args(argv)


def resolve_countries(countries_arg):
    if countries_arg is None:
        return parse_country_list(INCLUDED_COUNTRIES)
    return parse_country_list(countries_arg.split(","))


def build_output_document(data, filtered_features):
    output = {key: value for key, value in data.items() if key != "bbox"}
    output["type"] = "FeatureCollection"
    output["features"] = filtered_features
    return output


def print_summary(input_count, extracted_count, skipped_count, countries, type_counts, output_path):
    print()
    print(f"{BOLD}{CYAN}Filter By Country{RESET}")
    print(f"  {DIM}Countries:{RESET} {', '.join(countries)}")
    print(f"  {DIM}Input:{RESET}     {input_count:,}")
    print(f"  {DIM}Extracted:{RESET} {GREEN}{extracted_count:,}{RESET}")
    print(f"  {DIM}Skipped:{RESET}   {YELLOW}{skipped_count:,}{RESET}")
    print(f"  {DIM}Output:{RESET}    {output_path}")
    print()
    for name in ("redlight_cam", "speed_cam", "combined_cam", "tunnel_cam", "other"):
        print(f"  {name:<14} {WHITE}{type_counts[name]:>8,}{RESET}")


def main(argv=None):
    args = parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)

    try:
        countries = resolve_countries(args.countries)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if not input_path.is_file():
        print(f"Error: {input_path} does not exist or is not a file", file=sys.stderr)
        raise SystemExit(1)

    try:
        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"Error: input file is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        print("Error: input file is not a GeoJSON FeatureCollection", file=sys.stderr)
        raise SystemExit(1)

    features = data.get("features", [])
    if not isinstance(features, list):
        print("Error: input GeoJSON FeatureCollection must contain a features array", file=sys.stderr)
        raise SystemExit(1)

    filtered_features, skipped_count = filter_features(features, set(countries))
    type_counts = count_feature_types(filtered_features)
    output_data = build_output_document(data, filtered_features)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False)

    print_summary(
        input_count=len(features),
        extracted_count=len(filtered_features),
        skipped_count=skipped_count,
        countries=countries,
        type_counts=type_counts,
        output_path=output_path,
    )


if __name__ == "__main__":
    main()
