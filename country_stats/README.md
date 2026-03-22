# country_stats

Analyze features in a GeoJSON file by country. Reads the `properties.country` field (ISO 3166-1 alpha-2 code), converts it to a full country name, and prints a color-coded summary table sorted by feature count (descending).

## Usage

```bash
python country_stats/country_stats.py data/speed_cams_geocoded.geojson
```

### Arguments

| Argument     | Required | Description                       |
|--------------|----------|-----------------------------------|
| `input_file` | Yes      | Path to the GeoJSON file to analyze |

## Example output

```
    #      Country           Count       %
  ─────────────────────────────────────────────────────────────
     1  🇩🇪  Germany           4,210   34.2%  ██████████████████████████████
     2  🇫🇷  France            2,870   23.3%  ████████████████████▒░░░░░░░░░
     3  🇮🇹  Italy             1,540   12.5%  ██████████▒░░░░░░░░░░░░░░░░░░
     4  🇪🇸  Spain               980    8.0%  ███████░░░░░░░░░░░░░░░░░░░░░░
  ─────────────────────────────────────────────────────────────
           Total            12,300  4 countries
```
