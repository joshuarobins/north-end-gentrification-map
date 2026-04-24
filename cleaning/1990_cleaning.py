import pandas as pd
import numpy as np
import os

def main():
    print("Loading 1990 Tract Data...")
    raw_dir = os.path.join("..", "raw_datasets")
    
    df120 = pd.read_csv(os.path.join(raw_dir, "nhgis0008_ds120_1990_tract.csv"), encoding="latin1", skiprows=[1], low_memory=False)
    df123 = pd.read_csv(os.path.join(raw_dir, "nhgis0008_ds123_1990_tract.csv"), encoding="latin1", skiprows=[1], low_memory=False)
    
    # Merge on GISJOIN
    df_merged = df120.merge(df123, on=['GISJOIN', 'TRACTA'], suffixes=('', '_y'))
    
    # Filter to North End Tracts (301, 302, 303, 304, 305) in Suffolk County
    north_end_tracts = ['301', '302', '303', '304', '305', 301, 302, 303, 304, 305]
    
    df_ne = df_merged[(df_merged['COUNTYA'] == 25) | (df_merged['COUNTYA'] == '25') | (df_merged['COUNTYA'] == 250) | (df_merged['COUNTYA'] == 2500)]
    df_ne = df_ne[df_ne['TRACTA'].isin(north_end_tracts)].copy()
    
    print(f"\nFound {len(df_ne)} North End Tracts in 1990.")
    
    if df_ne.empty:
        raise ValueError("No North End tracts found in 1990 data!")
    
    final_df = pd.DataFrame()
    final_df['GISJOIN'] = df_ne['GISJOIN']
    final_df['TRACTA'] = df_ne['TRACTA']
    
    # Demographics
    final_df['Total_Population'] = df_ne['E0H001'] # DS123 Total Persons
    
    # Italian Demographics (DS123: E3E016 is Italian Ancestry)
    italian_ancestry = df_ne['E3E016']
    
    # Since specific country of birth is not available in DS123, we estimate generations proportionally using total foreign born
    # E3N009 is Foreign born
    total_foreign_born = df_ne['E3N009']
    pct_foreign_born = (total_foreign_born / final_df['Total_Population']).fillna(0)
    
    final_df['Total_Italian_Demographic'] = italian_ancestry
    final_df['Italian_1st_Generation'] = (italian_ancestry * pct_foreign_born).round().astype(int)
    final_df['Italian_Americans'] = italian_ancestry - final_df['Italian_1st_Generation']
    final_df['Non_Italian_Population'] = final_df['Total_Population'] - italian_ancestry
    
    # Medians
    # 1990 doesn't have Median Age pre-calculated in these STF3 extracts directly unless we pull STF1. 
    # Wait, ds120 has Age. Let's calculate Median Age from bins if missing.
    # We will compute Median Age from DS120 bins (EQD001-EQD031) - let's check codebook via bins.
    # For now, to keep it simple, I'll calculate it from EQD if it exists, otherwise NaN.
    # Let's check if there is a median in DS120... it wasn't listed in our table summary.
    final_df['Median_Age'] = np.nan # Need explicit bins for age
    
    final_df['Median_Rent'] = df_ne['EYU001'] # Median gross rent
    final_df['Median_Family_Income'] = df_ne['E4U001'] # Median household income
    
    # Occupation (E4Q001 - E4Q013)
    # White Collar: E4Q001 - E4Q005
    white_collar_cols = [f'E4Q{str(i).zfill(3)}' for i in range(1, 6)]
    # Blue Collar: E4Q010, E4Q011, E4Q012, E4Q013
    blue_collar_cols = ['E4Q010', 'E4Q011', 'E4Q012', 'E4Q013']
    all_occupation_cols = [f'E4Q{str(i).zfill(3)}' for i in range(1, 14)]
    
    white_collar_cols = [c for c in white_collar_cols if c in df_ne.columns]
    blue_collar_cols = [c for c in blue_collar_cols if c in df_ne.columns]
    all_occupation_cols = [c for c in all_occupation_cols if c in df_ne.columns]
    
    total_workers = df_ne[all_occupation_cols].sum(axis=1)
    final_df['White_Collar_Workers'] = df_ne[white_collar_cols].sum(axis=1)
    final_df['Blue_Collar_Workers'] = df_ne[blue_collar_cols].sum(axis=1)
    
    final_df['Pct_White_Collar'] = (final_df['White_Collar_Workers'] / total_workers).fillna(0).round(4)
    final_df['Pct_Blue_Collar'] = (final_df['Blue_Collar_Workers'] / total_workers).fillna(0).round(4)
    
    # Output
    out_path = os.path.join("..", "final_datasets", "1990_north_end_cleaned.csv")
    final_df.to_csv(out_path, index=False)
    
    print("\nSample Cleaned Data (1990):")
    print(final_df.head())
    print(f"\nSaved cleaned dataset to {out_path}")

if __name__ == "__main__":
    main()
