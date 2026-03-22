# filter_by_country

Filters a GeoJSON **FeatureCollection** by `properties.country` and writes a new GeoJSON file containing only the matching features.

The script uses a default `INCLUDED_COUNTRIES` list defined near the top of `filter_by_country.py`. You can override that list at runtime with the optional `--countries` argument.

## Usage

```bash
python filter_by_country/filter_by_country.py \
    --input data/all_cams.geojson \
    --output data/all_cams_bg_ro.geojson \
    --countries BG,RO
```

`--input` and `--output` are required.

`--countries` is optional. When provided, it overrides the in-file `INCLUDED_COUNTRIES` list completely.

## Input

A GeoJSON file with:

- top-level `"type": "FeatureCollection"`
- a `features` array of GeoJSON Feature objects
- alpha-2 country codes stored in `properties.country`

## Output

A GeoJSON `FeatureCollection` containing only features whose `properties.country` matches one of the selected countries.

The script preserves other top-level keys from the input document, except for `bbox`, which is omitted so the output does not contain stale bounds.

## Terminal Summary

After writing the output file, the script prints a colorized summary showing:

- active country list
- input feature count
- extracted feature count
- skipped feature count
- output path
- counts by `properties.type` for:
  - `redlight_cam`
  - `speed_cam`
  - `combined_cam`
  - `tunnel_cam`
  - `other`
