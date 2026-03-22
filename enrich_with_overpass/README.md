# enrich_with_overpass

Enriches a GeoJSON point file by querying the Overpass API for the nearest road to each point. Processes features in resumable batches with concurrent requests and automatic rate limiting.

## Usage

```bash
python enrich_with_overpass/enrich_with_overpass.py <input_file> <output_file> [options]
```

Both `input_file` and `output_file` are required positional arguments.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--batch-size` | 100 | Features per batch |
| `--max-workers` | 10 | Concurrent request threads |
| `--requests-per-second` | 9 | Max Overpass requests per second (540/min) |

### Example

```bash
python enrich_with_overpass/enrich_with_overpass.py \
  data/speed_cams.geojson \
  data/speed_cams_enriched.geojson \
  --batch-size 200 --max-workers 5
```

## How it works

1. Reads the input GeoJSON FeatureCollection (point features).
2. For each point, queries the Overpass API for nearby road ways within 30 m, filtered to standard highway classes.
3. Selects the single closest road and computes heading from the nearest segment.
4. Writes intermediate batch files to a temporary directory (`.{stem}_batches/`) so processing is resumable — existing batch files are skipped on re-run.
5. Merges all batches into the final output file and removes the temporary directory.

## Output properties

Each feature gains an `osm_road` object in its properties. For the closest road found, it contains:

| Property | Type | Description |
|----------|------|-------------|
| `osm_way_id` | int | OSM way ID |
| `road_class` | string | Highway tag value (e.g. `primary`, `residential`) |
| `road_ref` | string\|null | Road reference number (`ref` tag) |
| `int_ref` | string\|null | International reference (`int_ref` tag) |
| `names` | object | All name-related tags (`name`, `name:*`, `int_name`, etc.) |
| `maxspeed_tag` | string\|null | Speed limit from the `maxspeed` tag |
| `oneway` | bool | Whether the road is one-way |
| `distance` | float | Distance in metres from the point to the nearest segment |
| `heading` | float | Compass bearing (0–360) along the nearest segment |
| `heading_reverse` | float\|null | Reverse bearing (null if one-way) |

If no road is found within the search radius, `osm_road` is `null`. When a road is found, all property keys are always present — missing OSM tags are explicitly set to `null`.
