# combine_dataset

Merge per-speed-limit SCDB GeoJSON files into combined datasets grouped by camera type.

## What it does

Reads a folder of GeoJSON files produced by [csv_to_geojson](../csv_to_geojson/) and writes four output files:

| Output file            | Source files                        | Description                                            |
|------------------------|-------------------------------------|--------------------------------------------------------|
| `combined_cams.geojson`| `SCDB_Redlight_<N>.geojson`         | Red-light + speed combination cameras                  |
| `speed_cams.geojson`   | `SCDB_Speed_<N>.geojson`, `SCDB_Speed_variable.geojson` | Fixed and variable speed cameras    |
| `redlight_cams.geojson`| `SCDB_Redlight.geojson`             | Red-light-only cameras (straight copy)                 |
| `tunnel_cams.geojson`  | `SCDB_Tunnel.geojson`               | Tunnel cameras (straight copy)                         |

### Added properties

**Combined cams** — each feature gains:

| Field        | Type | Description                      |
|--------------|------|----------------------------------|
| `speedLimit` | int  | Speed limit parsed from filename |

**Speed cams** — each feature gains:

| Field        | Type    | Description                                      |
|--------------|---------|--------------------------------------------------|
| `speedLimit` | int / null | Speed limit parsed from filename (`null` for variable) |
| `isVariable` | bool    | `true` for entries from the variable-speed file   |

Files that don't match any of the four categories (e.g. `SCDB_Section_*`) are listed as skipped at the end of the run.

## Prerequisites

- Python 3.8+
- No external dependencies (uses only the standard library)

## Usage

Both `--input` and `--output` are required:

```
python combine_dataset.py --input <FOLDER> --output <FOLDER>
```

| Argument   | Description                                            |
|------------|--------------------------------------------------------|
| `--input`  | Path to folder containing SCDB GeoJSON files           |
| `--output` | Path to output folder for the combined GeoJSON files   |

### Example

```bash
python combine_dataset/combine_dataset.py \
    --input data/SCDB_geojson_21_mar_2026 \
    --output data/combined
```
