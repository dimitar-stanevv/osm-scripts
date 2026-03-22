#!/usr/bin/env python3
"""
Analyze features in a GeoJSON file by country.

Reads properties.country (ISO 3166-1 alpha-2 code) from each feature,
converts it to a human-readable country name, and prints a sorted
summary table to the console.

Usage:
    python country_stats.py <input_file>
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

COUNTRY_NAMES = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan",
    "AG": "Antigua and Barbuda", "AI": "Anguilla", "AL": "Albania",
    "AM": "Armenia", "AO": "Angola", "AQ": "Antarctica", "AR": "Argentina",
    "AS": "American Samoa", "AT": "Austria", "AU": "Australia", "AW": "Aruba",
    "AX": "Åland Islands", "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina",
    "BB": "Barbados", "BD": "Bangladesh", "BE": "Belgium",
    "BF": "Burkina Faso", "BG": "Bulgaria", "BH": "Bahrain", "BI": "Burundi",
    "BJ": "Benin", "BL": "Saint Barthélemy", "BM": "Bermuda",
    "BN": "Brunei", "BO": "Bolivia", "BQ": "Caribbean Netherlands",
    "BR": "Brazil", "BS": "Bahamas", "BT": "Bhutan",
    "BV": "Bouvet Island", "BW": "Botswana", "BY": "Belarus", "BZ": "Belize",
    "CA": "Canada", "CC": "Cocos (Keeling) Islands",
    "CD": "DR Congo", "CF": "Central African Republic",
    "CG": "Republic of the Congo", "CH": "Switzerland",
    "CI": "Côte d'Ivoire", "CK": "Cook Islands", "CL": "Chile",
    "CM": "Cameroon", "CN": "China", "CO": "Colombia", "CR": "Costa Rica",
    "CU": "Cuba", "CV": "Cape Verde", "CW": "Curaçao",
    "CX": "Christmas Island", "CY": "Cyprus", "CZ": "Czechia",
    "DE": "Germany", "DJ": "Djibouti", "DK": "Denmark", "DM": "Dominica",
    "DO": "Dominican Republic", "DZ": "Algeria", "EC": "Ecuador",
    "EE": "Estonia", "EG": "Egypt", "EH": "Western Sahara", "ER": "Eritrea",
    "ES": "Spain", "ET": "Ethiopia", "FI": "Finland", "FJ": "Fiji",
    "FK": "Falkland Islands", "FM": "Micronesia", "FO": "Faroe Islands",
    "FR": "France", "GA": "Gabon", "GB": "United Kingdom", "GD": "Grenada",
    "GE": "Georgia", "GF": "French Guiana", "GG": "Guernsey", "GH": "Ghana",
    "GI": "Gibraltar", "GL": "Greenland", "GM": "Gambia", "GN": "Guinea",
    "GP": "Guadeloupe", "GQ": "Equatorial Guinea", "GR": "Greece",
    "GS": "South Georgia", "GT": "Guatemala", "GU": "Guam",
    "GW": "Guinea-Bissau", "GY": "Guyana", "HK": "Hong Kong",
    "HM": "Heard Island", "HN": "Honduras", "HR": "Croatia", "HT": "Haiti",
    "HU": "Hungary", "ID": "Indonesia", "IE": "Ireland", "IL": "Israel",
    "IM": "Isle of Man", "IN": "India", "IO": "British Indian Ocean Territory",
    "IQ": "Iraq", "IR": "Iran", "IS": "Iceland", "IT": "Italy",
    "JE": "Jersey", "JM": "Jamaica", "JO": "Jordan", "JP": "Japan",
    "KE": "Kenya", "KG": "Kyrgyzstan", "KH": "Cambodia", "KI": "Kiribati",
    "KM": "Comoros", "KN": "Saint Kitts and Nevis", "KP": "North Korea",
    "KR": "South Korea", "KW": "Kuwait", "KY": "Cayman Islands",
    "KZ": "Kazakhstan", "LA": "Laos", "LB": "Lebanon",
    "LC": "Saint Lucia", "LI": "Liechtenstein", "LK": "Sri Lanka",
    "LR": "Liberia", "LS": "Lesotho", "LT": "Lithuania",
    "LU": "Luxembourg", "LV": "Latvia", "LY": "Libya", "MA": "Morocco",
    "MC": "Monaco", "MD": "Moldova", "ME": "Montenegro",
    "MF": "Saint Martin", "MG": "Madagascar", "MH": "Marshall Islands",
    "MK": "North Macedonia", "ML": "Mali", "MM": "Myanmar", "MN": "Mongolia",
    "MO": "Macao", "MP": "Northern Mariana Islands", "MQ": "Martinique",
    "MR": "Mauritania", "MS": "Montserrat", "MT": "Malta",
    "MU": "Mauritius", "MV": "Maldives", "MW": "Malawi", "MX": "Mexico",
    "MY": "Malaysia", "MZ": "Mozambique", "NA": "Namibia",
    "NC": "New Caledonia", "NE": "Niger", "NF": "Norfolk Island",
    "NG": "Nigeria", "NI": "Nicaragua", "NL": "Netherlands", "NO": "Norway",
    "NP": "Nepal", "NR": "Nauru", "NU": "Niue", "NZ": "New Zealand",
    "OM": "Oman", "PA": "Panama", "PE": "Peru", "PF": "French Polynesia",
    "PG": "Papua New Guinea", "PH": "Philippines", "PK": "Pakistan",
    "PL": "Poland", "PM": "Saint Pierre and Miquelon", "PN": "Pitcairn",
    "PR": "Puerto Rico", "PS": "Palestine", "PT": "Portugal", "PW": "Palau",
    "PY": "Paraguay", "QA": "Qatar", "RE": "Réunion", "RO": "Romania",
    "RS": "Serbia", "RU": "Russia", "RW": "Rwanda", "SA": "Saudi Arabia",
    "SB": "Solomon Islands", "SC": "Seychelles", "SD": "Sudan",
    "SE": "Sweden", "SG": "Singapore", "SH": "Saint Helena",
    "SI": "Slovenia", "SJ": "Svalbard", "SK": "Slovakia",
    "SL": "Sierra Leone", "SM": "San Marino", "SN": "Senegal",
    "SO": "Somalia", "SR": "Suriname", "SS": "South Sudan",
    "ST": "São Tomé and Príncipe", "SV": "El Salvador",
    "SX": "Sint Maarten", "SY": "Syria", "SZ": "Eswatini",
    "TC": "Turks and Caicos", "TD": "Chad", "TF": "French Southern Territories",
    "TG": "Togo", "TH": "Thailand", "TJ": "Tajikistan", "TK": "Tokelau",
    "TL": "Timor-Leste", "TM": "Turkmenistan", "TN": "Tunisia",
    "TO": "Tonga", "TR": "Turkey", "TT": "Trinidad and Tobago",
    "TV": "Tuvalu", "TW": "Taiwan", "TZ": "Tanzania", "UA": "Ukraine",
    "UG": "Uganda", "UM": "U.S. Minor Outlying Islands",
    "US": "United States", "UY": "Uruguay", "UZ": "Uzbekistan",
    "VA": "Vatican City", "VC": "Saint Vincent and the Grenadines",
    "VE": "Venezuela", "VG": "British Virgin Islands",
    "VI": "U.S. Virgin Islands", "VN": "Vietnam", "VU": "Vanuatu",
    "WF": "Wallis and Futuna", "WS": "Samoa", "XK": "Kosovo",
    "YE": "Yemen", "YT": "Mayotte", "ZA": "South Africa", "ZM": "Zambia",
    "ZW": "Zimbabwe",
}

COUNTRY_FLAGS = {
    code: chr(0x1F1E6 + ord(code[0]) - ord("A"))
        + chr(0x1F1E6 + ord(code[1]) - ord("A"))
    for code in COUNTRY_NAMES
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
WHITE = "\033[97m"


def country_name(code: str) -> str:
    return COUNTRY_NAMES.get(code.upper(), code)


def country_flag(code: str) -> str:
    return COUNTRY_FLAGS.get(code.upper(), "  ")


def has_valid_country(feat: dict) -> bool:
    props = feat.get("properties") or {}
    code = props.get("country")
    return bool(code and isinstance(code, str) and len(code) == 2)


def analyze(features: list[dict]) -> tuple[Counter, list[dict]]:
    """Return (counter of country codes, list of features missing country)."""
    counts: Counter = Counter()
    missing: list[dict] = []
    for feat in features:
        if has_valid_country(feat):
            code = feat["properties"]["country"]
            counts[code.upper()] += 1
        else:
            missing.append(feat)
    return counts, missing


def bar_char(fraction: float, width: int = 30) -> str:
    filled = round(fraction * width)
    return f"{GREEN}{'█' * filled}{DIM}{'░' * (width - filled)}{RESET}"


def print_table(counts: Counter, missing: int, total_features: int):
    ranked = counts.most_common()
    if not ranked:
        print("No features with a valid country code found.")
        return

    max_count = ranked[0][1]
    name_width = max(len(country_name(c)) for c, _ in ranked)
    name_width = max(name_width, 7)

    print()
    print(
        f"  {BOLD}{CYAN}{'#':>4}  {'':2}  {'Country':<{name_width}}  "
        f"{'Count':>8}  {'%':>6}  {'':30}{RESET}"
    )
    print(f"  {DIM}{'─' * (4 + 2 + 2 + name_width + 2 + 8 + 2 + 6 + 2 + 30)}{RESET}")

    for rank, (code, count) in enumerate(ranked, 1):
        name = country_name(code)
        flag = country_flag(code)
        pct = count / total_features * 100
        fraction = count / max_count
        bar = bar_char(fraction)

        print(
            f"  {BOLD}{WHITE}{rank:>4}{RESET}  "
            f"{flag}  "
            f"{YELLOW}{name:<{name_width}}{RESET}  "
            f"{BOLD}{WHITE}{count:>8,}{RESET}  "
            f"{MAGENTA}{pct:>5.1f}%{RESET}  "
            f"{bar}"
        )

    print(f"  {DIM}{'─' * (4 + 2 + 2 + name_width + 2 + 8 + 2 + 6 + 2 + 30)}{RESET}")
    print(
        f"  {BOLD}{'':>4}  {'':2}  {'Total':<{name_width}}  "
        f"{total_features:>8,}  {RESET}"
        f"{DIM}{len(ranked)} {'country' if len(ranked) == 1 else 'countries'}{RESET}"
    )
    if missing:
        print(f"  {DIM}     ⚠️   {missing:,} feature(s) without a valid country code{RESET}")
    print()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Analyze GeoJSON features by country."
    )
    parser.add_argument(
        "input_file",
        help="Path to the GeoJSON file to analyze",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    path = Path(args.input_file)

    if not path.is_file():
        print(f"Error: {path} is not a file", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    if not features:
        print("No features found in the GeoJSON file.")
        return

    counts, missing_features = analyze(features)
    print_table(counts, len(missing_features), len(features))

    if missing_features:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_name = f"_features_without_country_{timestamp}.geojson"
        out_path = path.parent / out_name
        collection = {
            "type": "FeatureCollection",
            "features": missing_features,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(collection, f, ensure_ascii=False)
        print(f"  {YELLOW}📄 Wrote {len(missing_features):,} feature(s) without country → {out_path}{RESET}")
        print()


if __name__ == "__main__":
    main()
