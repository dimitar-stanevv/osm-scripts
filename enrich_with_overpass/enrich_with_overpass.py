#!/usr/bin/env python3
"""
Enrich a GeoJSON point file with the single closest road from the Overpass API.
Processes in resumable batches, then auto-merges into the output file and
cleans up the temporary batch directory.
"""

import argparse
import json
import math
import os
import shutil
import sys
import time
import threading
from pathlib import Path

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# ---------------------------------------------------------------------------
# Defaults (overridable via CLI)
# ---------------------------------------------------------------------------
DEFAULT_BATCH_SIZE = 100
DEFAULT_MAX_WORKERS = 10
DEFAULT_REQUESTS_PER_SECOND = 9  # 540 req/min
HIGHWAY_CLASSES = (
    "motorway|motorway_link|trunk|trunk_link|primary|primary_link|"
    "secondary|secondary_link|tertiary|tertiary_link|"
    "residential|road|unclassified|living_street"
)
SEARCH_RADIUS = 30  # metres

NAME_KEYS = {
    "name", "int_name", "alt_name", "old_name",
    "short_name", "official_name", "loc_name",
}


# ---------------------------------------------------------------------------
# Rate limiter (token-bucket, thread-safe)
# ---------------------------------------------------------------------------
class RateLimiter:
    """Simple token-bucket rate limiter."""

    def __init__(self, max_per_second: float):
        self.max_per_second = max_per_second
        self._lock = threading.Lock()
        self._tokens = max_per_second
        self._last_refill = time.monotonic()

    def acquire(self):
        """Block until a token is available."""
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(
                    self.max_per_second,
                    self._tokens + elapsed * self.max_per_second,
                )
                self._last_refill = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            time.sleep(0.05)


# ---------------------------------------------------------------------------
# Geometry helpers (ported from Dart)
# ---------------------------------------------------------------------------
def _rad(deg: float) -> float:
    return deg * math.pi / 180


def _deg(rad: float) -> float:
    return rad * 180 / math.pi


def _round1(v: float) -> float:
    return round(v, 1)


def bearing_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compass bearing (0-360) from point 1 to point 2."""
    rlat1 = _rad(lat1)
    rlat2 = _rad(lat2)
    dlon = _rad(lon2 - lon1)
    x = math.sin(dlon) * math.cos(rlat2)
    y = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlon)
    return (_deg(math.atan2(x, y)) + 360) % 360


def point_to_segment_distance(px, py, ax, ay, bx, by) -> float:
    """Perpendicular distance (degree-units) from point P to segment A-B."""
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def way_min_distance_m(geometry: list, lat: float, lng: float) -> float:
    """Minimum distance in metres from any segment of the way to the point."""
    min_dist = float("inf")
    for i in range(len(geometry) - 1):
        n1 = geometry[i]
        n2 = geometry[i + 1]
        dist_deg = point_to_segment_distance(
            lng, lat, n1["lon"], n1["lat"], n2["lon"], n2["lat"]
        )
        dist_m = dist_deg * 111320
        if dist_m < min_dist:
            min_dist = dist_m
    return min_dist


def closest_segment_on_way(geometry: list, lat: float, lng: float):
    """Return (node_before, node_after) of the segment closest to the point."""
    best_dist = float("inf")
    best_n1 = None
    best_n2 = None
    for i in range(len(geometry) - 1):
        n1 = geometry[i]
        n2 = geometry[i + 1]
        dist_deg = point_to_segment_distance(
            lng, lat, n1["lon"], n1["lat"], n2["lon"], n2["lat"]
        )
        dist_m = dist_deg * 111320
        if dist_m < best_dist:
            best_dist = dist_m
            best_n1 = n1
            best_n2 = n2
    return best_n1, best_n2


# ---------------------------------------------------------------------------
# Overpass API helpers
# ---------------------------------------------------------------------------
def query_overpass(session: requests.Session, lat: float, lng: float,
                   rate_limiter: RateLimiter):
    """Query the Overpass API for nearby road ways. Returns parsed JSON or
    None on failure."""
    query = (
        f'[out:json][timeout:15];\n'
        f'way(around:{SEARCH_RADIUS},{lat},{lng})["highway"~"{HIGHWAY_CLASSES}"];\n'
        f'out geom;\n'
    )
    rate_limiter.acquire()
    try:
        resp = session.post(OVERPASS_URL, data={"data": query}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as exc:
        print(f"    ⚠  Error querying ({lng}, {lat}): {exc}")
        return None


def extract_closest_road(overpass_response, lat: float, lng: float) -> dict | None:
    """Parse Overpass response and return the single closest road, or None.

    When a road is found, every property key is always present — missing OSM
    tags are represented as null so the schema is self-documenting.
    """
    if not overpass_response:
        return None

    elements = overpass_response.get("elements", [])
    ways = [e for e in elements if e.get("type") == "way"]

    scored = []
    for way in ways:
        geom = way.get("geometry", [])
        if len(geom) < 2:
            continue
        dist = way_min_distance_m(geom, lat, lng)
        scored.append((dist, way))

    if not scored:
        return None

    dist, way = min(scored, key=lambda x: x[0])
    tags = way.get("tags", {})
    geom = way.get("geometry", [])

    n1, n2 = closest_segment_on_way(geom, lat, lng)
    heading = bearing_between(n1["lat"], n1["lon"], n2["lat"], n2["lon"])
    is_oneway = tags.get("oneway") in ("yes", "1", "true")

    names = {}
    for key, val in tags.items():
        if key in NAME_KEYS or key.startswith("name:"):
            names[key] = val

    return {
        "osm_way_id": way["id"],
        "road_class": tags.get("highway", "unknown"),
        "road_ref": tags.get("ref"),
        "int_ref": tags.get("int_ref"),
        "names": names or None,
        "maxspeed_tag": tags.get("maxspeed"),
        "oneway": is_oneway,
        "distance": _round1(dist),
        "heading": _round1(heading),
        "heading_reverse": None if is_oneway else _round1((heading + 180) % 360),
    }


# ---------------------------------------------------------------------------
# Feature processing
# ---------------------------------------------------------------------------
def enrich_feature(session: requests.Session, feature: dict,
                   rate_limiter: RateLimiter) -> dict:
    """Enrich a single GeoJSON feature with OSM road data."""
    coords = feature.get("geometry", {}).get("coordinates", [])
    if len(coords) < 2:
        print(f"    ⚠  Skipping feature with invalid coordinates: {coords}")
        feature["properties"]["osm_road"] = None
        return feature

    lng, lat = coords[0], coords[1]
    response = query_overpass(session, lat, lng, rate_limiter)
    feature["properties"]["osm_road"] = extract_closest_road(response, lat, lng)
    return feature


def process_batch(features: list, batch_index: int, max_workers: int,
                  rate_limiter: RateLimiter) -> list:
    """Process a whole batch using a thread pool while respecting the rate
    limit."""
    session = requests.Session()
    enriched = [None] * len(features)

    def _worker(idx, feat):
        return idx, enrich_feature(session, feat, rate_limiter)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_worker, i, f): i for i, f in enumerate(features)
        }
        for future in as_completed(futures):
            try:
                idx, feat = future.result()
                enriched[idx] = feat
            except Exception as exc:
                orig_idx = futures[future]
                print(f"    ⚠  Unhandled error for feature index {orig_idx}: {exc}")
                enriched[orig_idx] = features[orig_idx]
                enriched[orig_idx]["properties"]["osm_road"] = None

    session.close()
    return enriched


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def batch_dir_for(output_file: str) -> str:
    """Deterministic temporary batch directory derived from the output path."""
    parent = os.path.dirname(output_file) or "."
    stem = os.path.splitext(os.path.basename(output_file))[0]
    return os.path.join(parent, f".{stem}_batches")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Enrich a GeoJSON point file with the nearest Overpass road."
    )
    parser.add_argument("input_file", help="Path to the input GeoJSON file (points)")
    parser.add_argument("output_file", help="Path to the output GeoJSON file")
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help=f"Features per batch (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--max-workers", type=int, default=DEFAULT_MAX_WORKERS,
        help=f"Concurrent request threads (default: {DEFAULT_MAX_WORKERS})",
    )
    parser.add_argument(
        "--requests-per-second", type=float, default=DEFAULT_REQUESTS_PER_SECOND,
        help=f"Max Overpass requests per second (default: {DEFAULT_REQUESTS_PER_SECOND})",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_file = args.input_file
    output_file = args.output_file
    batch_size = args.batch_size
    max_workers = args.max_workers

    rate_limiter = RateLimiter(args.requests_per_second)
    batches_dir = batch_dir_for(output_file)
    os.makedirs(batches_dir, exist_ok=True)

    print(f"Reading {input_file} …")
    with open(input_file, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    features = data["features"]
    total = len(features)
    total_batches = (total + batch_size - 1) // batch_size

    print(f"Total features : {total}")
    print(f"Batch size     : {batch_size}")
    print(f"Max workers    : {max_workers}")
    print(f"Req/s limit    : {args.requests_per_second}")
    print(f"Total batches  : {total_batches}")
    print(f"Batch dir      : {batches_dir}")
    print()

    overall_start = time.time()

    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, total)
        batch_file = os.path.join(batches_dir, f"batch_{batch_idx:04d}.geojson")

        if os.path.exists(batch_file):
            print(
                f"[{batch_idx + 1}/{total_batches}] {batch_file} already exists — skipping"
            )
            continue

        print(
            f"[{batch_idx + 1}/{total_batches}] Processing features {start}–{end - 1} …"
        )
        batch_start = time.time()

        batch_features = features[start:end]
        enriched_features = process_batch(
            batch_features, batch_idx, max_workers, rate_limiter
        )

        batch_geojson = {
            "type": "FeatureCollection",
            "features": enriched_features,
        }
        with open(batch_file, "w", encoding="utf-8") as fh:
            json.dump(batch_geojson, fh, ensure_ascii=False)

        elapsed = time.time() - batch_start
        total_elapsed = time.time() - overall_start
        batches_done = batch_idx + 1
        avg_per_batch = total_elapsed / batches_done
        remaining = avg_per_batch * (total_batches - batches_done)

        print(
            f"    ✓ Saved {batch_file}  ({len(enriched_features)} features, "
            f"{elapsed:.1f}s this batch, ~{remaining / 60:.0f} min remaining)"
        )

    # ------------------------------------------------------------------
    # Merge all batches into the final output file
    # ------------------------------------------------------------------
    print()
    print("Merging batches …")
    all_features = []
    for batch_idx in range(total_batches):
        batch_file = os.path.join(batches_dir, f"batch_{batch_idx:04d}.geojson")
        with open(batch_file, "r", encoding="utf-8") as fh:
            batch_data = json.load(fh)
        all_features.extend(batch_data["features"])

    merged = {"type": "FeatureCollection", "features": all_features}
    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False)

    print(f"✓ Wrote {len(all_features)} features to {output_file}")

    # ------------------------------------------------------------------
    # Clean up temporary batch directory
    # ------------------------------------------------------------------
    shutil.rmtree(batches_dir)
    print(f"✓ Removed temporary batch directory {batches_dir}")
    print("Done!")


if __name__ == "__main__":
    main()
