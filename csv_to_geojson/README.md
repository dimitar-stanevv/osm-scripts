# csv_to_geojson

Convert CSV files containing point data into [GeoJSON](https://datatracker.ietf.org/doc/html/rfc7946) FeatureCollections.

## What it does

Reads every `.csv` file in an input folder, parses each row as a geographic point, and writes one GeoJSON file per CSV into an output folder.

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

Example row:

```
5.13214,52.05511,"SectionControl in Rtg. Den Haag","[5212]"
```

## Prerequisites

- Python 3.8+
- No external dependencies (uses only the standard library)

## Input file naming

The input CSV files should use the exact filenames from the `data/SCDB_CSV` folder (the speed-camera database export). Each CSV is typically named with a two-letter country code — e.g. `AT.csv`, `BG.csv`, `NL.csv`. The script produces one `.geojson` file per input CSV, keeping the same stem (`AT.csv` → `AT.geojson`), so matching the source filenames ensures consistent, traceable output.

## Usage

Both `--input` and `--output` are required:

```
python csv_to_geojson.py --input <FOLDER> --output <FOLDER>
```

| Argument   | Description                                |
|------------|--------------------------------------------|
| `--input`  | Path to folder containing CSV files        |
| `--output` | Path to output folder for GeoJSON files    |

### Example

```bash
python csv_to_geojson.py --input data/SCDB_CSV --output data/geojson
```

## Output format

Each output file is a standard GeoJSON FeatureCollection of Point features. Each feature's `properties` object contains:

| Field         | Type   | Description                              |
|---------------|--------|------------------------------------------|
| `id`          | string | Cleaned numeric ID (digits only)         |
| `description` | string | Description text from the CSV            |
