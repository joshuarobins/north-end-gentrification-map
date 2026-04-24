"""
merge_census_to_geojson.py

Merges 1970, 1980, 1990, and 2000 North End cleaned census CSVs onto the
2000 North End census tract GeoJSON geometries.

Output: final_datasets/north_end_census_1970_2000_geo.geojson
Each feature has:
  - GISJOIN / TRACTA (from geometry)
  - Nested decade objects: census_1970, census_1980, census_1990, census_2000
    containing all census attributes from the respective cleaned CSV.

GISJOIN mapping (2000 format):
  G2500250030100 -> tract 301  (G + state 250 + county 025 + tracta 030100)
  tracta = int(gisjoin[8:14]) // 100
"""

import json
import csv
import os

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON_IN  = os.path.join(BASE, "shape_files", "2000_WGS84.geojson")
FINAL_DIR   = os.path.join(BASE, "final_datasets")
OUT_FILE    = os.path.join(FINAL_DIR, "north_end_census_1970_2000_geo.geojson")

DECADES = {
    1970: os.path.join(FINAL_DIR, "1970_north_end_cleaned.csv"),
    1980: os.path.join(FINAL_DIR, "1980_north_end_cleaned.csv"),
    1990: os.path.join(FINAL_DIR, "1990_north_end_cleaned.csv"),
    2000: os.path.join(FINAL_DIR, "2000_north_end_cleaned.csv"),
}

# North End tract GISJOINs (2000 format)
NORTH_END_GISJOINS = {
    "G2500250030100",
    "G2500250030200",
    "G2500250030300",
    "G2500250030400",
    "G2500250030500",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def gisjoin_to_tract(gisjoin: str) -> int:
    """
    Extract integer tract number from a 2000-format GISJOIN.
    G2500250030100  ->  303010 // 100  = 301
    """
    return int(gisjoin[8:14]) // 100


def load_decade_csv(path: str) -> dict[int, dict]:
    """
    Load a decade CSV; key rows by integer TRACTA.
    Numeric values are cast to float (or int where appropriate).
    """
    rows: dict[int, dict] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tracta = int(float(row["TRACTA"]))
            # Cast numeric fields
            cleaned: dict = {}
            for k, v in row.items():
                if k in ("GISJOIN",):
                    cleaned[k] = v
                    continue
                try:
                    cleaned[k] = int(v) if v == str(int(float(v))) else float(v)
                except (ValueError, OverflowError):
                    cleaned[k] = v if v != "" else None
            rows[tracta] = cleaned
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # 1. Load all decade CSVs
    print("Loading decade CSVs...")
    decade_data: dict[int, dict[int, dict]] = {}
    for year, path in DECADES.items():
        decade_data[year] = load_decade_csv(path)
        print(f"  {year}: {list(decade_data[year].keys())}")

    # 2. Load the 2000 GeoJSON and extract North End features
    print("\nLoading 2000 GeoJSON (this may take a moment)...")
    with open(GEOJSON_IN, "r", encoding="utf-8") as f:
        geo = json.load(f)

    north_end_features = [
        feat for feat in geo["features"]
        if feat["properties"]["GISJOIN"] in NORTH_END_GISJOINS
    ]
    print(f"  Extracted {len(north_end_features)} North End tract geometries.")

    if len(north_end_features) != 5:
        raise ValueError(
            f"Expected 5 North End features, got {len(north_end_features)}. "
            "Check NORTH_END_GISJOINS."
        )

    # 3. Merge: attach census data from each decade to each feature
    print("\nMerging census data onto geometries...")
    merged_features = []

    for feat in north_end_features:
        gisjoin = feat["properties"]["GISJOIN"]
        tracta  = gisjoin_to_tract(gisjoin)

        props: dict = {
            "GISJOIN": gisjoin,
            "TRACTA":  tracta,
        }

        for year in (1970, 1980, 1990, 2000):
            year_rows = decade_data[year]
            if tracta not in year_rows:
                print(f"  WARNING: tract {tracta} not found in {year} CSV — filling None.")
                props[f"census_{year}"] = None
            else:
                row = dict(year_rows[tracta])
                # Remove redundant join keys from nested object
                row.pop("GISJOIN", None)
                row.pop("TRACTA", None)
                props[f"census_{year}"] = row

        merged_features.append({
            "type":       "Feature",
            "properties": props,
            "geometry":   feat["geometry"],
        })

        print(f"  Tract {tracta} ({gisjoin}) merged.")

    # 4. Build output FeatureCollection
    out_geojson = {
        "type": "FeatureCollection",
        "name": "north_end_census_1970_2000",
        "crs": geo.get("crs"),
        "features": merged_features,
    }

    # 5. Write output
    os.makedirs(FINAL_DIR, exist_ok=True)
    print(f"\nWriting output to:\n  {OUT_FILE}")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_geojson, f, indent=2)

    print("\n✓ Done.")
    print(f"  Features: {len(merged_features)}")
    print(f"  Decades:  1970, 1980, 1990, 2000")


if __name__ == "__main__":
    main()
