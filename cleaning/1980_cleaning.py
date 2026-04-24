import pandas as pd
import numpy as np
import os

def main():
    print("Loading 1980 Tract Data...")
    raw_dir = os.path.join("..", "raw_datasets")
    
    df104 = pd.read_csv(os.path.join(raw_dir, "nhgis0009_ds104_1980_tract.csv"), encoding="latin1", skiprows=[1], low_memory=False)
    df107 = pd.read_csv(os.path.join(raw_dir, "nhgis0009_ds107_1980_tract.csv"), encoding="latin1", skiprows=[1], low_memory=False)
    
    # Merge on GISJOIN
    df_merged = df104.merge(df107, on=['GISJOIN', 'TRACTA'], suffixes=('', '_y'))
    
    # Filter to North End Tracts (301, 302, 303, 304, 305) in Suffolk County
    north_end_tracts = ['301', '302', '303', '304', '305', 301, 302, 303, 304, 305]
    
    df_ne = df_merged[(df_merged['COUNTYA'] == 25) | (df_merged['COUNTYA'] == '25') | (df_merged['COUNTYA'] == 250)]
    df_ne = df_ne[df_ne['TRACTA'].isin(north_end_tracts)].copy()
    
    print(f"\nFound {len(df_ne)} North End Tracts in 1980.")
    
    if df_ne.empty:
        raise ValueError("No North End tracts found in 1980 data!")
    
    final_df = pd.DataFrame()
    final_df['GISJOIN'] = df_ne['GISJOIN']
    final_df['TRACTA'] = df_ne['TRACTA']
    
    # Demographics
    final_df['Total_Population'] = df_ne['C7L001'] # DS104 Total Persons
    
    # Italian Demographics
    # DG0008: Single ancestry group: Italian
    # DG1005: Italian and other group(s)
    total_italian = df_ne['DG0008'] + df_ne['DG1005']
    final_df['Total_Italian_Demographic'] = total_italian
    
    # Proportional estimation for generations
    # DG6004: Foreign born
    pct_foreign_born = (df_ne['DG6004'] / final_df['Total_Population']).fillna(0)
    
    final_df['Italian_1st_Generation'] = (total_italian * pct_foreign_born).round().astype(int)
    final_df['Italian_Americans'] = total_italian - final_df['Italian_1st_Generation']
    final_df['Non_Italian_Population'] = final_df['Total_Population'] - total_italian
    
    # Medians
    final_df['Median_Age'] = df_ne['C69001']
    final_df['Median_Rent'] = df_ne['C8O001']
    
    # Median Income calculation
    def calculate_median_grouped(row, bins):
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

    income_bins = [
        (0, 2500, 'DID001'), (2500, 5000, 'DID002'), (5000, 7500, 'DID003'),
        (7500, 10000, 'DID004'), (10000, 12500, 'DID005'), (12500, 15000, 'DID006'),
        (15000, 17500, 'DID007'), (17500, 20000, 'DID008'), (20000, 22500, 'DID009'),
        (22500, 25000, 'DID010'), (25000, 27500, 'DID011'), (27500, 30000, 'DID012'),
        (30000, 35000, 'DID013'), (35000, 40000, 'DID014'), (40000, 50000, 'DID015'),
        (50000, 75000, 'DID016'), (75000, np.nan, 'DID017')
    ]
    final_df['Median_Family_Income'] = df_ne.apply(lambda r: calculate_median_grouped(r, income_bins), axis=1).round(2)
    
    # Occupation
    # White Collar: DIB001, DIB002, DIB003, DIB004, DIB005
    white_collar_cols = ['DIB001', 'DIB002', 'DIB003', 'DIB004', 'DIB005']
    # Blue Collar: DIB010 (Precision production), DIB011 (Machine operators), DIB012 (Transportation), DIB013 (Handlers/laborers)
    # Wait, my earlier check showed DIB011 and DIB012. I'll include DIB010, DIB011, DIB012, DIB013
    blue_collar_cols = ['DIB010', 'DIB011', 'DIB012', 'DIB013']
    # Service and Farm: DIB006, DIB007, DIB008, DIB009
    all_occupation_cols = [f'DIB{str(i).zfill(3)}' for i in range(1, 14)]
    
    # We must ensure columns exist (DIB013 might not exist in the extract if it stopped at 012, but we checked the codebook)
    # Let's check which exist
    white_collar_cols = [c for c in white_collar_cols if c in df_ne.columns]
    blue_collar_cols = [c for c in blue_collar_cols if c in df_ne.columns]
    all_occupation_cols = [c for c in all_occupation_cols if c in df_ne.columns]
    
    total_workers = df_ne[all_occupation_cols].sum(axis=1)
    final_df['White_Collar_Workers'] = df_ne[white_collar_cols].sum(axis=1)
    final_df['Blue_Collar_Workers'] = df_ne[blue_collar_cols].sum(axis=1)
    
    final_df['Pct_White_Collar'] = (final_df['White_Collar_Workers'] / total_workers).fillna(0).round(4)
    final_df['Pct_Blue_Collar'] = (final_df['Blue_Collar_Workers'] / total_workers).fillna(0).round(4)
    
    # Output
    out_path = os.path.join("..", "final_datasets", "1980_north_end_cleaned.csv")
    final_df.to_csv(out_path, index=False)
    
    print("\nSample Cleaned Data (1980):")
    print(final_df.head())
    print(f"\nSaved cleaned dataset to {out_path}")

if __name__ == "__main__":
    main()
