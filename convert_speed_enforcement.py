#!/usr/bin/env python3
"""One-time converter: speed_enforcement_segments.json → section-control GeoJSON.

Each segment produces 4 points: forward start/end + reverse start/end.
Points are offset perpendicular to the road bearing (~7 m each side) and
nudged along-track (~3 m inward) so that no two points share coordinates.
"""

import json
import math
import sys
from pathlib import Path

INPUT = Path("/Users/dimitarstanev/Projects/bgtolltracker/assets/data/speed_enforcement_segments.json")
OUTPUT = Path(__file__).parent / "data" / "speed_enforcement_sections.geojson"

EARTH_R = 6_371_000  # metres

PERP_OFFSET_M = 7    # perpendicular offset per side (~14 m between directions)
ALONG_OFFSET_M = 3   # along-track nudge to separate shared junction points


def _bearing(lat1d, lng1d, lat2d, lng2d):
    """Return initial bearing in radians from point 1 to point 2."""
    lat1, lng1, lat2, lng2 = map(math.radians, (lat1d, lng1d, lat2d, lng2d))
    dlng = lng2 - lng1
    x = math.sin(dlng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlng)
    return math.atan2(x, y)


def _offset(lat_d, lng_d, bearing_rad, distance_m):
    """Offset a point by *distance_m* along *bearing_rad*. Returns (lng, lat)."""
    lat_r = math.radians(lat_d)
    dlat = (distance_m / EARTH_R) * math.cos(bearing_rad)
    dlng = (distance_m / EARTH_R) * math.sin(bearing_rad) / math.cos(lat_r)
    return (
        round(lng_d + math.degrees(dlng), 7),
        round(lat_d + math.degrees(dlat), 7),
    )


def _offset_point(lat, lng, road_bearing, perp_sign, along_sign):
    """Apply perpendicular + along-track offsets and return [lng, lat]."""
    perp_bearing = road_bearing + perp_sign * (math.pi / 2)
    lng1, lat1 = _offset(lat, lng, perp_bearing, PERP_OFFSET_M)
    lng2, lat2 = _offset(lat1, lng1, road_bearing, along_sign * ALONG_OFFSET_M)
    return [lng2, lat2]


def convert(segments: list) -> dict:
    features = []

    for seg in segments:
        props = seg["properties"]
        seg_id = props["id"]
        title = props["title"]
        speed = props["speedLimit"]["personal_car"]
        start = props["start"]
        end = props["end"]

        fwd_bearing = _bearing(start["lat"], start["lng"], end["lat"], end["lng"])
        rev_bearing = fwd_bearing + math.pi

        fwd_desc = f"{start['title']} - {end['title']}, {title}"
        rev_desc = f"{end['title']} - {start['title']}, {title}"

        # Forward start — right of road, nudged inward
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": _offset_point(
                    start["lat"], start["lng"], fwd_bearing,
                    perp_sign=+1, along_sign=+1),
            },
            "properties": {
                "id": seg_id,
                "description": fwd_desc,
                "type": "section_start",
                "max_speed": speed,
                "is_variable": False,
            },
        })

        # Forward end — right of road, nudged inward (against travel)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": _offset_point(
                    end["lat"], end["lng"], fwd_bearing,
                    perp_sign=+1, along_sign=-1),
            },
            "properties": {
                "id": seg_id,
                "description": fwd_desc,
                "type": "section_end",
            },
        })

        # Reverse start (at the forward-end location) — left of road, nudged inward
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": _offset_point(
                    end["lat"], end["lng"], rev_bearing,
                    perp_sign=+1, along_sign=+1),
            },
            "properties": {
                "id": seg_id,
                "description": rev_desc,
                "type": "section_start",
                "max_speed": speed,
                "is_variable": False,
            },
        })

        # Reverse end (at the forward-start location) — left of road, nudged inward
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": _offset_point(
                    start["lat"], start["lng"], rev_bearing,
                    perp_sign=+1, along_sign=-1),
            },
            "properties": {
                "id": seg_id,
                "description": rev_desc,
                "type": "section_end",
            },
        })

    # Final safety check — ensure no duplicate coordinates
    seen = {}
    nudge = 0
    for feat in features:
        coord = tuple(feat["geometry"]["coordinates"])
        while coord in seen:
            nudge += 1
            coord = (round(coord[0] + 0.000005 * nudge, 7),
                     round(coord[1] + 0.000005 * nudge, 7))
        seen[coord] = True
        feat["geometry"]["coordinates"] = list(coord)

    return {"type": "FeatureCollection", "features": features}


def main():
    if not INPUT.exists():
        print(f"Error: {INPUT} not found", file=sys.stderr)
        sys.exit(1)

    segments = json.loads(INPUT.read_text(encoding="utf-8"))
    print(f"Read {len(segments)} segments from {INPUT.name}")

    collection = convert(segments)
    n = len(collection["features"])
    print(f"Generated {n} features ({n // 2} start + {n // 2} end, "
          f"{len(segments)} segments × 2 directions)")

    coords = [tuple(f["geometry"]["coordinates"]) for f in collection["features"]]
    dupes = len(coords) - len(set(coords))
    print(f"Duplicate coordinates: {dupes}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written to {OUTPUT}")


if __name__ == "__main__":
    main()
