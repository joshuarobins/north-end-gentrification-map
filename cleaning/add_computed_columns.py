"""
add_computed_columns.py

Enriches both North End GeoJSON files with:
  1. Population percentage columns for each demographic group
  2. Globally-normalized (0-1 min-max) columns for rent, income, age,
     pct white collar, pct blue collar

Normalization is global across ALL tracts and ALL years (1950-2000)
so cross-decade comparisons are meaningful.

New fields added to each census_{year} sub-object:
  Pct_Italian_Demographic   – fraction of total population
  Pct_Italian_1st_Gen
  Pct_Italian_Americans
  Pct_Non_Italian
  Norm_Median_Rent          – 0-1 global min-max
  Norm_Median_Income
  Norm_Median_Age
  Norm_Pct_White_Collar
  Norm_Pct_Blue_Collar
"""

import json, os

BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINAL_DIR = os.path.join(BASE, "final_datasets")

FILES = {
    "1950_1960": os.path.join(FINAL_DIR, "north_end_census_1950_1960_geo.geojson"),
    "1970_2000": os.path.join(FINAL_DIR, "north_end_census_1970_2000_geo.geojson"),
}

DECADES = {
    "1950_1960": [1950, 1960],
    "1970_2000": [1970, 1980, 1990, 2000],
}

NORM_FIELDS = [
    "Median_Rent",
    "Median_Family_Income",
    "Median_Age",
    "Pct_White_Collar",
    "Pct_Blue_Collar",
]


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_census(feat, year):
    return feat["properties"].get(f"census_{year}")


def italian_key(census):
    for k in ("Total_Italian_Foreign_Stock", "Total_Italian_Demographic"):
        if census.get(k) is not None:
            return k
    return None


def safe_pct(num, denom):
    if num is None or denom is None or denom == 0:
        return None
    return round(float(num) / float(denom), 4)


def main():
    print("Loading GeoJSON files...")
    geo = {k: load(p) for k, p in FILES.items()}

    # ── Pass 1: collect all values for global normalization ───────────────────
    global_vals = {f: [] for f in NORM_FIELDS}

    for file_key, data in geo.items():
        for feat in data["features"]:
            for year in DECADES[file_key]:
                c = get_census(feat, year)
                if not c:
                    continue
                for field in NORM_FIELDS:
                    v = c.get(field)
                    if v is not None:
                        global_vals[field].append(float(v))

    g_min = {f: min(v) for f, v in global_vals.items() if v}
    g_max = {f: max(v) for f, v in global_vals.items() if v}

    print("Global ranges:")
    for f in NORM_FIELDS:
        print(f"  {f}: {g_min[f]:.4f} – {g_max[f]:.4f}")

    def norm(field, value):
        if value is None:
            return None
        lo, hi = g_min[field], g_max[field]
        if hi == lo:
            return 0.0
        return round((float(value) - lo) / (hi - lo), 4)

    # ── Pass 2: enrich each census sub-object ────────────────────────────────
    print("\nAdding computed columns...")
    for file_key, data in geo.items():
        for feat in data["features"]:
            for year in DECADES[file_key]:
                c = get_census(feat, year)
                if not c:
                    continue

                total = c.get("Total_Population")

                # Population percentage columns
                ik = italian_key(c)
                c["Pct_Italian_Demographic"] = safe_pct(c.get(ik) if ik else None, total)
                c["Pct_Italian_1st_Gen"]     = safe_pct(c.get("Italian_1st_Generation"), total)
                c["Pct_Italian_Americans"]   = safe_pct(c.get("Italian_Americans"), total)
                c["Pct_Non_Italian"]         = safe_pct(c.get("Non_Italian_Population"), total)

                # Globally-normalized columns
                for field in NORM_FIELDS:
                    c[f"Norm_{field}"] = norm(field, c.get(field))

    # ── Save ─────────────────────────────────────────────────────────────────
    print("\nSaving enriched GeoJSON files...")
    for file_key, data in geo.items():
        save(data, FILES[file_key])
        print(f"  Saved: {FILES[file_key]}")

    print("\nDone.")


if __name__ == "__main__":
    main()
