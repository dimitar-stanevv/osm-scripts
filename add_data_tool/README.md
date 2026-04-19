# add_data_tool

Interactive web tool for adding points on a Mapbox map and exporting them as an
enriched GeoJSON FeatureCollection.

For each added point, the tool performs two server-side enrichments:

1. **Mapbox reverse-geocode** — produces a `rev_geocode` object
   (`feature_type`, `full_address`, `name`, `postcode`) and a 2-letter
   `country` code, matching the shape emitted by `reverse_geocode.py`.
2. **Overpass nearest-road lookup** — produces an `osm_road` object
   (`osm_way_id`, `road_class`, `road_ref`, `int_ref`, `names`,
   `maxspeed_tag`, `oneway`, `distance`, `heading`, `heading_reverse`),
   matching the shape emitted by `enrich_with_overpass.py`.

## Install

```bash
pip install -r add_data_tool/requirements.txt
```

This tool reuses helpers from `reverse_geocode/` and `enrich_with_overpass/`
by loading them directly from their file paths — no additional setup needed.

## Run

```bash
python add_data_tool/add_data_tool.py
```

The tool reads the Mapbox token and Overpass URL from the top-level
`config.json` (same as `reverse_geocode.py` and `enrich_with_overpass.py`).
A browser window opens automatically at `http://127.0.0.1:5173/`.

Optional flags:

- `--host` (default `127.0.0.1`)
- `--port` (default `5173`)
- `--no-browser` — don't auto-open the browser

## Usage

1. Click anywhere on the map to drop a numbered marker. Enrichment starts
   immediately and the side panel updates when results arrive.
2. Drag a marker to relocate it — it is automatically re-enriched.
3. For each point, fill in the optional fields in the side panel:
   - **Type** — one of `speed_cam`, `combined_cam`, `redlight_cam`.
   - **Speed** — integer km/h, only shown for `speed_cam` / `combined_cam`,
     optional; omitted from export when empty.
   - **Desc.** — free-form description, optional; omitted from export when
     empty.
4. Click **Export** to download a GeoJSON FeatureCollection of all points.

## Output schema

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "1734523456789",
      "geometry": { "type": "Point", "coordinates": [13.405, 52.52] },
      "properties": {
        "description": "optional text",
        "type": "speed_cam",
        "speed_limit": 50,
        "rev_geocode": {
          "feature_type": "address",
          "full_address": "…",
          "name": "…",
          "postcode": "10115"
        },
        "country": "DE",
        "osm_road": {
          "osm_way_id": 12345678,
          "road_class": "primary",
          "road_ref": "B1",
          "int_ref": null,
          "names": { "name": "…" },
          "maxspeed_tag": "50",
          "oneway": false,
          "distance": 4.2,
          "heading": 87.3,
          "heading_reverse": 267.3
        }
      }
    }
  ]
}
```

`rev_geocode`, `country`, and `osm_road` are produced by the same helper
functions as the batch scripts, so the output is schema-compatible with the
rest of the pipeline. Any of these three may be `null` if the corresponding
API call failed or returned no match.
