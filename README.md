# osm-scripts
Scripts for querying OpenStreetMaps for data

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
