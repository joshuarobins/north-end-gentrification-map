import pandas as pd
import numpy as np
import os

def calculate_median_grouped(row, bins):
    """
    Calculate median from grouped frequency data.
    bins: list of tuples (lower_bound, upper_bound, col_name or list_of_col_names)
    """
    total = 0
    for _, _, cols in bins:
        if isinstance(cols, list):
            total += sum(row[c] for c in cols)
        else:
            total += row[cols]
            
    if total == 0 or pd.isna(total):
        return np.nan
        
    target = total / 2.0
    cumulative = 0
    
    for lower, upper, cols in bins:
        if isinstance(cols, list):
            count = sum(row[c] for c in cols)
        else:
            count = row[cols]
            
        if cumulative + count >= target:
            if pd.isna(upper):
                return lower
            else:
                fraction = (target - cumulative) / count if count > 0 else 0
                return lower + fraction * (upper - lower)
        cumulative += count
    return np.nan

def main():
    print("Loading 1960 Tract Data...")
    raw_path = os.path.join("..", "raw_datasets", "nhgis0008_ds92_1960_tract.csv")
    df = pd.read_csv(raw_path, encoding="latin1", skiprows=[1])
    
    # STEP 1: Filter to North End Tracts (TRACT F-1 to F-6 in Boston)
    north_end_mask = df['AREANAME'].str.contains(r'TRACT F-[1-6]\b.*?BOSTON CITY', regex=True, na=False)
    df_ne = df[north_end_mask].copy()
    
    print(f"\nFound {len(df_ne)} North End Tracts.")
    
    if df_ne.empty:
        raise ValueError("No North End tracts found! Check AREANAME format.")
    
    # Dataframe to hold our cleaned data
    final_df = pd.DataFrame()
    final_df['GISJOIN'] = df_ne['GISJOIN']
    final_df['TRACTA'] = df_ne['TRACTA']
    final_df['AREANAME'] = df_ne['AREANAME']
    
    # ---------------------------
    # Demographics
    # ---------------------------
    final_df['Total_Population'] = df_ne['CA4001']
    
    # Italian Demographics
    italian_fs = df_ne['B8K011'] # Italian Foreign Stock
    foreign_born = df_ne['B8J001']
    native_born_foreign_parentage = df_ne['B8J002']
    total_fs = foreign_born + native_born_foreign_parentage
    
    pct_foreign_born_fs = (foreign_born / total_fs).fillna(0)
    pct_second_gen_fs = (native_born_foreign_parentage / total_fs).fillna(0)
    
    final_df['Total_Italian_Foreign_Stock'] = italian_fs
    final_df['Italian_1st_Generation'] = (italian_fs * pct_foreign_born_fs).round().astype(int)
    final_df['Italian_Americans'] = (italian_fs * pct_second_gen_fs).round().astype(int)
    final_df['Non_Italian_Population'] = final_df['Total_Population'] - italian_fs
    
    # ---------------------------
    # Median Age
    # ---------------------------
    age_bins = [
        (0, 5, [f'B8G{str(i).zfill(3)}' for i in [1,2,33,34]]),
        (5, 10, [f'B8G{str(i).zfill(3)}' for i in [3,4,35,36]]),
        (10, 15, [f'B8G{str(i).zfill(3)}' for i in [5,6,37,38]]),
        (15, 20, [f'B8G{str(i).zfill(3)}' for i in [7,8,39,40]]),
        (20, 25, [f'B8G{str(i).zfill(3)}' for i in [9,10,41,42]]),
        (25, 30, [f'B8G{str(i).zfill(3)}' for i in [11,12,43,44]]),
        (30, 35, [f'B8G{str(i).zfill(3)}' for i in [13,14,45,46]]),
        (35, 40, [f'B8G{str(i).zfill(3)}' for i in [15,16,47,48]]),
        (40, 45, [f'B8G{str(i).zfill(3)}' for i in [17,18,49,50]]),
        (45, 50, [f'B8G{str(i).zfill(3)}' for i in [19,20,51,52]]),
        (50, 55, [f'B8G{str(i).zfill(3)}' for i in [21,22,53,54]]),
        (55, 60, [f'B8G{str(i).zfill(3)}' for i in [23,24,55,56]]),
        (60, 65, [f'B8G{str(i).zfill(3)}' for i in [25,26,57,58]]),
        (65, 70, [f'B8G{str(i).zfill(3)}' for i in [27,28,59,60]]),
        (70, 75, [f'B8G{str(i).zfill(3)}' for i in [29,30,61,62]]),
        (75, np.nan, [f'B8G{str(i).zfill(3)}' for i in [31,32,63,64]])
    ]
    final_df['Median_Age'] = df_ne.apply(lambda r: calculate_median_grouped(r, age_bins), axis=1).round(1)
    
    # ---------------------------
    # Median Rent
    # ---------------------------
    rent_bins = [
        (0, 20, 'CAR001'), (20, 30, 'CAR002'), (30, 40, 'CAR003'),
        (40, 50, 'CAR004'), (50, 60, 'CAR005'), (60, 70, 'CAR006'),
        (70, 80, 'CAR007'), (80, 90, 'CAR008'), (90, 100, 'CAR009'),
        (100, 120, 'CAR010'), (120, 150, 'CAR011'), (150, 200, 'CAR012'),
        (200, np.nan, 'CAR013')
    ]
    final_df['Median_Rent'] = df_ne.apply(lambda r: calculate_median_grouped(r, rent_bins), axis=1).round(2)
    
    # ---------------------------
    # Median Income
    # ---------------------------
    income_bins = [
        (0, 1000, 'B8W001'), (1000, 2000, 'B8W002'), (2000, 3000, 'B8W003'),
        (3000, 4000, 'B8W004'), (4000, 5000, 'B8W005'), (5000, 6000, 'B8W006'),
        (6000, 7000, 'B8W007'), (7000, 8000, 'B8W008'), (8000, 9000, 'B8W009'),
        (9000, 10000, 'B8W010'), (10000, 15000, 'B8W011'), (15000, 25000, 'B8W012'),
        (25000, np.nan, 'B8W013')
    ]
    final_df['Median_Family_Income'] = df_ne.apply(lambda r: calculate_median_grouped(r, income_bins), axis=1).round(2)
    
    # ---------------------------
    # Occupation
    # ---------------------------
    white_collar_cols = ['B9B001', 'B9B013', 'B9B003', 'B9B015', 'B9B004', 'B9B016', 'B9B005', 'B9B017']
    blue_collar_cols = ['B9B006', 'B9B018', 'B9B007', 'B9B019', 'B9B011', 'B9B023']
    
    all_occupation_cols = [f'B9B{str(i).zfill(3)}' for i in range(1, 25)]
    total_workers = df_ne[all_occupation_cols].sum(axis=1)
    
    final_df['White_Collar_Workers'] = df_ne[white_collar_cols].sum(axis=1)
    final_df['Blue_Collar_Workers'] = df_ne[blue_collar_cols].sum(axis=1)
    
    final_df['Pct_White_Collar'] = (final_df['White_Collar_Workers'] / total_workers).fillna(0).round(4)
    final_df['Pct_Blue_Collar'] = (final_df['Blue_Collar_Workers'] / total_workers).fillna(0).round(4)
    
    # Output to final_datasets
    os.makedirs("../final_datasets", exist_ok=True)
    out_path = os.path.join("..", "final_datasets", "1960_north_end_cleaned.csv")
    final_df.to_csv(out_path, index=False)
    
    print("\nSample Cleaned Data:")
    print(final_df.head())
    print(f"\nSaved cleaned dataset to {out_path}")

if __name__ == "__main__":
    main()