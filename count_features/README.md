# count_features

Count features in GeoJSON and CSV files within a given folder.

- **GeoJSON** — counts the number of features in the `FeatureCollection`.
- **CSV** — counts the number of data rows (excluding the header).

## Usage

```bash
python count_features/count_features.py --input data/
```

### Arguments

| Argument  | Required | Description                                  |
|-----------|----------|----------------------------------------------|
| `--input` | Yes      | Path to folder containing GeoJSON / CSV files |

## Example output

```
  speed_cams.geojson      12,345
  redlight_cams.geojson    3,210
  points.csv               1,500
  ──────────────────────  ────────
  Total                   17,055

  3 file(s)
```
