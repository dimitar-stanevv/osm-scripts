# csv_section_to_single_geojson

Convert SCDB section-control CSV files into a single combined GeoJSON file.

## What it does

Reads a folder of CSV files from the SCDB section-control database export, classifies each file by point role (start, mid, end) based on its filename, enriches features with max speed and role properties, and writes everything into a single GeoJSON FeatureCollection.

### Expected CSV format

Each row has four columns (no header row):

```
lng,lat,"description","id"
```

| Column | Description |
|--------|-------------|
| 1 | Longitude (decimal) |
| 2 | Latitude (decimal) |
| 3 | Free-text description |
| 4 | Point ID — may contain brackets, dashes, or other noise; only digits are kept |

### Point-role classification

Files are classified by their filename into three point roles:

| Filename pattern | Assigned `type` | Extra properties |
|------------------|-----------------|------------------|
| `SCDB_Section_<N>.csv` | `section_start` | `max_speed=<N>`, `is_variable=false` |
| `SCDB_Section_variable.csv` | `section_start` | `max_speed=null`, `is_variable=true` |
| `SCDB_Section_MID.csv` | `section_mid` | — |
| `SCDB_Section_End.csv` | `section_end` | — |

CSV files that don't match any pattern are skipped and reported in the output.

## Prerequisites

- Python 3.8+
- No external dependencies (uses only the standard library)

## Usage

Both `--input` and `--output` are required:

```
python csv_section_to_single_geojson.py --input <FOLDER> --output <FILE>
```

| Argument   | Description                                         |
|------------|-----------------------------------------------------|
| `--input`  | Path to folder containing SCDB section CSV files    |
| `--output` | Path to the output GeoJSON file                     |

### Example

```bash
python csv_section_to_single_geojson/csv_section_to_single_geojson.py \
    --input data/scdb_all_world_21_mar_2026/step0_csv \
    --output data/section_control.geojson
```

## Output format

A single GeoJSON FeatureCollection of Point features. Every feature has at minimum:

| Field         | Type   | Description                                              |
|---------------|--------|----------------------------------------------------------|
| `id`          | string | Cleaned numeric ID (digits only)                         |
| `description` | string | Description text from the CSV (empty if garbage)         |
| `type`        | string | Point role (`section_start`, `section_mid`, `section_end`) |

Features of type `section_start` additionally have:

| Field         | Type       | Description                                              |
|---------------|------------|----------------------------------------------------------|
| `max_speed`   | int / null | Speed limit parsed from filename (`null` for variable)   |
| `is_variable` | bool       | `true` for entries from the variable-speed file           |
