#!/usr/bin/env python3
"""
Interactive live-event point-collection tool.

Serves a small Mapbox GL JS web UI that lets an operator click a map to add
mock live events for testing the live-events integration. Each added point
is enriched on-the-fly via the same Mapbox reverse-geocode + Overpass
nearest-road pipeline used by ``add_data_tool``.

The browser accumulates points and exports a GeoJSON FeatureCollection in
the live-events schema documented in ``live_events.md`` (each feature's
``properties`` carries ``id``, ``type``, ``published_at``, ``country``,
``reverse_geocode`` and ``osm_road``).
"""

import argparse
import importlib.util
import json
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template, request

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
# Reuse helpers from add_data_tool by loading it as a module — keeps the
# enrichment + snapping logic in a single place.
# ---------------------------------------------------------------------------
def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_adt = _load_module(
    "_add_data_tool", _REPO_ROOT / "add_data_tool" / "add_data_tool.py"
)

_mapbox_reverse_geocode = _adt._mapbox_reverse_geocode
_snap_to_closest_road = _adt._snap_to_closest_road
_query_overpass = _adt._query_overpass
_extract_closest_road = _adt._extract_closest_road
_overpass_rate_limiter = _adt._overpass_rate_limiter
_session = _adt._session


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__, template_folder="templates")
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
        description="Interactive map tool for adding mock live-event points."
    )
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5174,
                        help="Port to bind (default: 5174)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Do not auto-open a browser window.")
    return parser.parse_args()


def _open_browser(url: str):
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()


def main():
    args = parse_args()
    url = f"http://{args.host}:{args.port}/"
    print(f"🚨  add_live_data_tool running at {url}")
    print("    • Click on the map to add live-event points.")
    print("    • Each point is enriched via Mapbox reverse-geocode + Overpass.")
    print("    • Pick a danger type per point and export GeoJSON in the")
    print("      live-events schema (paste features into points_live).")
    print()
    if not args.no_browser:
        _open_browser(url)
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
