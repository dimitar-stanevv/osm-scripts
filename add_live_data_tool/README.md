# add_live_data_tool

Interactive web tool for adding mock **live-event** points on a Mapbox map and
exporting them as a GeoJSON FeatureCollection in the live-events schema
(see [`live_events.md`](../live_events.md)).

Use it to seed test data for the live-events integration without depending on
real Waze / OpenWebNinja traffic.

For each added point, the tool performs the same two server-side enrichments
as `add_data_tool`:

1. **Mapbox reverse-geocode** — produces a `reverse_geocode` object
   (`feature_type`, `full_address`, `name`, `postcode`) and a 2-letter
   `country` code.
2. **Overpass nearest-road lookup** — produces an `osm_road` object
   (`osm_way_id`, `road_class`, `road_ref`, `int_ref`, `names`,
   `maxspeed_tag`, `oneway`, `distance`, `heading`, `heading_reverse`).

Internally it reuses the helpers from `add_data_tool/add_data_tool.py`, so
both tools share the exact same enrichment + road-snapping pipeline.

## Install

```bash
pip install -r add_live_data_tool/requirements.txt
```

## Run

```bash
python add_live_data_tool/add_live_data_tool.py
```

The tool reads the Mapbox token and Overpass URL from the top-level
`config.json`. A browser window opens automatically at
`http://127.0.0.1:5174/`. The default port is `5174` so this can run
alongside `add_data_tool` (which uses `5173`).

Optional flags:

- `--host` (default `127.0.0.1`)
- `--port` (default `5174`)
- `--no-browser` — don't auto-open the browser

## Usage

1. Click anywhere on the map to drop a numbered marker. Enrichment starts
   immediately and the side panel updates when results arrive.
2. Drag a marker to relocate it — it is automatically re-enriched (the
   `id` and `published_at` stay frozen at the original add time).
3. For each point, pick a danger **Type** from the dropdown. Supported
   types (from [`live_events.md`](../live_events.md)):
   - `hazard_pothole`
   - `hazard_construction`
   - `hazard_object_on_road`
   - `hazard_vehicle_on_road`
   - `hazard_accident`
   - `hazard_other`
   - `police` (default)
   - `police_mobile_camera`
   - `road_closure`
4. Click **Export** to download a GeoJSON FeatureCollection of all points.
   Paste the resulting features into the `points_live` array of the
   `/dangers` response.

## Output schema

Each feature follows the live-events schema documented in
[`live_events.md`](../live_events.md):

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [26.50927, 42.4793] },
      "properties": {
        "id": "1776590271114",
        "type": "police",
        "published_at": 1776590271114,
        "country": "BG",
        "reverse_geocode": {
          "feature_type": "address",
          "full_address": "…",
          "name": "…",
          "postcode": "…"
        },
        "osm_road": {
          "osm_way_id": 12345678,
          "road_class": "primary",
          "road_ref": "I-8",
          "int_ref": null,
          "names": { "name": "…" },
          "maxspeed_tag": "90",
          "oneway": false,
          "distance": 3.1,
          "heading": 87.3,
          "heading_reverse": 267.3
        }
      }
    }
  ]
}
```

Notes:

- `id` is the marker's creation timestamp (milliseconds since epoch) as a
  string, and `published_at` is the same timestamp as a number.
- Both stay frozen at the moment the marker was added — dragging the
  marker only updates geometry and re-enriches.
- `country`, `reverse_geocode`, or `osm_road` may be `null` if the
  corresponding API call failed or returned no match.
