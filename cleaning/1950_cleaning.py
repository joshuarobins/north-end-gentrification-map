import pandas as pd
import numpy as np
import os

def calculate_median_grouped(row, bins):
    """
    Calculate median from grouped frequency data.
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
    print("Loading 1950 Tract Data...")
    raw_dir = os.path.join("..", "raw_datasets")
    
    df50 = pd.read_csv(os.path.join(raw_dir, "nhgis0008_ds82_1950_tract.csv"), encoding="latin1", skiprows=[1], low_memory=False)
    
    # Filter to North End Tracts in Suffolk County
    # In 1950, PRETRACTA is 'F' and TRACTA is 1-6 for the North End.
    df_ne = df50[df50['COUNTY'].astype(str).str.contains('Suffolk', case=False, na=False)].copy()
    
    # Check if PRETRACTA and TRACTA are columns
    if 'PRETRACTA' in df_ne.columns and 'TRACTA' in df_ne.columns:
        df_ne = df_ne[(df_ne['PRETRACTA'] == 'F') & (df_ne['TRACTA'].isin([1, 2, 3, 4, 5, 6, '1', '2', '3', '4', '5', '6']))].copy()
    else:
        raise ValueError("Could not find PRETRACTA and TRACTA columns in 1950 data.")
    
    print(f"\nFound {len(df_ne)} North End Tracts in 1950.")
    
    if df_ne.empty:
        raise ValueError("No North End tracts found in 1950 data!")
    
    final_df = pd.DataFrame()
    final_df['GISJOIN'] = df_ne['GISJOIN']
    # Combine PRETRACTA and TRACTA to be consistent with later years (e.g. F-1)
    final_df['TRACTA'] = df_ne['PRETRACTA'].astype(str) + "-" + df_ne['TRACTA'].astype(str)
    
    # Demographics
    final_df['Total_Population'] = df_ne['BZ8001']
    
    # Italian Demographics
    # In 1950, we only have Country of Birth for the Foreign-Born White Population.
    # B1L021: Italy.
    # We do NOT have "Native of foreign or mixed parentage" (Italian Americans).
    final_df['Total_Italian_Demographic'] = np.nan
    final_df['Italian_1st_Generation'] = df_ne['B1L021']
    final_df['Italian_Americans'] = np.nan
    final_df['Non_Italian_Population'] = np.nan # Cannot calculate without Total Demographic
    
    # Age Medians
    # 17 bins for male (B0H001-B0H017) and 17 bins for female (B0H018-B0H034)
    # Bins: <5, 5-9, 10-14, 15-19, 20-24, 25-29, 30-34, 35-39, 40-44, 45-49, 50-54, 55-59, 60-64, 65-69, 70-74, 75-84, 85+
    age_limits = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 85, np.nan]
    age_bins = []
    for i in range(17):
        male_col = f'B0H{str(i+1).zfill(3)}'
        female_col = f'B0H{str(i+18).zfill(3)}'
        age_bins.append((age_limits[i], age_limits[i+1], [male_col, female_col]))
        
    final_df['Median_Age'] = df_ne.apply(lambda r: calculate_median_grouped(r, age_bins), axis=1).round(1)
    
    # Other Medians
    final_df['Median_Rent'] = df_ne['B05001']
    final_df['Median_Family_Income'] = df_ne['B0F001']
    
    # Occupation
    # White Collar: Professional, Managers, Clerical, Sales.
    white_collar_cols = ['B0R001', 'B0R002', 'B0R003', 'B0R004', 'B0R011', 'B0R012', 'B0R013', 'B0R014']
    # Blue Collar: Craftsmen, Operatives, Laborers.
    blue_collar_cols = ['B0R005', 'B0R006', 'B0R009', 'B0R015', 'B0R016', 'B0R019']
    
    all_occupation_cols = [f'B0R{str(i).zfill(3)}' for i in range(1, 21)]
    
    white_collar_cols = [c for c in white_collar_cols if c in df_ne.columns]
    blue_collar_cols = [c for c in blue_collar_cols if c in df_ne.columns]
    all_occupation_cols = [c for c in all_occupation_cols if c in df_ne.columns]
    
    total_workers = df_ne[all_occupation_cols].sum(axis=1)
    final_df['White_Collar_Workers'] = df_ne[white_collar_cols].sum(axis=1)
    final_df['Blue_Collar_Workers'] = df_ne[blue_collar_cols].sum(axis=1)
    
    final_df['Pct_White_Collar'] = (final_df['White_Collar_Workers'] / total_workers).fillna(0).round(4)
    final_df['Pct_Blue_Collar'] = (final_df['Blue_Collar_Workers'] / total_workers).fillna(0).round(4)
    
    # Output
    out_path = os.path.join("..", "final_datasets", "1950_north_end_cleaned.csv")
    final_df.to_csv(out_path, index=False)
    
    print("\nSample Cleaned Data (1950):")
    print(final_df.head())
    print(f"\nSaved cleaned dataset to {out_path}")

if __name__ == "__main__":
    main()
