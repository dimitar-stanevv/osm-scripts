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
├── csv_to_geojson/
│   ├── csv_to_geojson.py                # Script: CSV point data → GeoJSON
│   └── README.md
├── combine_dataset/
│   ├── combine_dataset.py               # Script: merge per-speed-limit GeoJSON files
│   └── README.md
├── enrich_with_overpass/
│   ├── enrich_with_overpass.py           # Script: enrich points with nearest road data
│   └── README.md
├── count_features/
│   ├── count_features.py                # Script: count features in GeoJSON / CSV files
│   └── README.md
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

### csv_to_geojson

Converts CSV files with point data (`lng,lat,"description","id"`) into GeoJSON FeatureCollections. One output file per input CSV.

```bash
python csv_to_geojson/csv_to_geojson.py --input data/SCDB_CSV --output data/geojson
```

Both `--input` and `--output` are required.

### combine_dataset

Merges per-speed-limit SCDB GeoJSON files (produced by `csv_to_geojson`) into combined datasets grouped by camera type. Outputs four files: `combined_cams.geojson`, `speed_cams.geojson`, `redlight_cams.geojson`, `tunnel_cams.geojson`. Adds `speedLimit` and (for speed cams) `isVariable` properties parsed from the source filenames.

```bash
python combine_dataset/combine_dataset.py --input data/SCDB_geojson_21_mar_2026 --output data/combined
```

Both `--input` and `--output` are required.

### enrich_with_overpass

Enriches a GeoJSON point file by querying the Overpass API for the nearest road to each point. Adds an `osm_road` object to each feature's properties containing the closest road's OSM way ID, road class, ref, names, maxspeed, heading, and distance. Processes in resumable batches with concurrent requests and rate limiting.

```bash
python enrich_with_overpass/enrich_with_overpass.py data/speed_cams.geojson data/speed_cams_enriched.geojson
```

Both positional arguments (`input_file` and `output_file`) are required. Optional flags: `--batch-size`, `--max-workers`, `--requests-per-second`.

### count_features

Counts features in GeoJSON and CSV files within a given folder. For GeoJSON files, counts the number of features in the FeatureCollection. For CSV files, counts the number of data rows (excluding the header). Prints a summary table with per-file counts and a total.

```bash
python count_features/count_features.py --input data/
```

`--input` is required.

## Adding a new script

1. Create a new folder at the repo root (e.g. `fetch_speed_cameras/`).
2. Load the Overpass URL from `config.json` — do not hardcode it.
3. Accept `--country` and `--output` via argparse with `required=True`.
4. Validate the country code (two-letter ISO 3166-1 alpha-2).
5. Write output as a GeoJSON FeatureCollection.
6. Add a `README.md` in the script folder documenting usage and output properties.
