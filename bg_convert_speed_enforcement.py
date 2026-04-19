#!/usr/bin/env python3
"""One-time converter: speed_enforcement_segments.json → section-control GeoJSON."""

import json
import sys
from pathlib import Path

INPUT = Path("/Users/dimitarstanev/Projects/bgtolltracker/assets/data/speed_enforcement_segments.json")
OUTPUT = Path(__file__).parent / "data" / "speed_enforcement_sections.geojson"


def convert(segments: list) -> dict:
    features = []

    for seg in segments:
        props = seg["properties"]
        seg_id = props["id"]
        title = props["title"]
        speed = props["speedLimit"]["personal_car"]
        start = props["start"]
        end = props["end"]

        description = f"{start['title']} - {end['title']}, {title}"

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [start["lng"], start["lat"]],
            },
            "properties": {
                "id": seg_id,
                "description": description,
                "type": "section_start",
                "max_speed": speed,
                "is_variable": False,
            },
        })

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [end["lng"], end["lat"]],
            },
            "properties": {
                "id": seg_id,
                "description": description,
                "type": "section_end",
            },
        })

    return {"type": "FeatureCollection", "features": features}


def main():
    if not INPUT.exists():
        print(f"Error: {INPUT} not found", file=sys.stderr)
        sys.exit(1)

    segments = json.loads(INPUT.read_text(encoding="utf-8"))
    print(f"Read {len(segments)} segments from {INPUT.name}")

    collection = convert(segments)
    print(f"Generated {len(collection['features'])} features "
          f"({len(segments)} start + {len(segments)} end)")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written to {OUTPUT}")


if __name__ == "__main__":
    main()
