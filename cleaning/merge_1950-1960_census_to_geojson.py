"""
merge_1950_1960_census_to_geojson.py

Merges 1950 and 1960 North End cleaned census CSVs onto the
1960 North End census tract GeoJSON geometries.

Output: final_datasets/north_end_census_1950_1960_geo.geojson
Each feature has:
  - GISJOIN
  - TRACTA (from 1950/1960 data)
  - Nested decade objects: census_1950, census_1960
    containing all census attributes from the respective cleaned CSV.
"""

import json
import csv
import os

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON_IN  = os.path.join(BASE, "shape_files", "1960_WGS84.geojson")
FINAL_DIR   = os.path.join(BASE, "final_datasets")
OUT_FILE    = os.path.join(FINAL_DIR, "north_end_census_1950_1960_geo.geojson")

DECADES = {
    1950: os.path.join(FINAL_DIR, "1950_north_end_cleaned.csv"),
    1960: os.path.join(FINAL_DIR, "1960_north_end_cleaned.csv"),
}

# North End tract GISJOINs
NORTH_END_GISJOINS = {
    "G2500250F0001",
    "G2500250F0002",
    "G2500250F0003",
    "G2500250F0004",
    "G2500250F0005",
    "G2500250F0006",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_decade_csv(path: str) -> dict[str, dict]:
    """
    Load a decade CSV; key rows by string GISJOIN.
    Numeric values are cast to float (or int where appropriate).
    """
    rows: dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gisjoin = row["GISJOIN"]
            # Cast numeric fields
            cleaned: dict = {}
            for k, v in row.items():
                if k in ("GISJOIN", "TRACTA", "AREANAME"):
                    cleaned[k] = v
                    continue
                try:
                    cleaned[k] = int(v) if v == str(int(float(v))) else float(v)
                except (ValueError, OverflowError):
                    cleaned[k] = v if v != "" else None
            rows[gisjoin] = cleaned
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # 1. Load all decade CSVs
    print("Loading decade CSVs...")
    decade_data: dict[int, dict[str, dict]] = {}
    for year, path in DECADES.items():
        decade_data[year] = load_decade_csv(path)
        print(f"  {year}: {list(decade_data[year].keys())}")

    # 2. Load the 1960 GeoJSON and extract North End features
    print("\nLoading 1960 GeoJSON (this may take a moment)...")
    with open(GEOJSON_IN, "r", encoding="utf-8") as f:
        geo = json.load(f)

    north_end_features = [
        feat for feat in geo["features"]
        if feat["properties"].get("GISJOIN") in NORTH_END_GISJOINS
    ]
    print(f"  Extracted {len(north_end_features)} North End tract geometries.")

    if len(north_end_features) != 6:
        raise ValueError(
            f"Expected 6 North End features, got {len(north_end_features)}. "
            "Check NORTH_END_GISJOINS."
        )

    # 3. Merge: attach census data from each decade to each feature
    print("\nMerging census data onto geometries...")
    merged_features = []

    for feat in north_end_features:
        gisjoin = feat["properties"]["GISJOIN"]

        props: dict = {
            "GISJOIN": gisjoin,
        }

        for year in (1950, 1960):
            year_rows = decade_data[year]
            if gisjoin not in year_rows:
                print(f"  WARNING: tract {gisjoin} not found in {year} CSV — filling None.")
                props[f"census_{year}"] = None
            else:
                row = dict(year_rows[gisjoin])
                # Provide a TRACTA alias at top level if not present
                if "TRACTA" not in props and "TRACTA" in row:
                     props["TRACTA"] = row["TRACTA"]
                
                # Remove redundant join keys from nested object
                row.pop("GISJOIN", None)
                # We can keep TRACTA inside the decade, but optionally pop it
                # row.pop("TRACTA", None)
                props[f"census_{year}"] = row

        merged_features.append({
            "type":       "Feature",
            "properties": props,
            "geometry":   feat["geometry"],
        })

        print(f"  Tract ({gisjoin}) merged.")

    # 4. Build output FeatureCollection
    out_geojson = {
        "type": "FeatureCollection",
        "name": "north_end_census_1950_1960",
        "crs": geo.get("crs"),
        "features": merged_features,
    }

    # 5. Write output
    os.makedirs(FINAL_DIR, exist_ok=True)
    print(f"\nWriting output to:\n  {OUT_FILE}")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out_geojson, f, indent=2)

    print("\nDone.")
    print(f"  Features: {len(merged_features)}")
    print(f"  Decades:  1950, 1960")


if __name__ == "__main__":
    main()
