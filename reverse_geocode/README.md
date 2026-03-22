# reverse_geocode

Reverse-geocodes every feature in a GeoJSON file using the Mapbox Geocoding batch API. Adds address context and country information to each feature's properties. Processes in resumable batches.

## Prerequisites

Set `mapbox_access_token` in the root `config.json` to a valid Mapbox access token.

## Usage

```bash
python reverse_geocode/reverse_geocode.py <input_file> <output_file> [options]
```

Both `input_file` and `output_file` are required positional arguments.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--batch-size` | 1000 | Features per batch (max 1000) |
| `--requests-per-minute` | 500 | Max batch API requests per minute |

### Example

```bash
python reverse_geocode/reverse_geocode.py \
  data/speed_cams.geojson \
  data/speed_cams_geocoded.geojson
```

## How it works

1. Reads the input GeoJSON FeatureCollection.
2. Splits features into batches of up to 1000 and sends each batch to the Mapbox batch reverse-geocode endpoint (`POST /search/geocode/v6/batch`).
3. Extracts address context from the first (most specific) result for each coordinate.
4. Writes intermediate batch files to a temporary directory (`.{stem}_batches/`) so processing is resumable — existing batch files are skipped on re-run.
5. Merges all batches into the final output file and removes the temporary directory.

## Output properties

Each feature gains two new properties:

### `rev_geocode` (object | null)

| Property | Type | Description |
|----------|------|-------------|
| `feature_type` | string | Type of the matched feature (e.g. `street`, `address`, `place`) |
| `full_address` | string | Full formatted address string |
| `name` | string | Name of the matched feature |
| `postcode` | string\|null | Postal code from the context hierarchy |

### `country` (string | null)

ISO 3166-1 alpha-2 country code extracted from the reverse-geocode context (e.g. `BG`, `DE`).

If the Mapbox API returns no results for a coordinate, both `rev_geocode` and `country` are set to `null`.
