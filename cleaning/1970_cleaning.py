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
    print("Loading 1970 Tract Data...")
    raw_dir = os.path.join("..", "raw_datasets")
    
    df95 = pd.read_csv(os.path.join(raw_dir, "nhgis0008_ds95_1970_tract.csv"), encoding="latin1", skiprows=[1], low_memory=False)
    df97 = pd.read_csv(os.path.join(raw_dir, "nhgis0008_ds97_1970_tract.csv"), encoding="latin1", skiprows=[1], low_memory=False)
    df99 = pd.read_csv(os.path.join(raw_dir, "nhgis0008_ds99_1970_tract.csv"), encoding="latin1", skiprows=[1], low_memory=False)
    
    # Merge on GISJOIN
    df_merged = df95.merge(df97, on=['GISJOIN', 'TRACTA'], suffixes=('', '_y'))
    df_merged = df_merged.merge(df99, on=['GISJOIN', 'TRACTA'], suffixes=('', '_z'))
    
    # Filter to North End Tracts (301, 302, 303, 304, 305) in Suffolk County (25)
    # TRACTA could be int or string depending on pandas inference
    north_end_tracts = ['301', '302', '303', '304', '305', 301, 302, 303, 304, 305]
    
    df_ne = df_merged[(df_merged['COUNTYA'] == 25) | (df_merged['COUNTYA'] == '25') | (df_merged['COUNTYA'] == 250)]
    df_ne = df_ne[df_ne['TRACTA'].isin(north_end_tracts)].copy()
    
    print(f"\nFound {len(df_ne)} North End Tracts in 1970.")
    
    if df_ne.empty:
        raise ValueError("No North End tracts found in 1970 data!")
    
    # Dataframe to hold our cleaned data
    final_df = pd.DataFrame()
    final_df['GISJOIN'] = df_ne['GISJOIN']
    final_df['TRACTA'] = df_ne['TRACTA']
    
    # ---------------------------
    # Demographics
    # ---------------------------
    final_df['Total_Population'] = df_ne['CY7001'] # DS97
    
    # Italian Demographics from DS99
    # C1Z020: Native (of foreign or mixed parentage) >> Italy
    # C1Z053: Foreign born >> Italy
    italian_1st_gen = df_ne['C1Z053']
    italian_americans = df_ne['C1Z020']
    italian_fs = italian_1st_gen + italian_americans
    
    final_df['Total_Italian_Foreign_Stock'] = italian_fs
    final_df['Italian_1st_Generation'] = italian_1st_gen
    final_df['Italian_Americans'] = italian_americans
    final_df['Non_Italian_Population'] = final_df['Total_Population'] - italian_fs
    
    # ---------------------------
    # Median Age
    # ---------------------------
    # Using DS95 (CE6001 - CE6202)
    # Let's map the bins.
    # We found CE6001: Male <1, CE6002: 1, CE6003: 2... CE6020: 19
    # CE6102: Female <1, CE6103: 1, CE6104: 2...
    # Since we need to calculate median, we can construct 5-year bins for simplicity or 1-year bins if we want to be exhaustive.
    # 1-year bins are easy:
    age_bins = []
    age_bins.append((0, 1, ['CE6001', 'CE6102']))
    for i in range(1, 100):
        male_col = f'CE6{str(i).zfill(3)}'
        female_col = f'CE61{str(i+2).zfill(2)}' if i < 98 else f'CE620{i-98}' # wait, this is getting complicated.
        # Let's verify female codes: CE6103 is 1 year, CE6104 is 2 years...
        # CE6102 + i is the female column. 
        # i=1: 6103. i=97: 6199. i=98: 6200. i=99: 6201.
        if i < 98:
            female_col = f'CE6{str(102+i)}'
        else:
            female_col = f'CE6{str(102+i)}' # 102+98 = 200 => CE6200.
        
        age_bins.append((i, i+1, [male_col, female_col]))
    
    # CE6101 is male 100+, CE6202 is female 100+
    age_bins.append((100, np.nan, ['CE6101', 'CE6202']))
    
    final_df['Median_Age'] = df_ne.apply(lambda r: calculate_median_grouped(r, age_bins), axis=1).round(1)
    
    # ---------------------------
    # Median Rent
    # ---------------------------
    # DS97 CS2001 - CS2014
    rent_bins = [
        (0, 30, 'CS2001'), (30, 40, 'CS2002'), (40, 50, 'CS2003'),
        (50, 60, 'CS2004'), (60, 70, 'CS2005'), (70, 80, 'CS2006'),
        (80, 90, 'CS2007'), (90, 100, 'CS2008'), (100, 120, 'CS2009'),
        (120, 150, 'CS2010'), (150, 200, 'CS2011'), (200, 250, 'CS2012'),
        (250, 300, 'CS2013'), (300, np.nan, 'CS2014')
    ]
    final_df['Median_Rent'] = df_ne.apply(lambda r: calculate_median_grouped(r, rent_bins), axis=1).round(2)
    
    # ---------------------------
    # Median Income
    # ---------------------------
    # DS99 C3T001 - C3T015 (Family Income)
    income_bins = [
        (0, 1000, 'C3T001'), (1000, 2000, 'C3T002'), (2000, 3000, 'C3T003'),
        (3000, 4000, 'C3T004'), (4000, 5000, 'C3T005'), (5000, 6000, 'C3T006'),
        (6000, 7000, 'C3T007'), (7000, 8000, 'C3T008'), (8000, 9000, 'C3T009'),
        (9000, 10000, 'C3T010'), (10000, 12000, 'C3T011'), (12000, 15000, 'C3T012'),
        (15000, 25000, 'C3T013'), (25000, 50000, 'C3T014'), (50000, np.nan, 'C3T015')
    ]
    final_df['Median_Family_Income'] = df_ne.apply(lambda r: calculate_median_grouped(r, income_bins), axis=1).round(2)
    
    # ---------------------------
    # Occupation
    # ---------------------------
    # White Collar: C27001 - C27017
    white_collar_cols = [f'C27{str(i).zfill(3)}' for i in range(1, 18)]
    # Blue Collar: C27018 - C27032
    blue_collar_cols = [f'C27{str(i).zfill(3)}' for i in range(18, 33)]
    
    all_occupation_cols = [f'C27{str(i).zfill(3)}' for i in range(1, 43)]
    total_workers = df_ne[all_occupation_cols].sum(axis=1)
    
    final_df['White_Collar_Workers'] = df_ne[white_collar_cols].sum(axis=1)
    final_df['Blue_Collar_Workers'] = df_ne[blue_collar_cols].sum(axis=1)
    
    final_df['Pct_White_Collar'] = (final_df['White_Collar_Workers'] / total_workers).fillna(0).round(4)
    final_df['Pct_Blue_Collar'] = (final_df['Blue_Collar_Workers'] / total_workers).fillna(0).round(4)
    
    # Output to final_datasets
    os.makedirs("../final_datasets", exist_ok=True)
    out_path = os.path.join("..", "final_datasets", "1970_north_end_cleaned.csv")
    final_df.to_csv(out_path, index=False)
    
    print("\nSample Cleaned Data (1970):")
    print(final_df.head())
    print(f"\nSaved cleaned dataset to {out_path}")

if __name__ == "__main__":
    main()
