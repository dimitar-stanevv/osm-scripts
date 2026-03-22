# prepare_for_mongo_import

Converts a GeoJSON **FeatureCollection** into a plain JSON array of its features, removing the `FeatureCollection` wrapper. The resulting file can be imported directly into MongoDB with:

```bash
mongoimport --db mydb --collection cams --jsonArray --file data/cams.json
```

## Usage

```bash
python prepare_for_mongo_import/prepare_for_mongo_import.py \
    --input data/all_cams.geojson \
    --output data/all_cams.json
```

Both `--input` and `--output` are required.

## Input

A standard GeoJSON file with `"type": "FeatureCollection"` at the top level.

## Output

A JSON file containing a single array (`[...]`) of the Feature objects that were inside the FeatureCollection. No other wrapper or metadata is included.
