#!/usr/bin/env python3
"""
Reverse-geocode every feature in a GeoJSON file using the Mapbox Geocoding
batch API.  Adds a `rev_geocode` object and a `country` property to each
feature's properties.

Processes in resumable batches, then auto-merges into the output file and
cleans up the temporary batch directory.
"""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _REPO_ROOT / "config.json"

BATCH_API_URL = "https://api.mapbox.com/search/geocode/v6/batch"

DEFAULT_BATCH_SIZE = 1000  # Mapbox batch API max
DEFAULT_REQUESTS_PER_MINUTE = 500
MAX_RETRIES = 3


def _load_config() -> dict:
    if not _CONFIG_PATH.is_file():
        print(f"Error: config file not found at {_CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


_CONFIG = _load_config()
MAPBOX_TOKEN = _CONFIG.get("mapbox_access_token", "")

if not MAPBOX_TOKEN:
    print(
        "Error: mapbox_access_token is empty in config.json. "
        "Set it to a valid Mapbox access token.",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Rate limiter (simple token-bucket)
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, max_per_minute: float):
        self._interval = 60.0 / max_per_minute
        self._last = 0.0

    def acquire(self):
        now = time.monotonic()
        wait = self._interval - (now - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()


# ---------------------------------------------------------------------------
# Mapbox batch reverse-geocode helpers
# ---------------------------------------------------------------------------
def _build_batch_body(features: list[dict]) -> list[dict]:
    """Build the JSON body for a Mapbox batch reverse-geocode request."""
    body = []
    for feat in features:
        coords = feat.get("geometry", {}).get("coordinates", [])
        if len(coords) >= 2:
            body.append({"longitude": coords[0], "latitude": coords[1]})
        else:
            body.append({"longitude": 0, "latitude": 0})
    return body


def _send_batch(session: requests.Session, body: list[dict],
                rate_limiter: RateLimiter) -> dict | None:
    """POST a batch request with retries for 429 (rate-limit) responses."""
    for attempt in range(1, MAX_RETRIES + 1):
        rate_limiter.acquire()
        try:
            resp = session.post(
                BATCH_API_URL,
                params={"access_token": MAPBOX_TOKEN},
                json=body,
                timeout=120,
            )
            if resp.status_code == 429:
                wait = 2 ** attempt
                print(f"    ⚠  Rate-limited (429). Retrying in {wait}s …")
                time.sleep(wait)
                continue
            if resp.status_code == 422:
                print(
                    f"    ⚠  Unprocessable request (422): {resp.text}",
                    file=sys.stderr,
                )
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            print(f"    ⚠  Request error (attempt {attempt}/{MAX_RETRIES}): {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)

    print("    ⚠  Batch failed after all retries.", file=sys.stderr)
    return None


def _extract_rev_geocode(feature_collection: dict) -> tuple[dict | None, str | None]:
    """Extract rev_geocode and country from a single reverse-geocode result."""
    feats = feature_collection.get("features", [])
    if not feats:
        return None, None

    props = feats[0].get("properties", {})
    context = props.get("context", {})

    postcode_obj = context.get("postcode")
    country_obj = context.get("country")

    rev_geocode = {
        "feature_type": props.get("feature_type"),
        "full_address": props.get("full_address"),
        "name": props.get("name"),
        "postcode": postcode_obj.get("name") if postcode_obj else None,
    }

    country = country_obj.get("country_code") if country_obj else None
    return rev_geocode, country


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------
def process_batch(session: requests.Session, features: list[dict],
                  rate_limiter: RateLimiter) -> list[dict]:
    """Reverse-geocode a batch of features and attach results."""
    body = _build_batch_body(features)
    response = _send_batch(session, body, rate_limiter)

    results = response.get("batch", []) if response else []

    for i, feat in enumerate(features):
        if i < len(results):
            rev_geocode, country = _extract_rev_geocode(results[i])
        else:
            rev_geocode, country = None, None

        feat["properties"]["rev_geocode"] = rev_geocode
        feat["properties"]["country"] = country

    return features


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def batch_dir_for(output_file: str) -> str:
    parent = os.path.dirname(output_file) or "."
    stem = os.path.splitext(os.path.basename(output_file))[0]
    return os.path.join(parent, f".{stem}_batches")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Reverse-geocode a GeoJSON file via the Mapbox batch API."
    )
    parser.add_argument("input_file", help="Path to the input GeoJSON file")
    parser.add_argument("output_file", help="Path to the output GeoJSON file")
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help=f"Features per batch (default: {DEFAULT_BATCH_SIZE}, max 1000)",
    )
    parser.add_argument(
        "--requests-per-minute", type=float, default=DEFAULT_REQUESTS_PER_MINUTE,
        help=f"Max batch API requests per minute (default: {DEFAULT_REQUESTS_PER_MINUTE})",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_file = args.input_file
    output_file = args.output_file
    batch_size = min(args.batch_size, 1000)

    rate_limiter = RateLimiter(args.requests_per_minute)
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
    print(f"Req/min limit  : {args.requests_per_minute}")
    print(f"Total batches  : {total_batches}")
    print(f"Batch dir      : {batches_dir}")
    print()

    session = requests.Session()
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
            session, batch_features, rate_limiter
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

    session.close()

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
