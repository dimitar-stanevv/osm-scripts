# merge_datasets

Merge multiple GeoJSON FeatureCollection files from a folder into a single combined GeoJSON FeatureCollection.

## Usage

```bash
python merge_datasets/merge_datasets.py --input data/geojsons --output data/merged.geojson
```

Both `--input` and `--output` are required.

| Argument   | Description                                      |
|------------|--------------------------------------------------|
| `--input`  | Path to a folder containing `.geojson` files     |
| `--output` | Path for the merged GeoJSON output file          |

## Behavior

- Scans the input folder for all `*.geojson` files (sorted alphabetically).
- Each file must be a valid GeoJSON **FeatureCollection**; files that are not are skipped with a warning.
- All features from every valid file are combined into a single FeatureCollection and written to the output path.
- Prints a per-file summary with feature counts and a total.

## Output format

Standard GeoJSON FeatureCollection containing every feature from the input files, in order:

```json
{
  "type": "FeatureCollection",
  "features": [ ... ]
}
```
