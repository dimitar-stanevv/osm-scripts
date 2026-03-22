# osm-scripts
Scripts for querying OpenStreetMaps for data

## Configuration

Create the `config.json` file in the root directory and set the needed config properties:

```
{
  "overpass_url": "OVERPASS_API_URL",
  "mapbox_access_token": "MAPBOX_ACCESS_TOKEN"
}
```

## Scripts

### fetch_section_control

Queries OSM for section-control (average-speed enforcement) relations within a given country and exports a GeoJSON FeatureCollection.

```bash
python fetch_section_control/fetch_section_control.py --country BG --output data/section_control_BG.geojson
```

### csv_to_geojson

Converts CSV point-data files into GeoJSON FeatureCollections. See [csv_to_geojson/README.md](csv_to_geojson/README.md) for details.

```bash
python csv_to_geojson/csv_to_geojson.py --input data/SCDB_CSV --output data/geojson
```

**Important:** the input CSV files must use the exact filenames from the `data/SCDB_CSV` folder (the speed-camera database export). The script converts each `.csv` file one-to-one into a `.geojson` file, preserving the stem of the filename, so consistent naming ensures the output files can be matched back to their source data.

### combine_scdb_dataset_single

Combines the four camera-type GeoJSON files (from [combine_dataset](combine_dataset/)) into a single GeoJSON file with a `type` property on every feature. See [combine_scdb_dataset_single/README.md](combine_scdb_dataset_single/README.md).

```bash
python combine_scdb_dataset_single/combine_scdb_dataset_single.py \
    --input data/combined --output data/all_cams.geojson
```

### country_stats

Analyzes a GeoJSON file and prints a per-country feature breakdown with flag emojis, counts, and bar charts. See [country_stats/README.md](country_stats/README.md).

```bash
python country_stats/country_stats.py data/speed_cams_geocoded.geojson
```

## Data directory

Generated and source data files live under `data/` and are git-ignored. The expected layout is:

```
data/
├── SCDB_CSV/          # Input CSVs from the speed-camera database
│   ├── AT.csv
│   ├── BG.csv
│   └── …
└── geojson/           # GeoJSON output from csv_to_geojson
    ├── AT.geojson
    ├── BG.geojson
    └── …
```
