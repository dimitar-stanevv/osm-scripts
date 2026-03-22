# csv_to_single_geojson

Convert SCDB CSV files directly into a single combined GeoJSON file.

## What it does

Reads a folder of CSV files from the SCDB speed-camera database export, classifies each file by camera type based on its filename, enriches features with type and speed-limit properties, and writes everything into a single GeoJSON FeatureCollection.

This script replaces the previous three-step pipeline (`csv_to_geojson` → `combine_dataset` → `combine_scdb_dataset_single`) with a single command.

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

### Camera-type classification

Files are classified by their filename into four camera types:

| Filename pattern | Assigned `type` | Extra properties |
|------------------|-----------------|------------------|
| `SCDB_Redlight_<N>.csv` | `combined_cam` | `speedLimit`, `speed_limit` |
| `SCDB_Speed_<N>.csv` | `speed_cam` | `speedLimit`, `speed_limit`, `isVariable=false` |
| `SCDB_Speed_variable.csv` | `speed_cam` | `speedLimit=null`, `speed_limit=null`, `isVariable=true` |
| `SCDB_Redlight.csv` | `redlight_cam` | — |
| `SCDB_Tunnel.csv` | `tunnel_cam` | — |

CSV files that don't match any pattern are skipped and reported in the output.

## Prerequisites

- Python 3.8+
- No external dependencies (uses only the standard library)

## Usage

Both `--input` and `--output` are required:

```
python csv_to_single_geojson.py --input <FOLDER> --output <FILE>
```

| Argument   | Description                                |
|------------|--------------------------------------------|
| `--input`  | Path to folder containing SCDB CSV files   |
| `--output` | Path to the output GeoJSON file            |

### Example

```bash
python csv_to_single_geojson/csv_to_single_geojson.py \
    --input data/SCDB_CSV \
    --output data/all_cams.geojson
```

## Output format

A single GeoJSON FeatureCollection of Point features. Every feature has at minimum:

| Field         | Type   | Description                                              |
|---------------|--------|----------------------------------------------------------|
| `id`          | string | Cleaned numeric ID (digits only)                         |
| `description` | string | Description text from the CSV                            |
| `type`        | string | Camera type (`combined_cam`, `speed_cam`, `redlight_cam`, `tunnel_cam`) |

Features of type `combined_cam` and `speed_cam` additionally have:

| Field         | Type       | Description                                              |
|---------------|------------|----------------------------------------------------------|
| `speedLimit`  | int / null | Speed limit parsed from filename (`null` for variable)   |
| `speed_limit` | int / null | Same value, snake_case alias                             |

Features of type `speed_cam` additionally have:

| Field        | Type | Description                                     |
|--------------|------|-------------------------------------------------|
| `isVariable` | bool | `true` for entries from the variable-speed file  |
