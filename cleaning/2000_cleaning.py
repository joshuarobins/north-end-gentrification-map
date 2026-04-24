import pandas as pd
import numpy as np
import os

def main():
    print("Loading 2000 Tract Data...")
    raw_dir = os.path.join("..", "raw_datasets")
    
    df146 = pd.read_csv(os.path.join(raw_dir, "nhgis0010_ds146_2000_tract.csv"), encoding="latin1", skiprows=[1], low_memory=False)
    df151 = pd.read_csv(os.path.join(raw_dir, "nhgis0010_ds151_2000_tract.csv"), encoding="latin1", skiprows=[1], low_memory=False)
    
    # Merge on GISJOIN
    df_merged = df146.merge(df151, on=['GISJOIN', 'TRACTA'], suffixes=('', '_y'))
    
    # Filter to North End Tracts (301, 302, 303, 304, 305) in Suffolk County
    # In 2000, tract IDs are 6 digits padded with 00 for the suffix. 
    # For example, Tract 301 is 30100. Tract 3.01 is 301 (or 00301).
    df_ne = df_merged[(df_merged['COUNTYA'] == 25) | (df_merged['COUNTYA'] == '25') | (df_merged['COUNTYA'] == 250) | (df_merged['COUNTYA'] == 2500) | (df_merged['COUNTYA'] == 25000)]
    
    # Restrict strictly to 30100-30500
    valid_tracts = ['30100', '30200', '30300', '30400', '30500']
    df_ne = df_ne[df_ne['TRACTA'].astype(str).isin(valid_tracts)].copy()
    
    print(f"\nFound {len(df_ne)} North End Tracts in 2000.")
    
    if df_ne.empty:
        raise ValueError("No North End tracts found in 2000 data!")
    
    final_df = pd.DataFrame()
    final_df['GISJOIN'] = df_ne['GISJOIN']
    # Strip the trailing '00' from the tract ID to match previous decades
    final_df['TRACTA'] = df_ne['TRACTA'].astype(str).apply(lambda x: x[:-2] if x.endswith('00') else x)
    
    # Demographics
    final_df['Total_Population'] = df_ne['FL5001'] # DS146 Total Persons
    
    # Italian Demographics
    # GV5040: Italian Ancestry (Total Italian Ancestry)
    total_italian = df_ne['GV5040']
    final_df['Total_Italian_Demographic'] = total_italian
    
    # Proportional estimation for generations
    # GI8002: Foreign born
    # GHC001: Total Population (from DS151)
    pct_foreign_born = (df_ne['GI8002'] / df_ne['GHC001']).fillna(0)
    
    final_df['Italian_1st_Generation'] = (total_italian * pct_foreign_born).round().astype(int)
    final_df['Italian_Americans'] = total_italian - final_df['Italian_1st_Generation']
    final_df['Non_Italian_Population'] = final_df['Total_Population'] - total_italian
    
    # Medians
    final_df['Median_Age'] = df_ne['FM6001']
    final_df['Median_Rent'] = df_ne['GBO001'] # Median gross rent
    final_df['Median_Family_Income'] = df_ne['GMY001'] # Median household income
    
    # Occupation
    # White Collar: GMJ001, GMJ003, GMJ007, GMJ009
    white_collar_cols = ['GMJ001', 'GMJ003', 'GMJ007', 'GMJ009']
    # Blue Collar: GMJ005, GMJ006, GMJ011, GMJ012
    blue_collar_cols = ['GMJ005', 'GMJ006', 'GMJ011', 'GMJ012']
    all_occupation_cols = [f'GMJ{str(i).zfill(3)}' for i in range(1, 13)]
    
    white_collar_cols = [c for c in white_collar_cols if c in df_ne.columns]
    blue_collar_cols = [c for c in blue_collar_cols if c in df_ne.columns]
    all_occupation_cols = [c for c in all_occupation_cols if c in df_ne.columns]
    
    total_workers = df_ne[all_occupation_cols].sum(axis=1)
    final_df['White_Collar_Workers'] = df_ne[white_collar_cols].sum(axis=1)
    final_df['Blue_Collar_Workers'] = df_ne[blue_collar_cols].sum(axis=1)
    
    final_df['Pct_White_Collar'] = (final_df['White_Collar_Workers'] / total_workers).fillna(0).round(4)
    final_df['Pct_Blue_Collar'] = (final_df['Blue_Collar_Workers'] / total_workers).fillna(0).round(4)
    
    # Output
    out_path = os.path.join("..", "final_datasets", "2000_north_end_cleaned.csv")
    final_df.to_csv(out_path, index=False)
    
    print("\nSample Cleaned Data (2000):")
    print(final_df.head())
    print(f"\nSaved cleaned dataset to {out_path}")

if __name__ == "__main__":
    main()
