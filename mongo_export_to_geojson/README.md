# mongo_export_to_geojson

Wraps a MongoDB export JSON array back into a GeoJSON FeatureCollection. Strips the `_id` field that MongoDB adds to every document.

## Usage

```bash
python mongo_export_to_geojson/mongo_export_to_geojson.py --input data/cams.json --output data/cams.geojson
```

Both `--input` and `--output` are required.

## Input

A plain JSON array of GeoJSON Feature objects, as produced by `mongoimport --jsonArray` or the `prepare_for_mongo_import` script. Each feature may contain a `_id` field added by MongoDB — this field is removed automatically.

## Output

A GeoJSON FeatureCollection containing all features from the input array, without the `_id` field.

```json
{
  "type": "FeatureCollection",
  "features": [...]
}
```
