# fetch_section_control

Fetch **average-speed enforcement** (section control) data from [OpenStreetMap](https://www.openstreetmap.org/) via the Overpass API and export it as a GeoJSON file.

## What it does

The script queries OSM for relations tagged `type=enforcement` + `enforcement=average_speed` within a given country and converts them into a GeoJSON FeatureCollection. Each feature contains:

- **Geometry** — the controlled road section as a LineString (or MultiLineString when ways cannot be joined end-to-end).
- **Properties** — `maxspeed`, camera device locations, from/to entry points, computed section length in metres, road reference and name, highway class, and the full OSM relation tags.

## Prerequisites

- Python 3.8+
- [requests](https://pypi.org/project/requests/)
- The repo-level `config.json` must exist (see the root README)

Install the dependency:

```
pip install requests
```

## Usage

Both `--country` and `--output` are required:

```
python fetch_section_control.py --country <CODE> --output <FILE>
```

| Argument    | Description                                           |
|-------------|-------------------------------------------------------|
| `--country` | ISO 3166-1 alpha-2 country code (e.g. `BG`, `DE`, `AT`) |
| `--output`  | Path to the output GeoJSON file                       |

### Examples

```bash
# Bulgaria
python fetch_section_control.py --country BG --output section_control_BG.geojson

# Germany
python fetch_section_control.py --country DE --output data/section_control_DE.geojson
```

## Output format

The output is a standard [GeoJSON FeatureCollection](https://datatracker.ietf.org/doc/html/rfc7946). Each feature's `properties` object contains:

| Field              | Type            | Description                                    |
|--------------------|-----------------|------------------------------------------------|
| `osm_relation_id`  | integer         | OSM relation ID                                |
| `enforcement`      | string          | Always `"average_speed"`                       |
| `maxspeed`         | string or null  | Speed limit on the section (e.g. `"140"`)      |
| `road_ref`         | string or null  | Road reference number (e.g. `"AM1"`)           |
| `road_names`       | object          | Name tags from the road (`name`, `name:en`, …) |
| `highway_class`    | string or null  | OSM highway classification (e.g. `"motorway"`) |
| `from`             | [lon, lat] or null | Start point of the section                  |
| `to`               | [lon, lat] or null | End point of the section                    |
| `devices`          | array of [lon, lat] | Camera/device positions                    |
| `section_length_m` | float           | Computed length of the section in metres       |
| `relation_tags`    | object          | All OSM tags on the enforcement relation       |
