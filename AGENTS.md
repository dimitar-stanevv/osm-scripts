# AGENTS.md — osm-scripts

## Project overview

A collection of Python scripts that query OpenStreetMap data via the Overpass API and export results as GeoJSON. Each script lives in its own folder under the repo root.

## Repository layout

```
osm-scripts/
├── config.json                          # Shared config (Overpass URL, etc.)
├── AGENTS.md                            # This file
├── README.md                            # Repo-level readme
├── .gitignore
└── fetch_section_control/
    ├── fetch_section_control.py          # Script: section control / average-speed enforcement
    └── README.md                         # Per-script documentation
```

## Shared configuration — `config.json`

All scripts read their Overpass API endpoint from the top-level `config.json`:

```json
{
  "overpass_url": "http://overpassdev.tolltracker.eu:12345/api/interpreter"
}
```

The URL points to a private Overpass instance, not the public `overpass-api.de`. When adding a new script, load this config instead of hardcoding the URL. See `fetch_section_control.py` for the loading pattern (resolve `Path(__file__).parent.parent / "config.json"`).

## Conventions

- **Language**: Python 3.8+. Only external dependency so far is `requests`.
- **One folder per script**: each script gets its own directory with a `README.md` explaining usage and output format.
- **CLI arguments**: use `argparse`. Required arguments should use `required=True` — no implicit defaults for file paths or country codes.
- **Country codes**: ISO 3166-1 alpha-2 (two uppercase letters). Validate with a regex before querying.
- **Output format**: GeoJSON FeatureCollection. Scripts write to the file path given via `--output`.
- **Data directory**: generated data files go in `data/` (git-ignored).
- **Coordinates**: GeoJSON order — `[longitude, latitude]`.
- **Geometry joining**: when building geometries from multiple OSM ways, attempt end-to-end joining; fall back to MultiLineString if segments are disjoint.

## Existing scripts

### fetch_section_control

Queries OSM for `type=enforcement` + `enforcement=average_speed` relations within a country. Outputs a GeoJSON FeatureCollection with road section geometry and properties including maxspeed, device locations, from/to points, and computed section length in metres.

```bash
python fetch_section_control/fetch_section_control.py --country BG --output data/section_control_BG.geojson
```

Both `--country` and `--output` are required.

## Adding a new script

1. Create a new folder at the repo root (e.g. `fetch_speed_cameras/`).
2. Load the Overpass URL from `config.json` — do not hardcode it.
3. Accept `--country` and `--output` via argparse with `required=True`.
4. Validate the country code (two-letter ISO 3166-1 alpha-2).
5. Write output as a GeoJSON FeatureCollection.
6. Add a `README.md` in the script folder documenting usage and output properties.
