#!/usr/bin/env python3
"""
Fetch average-speed enforcement (section control) data from OpenStreetMap
via the Overpass API and write the results as a GeoJSON FeatureCollection.

Each GeoJSON feature represents one enforcement relation with its controlled
road section as geometry and metadata (maxspeed, devices, from/to points,
section length) in properties.

Usage:
    python fetch_section_control.py --country BG --output section_control_BG.geojson
"""

import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / "config.json"


def _load_config() -> dict:
    if not _CONFIG_PATH.is_file():
        print(f"Error: config file not found at {_CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


_CONFIG = _load_config()
OVERPASS_URL = _CONFIG["overpass_url"]
QUERY_TIMEOUT = 120  # seconds for the Overpass [timeout:…] directive
REQUEST_TIMEOUT = 180  # seconds for the HTTP request itself


# ---------------------------------------------------------------------------
# Overpass query
# ---------------------------------------------------------------------------
def build_overpass_query(country_code: str) -> str:
    return (
        f'[out:json][timeout:{QUERY_TIMEOUT}];\n'
        f'area["ISO3166-1"="{country_code}"]->.searchArea;\n'
        f'rel["type"="enforcement"]["enforcement"="average_speed"](area.searchArea);\n'
        f'out body;\n'
        f'>;\n'
        f'out skel qt;\n'
    )


def fetch_overpass(query: str) -> dict:
    print(f"Querying Overpass API at {OVERPASS_URL} …")
    resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    print(f"  Received {len(data.get('elements', []))} elements")
    return data


# ---------------------------------------------------------------------------
# Element indexing
# ---------------------------------------------------------------------------
def index_elements(elements: list) -> tuple:
    """Build lookup dicts: nodes_by_id and ways_by_id from the flat element list."""
    nodes = {}
    ways = {}
    for el in elements:
        eid = el["id"]
        if el["type"] == "node":
            nodes[eid] = el
        elif el["type"] == "way":
            ways[eid] = el
    return nodes, ways


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def build_way_coords(way: dict, nodes_by_id: dict) -> list:
    """Return [[lng, lat], …] for a way, resolving node references."""
    coords = []
    for nid in way.get("nodes", []):
        node = nodes_by_id.get(nid)
        if node:
            coords.append([node["lon"], node["lat"]])
    return coords


def join_ways(coord_lists: list) -> tuple:
    """Try to join multiple coordinate lists end-to-end into a single LineString.

    Returns (geometry_type, coordinates) where geometry_type is either
    "LineString" or "MultiLineString".
    """
    if not coord_lists:
        return "LineString", []
    if len(coord_lists) == 1:
        return "LineString", coord_lists[0]

    joined = [coord_lists[0]]

    for segment in coord_lists[1:]:
        if not segment:
            continue
        tail = joined[-1][-1] if joined[-1] else None

        if tail and segment[0] == tail:
            joined[-1].extend(segment[1:])
        elif tail and segment[-1] == tail:
            joined[-1].extend(list(reversed(segment))[1:])
        elif joined[-1] and joined[-1][0] == segment[-1]:
            joined[-1] = segment[:-1] + joined[-1]
        elif joined[-1] and joined[-1][0] == segment[0]:
            joined[-1] = list(reversed(segment))[:-1] + joined[-1]
        else:
            joined.append(segment)

    if len(joined) == 1:
        return "LineString", joined[0]
    return "MultiLineString", joined


def _haversine(lon1, lat1, lon2, lat2) -> float:
    """Distance in metres between two WGS-84 points."""
    r = 6_371_000
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def linestring_length_m(coords: list) -> float:
    total = 0.0
    for i in range(len(coords) - 1):
        total += _haversine(coords[i][0], coords[i][1],
                            coords[i + 1][0], coords[i + 1][1])
    return round(total, 1)


def geometry_length_m(geom_type: str, coords) -> float:
    if geom_type == "LineString":
        return linestring_length_m(coords)
    total = 0.0
    for part in coords:
        total += linestring_length_m(part)
    return round(total, 1)


# ---------------------------------------------------------------------------
# Relation → GeoJSON Feature
# ---------------------------------------------------------------------------
def relation_to_feature(relation: dict, nodes_by_id: dict, ways_by_id: dict) -> Optional[dict]:
    tags = relation.get("tags", {})
    members = relation.get("members", [])

    section_coord_lists = []
    devices = []
    from_point = None
    to_point = None
    section_tags = {}

    for member in members:
        role = member.get("role", "")
        ref = member["ref"]
        mtype = member["type"]

        if role == "section" and mtype == "way":
            way = ways_by_id.get(ref)
            if way:
                coords = build_way_coords(way, nodes_by_id)
                if coords:
                    section_coord_lists.append(coords)
                if not section_tags:
                    section_tags = way.get("tags", {})

        elif role == "device":
            if mtype == "node":
                node = nodes_by_id.get(ref)
                if node:
                    devices.append([node["lon"], node["lat"]])
            elif mtype == "way":
                way = ways_by_id.get(ref)
                if way:
                    coords = build_way_coords(way, nodes_by_id)
                    if coords:
                        devices.append(coords[0])

        elif role == "from" and mtype == "node":
            node = nodes_by_id.get(ref)
            if node:
                from_point = [node["lon"], node["lat"]]

        elif role == "to" and mtype == "node":
            node = nodes_by_id.get(ref)
            if node:
                to_point = [node["lon"], node["lat"]]

    geom_type, geom_coords = join_ways(section_coord_lists)

    if not geom_coords:
        print(f"  ⚠  Relation {relation['id']} has no section geometry — skipping")
        return None

    section_length = geometry_length_m(geom_type, geom_coords)

    road_names = {}
    for key, val in section_tags.items():
        if key == "name" or key.startswith("name:") or key in ("int_name", "ref", "int_ref"):
            road_names[key] = val

    properties = {
        "osm_relation_id": relation["id"],
        "enforcement": tags.get("enforcement", "average_speed"),
        "maxspeed": tags.get("maxspeed"),
        "road_ref": section_tags.get("ref") or tags.get("ref"),
        "road_names": road_names,
        "highway_class": section_tags.get("highway"),
        "from": from_point,
        "to": to_point,
        "devices": devices,
        "section_length_m": section_length,
        "relation_tags": tags,
    }

    return {
        "type": "Feature",
        "geometry": {"type": geom_type, "coordinates": geom_coords},
        "properties": properties,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch average-speed enforcement (section control) data from OSM."
    )
    parser.add_argument(
        "--country", required=True,
        help="ISO 3166-1 alpha-2 country code (e.g. BG, DE, AT)"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output GeoJSON file path (e.g. section_control_BG.geojson)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    country = args.country.upper()
    output_file = args.output

    if not re.fullmatch(r"[A-Z]{2}", country):
        print(f"Error: '{args.country}' is not a valid ISO 3166-1 alpha-2 country code.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching enforcement=average_speed relations for {country} …")
    query = build_overpass_query(country)
    data = fetch_overpass(query)

    elements = data.get("elements", [])
    nodes_by_id, ways_by_id = index_elements(elements)

    relations = [el for el in elements if el["type"] == "relation"]
    print(f"  Found {len(relations)} enforcement relation(s)")

    features = []
    for rel in relations:
        feat = relation_to_feature(rel, nodes_by_id, ways_by_id)
        if feat:
            features.append(feat)

    collection = {"type": "FeatureCollection", "features": features}

    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(collection, fh, ensure_ascii=False, indent=2)

    print()
    print(f"✓ Wrote {len(features)} section-control features to {output_file}")

    for i, feat in enumerate(features):
        props = feat["properties"]
        maxspeed = props["maxspeed"] or "?"
        length = props["section_length_m"]
        ref = props["road_ref"] or "unnamed"
        devices = len(props["devices"])
        print(f"  [{i + 1}] {ref} — {maxspeed} km/h, {length:.0f} m, {devices} device(s)")

    print("Done!")


if __name__ == "__main__":
    main()
