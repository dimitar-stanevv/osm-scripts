# combine_scdb_dataset_single

Combine four camera-type GeoJSON files into a single GeoJSON file with a `type` property on every feature.

## What it does

Reads a folder that must contain **exactly** these four files (produced by [combine_dataset](../combine_dataset/)):

| Input file              | Assigned `type`  |
|-------------------------|------------------|
| `combined_cams.geojson` | `combined_cam`   |
| `redlight_cams.geojson` | `redlight_cam`   |
| `speed_cams.geojson`    | `speed_cam`      |
| `tunnel_cams.geojson`   | `tunnel_cam`     |

All features are merged into a single `FeatureCollection`. If the folder is missing any of the four files or contains extra files the script exits with a red error message.

### Added properties

Every feature gains:

| Field  | Type   | Description                                  |
|--------|--------|----------------------------------------------|
| `type` | string | Camera type (`combined_cam`, `redlight_cam`, `speed_cam`, `tunnel_cam`) |

Features from **combined_cams** and **speed_cams** also gain:

| Field         | Type       | Description                                          |
|---------------|------------|------------------------------------------------------|
| `speed_limit` | int / null | Speed limit copied from the existing `speedLimit` property |

### Large-file handling

The script streams features to the output file one at a time and processes input files sequentially, so only one source file is held in memory at any point. This keeps peak memory usage manageable for inputs of 50–100 MB per file.

## Prerequisites

- Python 3.8+
- No external dependencies (uses only the standard library)

## Usage

Both `--input` and `--output` are required:

```
python combine_scdb_dataset_single.py --input <FOLDER> --output <FILE>
```

| Argument   | Description                                                    |
|------------|----------------------------------------------------------------|
| `--input`  | Path to folder containing the four camera GeoJSON files        |
| `--output` | Path to the output GeoJSON file (parent dirs created if needed)|

### Example

```bash
python combine_scdb_dataset_single/combine_scdb_dataset_single.py \
    --input data/combined \
    --output data/all_cams.geojson
```
