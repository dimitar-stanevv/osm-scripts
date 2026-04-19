#!/usr/bin/env python3
"""
Interactive point-collection tool.

Serves a small Mapbox GL JS web UI that lets an operator click a map to add
points. Each added point is enriched on-the-fly via:

  1. Mapbox reverse-geocode (v6 single-point endpoint) — produces `rev_geocode`
     and `country` matching the shape emitted by `reverse_geocode.py`.
  2. Overpass nearest-road lookup — produces `osm_road` matching the shape
     emitted by `enrich_with_overpass.py`.

The browser accumulates points and exports a GeoJSON FeatureCollection that
is schema-compatible with the batch scripts.
"""

import argparse
import importlib.util
import json
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Optional

import requests
from flask import Flask, jsonify, render_template, request

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
MAPBOX_TOKEN = _CONFIG.get("mapbox_access_token", "")
OVERPASS_URL = _CONFIG.get("overpass_url", "")

if not MAPBOX_TOKEN:
    print(
        "Error: mapbox_access_token is empty in config.json. "
        "Set it to a valid Mapbox access token.",
        file=sys.stderr,
    )
    sys.exit(1)

if not OVERPASS_URL:
    print("Error: overpass_url is empty in config.json.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Reuse sibling-script helpers by loading them as modules from their file
# paths (neither folder is a proper Python package).
# ---------------------------------------------------------------------------
def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_rg = _load_module(
    "_rg_helper", _REPO_ROOT / "reverse_geocode" / "reverse_geocode.py"
)
_ov = _load_module(
    "_ov_helper", _REPO_ROOT / "enrich_with_overpass" / "enrich_with_overpass.py"
)

_extract_rev_geocode = _rg._extract_rev_geocode
_query_overpass = _ov.query_overpass
_extract_closest_road = _ov.extract_closest_road
_way_min_distance_m = _ov.way_min_distance_m
_closest_segment_on_way = _ov.closest_segment_on_way
_RateLimiter = _ov.RateLimiter

# A generous per-process rate limiter shared across requests so rapid
# map-clicks don't flood Overpass.
_overpass_rate_limiter = _RateLimiter(max_per_second=20.0)

# Shared HTTP session for connection reuse.
_session = requests.Session()

MAPBOX_REVERSE_URL = "https://api.mapbox.com/search/geocode/v6/reverse"


def _mapbox_reverse_geocode(lng: float, lat: float):
    """Single-point reverse geocode via Mapbox v6. Returns (rev_geocode, country)."""
    try:
        resp = _session.get(
            MAPBOX_REVERSE_URL,
            params={
                "longitude": lng,
                "latitude": lat,
                "access_token": MAPBOX_TOKEN,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as exc:
        print(f"    ⚠  Mapbox reverse-geocode error ({lng}, {lat}): {exc}",
              file=sys.stderr)
        return None, None

    return _extract_rev_geocode(data)


def _snap_to_closest_road(overpass_response, lng: float, lat: float):
    """Project (lng, lat) onto the closest segment of the closest way in the
    Overpass response. Returns (snap_lng, snap_lat) or None if no way matched.
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
        scored.append((_way_min_distance_m(geom, lat, lng), way))

    if not scored:
        return None

    _, way = min(scored, key=lambda x: x[0])
    n1, n2 = _closest_segment_on_way(way["geometry"], lat, lng)

    ax, ay = n1["lon"], n1["lat"]
    bx, by = n2["lon"], n2["lat"]
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return ax, ay
    t = ((lng - ax) * dx + (lat - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return ax + t * dx, ay + t * dy


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder="templates")
# Reload templates from disk on every request so HTML/CSS tweaks don't require
# a server restart.
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True


@app.route("/")
def index():
    return render_template("index.html", mapbox_token=MAPBOX_TOKEN)


@app.route("/api/enrich", methods=["POST"])
def api_enrich():
    payload = request.get_json(silent=True) or {}
    try:
        lng = float(payload["lng"])
        lat = float(payload["lat"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Expected JSON body with numeric 'lng' and 'lat'."}), 400

    overpass_response = _query_overpass(
        _session, lat, lng, _overpass_rate_limiter
    )

    snap = _snap_to_closest_road(overpass_response, lng, lat)
    if snap is not None:
        snap_lng, snap_lat = snap
        snapped_payload = {"lng": snap_lng, "lat": snap_lat}
    else:
        snap_lng, snap_lat = lng, lat
        snapped_payload = None

    rev_geocode, country = _mapbox_reverse_geocode(snap_lng, snap_lat)
    osm_road = _extract_closest_road(overpass_response, snap_lat, snap_lng)

    return jsonify({
        "snapped": snapped_payload,
        "rev_geocode": rev_geocode,
        "country": country,
        "osm_road": osm_road,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Interactive map tool for adding and enriching points."
    )
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5173,
                        help="Port to bind (default: 5173)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Do not auto-open a browser window.")
    return parser.parse_args()


def _open_browser(url: str):
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()


def main():
    args = parse_args()
    url = f"http://{args.host}:{args.port}/"
    print(f"🗺  add_data_tool running at {url}")
    print("    • Click on the map to add points.")
    print("    • Each point is enriched via Mapbox reverse-geocode + Overpass.")
    print("    • Use the side panel to edit per-point fields and export GeoJSON.")
    print()
    if not args.no_browser:
        _open_browser(url)
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
